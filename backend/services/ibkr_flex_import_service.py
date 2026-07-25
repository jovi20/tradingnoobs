"""Local-file staging and owner limits for IBKR Flex imports."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import tempfile

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app_config.release_contract import JOURNAL_BETA_CONTRACT
from models import ImportSession, User
from services.auth_rate_limit_service import (
    RateLimitExceeded,
    consume_auth_attempt,
)
from services.generic_import_service import (
    NONTERMINAL_STATUSES,
    import_temp_root,
)


IBKR_UPLOAD_SCOPE = "IBKR_FLEX_UPLOAD_V1"
IBKR_FILE_PREFIX = "tradingnoobs-import-ibkr-"
MAX_FILE_BYTES = JOURNAL_BETA_CONTRACT.imports.common_limits.max_file_bytes
OWNER_LIMITS = JOURNAL_BETA_CONTRACT.imports.ibkr_flex_xml_v1.owner_upload_limits


class IbkrFlexImportError(ValueError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int = 422,
        retry_after_seconds: int | None = None,
    ):
        self.code = code
        self.http_status = http_status
        self.retry_after_seconds = retry_after_seconds
        super().__init__(message)


@dataclass(frozen=True)
class StagedIbkrFlexFile:
    path: Path
    file_hash: str
    size_bytes: int
    original_filename: str
    media_type: str | None


def _safe_xml_filename(value: str | None) -> str:
    filename = Path((value or "statement.xml").replace("\x00", "")).name
    filename = filename.strip() or "statement.xml"
    if Path(filename).suffix.lower() != ".xml":
        raise IbkrFlexImportError(
            "UNSUPPORTED_IMPORT_FORMAT",
            "IBKR Flex import requires an XML file",
        )
    return filename[:255]


async def stage_ibkr_flex_upload(
    upload: UploadFile,
    *,
    temp_root: Path | None = None,
) -> StagedIbkrFlexFile:
    original_filename = _safe_xml_filename(upload.filename)
    root = temp_root or import_temp_root()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    descriptor, raw_path = tempfile.mkstemp(
        prefix=IBKR_FILE_PREFIX,
        suffix=".xml",
        dir=root,
    )
    path = Path(raw_path)
    os.chmod(path, 0o600)
    digest = hashlib.sha256()
    size = 0
    try:
        with os.fdopen(descriptor, "wb") as staged:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_FILE_BYTES:
                    raise IbkrFlexImportError(
                        "IMPORT_FILE_TOO_LARGE",
                        f"IBKR XML must not exceed {MAX_FILE_BYTES} bytes",
                        http_status=413,
                    )
                digest.update(chunk)
                staged.write(chunk)
        return StagedIbkrFlexFile(
            path=path,
            file_hash="sha256:" + digest.hexdigest(),
            size_bytes=size,
            original_filename=original_filename,
            media_type=upload.content_type,
        )
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def remove_staged_ibkr_flex_file(
    staged: StagedIbkrFlexFile | None,
) -> None:
    if staged is not None:
        staged.path.unlink(missing_ok=True)


def enforce_ibkr_owner_upload_limits(
    db: Session,
    *,
    user_id: int,
    now: datetime | None = None,
) -> User:
    current_time = now or datetime.now(timezone.utc)
    try:
        consume_auth_attempt(
            db,
            action=IBKR_UPLOAD_SCOPE,
            dimension="OWNER",
            value=str(user_id),
            limit=OWNER_LIMITS.max_uploads_per_window,
            window_seconds=OWNER_LIMITS.window_seconds,
            block_seconds=OWNER_LIMITS.window_seconds,
            now=current_time,
        )
    except RateLimitExceeded as exc:
        raise IbkrFlexImportError(
            "IBKR_UPLOAD_RATE_LIMITED",
            "Too many IBKR Flex uploads for this owner",
            http_status=429,
            retry_after_seconds=exc.retry_after_seconds,
        ) from exc

    owner = (
        db.query(User)
        .filter(User.id == user_id)
        .with_for_update()
        .one_or_none()
    )
    if owner is None:
        raise IbkrFlexImportError(
            "IMPORT_OWNER_NOT_FOUND",
            "Import owner does not exist",
            http_status=404,
        )
    active_count = (
        db.query(ImportSession.id)
        .filter(
            ImportSession.user_id == user_id,
            ImportSession.adapter_kind == "IBKR_FLEX_XML_V1",
            ImportSession.status.in_(NONTERMINAL_STATUSES),
        )
        .count()
    )
    if active_count >= OWNER_LIMITS.max_nonterminal_sessions:
        raise IbkrFlexImportError(
            "IBKR_ACTIVE_SESSION_LIMIT",
            "Owner already has the maximum number of active IBKR previews",
            http_status=429,
        )
    return owner
