from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from io import BytesIO
import os
from pathlib import Path
import stat
import tempfile

import pytest
from fastapi import UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import IdempotencyKey, ImportSession, TradingAccount, User
from services.ibkr_flex_import_service import (
    IbkrFlexImportError,
    enforce_ibkr_owner_upload_limits,
    remove_staged_ibkr_flex_file,
    stage_ibkr_flex_upload,
)


@pytest.fixture()
def db():
    descriptor, path = tempfile.mkstemp(suffix=".db")
    os.close(descriptor)
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
        os.remove(path)


def owner_and_account(db):
    owner = User(
        public_id="jrn013-limit-owner",
        email="jrn013-limit@example.com",
        email_normalized="jrn013-limit@example.com",
        hashed_password="hash",
        timezone="UTC",
    )
    account = TradingAccount(
        public_id="jrn013-limit-account",
        user=owner,
        name="IBKR",
        broker="IBKR",
        currency="USD",
        is_active=True,
    )
    db.add_all([owner, account])
    db.commit()
    return owner, account


def add_session(db, owner, account, suffix, status="PREVIEW_READY"):
    record = IdempotencyKey(
        public_id=f"limit-idem-{suffix}",
        user_id=owner.id,
        scope="IBKR_FLEX_UPLOAD_V1",
        key=f"limit-{suffix}",
        request_hash=f"sha256:{suffix:0<64}"[:71],
        status="COMPLETED",
        response_json={},
    )
    db.add(record)
    db.flush()
    db.add(
        ImportSession(
            public_id=f"limit-session-{suffix}",
            user_id=owner.id,
            account_id=account.id,
            upload_idempotency_id=record.id,
            adapter_kind="IBKR_FLEX_XML_V1",
            file_format="XML",
            file_hash=f"sha256:{suffix:0<64}"[:71],
            file_size_bytes=10,
            original_filename=f"{suffix}.xml",
            media_type="application/xml",
            status=status,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
    )
    db.commit()


def test_staging_uses_private_file_and_explicit_cleanup(tmp_path):
    upload = UploadFile(
        filename="statement.xml",
        file=BytesIO(b"<FlexQueryResponse />"),
        headers={"content-type": "application/xml"},
    )
    staged = asyncio.run(
        stage_ibkr_flex_upload(upload, temp_root=tmp_path)
    )

    assert staged.path.is_file()
    assert stat.S_IMODE(staged.path.stat().st_mode) == 0o600
    assert staged.file_hash.startswith("sha256:")
    remove_staged_ibkr_flex_file(staged)
    assert not staged.path.exists()


def test_invalid_extension_and_oversize_remove_partial_file(
    tmp_path,
    monkeypatch,
):
    wrong = UploadFile(
        filename="statement.csv",
        file=BytesIO(b"not xml"),
    )
    with pytest.raises(IbkrFlexImportError) as wrong_failure:
        asyncio.run(stage_ibkr_flex_upload(wrong, temp_root=tmp_path))
    assert wrong_failure.value.code == "UNSUPPORTED_IMPORT_FORMAT"

    monkeypatch.setattr(
        "services.ibkr_flex_import_service.MAX_FILE_BYTES",
        4,
    )
    oversized = UploadFile(
        filename="statement.xml",
        file=BytesIO(b"12345"),
    )
    with pytest.raises(IbkrFlexImportError) as size_failure:
        asyncio.run(
            stage_ibkr_flex_upload(oversized, temp_root=tmp_path)
        )
    assert size_failure.value.code == "IMPORT_FILE_TOO_LARGE"
    assert list(Path(tmp_path).iterdir()) == []


def test_two_nonterminal_sessions_are_allowed_but_third_is_blocked(db):
    owner, account = owner_and_account(db)
    enforce_ibkr_owner_upload_limits(db, user_id=owner.id)
    add_session(db, owner, account, "one")
    enforce_ibkr_owner_upload_limits(db, user_id=owner.id)
    add_session(db, owner, account, "two")

    with pytest.raises(IbkrFlexImportError) as failure:
        enforce_ibkr_owner_upload_limits(db, user_id=owner.id)
    assert failure.value.code == "IBKR_ACTIVE_SESSION_LIMIT"

    first = db.query(ImportSession).filter(
        ImportSession.public_id == "limit-session-one"
    ).one()
    first.status = "EXPIRED"
    db.commit()
    assert enforce_ibkr_owner_upload_limits(db, user_id=owner.id).id == owner.id


def test_eleventh_upload_in_window_is_rate_limited(db):
    owner, _ = owner_and_account(db)
    now = datetime(2026, 7, 26, tzinfo=timezone.utc)
    for _ in range(10):
        enforce_ibkr_owner_upload_limits(
            db,
            user_id=owner.id,
            now=now,
        )

    with pytest.raises(IbkrFlexImportError) as failure:
        enforce_ibkr_owner_upload_limits(
            db,
            user_id=owner.id,
            now=now,
        )
    assert failure.value.code == "IBKR_UPLOAD_RATE_LIMITED"
    assert failure.value.retry_after_seconds == 600
