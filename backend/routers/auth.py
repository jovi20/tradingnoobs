"""
Trading Noobs Backend - Authentication Router
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError

from database import get_db
from schemas import PasswordChangeRequest, PasswordChangeResponse, UserProfileUpdate, UserResponse, Token
from services.auth_service import (
    authenticate_user,
    get_password_hash,
    get_user_credential,
    get_current_user,
    create_authenticated_session,
    oauth2_scheme,
    revoke_access_token,
    utc_now,
    verify_password,
)
from models import AuthToken, User, UserCredential, UserSession

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Login and get access token"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_authenticated_session(
        db=db,
        user=user,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current user's profile preferences."""
    update_data = profile_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value.strip() if isinstance(value, str) else value)
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/change-password", response_model=PasswordChangeResponse)
async def change_password(
    password_data: PasswordChangeRequest,
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change current user's password and revoke other active sessions."""
    credential = get_user_credential(db, current_user.id)
    current_hash = credential.password_hash if credential else current_user.hashed_password
    if not current_hash or not verify_password(password_data.current_password, current_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    if verify_password(password_data.new_password, current_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password",
        )

    new_hash = get_password_hash(password_data.new_password)
    now = utc_now()
    current_user.hashed_password = new_hash

    if credential is None:
        credential = UserCredential(
            user_id=current_user.id,
            password_hash=new_hash,
            password_updated_at=now,
        )
    else:
        credential.password_hash = new_hash
        credential.password_updated_at = now

    db.add(current_user)
    db.add(credential)
    db.flush()

    active_sessions_revoked = False
    current_token_jti = _decode_token_jti(token)
    current_token = db.query(AuthToken).filter(AuthToken.user_id == current_user.id).all()
    active_session_ids = set()
    for auth_token in current_token:
        if auth_token.token_jti == current_token_jti:
            continue
        if auth_token.revoked_at is None:
            auth_token.revoked_at = now
            db.add(auth_token)
            active_sessions_revoked = True
        active_session_ids.add(auth_token.session_id)

    for session_id in active_session_ids:
        session = db.query(UserSession).filter(UserSession.id == session_id).first()
        if session is not None and session.revoked_at is None:
            session.status = "REVOKED"
            session.revoked_at = now
            session.last_seen_at = now
            db.add(session)
            active_sessions_revoked = True

    db.commit()
    return PasswordChangeResponse(
        message="Password updated",
        active_sessions_revoked=active_sessions_revoked,
    )


def _decode_token_jti(token: str) -> str | None:
    from jose import jwt
    from config import get_settings

    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload.get("jti")
    except JWTError:
        return None


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Revoke the current access token and its session."""
    try:
        revoke_access_token(db, token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
