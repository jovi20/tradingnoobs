"""Trading account routes for the journal release."""
from datetime import timezone
from typing import List
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app_config.release_contract import (
    ReleaseContractViolation,
    release_violation_detail,
    require_release_currency,
)
from database import get_db
from models import (
    AccountingHealth,
    AccountLedgerEntry,
    LedgerPostingKind,
    TradingAccount,
    User,
)
from schemas import (
    FinancialFactReverseCreate,
    TradingAccountCreate,
    TradingAccountUpdate,
    TradingAccountResponse,
)
from services.account_ledger_service import (
    AccountingReconciliationRequiredError,
    LedgerPostingConflictError,
    calculate_account_cash_balance_read_model,
    create_or_replay_posting,
    require_accounting_healthy,
    sync_opening_balance_to_account_ledger,
)
from services.auth_service import get_current_user
from services.financial_command_service import (
    FinancialCommandError,
    account_has_financial_history,
    account_has_import_history,
    begin_financial_command,
    complete_financial_command,
    financial_request_id,
    lock_owned_account,
    permanently_forbid_account_hard_delete,
)
from services.timezone_service import LocalDateTimeError, normalize_user_datetime_to_utc

router = APIRouter(prefix="/api/accounts", tags=["Trading Accounts"])


def _require_release_currency(value: object, *, field: str = "currency") -> str:
    try:
        return require_release_currency(value, field=field)
    except ReleaseContractViolation as violation:
        raise HTTPException(
            status_code=422,
            detail=release_violation_detail(violation),
        ) from violation


