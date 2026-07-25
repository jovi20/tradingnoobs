"""
Trading Noobs Backend - Account Ledger Service
"""
from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timezone
import uuid

from sqlalchemy.orm import Session

from models import (
    AccountLedgerEntry,
    AccountLedgerEntryType,
    PositionEvent,
    Transaction,
    TransactionType,
    TradingAccount,
    TradingPosition,
)


ACCOUNT_LEDGER_NAMESPACE = uuid.UUID("59f7cb40-f4a6-46c2-9943-6470a42c24c8")


def _deterministic_ledger_public_id(source: str) -> str:
    return str(uuid.uuid5(ACCOUNT_LEDGER_NAMESPACE, source))


def _transaction_entry_type(transaction_type: TransactionType) -> AccountLedgerEntryType:
    if transaction_type == TransactionType.DEPOSIT:
        return AccountLedgerEntryType.DEPOSIT
    if transaction_type == TransactionType.WITHDRAWAL:
        return AccountLedgerEntryType.WITHDRAWAL
    if transaction_type == TransactionType.FEE:
        return AccountLedgerEntryType.FEE
    if transaction_type == TransactionType.TRANSFER_IN:
        return AccountLedgerEntryType.DEPOSIT
    if transaction_type == TransactionType.TRANSFER_OUT:
        return AccountLedgerEntryType.WITHDRAWAL
    return AccountLedgerEntryType.CASH_ADJUSTMENT


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


def sync_transaction_to_account_ledger(
    db: Session,
    *,
    transaction: Transaction,
    account: TradingAccount,
) -> AccountLedgerEntry:
    if transaction.account_id != account.id:
        raise ValueError("Transaction and account have different owners")
    if transaction.id is None:
        db.flush()

    ledger_entry = (
        db.query(AccountLedgerEntry)
        .filter(AccountLedgerEntry.transaction_id == transaction.id)
        .first()
    )
    if ledger_entry is not None and (
        ledger_entry.user_id != account.user_id
        or ledger_entry.account_id != account.id
    ):
        raise ValueError("Transaction ledger entry owner graph is inconsistent")
    if not ledger_entry:
        ledger_entry = AccountLedgerEntry(
            public_id=_deterministic_ledger_public_id(f"transaction:{transaction.public_id}")
        )
        db.add(ledger_entry)

    ledger_entry.user_id = account.user_id
    ledger_entry.account_id = account.id
    ledger_entry.transaction_id = transaction.id
    ledger_entry.entry_type = _transaction_entry_type(transaction.type)
    ledger_entry.occurred_at = transaction.date
    ledger_entry.currency = transaction.currency or account.currency or "USD"
    ledger_entry.amount = Decimal(str(transaction.amount))
    ledger_entry.amount_account_ccy = Decimal(str(transaction.amount))
    ledger_entry.fx_rate_to_account_ccy = Decimal("1")
    ledger_entry.source = "TRANSACTION"
    ledger_entry.source_run_id = transaction.public_id
    ledger_entry.description = transaction.description
    db.flush()
    return ledger_entry


def sync_opening_balance_to_account_ledger(
    db: Session,
    *,
    account: TradingAccount,
) -> AccountLedgerEntry | None:
    opening_balance = Decimal(str(account.initial_balance or 0))
    if opening_balance == 0:
        return None

    if account.id is None:
        db.flush()

    source_run_id = account.public_id or str(account.id)
    ledger_entry = (
        db.query(AccountLedgerEntry)
        .filter(
            AccountLedgerEntry.account_id == account.id,
            AccountLedgerEntry.user_id == account.user_id,
            AccountLedgerEntry.source == "OPENING_BALANCE",
        )
        .first()
    )
    if not ledger_entry:
        ledger_entry = AccountLedgerEntry(
            public_id=_deterministic_ledger_public_id(f"account:{source_run_id}:opening_balance")
        )
        db.add(ledger_entry)

    ledger_entry.user_id = account.user_id
    ledger_entry.account_id = account.id
    ledger_entry.entry_type = AccountLedgerEntryType.CASH_ADJUSTMENT
    ledger_entry.occurred_at = account.created_at or datetime.now(timezone.utc)
    ledger_entry.currency = account.currency or "USD"
    ledger_entry.amount = opening_balance
    ledger_entry.amount_account_ccy = opening_balance
    ledger_entry.fx_rate_to_account_ccy = Decimal("1")
    ledger_entry.source = "OPENING_BALANCE"
    ledger_entry.source_run_id = source_run_id
    ledger_entry.description = "Opening cash balance"
    db.flush()
    return ledger_entry


