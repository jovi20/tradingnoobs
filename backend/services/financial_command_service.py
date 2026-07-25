"""Shared locking, idempotency, and account-lifecycle rules for financial commands."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from models import (
    AccountLedgerEntry,
    IdempotencyKey,
    PositionEvent,
    Transaction,
    TradingAccount,
    TradingPosition,
)
from services.idempotency_service import (
    begin_idempotent_request,
    complete_idempotent_request,
)


class FinancialCommandError(ValueError):
    def __init__(self, code: str, message: str, *, http_status: int) -> None:
        self.code = code
        self.http_status = http_status
        super().__init__(message)


@dataclass(frozen=True)
class FinancialCommandBegin:
    record: IdempotencyKey
    replay_response: dict | list | str | int | float | bool | None


def lock_owned_account(
    db: Session,
    *,
    user_id: int,
    account_public_id: str,
) -> TradingAccount | None:
    query = db.query(TradingAccount).filter(TradingAccount.user_id == user_id)
    if account_public_id.isdigit():
        query = query.filter(
            (TradingAccount.public_id == account_public_id)
            | (TradingAccount.id == int(account_public_id))
        )
    else:
        query = query.filter(TradingAccount.public_id == account_public_id)
    account = query.with_for_update().first()
    if account is not None and db.get_bind().dialect.name == "sqlite":
        db.execute(
            text(
                """
                UPDATE trading_accounts
                SET trade_source_state = trade_source_state
                WHERE id = :account_id
                """
            ),
            {"account_id": account.id},
        )
    return account


def begin_financial_command(
    db: Session,
    *,
    user_id: int,
    scope: str,
    idempotency_key: str | None,
    request_payload: dict,
) -> FinancialCommandBegin:
    normalized_key = (idempotency_key or "").strip()
    if not normalized_key:
        raise FinancialCommandError(
            "IDEMPOTENCY_KEY_REQUIRED",
            "Idempotency-Key is required for financial commands",
            http_status=422,
        )
    if len(normalized_key) > 255:
        raise FinancialCommandError(
            "IDEMPOTENCY_KEY_INVALID",
            "Idempotency-Key must be at most 255 characters",
            http_status=422,
        )
    try:
        result = begin_idempotent_request(
            db,
            scope=scope,
            key=normalized_key,
            request_payload=request_payload,
            user_id=user_id,
            ttl_seconds=None,
        )
    except ValueError as exc:
        raise FinancialCommandError(
            "IDEMPOTENCY_KEY_REUSED",
            str(exc),
            http_status=409,
        ) from exc

    if result.created:
        return FinancialCommandBegin(result.record, None)
    if result.record.status == "COMPLETED" and result.record.response_json is not None:
        return FinancialCommandBegin(result.record, result.record.response_json)
    raise FinancialCommandError(
        "IDEMPOTENCY_REQUEST_IN_PROGRESS",
        "Idempotent request is already in progress",
        http_status=409,
    )


def complete_financial_command(
    db: Session,
    *,
    record: IdempotencyKey,
    response_json: dict,
    source_fact_public_id: str,
) -> None:
    complete_idempotent_request(
        db,
        record=record,
        response_json=response_json,
        source_fact_public_id=source_fact_public_id,
    )


def financial_request_id(value: str | None, *, fallback: str) -> str:
    normalized = (value or fallback).strip()
    if not normalized or len(normalized) > 100:
        raise FinancialCommandError(
            "REQUEST_ID_INVALID",
            "X-Request-ID must contain 1 to 100 characters",
            http_status=422,
        )
    return normalized


def account_has_financial_history(db: Session, *, account: TradingAccount) -> bool:
    checks = (
        db.query(AccountLedgerEntry.id).filter(
            AccountLedgerEntry.account_id == account.id,
            AccountLedgerEntry.user_id == account.user_id,
        ),
        db.query(Transaction.id).filter(Transaction.account_id == account.id),
        db.query(TradingPosition.id).filter(
            TradingPosition.account_id == account.id,
            TradingPosition.user_id == account.user_id,
        ),
        db.query(PositionEvent.id).filter(
            PositionEvent.account_id == account.id,
            PositionEvent.user_id == account.user_id,
        ),
    )
    return any(query.first() is not None for query in checks)


def permanently_forbid_account_hard_delete(account: TradingAccount) -> None:
    account.hard_delete_eligible = False
