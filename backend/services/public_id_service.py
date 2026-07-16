"""
Trading Noobs Backend - Public ID Resolution Helpers
"""
from sqlalchemy.orm import Session

from models import Position, TradeBatch, TradingAccount, TradingPosition, Transaction
from services.truth_legacy_projection_service import resolve_legacy_position_for_truth


def resolve_trading_account(db: Session, user_id: int, identifier: str):
    account = db.query(TradingAccount).filter(
        TradingAccount.public_id == identifier,
        TradingAccount.user_id == user_id,
    ).first()
    if account:
        return account
    if identifier.isdigit():
        return db.query(TradingAccount).filter(
            TradingAccount.id == int(identifier),
            TradingAccount.user_id == user_id,
        ).first()
    return None


def resolve_position(db: Session, user_id: int, identifier: str):
    position = db.query(Position).filter(
        Position.public_id == identifier,
        Position.user_id == user_id,
    ).first()
    if position:
        return position
    if identifier.isdigit():
        position = db.query(Position).filter(
            Position.id == int(identifier),
            Position.user_id == user_id,
        ).first()
        if position:
            return position

    truth_position = db.query(TradingPosition).filter(
        TradingPosition.public_id == identifier,
        TradingPosition.user_id == user_id,
    ).first()
    if truth_position:
        return resolve_legacy_position_for_truth(db, truth_position=truth_position)
    return None


def resolve_trade_batch(db: Session, user_id: int, identifier: str):
    batch = db.query(TradeBatch).join(Position).filter(
        TradeBatch.public_id == identifier,
        Position.user_id == user_id,
    ).first()
    if batch:
        return batch
    if identifier.isdigit():
        return db.query(TradeBatch).join(Position).filter(
            TradeBatch.id == int(identifier),
            Position.user_id == user_id,
        ).first()
    return None


def resolve_transaction(db: Session, user_id: int, identifier: str):
    transaction = db.query(Transaction).join(TradingAccount).filter(
        Transaction.public_id == identifier,
        TradingAccount.user_id == user_id,
    ).first()
    if transaction:
        return transaction
    if identifier.isdigit():
        return db.query(Transaction).join(TradingAccount).filter(
            Transaction.id == int(identifier),
            TradingAccount.user_id == user_id,
        ).first()
    return None
