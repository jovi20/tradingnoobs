# P16 Market Data Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split market data routing from provider adapters so quotes, validation, freshness, and degradation are testable and explainable.

**Architecture:** Keep `MarketDataService` as the public facade during migration, but move provider selection into a small orchestrator with typed provider results. Provider modules return normalized data and metadata; routers return freshness/degradation fields instead of swallowing provider failures into ambiguous payloads.

**Tech Stack:** FastAPI, SQLAlchemy, provider adapter modules, Pydantic schemas, existing AKShare/Binance/Finnhub/YFinance integrations, Next.js 16, TypeScript.

---

## Current Baseline

Known current issue:
- `backend/routers/market.py` calls `service.get_quote(...)` without `await`, so `/api/market/quote/{symbol}` can return a coroutine-like value or fail serialization. P16 must lock this with a regression test before provider refactor.

Existing providers:
- `backend/services/providers/akshare_provider.py`
- `backend/services/providers/binance_provider.py`
- Finnhub and YFinance logic currently live inside `backend/services/market_data_service.py`.

## Files Likely To Touch

Backend:
- Create: `backend/services/market_data_types.py`
- Create: `backend/services/market_data_orchestrator.py`
- Create: `backend/services/provider_router.py`
- Create: `backend/services/providers/finnhub_provider.py`
- Modify: `backend/services/market_data_service.py`
- Modify: `backend/services/providers/akshare_provider.py`
- Modify: `backend/services/providers/binance_provider.py`
- Modify: `backend/services/providers/__init__.py`
- Modify: `backend/routers/market.py`
- Modify: `backend/schemas.py`
- Test: `backend/tests/test_market_data_orchestrator.py`
- Test: `backend/tests/test_market_router.py`
- Test: `backend/tests/test_market_provider_contracts.py`

Frontend:
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/components/MarketStatus.tsx`
- Test: `frontend/tests/market-data.test.mts`

Docs:
- Modify: `docs/market_data_sources.md`
- Modify: `docs/TODO.md`
- Modify: `docs/DEVELOPER_GUIDE.md`
- Modify: `docs/superpowers/plans/2026-06-11-dev-p16-market-data-platform-plan.md`

## Normalized Quote Contract

Provider result shape inside backend:

```python
{
    "symbol": "MSFT",
    "provider": "finnhub",
    "price": 421.13,
    "previous_close": 418.90,
    "high": 424.00,
    "low": 417.10,
    "open": 419.00,
    "change_percent": 0.53,
    "as_of": "2026-06-11T10:30:00Z",
    "freshness": "FRESH",
    "degraded": false,
    "source_refs": ["provider:finnhub", "symbol:MSFT"]
}
```

Public API can preserve the legacy `quote.c` fields during migration, but must add `provider`, `freshness`, `degraded`, and `source_refs`.

## Task 1: Lock Market Quote Router Contract

**Goal:** fix the missing `await` and prevent regression.

- [x] Add `backend/tests/test_market_router.py` with:
  - `test_quote_endpoint_awaits_market_data_service`
  - `test_quote_endpoint_returns_error_payload_on_provider_failure`
  - `test_validate_endpoint_preserves_existing_shape`
- [x] Mock `MarketDataService.get_quote` with an async fake returning `{"c": 100, "pc": 95}`.
- [x] Run targeted test and confirm RED because the quote endpoint does not await `get_quote`.

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_market_router.py
```

- [x] Fix `backend/routers/market.py` to call `quote = await service.get_quote(symbol, exchange)`.
- [x] Keep response compatibility:

```json
{
  "symbol": "MSFT",
  "asset_type": "US_STOCK",
  "quote": {"c": 100, "pc": 95}
}
```

- [x] Run targeted test and confirm GREEN.
- [x] Commit:

```bash
git add backend/routers/market.py backend/tests/test_market_router.py
git commit -m "fix: await market quote endpoint"
```

## Task 2: Add Provider Result Types And Router

**Goal:** centralize provider selection rules outside the fetch service.

- [x] Create `backend/services/market_data_types.py` with dataclasses:
  - `MarketDataRequest`
  - `MarketDataProviderResult`
  - `MarketDataProviderError`
  - `ProviderRoute`
- [x] Create `backend/services/provider_router.py` with:
  - `detect_asset_route(symbol, exchange=None, core_type=None, market=None, instrument=None)`.
  - deterministic routes for `CRYPTO`, `A_SHARE`, `HK`, `US`, `FOREX`, `FUND`.
  - provider fallback order for US: `["finnhub", "yfinance"]`.
- [x] Add tests in `backend/tests/test_market_data_orchestrator.py`:
  - `BTCUSDT` routes to Binance.
  - `600519` routes to AKShare A-share.
  - `0700.HK` routes to AKShare HK.
  - `MSFT` routes to Finnhub then YFinance.
  - `USDCNY` routes to FX provider.
- [x] Run targeted test and confirm GREEN.
- [x] Commit:

```bash
git add backend/services/market_data_types.py backend/services/provider_router.py backend/tests/test_market_data_orchestrator.py
git commit -m "feat: add market provider routing contracts"
```

## Task 3: Extract Provider Adapters

