"""
Trading Noobs Backend - Authentication Service
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
import bcrypt
import uuid
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from config import get_settings
from database import get_db
from models import AuthToken, User, UserCredential, UserSession

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def normalize_email(email: str) -> str:
    """Normalize email for lookup and uniqueness checks."""
    return email.strip().lower()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    token_jti: Optional[str] = None,
) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    expire = utc_now() + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire})
    if token_jti is not None:
        to_encode.update({"jti": token_jti})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    normalized = normalize_email(email)
    user = db.query(User).filter(User.email_normalized == normalized).first()
    if user:
        return user
    return db.query(User).filter(User.email == email).first()


def get_user_credential(db: Session, user_id: int) -> Optional[UserCredential]:
    return db.query(UserCredential).filter(UserCredential.user_id == user_id).first()


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user"""
    user = get_user_by_email(db, email)
    credential = get_user_credential(db, user.id) if user else None
    password_hash = credential.password_hash if credential else (user.hashed_password if user else None)
    if not user or not password_hash or not verify_password(password, password_hash):
        return None
    user.last_login_at = utc_now()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_user(db: Session, email: str, password: str) -> User:
    """Create a new user"""
    hashed_password = get_password_hash(password)
    normalized = normalize_email(email)
    user = User(
        email=email.strip(),
        email_normalized=normalized,
        hashed_password=hashed_password,
        status="ACTIVE",
    )
    db.add(user)
    db.flush()
    credential = UserCredential(
        user_id=user.id,
        password_hash=hashed_password,
        password_updated_at=utc_now(),
    )
    db.add(credential)
    db.commit()
    db.refresh(user)
    return user


def create_authenticated_session(
    db: Session,
    user: User,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> str:
    expires_at = utc_now() + timedelta(minutes=settings.access_token_expire_minutes)
    session = UserSession(
        user_id=user.id,
        status="ACTIVE",
        ip_address=ip_address,
        user_agent=user_agent,
        last_seen_at=utc_now(),
        expires_at=expires_at,
    )
    db.add(session)
    db.flush()

    token_jti = str(uuid.uuid4())
    auth_token = AuthToken(
        user_id=user.id,
        session_id=session.id,
        token_jti=token_jti,
        token_type="bearer",
        issued_at=utc_now(),
        expires_at=expires_at,
    )
    db.add(auth_token)
    db.commit()
    return create_access_token(data={"sub": str(user.id)}, token_jti=token_jti)


def revoke_access_token(db: Session, token: str) -> None:
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    token_jti = payload.get("jti")
    if token_jti is None:
        raise JWTError("Missing jti")

    auth_token = db.query(AuthToken).filter(AuthToken.token_jti == token_jti).first()
    if auth_token is None or auth_token.revoked_at is not None:
        raise JWTError("Token not active")

    auth_token.revoked_at = utc_now()
    if auth_token.session is not None:
        auth_token.session.status = "REVOKED"
        auth_token.session.revoked_at = utc_now()
        auth_token.session.last_seen_at = utc_now()
        db.add(auth_token.session)
    db.add(auth_token)
    db.commit()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get the current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id_raw = payload.get("sub")
        token_jti = payload.get("jti")
        if user_id_raw is None:
            raise credentials_exception
        if token_jti is None:
            raise credentials_exception
        # 确保 user_id 是整数类型
        user_id = int(user_id_raw)
    except (JWTError, ValueError):
        raise credentials_exception

    auth_token = db.query(AuthToken).filter(AuthToken.token_jti == token_jti).first()
    if auth_token is None or auth_token.revoked_at is not None:
        raise credentials_exception
    if auth_token.expires_at is not None and as_utc(auth_token.expires_at) < utc_now():
        raise credentials_exception
    if auth_token.session is None or auth_token.session.revoked_at is not None or auth_token.session.status != "ACTIVE":
        raise credentials_exception
    auth_token.session.last_seen_at = utc_now()
    db.add(auth_token.session)
    db.commit()
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user
