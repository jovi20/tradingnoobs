"""
Trading Noobs Backend - TradingPosition Truth Read Router
"""
from __future__ import annotations

from copy import deepcopy

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app_config.release_contract import (
    JOURNAL_BETA_CONTRACT,
    ReleaseContractViolation,
    release_violation_detail,
    require_release_currency,
)
from database import get_db
from models import PositionEvent, PositionEventType, User
from release_profile import RuntimeCapability
from schemas import (
    TradingPositionDividendCreate,
    TradingPositionEventNarrativeUpdate,
    TradingPositionLifecycleResponse,
    TradingPositionManualAdjustmentCreate,
    TradingPositionTradeEventCreate,
    TradingPositionTradeEventReverseCreate,
)
from services.account_ledger_service import (
    AccountingReconciliationRequiredError,
    LedgerPostingConflictError,
    sync_dividend_event_to_account_ledger,
)
from services.auth_service import get_current_user
from services.capability_service import is_effective_capability_enabled
from services.idempotency_service import begin_idempotent_request, complete_idempotent_request
from services.outbox_service import enqueue_position_event_created_outbox
from services.position_instrument_projection_service import project_exact_truth_instrument
from services.trading_position_read_service import (
    CanonicalAccountingUnresolvedError,
    build_trading_position_lifecycle_payload,
    canonical_accounting_unresolved_detail,
    require_resolved_truth_position_quantities,
    resolve_truth_position_by_public_id,
)
from services.trading_position_write_service import (
    ArchivedTradingPositionWriteError,
    SourceBoundTradeWriteError,
    TradeEventChronologyError,
    TradeEventQuantityError,
    append_truth_trade_event,
    lock_owned_truth_position,
    require_truth_position_financial_write_allowed,
    reverse_latest_truth_trade_event,
)
from services.timezone_service import LocalDateTimeError, normalize_user_datetime_to_utc

router = APIRouter(prefix="/api/trading-positions", tags=["Trading Positions"])


def _require_release_currency(value: object, *, field: str) -> str:
    try:
        return require_release_currency(value, field=field)
    except ReleaseContractViolation as violation:
        raise HTTPException(
            status_code=422,
            detail=release_violation_detail(violation),
        ) from violation


def _require_same_currency_financial_fact(
    truth_position,
    *,
    currency: object,
    fee_currency: object | None = None,
    fx_rate_to_account_ccy: object = 1,
) -> tuple[str, str | None]:
    _require_release_currency(truth_position.base_currency, field="account.currency")
    normalized_currency = _require_release_currency(currency, field="currency")
    normalized_fee_currency = None
    if fee_currency is not None:
        normalized_fee_currency = _require_release_currency(
            fee_currency,
            field="fee_currency",
        )
    if fx_rate_to_account_ccy != 1:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "UNSUPPORTED_RELEASE_FX_RATE",
                "message": "Journal Beta financial facts must already be in account currency",
                "field": "fx_rate_to_account_ccy",
            },
        )
    return normalized_currency, normalized_fee_currency


def _require_exact_truth_instrument_provenance(truth_position) -> None:
    if project_exact_truth_instrument(truth_position) is not None:
        return
    violation = ReleaseContractViolation(
        JOURNAL_BETA_CONTRACT.instruments.legacy_unproven_error,
        "trading_position.instrument",
        truth_position.public_id,
    )
    raise HTTPException(
        status_code=422,
        detail=release_violation_detail(violation),
    )


def _require_resolved_truth_accounting(truth_position) -> None:
    try:
        require_resolved_truth_position_quantities(truth_position)
    except CanonicalAccountingUnresolvedError as exc:
        raise HTTPException(
            status_code=409,
            detail=canonical_accounting_unresolved_detail(exc),
        ) from exc


def _require_financial_write_allowed(truth_position) -> None:
    try:
        require_truth_position_financial_write_allowed(truth_position)
    except ArchivedTradingPositionWriteError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={
                "code": exc.code,
                "message": str(exc),
                "position_public_id": exc.position_public_id,
            },
        ) from exc


