from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from sqlalchemy.orm import Session

from models import DailySnapshot, TradingPosition, TradingPositionStatus


RiskAlertSeverity = Literal["INFO", "NOTICE", "WARNING", "CRITICAL"]
RiskAlertKind = Literal["DAILY_LOSS_LIMIT", "CONCENTRATION", "DRAWDOWN", "DATA_STALE"]


@dataclass(frozen=True)
class RiskThresholds:
    daily_loss_warning_percent: Decimal = Decimal("-3")
    daily_loss_critical_percent: Decimal = Decimal("-5")
    concentration_warning_ratio: Decimal = Decimal("0.35")
    concentration_critical_ratio: Decimal = Decimal("0.50")
    drawdown_warning_ratio: Decimal = Decimal("0.12")
    drawdown_critical_ratio: Decimal = Decimal("0.25")


def classify_daily_loss_percent(
    daily_loss_percent: Decimal | None,
    thresholds: RiskThresholds | None = None,
) -> RiskAlertSeverity | None:
    if daily_loss_percent is None:
        return None

    active_thresholds = thresholds or RiskThresholds()
    if daily_loss_percent <= active_thresholds.daily_loss_critical_percent:
        return "CRITICAL"
    if daily_loss_percent <= active_thresholds.daily_loss_warning_percent:
        return "WARNING"
    return None


def classify_concentration_ratio(
    concentration_ratio: Decimal,
    thresholds: RiskThresholds | None = None,
) -> RiskAlertSeverity | None:
    active_thresholds = thresholds or RiskThresholds()
    if concentration_ratio >= active_thresholds.concentration_critical_ratio:
        return "CRITICAL"
    if concentration_ratio >= active_thresholds.concentration_warning_ratio:
        return "WARNING"
    return None


def classify_drawdown_ratio(
    drawdown_ratio: Decimal | None,
    thresholds: RiskThresholds | None = None,
) -> RiskAlertSeverity | None:
    if drawdown_ratio is None:
        return None

    active_thresholds = thresholds or RiskThresholds()
    if drawdown_ratio >= active_thresholds.drawdown_critical_ratio:
        return "CRITICAL"
    if drawdown_ratio >= active_thresholds.drawdown_warning_ratio:
        return "WARNING"
    return None


def build_portfolio_risk_summary(
    db: Session,
    user_id: int,
    *,
    as_of: datetime | None = None,
    thresholds: RiskThresholds | None = None,
) -> dict:
    active_thresholds = thresholds or RiskThresholds()
    effective_as_of = as_of or datetime.now(timezone.utc)
    if effective_as_of.tzinfo is None:
        effective_as_of = effective_as_of.replace(tzinfo=timezone.utc)

    snapshots = (
        db.query(DailySnapshot)
        .filter(DailySnapshot.user_id == user_id, DailySnapshot.date <= effective_as_of.date())
        .order_by(DailySnapshot.date.desc(), DailySnapshot.id.desc())
        .limit(2)
        .all()
    )
    latest_snapshot = snapshots[0] if snapshots else None
    previous_snapshot = snapshots[1] if len(snapshots) > 1 else None

    gross_exposure, symbol_exposures = _calculate_open_position_exposure(db, user_id)
    latest_equity = Decimal(latest_snapshot.total_equity) if latest_snapshot else Decimal("0")
    daily_pnl, daily_pnl_percent = _calculate_daily_pnl(latest_snapshot, previous_snapshot)
    max_drawdown = _calculate_max_drawdown(db, user_id, latest_equity)

    alerts: list[dict] = []
    daily_severity = classify_daily_loss_percent(daily_pnl_percent, active_thresholds)
    if daily_severity:
        alerts.append(
            _build_daily_loss_alert(
                severity=daily_severity,
                daily_pnl_percent=daily_pnl_percent,
                snapshot_date=latest_snapshot.date,
                threshold_percent=(
                    active_thresholds.daily_loss_critical_percent
                    if daily_severity == "CRITICAL"
                    else active_thresholds.daily_loss_warning_percent
                ),
            )
        )

    if gross_exposure > 0:
        for symbol, exposure in sorted(symbol_exposures.items(), key=lambda item: item[1], reverse=True):
            concentration_ratio = exposure / gross_exposure
            concentration_severity = classify_concentration_ratio(concentration_ratio, active_thresholds)
            if not concentration_severity:
                continue
            alerts.append(
                _build_concentration_alert(
                    severity=concentration_severity,
                    symbol=symbol,
                    concentration_ratio=concentration_ratio,
                    exposure=exposure,
                )
            )
            break

    drawdown_severity = classify_drawdown_ratio(max_drawdown, active_thresholds)
    if drawdown_severity and max_drawdown is not None:
        alerts.append(_build_drawdown_alert(severity=drawdown_severity, max_drawdown=max_drawdown))

    return {
        "as_of": effective_as_of.isoformat().replace("+00:00", "Z"),
        "base_currency": "USD",
        "portfolio": {
            "gross_exposure": _to_float(gross_exposure),
            "net_liquidation_value": _to_float(latest_equity),
            "daily_pnl": _to_float(daily_pnl),
            "daily_pnl_percent": _to_float(daily_pnl_percent),
            "max_drawdown": _to_float(max_drawdown),
        },
        "alerts": alerts,
        "trust": {
            "freshness": "FRESH",
            "source": "DERIVED",
            "source_refs": ["TradingPosition", "AccountLedgerEntry", "DailySnapshot"],
        },
    }


