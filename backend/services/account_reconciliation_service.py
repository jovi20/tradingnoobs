"""Preview and audited repair workflow for journal ledger divergence."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from models import (
    AccountingHealth,
    AccountingReconciliationCase,
    AccountLedgerEntry,
    LedgerPostingKind,
    TradingAccount,
)
from services.account_ledger_service import (
    LedgerPostingConflictError,
    _ledger_entry_owner_graph_is_consistent,
    calculate_account_cash_balance_read_model,
    create_or_replay_posting,
)
from services.trading_accounting_service import quantize_posting


@dataclass(frozen=True)
class LedgerDivergence:
    code: str
    ledger_entry_public_id: str | None
    detail: str


@dataclass(frozen=True)
class AccountReconciliationPreview:
    account_public_id: str
    accounting_health: str
    journal_balance: str
    ledger_entry_count: int
    open_case_count: int
    divergences: tuple[LedgerDivergence, ...]

    @property
    def can_mark_healthy(self) -> bool:
        return not self.divergences and self.open_case_count == 0

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["can_mark_healthy"] = self.can_mark_healthy
        return payload


def _health_value(account: TradingAccount) -> str:
    value = account.accounting_health or AccountingHealth.HEALTHY.value
    return value.value if hasattr(value, "value") else str(value)


def preview_account_reconciliation(
    db: Session,
    *,
    account: TradingAccount,
) -> AccountReconciliationPreview:
    entries = db.query(AccountLedgerEntry).filter(
        AccountLedgerEntry.account_id == account.id,
    ).order_by(
        AccountLedgerEntry.occurred_at.asc(),
        AccountLedgerEntry.id.asc(),
    ).all()
    by_id = {entry.id: entry for entry in entries}
    compensated_ids = {
        entry.reverses_ledger_entry_id
        for entry in entries
        if entry.posting_kind == LedgerPostingKind.COMPENSATING_REVERSAL.value
        and entry.reverses_ledger_entry_id is not None
    }
    divergences: list[LedgerDivergence] = []
    keys: set[tuple[str, str]] = set()

    for entry in entries:
        key = (entry.source_fact_public_id, entry.posting_kind)
        if key in keys:
            divergences.append(
                LedgerDivergence(
                    "DUPLICATE_POSTING_KEY",
                    entry.public_id,
                    f"duplicate key {key[0]}/{key[1]}",
                )
            )
        keys.add(key)

        if not _ledger_entry_owner_graph_is_consistent(
            db,
            entry=entry,
            account=account,
        ):
            divergences.append(
                LedgerDivergence(
                    "OWNER_GRAPH_MISMATCH",
                    entry.public_id,
                    "ledger entry does not belong to the account owner graph",
                )
            )

        expected_account_amount = quantize_posting(
            Decimal(str(entry.amount))
            * Decimal(str(entry.fx_rate_to_account_ccy or 1))
        )
        actual_account_amount = quantize_posting(
            entry.amount_account_ccy
            if entry.amount_account_ccy is not None
            else entry.amount
        )
        if actual_account_amount != expected_account_amount:
            divergences.append(
                LedgerDivergence(
                    "ACCOUNT_CURRENCY_AMOUNT_MISMATCH",
                    entry.public_id,
                    f"expected {expected_account_amount}, got {actual_account_amount}",
                )
            )

        if (
            entry.posting_kind == LedgerPostingKind.LEGACY_UNRESOLVED.value
            and entry.id not in compensated_ids
        ):
            divergences.append(
                LedgerDivergence(
                    "LEGACY_UNRESOLVED_POSTING",
                    entry.public_id,
                    "legacy posting has no audited compensating entry",
                )
            )

        if entry.reverses_ledger_entry_id is not None:
            original = by_id.get(entry.reverses_ledger_entry_id)
            if (
                original is None
                or original.account_id != entry.account_id
                or original.user_id != entry.user_id
                or quantize_posting(entry.amount_account_ccy)
                != -quantize_posting(original.amount_account_ccy)
            ):
                divergences.append(
                    LedgerDivergence(
                        "INVALID_COMPENSATING_ENTRY",
                        entry.public_id,
                        "compensation is not an exact account-currency negation",
                    )
                )

    open_case_count = db.query(AccountingReconciliationCase).filter(
        AccountingReconciliationCase.account_id == account.id,
        AccountingReconciliationCase.status == "OPEN",
    ).count()
    return AccountReconciliationPreview(
        account_public_id=account.public_id,
        accounting_health=_health_value(account),
        journal_balance=format(
            calculate_account_cash_balance_read_model(db, account=account),
            "f",
        ),
        ledger_entry_count=len(entries),
        open_case_count=open_case_count,
        divergences=tuple(divergences),
    )


def preview_all_account_reconciliation(
    db: Session,
) -> list[AccountReconciliationPreview]:
    accounts = db.query(TradingAccount).order_by(
        TradingAccount.user_id.asc(),
        TradingAccount.id.asc(),
    ).all()
    return [
        preview_account_reconciliation(db, account=account)
        for account in accounts
    ]


def refresh_accounting_health(
    db: Session,
    *,
    account: TradingAccount,
    apply: bool = False,
) -> AccountReconciliationPreview:
    preview = preview_account_reconciliation(db, account=account)
    if apply:
        account.accounting_health = (
            AccountingHealth.HEALTHY.value
            if preview.can_mark_healthy
            else AccountingHealth.RECONCILIATION_REQUIRED.value
        )
        db.flush()
        preview = preview_account_reconciliation(db, account=account)
    return preview


def apply_compensating_repair(
    db: Session,
    *,
    case: AccountingReconciliationCase,
    actor_user_id: int,
    reason: str,
) -> AccountLedgerEntry:
    if case.status != "OPEN":
        raise LedgerPostingConflictError("Reconciliation case is not open")
    if not reason.strip():
        raise ValueError("A reconciliation reason is required")
    original = case.original_ledger_entry
    account = case.account
    if original is None or original.account_id != account.id:
        raise LedgerPostingConflictError(
            "Reconciliation case has no valid source posting"
        )

    compensation = create_or_replay_posting(
        db,
        user_id=account.user_id,
        account_id=account.id,
        position_id=original.position_id,
        position_event_id=None,
        transaction_id=None,
        source_fact_public_id=case.public_id,
        posting_kind=LedgerPostingKind.COMPENSATING_REVERSAL,
        occurred_at=datetime.now(timezone.utc),
        currency=original.currency,
        amount=-quantize_posting(original.amount),
        fx_rate_to_account_ccy=original.fx_rate_to_account_ccy or 1,
        reverses_ledger_entry_id=original.id,
        source="ACCOUNTING_RECONCILIATION",
        source_run_id=case.public_id,
        description=reason.strip(),
    )
    case.status = "RESOLVED"
    case.resolution_note = reason.strip()
    case.resolved_by_user_id = actor_user_id
    case.resolved_at = datetime.now(timezone.utc)
    db.flush()
    refresh_accounting_health(db, account=account, apply=True)
    return compensation