def _lifecycle_response_content(
    db: Session,
    truth_position,
    *,
    actor_key: str,
    source: str = "DERIVED",
    include_ai_sidecar: bool | None = None,
) -> dict:
    if include_ai_sidecar is None:
        include_ai_sidecar = is_effective_capability_enabled(
            db,
            RuntimeCapability.AI_INSIGHTS,
            actor_key=actor_key,
        )
    try:
        data = build_trading_position_lifecycle_payload(
            db,
            truth_position,
            include_ai_sidecar=include_ai_sidecar,
        )
    except CanonicalAccountingUnresolvedError as exc:
        raise HTTPException(
            status_code=409,
            detail=canonical_accounting_unresolved_detail(exc),
        ) from exc
    return {
        "data": data,
        "meta": {
            "as_of": truth_position.updated_at or truth_position.created_at,
            "generated_at": truth_position.updated_at or truth_position.created_at,
            "freshness": "FRESH",
            "source": source,
            "maturity": "EARLY_SIGNAL",
            "value_status": "FINAL",
        },
    }


def _lifecycle_response(
    db: Session,
    truth_position,
    *,
    actor_key: str,
    source: str = "DERIVED",
    status_code: int = 200,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(
            _lifecycle_response_content(
                db,
                truth_position,
                actor_key=actor_key,
                source=source,
            )
        ),
    )


def _begin_idempotent_lifecycle_write(
    db: Session,
    *,
    scope: str,
    idempotency_key: str | None,
    current_user: User,
    position_public_id: str,
    payload,
    structured_errors: bool = False,
) -> tuple[object | None, JSONResponse | None]:
    if idempotency_key is None:
        return None, None
    normalized_key = idempotency_key.strip()
    if not normalized_key:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "IDEMPOTENCY_KEY_REQUIRED",
                "message": "Idempotency-Key must not be blank",
            },
        )

    try:
        idempotency_begin = begin_idempotent_request(
            db,
            scope=scope,
            key=normalized_key,
            request_payload={
                "position_public_id": position_public_id,
                "payload": jsonable_encoder(payload),
            },
            user_id=current_user.id,
            ttl_seconds=None,
        )
    except (
        AccountingReconciliationRequiredError,
        LedgerPostingConflictError,
    ) as exc:
        db.rollback()
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    except ValueError as exc:
        db.rollback()
        if not structured_errors:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        raise HTTPException(
            status_code=409,
            detail={
                "code": "IDEMPOTENCY_KEY_REUSED",
                "message": str(exc),
            },
        ) from exc

    record = idempotency_begin.record
    if idempotency_begin.created:
        return record, None

    if record.status == "COMPLETED" and record.response_json is not None:
        response_json = deepcopy(record.response_json)
        if not is_effective_capability_enabled(
            db,
            RuntimeCapability.AI_INSIGHTS,
            actor_key=current_user.public_id,
        ):
            ai_sidecar = response_json.get("data", {}).get("ai_sidecar")
            if isinstance(ai_sidecar, dict):
                ai_sidecar["items"] = []
        return record, JSONResponse(
            status_code=201,
            content=jsonable_encoder(response_json),
        )

    detail = (
        {
            "code": "IDEMPOTENCY_REQUEST_IN_PROGRESS",
            "message": "Idempotent request is already in progress",
        }
        if structured_errors
        else "Idempotent request is already in progress."
    )
    raise HTTPException(status_code=409, detail=detail)


def _complete_idempotent_lifecycle_write(
    db: Session,
    *,
    record,
    response_content: dict,
    source_fact_public_id: str | None = None,
) -> None:
    if record is None:
        return
    complete_idempotent_request(
        db,
        record=record,
        response_json=jsonable_encoder(response_content),
        source_fact_public_id=source_fact_public_id,
    )


