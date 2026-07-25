"""Read-only instrument identity projection for legacy Position responses."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from app_config.release_contract import JOURNAL_BETA_CONTRACT, ReleaseContractViolation
from sqlalchemy.orm import Session

from models import AssetMaster, Position, TradingPosition
from services.legacy_truth_sync_service import (
    LegacyInstrumentIdentity,
    validate_legacy_instrument_identity,
)
from services.instrument_identity_service import (
    InstrumentIdentity,
    canonical_asset_code,
)


_JOURNAL_IDENTITY_METADATA_KEY = "journal_identity_v1"
_IDENTITY_FIELDS = frozenset(JOURNAL_BETA_CONTRACT.instruments.identity_fields)


def _enum_value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value or "")


def _asset_has_exact_identity(
    asset: AssetMaster,
    identity: LegacyInstrumentIdentity,
) -> bool:
    expected_code = canonical_asset_code(
        InstrumentIdentity(**asdict(identity))
    )
    return (
        asset.canonical_code in {identity.normalized_symbol, expected_code}
        and _enum_value(asset.asset_type) == identity.asset_type
        and _enum_value(asset.quote_currency) == identity.quote_currency
        and isinstance(asset.metadata_json, dict)
        and asset.metadata_json.get(_JOURNAL_IDENTITY_METADATA_KEY) == asdict(identity)
    )


@dataclass(frozen=True)
class PositionInstrumentProjection:
    identity: LegacyInstrumentIdentity
    name: str | None
    sector: str | None
    source: Literal[
        "CANONICAL_TRUTH",
        "EXACT_IDENTITY_PROOF",
        "VALIDATED_PREUPGRADE_TRUTH",
    ]

    def response_metadata(self) -> dict[str, str | None]:
        return {
            "symbol": self.identity.normalized_symbol,
            "name": self.name,
            "core_type": self.identity.asset_type,
            "market": self.identity.market,
            "currency": self.identity.quote_currency,
            "sector": self.sector,
            "instrument": self.identity.instrument_type,
        }


def _exact_truth_projection(
    position: Position,
    truth_position: TradingPosition | None,
) -> PositionInstrumentProjection | None:
    if truth_position is None or truth_position.instrument is None:
        return None

    instrument = truth_position.instrument
    asset = instrument.asset
    if asset is None or not isinstance(asset.metadata_json, dict):
        return None

    payload = asset.metadata_json.get(_JOURNAL_IDENTITY_METADATA_KEY)
    if not isinstance(payload, dict) or set(payload) != _IDENTITY_FIELDS:
        return None

    account = position.trading_account
    account_currency = account.currency if account is not None else truth_position.base_currency
    try:
        identity = validate_legacy_instrument_identity(
            position_asset_type=payload["asset_type"],
            account_currency=account_currency,
            symbol=payload["normalized_symbol"],
            exchange_code=payload["exchange_code"],
            metadata_core_type=payload["asset_type"],
            metadata_market=payload["market"],
            metadata_currency=payload["quote_currency"],
            metadata_instrument=payload["instrument_type"],
        )
    except (KeyError, ReleaseContractViolation):
        return None

    # Exact evidence is canonical only when every linked storage projection
    # agrees. A malformed partial upgrade falls back to validated legacy reads.
    if payload != asdict(identity):
        return None
    if not _asset_has_exact_identity(asset, identity):
        return None
    if _enum_value(instrument.instrument_type) != identity.instrument_type:
        return None
    if instrument.contract_symbol != identity.normalized_symbol:
        return None
    if _enum_value(truth_position.base_currency) != identity.quote_currency:
        return None
    if truth_position.account_id != position.account_id or truth_position.user_id != position.user_id:
        return None

    return PositionInstrumentProjection(
        identity=identity,
        name=asset.name,
        sector=asset.sector,
        source="CANONICAL_TRUTH",
    )


def project_exact_truth_instrument(
    truth_position: TradingPosition,
) -> PositionInstrumentProjection | None:
    """Return canonical identity only when the truth graph proves every field."""
    instrument = truth_position.instrument
    account = truth_position.account
    if instrument is None or account is None or account.user_id != truth_position.user_id:
        return None

    asset = instrument.asset
    if asset is None or not isinstance(asset.metadata_json, dict):
        return None

    payload = asset.metadata_json.get(_JOURNAL_IDENTITY_METADATA_KEY)
    if not isinstance(payload, dict) or set(payload) != _IDENTITY_FIELDS:
        return None

    try:
        identity = validate_legacy_instrument_identity(
            position_asset_type=payload["asset_type"],
            account_currency=account.currency,
            symbol=payload["normalized_symbol"],
            exchange_code=payload["exchange_code"],
            metadata_core_type=payload["asset_type"],
            metadata_market=payload["market"],
            metadata_currency=payload["quote_currency"],
            metadata_instrument=payload["instrument_type"],
        )
    except (KeyError, ReleaseContractViolation):
        return None

    if payload != asdict(identity):
        return None
    if not _asset_has_exact_identity(asset, identity):
        return None
    if _enum_value(instrument.instrument_type) != identity.instrument_type:
        return None
    if instrument.contract_symbol != identity.normalized_symbol:
        return None
    if _enum_value(truth_position.base_currency) != identity.quote_currency:
        return None

    return PositionInstrumentProjection(
        identity=identity,
        name=asset.name,
        sector=asset.sector,
        source="CANONICAL_TRUTH",
    )


def _validated_preupgrade_truth_projection(
    db: Session,
    position: Position,
    truth_position: TradingPosition | None,
) -> PositionInstrumentProjection | None:
    if truth_position is not None and (
        truth_position.account_id != position.account_id
        or truth_position.user_id != position.user_id
    ):
        return None

    account = position.trading_account
    if account is None:
        return None

    metadata = position.asset_metadata
    try:
        identity = validate_legacy_instrument_identity(
            position_asset_type=position.asset_type,
            account_currency=account.currency,
            symbol=position.symbol,
            exchange_code=position.exchange,
            metadata_core_type=metadata.core_type if metadata else None,
            metadata_market=metadata.market if metadata else None,
            metadata_currency=metadata.currency if metadata else None,
            metadata_instrument=metadata.instrument if metadata else None,
        )
    except ReleaseContractViolation:
        return None

    proven_asset: AssetMaster | None = None
    if truth_position is None:
        proven_asset = db.query(AssetMaster).filter(
            AssetMaster.canonical_code == identity.normalized_symbol
        ).first()
        if proven_asset is None or not _asset_has_exact_identity(proven_asset, identity):
            return None

    source_name = metadata.name if metadata else position.symbol
    source_sector = metadata.sector if metadata else None
    if proven_asset is not None:
        source_name = proven_asset.name
        source_sector = proven_asset.sector

    return PositionInstrumentProjection(
        identity=identity,
        name=source_name,
        sector=source_sector,
        source=(
            "EXACT_IDENTITY_PROOF"
            if proven_asset is not None
            else "VALIDATED_PREUPGRADE_TRUTH"
        ),
    )


def project_position_instrument(
    db: Session,
    position: Position,
    *,
    truth_position: TradingPosition | None = None,
) -> PositionInstrumentProjection | None:
    """Project response identity without creating or rewriting canonical facts."""
    return _exact_truth_projection(
        position,
        truth_position,
    ) or _validated_preupgrade_truth_projection(db, position, truth_position)
