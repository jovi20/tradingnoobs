from models import MarketDataCoverage, ProviderSymbolMapping
from services.market_orchestration_service import MarketOrchestrationService


def test_provider_symbol_mapping_is_distinct_from_asset_and_instrument(db_session):
    service = MarketOrchestrationService(db_session)

    mapping = service.resolve_symbol_mapping(
        asset_symbol="AAPL",
        provider_key="finnhub",
        provider_symbol="AAPL",
        provider_market="US",
        capabilities={"quote": True, "daily": True},
    )

    stored = db_session.query(ProviderSymbolMapping).filter_by(public_id=mapping.public_id).one()
    coverage_rows = db_session.query(MarketDataCoverage).filter_by(provider_symbol_mapping_id=stored.id).all()

    assert stored.asset_id is not None
    assert stored.instrument_id is not None
    assert stored.provider_key == "finnhub"
    assert stored.provider_symbol == "AAPL"
    assert stored.provider_market == "US"
    assert stored.capabilities_json == {"quote": True, "daily": True}
    assert stored.quality_status == "ACTIVE"
    assert {coverage.capability for coverage in coverage_rows} == {"quote", "daily"}
    assert {coverage.quality_status for coverage in coverage_rows} == {"ACTIVE"}