def sync_cash_balance_adjustment_to_account_ledger(
    db: Session,
    *,
    account: TradingAccount,
    target_cash_balance,
    description: str | None = None,
) -> AccountLedgerEntry | None:
    target_balance = Decimal(str(target_cash_balance))
    current_balance = calculate_account_cash_balance_read_model(db, account=account)
    adjustment_amount = target_balance - current_balance
    if adjustment_amount == 0:
        return None

    if account.id is None:
        db.flush()

    ledger_entry = AccountLedgerEntry(
        public_id=str(uuid.uuid4()),
        user_id=account.user_id,
        account_id=account.id,
        entry_type=AccountLedgerEntryType.CASH_ADJUSTMENT,
        occurred_at=datetime.now(timezone.utc),
        currency=account.currency or "USD",
        amount=adjustment_amount,
        amount_account_ccy=adjustment_amount,
        fx_rate_to_account_ccy=Decimal("1"),
        source="MANUAL_CASH_ADJUSTMENT",
        source_run_id=account.public_id or str(account.id),
        description=description or "Manual cash balance adjustment",
    )
    db.add(ledger_entry)
    db.flush()
    return ledger_entry


def sync_dividend_event_to_account_ledger(
    db: Session,
    *,
    event: PositionEvent,
) -> AccountLedgerEntry:
    _require_event_owner_graph(db, event)
    if event.id is None:
        db.flush()

    ledger_entry = (
        db.query(AccountLedgerEntry)
        .filter(AccountLedgerEntry.position_event_id == event.id)
        .first()
    )
    if ledger_entry is not None and (
        ledger_entry.user_id != event.user_id
        or ledger_entry.account_id != event.account_id
        or ledger_entry.position_id != event.position_id
    ):
        raise ValueError("Dividend ledger entry owner graph is inconsistent")
    if not ledger_entry:
        ledger_entry = AccountLedgerEntry(
            public_id=_deterministic_ledger_public_id(f"position_event:{event.public_id}:dividend")
        )
        db.add(ledger_entry)

    dividend_amount = Decimal(str(event.gross_amount or 0))
    ledger_entry.user_id = event.user_id
    ledger_entry.account_id = event.account_id
    ledger_entry.position_id = event.position_id
    ledger_entry.position_event_id = event.id
    ledger_entry.entry_type = AccountLedgerEntryType.DIVIDEND
    ledger_entry.occurred_at = event.event_time
    ledger_entry.currency = event.currency or "USD"
    ledger_entry.amount = dividend_amount
    ledger_entry.amount_account_ccy = dividend_amount * Decimal(str(event.fx_rate_to_account_ccy or 1))
    ledger_entry.fx_rate_to_account_ccy = Decimal(str(event.fx_rate_to_account_ccy or 1))
    ledger_entry.source = "POSITION_EVENT"
    ledger_entry.source_run_id = event.public_id
    ledger_entry.description = event.note or "Dividend"
    db.flush()
    return ledger_entry


def sync_manual_adjustment_event_to_account_ledger(
    db: Session,
    *,
    event: PositionEvent,
) -> AccountLedgerEntry:
    _require_event_owner_graph(db, event)
    if event.id is None:
        db.flush()

    ledger_entry = (
        db.query(AccountLedgerEntry)
        .filter(
            AccountLedgerEntry.position_event_id == event.id,
            AccountLedgerEntry.entry_type == AccountLedgerEntryType.CASH_ADJUSTMENT,
        )
        .first()
    )
    if ledger_entry is not None and (
        ledger_entry.user_id != event.user_id
        or ledger_entry.account_id != event.account_id
        or ledger_entry.position_id != event.position_id
    ):
        raise ValueError("Adjustment ledger entry owner graph is inconsistent")
    if not ledger_entry:
        ledger_entry = AccountLedgerEntry(
            public_id=_deterministic_ledger_public_id(f"position_event:{event.public_id}:manual_adjustment")
        )
        db.add(ledger_entry)

    adjustment_amount = Decimal(str(event.gross_amount or 0))
    fx_rate = Decimal(str(event.fx_rate_to_account_ccy or 1))
    ledger_entry.user_id = event.user_id
    ledger_entry.account_id = event.account_id
    ledger_entry.position_id = event.position_id
    ledger_entry.position_event_id = event.id
    ledger_entry.entry_type = AccountLedgerEntryType.CASH_ADJUSTMENT
    ledger_entry.occurred_at = event.event_time
    ledger_entry.currency = event.currency or "USD"
    ledger_entry.amount = adjustment_amount
    ledger_entry.amount_account_ccy = adjustment_amount * fx_rate
    ledger_entry.fx_rate_to_account_ccy = fx_rate
    ledger_entry.source = "POSITION_EVENT"
    ledger_entry.source_run_id = event.public_id
    ledger_entry.description = event.note or "Manual position adjustment"
    db.flush()
    return ledger_entry


