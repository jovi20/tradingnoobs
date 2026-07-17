"""
Trading Noobs - Unified Market Data Service
Routes requests to appropriate providers based on asset type:
- US Stocks → Finnhub
- A-Shares/HK Stocks → AKShare  
- Crypto → Binance
"""
import re
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
import finnhub
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
import asyncio
from fastapi.concurrency import run_in_threadpool

from models import AssetMaster, AssetMetadata, AssetCoreType, AssetMarket, AssetCurrency, AssetRiskLevel
from observability import get_structured_logger, log_event
from services.market_data_job_service import enqueue_daily_backfill
from services.market_data_orchestrator import get_daily_bars_with_metadata, get_quote_with_metadata
from services.market_data_repository import MarketDataRepository
from services.market_data_types import MarketDataRequest
from services.market_provider_registry import MarketDataCapability
from services.market_session_calendar import expected_daily_sessions
from services.provider_router import detect_asset_route
from services.providers import yfinance_provider
from services.platform_config_service import get_finnhub_api_key

# Cache TTL in seconds (1 minute)
CACHE_TTL_SECONDS = 60
logger = get_structured_logger("market_data")


class MarketDataService:
    # Class-level cache shared across instances
    _quote_cache: Dict[str, Dict[str, Any]] = {}

    def _get_cached_quote(self, symbol: str, fetch_func):
        """
        Generic caching wrapper for any quote fetching function
        """
        symbol_upper = symbol.upper()
        cache_key = f"quote_{symbol_upper}"
        
        # Check cache
        cached = MarketDataService._quote_cache.get(cache_key)
        if cached:
            cache_age = datetime.now() - cached['timestamp']
            if cache_age.total_seconds() < CACHE_TTL_SECONDS:
                return cached['data']
        
        # Fetch fresh data
        try:
            data = fetch_func()
            
            # Update cache
            MarketDataService._quote_cache[cache_key] = {
                'data': data,
                'timestamp': datetime.now()
            }
            return data
        except Exception as e:
            log_event(logger, "warning", "quote_fetch_failed", symbol=symbol, error=str(e))
            raise e
    _asset_type_cache: Dict[str, str] = {}
    
    def __init__(self, db: Session, *, persistence_db: Session | None = None):
        self.db = db
        self._shared_persistence_db = persistence_db
        self._finnhub_client = None

    @contextmanager
    def _persistence_unit(self):
        if self._shared_persistence_db is not None:
            yield self._shared_persistence_db
            self._shared_persistence_db.flush()
            return

        persistence_db = Session(bind=self.db.get_bind())
        try:
            yield persistence_db
            persistence_db.commit()
        except Exception:
            persistence_db.rollback()
            raise
        finally:
            persistence_db.close()

    @staticmethod
    def _quote_currency(market: str, symbol: str) -> str | None:
        normalized_market = (market or "").upper()
        if normalized_market == "US":
            return "USD"
        if normalized_market == "A_SHARE":
            return "CNY"
        if normalized_market == "HK":
            return "HKD"
        if normalized_market == "CRYPTO":
            for suffix in ("USDT", "USDC", "BUSD", "BTC", "ETH", "BNB"):
                if symbol.upper().endswith(suffix):
                    return suffix
        if normalized_market == "FOREX" and len(symbol) == 6:
            return symbol.upper()[3:]
        return None

    @staticmethod
    def _find_asset(db: Session, *, symbol: str, market: str) -> AssetMaster | None:
        normalized_symbol = symbol.upper()
        exact_codes = [normalized_symbol, f"{market.upper()}:{normalized_symbol}"]
        asset = (
            db.query(AssetMaster)
            .filter(AssetMaster.canonical_code.in_(exact_codes))
            .order_by(AssetMaster.id)
            .first()
        )
        if asset is not None:
            return asset
        candidates = (
            db.query(AssetMaster)
            .filter(AssetMaster.display_symbol == normalized_symbol)
            .order_by(AssetMaster.id)
            .all()
        )
        for candidate in candidates:
            if (candidate.metadata_json or {}).get("market") == market.upper():
                return candidate
        return candidates[0] if len(candidates) == 1 else None

    def _persist_quote_payload(
        self,
        payload: Dict[str, Any],
        *,
        exchange: str | None,
    ) -> None:
        quote = payload.get("quote") or {}
        provider = payload.get("provider") or quote.get("provider")
        if not provider or quote.get("c") is None:
            return

        try:
            with self._persistence_unit() as persistence_db:
                repository = MarketDataRepository(persistence_db)
                asset = repository.resolve_or_create_asset(
                    symbol=payload["symbol"],
                    market=payload.get("market") or "UNKNOWN",
                    asset_type=payload.get("asset_type") or "UNKNOWN",
                    quote_currency=self._quote_currency(
                        payload.get("market") or "",
                        payload["symbol"],
                    ),
                    name=quote.get("name") or payload["symbol"],
                )
                repository.upsert_provider_symbol_mapping(
                    asset_id=asset.id,
                    provider_key=provider,
                    provider_symbol=payload["symbol"],
                    provider_market=payload.get("market") or "UNKNOWN",
                    capabilities=["LATEST_QUOTE"],
                )
                received_at = datetime.now(timezone.utc)
                stored = repository.upsert_latest_quote(
                    asset_id=asset.id,
                    provider=provider,
                    price=quote.get("c"),
                    previous_close=quote.get("pc"),
                    open_price=quote.get("o"),
                    high_price=quote.get("h"),
                    low_price=quote.get("l"),
                    volume=quote.get("volume"),
                    change_amount=quote.get("d"),
                    change_percent=quote.get("dp"),
                    currency=asset.quote_currency,
                    market_time=quote.get("as_of"),
                    received_at=received_at,
                    raw_payload={
                        "source_refs": quote.get("source_refs") or payload.get("source_refs") or [],
                        "freshness": quote.get("freshness") or payload.get("freshness"),
                    },
                )
                coverage_date = (stored.market_time or stored.received_at).date()
                repository.upsert_watermark(
                    asset_id=asset.id,
                    data_type="LATEST_QUOTE",
                    provider=provider,
                    covered_from=coverage_date,
                    covered_to=coverage_date,
                    last_success_at=received_at,
                )

                warmup_end = received_at.replace(hour=0, minute=0, second=0, microsecond=0)
                warmup_start = warmup_end - timedelta(days=365)
                daily_route = detect_asset_route(
                    payload["symbol"],
                    exchange=exchange,
                    core_type=payload.get("asset_type"),
                    market=payload.get("market"),
                    capability=MarketDataCapability.DAILY_BAR,
                )
                has_daily_coverage = False
                for daily_provider in daily_route.provider_order:
                    daily_watermark = repository.get_watermark(
                        asset_id=asset.id,
                        data_type="DAILY_BAR",
                        provider=daily_provider,
                    )
                    if (
                        daily_watermark is not None
                        and daily_watermark.covered_from is not None
                        and daily_watermark.covered_to is not None
                        and daily_watermark.covered_from <= warmup_start.date()
                        and daily_watermark.covered_to >= warmup_end.date() - timedelta(days=7)
                    ):
                        has_daily_coverage = True
                        break

                if not has_daily_coverage:
                    enqueue_daily_backfill(
                        persistence_db,
                        symbol=payload["symbol"],
                        exchange=exchange,
                        start=warmup_start,
                        end=warmup_end,
                    )
        except Exception as error:
            log_event(
                logger,
                "warning",
                "market_quote_persistence_failed",
                symbol=payload.get("symbol"),
                error=str(error),
            )
            if self._shared_persistence_db is not None:
                raise

    def _load_last_known_quote(self, payload: Dict[str, Any]) -> Dict[str, Any] | None:
        try:
            with self._persistence_unit() as persistence_db:
                asset = self._find_asset(
                    persistence_db,
                    symbol=payload.get("symbol") or "",
                    market=payload.get("market") or "UNKNOWN",
                )
                if asset is None:
                    return None
                stored = MarketDataRepository(persistence_db).get_latest_quote(
                    asset_id=asset.id,
                    quality_statuses=["GOOD"],
                )
                if stored is None:
                    return None
                as_of = stored.market_time or stored.received_at
                refs = [
                    f"provider:{stored.provider}",
                    f"symbol:{payload.get('symbol')}",
                    "storage:latest_market_quotes",
                ]
                return {
                    "c": float(stored.price),
                    "pc": float(stored.previous_close) if stored.previous_close is not None else None,
                    "h": float(stored.high_price) if stored.high_price is not None else None,
                    "l": float(stored.low_price) if stored.low_price is not None else None,
                    "o": float(stored.open_price) if stored.open_price is not None else None,
                    "d": float(stored.change_amount) if stored.change_amount is not None else None,
                    "dp": float(stored.change_percent) if stored.change_percent is not None else None,
                    "volume": float(stored.volume) if stored.volume is not None else None,
                    "name": asset.name,
                    "provider": stored.provider,
                    "as_of": as_of.isoformat(),
                    "freshness": "STALE",
                    "degraded": True,
                    "degraded_reason": payload.get("degraded_reason") or "Live providers unavailable",
                    "source_refs": refs,
                }
        except Exception as error:
            log_event(
                logger,
                "warning",
                "market_quote_persisted_fallback_failed",
                symbol=payload.get("symbol"),
                error=str(error),
            )
            return None

    @staticmethod
    def _daily_row_payload(row) -> Dict[str, Any]:
        return {
            "date": row.trading_date.isoformat(),
            "open": float(row.open_price),
            "high": float(row.high_price),
            "low": float(row.low_price),
            "close": float(row.close_price),
            "volume": float(row.volume) if row.volume is not None else None,
        }

    @staticmethod
    def _has_complete_local_daily_coverage(
        rows,
        *,
        market: str,
        start: date,
        end: date,
    ) -> bool:
        if not rows:
            return False
        expected_sessions = expected_daily_sessions(market, start, end)
        if expected_sessions is None:
            return False
        stored_dates = {row.trading_date for row in rows}
        return expected_sessions.issubset(stored_dates)

    def _load_persisted_daily_bars(
        self,
        request: MarketDataRequest,
        start: datetime,
        end: datetime,
        *,
        require_coverage: bool,
    ) -> List[Dict[str, Any]]:
        route = detect_asset_route(
            request.symbol,
            exchange=request.exchange,
            core_type=request.core_type,
            market=request.market,
            instrument=request.instrument,
            capability=MarketDataCapability.DAILY_BAR,
            credential_availability={"finnhub_api_key": bool(get_finnhub_api_key(self.db))},
        )
        try:
            with self._persistence_unit() as persistence_db:
                asset = self._find_asset(
                    persistence_db,
                    symbol=route.normalized_symbol,
                    market=route.market,
                )
                if asset is None:
                    return []
                repository = MarketDataRepository(persistence_db)
                for provider in route.provider_order:
                    adjustment_mode = "QFQ" if provider == "akshare" else "RAW"
                    watermark = repository.get_watermark(
                        asset_id=asset.id,
                        data_type="DAILY_BAR",
                        provider=provider,
                    )
                    if require_coverage:
                        if watermark is None or watermark.covered_from is None or watermark.covered_to is None:
                            continue
                        requested_end = min(end.date(), date.today())
                        if watermark.covered_from > start.date():
                            continue
                        if watermark.covered_to < requested_end - timedelta(days=7):
                            continue
                    rows = repository.get_daily_bars(
                        asset_id=asset.id,
                        start_date=start,
                        end_date=end,
                        provider=provider,
                        adjustment_mode=adjustment_mode,
                        quality_statuses=["GOOD"],
                    )
                    if rows and (
                        not require_coverage
                        or self._has_complete_local_daily_coverage(
                            rows,
                            market=route.market,
                            start=start.date(),
                            end=min(requested_end, watermark.covered_to),
                        )
                    ):
                        return [self._daily_row_payload(row) for row in rows]
                return []
        except Exception as error:
            log_event(
                logger,
                "warning",
                "market_daily_persisted_read_failed",
                symbol=request.symbol,
                error=str(error),
            )
            return []

    def _persist_daily_payload(self, payload: Dict[str, Any]) -> None:
        rows = payload.get("rows") or []
        provider = payload.get("provider")
        if not provider or not rows:
            return
        try:
            with self._persistence_unit() as persistence_db:
                repository = MarketDataRepository(persistence_db)
                asset = repository.resolve_or_create_asset(
                    symbol=payload["symbol"],
                    market=payload.get("market") or "UNKNOWN",
                    asset_type=payload.get("asset_type") or "UNKNOWN",
                    quote_currency=self._quote_currency(
                        payload.get("market") or "",
                        payload["symbol"],
                    ),
                )
                repository.upsert_provider_symbol_mapping(
                    asset_id=asset.id,
                    provider_key=provider,
                    provider_symbol=payload["symbol"],
                    provider_market=payload.get("market") or "UNKNOWN",
                    capabilities=["DAILY_BAR"],
                )
                stored_rows = repository.upsert_daily_bars(
                    asset_id=asset.id,
                    provider=provider,
                    bars=rows,
                    adjustment_mode=payload.get("adjustment_mode") or "RAW",
                    currency=asset.quote_currency,
                )
                covered_dates = [row.trading_date for row in stored_rows]
                if covered_dates:
                    repository.upsert_watermark(
                        asset_id=asset.id,
                        data_type="DAILY_BAR",
                        provider=provider,
                        covered_from=min(covered_dates),
                        covered_to=max(covered_dates),
                        last_success_at=datetime.now(timezone.utc),
                    )
        except Exception as error:
            log_event(
                logger,
                "warning",
                "market_daily_persistence_failed",
                symbol=payload.get("symbol"),
                provider=provider,
                error=str(error),
            )
            if self._shared_persistence_db is not None:
                raise

    async def _fetch_with_timeout(self, coro, timeout=5):
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            raise Exception(f"Market data request timed out ({timeout}s)")

    def _get_finnhub_client(self):
        """Lazy load Finnhub client"""
        if self._finnhub_client is None:
            api_key = get_finnhub_api_key(self.db)
            if api_key:
                self._finnhub_client = finnhub.Client(api_key=api_key)
        return self._finnhub_client

    def detect_asset_type(self, symbol: str, exchange: Optional[str] = None) -> str:
        """
        Detect asset type based on symbol and exchange
        Returns: 'A_STOCK', 'HK_STOCK', 'CRYPTO', 'US_STOCK'
        """
        symbol_upper = symbol.upper()
        exchange_upper = (exchange or '').upper()
        
        # Crypto detection
        crypto_patterns = ['USDT', 'BUSD', 'BTC', 'ETH', 'BNB']
        if any(symbol_upper.endswith(p) for p in crypto_patterns):
            return 'CRYPTO'
        if 'BINANCE' in exchange_upper or exchange_upper in ['CRYPTO', 'BINANCE']:
            return 'CRYPTO'
        
        # A-Share detection (6-digit codes)
        a_share_patterns = [
            r'^0[0-3]\d{4}$',   # 深圳主板/中小板 000xxx, 001xxx, 002xxx, 003xxx
            r'^300\d{3}$',      # 创业板 300xxx
            r'^6[0-9]\d{4}$',   # 上海主板 600xxx, 601xxx, 603xxx, 688xxx
            r'^[48][37]\d{4}$', # 北交所 43xxxx, 83xxxx, 87xxxx
        ]
        for pattern in a_share_patterns:
            if re.match(pattern, symbol_upper):
                return 'A_STOCK'
        
        # Fund detection (6-digit codes starting with specific prefixes)
        fund_patterns = [
            r'^5[016]\d{4}$',   # 场内基金 (50, 51, 56)
            r'^1[568]\d{4}$',   # 场内基金 (15, 16, 18)
            r'^0\d{5}$',        # 场外基金 (0xxxxx - note: 000xxx collision with SZ stock handled by order)
        ]
        for pattern in fund_patterns:
            if re.match(pattern, symbol_upper):
                return 'ETF_EQUITY' # Treating all funds as ETF_EQUITY for simplicity in types for now
        
        # HK Stock detection
        if symbol_upper.endswith('.HK') or exchange_upper in ['HKEX', 'HK', 'HONG KONG']:
            return 'HK_STOCK'
        if re.match(r'^\d{5}$', symbol_upper):  # 5-digit HK code
            return 'HK_STOCK'
        
        # Forex detection: 6-letter alphabetic pairs
        # Common pattern: USDCNY, EURUSD, GBPJPY
        if re.match(r'^[A-Z]{6}$', symbol_upper):
             # We can be more specific, but for now 6 alphabetic letters is a strong hint for FX
             return 'FOREX'

        # US Stock detection (Basic: 1-5 letters, 7-8 letters)
        if re.match(r'^[A-Z\.]{1,8}$', symbol_upper):
            return 'US_STOCK'

        # Default/Unknown
        return 'UNKNOWN'

    async def get_or_create_asset_metadata(self, symbol: str, name: Optional[str] = None, exchange: Optional[str] = None) -> AssetMetadata:
        """
        Get asset metadata from DB, or create/detect it using deterministic rules.
        """
        symbol_upper = symbol.upper()
        
        # 1. Check Database
        metadata = self.db.query(AssetMetadata).filter(AssetMetadata.symbol == symbol_upper).first()
        if metadata and metadata.core_type: # Ensure it's fully populated
            return metadata
            
        if not metadata:
            metadata = AssetMetadata(symbol=symbol_upper, name=name or symbol_upper)
            self.db.add(metadata)
        
        # 2. Rule-based Detection (Market and Currency)
        base_type = self.detect_asset_type(symbol, exchange)
        
        # Market Mapping
        if base_type == 'A_STOCK':
            metadata.market = AssetMarket.A_SHARE
            metadata.currency = AssetCurrency.CNY
            metadata.core_type = AssetCoreType.STOCK
        elif base_type == 'HK_STOCK':
            metadata.market = AssetMarket.HK
            metadata.currency = AssetCurrency.HKD
            metadata.core_type = AssetCoreType.STOCK
        elif base_type == 'CRYPTO':
            metadata.core_type = AssetCoreType.CRYPTO
            metadata.market = AssetMarket.CRYPTO
            metadata.currency = AssetCurrency.USD # Most pairs are USDT/USD
        elif base_type == 'ETF_EQUITY':
            # Could be A-share or HK or US. Let's check symbol.
            if re.match(r'^\d{6}$', symbol_upper):
                metadata.market = AssetMarket.A_SHARE
                metadata.currency = AssetCurrency.CNY
            metadata.core_type = AssetCoreType.FUND
        elif base_type == 'FOREX':
            metadata.market = AssetMarket.FOREX
            metadata.core_type = AssetCoreType.FX
            # Currency depends on the pair, LLM is better here
            
        # 3. Deterministic final fallbacks
        if not metadata.core_type:
             metadata.core_type = AssetCoreType.STOCK if base_type == 'US_STOCK' else AssetCoreType.STOCK
        if not metadata.market:
             metadata.market = AssetMarket.US if base_type == 'US_STOCK' else AssetMarket.US
        if not metadata.currency:
             metadata.currency = AssetCurrency.USD
        if not metadata.risk_level:
             metadata.risk_level = AssetRiskLevel.GROWTH # Default
             if metadata.core_type == AssetCoreType.CRYPTO:
                 metadata.risk_level = AssetRiskLevel.AGGRESSIVE
             elif metadata.core_type == AssetCoreType.FX:
                 metadata.risk_level = AssetRiskLevel.MODERATE
        
        self.db.commit()
        self.db.refresh(metadata)
        return metadata

    async def detect_asset_type_enhanced(self, symbol: str, exchange: Optional[str] = None) -> str:
        """
        Maintains backward compatibility but uses the new metadata system.
        """
        metadata = await self.get_or_create_asset_metadata(symbol, exchange=exchange)
        return metadata.core_type.value if metadata.core_type else "EQUITY"

    async def get_quote(
        self, 
        symbol: str, 
        exchange: Optional[str] = None,
        core_type: Optional[str] = None,
        market: Optional[str] = None,
        instrument: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get quote from appropriate provider based on asset type
        Hints (core_type, market, instrument) help in choosing the right provider
        """
        payload = await run_in_threadpool(
            get_quote_with_metadata,
            MarketDataRequest(
                symbol=symbol,
                exchange=exchange,
                core_type=core_type,
                market=market,
                instrument=instrument,
            ),
            self.db,
        )
        if payload.get("quote") is not None:
            self._persist_quote_payload(payload, exchange=exchange)
            return payload["quote"]

        stored_quote = self._load_last_known_quote(payload)
        if stored_quote is not None:
            return stored_quote

        return {
            "error": payload.get("error"),
            "provider": payload.get("provider"),
            "freshness": payload.get("freshness"),
            "degraded": payload.get("degraded", True),
            "degraded_reason": payload.get("degraded_reason"),
            "source_refs": payload.get("source_refs", []),
        }

    async def _get_finnhub_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get quote from Finnhub (US stocks) with caching and fallback to YFinance
        """
        symbol_upper = symbol.upper()
        cache_key = f"finnhub_{symbol_upper}"
        
        # Check cache first
        cached = MarketDataService._quote_cache.get(cache_key)
        if cached:
            cache_age = datetime.now() - cached['timestamp']
            if cache_age.total_seconds() < CACHE_TTL_SECONDS:
                log_event(logger, "debug", "finnhub_quote_cache_hit", symbol=symbol_upper)
                return cached['data']
            else:
                log_event(logger, "debug", "finnhub_quote_cache_expired", symbol=symbol_upper)
        
        # 1. Try Finnhub first
        try:
            client = self._get_finnhub_client()
            if client:
                data = await run_in_threadpool(client.quote, symbol_upper)
                # Check if data is valid (Finnhub sometimes returns 0s for invalid symbols, but usually c=0)
                # But for valid symbol c should be > 0 ideally, or at least pc
                if data.get('c') == 0 and data.get('pc') == 0:
                     raise ValueError("Finnhub returned empty data")
                     
                result = {
                    'c': data.get('c'),   # current price
                    'pc': data.get('pc'), # previous close
                    'h': data.get('h'),   # high
                    'l': data.get('l'),   # low
                    'o': data.get('o'),   # open
                    'd': data.get('d'),   # change
                    'dp': data.get('dp'), # change percent
                    'name': symbol_upper # Finnhub quote doesn't return name, use symbol
                }
                
                # Update cache
                MarketDataService._quote_cache[cache_key] = {
                    'data': result,
                    'timestamp': datetime.now()
                }
                log_event(logger, "debug", "finnhub_quote_cache_updated", symbol=symbol_upper)
                
                return result
        except Exception as e:
            log_event(logger, "warning", "finnhub_quote_failed", symbol=symbol, error=str(e))
            # Continue to fallback
            
        # 2. Fallback to Yahoo Finance
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol.upper())
            info = await run_in_threadpool(getattr, ticker, "fast_info")
            
            if not info.last_price:
                 raise ValueError("Yahoo Finance returned empty data")

            previous_close = info.previous_close
            current_price = info.last_price
            change_percent = 0
            if previous_close:
                change_percent = ((current_price - previous_close) / previous_close) * 100

            return {
                'c': current_price,
                'pc': previous_close,
                'h': info.day_high,
                'l': info.day_low,
                'o': info.open,
                'd': current_price - previous_close,
                'dp': change_percent,
                'name': symbol.upper()
            }
        except Exception as yf_error:
            raise Exception(f"Market data failed. Finnhub & YFinance both failed for {symbol}: {str(yf_error)}")

    async def validate_symbol(self, symbol: str, exchange: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate if a symbol exists and return basic info
        """
        try:
            # Get rich metadata (handles DB cache internally)
            metadata = await self.get_or_create_asset_metadata(symbol, exchange=exchange)
            
            # Get current quote
            quote = await self.get_quote(symbol, exchange)
            
            return {
                'valid': True,
                'symbol': symbol.upper(),
                'asset_type': metadata.core_type.value if metadata.core_type else "EQUITY",
                'price': quote.get('c'),
                'name': quote.get('name') or metadata.name,
                'metadata': {
                    'name': metadata.name,
                    'core_type': metadata.core_type.value if metadata.core_type else None,
                    'market': metadata.market.value if metadata.market else None,
                    'currency': metadata.currency.value if metadata.currency else None,
                    'sector': metadata.sector,
                    'risk_level': metadata.risk_level.value if metadata.risk_level else None,
                    'instrument': metadata.instrument
                },
                'provider': quote.get('provider') or self._get_provider_name(
                    metadata.core_type.value if metadata.core_type else "EQUITY"
                ),
                'as_of': quote.get('as_of'),
                'freshness': quote.get('freshness'),
                'degraded': bool(quote.get('degraded', False)),
                'degraded_reason': quote.get('degraded_reason'),
                'source_refs': quote.get('source_refs') or [],
            }
        except Exception as e:
            # Generate candidates on failure
            candidates = []
            symbol_upper = symbol.upper()
            raw_error = str(e)
            
            # Crypto Smart Suggestions
            # If 3-5 letters, suggest adding USDT
            # But avoid double-suffixing if user is already typing the suffix (e.g. "ETHUS" -> "ETHUSUSDT" is bad)
            # So we skip if it ends with common suffix starts
            
            is_potential_len = re.match(r'^[A-Z0-9]{3,5}$', symbol_upper)
            is_pure_numeric = re.match(r'^\d+$', symbol_upper)
            has_partial_suffix = symbol_upper.endswith(('U', 'US', 'USD', 'BUS', 'BUSD'))
            
            if is_potential_len and not is_pure_numeric and not has_partial_suffix:
                 candidates.append({
                     'symbol': f"{symbol_upper}USDT",
                     'asset_type': 'CRYPTO',
                     'reason': '推荐: Binance 交易对'
                 })
            
            # Sanitize Error Message
            error_msg = "查询失败，请检查代码是否正确"
            
            if "Invalid symbol" in raw_error or "-1121" in raw_error:
                error_msg = "未找到该交易对 (Invalid Symbol)"
            elif "not found" in raw_error.lower() or "404" in raw_error:
                error_msg = "未找到该标的"
            elif "empty data" in raw_error:
                error_msg = "暂无该标的数据"
            elif "Unauthorized" in raw_error or "401" in raw_error:
                error_msg = "API 密钥无效或过期"
            elif "AKShare" in raw_error:
                error_msg = "数据源 (AKShare) 查询失败，请稍后再试"
            elif "Binance" in raw_error:
                error_msg = "数据源 (Binance) 查询失败，请检查交易对格式"
            
            return {
                'valid': False,
                'symbol': symbol.upper(),
                'error': error_msg,
                'candidates': candidates,
                'raw_error': raw_error # Optional: keep raw error for debug in console if needed, but UI shows 'error'
            }

    def _get_provider_name(self, asset_type: str) -> str:
        """Get provider name for display"""
        return {
            'A_STOCK': 'AKShare',
            'HK_STOCK': 'AKShare', 
            'CRYPTO': 'Binance',
            'US_STOCK': 'Finnhub',
            'FOREX': 'AKShare/YFinance',
            'ETF_EQUITY': 'AKShare'
        }.get(asset_type, 'Unknown')

    async def get_price_history(self, symbol: str, start: datetime, end: datetime, exchange: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get historical price data (K-lines)
        Returns: [{'date': 'YYYY-MM-DD', 'open': 10, 'high': 12, 'low': 9, 'close': 11, 'volume': 100}, ...]
        """
        asset_type = self.detect_asset_type(symbol, exchange)
        route_hints = {
            "A_STOCK": {"core_type": "STOCK", "market": "A_SHARE"},
            "HK_STOCK": {"core_type": "STOCK", "market": "HK"},
            "CRYPTO": {"core_type": "CRYPTO", "market": "CRYPTO"},
            "US_STOCK": {"core_type": "STOCK", "market": "US"},
        }
        hints = route_hints.get(asset_type)
        if hints is None:
            try:
                return await run_in_threadpool(yfinance_provider.get_history, symbol, start, end)
            except Exception as error:
                log_event(logger, "warning", "history_fetch_failed", symbol=symbol, error=str(error))
                return []

        request = MarketDataRequest(
            symbol=symbol,
            exchange=exchange,
            core_type=hints["core_type"],
            market=hints["market"],
        )
        persisted = self._load_persisted_daily_bars(
            request,
            start,
            end,
            require_coverage=True,
        )
        if persisted:
            return persisted

        payload = await run_in_threadpool(
            get_daily_bars_with_metadata,
            request,
            start,
            end,
            self.db,
        )
        rows = payload.get("rows") or []
        if rows:
            self._persist_daily_payload(payload)
            return rows

        stored_rows = self._load_persisted_daily_bars(
            request,
            start,
            end,
            require_coverage=False,
        )
        if stored_rows:
            log_event(
                logger,
                "warning",
                "market_daily_persisted_fallback_used",
                symbol=symbol,
                provider_failures=payload.get("degraded_reason"),
            )
            return stored_rows
        log_event(
            logger,
            "warning",
            "history_fetch_failed",
            symbol=symbol,
            error=payload.get("degraded_reason") or payload.get("error"),
        )
        return []

    def _get_us_history(self, symbol: str, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        try:
            # Try Finnhub first if key exists
            client = self._get_finnhub_client()
            if client:
                # Finnhub uses unix timestamp in seconds
                res = client.stock_candles(symbol.upper(), 'D', int(start.timestamp()), int(end.timestamp()))
                if res['s'] == 'ok':
                    history = []
                    for i in range(len(res['t'])):
                        history.append({
                            'date': datetime.fromtimestamp(res['t'][i]).strftime('%Y-%m-%d'),
                            'open': res['o'][i],
                            'high': res['h'][i],
                            'low': res['l'][i],
                            'close': res['c'][i],
                            'volume': res['v'][i]
                        })
                    return history
        except:
            pass
            
        return self._get_yfinance_history(symbol, start, end)

    def _get_yfinance_history(self, symbol: str, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        return yfinance_provider.get_history(symbol, start, end)

    async def validate_api_key(self):
        """Test if the Finnhub API key works"""
        try:
            return await self._get_finnhub_quote('AAPL')
        except Exception as e:
            raise Exception(f"Validation failed: {str(e)}")
