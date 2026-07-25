"""Trading account routes for the journal release."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app_config.release_contract import (
    ReleaseContractViolation,
    release_violation_detail,
    require_release_currency,
)
from database import get_db
from models import AccountingHealth, TradingAccount, User
from schemas import TradingAccountCreate, TradingAccountUpdate, TradingAccountResponse
from services.account_ledger_service import (
    calculate_account_cash_balance_read_model,
    sync_opening_balance_to_account_ledger,
)
from services.auth_service import get_current_user
from services.public_id_service import resolve_trading_account

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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new trading account"""
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
    db.add(account)
    db.flush()
    sync_opening_balance_to_account_ledger(db, account=account)
    db.commit()
    db.refresh(account)
    return await get_account(account.public_id, current_user, db)


@router.get("/{account_id}", response_model=TradingAccountResponse)
async def get_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific journal account."""
    account = resolve_trading_account(db, current_user.id, account_id)
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
    account = resolve_trading_account(db, current_user.id, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    update_data = account_data.model_dump(exclude_unset=True)
    if "currency" in update_data:
        update_data["currency"] = _require_release_currency(
            update_data["currency"],
            field="currency",
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
    account = resolve_trading_account(db, current_user.id, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    db.delete(account)
    db.commit()
    return None
