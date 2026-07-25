"""One-time generic bootstrap confirm and canonical replay."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from models import (
    AccountingHealth,
    AccountLedgerEntry,
    ImportAdapterKind,
    IdempotencyKey,
    ImportRow,
    ImportSession,
    ImportSessionStatus,
    LedgerPostingKind,
    Position,
    PositionEvent,
    PositionEventType,
    TradeSourceState,
    TradingAccount,
    TradingPosition,
    TradingPositionSide,
    Transaction,
)
from services.generic_import_service import (
    GenericImportError,
    _as_utc,
    _idempotency_key_hash,
    expire_session_if_due,
    normalize_import_row,
    transition_import_session,
    utc_now,
)
from services.idempotency_service import (
    begin_idempotent_request,
    complete_idempotent_request,
    request_hash,
)
from services.instrument_identity_service import InstrumentIdentity
from services.outbox_service import enqueue_position_event_created_outbox
from services.trading_position_write_service import append_truth_trade_event
from services.truth_native_open_service import create_truth_native_open


CONFIRM_SCOPE = "GENERIC_IMPORT_CONFIRM_V1"
ALLOWED_BOOTSTRAP_LEDGER_KINDS = frozenset(
    {LedgerPostingKind.OPENING_BALANCE.value}
)


@dataclass(frozen=True)
class ConfirmCommandResult:
    body: dict[str, Any]
    http_status: int
    replayed: bool


def _enum_value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _confirm_error(code: str, message: str, *, status: int = 422) -> None:
    raise GenericImportError(code, message, http_status=status)


def _require_generic_bootstrap_eligible(
    db: Session,
    *,
    account: TradingAccount,
) -> None:
    if not account.is_active:
        _confirm_error("ACCOUNT_ARCHIVED", "Archived accounts are read-only", status=409)
    if _enum_value(account.accounting_health) != AccountingHealth.HEALTHY.value:
        _confirm_error(
            "ACCOUNTING_RECONCILIATION_REQUIRED",
            "Account accounting must be healthy before bootstrap import",
            status=409,
        )
    if _enum_value(account.trade_source_state) != TradeSourceState.CLEAN.value:
        _confirm_error(
            "GENERIC_BOOTSTRAP_NOT_ELIGIBLE",
            "Generic bootstrap requires a CLEAN account",
            status=409,
        )
    if db.query(TradingPosition.id).filter(
        TradingPosition.user_id == account.user_id,
        TradingPosition.account_id == account.id,
    ).first() is not None:
        _confirm_error(
            "GENERIC_BOOTSTRAP_NOT_ELIGIBLE",
            "Account already has canonical trade history",
            status=409,
        )
    if db.query(Position.id).filter(
        Position.user_id == account.user_id,
        Position.account_id == account.id,
    ).first() is not None:
        _confirm_error(
            "GENERIC_BOOTSTRAP_NOT_ELIGIBLE",
            "Account already has legacy trade history",
            status=409,
        )
    if db.query(PositionEvent.id).filter(
        PositionEvent.user_id == account.user_id,
        PositionEvent.account_id == account.id,
    ).first() is not None:
        _confirm_error(
            "GENERIC_BOOTSTRAP_NOT_ELIGIBLE",
            "Account already has canonical event history",
            status=409,
        )
    if db.query(Transaction.id).filter(
        Transaction.account_id == account.id,
    ).first() is not None:
        _confirm_error(
            "GENERIC_BOOTSTRAP_NOT_ELIGIBLE",
            "Account already has cash transaction history",
            status=409,
        )
    disallowed_posting = db.query(AccountLedgerEntry.id).filter(
        AccountLedgerEntry.user_id == account.user_id,
        AccountLedgerEntry.account_id == account.id,
        AccountLedgerEntry.posting_kind.notin_(
            tuple(ALLOWED_BOOTSTRAP_LEDGER_KINDS)
        ),
    ).first()
    if disallowed_posting is not None:
        _confirm_error(
            "GENERIC_BOOTSTRAP_NOT_ELIGIBLE",
            "Account has non-opening-balance financial history",
            status=409,
        )


def _identity(values: dict[str, Any]) -> InstrumentIdentity:
    return InstrumentIdentity(
        asset_type=str(values["asset_type"]),
        market=str(values["market"]),
        exchange_code=str(values["exchange_code"]),
        normalized_symbol=str(values["symbol"]),
        instrument_type=str(values["instrument_type"]),
        quote_currency=str(values["currency"]),
    )


def _group_key(values: dict[str, Any]) -> tuple[str, ...]:
    identity = _identity(values)
    return (
        identity.asset_type,
        identity.market,
        identity.exchange_code,
        identity.normalized_symbol,
        identity.instrument_type,
        identity.quote_currency,
        str(values["direction"]),
    )


def _normalized_for_digest(values: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in values.items()
        if key != "instrument_resolution"
    }


def _selected_rows(
    db: Session,
    *,
    session: ImportSession,
    selected_row_public_ids: list[str],
    account: TradingAccount,
    timezone_name: str,
) -> list[tuple[ImportRow, dict[str, Any]]]:
    if len(selected_row_public_ids) != len(set(selected_row_public_ids)):
        _confirm_error(
            "DUPLICATE_IMPORT_ROW_SELECTION",
            "Each import row may be selected at most once",
        )
    if not selected_row_public_ids:
        return []

    rows = (
        db.query(ImportRow)
        .filter(
            ImportRow.session_id == session.id,
            ImportRow.user_id == session.user_id,
            ImportRow.account_id == session.account_id,
            ImportRow.public_id.in_(selected_row_public_ids),
        )
        .order_by(ImportRow.row_number.asc())
        .all()
    )
    if len(rows) != len(selected_row_public_ids):
        _confirm_error(
            "IMPORT_ROW_NOT_FOUND",
            "One or more selected rows do not belong to this import session",
            status=404,
        )

    refreshed: list[tuple[ImportRow, dict[str, Any]]] = []
    for row in rows:
        if row.applied_event_public_id is not None:
            _confirm_error(
                "IMPORT_ROW_ALREADY_APPLIED",
                "An import row has already been applied",
                status=409,
            )
        normalized, errors, _warnings = normalize_import_row(
            db,
            raw_values=row.raw_values_json or {},
            account=account,
            timezone_name=timezone_name,
        )
        if errors or not row.is_valid:
            _confirm_error(
                "IMPORT_ROW_INVALID",
                f"Selected row {row.row_number} is not valid",
            )
        if _normalized_for_digest(normalized) != _normalized_for_digest(
            row.normalized_values_json or {}
        ):
            _confirm_error(
                "STALE_IMPORT_PREVIEW",
                f"Selected row {row.row_number} no longer matches its preview",
                status=409,
            )
        refreshed.append((row, normalized))
    return refreshed


def _validate_lifecycle_prefixes(
    selected: list[tuple[ImportRow, dict[str, Any]]],
) -> list[tuple[ImportRow, dict[str, Any]]]:
    grouped: dict[tuple[str, ...], list[tuple[ImportRow, dict[str, Any]]]] = (
        defaultdict(list)
    )
    for item in selected:
        grouped[_group_key(item[1])].append(item)

    ordered: list[tuple[ImportRow, dict[str, Any]]] = []
    for key in sorted(grouped):
        group = sorted(
            grouped[key],
            key=lambda item: (
                str(item[1]["occurred_at"]),
                item[0].row_number,
            ),
        )
        open_quantity = Decimal("0")
        for row, values in group:
            action = str(values["action"])
            quantity = Decimal(str(values["quantity"]))
            if action == "OPEN":
                if open_quantity != 0:
                    _confirm_error(
                        "IMPORT_LIFECYCLE_OPEN_CONFLICT",
                        f"Row {row.row_number} opens an already-open lifecycle",
                    )
                open_quantity = quantity
            elif action == "ADD":
                if open_quantity <= 0:
                    _confirm_error(
                        "IMPORT_LIFECYCLE_ORPHAN_EVENT",
                        f"Row {row.row_number} has ADD without an open lifecycle",
                    )
                open_quantity += quantity
            elif action == "REDUCE":
                if open_quantity <= 0:
                    _confirm_error(
                        "IMPORT_LIFECYCLE_ORPHAN_EVENT",
                        f"Row {row.row_number} has REDUCE without an open lifecycle",
                    )
                if quantity >= open_quantity:
                    _confirm_error(
                        "IMPORT_LIFECYCLE_OVER_REDUCE",
                        f"Row {row.row_number} REDUCE must leave positive quantity",
                    )
                open_quantity -= quantity
            elif action == "CLOSE":
                if open_quantity <= 0:
                    _confirm_error(
                        "IMPORT_LIFECYCLE_ORPHAN_EVENT",
                        f"Row {row.row_number} has CLOSE without an open lifecycle",
                    )
                if quantity != open_quantity:
                    _confirm_error(
                        "IMPORT_LIFECYCLE_CLOSE_QUANTITY_MISMATCH",
                        f"Row {row.row_number} CLOSE must consume the full quantity",
                    )
                open_quantity = Decimal("0")
            else:
                _confirm_error(
                    "UNSUPPORTED_IMPORT_ACTION",
                    f"Row {row.row_number} has an unsupported lifecycle action",
                )
        ordered.extend(group)
    return ordered


def _terminal_replay(
    db: Session,
    *,
    session: ImportSession,
    key_hash: str,
    request_payload: dict[str, Any],
) -> ConfirmCommandResult | None:
    if session.confirm_idempotency_id is None:
        return None
    record = db.query(IdempotencyKey).filter(
        IdempotencyKey.id == session.confirm_idempotency_id,
        IdempotencyKey.user_id == session.user_id,
        IdempotencyKey.scope == CONFIRM_SCOPE,
    ).first()
    if (
        record is None
        or record.key != key_hash
        or record.request_hash != request_hash(request_payload)
    ):
        _confirm_error(
            "IMPORT_SESSION_ALREADY_CONSUMED",
            "Import session was already consumed by another confirm request",
            status=409,
        )
    if record.status != "COMPLETED" or not isinstance(record.response_json, dict):
        _confirm_error(
            "IDEMPOTENCY_REQUEST_IN_PROGRESS",
            "Import confirm is already in progress",
            status=409,
        )
    return ConfirmCommandResult(
        body=record.response_json,
        http_status=200,
        replayed=True,
    )


def confirm_generic_bootstrap(
    db: Session,
    *,
    user_id: int,
    timezone_name: str,
    session_public_id: str,
    selected_row_public_ids: list[str],
    idempotency_key: str | None,
    now: datetime | None = None,
) -> ConfirmCommandResult:
    now = _as_utc(now or utc_now())
    normalized_selection = sorted(selected_row_public_ids)
    request_payload = {
        "session_public_id": session_public_id,
        "selected_row_public_ids": normalized_selection,
    }

    session = (
        db.query(ImportSession)
        .filter(
            ImportSession.public_id == session_public_id,
            ImportSession.user_id == user_id,
            ImportSession.adapter_kind
            == ImportAdapterKind.GENERIC_BOOTSTRAP.value,
        )
        .first()
    )
    if session is None:
        _confirm_error(
            "IMPORT_SESSION_NOT_FOUND",
            "Import session not found",
            status=404,
        )
    key_hash = _idempotency_key_hash(idempotency_key)

    replay = _terminal_replay(
        db,
        session=session,
        key_hash=key_hash,
        request_payload=request_payload,
    )
    if replay is not None:
        return replay

    account = (
        db.query(TradingAccount)
        .filter(
            TradingAccount.id == session.account_id,
            TradingAccount.user_id == user_id,
        )
        .populate_existing()
        .with_for_update()
        .one()
    )
    session = (
        db.query(ImportSession)
        .filter(
            ImportSession.id == session.id,
            ImportSession.user_id == user_id,
            ImportSession.account_id == account.id,
            ImportSession.adapter_kind
            == ImportAdapterKind.GENERIC_BOOTSTRAP.value,
        )
        .populate_existing()
        .with_for_update()
        .one()
    )
    replay = _terminal_replay(
        db,
        session=session,
        key_hash=key_hash,
        request_payload=request_payload,
    )
    if replay is not None:
        return replay
    if expire_session_if_due(db, session=session, now=now):
        _confirm_error(
            "IMPORT_SESSION_EXPIRED",
            "Import preview session has expired",
            status=410,
        )
    if session.status != ImportSessionStatus.PREVIEW_READY.value:
        _confirm_error(
            "IMPORT_SESSION_STATE_CONFLICT",
            "Import session is not ready for confirm",
            status=409,
        )
    _require_generic_bootstrap_eligible(db, account=account)
    selected = _selected_rows(
        db,
        session=session,
        selected_row_public_ids=selected_row_public_ids,
        account=account,
        timezone_name=timezone_name,
    )
    ordered = _validate_lifecycle_prefixes(selected)

    try:
        command = begin_idempotent_request(
            db,
            scope=CONFIRM_SCOPE,
            key=key_hash,
            request_payload=request_payload,
            user_id=user_id,
            ttl_seconds=None,
            now=now,
        )
    except ValueError as exc:
        _confirm_error("IDEMPOTENCY_KEY_REUSED", str(exc), status=409)
    if not command.created:
        _confirm_error(
            "IMPORT_SESSION_ALREADY_CONSUMED",
            "Confirm idempotency belongs to another consumed session",
            status=409,
        )
    session.confirm_idempotency_id = command.record.id
    transition_import_session(
        db,
        session=session,
        from_status=ImportSessionStatus.PREVIEW_READY.value,
        to_status=ImportSessionStatus.CONFIRMING.value,
        now=now,
    )

    position_ids: list[str] = []
    event_ids: list[str] = []
    current_positions: dict[tuple[str, ...], TradingPosition] = {}
    for row, values in ordered:
        key = _group_key(values)
        action = PositionEventType(str(values["action"]))
        quantity = Decimal(str(values["quantity"]))
        price = Decimal(str(values["price"]))
        fee_amount = Decimal(str(values.get("commission") or "0"))
        occurred_at = datetime.fromisoformat(
            str(values["occurred_at"]).replace("Z", "+00:00")
        ).astimezone(timezone.utc)
        if action == PositionEventType.OPEN:
            _legacy, position, event = create_truth_native_open(
                db,
                user_id=user_id,
                account=account,
                strategy=None,
                identity=_identity(values),
                side=TradingPositionSide(str(values["direction"])),
                quantity=quantity,
                price=price,
                occurred_at=occurred_at,
                fee_amount=fee_amount,
                reason=values.get("reason"),
            )
            current_positions[key] = position
            position_ids.append(position.public_id)
        else:
            position = current_positions[key]
            event = append_truth_trade_event(
                db,
                position=position,
                account=account,
                event_type=action,
                quantity=quantity,
                price=price,
                currency=str(values["currency"]),
                occurred_at=occurred_at,
                fee_amount=fee_amount,
                fee_currency=str(values["fee_currency"]),
                reason=values.get("reason"),
                note=values.get("note"),
            )
            enqueue_position_event_created_outbox(
                db,
                position=position,
                event=event,
            )
            if action == PositionEventType.CLOSE:
                del current_positions[key]
        event.input_source = ImportAdapterKind.GENERIC_BOOTSTRAP.value
        row.applied_position_public_id = position.public_id
        row.applied_event_public_id = event.public_id
        event_ids.append(event.public_id)

    db.flush()
    postings = (
        db.query(AccountLedgerEntry)
        .join(PositionEvent, AccountLedgerEntry.position_event_id == PositionEvent.id)
        .filter(
            PositionEvent.public_id.in_(event_ids),
            PositionEvent.user_id == user_id,
            PositionEvent.account_id == account.id,
        )
        .order_by(AccountLedgerEntry.id.asc())
        .all()
        if event_ids
        else []
    )
    status = (
        ImportSessionStatus.COMPLETED.value
        if ordered
        else ImportSessionStatus.COMPLETED_NOOP.value
    )
    if ordered:
        account.trade_source_state = TradeSourceState.MANUAL.value
        account.hard_delete_eligible = False

    body = {
        "schema_version": 1,
        "session_public_id": session.public_id,
        "account_public_id": account.public_id,
        "status": status,
        "selected_row_count": len(ordered),
        "position_count": len(position_ids),
        "event_count": len(event_ids),
        "posting_count": len(postings),
        "source_ids": {
            "position_public_ids": position_ids,
            "event_public_ids": event_ids,
            "posting_public_ids": [posting.public_id for posting in postings],
        },
    }
    complete_idempotent_request(
        db,
        record=command.record,
        response_json=body,
        source_fact_public_id=session.public_id,
        now=now,
    )
    transition_import_session(
        db,
        session=session,
        from_status=ImportSessionStatus.CONFIRMING.value,
        to_status=status,
        now=now,
    )
    db.commit()
    return ConfirmCommandResult(body=body, http_status=200, replayed=False)
