"""
Trading Noobs Backend - Account Ledger Service
"""
from __future__ import annotations

from decimal import Decimal
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


def delete_transaction_ledger_entries(db: Session, *, transaction: Transaction) -> None:
    db.query(AccountLedgerEntry).filter(
        AccountLedgerEntry.transaction_id == transaction.id
    ).delete(synchronize_session=False)
