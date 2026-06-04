from models import AssetMaster, MarketDataCoverage, ProviderSymbolMapping, TradeInstrument
from services.identity_service import generate_public_id


class MarketOrchestrationService:
    def __init__(self, db_session):
        self.db = db_session

    def resolve_symbol_mapping(
        self,
        *,
        asset_symbol: str,
        provider_key: str,
        provider_symbol: str,
        provider_market: str,
        capabilities: dict,
    ) -> ProviderSymbolMapping:
        normalized_asset_symbol = asset_symbol.strip().upper()
        normalized_provider_symbol = provider_symbol.strip().upper()
        asset = self._get_or_create_asset(normalized_asset_symbol)
        instrument = self._get_or_create_instrument(asset=asset, symbol=normalized_asset_symbol, provider_market=provider_market)

        mapping = self.db.query(ProviderSymbolMapping).filter_by(
            provider_key=provider_key,
            provider_symbol=normalized_provider_symbol,
        ).one_or_none()
        if not mapping:
            mapping = ProviderSymbolMapping(
                public_id=generate_public_id(),
                asset_id=asset.id,
                instrument_id=instrument.id,
                provider_key=provider_key,
                provider_symbol=normalized_provider_symbol,
                provider_market=provider_market,
                capabilities_json=capabilities,
                quality_status="ACTIVE",
            )
            self.db.add(mapping)
            self.db.flush()
        else:
            mapping.asset_id = asset.id
            mapping.instrument_id = instrument.id
            mapping.provider_market = provider_market
            mapping.capabilities_json = capabilities
            mapping.quality_status = "ACTIVE"

        for capability, enabled in capabilities.items():
            if enabled and not self.db.query(MarketDataCoverage).filter_by(
                provider_symbol_mapping_id=mapping.id,
                capability=capability,
            ).one_or_none():
                self.db.add(
                    MarketDataCoverage(
                        public_id=generate_public_id(),
                        provider_symbol_mapping_id=mapping.id,
                        capability=capability,
                        quality_status="ACTIVE",
                    )
                )
        self.db.flush()
        return mapping

    def _get_or_create_asset(self, symbol: str) -> AssetMaster:
        asset = self.db.query(AssetMaster).filter_by(symbol=symbol).one_or_none()
        if asset:
            return asset
        asset = AssetMaster(public_id=generate_public_id(), symbol=symbol, name=symbol)
        self.db.add(asset)
        self.db.flush()
        return asset

    def _get_or_create_instrument(self, *, asset: AssetMaster, symbol: str, provider_market: str) -> TradeInstrument:
        instrument = self.db.query(TradeInstrument).filter_by(symbol=symbol, venue=provider_market).one_or_none()
        if instrument:
            return instrument
        instrument = TradeInstrument(
            public_id=generate_public_id(),
            asset_id=asset.id,
            symbol=symbol,
            venue=provider_market,
            instrument_type="EQUITY",
            currency=asset.currency,
        )
        self.db.add(instrument)
        self.db.flush()
        return instrument