def sync_realized_pnl_event_to_account_ledger(
    db: Session,
    *,
    event: PositionEvent,
    position: TradingPosition,
) -> AccountLedgerEntry | None:
    if (
        event.user_id != position.user_id
        or event.position_id != position.id
        or event.account_id != position.account_id
    ):
        raise ValueError("Position event and position have different owners")
    _require_event_owner_graph(db, event)
    if event.id is None:
        db.flush()

    ledger_entry = (
        db.query(AccountLedgerEntry)
        .filter(
            AccountLedgerEntry.position_event_id == event.id,
            AccountLedgerEntry.entry_type == AccountLedgerEntryType.REALIZED_PNL,
        )
        .first()
    )
    if ledger_entry is not None and (
        ledger_entry.user_id != event.user_id
        or ledger_entry.account_id != event.account_id
        or ledger_entry.position_id != position.id
    ):
        raise ValueError("Realized PnL ledger entry owner graph is inconsistent")
    realized_pnl = Decimal(str(event.realized_pnl_net or 0))

    if realized_pnl == 0:
        if ledger_entry:
            db.delete(ledger_entry)
            db.flush()
        return None

    if not ledger_entry:
        ledger_entry = AccountLedgerEntry(
            public_id=_deterministic_ledger_public_id(f"position_event:{event.public_id}:realized_pnl")
        )
        db.add(ledger_entry)

    fx_rate = Decimal(str(event.fx_rate_to_account_ccy or 1))
    ledger_entry.user_id = event.user_id
    ledger_entry.account_id = event.account_id
    ledger_entry.position_id = position.id
    ledger_entry.position_event_id = event.id
    ledger_entry.entry_type = AccountLedgerEntryType.REALIZED_PNL
    ledger_entry.occurred_at = event.event_time
    ledger_entry.currency = event.currency or position.base_currency or "USD"
    ledger_entry.amount = realized_pnl
    ledger_entry.amount_account_ccy = realized_pnl * fx_rate
    ledger_entry.fx_rate_to_account_ccy = fx_rate
    ledger_entry.source = "POSITION_EVENT"
    ledger_entry.source_run_id = event.public_id
    ledger_entry.description = f"{position.instrument.contract_symbol} realized PnL" if position.instrument else "Realized PnL"
    db.flush()
    return ledger_entry


def delete_transaction_ledger_entries(db: Session, *, transaction: Transaction) -> None:
    db.query(AccountLedgerEntry).filter(
        AccountLedgerEntry.transaction_id == transaction.id
    ).delete(synchronize_session=False)


def calculate_account_cash_balance_read_model(db: Session, *, account: TradingAccount) -> Decimal:
    """
    Return account cash from the ledger when an opening balance is available.

    Transitional rule: legacy accounts without `initial_balance` keep using the
    stored `cash_balance`, because old data may not have a complete opening
    ledger. Newer accounts can derive cash as opening balance + ledger effects.
    """
    ledger_entries = (
        db.query(AccountLedgerEntry)
        .filter(
            AccountLedgerEntry.account_id == account.id,
            AccountLedgerEntry.user_id == account.user_id,
        )
        .all()
    )
    ledger_entries = [
        entry
        for entry in ledger_entries
        if _ledger_entry_owner_graph_is_consistent(
            db,
            entry=entry,
            account=account,
        )
    ]
    has_opening_balance_ledger = any(entry.source == "OPENING_BALANCE" for entry in ledger_entries)
    ledger_total = sum(
        (
            Decimal(str(entry.amount_account_ccy))
            if entry.amount_account_ccy is not None
            else Decimal(str(entry.amount))
        )
        for entry in ledger_entries
    )

    if has_opening_balance_ledger:
        return ledger_total

    if account.initial_balance is not None:
        return Decimal(str(account.initial_balance)) + ledger_total

    if ledger_entries and account.cash_balance is None:
        return ledger_total

    return Decimal(str(account.cash_balance or 0))
