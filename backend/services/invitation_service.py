from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from models import Invitation, User
from services.security_audit_service import add_security_audit_event


class InvitationError(Exception):
    code = "INVITATION_INVALID"

    def __init__(self, invitation_public_id: str | None = None):
        super().__init__(self.code)
        self.invitation_public_id = invitation_public_id


class InvitationExpired(InvitationError):
    code = "INVITATION_EXPIRED"


class InvitationRevoked(InvitationError):
    code = "INVITATION_REVOKED"


class InvitationAlreadyRedeemed(InvitationError):
    code = "INVITATION_ALREADY_REDEEMED"


def hash_invitation_code(code: str) -> str:
    return hashlib.sha256(code.strip().encode("utf-8")).hexdigest()


def create_invitation(
    db: Session,
    *,
    actor: User,
    expires_in_hours: int,
    ip_address: str | None = None,
) -> tuple[Invitation, str]:
    code = secrets.token_urlsafe(32)
    invitation = Invitation(
        code_hash=hash_invitation_code(code),
        created_by_user_id=actor.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_in_hours),
    )
    db.add(invitation)
    db.flush()
    add_security_audit_event(
        db,
        event_type="INVITATION_CREATED",
        outcome="SUCCESS",
        actor_user_id=actor.id,
        subject_type="INVITATION",
        subject_public_id=invitation.public_id,
        ip_address=ip_address,
    )
    db.commit()
    db.refresh(invitation)
    return invitation, code


def redeem_invitation(
    db: Session,
    *,
    code: str,
    user: User,
    ip_address: str | None = None,
) -> Invitation:
    invitation = (
        db.query(Invitation)
        .filter(Invitation.code_hash == hash_invitation_code(code))
        .with_for_update()
        .first()
    )
    if invitation is None:
        raise InvitationError()
    if invitation.revoked_at is not None:
        raise InvitationRevoked(invitation.public_id)
    if invitation.redeemed_at is not None:
        raise InvitationAlreadyRedeemed(invitation.public_id)
    expires_at = invitation.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        raise InvitationExpired(invitation.public_id)

    invitation.redeemed_at = datetime.now(timezone.utc)
    invitation.redeemed_by_user_id = user.id
    db.add(invitation)
    add_security_audit_event(
        db,
        event_type="INVITATION_REDEEMED",
        outcome="SUCCESS",
        actor_user_id=user.id,
        subject_type="INVITATION",
        subject_public_id=invitation.public_id,
        ip_address=ip_address,
    )
    return invitation


def revoke_invitation(
    db: Session,
    *,
    invitation: Invitation,
    actor: User,
    ip_address: str | None = None,
) -> Invitation:
    if invitation.redeemed_at is not None:
        raise InvitationAlreadyRedeemed()
    if invitation.revoked_at is None:
        invitation.revoked_at = datetime.now(timezone.utc)
        invitation.revoked_by_user_id = actor.id
        db.add(invitation)
        add_security_audit_event(
            db,
            event_type="INVITATION_REVOKED",
            outcome="SUCCESS",
            actor_user_id=actor.id,
            subject_type="INVITATION",
            subject_public_id=invitation.public_id,
            ip_address=ip_address,
        )
        db.commit()
        db.refresh(invitation)
    return invitation
