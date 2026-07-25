"""Immutable account cash-fact commands for the journal release."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app_config.release_contract import (
    ReleaseContractViolation,
    release_violation_detail,
    require_allowed_transaction_type,
    require_release_currency,
)
from database import get_db
from models import Transaction, TransactionType, TradingAccount, User
from schemas import (
    FinancialFactReverseCreate,
    TransactionCreate,
    TransactionResponse,
)
from services.account_ledger_service import (
    AccountingReconciliationRequiredError,
    LedgerPostingConflictError,
    sync_transaction_reversal_to_account_ledger,
    sync_transaction_to_account_ledger,
)
from services.auth_service import get_current_user
from services.financial_command_service import (
    FinancialCommandError,
    begin_financial_command,
    complete_financial_command,
    financial_request_id,
    lock_owned_account,
    permanently_forbid_account_hard_delete,
)
from services.public_id_service import resolve_transaction
from services.timezone_service import LocalDateTimeError, normalize_user_datetime_to_utc

router = APIRouter(prefix="/api", tags=["transactions"])


def _contract_value(callable_, *args, **kwargs):
    try:
        return callable_(*args, **kwargs)
    except ReleaseContractViolation as violation:
        raise HTTPException(
            status_code=422,
            detail=release_violation_detail(violation),
        ) from violation


def _occurred_at(value: datetime, *, current_user: User) -> datetime:
    try:
        return normalize_user_datetime_to_utc(value, timezone_name=current_user.timezone)
    except LocalDateTimeError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": exc.code, "message": str(exc), "field": "date"},
        ) from exc


def _transaction_payload(db: Session, transaction: Transaction) -> dict:
    original_public_id = None
    reversal_public_id = db.query(Transaction.public_id).filter(
        Transaction.reverses_transaction_id == transaction.id
    ).scalar()
    if transaction.reverses_transaction_id is not None:
        original_public_id = db.query(Transaction.public_id).filter(
            Transaction.id == transaction.reverses_transaction_id
        ).scalar()
    return {
        "id": transaction.id,
        "public_id": transaction.public_id,
        "account_id": transaction.account_id,
        "type": (
            transaction.type.value
            if hasattr(transaction.type, "value")
            else str(transaction.type)
        ),
        "amount": transaction.amount,
        "currency": transaction.currency,
        "date": transaction.date,
        "description": transaction.description,
        "created_at": transaction.created_at,
        "updated_at": transaction.updated_at,
        "reverses_transaction_public_id": original_public_id,
        "reversed_by_transaction_public_id": reversal_public_id,
        "reversal_reason": transaction.reversal_reason,
        "request_id": transaction.request_id,
    }


def _command_error(db: Session, exc: Exception) -> HTTPException:
    db.rollback()
    if isinstance(exc, FinancialCommandError):
        return HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": str(exc)},
        )
    if isinstance(exc, (AccountingReconciliationRequiredError, LedgerPostingConflictError)):
        return HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": str(exc)},
        )
    raise exc


@router.post(
    "/accounts/{account_id}/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_transaction(
    account_id: str,
    transaction: TransactionCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    request_id: str | None = Header(default=None, alias="X-Request-ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    account = lock_owned_account(
        db,
        user_id=current_user.id,
        account_public_id=account_id,
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    try:
        command = begin_financial_command(
            db,
            user_id=current_user.id,
            scope="account.cash-transaction.create.v1",
            idempotency_key=idempotency_key,
            request_payload={
                "account_public_id": account.public_id,
                "payload": jsonable_encoder(transaction),
            },
        )
        if command.replay_response is not None:
            return JSONResponse(status_code=201, content=command.replay_response)
        if not account.is_active:
            raise FinancialCommandError(
                "ACCOUNT_ARCHIVED",
                "Archived accounts are read-only",
                http_status=409,
            )
        transaction_type = _contract_value(
            require_allowed_transaction_type,
            transaction.type,
        )
        account_currency = _contract_value(
            require_release_currency,
            account.currency,
            field="account.currency",
        )
        currency = _contract_value(
            require_release_currency,
            transaction.currency,
            field="currency",
        )
        if currency != account_currency:
            raise FinancialCommandError(
                "ACCOUNT_CURRENCY_MISMATCH",
                "Transaction currency must match account currency",
                http_status=422,
            )
        normalized_time = _occurred_at(
            transaction.date,
            current_user=current_user,
        )

        amount = Decimal(transaction.amount)
        if transaction_type in {"WITHDRAWAL", "FEE"}:
            amount = -amount
        db_transaction = Transaction(
            account_id=account.id,
            type=TransactionType(transaction_type),
            amount=amount,
            currency=currency,
            date=normalized_time,
            description=transaction.description,
            actor_user_id=current_user.id,
            request_id=financial_request_id(
                request_id,
                fallback=idempotency_key or "",
            ),
        )
        db.add(db_transaction)
        db.flush()
        permanently_forbid_account_hard_delete(account)
        sync_transaction_to_account_ledger(
            db,
            transaction=db_transaction,
            account=account,
        )
        response_content = jsonable_encoder(_transaction_payload(db, db_transaction))
        complete_financial_command(
            db,
            record=command.record,
            response_json=response_content,
            source_fact_public_id=db_transaction.public_id,
        )
        db.commit()
        return JSONResponse(status_code=201, content=response_content)
    except (
        FinancialCommandError,
        AccountingReconciliationRequiredError,
        LedgerPostingConflictError,
    ) as exc:
        raise _command_error(db, exc) from exc


@router.get(
    "/accounts/{account_id}/transactions",
    response_model=List[TransactionResponse],
)
def list_transactions(
    account_id: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    account = lock_owned_account(
        db,
        user_id=current_user.id,
        account_public_id=account_id,
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    transactions = (
        db.query(Transaction)
        .filter(Transaction.account_id == account.id)
        .order_by(desc(Transaction.date), desc(Transaction.id))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_transaction_payload(db, transaction) for transaction in transactions]


@router.post(
    "/transactions/{transaction_id}/reverse",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def reverse_transaction(
    transaction_id: str,
    payload: FinancialFactReverseCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    request_id: str | None = Header(default=None, alias="X-Request-ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = resolve_transaction(db, current_user.id, transaction_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    account_public_id = db.query(TradingAccount.public_id).filter(
        TradingAccount.id == candidate.account_id
    ).scalar()
    account = lock_owned_account(
        db,
        user_id=current_user.id,
        account_public_id=account_public_id,
    )
    original = (
        db.query(Transaction)
        .filter(
            Transaction.id == candidate.id,
            Transaction.account_id == account.id,
        )
        .with_for_update()
        .one()
    )
    try:
        command = begin_financial_command(
            db,
            user_id=current_user.id,
            scope="account.cash-transaction.reverse.v1",
            idempotency_key=idempotency_key,
            request_payload={
                "transaction_public_id": original.public_id,
                "payload": jsonable_encoder(payload),
            },
        )
        if command.replay_response is not None:
            return JSONResponse(status_code=201, content=command.replay_response)
        if not account.is_active:
            raise FinancialCommandError(
                "ACCOUNT_ARCHIVED",
                "Archived accounts are read-only",
                http_status=409,
            )
        if original.reverses_transaction_id is not None:
            raise FinancialCommandError(
                "REVERSAL_OF_REVERSAL_FORBIDDEN",
                "A compensating reversal cannot itself be reversed",
                http_status=409,
            )
        if db.query(Transaction.id).filter(
            Transaction.reverses_transaction_id == original.id
        ).first() is not None:
            raise FinancialCommandError(
                "FINANCIAL_FACT_ALREADY_REVERSED",
                "Transaction has already been reversed",
                http_status=409,
            )

        reversal_time = _occurred_at(
            payload.occurred_at,
            current_user=current_user,
        )
        original_time = original.date
        if original_time.tzinfo is None:
            original_time = original_time.replace(tzinfo=timezone.utc)
        if reversal_time < original_time.astimezone(timezone.utc):
            raise FinancialCommandError(
                "REVERSAL_CHRONOLOGY_VIOLATION",
                "Transaction reversal cannot predate the original fact",
                http_status=422,
            )
        reversal = Transaction(
            account_id=account.id,
            type=original.type,
            amount=-Decimal(original.amount),
            currency=original.currency,
            date=reversal_time,
            description=f"Reversal of {original.public_id}",
            reverses_transaction_id=original.id,
            actor_user_id=current_user.id,
            request_id=financial_request_id(
                request_id,
                fallback=idempotency_key or "",
            ),
            reversal_reason=payload.reason.strip(),
        )
        db.add(reversal)
        db.flush()
        sync_transaction_reversal_to_account_ledger(
            db,
            transaction=reversal,
            original=original,
            account=account,
        )
        response_content = jsonable_encoder(_transaction_payload(db, reversal))
        complete_financial_command(
            db,
            record=command.record,
            response_json=response_content,
            source_fact_public_id=reversal.public_id,
        )
        db.commit()
        return JSONResponse(status_code=201, content=response_content)
    except (
        FinancialCommandError,
        AccountingReconciliationRequiredError,
        LedgerPostingConflictError,
    ) as exc:
        raise _command_error(db, exc) from exc


@router.delete("/transactions/{transaction_id}", status_code=405)
def delete_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if resolve_transaction(db, current_user.id, transaction_id) is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    raise HTTPException(
        status_code=405,
        detail={
            "code": "FINANCIAL_FACT_IMMUTABLE",
            "message": "Posted transactions cannot be deleted; create a reversal",
        },
    )