@router.get("/{position_public_id}/lifecycle", response_model=TradingPositionLifecycleResponse)
def get_trading_position_lifecycle(
    position_public_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    truth_position = resolve_truth_position_by_public_id(db, current_user.id, position_public_id)
    if not truth_position:
        raise HTTPException(status_code=404, detail="Trading position not found")

    return _lifecycle_response(
        db,
        truth_position,
        actor_key=current_user.public_id,
    )


@router.patch(
    "/{position_public_id}/events/{event_public_id}",
    response_model=TradingPositionLifecycleResponse,
    include_in_schema=False,
)
@router.patch(
    "/{position_public_id}/events/{event_public_id}/narrative",
    response_model=TradingPositionLifecycleResponse,
)
def update_trading_position_event_narrative(
    position_public_id: str,
    event_public_id: str,
    payload: TradingPositionEventNarrativeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    truth_position = resolve_truth_position_by_public_id(db, current_user.id, position_public_id)
    if not truth_position:
        raise HTTPException(status_code=404, detail="Trading position not found")

    event = db.query(PositionEvent).filter(
        PositionEvent.public_id == event_public_id,
        PositionEvent.position_id == truth_position.id,
        PositionEvent.user_id == current_user.id,
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Position event not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(event, key, value)
    event.input_source = "MANUAL"

    db.commit()

    updated_position = resolve_truth_position_by_public_id(db, current_user.id, position_public_id)
    return _lifecycle_response(
        db,
        updated_position,
        actor_key=current_user.public_id,
        source="MANUAL",
    )


@router.post(
    "/{position_public_id}/events",
    status_code=201,
    response_model=TradingPositionLifecycleResponse,
)
def create_trading_position_trade_event(
    position_public_id: str,
    payload: TradingPositionTradeEventCreate,
    idempotency_key: str = Header(
        ...,
        alias="Idempotency-Key",
        min_length=1,
        max_length=255,
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        occurred_at = normalize_user_datetime_to_utc(
            payload.occurred_at,
            timezone_name=current_user.timezone,
        )
        locked = lock_owned_truth_position(
            db,
            user_id=current_user.id,
            position_public_id=position_public_id,
        )
        if locked is None:
            raise HTTPException(status_code=404, detail="Trading position not found")
        account, truth_position = locked

        normalized_payload = {
            **payload.model_dump(),
            "occurred_at": occurred_at,
        }
        idempotency_record, replay_response = _begin_idempotent_lifecycle_write(
            db,
            scope="POSITION_LIFECYCLE_APPEND",
            idempotency_key=idempotency_key,
            current_user=current_user,
            position_public_id=position_public_id,
            payload=normalized_payload,
            structured_errors=True,
        )
        if replay_response is not None:
            db.rollback()
            return replay_response

        _require_financial_write_allowed(truth_position)
        _require_exact_truth_instrument_provenance(truth_position)
        _require_resolved_truth_accounting(truth_position)
        currency, fee_currency = _require_same_currency_financial_fact(
            truth_position,
            currency=payload.currency,
            fee_currency=payload.fee_currency,
            fx_rate_to_account_ccy=payload.fx_rate_to_account_ccy,
        )

        event = append_truth_trade_event(
            db,
            position=truth_position,
            account=account,
            event_type=PositionEventType(payload.event_type.value),
            quantity=payload.quantity,
            price=payload.price,
            currency=currency,
            occurred_at=occurred_at,
            fee_amount=payload.fee_amount,
            fee_currency=fee_currency,
            fx_rate_to_account_ccy=payload.fx_rate_to_account_ccy,
            reason=payload.reason,
            emotion=payload.emotion,
            confidence=payload.confidence,
            note=payload.note,
        )
        enqueue_position_event_created_outbox(db, position=truth_position, event=event)
        db.flush()
        db.expire_all()
        updated_position = resolve_truth_position_by_public_id(
            db,
            current_user.id,
            position_public_id,
        )
        response_content = _lifecycle_response_content(
            db,
            updated_position,
            actor_key=current_user.public_id,
            source="MANUAL",
            include_ai_sidecar=False,
        )
        _complete_idempotent_lifecycle_write(
            db,
            record=idempotency_record,
            response_content=response_content,
            source_fact_public_id=event.public_id,
        )
        db.commit()
        return JSONResponse(status_code=201, content=jsonable_encoder(response_content))
    except HTTPException:
        db.rollback()
        raise
    except LocalDateTimeError as exc:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    except ArchivedTradingPositionWriteError as exc:
        db.rollback()
        raise HTTPException(
            status_code=exc.http_status,
            detail={
                "code": exc.code,
                "message": str(exc),
                "position_public_id": exc.position_public_id,
            },
        ) from exc
    except (
        AccountingReconciliationRequiredError,
        LedgerPostingConflictError,
        SourceBoundTradeWriteError,
        TradeEventChronologyError,
        TradeEventQuantityError,
    ) as exc:
        db.rollback()
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise


@router.post("/{position_public_id}/events/{event_public_id}/reverse", status_code=201)
def reverse_trading_position_trade_event(
    position_public_id: str,
    event_public_id: str,
    payload: TradingPositionTradeEventReverseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    locked = lock_owned_truth_position(
        db,
        user_id=current_user.id,
        position_public_id=position_public_id,
    )
    if locked is None:
        raise HTTPException(status_code=404, detail="Trading position not found")
    _, truth_position = locked

    _require_financial_write_allowed(truth_position)
    _require_exact_truth_instrument_provenance(truth_position)
    _require_resolved_truth_accounting(truth_position)

    event = db.query(PositionEvent).filter(
        PositionEvent.public_id == event_public_id,
        PositionEvent.position_id == truth_position.id,
        PositionEvent.user_id == current_user.id,
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Position event not found")

    try:
        reversal_event = reverse_latest_truth_trade_event(
            db,
            position=truth_position,
            event=event,
            occurred_at=payload.occurred_at,
            note=payload.note,
        )
        enqueue_position_event_created_outbox(db, position=truth_position, event=reversal_event)
    except ArchivedTradingPositionWriteError as exc:
        db.rollback()
        raise HTTPException(
            status_code=exc.http_status,
            detail={
                "code": exc.code,
                "message": str(exc),
                "position_public_id": exc.position_public_id,
            },
        ) from exc
    except (
        AccountingReconciliationRequiredError,
        LedgerPostingConflictError,
    ) as exc:
        db.rollback()
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()

    updated_position = resolve_truth_position_by_public_id(db, current_user.id, position_public_id)
    return _lifecycle_response(
        db,
        updated_position,
        actor_key=current_user.public_id,
        source="MANUAL",
        status_code=201,
    )


@router.post("/{position_public_id}/dividends", status_code=201)
def create_trading_position_dividend(
    position_public_id: str,
    payload: TradingPositionDividendCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    truth_position = resolve_truth_position_by_public_id(db, current_user.id, position_public_id)
    if not truth_position:
        raise HTTPException(status_code=404, detail="Trading position not found")

    _require_financial_write_allowed(truth_position)
    _require_exact_truth_instrument_provenance(truth_position)
    _require_resolved_truth_accounting(truth_position)

    currency, _ = _require_same_currency_financial_fact(
        truth_position,
        currency=payload.currency,
        fx_rate_to_account_ccy=payload.fx_rate_to_account_ccy,
    )

    idempotency_record, replay_response = _begin_idempotent_lifecycle_write(
        db,
        scope="trading_position.dividend.create",
        idempotency_key=idempotency_key,
        current_user=current_user,
        position_public_id=position_public_id,
        payload=payload,
    )
    if replay_response is not None:
        return replay_response

    event = PositionEvent(
        user_id=current_user.id,
        position_id=truth_position.id,
        account_id=truth_position.account_id,
        instrument_id=truth_position.instrument_id,
        event_type=PositionEventType.DIVIDEND,
        event_time=payload.occurred_at,
        currency=currency,
        gross_amount=payload.amount,
        fx_rate_to_account_ccy=payload.fx_rate_to_account_ccy,
        input_source="MANUAL",
        note=payload.note,
    )
    db.add(event)
    db.flush()
    try:
        sync_dividend_event_to_account_ledger(db, event=event)
    except (
        AccountingReconciliationRequiredError,
        LedgerPostingConflictError,
    ) as exc:
        db.rollback()
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    enqueue_position_event_created_outbox(db, position=truth_position, event=event)

    db.flush()
    db.expire_all()
    updated_position = resolve_truth_position_by_public_id(db, current_user.id, position_public_id)
    response_content = _lifecycle_response_content(
        db,
        updated_position,
        actor_key=current_user.public_id,
        source="MANUAL",
        include_ai_sidecar=False,
    )
    _complete_idempotent_lifecycle_write(db, record=idempotency_record, response_content=response_content)
    db.commit()
    return JSONResponse(status_code=201, content=jsonable_encoder(response_content))


@router.post(
    "/{position_public_id}/adjustments",
    status_code=201,
    include_in_schema=False,
)
def create_trading_position_manual_adjustment(
    position_public_id: str,
    payload: TradingPositionManualAdjustmentCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    truth_position = resolve_truth_position_by_public_id(db, current_user.id, position_public_id)
    if not truth_position:
        raise HTTPException(status_code=404, detail="Trading position not found")

    raise HTTPException(
        status_code=422,
        detail={
            "code": "UNSUPPORTED_EVENT_TYPE",
            "message": "Manual adjustments are outside the trading-journal Beta contract",
            "field": "event_type",
        },
    )
