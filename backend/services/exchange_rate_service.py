"""
Trading Noobs - Exchange Rate Service
获取外汇汇率并缓存，用于 Dashboard 跨币种资产统一换算。

核心规则:
  1. USDT 不是 USD alias；当前 release contract 明确拒绝该换算。
  2. 跨币种 provider 访问要求 deployment ceiling 与 runtime rollout 同时启用。
  3. 所有已启用换算统一经 USD 中转: X -> USD -> target
"""
from datetime import datetime
from typing import Dict, Optional
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app_config.release_contract import ReleaseContractViolation
from release_profile import RuntimeCapability
from services.capability_service import is_effective_capability_enabled

# 汇率缓存 TTL (10 分钟)
FX_CACHE_TTL_SECONDS = 600

# 模块级缓存
_fx_cache: Dict[str, Dict] = {}


class ExchangeRateUnavailableError(RuntimeError):
    """Raised when a cross-currency rate lacks effective Market authorization."""


async def get_exchange_rate(
    from_currency: str,
    to_currency: str,
    *,
    db: Session | None = None,
    actor_key: str | None = None,
) -> float:
    """
    获取 from_currency -> to_currency 的汇率。
    Provider access requires an explicit database session so runtime rollout can
    be proven. Without that proof, only an identical non-USDT pair is resolved.
    """
    from_c = from_currency.upper().strip()
    to_c = to_currency.upper().strip()

    if "USDT" in {from_c, to_c}:
        raise ReleaseContractViolation(
            "UNSUPPORTED_RELEASE_CURRENCY",
            "currency",
            "USDT",
        )

    if from_c == to_c:
        return 1.0

    if db is None or not is_effective_capability_enabled(
        db,
        RuntimeCapability.MARKET,
        actor_key=actor_key,
    ):
        raise ExchangeRateUnavailableError(
            "MARKET capability is not effectively enabled for exchange-rate access"
        )

    # 统一路径: from_c -> USD -> to_c
    # 1) from_c -> USD
    rate_from_to_usd = 1.0
    if from_c != 'USD':
        rate_from_to_usd = await _get_cached_rate(from_c, 'USD')

    # 2) USD -> to_c
    rate_usd_to_target = 1.0
    if to_c != 'USD':
        rate_usd_to_target = await _get_cached_rate('USD', to_c)

    return rate_from_to_usd * rate_usd_to_target


async def _get_cached_rate(from_c: str, to_c: str) -> float:
    """带缓存的单步汇率获取"""
    cache_key = f"{from_c}_{to_c}"

    cached = _fx_cache.get(cache_key)
    if cached:
        age = (datetime.now() - cached['timestamp']).total_seconds()
        if age < FX_CACHE_TTL_SECONDS:
            return cached['rate']

    rate = await _fetch_rate(from_c, to_c)

    _fx_cache[cache_key] = {'rate': rate, 'timestamp': datetime.now()}
    if rate > 0:
        reverse_key = f"{to_c}_{from_c}"
        _fx_cache[reverse_key] = {'rate': 1.0 / rate, 'timestamp': datetime.now()}

    return rate


async def _fetch_rate(from_c: str, to_c: str) -> float:
    """从数据源获取汇率"""
    pair_symbol = f"{from_c}{to_c}"

    # 1. AKShare
    try:
        rate = await run_in_threadpool(_fetch_akshare_rate, from_c, to_c)
        if rate and rate > 0:
            return rate
    except Exception as e:
        print(f"[FX] AKShare failed for {pair_symbol}: {e}")

    # 2. Yahoo Finance 兜底
    try:
        rate = await run_in_threadpool(_fetch_yfinance_rate, pair_symbol)
        if rate and rate > 0:
            return rate
    except Exception as e:
        print(f"[FX] YFinance failed for {pair_symbol}: {e}")

    raise ExchangeRateUnavailableError(
        f"No exchange-rate provider returned a valid rate for {from_c}->{to_c}"
    )


def _fetch_akshare_rate(from_c: str, to_c: str) -> Optional[float]:
    """通过 AKShare 获取汇率"""
    import akshare as ak

    pair_symbol = f"{from_c}{to_c}"

    # CNY 相关：使用 fx_spot_quote
    if 'CNY' in pair_symbol:
        df = ak.fx_spot_quote()
        cn_map = {
            'USD': '美元', 'CNY': '人民币', 'EUR': '欧元',
            'JPY': '日元', 'GBP': '英镑', 'AUD': '澳元', 'HKD': '港币'
        }
        row = df[
            df['货币对'].str.contains(from_c, case=False) &
            df['货币对'].str.contains(to_c, case=False)
        ]
        if not row.empty:
            price = float(row.iloc[0]['买报价'])
            pair_name = row.iloc[0]['货币对']
            from_name = cn_map.get(from_c, from_c)
            if from_name in pair_name.split('/')[0]:
                return price
            else:
                return 1.0 / price if price > 0 else None
        return None

    # 国际货币对
    df = ak.fx_pair_quote()
    row = df[
        df['货币对'].str.contains(from_c, case=False) &
        df['货币对'].str.contains(to_c, case=False)
    ]
    if not row.empty:
        price = float(row.iloc[0]['买报价'])
        pair_name = row.iloc[0]['货币对']
        if from_c in pair_name.split('/')[0].upper():
            return price
        else:
            return 1.0 / price if price > 0 else None

    return None


def _fetch_yfinance_rate(pair_symbol: str) -> Optional[float]:
    """通过 Yahoo Finance 获取汇率 (格式: USDCNY=X)"""
    import yfinance as yf
    ticker = yf.Ticker(f"{pair_symbol}=X")
    info = ticker.fast_info
    if info.last_price and info.last_price > 0:
        return float(info.last_price)
    return None


async def get_rates_batch(
    currencies: list,
    target_currency: str,
    *,
    db: Session | None = None,
    actor_key: str | None = None,
) -> Dict[str, float]:
    """
    批量获取多个币种到目标币种的汇率。
    返回 { "USD": 1.0, "HKD": 0.128, ... }
    """
    unique = set(c.upper() for c in currencies)
    result = {}
    for c in unique:
        result[c] = await get_exchange_rate(
            c,
            target_currency,
            db=db,
            actor_key=actor_key,
        )
    return result
