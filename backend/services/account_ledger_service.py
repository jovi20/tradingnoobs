"""Append-only journal ledger and replay services."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import uuid

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from models import (
    AccountingHealth,
    AccountLedgerEntry,
    AccountLedgerEntryType,
    LedgerPostingKind,
    PositionEvent,
    PositionEventType,
    Transaction,
    TransactionType,
    TradingAccount,
    TradingPosition,
)
from services.trading_accounting_service import quantize_posting


ACCOUNT_LEDGER_NAMESPACE = uuid.UUID("59f7cb40-f4a6-46c2-9943-6470a42c24c8")


class LedgerPostingConflictError(ValueError):
    code = "POSTING_FACT_CONFLICT"
    http_status = 409


class AccountingReconciliationRequiredError(ValueError):
    code = "ACCOUNTING_RECONCILIATION_REQUIRED"
    http_status = 409


def _value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _deterministic_ledger_public_id(
    source_fact_public_id: str,
    posting_kind: str,
) -> str:
    return str(
        uuid.uuid5(
            ACCOUNT_LEDGER_NAMESPACE,
            f"{source_fact_public_id}:{posting_kind}",
        )
    )


def _transaction_posting_kind(transaction_type: TransactionType) -> LedgerPostingKind:
    mapping = {
        TransactionType.DEPOSIT: LedgerPostingKind.DEPOSIT,
        TransactionType.WITHDRAWAL: LedgerPostingKind.WITHDRAWAL,
        TransactionType.INTEREST: LedgerPostingKind.INTEREST,
        TransactionType.FEE: LedgerPostingKind.ACCOUNT_FEE,
        TransactionType.TRANSFER_IN: LedgerPostingKind.DEPOSIT,
        TransactionType.TRANSFER_OUT: LedgerPostingKind.WITHDRAWAL,
    }
    return mapping[transaction_type]


def _legacy_entry_type(posting_kind: LedgerPostingKind) -> AccountLedgerEntryType:
    mapping = {
        LedgerPostingKind.OPENING_BALANCE: AccountLedgerEntryType.CASH_ADJUSTMENT,
        LedgerPostingKind.DEPOSIT: AccountLedgerEntryType.DEPOSIT,
        LedgerPostingKind.WITHDRAWAL: AccountLedgerEntryType.WITHDRAWAL,
        LedgerPostingKind.INTEREST: AccountLedgerEntryType.CASH_ADJUSTMENT,
        LedgerPostingKind.ACCOUNT_FEE: AccountLedgerEntryType.FEE,
        LedgerPostingKind.CASH_DIVIDEND_RECEIVED: AccountLedgerEntryType.DIVIDEND,
        LedgerPostingKind.CASH_DIVIDEND_PAID_IN_LIEU: AccountLedgerEntryType.DIVIDEND,
        LedgerPostingKind.REALIZED_GROSS: AccountLedgerEntryType.REALIZED_PNL,
        LedgerPostingKind.TRADE_FEE: AccountLedgerEntryType.FEE,
        LedgerPostingKind.COMPENSATING_REVERSAL: AccountLedgerEntryType.CASH_ADJUSTMENT,
        LedgerPostingKind.LEGACY_UNRESOLVED: AccountLedgerEntryType.CASH_ADJUSTMENT,
    }
    return mapping[posting_kind]


def require_accounting_healthy(account: TradingAccount) -> None:
    health = account.accounting_health or AccountingHealth.HEALTHY.value
    if _value(health) != AccountingHealth.HEALTHY.value:
        raise AccountingReconciliationRequiredError(
            f"Account {account.public_id} requires accounting reconciliation"
        )


def _require_event_owner_graph(db: Session, event: PositionEvent) -> None:
    account_matches = db.query(TradingAccount.id).filter(
        TradingAccount.id == event.account_id,
        TradingAccount.user_id == event.user_id,
    ).first()
    position_matches = db.query(TradingPosition.id).filter(
        TradingPosition.id == event.position_id,
        TradingPosition.user_id == event.user_id,
        TradingPosition.account_id == event.account_id,
    ).first()
    if account_matches is None or position_matches is None:
        raise ValueError("Position event owner graph is inconsistent")


def _ledger_entry_owner_graph_is_consistent(
    db: Session,
    *,
    entry: AccountLedgerEntry,
    account: TradingAccount,
) -> bool:
    if entry.user_id != account.user_id or entry.account_id != account.id:
        return False
    if entry.position_id is not None:
        position = db.query(TradingPosition).filter(
            TradingPosition.id == entry.position_id,
            TradingPosition.user_id == account.user_id,
            TradingPosition.account_id == account.id,
        ).first()
        if position is None:
            return False
    if entry.position_event_id is not None:
        event = db.query(PositionEvent).filter(
            PositionEvent.id == entry.position_event_id,
            PositionEvent.user_id == account.user_id,
            PositionEvent.account_id == account.id,
        ).first()
        if event is None or (
            entry.position_id is not None
            and event.position_id != entry.position_id
        ):
            return False
    if entry.transaction_id is not None:
        transaction = db.query(Transaction).filter(
            Transaction.id == entry.transaction_id,
            Transaction.account_id == account.id,
        ).first()
        if transaction is None:
            return False
    return True


def _posting_matches(
    entry: AccountLedgerEntry,
    *,
    user_id: int,
    account_id: int,
    position_id: int | None,
    position_event_id: int | None,
    transaction_id: int | None,
    reverses_ledger_entry_id: int | None,
    occurred_at: datetime,
    currency: str,
    amount: Decimal,
    amount_account_ccy: Decimal,
    fx_rate_to_account_ccy: Decimal,
) -> bool:
    return (
        entry.user_id == user_id
        and entry.account_id == account_id
        and entry.position_id == position_id
        and entry.position_event_id == position_event_id
        and entry.transaction_id == transaction_id
        and entry.reverses_ledger_entry_id == reverses_ledger_entry_id
        and _normalized_timestamp(entry.occurred_at)
        == _normalized_timestamp(occurred_at)
        and entry.currency == currency
        and quantize_posting(entry.amount) == amount
        and quantize_posting(
            entry.amount_account_ccy
            if entry.amount_account_ccy is not None
            else entry.amount
        ) == amount_account_ccy
        and quantize_posting(entry.fx_rate_to_account_ccy or 1)
        == fx_rate_to_account_ccy
    )


def _normalized_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _find_posting(
    db: Session,
    *,
    source_fact_public_id: str,
    posting_kind: LedgerPostingKind,
) -> AccountLedgerEntry | None:
    return db.query(AccountLedgerEntry).filter(
        AccountLedgerEntry.source_fact_public_id == source_fact_public_id,
        AccountLedgerEntry.posting_kind == posting_kind.value,
    ).first()


def create_or_replay_posting(
    db: Session,
    *,
    user_id: int,
    account_id: int,
    source_fact_public_id: str,
    posting_kind: LedgerPostingKind,
    occurred_at: datetime,
    currency: str,
    amount,
    fx_rate_to_account_ccy=Decimal("1"),
    position_id: int | None = None,
    position_event_id: int | None = None,
    transaction_id: int | None = None,
    reverses_ledger_entry_id: int | None = None,
    source: str | None = None,
    source_run_id: str | None = None,
    description: str | None = None,
) -> AccountLedgerEntry:
    kind = LedgerPostingKind(_value(posting_kind))
    normalized_amount = quantize_posting(amount)
    normalized_fx = quantize_posting(fx_rate_to_account_ccy)
    normalized_account_amount = quantize_posting(
        normalized_amount * normalized_fx
    )
    normalized_currency = (currency or "USD").strip().upper()

    existing = _find_posting(
        db,
        source_fact_public_id=source_fact_public_id,
        posting_kind=kind,
    )
    if existing is not None:
        if not _posting_matches(
            existing,
            user_id=user_id,
            account_id=account_id,
            position_id=position_id,
            position_event_id=position_event_id,
            transaction_id=transaction_id,
            reverses_ledger_entry_id=reverses_ledger_entry_id,
            occurred_at=occurred_at,
            currency=normalized_currency,
            amount=normalized_amount,
            amount_account_ccy=normalized_account_amount,
            fx_rate_to_account_ccy=normalized_fx,
        ):
            raise LedgerPostingConflictError(
                f"Posting {source_fact_public_id}/{kind.value} conflicts "
                "with the immutable ledger"
            )
        return existing

    entry = AccountLedgerEntry(
        public_id=_deterministic_ledger_public_id(
            source_fact_public_id,
            kind.value,
        ),
        user_id=user_id,
        account_id=account_id,
        position_id=position_id,
        position_event_id=position_event_id,
        transaction_id=transaction_id,
        reverses_ledger_entry_id=reverses_ledger_entry_id,
        entry_type=_legacy_entry_type(kind),
        source_fact_public_id=source_fact_public_id,
        posting_kind=kind.value,
        occurred_at=occurred_at,
        currency=normalized_currency,
        amount=normalized_amount,
        amount_account_ccy=normalized_account_amount,
        fx_rate_to_account_ccy=normalized_fx,
        source=source,
        source_run_id=source_run_id,
        description=description,
    )
    try:
        with db.begin_nested():
            db.add(entry)
            db.flush()
        return entry
    except IntegrityError:
        existing = _find_posting(
            db,
            source_fact_public_id=source_fact_public_id,
            posting_kind=kind,
        )
        if existing is None or not _posting_matches(
            existing,
            user_id=user_id,
            account_id=account_id,
            position_id=position_id,
            position_event_id=position_event_id,
            transaction_id=transaction_id,
            reverses_ledger_entry_id=reverses_ledger_entry_id,
            occurred_at=occurred_at,
            currency=normalized_currency,
            amount=normalized_amount,
            amount_account_ccy=normalized_account_amount,
            fx_rate_to_account_ccy=normalized_fx,
        ):
            raise LedgerPostingConflictError(
                f"Posting {source_fact_public_id}/{kind.value} lost a "
                "concurrent write race with different facts"
            )
        return existing


def sync_transaction_to_account_ledger(
    db: Session,
    *,
    transaction: Transaction,
    account: TradingAccount,
) -> AccountLedgerEntry:
    if transaction.account_id != account.id:
        raise ValueError("Transaction and account have different owners")
    require_accounting_healthy(account)
    if transaction.id is None:
        db.flush()
    kind = _transaction_posting_kind(transaction.type)
    return create_or_replay_posting(
        db,
        user_id=account.user_id,
        account_id=account.id,
        source_fact_public_id=transaction.public_id,
        posting_kind=kind,
        occurred_at=transaction.date,
        currency=transaction.currency or account.currency or "USD",
        amount=transaction.amount,
        transaction_id=transaction.id,
        source="TRANSACTION",
        source_run_id=transaction.public_id,
        description=transaction.description,
    )


def sync_opening_balance_to_account_ledger(
    db: Session,
    *,
    account: TradingAccount,
) -> AccountLedgerEntry | None:
    opening_balance = quantize_posting(account.initial_balance or 0)
    if opening_balance == 0:
        return None
    if account.id is None:
        db.flush()
    return create_or_replay_posting(
        db,
        user_id=account.user_id,
        account_id=account.id,
        source_fact_public_id=account.public_id,
        posting_kind=LedgerPostingKind.OPENING_BALANCE,
        occurred_at=account.created_at or datetime.now(timezone.utc),
        currency=account.currency or "USD",
        amount=opening_balance,
        source="OPENING_BALANCE",
        source_run_id=account.public_id,
        description="Opening cash balance",
    )


def sync_cash_balance_adjustment_to_account_ledger(
    db: Session,
    *,
    account: TradingAccount,
    target_cash_balance,
    description: str | None = None,
) -> AccountLedgerEntry | None:
    require_accounting_healthy(account)
    target_balance = quantize_posting(target_cash_balance)
    adjustment_amount = quantize_posting(
        target_balance
        - calculate_account_cash_balance_read_model(db, account=account)
    )
    if adjustment_amount == 0:
        return None
    fact_id = str(uuid.uuid4())
    return create_or_replay_posting(
        db,
        user_id=account.user_id,
        account_id=account.id,
        source_fact_public_id=fact_id,
        posting_kind=LedgerPostingKind.LEGACY_UNRESOLVED,
        occurred_at=datetime.now(timezone.utc),
        currency=account.currency or "USD",
        amount=adjustment_amount,
        source="MANUAL_CASH_ADJUSTMENT",
        source_run_id=fact_id,
        description=description or "Manual cash balance adjustment",
    )


def sync_dividend_event_to_account_ledger(
    db: Session,
    *,
    event: PositionEvent,
) -> AccountLedgerEntry:
    _require_event_owner_graph(db, event)
    account = db.query(TradingAccount).filter(
        TradingAccount.id == event.account_id,
        TradingAccount.user_id == event.user_id,
    ).one()
    require_accounting_healthy(account)
    if event.id is None:
        db.flush()
    amount = quantize_posting(event.gross_amount or 0)
    kind = (
        LedgerPostingKind.CASH_DIVIDEND_RECEIVED
        if amount >= 0
        else LedgerPostingKind.CASH_DIVIDEND_PAID_IN_LIEU
    )
    return create_or_replay_posting(
        db,
        user_id=event.user_id,
        account_id=event.account_id,
        position_id=event.position_id,
        position_event_id=event.id,
        source_fact_public_id=event.public_id,
        posting_kind=kind,
        occurred_at=event.event_time,
        currency=event.currency or account.currency or "USD",
        amount=amount,
        fx_rate_to_account_ccy=event.fx_rate_to_account_ccy or 1,
        source="POSITION_EVENT",
        source_run_id=event.public_id,
        description=event.note or "Dividend",
    )


def sync_manual_adjustment_event_to_account_ledger(
    db: Session,
    *,
    event: PositionEvent,
) -> AccountLedgerEntry:
    _require_event_owner_graph(db, event)
    if event.id is None:
        db.flush()
    return create_or_replay_posting(
        db,
        user_id=event.user_id,
        account_id=event.account_id,
        position_id=event.position_id,
        position_event_id=event.id,
        source_fact_public_id=event.public_id,
        posting_kind=LedgerPostingKind.LEGACY_UNRESOLVED,
        occurred_at=event.event_time,
        currency=event.currency or "USD",
        amount=event.gross_amount or 0,
        fx_rate_to_account_ccy=event.fx_rate_to_account_ccy or 1,
        source="POSITION_EVENT",
        source_run_id=event.public_id,
        description=event.note or "Manual position adjustment",
    )


def sync_trade_event_postings(
    db: Session,
    *,
    event: PositionEvent,
    position: TradingPosition,
) -> list[AccountLedgerEntry]:
    if (
        event.user_id != position.user_id
        or event.position_id != position.id
        or event.account_id != position.account_id
    ):
        raise ValueError("Position event and position have different owners")
    _require_event_owner_graph(db, event)
    account = db.query(TradingAccount).filter(
        TradingAccount.id == event.account_id,
        TradingAccount.user_id == event.user_id,
    ).one()
    require_accounting_healthy(account)
    if event.id is None:
        db.flush()

    if event.event_type == PositionEventType.REVERSAL:
        if event.reverses_event_id is None:
            raise LedgerPostingConflictError(
                "A reversal event must reference its original event"
            )
        originals = db.query(AccountLedgerEntry).filter(
            AccountLedgerEntry.position_event_id == event.reverses_event_id,
        ).order_by(AccountLedgerEntry.id.asc()).all()
        return [
            create_or_replay_posting(
                db,
                user_id=event.user_id,
                account_id=event.account_id,
                position_id=position.id,
                position_event_id=event.id,
                source_fact_public_id=event.public_id,
                posting_kind=LedgerPostingKind(original.posting_kind),
                occurred_at=event.event_time,
                currency=original.currency,
                amount=-quantize_posting(original.amount),
                fx_rate_to_account_ccy=original.fx_rate_to_account_ccy or 1,
                reverses_ledger_entry_id=original.id,
                source="POSITION_EVENT_REVERSAL",
                source_run_id=event.public_id,
                description=f"Reversal of {original.public_id}",
            )
            for original in originals
        ]

    entries: list[AccountLedgerEntry] = []
    currency = event.currency or position.base_currency or account.currency or "USD"
    fx_rate = event.fx_rate_to_account_ccy or 1
    if event.event_type in {PositionEventType.REDUCE, PositionEventType.CLOSE}:
        entries.append(
            create_or_replay_posting(
                db,
                user_id=event.user_id,
                account_id=event.account_id,
                position_id=position.id,
                position_event_id=event.id,
                source_fact_public_id=event.public_id,
                posting_kind=LedgerPostingKind.REALIZED_GROSS,
                occurred_at=event.event_time,
                currency=currency,
                amount=event.realized_pnl_gross or 0,
                fx_rate_to_account_ccy=fx_rate,
                source="POSITION_EVENT",
                source_run_id=event.public_id,
                description=(
                    f"{position.instrument.contract_symbol} realized gross"
                    if position.instrument
                    else "Realized gross"
                ),
            )
        )
    fee = quantize_posting(event.fee_amount or 0)
    if fee:
        entries.append(
            create_or_replay_posting(
                db,
                user_id=event.user_id,
                account_id=event.account_id,
                position_id=position.id,
                position_event_id=event.id,
                source_fact_public_id=event.public_id,
                posting_kind=LedgerPostingKind.TRADE_FEE,
                occurred_at=event.event_time,
                currency=event.fee_currency or currency,
                amount=-abs(fee),
                fx_rate_to_account_ccy=fx_rate,
                source="POSITION_EVENT",
                source_run_id=event.public_id,
                description=(
                    f"{position.instrument.contract_symbol} trade fee"
                    if position.instrument
                    else "Trade fee"
                ),
            )
        )
    return entries


def sync_realized_pnl_event_to_account_ledger(
    db: Session,
    *,
    event: PositionEvent,
    position: TradingPosition,
) -> AccountLedgerEntry | None:
    entries = sync_trade_event_postings(db, event=event, position=position)
    return next(
        (
            entry
            for entry in entries
            if entry.posting_kind == LedgerPostingKind.REALIZED_GROSS.value
        ),
        entries[0] if entries else None,
    )


def delete_transaction_ledger_entries(
    db: Session,
    *,
    transaction: Transaction,
) -> None:
    raise LedgerPostingConflictError(
        "Posted transactions are immutable; create a compensating reversal"
    )


def calculate_account_cash_balance_read_model(
    db: Session,
    *,
    account: TradingAccount,
) -> Decimal:
    ledger_entries = db.query(AccountLedgerEntry).filter(
        AccountLedgerEntry.account_id == account.id,
        AccountLedgerEntry.user_id == account.user_id,
    ).all()
    valid_entries = [
        entry
        for entry in ledger_entries
        if _ledger_entry_owner_graph_is_consistent(
            db,
            entry=entry,
            account=account,
        )
    ]
    total = quantize_posting(
        sum(
            (
                Decimal(str(entry.amount_account_ccy))
                if entry.amount_account_ccy is not None
                else Decimal(str(entry.amount))
            )
            for entry in valid_entries
        )
    )
    return Decimal("0") if total == 0 else total
