from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime

from app_config.release_contract import (
    ReleaseContractViolation,
    release_violation_detail,
    require_allowed_transaction_type,
    require_release_currency,
)
from database import get_db
from models import Transaction, TradingAccount, TransactionType, User
from schemas import TransactionCreate, TransactionResponse
from services.account_ledger_service import delete_transaction_ledger_entries, sync_transaction_to_account_ledger
from services.auth_service import get_current_user
from services.public_id_service import resolve_trading_account, resolve_transaction

router = APIRouter(
    prefix="/api",
    tags=["transactions"]
)


def _release_contract_value(callable_, *args, **kwargs):
    try:
        return callable_(*args, **kwargs)
    except ReleaseContractViolation as violation:
        raise HTTPException(
            status_code=422,
            detail=release_violation_detail(violation),
        ) from violation

@router.post("/accounts/{account_id}/transactions", response_model=TransactionResponse)
def create_transaction(
    account_id: str,
    transaction: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new transaction and update account cash balance.
    """
    # 1. Verify Account Ownership
    account = resolve_trading_account(db, current_user.id, account_id)
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    transaction_type = _release_contract_value(
        require_allowed_transaction_type,
        transaction.type,
    )
    _release_contract_value(
        require_release_currency,
        account.currency,
        field="account.currency",
    )
    currency = _release_contract_value(
        require_release_currency,
        transaction.currency,
        field="currency",
    )

    # 2. Create Transaction Record
    db_transaction = Transaction(
        account_id=account.id,
        type=TransactionType(transaction_type),
        amount=transaction.amount,
        currency=currency,
        date=transaction.date,
        description=transaction.description
    )
    db.add(db_transaction)
    
    # 3. Update Account Cash Balance
    # DEPOSIT/INTEREST/TRANSFER_IN -> Add
    # WITHDRAWAL/FEE/TRANSFER_OUT -> Subtract (assuming amount is clear, but let's stick to signed amount logic)
    # Convention: Frontend sends positive for Deposit, negative for Withdrawal? 
    # Or keep amount positive and use Type to determine sign?
    # Let's use Type to determine sign for safety, or expect signed amount.
    # Plan: "Signed Amount" in model. 
    # DEPOSIT: +1000
    # WITHDRAWAL: -500
    # FEE: -10
    # If user sends +500 for Withdrawal, we should flip it or trust input?
    # Better to enforce sign based on type for consistency.
    
    amount = transaction.amount
    if transaction.type in [TransactionType.WITHDRAWAL, TransactionType.FEE, TransactionType.TRANSFER_OUT]:
        if amount > 0:
            amount = -amount # Enforce negative
    elif transaction.type in [TransactionType.DEPOSIT, TransactionType.INTEREST, TransactionType.TRANSFER_IN]:
        if amount < 0:
            amount = -amount # Enforce positive
            
    db_transaction.amount = amount
    
    # Initialize cash_balance if None
    if account.cash_balance is None:
        account.cash_balance = 0
        
    account.cash_balance += amount
    db.flush()
    sync_transaction_to_account_ledger(db, transaction=db_transaction, account=account)
    
    db.commit()
    db.refresh(db_transaction)
    db.refresh(account)
    
    return db_transaction

@router.get("/accounts/{account_id}/transactions", response_model=List[TransactionResponse])
def list_transactions(
    account_id: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify ownership
    account = resolve_trading_account(db, current_user.id, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
        
    transactions = db.query(Transaction).filter(
        Transaction.account_id == account.id
    ).order_by(desc(Transaction.date)).offset(skip).limit(limit).all()
    
    return transactions

@router.delete("/transactions/{transaction_id}")
def delete_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a transaction and revert the balance change.
    """
    # Get transaction and verify ownership through account
    transaction = resolve_transaction(db, current_user.id, transaction_id)
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    # Revert Balance
    account = transaction.trading_account
    account.cash_balance -= transaction.amount
    delete_transaction_ledger_entries(db, transaction=transaction)
    
    db.delete(transaction)
    db.commit()
    
    return {"ok": True}
