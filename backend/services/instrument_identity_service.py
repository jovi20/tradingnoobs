"""Deterministic journal instrument identity resolution."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import AssetMaster, TradeInstrument, TradeInstrumentType


INSTRUMENT_IDENTITY_NAMESPACE = uuid.UUID(
    "9ab63b47-712e-4e5b-a16a-55aee16c9591"
)
JOURNAL_IDENTITY_METADATA_KEY = "journal_identity_v1"


@dataclass(frozen=True)
class InstrumentIdentity:
    asset_type: str
    market: str
    exchange_code: str
    normalized_symbol: str
    instrument_type: str
    quote_currency: str


def identity_payload(identity: InstrumentIdentity) -> dict[str, str]:
    return asdict(identity)


def _serialized_identity(identity: InstrumentIdentity) -> str:
    return json.dumps(
        identity_payload(identity),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def canonical_asset_code(identity: InstrumentIdentity) -> str:
    digest = hashlib.sha256(
        _serialized_identity(identity).encode("ascii")
    ).hexdigest()
    return f"JRN1:{digest}"


def _deterministic_public_id(kind: str, key: str) -> str:
    return str(uuid.uuid5(INSTRUMENT_IDENTITY_NAMESPACE, f"{kind}:{key}"))


def _asset_matches(asset: AssetMaster, identity: InstrumentIdentity) -> bool:
    return (
        asset.asset_type == identity.asset_type
        and asset.quote_currency == identity.quote_currency
        and isinstance(asset.metadata_json, dict)
        and asset.metadata_json.get(JOURNAL_IDENTITY_METADATA_KEY)
        == identity_payload(identity)
    )


def _find_compatible_legacy_asset(
    db: Session,
    *,
    identity: InstrumentIdentity,
) -> AssetMaster | None:
    candidates = db.query(AssetMaster).filter(
        AssetMaster.display_symbol == identity.normalized_symbol,
    ).order_by(AssetMaster.id.asc()).all()
    return next(
        (asset for asset in candidates if _asset_matches(asset, identity)),
        None,
    )


def get_or_create_journal_instrument(
    db: Session,
    *,
    identity: InstrumentIdentity,
    display_name: str | None = None,
) -> TradeInstrument:
    canonical_code = canonical_asset_code(identity)
    asset = db.query(AssetMaster).filter(
        AssetMaster.canonical_code == canonical_code,
    ).first()
    if asset is None:
        asset = _find_compatible_legacy_asset(db, identity=identity)
    if asset is not None and not _asset_matches(asset, identity):
        raise ValueError("INSTRUMENT_IDENTITY_CONFLICT")

    if asset is None:
        candidate = AssetMaster(
            public_id=_deterministic_public_id("asset", canonical_code),
            canonical_code=canonical_code,
            display_symbol=identity.normalized_symbol,
            name=display_name or identity.normalized_symbol,
            asset_type=identity.asset_type,
            quote_currency=identity.quote_currency,
            status="ACTIVE",
            metadata_json={
                JOURNAL_IDENTITY_METADATA_KEY: identity_payload(identity),
            },
        )
        try:
            with db.begin_nested():
                db.add(candidate)
                db.flush()
            asset = candidate
        except IntegrityError:
            asset = db.query(AssetMaster).filter(
                AssetMaster.canonical_code == canonical_code,
            ).one()
            if not _asset_matches(asset, identity):
                raise ValueError("INSTRUMENT_IDENTITY_CONFLICT") from None

    instrument_type = TradeInstrumentType(identity.instrument_type)
    instrument = db.query(TradeInstrument).filter(
        TradeInstrument.asset_id == asset.id,
        TradeInstrument.instrument_type == instrument_type,
        TradeInstrument.contract_symbol == identity.normalized_symbol,
    ).first()
    if instrument is not None:
        return instrument

    instrument_key = (
        f"{asset.public_id}:{instrument_type.value}:"
        f"{identity.normalized_symbol}"
    )
    candidate = TradeInstrument(
        public_id=_deterministic_public_id("instrument", instrument_key),
        asset_id=asset.id,
        instrument_type=instrument_type,
        display_name=display_name or asset.name,
        contract_symbol=identity.normalized_symbol,
        status="ACTIVE",
    )
    try:
        with db.begin_nested():
            db.add(candidate)
            db.flush()
        return candidate
    except IntegrityError:
        return db.query(TradeInstrument).filter(
            TradeInstrument.asset_id == asset.id,
            TradeInstrument.instrument_type == instrument_type,
            TradeInstrument.contract_symbol == identity.normalized_symbol,
        ).one()