def _calculate_open_position_exposure(db: Session, user_id: int) -> tuple[Decimal, dict[str, Decimal]]:
    positions = (
        db.query(TradingPosition)
        .filter(
            TradingPosition.user_id == user_id,
            TradingPosition.status == TradingPositionStatus.OPEN,
            TradingPosition.deleted_at.is_(None),
        )
        .all()
    )

    symbol_exposures: dict[str, Decimal] = {}
    gross_exposure = Decimal("0")
    for position in positions:
        open_quantity = Decimal(position.quantity_opened or 0) - Decimal(position.quantity_closed or 0)
        avg_open_price = Decimal(position.avg_open_price or 0)
        exposure = abs(open_quantity * avg_open_price)
        if exposure <= 0:
            continue
        symbol = position.instrument.contract_symbol if position.instrument else position.public_id
        symbol_exposures[symbol] = symbol_exposures.get(symbol, Decimal("0")) + exposure
        gross_exposure += exposure

    return gross_exposure, symbol_exposures


def _calculate_daily_pnl(
    latest_snapshot: DailySnapshot | None,
    previous_snapshot: DailySnapshot | None,
) -> tuple[Decimal | None, Decimal | None]:
    if not latest_snapshot or not previous_snapshot:
        return None, None

    previous_equity = Decimal(previous_snapshot.total_equity)
    latest_equity = Decimal(latest_snapshot.total_equity)
    daily_pnl = latest_equity - previous_equity
    if previous_equity == 0:
        return daily_pnl, None
    daily_pnl_percent = (daily_pnl / previous_equity) * Decimal("100")
    return daily_pnl, daily_pnl_percent


def _calculate_max_drawdown(db: Session, user_id: int, latest_equity: Decimal) -> Decimal | None:
    snapshots = (
        db.query(DailySnapshot)
        .filter(DailySnapshot.user_id == user_id)
        .order_by(DailySnapshot.date.asc(), DailySnapshot.id.asc())
        .all()
    )
    equity_curve = [Decimal(snapshot.total_equity) for snapshot in snapshots if snapshot.total_equity is not None]
    if latest_equity > 0 and (not equity_curve or equity_curve[-1] != latest_equity):
        equity_curve.append(latest_equity)
    if len(equity_curve) < 2:
        return None

    peak = equity_curve[0]
    max_drawdown = Decimal("0")
    for equity in equity_curve:
        if equity > peak:
            peak = equity
        if peak <= 0:
            continue
        drawdown = (peak - equity) / peak
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    return max_drawdown


def _build_daily_loss_alert(
    *,
    severity: RiskAlertSeverity,
    daily_pnl_percent: Decimal,
    snapshot_date,
    threshold_percent: Decimal,
) -> dict:
    percent_label = f"{daily_pnl_percent.quantize(Decimal('0.01'))}%"
    threshold_label = f"{threshold_percent.copy_abs().quantize(Decimal('0.01')).normalize()}%"
    return {
        "public_id": f"risk:daily_loss:{snapshot_date.isoformat()}",
        "kind": "DAILY_LOSS_LIMIT",
        "severity": severity,
        "summary": f"今日亏损已达到 {percent_label}",
        "reason": f"Daily equity change crossed the -{threshold_label} {'critical' if severity == 'CRITICAL' else 'warning'} threshold.",
        "recommended_action": {
            "kind": "OPEN_DASHBOARD",
            "label": "查看组合风险",
            "href": "/dashboard",
        },
        "source_refs": [f"daily_snapshot:{snapshot_date.isoformat()}", "risk:daily_loss"],
        "trust": _alert_trust(value_status="ESTIMATED"),
    }


def _build_concentration_alert(
    *,
    severity: RiskAlertSeverity,
    symbol: str,
    concentration_ratio: Decimal,
    exposure: Decimal,
) -> dict:
    concentration_percent = (concentration_ratio * Decimal("100")).quantize(Decimal("0.01"))
    return {
        "public_id": f"risk:concentration:{symbol}",
        "kind": "CONCENTRATION",
        "severity": severity,
        "summary": f"{symbol} 持仓集中度达到 {concentration_percent}%",
        "reason": f"{symbol} exposure is {_to_float(exposure)} and exceeds the portfolio concentration threshold.",
        "recommended_action": {
            "kind": "OPEN_DASHBOARD",
            "label": "查看组合结构",
            "href": "/dashboard",
        },
        "source_refs": [f"trading_position:{symbol}", "risk:concentration"],
        "trust": _alert_trust(value_status="ESTIMATED"),
    }


def _build_drawdown_alert(*, severity: RiskAlertSeverity, max_drawdown: Decimal) -> dict:
    drawdown_percent = (max_drawdown * Decimal("100")).quantize(Decimal("0.01"))
    return {
        "public_id": "risk:drawdown:portfolio",
        "kind": "DRAWDOWN",
        "severity": severity,
        "summary": f"最大回撤达到 {drawdown_percent}%",
        "reason": "Portfolio drawdown crossed the configured risk threshold.",
        "recommended_action": {
            "kind": "OPEN_DASHBOARD",
            "label": "查看回撤",
            "href": "/dashboard",
        },
        "source_refs": ["daily_snapshots", "risk:drawdown"],
        "trust": _alert_trust(value_status="ESTIMATED"),
    }


def _alert_trust(*, value_status: str) -> dict:
    return {
        "freshness": "FRESH",
        "source": "DERIVED",
        "value_status": value_status,
    }


def _to_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)
