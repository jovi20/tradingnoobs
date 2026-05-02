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
    Transaction,
    TransactionType,
    TradingAccount,
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


def sync_transaction_to_account_ledger(
    db: Session,
    *,
    transaction: Transaction,
    account: TradingAccount,
) -> AccountLedgerEntry:
    if transaction.id is None:
        db.flush()

    ledger_entry = (
        db.query(AccountLedgerEntry)
        .filter(AccountLedgerEntry.transaction_id == transaction.id)
        .first()
    )
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
        .filter(AccountLedgerEntry.account_id == account.id)
        .all()
    )
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
