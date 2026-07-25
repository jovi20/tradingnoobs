"""Owner-bound persistent generic import upload and preview routes."""
from __future__ import annotations

import csv
import io

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    UploadFile,
)
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from app_config.ibkr_flex_provider_evidence import (
    IbkrProviderEvidenceError,
    require_verified_ibkr_flex_provider_contract,
)
from database import get_db
from models import ImportSessionStatus, User
from routers.auth import get_current_user
from schemas import (
    ImportConfirmRequest,
    ImportConfirmResponse,
    ImportSessionResponse,
)
from services.financial_command_service import lock_owned_account
from services.generic_import_service import (
    GenericImportError,
    expire_session_if_due,
    get_owned_import_session,
    remove_staged_import_file,
    serialize_import_session,
    stage_import_upload,
    upload_preview,
)
from services.generic_import_confirm_service import confirm_generic_bootstrap
from services.ibkr_flex_import_service import (
    IbkrFlexImportError,
    stage_and_upload_ibkr_flex_preview,
)


router = APIRouter(prefix="/api/positions/import", tags=["position-import"])


def _import_error(exc: GenericImportError) -> HTTPException:
    return HTTPException(
        status_code=exc.http_status,
        detail={"code": exc.code, "message": str(exc)},
    )


def _ibkr_import_error(exc: IbkrFlexImportError) -> HTTPException:
    headers = None
    if exc.retry_after_seconds is not None:
        headers = {"Retry-After": str(exc.retry_after_seconds)}
    return HTTPException(
        status_code=exc.http_status,
        detail={"code": exc.code, "message": str(exc)},
        headers=headers,
    )


@router.post(
    "/confirm",
    response_model=ImportConfirmResponse,
)
async def confirm_generic_import(
    payload: ImportConfirmRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = confirm_generic_bootstrap(
            db,
            user_id=current_user.id,
            timezone_name=current_user.timezone,
            session_public_id=payload.session_public_id,
            selected_row_public_ids=payload.selected_row_public_ids,
            idempotency_key=idempotency_key,
        )
        return JSONResponse(status_code=result.http_status, content=result.body)
    except GenericImportError as exc:
        db.rollback()
        raise _import_error(exc) from exc
    except BaseException:
        db.rollback()
        raise


@router.post(
    "/upload",
    response_model=ImportSessionResponse,
    status_code=201,
)
async def upload_generic_import(
    account_id: str = Form(...),
    adapter_kind: str = Form(default="GENERIC_BOOTSTRAP"),
    file: UploadFile = File(...),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if adapter_kind != "GENERIC_BOOTSTRAP":
        await file.close()
        raise HTTPException(
            status_code=422,
            detail={
                "code": "UNSUPPORTED_IMPORT_ADAPTER",
                "message": "This endpoint only accepts GENERIC_BOOTSTRAP",
            },
        )

    staged = None
    try:
        staged = await stage_import_upload(file)
        account = lock_owned_account(
            db,
            user_id=current_user.id,
            account_public_id=account_id,
        )
        if account is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="Account not found")
        result = upload_preview(
            db,
            user_id=current_user.id,
            timezone_name=current_user.timezone,
            account=account,
            staged=staged,
            idempotency_key=idempotency_key,
        )
        return JSONResponse(status_code=result.http_status, content=result.body)
    except GenericImportError as exc:
        db.rollback()
        raise _import_error(exc) from exc
    except HTTPException:
        raise
    except BaseException:
        db.rollback()
        raise
    finally:
        remove_staged_import_file(staged)
        await file.close()


@router.post(
    "/ibkr-flex/upload",
    response_model=ImportSessionResponse,
    status_code=201,
)
async def upload_ibkr_flex_import(
    account_id: str = Form(...),
    source_timezone: str = Form(...),
    file: UploadFile = File(...),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        provider_contract = require_verified_ibkr_flex_provider_contract()
    except IbkrProviderEvidenceError as exc:
        await file.close()
        raise HTTPException(
            status_code=404,
            detail={
                "code": "FEATURE_DISABLED",
                "message": (
                    "IBKR Flex file import is unavailable until its provider "
                    "contract is verified"
                ),
            },
        ) from exc

    try:
        result = await stage_and_upload_ibkr_flex_preview(
            db,
            user_id=current_user.id,
            account_public_id=account_id,
            source_timezone=source_timezone,
            upload=file,
            idempotency_key=idempotency_key,
            provider_contract=provider_contract,
        )
        return JSONResponse(status_code=result.http_status, content=result.body)
    except IbkrFlexImportError as exc:
        db.rollback()
        raise _ibkr_import_error(exc) from exc
    except BaseException:
        db.rollback()
        raise


@router.get(
    "/sessions/{session_public_id}",
    response_model=ImportSessionResponse,
    response_model_exclude_unset=True,
)
async def get_generic_import_session(
    session_public_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = get_owned_import_session(
        db,
        user_id=current_user.id,
        session_public_id=session_public_id,
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Import session not found")
    if expire_session_if_due(db, session=session):
        raise HTTPException(
            status_code=410,
            detail={
                "code": "IMPORT_SESSION_EXPIRED",
                "message": "Import preview session has expired",
            },
        )
    include_rows = session.status in {
        ImportSessionStatus.PREVIEW_READY.value,
        ImportSessionStatus.CONFLICTED.value,
    }
    return serialize_import_session(
        db,
        session=session,
        include_rows=include_rows,
    )


@router.get("/template")
async def download_generic_import_template():
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        (
            "asset_type",
            "market",
            "exchange_code",
            "symbol",
            "instrument_type",
            "direction",
            "action",
            "timestamp",
            "price",
            "quantity",
            "currency",
            "commission",
            "fee_currency",
            "reason",
            "note",
        )
    )
    payload = io.BytesIO(buffer.getvalue().encode("utf-8"))
    return StreamingResponse(
        payload,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                'attachment; filename="trading-journal-import-template.csv"'
            )
        },
    )
