"""Journal-safe realized dashboard routes.

The Beta dashboard is derived only from journal facts. Market marks, FX,
portfolio risk, and NAV-style claims belong to disabled optional capabilities.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from database import get_db
from models import (
    AccountingHealth,
    BatchType,
    Position,
    PositionEvent,
    PositionEventType,
    PositionStatus,
    Strategy,
    TradeBatch,
    TradingAccount,
    TradingPosition,
    User,
)
from schemas import DashboardAccountBalance, DashboardStats
from services.account_ledger_service import calculate_account_cash_balance_read_model
from services.auth_service import get_current_user
from services.truth_legacy_projection_service import (
    exclude_void_truth_legacy_positions,
    resolve_user_truth_positions_for_legacy,
)


router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


def _sankey_asset_type_label(value: str) -> str:
    labels = {
        "STOCK": "股票",
        "EQUITY": "股票",
        "BOND": "债券",
        "FUND": "基金",
        "COMMODITY": "大宗商品",
        "FX": "外汇",
        "DERIVATIVE": "衍生品",
        "CRYPTO": "加密资产",
        "CASH": "现金",
    }
    return labels.get(value, "其他资产")


def _active_truth_exit_events(
    db: Session,
    *,
    user_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[PositionEvent]:
    reversed_event_ids = {
        row[0]
        for row in db.query(PositionEvent.reverses_event_id).join(
            TradingPosition,
            PositionEvent.position_id == TradingPosition.id,
        ).join(
            TradingAccount,
            PositionEvent.account_id == TradingAccount.id,
        ).outerjoin(
            Strategy,
            TradingPosition.strategy_id == Strategy.id,
        ).filter(
            PositionEvent.user_id == user_id,
            TradingPosition.user_id == user_id,
            TradingPosition.account_id == PositionEvent.account_id,
            TradingAccount.user_id == user_id,
            or_(
                TradingPosition.strategy_id.is_(None),
                Strategy.user_id == user_id,
            ),
            PositionEvent.event_type == PositionEventType.REVERSAL,
            PositionEvent.reverses_event_id.isnot(None),
        ).all()
    }
    query = db.query(PositionEvent).join(
        TradingPosition,
        PositionEvent.position_id == TradingPosition.id,
    ).join(
        TradingAccount,
        PositionEvent.account_id == TradingAccount.id,
    ).outerjoin(
        Strategy,
        TradingPosition.strategy_id == Strategy.id,
    ).filter(
        PositionEvent.user_id == user_id,
        TradingPosition.user_id == user_id,
        TradingPosition.account_id == PositionEvent.account_id,
        TradingAccount.user_id == user_id,
        or_(
            TradingPosition.strategy_id.is_(None),
            Strategy.user_id == user_id,
        ),
        PositionEvent.event_type.in_({PositionEventType.REDUCE, PositionEventType.CLOSE}),
    )
    if reversed_event_ids:
        query = query.filter(PositionEvent.id.notin_(reversed_event_ids))

    events = query.all()
    return [
        event
        for event in events
        if (start_date is None or event.event_time.date() >= start_date)
        and (end_date is None or event.event_time.date() <= end_date)
    ]


def _legacy_exit_batches(
    db: Session,
    *,
    user_id: int,
    truth_legacy_ids: set[int],
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[TradeBatch]:
    query = db.query(TradeBatch).join(Position).join(
        TradingAccount,
        Position.account_id == TradingAccount.id,
    ).outerjoin(
        Strategy,
        Position.strategy_id == Strategy.id,
    ).filter(
        Position.user_id == user_id,
        TradingAccount.user_id == user_id,
        or_(Position.strategy_id.is_(None), Strategy.user_id == user_id),
        TradeBatch.type == BatchType.EXIT,
    )
    if truth_legacy_ids:
        query = query.filter(Position.id.notin_(truth_legacy_ids))
    batches = query.all()
    return [
        batch
        for batch in batches
        if batch.time is not None
        and (start_date is None or batch.time.date() >= start_date)
        and (end_date is None or batch.time.date() <= end_date)
    ]


def _account_balances(
    db: Session,
    *,
    user_id: int,
) -> tuple[float, list[DashboardAccountBalance], list[str]]:
    accounts = db.query(TradingAccount).filter(
        TradingAccount.user_id == user_id,
        TradingAccount.is_active == True,
    ).all()
    values = []
    warnings = []
    for account in accounts:
        if (account.currency or "").strip().upper() != "USD":
            continue
        health = account.accounting_health or AccountingHealth.HEALTHY.value
        health_value = health.value if hasattr(health, "value") else str(health)
        trusted = health_value == AccountingHealth.HEALTHY.value
        value = float(calculate_account_cash_balance_read_model(db, account=account))
        values.append((account, value, health_value, trusted))
        if not trusted:
            warnings.append(
                f"ACCOUNTING_RECONCILIATION_REQUIRED:{account.public_id}"
            )
    total = sum(value for _, value, _, trusted in values if trusted)
    balances = [
        DashboardAccountBalance(
            name=account.name,
            broker=account.broker,
            journal_balance=value,
            accounting_health=health,
            journal_balance_trusted=trusted,
        )
        for account, value, health, trusted in values
    ]
    return total, balances, warnings


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    truth_by_legacy_id = resolve_user_truth_positions_for_legacy(
        db,
        user_id=current_user.id,
    )
    truth_events = _active_truth_exit_events(
        db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
    )
    legacy_batches = _legacy_exit_batches(
        db,
        user_id=current_user.id,
        truth_legacy_ids=set(truth_by_legacy_id),
        start_date=start_date,
        end_date=end_date,
    )
    exit_pnls = [float(event.realized_pnl_net or 0) for event in truth_events]
    exit_pnls.extend(float(batch.pnl or 0) for batch in legacy_batches)

    position_query = db.query(Position).join(
        TradingAccount,
        Position.account_id == TradingAccount.id,
    ).outerjoin(
        Strategy,
        Position.strategy_id == Strategy.id,
    ).filter(
        Position.user_id == current_user.id,
        TradingAccount.user_id == current_user.id,
        or_(
            Position.strategy_id.is_(None),
            Strategy.user_id == current_user.id,
        ),
    )
    if start_date:
        position_query = position_query.filter(Position.opened_at >= start_date)
    if end_date:
        position_query = position_query.filter(Position.opened_at <= end_date)
    counted_positions = exclude_void_truth_legacy_positions(
        db,
        user_id=current_user.id,
        positions=position_query.all(),
    )
    total_trades = len(counted_positions)
    closed_trades = sum(
        1 for position in counted_positions
        if position.status == PositionStatus.CLOSED
    )
    open_positions = sum(
        1 for position in counted_positions
        if position.status == PositionStatus.OPEN
    )

    wins = [pnl for pnl in exit_pnls if pnl > 0]
    losses = [abs(pnl) for pnl in exit_pnls if pnl < 0]
    total_journal_balance, account_balances, accounting_warnings = _account_balances(
        db,
        user_id=current_user.id,
    )

    return DashboardStats(
        journal_balance=total_journal_balance,
        realized_pnl=sum(exit_pnls),
        win_rate=(len(wins) / len(exit_pnls) * 100) if exit_pnls else 0.0,
        avg_pnl_ratio=(sum(wins) / sum(losses)) if losses else 0.0,
        total_trades=total_trades,
        open_positions=open_positions,
        closed_trades=closed_trades,
        account_balances=account_balances[:5],
        accounting_degraded=bool(accounting_warnings),
        accounting_warnings=accounting_warnings,
    )


@router.get("/pnl-history")
def get_pnl_history(
    days: int = Query(30, ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if days > 1000 and current_user.created_at:
        start_date = current_user.created_at.date()
    else:
        start_date = date.today() - timedelta(days=days)
    end_date = date.today()

    truth_by_legacy_id = resolve_user_truth_positions_for_legacy(
        db,
        user_id=current_user.id,
    )
    truth_events = _active_truth_exit_events(
        db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
    )
    legacy_batches = _legacy_exit_batches(
        db,
        user_id=current_user.id,
        truth_legacy_ids=set(truth_by_legacy_id),
        start_date=start_date,
        end_date=end_date,
    )

    realized_by_day: dict[date, float] = defaultdict(float)
    for event in truth_events:
        realized_by_day[event.event_time.date()] += float(event.realized_pnl_net or 0)
    for batch in legacy_batches:
        realized_by_day[batch.time.date()] += float(batch.pnl or 0)

    principal = sum(
        float(account.initial_balance or 0)
        for account in db.query(TradingAccount).filter(
            TradingAccount.user_id == current_user.id,
            TradingAccount.is_active == True,
        ).all()
        if (account.currency or "").strip().upper() == "USD"
    )
    result = []
    cumulative_realized = 0.0
    current_date = start_date
    while current_date <= end_date:
        cumulative_realized += realized_by_day[current_date]
        result.append(
            {
                "date": current_date.isoformat(),
                "pnl": round(cumulative_realized, 2),
                "pnl_percent": round(cumulative_realized / principal * 100, 2)
                if principal
                else 0.0,
            }
        )
        current_date += timedelta(days=1)
    return result
