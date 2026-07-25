"""Invite-only onboarding available in the journal baseline."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app_config.default_strategies import DEFAULT_STRATEGIES
from database import get_db
from models import Strategy, UserSettings
from schemas import UserCreate, UserResponse
from services.auth_rate_limit_service import (
    RateLimitExceeded,
    check_auth_rate_limit,
    consume_auth_attempt,
)
from services.auth_service import create_user, get_user_by_email, normalize_email
from services.invitation_service import InvitationError, redeem_invitation
from services.security_audit_service import add_security_audit_event
from services.timezone_service import normalize_iana_timezone


router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _raise_rate_limited(error: RateLimitExceeded) -> None:
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "code": "AUTH_RATE_LIMITED",
            "message": "Too many onboarding attempts",
        },
        headers={"Retry-After": str(error.retry_after_seconds)},
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    ip_address = _client_ip(request)
    try:
        check_auth_rate_limit(
            db,
            action="INVITE_REDEMPTION",
            dimension="IP",
            value=ip_address,
        )
        check_auth_rate_limit(
            db,
            action="INVITE_REDEMPTION",
            dimension="ACCOUNT",
            value=normalize_email(user_data.email),
        )
    except RateLimitExceeded as error:
        _raise_rate_limited(error)

    try:
        timezone_name = normalize_iana_timezone(user_data.timezone)
    except ValueError as error:
        _record_rejected_attempt(db, ip_address, user_data.email)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "TIMEZONE_INVALID", "message": str(error)},
        ) from None

    if get_user_by_email(db, user_data.email):
        _record_rejected_attempt(db, ip_address, user_data.email)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    try:
        user = create_user(
            db,
            user_data.email,
            user_data.password,
            timezone_name=timezone_name,
            commit=False,
        )
        db.add(UserSettings(user_id=user.id))
        for strategy_data in DEFAULT_STRATEGIES:
            db.add(
                Strategy(
                    user_id=user.id,
                    name=strategy_data["name"],
                    description=strategy_data.get("description"),
                    entry_rules=strategy_data.get("entry_rules"),
                    exit_rules=strategy_data.get("exit_rules"),
                    risk_rules=strategy_data.get("risk_rules"),
                    symbols=[],
                )
            )
        redeem_invitation(
            db,
            code=user_data.invite_code,
            user=user,
            ip_address=ip_address,
        )
        db.commit()
        db.refresh(user)
        return user
    except InvitationError as error:
        db.rollback()
        _record_rejected_attempt(db, ip_address, user_data.email)
        add_security_audit_event(
            db,
            event_type="INVITATION_REDEMPTION_REJECTED",
            outcome=error.code,
            subject_type="INVITATION",
            subject_public_id=error.invitation_public_id,
            ip_address=ip_address,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": error.code,
                "message": "Invitation cannot be redeemed",
            },
        ) from None
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or invitation already used",
        ) from None


def _record_rejected_attempt(
    db: Session,
    ip_address: str | None,
    email: str,
) -> None:
    try:
        consume_auth_attempt(
            db,
            action="INVITE_REDEMPTION",
            dimension="IP",
            value=ip_address,
            limit=10,
        )
        consume_auth_attempt(
            db,
            action="INVITE_REDEMPTION",
            dimension="ACCOUNT",
            value=normalize_email(email),
            limit=5,
        )
        db.commit()
    except RateLimitExceeded as error:
        _raise_rate_limited(error)