**Goal:** each provider returns normalized values and does not decide product-level degradation semantics.

- [x] Create `backend/services/providers/finnhub_provider.py` with:
  - `get_quote(symbol, client) -> dict`
  - `get_history(symbol, start, end, client) -> list[dict]`
- [x] Add adapter functions to existing provider modules:
  - `akshare_provider.get_normalized_quote(symbol, market)`
  - `binance_provider.get_normalized_quote(symbol)`
- [x] Remove direct `print()` in `binance_provider.get_klines`; replace with structured logger or empty result reason.
- [x] Add `backend/tests/test_market_provider_contracts.py` with fake provider data and no network calls.
- [x] Run:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_market_provider_contracts.py
```

- [x] Commit:

```bash
git add backend/services/providers/finnhub_provider.py backend/services/providers/akshare_provider.py backend/services/providers/binance_provider.py backend/services/providers/__init__.py backend/tests/test_market_provider_contracts.py
git commit -m "feat: normalize market provider adapters"
```

## Task 4: Add Orchestrator With Freshness And Degradation

**Goal:** quote failures become explainable read-model metadata.

- [x] Create `backend/services/market_data_orchestrator.py` with:
  - `get_quote_with_metadata(request, db)`.
  - provider fallback loop.
  - cache hit freshness.
  - degradation reason when primary provider fails and fallback succeeds.
  - structured log events for provider failure and fallback success.
- [x] Modify `MarketDataService.get_quote(...)` to delegate to orchestrator but preserve legacy quote keys.
- [x] Add public response schemas in `backend/schemas.py`:
  - `MarketQuoteTrustMeta`
  - `MarketQuoteResponse`
  - `MarketValidationResponse`
- [x] Modify `backend/routers/market.py` to include `provider`, `freshness`, `degraded`, and `source_refs`.
- [x] Add tests:
  - primary success returns `freshness=FRESH`.
  - fallback success returns `degraded=true`.
  - all providers fail returns stable `error` and `source_refs`.
- [x] Run:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_market_data_orchestrator.py
../.venv313/bin/python -m unittest discover -s tests -p test_market_router.py
```

- [x] Commit:

```bash
git add backend/services/market_data_orchestrator.py backend/services/market_data_service.py backend/routers/market.py backend/schemas.py backend/tests/test_market_data_orchestrator.py backend/tests/test_market_router.py
git commit -m "feat: add market data freshness metadata"
```

## Task 5: Surface Freshness In Frontend And Docs

**Goal:** users can tell whether market data is fresh, stale, or degraded.

- [x] Extend `frontend/lib/api.ts` market types with freshness metadata.
- [x] Update `frontend/components/MarketStatus.tsx` to show:
  - provider name.
  - freshness label.
  - degraded reason when present.
- [x] Add `frontend/tests/market-data.test.mts` covering adapter/label logic.
- [x] Update `docs/market_data_sources.md` with provider routing, fallback, freshness, and validation commands.
- [x] Run:

```bash
cd frontend
node --experimental-strip-types --test tests/market-data.test.mts
./node_modules/.bin/tsc --noEmit --pretty false
```

- [x] Commit:

```bash
git add frontend/lib/api.ts frontend/components/MarketStatus.tsx frontend/tests/market-data.test.mts docs/market_data_sources.md
git commit -m "feat: show market data freshness metadata"
```

## Task 6: P16 Completion Gate

- [x] Backend market targeted tests pass.
- [x] Full backend tests pass.
- [x] Frontend typecheck, lint, and Node tests pass.
- [x] `docs/TODO.md` marks P16 complete and P17 as next lane.

Final verification:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests
cd ../frontend
./node_modules/.bin/tsc --noEmit --pretty false
npm run lint
node --experimental-strip-types --test tests/*.test.mts
cd ..
git diff --check
git status --short --branch
```

## Execution Log

- Task 1 committed as `c9bf3f7 fix: await market quote endpoint`.
- Task 2 committed as `907cb07 feat: add market provider routing contracts`.
- Task 3 committed as `377a632 feat: normalize market provider adapters`.
- Task 4 committed as `d6f45fa feat: add market data freshness metadata`.
- Task 5 committed as `ae50afc feat: show market data freshness metadata`.
- P16 targeted verification completed:
  - `test_market_router.py`: passed.
  - `test_market_data_orchestrator.py`: passed.
  - `test_market_provider_contracts.py`: passed.
  - `test_openapi_contracts.py`: passed.
  - `frontend/tests/market-data.test.mts`: passed.
  - Frontend typecheck and lint: passed.
- Final completion gate:
  - Backend full test suite: 212 tests passed.
  - Frontend typecheck: passed.
  - Frontend lint: passed.
  - Frontend Node tests: 109 tests passed.
  - `git diff --check`: passed.
- P16 completion docs updated to mark P17 as the next active lane.

## Stop Conditions

- Stop before replacing all provider internals at once if public quote compatibility breaks.
- Stop before adding paid provider dependencies.
- Stop before removing legacy `MarketDataService`; keep it as a facade until all callers move.
- Stop before adding background refresh jobs; P16 is provider/orchestrator hardening.
