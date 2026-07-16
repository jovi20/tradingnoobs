"""
Broker trade-record sync service.

This module syncs execution records only. It intentionally does not fetch quotes,
K-lines, or any market-price data.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal
import hmac
import hashlib
import json
from typing import Any
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

import httpx
from sqlalchemy.orm import Session

from models import BrokerExecution, BrokerSyncRun, User, UserSettings


BINANCE_SPOT_BASE_URL = "https://api.binance.com"
BINANCE_USD_M_FUTURES_BASE_URL = "https://fapi.binance.com"
IBKR_FLEX_BASE_URL = "https://gdcdyn.interactivebrokers.com/Universal/servlet/FlexStatementService.SendRequest"
IBKR_FLEX_STATEMENT_URL = "https://gdcdyn.interactivebrokers.com/Universal/servlet/FlexStatementService.GetStatement"


@dataclass(frozen=True)
class NormalizedBrokerExecution:
    provider: str
    market_type: str | None
    account_ref: str | None
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    trade_time: datetime
    currency: str | None
    commission: Decimal | None
    commission_currency: str | None
    external_trade_id: str
    external_order_id: str | None
    idempotency_key: str
    raw_payload: dict[str, Any]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_datetime(value: date | None, end_of_day: bool = False) -> datetime | None:
    if value is None:
        return None
    clock = time.max if end_of_day else time.min
    return datetime.combine(value, clock, tzinfo=timezone.utc)


def _to_decimal(value: Any, default: str = "0") -> Decimal:
    if value is None or value == "":
        return Decimal(default)
    return Decimal(str(value))


def _clean_symbol(value: Any) -> str:
    return str(value or "").upper().replace("/", "").replace("-", "").strip()


def _parse_ms_timestamp(value: Any) -> datetime:
    return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)


def _parse_ibkr_datetime(value: str | None) -> datetime:
    raw = (value or "").strip()
    for fmt in ("%Y%m%d;%H:%M:%S", "%Y%m%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y%m%d"):
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(raw)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError(f"Unsupported IBKR trade time: {raw}") from exc


def _json_safe(payload: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(payload, default=str))


def _settings_for_user(db: Session, user: User) -> UserSettings:
    settings = db.query(UserSettings).filter(UserSettings.user_id == user.id).first()
    if not settings:
        settings = UserSettings(user_id=user.id)
        db.add(settings)
        db.flush()
    return settings


async def test_ibkr_flex_connection(db: Session, user: User) -> dict[str, Any]:
    settings = _settings_for_user(db, user)
    missing = []
    if not settings.ibkr_flex_query_id:
        missing.append("Flex Query ID")
    if not settings.ibkr_flex_token:
        missing.append("Flex Token")
    if missing:
        return {"ok": False, "provider": "IBKR", "message": f"缺少 {', '.join(missing)}"}

    try:
        reference_code = await _request_ibkr_flex_reference(settings.ibkr_flex_token, settings.ibkr_flex_query_id)
    except Exception as exc:
        return {"ok": False, "provider": "IBKR", "message": str(exc)}

    return {
        "ok": True,
        "provider": "IBKR",
        "message": "Flex Web Service 已返回 reference code",
        "reference_code": reference_code,
    }


async def test_binance_connection(db: Session, user: User) -> dict[str, Any]:
    settings = _settings_for_user(db, user)
    symbols = settings.binance_symbols or []
    missing = []
    if not settings.binance_api_key:
        missing.append("API Key")
    if not settings.binance_api_secret:
        missing.append("API Secret")
    if not symbols:
        missing.append("同步交易对")
    if missing:
        return {"ok": False, "provider": "Binance", "message": f"缺少 {', '.join(missing)}"}

    try:
        await _fetch_binance_account_trades(
            api_key=settings.binance_api_key,
            api_secret=settings.binance_api_secret,
            market_type=settings.binance_market_type or "SPOT",
            symbol=symbols[0],
            start_time=None,
            end_time=None,
            limit=1,
        )
    except Exception as exc:
        return {"ok": False, "provider": "Binance", "message": str(exc)}

    return {
        "ok": True,
        "provider": "Binance",
        "message": f"已成功访问 {symbols[0]} 的账户成交接口",
    }


async def sync_ibkr_flex_executions(
    db: Session,
    user: User,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> BrokerSyncRun:
    settings = _settings_for_user(db, user)
    if not settings.ibkr_flex_query_id or not settings.ibkr_flex_token:
        raise ValueError("IBKR Flex Query ID / Token 未配置")

    requested_start = start_date or settings.ibkr_flex_start_date
    run = _create_sync_run(
        db,
        user=user,
        provider="IBKR",
        market_type="FLEX",
        requested_start_date=requested_start,
        requested_end_date=end_date,
        metadata={"query_id": settings.ibkr_flex_query_id},
    )
    db.commit()

    try:
        reference_code = await _request_ibkr_flex_reference(settings.ibkr_flex_token, settings.ibkr_flex_query_id)
        statement_xml = await _request_ibkr_flex_statement(settings.ibkr_flex_token, reference_code)
        executions = _parse_ibkr_flex_executions(statement_xml, user_id=user.id)
        executions = _filter_by_date(executions, start_date=requested_start, end_date=end_date)
        _persist_executions(db, user=user, run=run, executions=executions)
        run.status = "SUCCEEDED"
        run.finished_at = _utc_now()
        run.metadata_json = {**(run.metadata_json or {}), "reference_code": reference_code}
        db.commit()
        db.refresh(run)
        return run
    except Exception as exc:
        db.rollback()
        run = db.query(BrokerSyncRun).filter(BrokerSyncRun.id == run.id).one()
        run.status = "FAILED"
        run.error_message = str(exc)
        run.finished_at = _utc_now()
        db.commit()
        db.refresh(run)
        raise


async def sync_binance_executions(
    db: Session,
    user: User,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> BrokerSyncRun:
    settings = _settings_for_user(db, user)
    symbols = settings.binance_symbols or []
    if not settings.binance_api_key or not settings.binance_api_secret:
        raise ValueError("Binance API Key / Secret 未配置")
    if not symbols:
        raise ValueError("Binance 同步交易对未配置")

    market_type = settings.binance_market_type or "SPOT"
    run = _create_sync_run(
        db,
        user=user,
        provider="BINANCE",
        market_type=market_type,
        requested_start_date=start_date,
        requested_end_date=end_date,
        metadata={"symbols": symbols},
    )
    db.commit()

    try:
        executions: list[NormalizedBrokerExecution] = []
        for symbol in symbols:
            raw_trades = await _fetch_binance_account_trades(
                api_key=settings.binance_api_key,
                api_secret=settings.binance_api_secret,
                market_type=market_type,
                symbol=symbol,
                start_time=_as_datetime(start_date),
                end_time=_as_datetime(end_date, end_of_day=True),
            )
            executions.extend(
                _normalize_binance_trades(
                    raw_trades,
                    user_id=user.id,
                    market_type=market_type,
                    symbol=symbol,
                )
            )
        _persist_executions(db, user=user, run=run, executions=executions)
        run.status = "SUCCEEDED"
        run.finished_at = _utc_now()
        db.commit()
        db.refresh(run)
        return run
    except Exception:
        db.rollback()
        run = db.query(BrokerSyncRun).filter(BrokerSyncRun.id == run.id).one()
        run.status = "FAILED"
        run.error_message = "Binance 成交同步失败"
        run.finished_at = _utc_now()
        db.commit()
        db.refresh(run)
        raise


def list_sync_runs(db: Session, user: User, *, limit: int = 20) -> list[BrokerSyncRun]:
    return (
        db.query(BrokerSyncRun)
        .filter(BrokerSyncRun.user_id == user.id)
        .order_by(BrokerSyncRun.created_at.desc(), BrokerSyncRun.id.desc())
        .limit(limit)
        .all()
    )


def list_executions(db: Session, user: User, *, limit: int = 100) -> list[BrokerExecution]:
    return (
        db.query(BrokerExecution)
        .filter(BrokerExecution.user_id == user.id)
        .order_by(BrokerExecution.trade_time.desc(), BrokerExecution.id.desc())
        .limit(limit)
        .all()
    )


def _create_sync_run(
    db: Session,
    *,
    user: User,
    provider: str,
    market_type: str | None,
    requested_start_date: date | None,
    requested_end_date: date | None,
    metadata: dict[str, Any] | None = None,
) -> BrokerSyncRun:
    now = _utc_now()
    run = BrokerSyncRun(
        user_id=user.id,
        provider=provider,
        market_type=market_type,
        status="RUNNING",
        requested_start_date=requested_start_date,
        requested_end_date=requested_end_date,
        started_at=now,
        metadata_json=metadata or {},
    )
    db.add(run)
    db.flush()
    return run


def _filter_by_date(
    executions: list[NormalizedBrokerExecution],
    *,
    start_date: date | None,
    end_date: date | None,
) -> list[NormalizedBrokerExecution]:
    start_dt = _as_datetime(start_date)
    end_dt = _as_datetime(end_date, end_of_day=True)
    result = []
    for execution in executions:
        trade_time = execution.trade_time
        if trade_time.tzinfo is None:
            trade_time = trade_time.replace(tzinfo=timezone.utc)
        if start_dt and trade_time < start_dt:
            continue
        if end_dt and trade_time > end_dt:
            continue
        result.append(execution)
    return result


def _persist_executions(
    db: Session,
    *,
    user: User,
    run: BrokerSyncRun,
    executions: list[NormalizedBrokerExecution],
) -> None:
    run.records_fetched = len(executions)
    inserted = 0
    skipped = 0

    for execution in executions:
        existing = db.query(BrokerExecution.id).filter(
            BrokerExecution.idempotency_key == execution.idempotency_key
        ).first()
        if existing:
            skipped += 1
            continue
        row = BrokerExecution(
            user_id=user.id,
            sync_run_id=run.id,
            provider=execution.provider,
            market_type=execution.market_type,
            account_ref=execution.account_ref,
            symbol=execution.symbol,
            side=execution.side,
            quantity=execution.quantity,
            price=execution.price,
            trade_time=execution.trade_time,
            currency=execution.currency,
            commission=execution.commission,
            commission_currency=execution.commission_currency,
            external_trade_id=execution.external_trade_id,
            external_order_id=execution.external_order_id,
            idempotency_key=execution.idempotency_key,
            raw_payload=_json_safe(execution.raw_payload),
        )
        db.add(row)
        db.flush()
        inserted += 1

    run.records_inserted = inserted
    run.records_skipped = skipped
    db.add(run)
    db.flush()


async def _request_ibkr_flex_reference(token: str, query_id: str) -> str:
    params = {"t": token, "q": query_id, "v": "3"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(IBKR_FLEX_BASE_URL, params=params)
        response.raise_for_status()
    root = ET.fromstring(response.text)
    if root.attrib.get("status") == "Fail":
        message = root.findtext(".//ErrorMessage") or "IBKR Flex SendRequest failed"
        raise RuntimeError(message)
    reference_code = root.findtext(".//ReferenceCode")
    if not reference_code:
        raise RuntimeError("IBKR Flex did not return a reference code")
    return reference_code


async def _request_ibkr_flex_statement(token: str, reference_code: str) -> str:
    params = {"t": token, "q": reference_code, "v": "3"}
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(IBKR_FLEX_STATEMENT_URL, params=params)
        response.raise_for_status()
    root = ET.fromstring(response.text)
    if root.tag == "FlexStatementResponse" and root.attrib.get("status") == "Fail":
        message = root.findtext(".//ErrorMessage") or "IBKR Flex GetStatement failed"
        raise RuntimeError(message)
    return response.text


def _parse_ibkr_flex_executions(xml_text: str, *, user_id: int) -> list[NormalizedBrokerExecution]:
    root = ET.fromstring(xml_text)
    executions = []
    trade_nodes = root.findall(".//Trade")
    for index, trade in enumerate(trade_nodes):
        attrs = dict(trade.attrib)
        symbol = _clean_symbol(attrs.get("symbol") or attrs.get("underlyingSymbol") or attrs.get("description"))
        if not symbol:
            continue
        side_value = str(attrs.get("buySell") or attrs.get("side") or attrs.get("transactionType") or "").upper()
        quantity = abs(_to_decimal(attrs.get("quantity")))
        price = _to_decimal(attrs.get("tradePrice") or attrs.get("price"))
        trade_time = _parse_ibkr_datetime(attrs.get("dateTime") or attrs.get("tradeDate") or attrs.get("reportDate"))
        exec_id = str(attrs.get("ibExecID") or attrs.get("execID") or attrs.get("tradeID") or f"{symbol}:{trade_time.isoformat()}:{index}")
        side = "BUY" if side_value.startswith("B") else "SELL"
        account_ref = attrs.get("accountId") or attrs.get("account") or attrs.get("acctId")
        currency = attrs.get("currency") or attrs.get("tradeCurrency")
        commission = _to_decimal(attrs.get("ibCommission") or attrs.get("commission"), default="0")
        commission_currency = attrs.get("ibCommissionCurrency") or attrs.get("commissionCurrency") or currency
        executions.append(
            NormalizedBrokerExecution(
                provider="IBKR",
                market_type="FLEX",
                account_ref=account_ref,
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                trade_time=trade_time,
                currency=currency,
                commission=commission,
                commission_currency=commission_currency,
                external_trade_id=exec_id,
                external_order_id=attrs.get("orderID") or attrs.get("orderId"),
                idempotency_key=f"IBKR:{user_id}:{account_ref or 'UNKNOWN'}:{exec_id}",
                raw_payload=attrs,
            )
        )
    return executions


async def _fetch_binance_account_trades(
    *,
    api_key: str,
    api_secret: str,
    market_type: str,
    symbol: str,
    start_time: datetime | None,
    end_time: datetime | None,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    market = market_type.upper()
    base_url = BINANCE_USD_M_FUTURES_BASE_URL if market == "USD_M_FUTURES" else BINANCE_SPOT_BASE_URL
    path = "/fapi/v1/userTrades" if market == "USD_M_FUTURES" else "/api/v3/myTrades"
    params: dict[str, Any] = {
        "symbol": _clean_symbol(symbol),
        "timestamp": int(_utc_now().timestamp() * 1000),
        "limit": limit,
    }
    if start_time:
        params["startTime"] = int(start_time.timestamp() * 1000)
    if end_time:
        params["endTime"] = int(end_time.timestamp() * 1000)
    query = urlencode(params)
    signature = hmac.new(api_secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()
    url = f"{base_url}{path}?{query}&signature={signature}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers={"X-MBX-APIKEY": api_key})
        response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise RuntimeError("Binance account trade response is not a list")
    return payload


def _normalize_binance_trades(
    trades: list[dict[str, Any]],
    *,
    user_id: int,
    market_type: str,
    symbol: str,
) -> list[NormalizedBrokerExecution]:
    normalized = []
    clean_symbol = _clean_symbol(symbol)
    market = market_type.upper()
    for trade in trades:
        trade_id = str(trade.get("id"))
        order_id = str(trade.get("orderId")) if trade.get("orderId") is not None else None
        side = str(trade.get("side") or ("BUY" if trade.get("isBuyer") else "SELL")).upper()
        quantity = _to_decimal(trade.get("qty") or trade.get("baseQty"))
        price = _to_decimal(trade.get("price"))
        trade_time = _parse_ms_timestamp(trade.get("time"))
        commission = _to_decimal(trade.get("commission"), default="0")
        commission_currency = trade.get("commissionAsset")
        normalized.append(
            NormalizedBrokerExecution(
                provider="BINANCE",
                market_type=market,
                account_ref=None,
                symbol=clean_symbol,
                side=side,
                quantity=quantity,
                price=price,
                trade_time=trade_time,
                currency=clean_symbol[-4:] if clean_symbol.endswith("USDT") else None,
                commission=commission,
                commission_currency=commission_currency,
                external_trade_id=trade_id,
                external_order_id=order_id,
                idempotency_key=f"BINANCE:{user_id}:{market}:{clean_symbol}:{trade_id}",
                raw_payload=trade,
            )
        )
    return normalized
