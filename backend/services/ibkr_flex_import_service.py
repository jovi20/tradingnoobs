"""Local-file staging and owner limits for IBKR Flex imports."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import os
from pathlib import Path
import tempfile
from typing import Any

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app_config.ibkr_flex_provider_evidence import (
    VerifiedIbkrFlexProviderContract,
)
from app_config.release_contract import JOURNAL_BETA_CONTRACT
from models import (
    ImportAdapterKind,
    ImportSession,
    ImportSessionStatus,
    ImportSourceBinding,
    TradingAccount,
    User,
)
from services.auth_rate_limit_service import (
    RateLimitExceeded,
    consume_auth_attempt,
)
from services.financial_command_service import (
    lock_owned_account,
    permanently_forbid_account_hard_delete,
)
from services.generic_import_service import (
    NONTERMINAL_STATUSES,
    PREVIEW_TTL_SECONDS,
    import_temp_root,
    serialize_import_session,
    transition_import_session,
)
from services.ibkr_flex_bootstrap_preview_service import (
    BootstrapPreviewResult,
    IbkrBootstrapPreviewError,
    preview_ibkr_source_bootstrap,
)
from services.ibkr_flex_parser import (
    IbkrFlexParseError,
    parse_ibkr_flex_xml,
)
from services.ibkr_flex_preview_service import (
    BoundPreviewResult,
    IbkrFlexPreviewError,
    preview_bound_ibkr_statement,
)
from services.idempotency_service import (
    begin_idempotent_request,
    complete_idempotent_request,
)


IBKR_UPLOAD_SCOPE = "IBKR_FLEX_UPLOAD_V1"
IBKR_UPLOAD_RESPONSE_SCHEMA_VERSION = 1
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


@dataclass(frozen=True)
class IbkrFlexUploadCommandResult:
    body: dict[str, Any]
    http_status: int
    replayed: bool


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _idempotency_key_hash(raw_key: str | None) -> str:
    normalized = (raw_key or "").strip()
    if not normalized:
        raise IbkrFlexImportError(
            "IDEMPOTENCY_KEY_REQUIRED",
            "Idempotency-Key is required for IBKR Flex upload",
        )
    if len(normalized) > 255:
        raise IbkrFlexImportError(
            "IDEMPOTENCY_KEY_INVALID",
            "Idempotency-Key must be at most 255 characters",
        )
    return "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


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


def _serialize_source_preview(
    result: BootstrapPreviewResult | BoundPreviewResult,
) -> dict[str, Any]:
    common = {
        "masked_external_account_ref": result.masked_external_account_ref,
        "source_preview_schema_version": result.source_preview_schema_version,
        "source_preview_digest": result.source_preview_digest,
    }
    if isinstance(result, BootstrapPreviewResult):
        return {
            **common,
            "mode": "BOOTSTRAP",
            "flat_boundary_evidence": result.flat_boundary_evidence,
            "effective_execution_count": result.effective_execution_count,
            "accepted_tombstone_count": result.accepted_tombstone_count,
            "conflict_reason": result.conflict_reason,
        }
    return {
        **common,
        "mode": "BOUND",
        "binding_public_id": result.binding_public_id,
        "statement_public_id": result.statement_public_id,
        "source_health": result.source_health,
        "source_completeness": result.source_completeness,
        "coverage_gap": result.coverage_gap,
        "pending_statement_count": result.pending_statement_count,
        "pending_execution_count": result.pending_execution_count,
    }


def _serialize_upload_response(
    db: Session,
    *,
    session: ImportSession,
    preview: BootstrapPreviewResult | BoundPreviewResult | None,
) -> dict[str, Any]:
    body = serialize_import_session(
        db,
        session=session,
        include_rows=session.status
        in {
            ImportSessionStatus.PREVIEW_READY.value,
            ImportSessionStatus.CONFLICTED.value,
        },
    )
    body["schema_version"] = IBKR_UPLOAD_RESPONSE_SCHEMA_VERSION
    body["source_preview"] = (
        _serialize_source_preview(preview) if preview is not None else None
    )
    return body


def _existing_binding(
    db: Session,
    *,
    account: TradingAccount,
) -> ImportSourceBinding | None:
    return (
        db.query(ImportSourceBinding)
        .filter(
            ImportSourceBinding.user_id == account.user_id,
            ImportSourceBinding.account_id == account.id,
        )
        .with_for_update()
        .one_or_none()
    )


def upload_ibkr_flex_preview(
    db: Session,
    *,
    user_id: int,
    account: TradingAccount,
    source_timezone: str,
    staged: StagedIbkrFlexFile,
    idempotency_key: str | None,
    provider_contract: VerifiedIbkrFlexProviderContract,
    now: datetime | None = None,
) -> IbkrFlexUploadCommandResult:
    current_time = _as_utc(now or datetime.now(timezone.utc))
    key_hash = _idempotency_key_hash(idempotency_key)
    request_payload = {
        "account_public_id": account.public_id,
        "adapter_kind": ImportAdapterKind.IBKR_FLEX_XML_V1.value,
        "file_hash": staged.file_hash,
        "source_timezone": source_timezone,
    }
    try:
        command = begin_idempotent_request(
            db,
            scope=IBKR_UPLOAD_SCOPE,
            key=key_hash,
            request_payload=request_payload,
            user_id=user_id,
            ttl_seconds=None,
            now=current_time,
        )
    except ValueError as exc:
        raise IbkrFlexImportError(
            "IDEMPOTENCY_KEY_REUSED",
            str(exc),
            http_status=409,
        ) from exc
    if not command.created:
        if (
            command.record.status == "COMPLETED"
            and isinstance(command.record.response_json, dict)
        ):
            envelope = command.record.response_json
            return IbkrFlexUploadCommandResult(
                body=envelope["body"],
                http_status=int(envelope["http_status"]),
                replayed=True,
            )
        raise IbkrFlexImportError(
            "IDEMPOTENCY_REQUEST_IN_PROGRESS",
            "IBKR Flex upload with this Idempotency-Key is already in progress",
            http_status=409,
        )

    if account.user_id != user_id:
        raise IbkrFlexImportError(
            "IMPORT_ACCOUNT_NOT_FOUND",
            "Import account does not exist",
            http_status=404,
        )
    enforce_ibkr_owner_upload_limits(
        db,
        user_id=user_id,
        now=current_time,
    )
    session = ImportSession(
        user_id=user_id,
        account_id=account.id,
        upload_idempotency_id=command.record.id,
        adapter_kind=ImportAdapterKind.IBKR_FLEX_XML_V1.value,
        file_format="XML",
        file_hash=staged.file_hash,
        file_size_bytes=staged.size_bytes,
        original_filename=staged.original_filename,
        media_type=staged.media_type,
        status=ImportSessionStatus.UPLOADING.value,
        expires_at=current_time + timedelta(seconds=PREVIEW_TTL_SECONDS),
        status_changed_at=current_time,
        response_schema_version=IBKR_UPLOAD_RESPONSE_SCHEMA_VERSION,
    )
    db.add(session)
    permanently_forbid_account_hard_delete(account)
    db.flush()

    preview: BootstrapPreviewResult | BoundPreviewResult | None = None
    http_status = 201
    try:
        with db.begin_nested():
            parsed = parse_ibkr_flex_xml(
                staged.path,
                source_timezone=source_timezone,
                provider_contract=provider_contract,
            )
            binding = _existing_binding(db, account=account)
            if binding is None:
                preview = preview_ibkr_source_bootstrap(
                    db,
                    account=account,
                    session=session,
                    parsed=parsed,
                    provider_contract=provider_contract,
                    now=current_time,
                )
            else:
                preview = preview_bound_ibkr_statement(
                    db,
                    account=account,
                    binding=binding,
                    session=session,
                    parsed=parsed,
                    provider_contract=provider_contract,
                    now=current_time,
                )
    except (IbkrFlexParseError, IbkrBootstrapPreviewError, IbkrFlexPreviewError) as exc:
        db.refresh(session)
        session.error_code = exc.code
        session.error_message = str(exc)
        transition_import_session(
            db,
            session=session,
            from_status=ImportSessionStatus.UPLOADING.value,
            to_status=ImportSessionStatus.FAILED.value,
            now=current_time,
        )
        http_status = getattr(exc, "http_status", 422)

    body = _serialize_upload_response(
        db,
        session=session,
        preview=preview,
    )
    complete_idempotent_request(
        db,
        record=command.record,
        response_json={"http_status": http_status, "body": body},
        source_fact_public_id=session.public_id,
        now=current_time,
    )
    db.commit()
    return IbkrFlexUploadCommandResult(
        body=body,
        http_status=http_status,
        replayed=False,
    )


async def stage_and_upload_ibkr_flex_preview(
    db: Session,
    *,
    user_id: int,
    account_public_id: str,
    source_timezone: str,
    upload: UploadFile,
    idempotency_key: str | None,
    provider_contract: VerifiedIbkrFlexProviderContract,
    now: datetime | None = None,
    temp_root: Path | None = None,
) -> IbkrFlexUploadCommandResult:
    staged: StagedIbkrFlexFile | None = None
    try:
        account = lock_owned_account(
            db,
            user_id=user_id,
            account_public_id=account_public_id,
        )
        if account is None:
            raise IbkrFlexImportError(
                "IMPORT_ACCOUNT_NOT_FOUND",
                "Import account does not exist",
                http_status=404,
            )
        staged = await stage_ibkr_flex_upload(upload, temp_root=temp_root)
        return upload_ibkr_flex_preview(
            db,
            user_id=user_id,
            account=account,
            source_timezone=source_timezone,
            staged=staged,
            idempotency_key=idempotency_key,
            provider_contract=provider_contract,
            now=now,
        )
    finally:
        try:
            remove_staged_ibkr_flex_file(staged)
        finally:
            await upload.close()