def _journal_account_response(
    db: Session,
    account: TradingAccount,
) -> TradingAccountResponse:
    """Serialize the journal read model without relabeling it as cash or NAV."""
    health = account.accounting_health or AccountingHealth.HEALTHY.value
    health_value = health.value if hasattr(health, "value") else str(health)
    return TradingAccountResponse(
        id=account.id,
        public_id=account.public_id,
        user_id=account.user_id,
        name=account.name,
        broker=account.broker,
        account_type=account.account_type,
        currency=account.currency,
        initial_balance=account.initial_balance,
        journal_balance=calculate_account_cash_balance_read_model(db, account=account),
        accounting_health=health_value,
        trade_source_state=(
            account.trade_source_state.value
            if hasattr(account.trade_source_state, "value")
            else str(account.trade_source_state)
        ),
        journal_balance_trusted=health_value == AccountingHealth.HEALTHY.value,
        description=account.description,
        is_active=account.is_active,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


@router.get("", response_model=List[TradingAccountResponse])
async def list_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get journal accounts without depending on optional market data."""
    accounts = db.query(TradingAccount).filter(
        TradingAccount.user_id == current_user.id
    ).order_by(TradingAccount.created_at.desc()).all()
    return [_journal_account_response(db, account) for account in accounts]


@router.post("", response_model=TradingAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    account_data: TradingAccountCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new trading account"""
    command = None
    if account_data.initial_balance not in (None, 0):
        try:
            command = begin_financial_command(
                db,
                user_id=current_user.id,
                scope="account.opening-balance.create.v1",
                idempotency_key=idempotency_key,
                request_payload=jsonable_encoder(account_data),
            )
        except FinancialCommandError as exc:
            db.rollback()
            raise HTTPException(
                status_code=exc.http_status,
                detail={"code": exc.code, "message": str(exc)},
            ) from exc
        if command.replay_response is not None:
            return JSONResponse(status_code=201, content=command.replay_response)
    currency = _require_release_currency(account_data.currency)

    account = TradingAccount(
        user_id=current_user.id,
        name=account_data.name,
        broker=account_data.broker,
        account_type=account_data.account_type,
        currency=currency,
        initial_balance=account_data.initial_balance,
        description=account_data.description
    )
    try:
        db.add(account)
        db.flush()
        opening_entry = sync_opening_balance_to_account_ledger(db, account=account)
        if opening_entry is not None:
            permanently_forbid_account_hard_delete(account)
    except (
        AccountingReconciliationRequiredError,
        LedgerPostingConflictError,
    ) as exc:
        db.rollback()
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    response_content = jsonable_encoder(_journal_account_response(db, account))
    if command is not None and opening_entry is not None:
        complete_financial_command(
            db,
            record=command.record,
            response_json=response_content,
            source_fact_public_id=account.public_id,
        )
    db.commit()
    return JSONResponse(status_code=201, content=response_content)


@router.get("/{account_id}", response_model=TradingAccountResponse)
async def get_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific journal account."""
    account = lock_owned_account(
        db,
        user_id=current_user.id,
        account_public_id=account_id,
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return _journal_account_response(db, account)


@router.patch("/{account_id}", response_model=TradingAccountResponse)
async def update_account(
    account_id: str,
    account_data: TradingAccountUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a trading account"""
    account = lock_owned_account(
        db,
        user_id=current_user.id,
        account_public_id=account_id,
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    update_data = account_data.model_dump(exclude_unset=True)
    if "currency" in update_data:
        update_data["currency"] = _require_release_currency(
            update_data["currency"],
            field="currency",
        )
        if (
            update_data["currency"] != account.currency
            and (
                not account.hard_delete_eligible
                or account_has_financial_history(db, account=account)
                or account_has_import_history(db, account=account)
            )
        ):
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "ACCOUNT_BASE_CURRENCY_FROZEN",
                    "message": "Account currency is immutable after the first financial fact",
                },
            )

    for key, value in update_data.items():
        setattr(account, key, value)

    db.commit()
    db.refresh(account)
    return await get_account(account.public_id, current_user, db)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a trading account"""
    account = lock_owned_account(
        db,
        user_id=current_user.id,
        account_public_id=account_id,
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    if (
        not account.hard_delete_eligible
        or account_has_financial_history(db, account=account)
        or account_has_import_history(db, account=account)
    ):
        account.is_active = False
    else:
        db.delete(account)
    db.commit()
    return None


@router.post(
    "/{account_id}/opening-balance/reverse",
    response_model=TradingAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def reverse_opening_balance(
    account_id: str,
    payload: FinancialFactReverseCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    request_id: str | None = Header(default=None, alias="X-Request-ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = lock_owned_account(
        db,
        user_id=current_user.id,
        account_public_id=account_id,
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    original = (
        db.query(AccountLedgerEntry)
        .filter(
            AccountLedgerEntry.account_id == account.id,
            AccountLedgerEntry.user_id == current_user.id,
            AccountLedgerEntry.posting_kind
            == LedgerPostingKind.OPENING_BALANCE.value,
        )
        .with_for_update()
        .first()
    )
    if original is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "OPENING_BALANCE_NOT_FOUND", "message": "Account has no posted opening balance"},
        )
    try:
        command = begin_financial_command(
            db,
            user_id=current_user.id,
            scope="account.opening-balance.reverse.v1",
            idempotency_key=idempotency_key,
            request_payload={
                "account_public_id": account.public_id,
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
        if db.query(AccountLedgerEntry.id).filter(
            AccountLedgerEntry.reverses_ledger_entry_id == original.id
        ).first() is not None:
            raise FinancialCommandError(
                "FINANCIAL_FACT_ALREADY_REVERSED",
                "Opening balance has already been reversed",
                http_status=409,
            )
        occurred_at = normalize_user_datetime_to_utc(
            payload.occurred_at,
            timezone_name=current_user.timezone,
        )
        original_time = original.occurred_at
        if original_time.tzinfo is None:
            original_time = original_time.replace(tzinfo=timezone.utc)
        if occurred_at < original_time.astimezone(timezone.utc):
            raise FinancialCommandError(
                "REVERSAL_CHRONOLOGY_VIOLATION",
                "Opening-balance reversal cannot predate the original fact",
                http_status=422,
            )
        require_accounting_healthy(account)
        source_fact_public_id = str(uuid.uuid4())
        create_or_replay_posting(
            db,
            user_id=current_user.id,
            account_id=account.id,
            source_fact_public_id=source_fact_public_id,
            posting_kind=LedgerPostingKind.COMPENSATING_REVERSAL,
            occurred_at=occurred_at,
            currency=original.currency,
            amount=-original.amount,
            fx_rate_to_account_ccy=original.fx_rate_to_account_ccy or 1,
            reverses_ledger_entry_id=original.id,
            source="OPENING_BALANCE_REVERSAL",
            source_run_id=financial_request_id(
                request_id,
                fallback=idempotency_key or "",
            ),
            description=payload.reason.strip(),
        )
        response_content = jsonable_encoder(_journal_account_response(db, account))
        complete_financial_command(
            db,
            record=command.record,
            response_json=response_content,
            source_fact_public_id=source_fact_public_id,
        )
        db.commit()
        return JSONResponse(status_code=201, content=response_content)
    except LocalDateTimeError as exc:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail={"code": exc.code, "message": str(exc), "field": "occurred_at"},
        ) from exc
    except FinancialCommandError as exc:
        db.rollback()
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    except AccountingReconciliationRequiredError as exc:
        db.rollback()
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
