# User Read Models Task 5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver V1 user-facing read models for the timeline-first homepage and lifecycle detail before frontend page migration begins.

**Architecture:** Add read-model services and V1 endpoints that consume the Task 3 truth model without expanding legacy dashboard/position routers. Every response returns `meta: TrustMeta`; timeline and review inbox are action-oriented; lifecycle detail is event-sourced from `TradingPosition / PositionEvent / AccountLedgerEntry`; external catalysts remain evidence-linked only.

**Tech Stack:** FastAPI, SQLAlchemy ORM, Alembic, SQLite test harness, pytest, FastAPI TestClient, Decimal accounting.

---

## Files And Responsibilities

- Create `backend/services/read_model_service.py`: builds `TrustMeta`, timeline events, review inbox items, lifecycle nodes, evidence items, and linked narrative signals.
- Create `backend/routers/read_models.py`: exposes `/api/v1/read-models/home` and `/api/v1/read-models/trading-positions/{position_public_id}/lifecycle`.
- Modify `backend/schemas.py`: adds read-model DTO shells for stable shape and documentation.
- Modify `backend/main.py`: includes the read-model router.
- Modify `backend/models.py`: adds minimal `EvidenceItem`, `ExternalCatalyst`, `NarrativeSignal`, `ProviderSymbolMapping`, `MarketDataCoverage`, `DashboardCache`, and `PositionMetric` tables.
- Create `backend/services/market_orchestration_service.py`: resolves provider symbol mapping without calling provider SDKs.
- Create `backend/services/derived_read_model_service.py`: stores and reads dashboard/position materialization metadata.
- Create `backend/alembic/versions/20260604_0004_user_read_models.py`: persists evidence, market mapping, and derived-cache tables.
- Create tests under `backend/tests/`: prove read-model shape, external catalyst filtering, lifecycle evidence, provider mapping, derived cache, and migration upgrade.
- Modify `docs/superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md`: mark Task 5 only after all read-model gates verify.

---

### Task 5A: TrustMeta And Timeline/Review Read Service

**Files:**
- Create: `backend/tests/test_read_model_service.py`
- Create: `backend/services/read_model_service.py`

- [x] **Step 1: Write failing home read-model service test**

Create a test that opens a position with decision-quality fields and asserts `ReadModelService.build_home_read_model(user_id=1)` returns `meta`, `timeline_events`, `review_inbox`, and `context_rail`; every timeline event and review item carries `trust_meta`.

- [x] **Step 2: Run home read-model service test and verify RED**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_read_model_service.py::test_home_read_model_returns_trust_wrapped_timeline_and_review_inbox -q`

Expected: FAIL because `services.read_model_service` does not exist.

- [x] **Step 3: Implement minimal read-model service**

Create `TrustMeta` as a dict helper and derive timeline events from `PositionEvent`. Generate Review Inbox items for `MISSING_THESIS`, `REVIEW_DUE`, and `CHECKLIST_MISS` from first-class decision fields.

- [x] **Step 4: Run home read-model service test and verify GREEN**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_read_model_service.py::test_home_read_model_returns_trust_wrapped_timeline_and_review_inbox -q`

Expected: PASS.

---

### Task 5B: Lifecycle Detail And Evidence Read Service

**Files:**
- Modify: `backend/tests/test_read_model_service.py`
- Modify: `backend/services/read_model_service.py`

- [x] **Step 1: Write failing lifecycle service test**

Add a test that opens, adds, reduces, and closes a position, then asserts `build_lifecycle_detail()` returns `meta`, `position_public_id`, ordered `lifecycle_nodes`, `ledger_refs`, `evidence_items`, and an empty `narrative_signals` list when no linked catalyst exists.

- [x] **Step 2: Run lifecycle service test and verify RED**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_read_model_service.py::test_lifecycle_detail_returns_ordered_nodes_and_evidence -q`

Expected: FAIL because `build_lifecycle_detail()` is not implemented.

- [x] **Step 3: Implement lifecycle read model**

Build lifecycle nodes from `PositionEvent`, attach ledger entry public IDs by position, and create evidence items from decision fields such as thesis, invalidation rule, and checklist snapshot.

- [x] **Step 4: Run lifecycle service test and verify GREEN**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_read_model_service.py::test_lifecycle_detail_returns_ordered_nodes_and_evidence -q`

Expected: PASS.

---

### Task 5C: V1 Read-Model API

**Files:**
- Create: `backend/tests/test_read_models_api.py`
- Modify: `backend/schemas.py`
- Create: `backend/routers/read_models.py`
- Modify: `backend/main.py`

- [x] **Step 1: Write failing read-model API test**

Create a FastAPI TestClient test for `GET /api/v1/read-models/home` and `GET /api/v1/read-models/trading-positions/{position_public_id}/lifecycle`, asserting both expose `meta` and no raw internal integer `id`.

- [x] **Step 2: Run read-model API test and verify RED**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_read_models_api.py::test_v1_read_model_endpoints_return_trust_wrapped_contracts -q`

Expected: FAIL because the router does not exist.

- [x] **Step 3: Implement schemas and router**

Add DTO shells and router endpoints that call `ReadModelService`. Include the router in `main.py`.

- [x] **Step 4: Run read-model API test and verify GREEN**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_read_models_api.py::test_v1_read_model_endpoints_return_trust_wrapped_contracts -q`

Expected: PASS.

---

### Task 5D: Evidence-Linked External Catalyst Boundary

**Files:**
- Modify: `backend/tests/test_read_model_service.py`
- Modify: `backend/models.py`
- Modify: `backend/services/read_model_service.py`

- [x] **Step 1: Write failing catalyst filtering test**

Add a test that creates one linked `ExternalCatalyst` with an `EvidenceItem` for the position and one unlinked catalyst, then asserts only the linked catalyst appears in lifecycle narrative signals.

- [x] **Step 2: Run catalyst filtering test and verify RED**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_read_model_service.py::test_external_catalysts_only_surface_when_linked_to_position_evidence -q`

Expected: FAIL because evidence/catalyst models do not exist.

- [x] **Step 3: Add evidence/catalyst models and filtering**

Add minimal ORM models and read-model filtering by `linked_object_public_id` and evidence refs. Do not expose raw news feeds.

- [x] **Step 4: Run catalyst filtering test and verify GREEN**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_read_model_service.py::test_external_catalysts_only_surface_when_linked_to_position_evidence -q`

Expected: PASS.

---

### Task 5E: Provider Mapping And Market Coverage Baseline

**Files:**
- Create: `backend/tests/test_market_orchestration_service.py`
- Modify: `backend/models.py`
- Create: `backend/services/market_orchestration_service.py`

- [x] **Step 1: Write failing provider mapping test**

Create a test that resolves `AAPL` for provider `finnhub` and asserts a `ProviderSymbolMapping` row stores provider key, provider symbol, provider market, capabilities, quality status, and `asset_id` or `instrument_id`.

- [x] **Step 2: Run provider mapping test and verify RED**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_market_orchestration_service.py::test_provider_symbol_mapping_is_distinct_from_asset_and_instrument -q`

Expected: FAIL because provider mapping models/service do not exist.

- [x] **Step 3: Implement market mapping baseline**

Add `ProviderSymbolMapping`, `MarketDataCoverage`, and `MarketOrchestrationService.resolve_symbol_mapping()` without calling external provider SDKs.

- [x] **Step 4: Run provider mapping test and verify GREEN**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_market_orchestration_service.py::test_provider_symbol_mapping_is_distinct_from_asset_and_instrument -q`

Expected: PASS.

---

### Task 5F: Derived Read Model Cache Baseline

**Files:**
- Create: `backend/tests/test_derived_read_model_service.py`
- Modify: `backend/models.py`
- Create: `backend/services/derived_read_model_service.py`

- [x] **Step 1: Write failing derived cache test**

Create a test that writes a dashboard cache payload and position metric payload with freshness metadata, then reads them back with `TrustMeta` fields.

- [x] **Step 2: Run derived cache test and verify RED**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_derived_read_model_service.py::test_derived_cache_returns_payload_with_freshness_metadata -q`

Expected: FAIL because derived cache models/service do not exist.

- [x] **Step 3: Implement derived cache baseline**

Add `DashboardCache`, `PositionMetric`, and service methods `store_dashboard_cache()`, `get_dashboard_cache()`, `store_position_metric()`, and `get_position_metric()`.

- [x] **Step 4: Run derived cache test and verify GREEN**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_derived_read_model_service.py::test_derived_cache_returns_payload_with_freshness_metadata -q`

Expected: PASS.

---

### Task 5G: Migration And Gate Verification

**Files:**
- Create: `backend/alembic/versions/20260604_0004_user_read_models.py`
- Modify: `docs/superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md`
- Modify: `docs/superpowers/plans/2026-06-04-user-read-models-task5-implementation-plan.md`

- [x] **Step 1: Add Alembic migration**

Create revision `20260604_0004` for evidence, catalysts, narrative signals, provider symbol mappings, market coverage, dashboard cache, and position metrics.

- [x] **Step 2: Run full backend tests**

Run: `cd backend && ../.venv/bin/python -m pytest tests -q`

Expected: PASS.

- [x] **Step 3: Run Alembic smoke and upgrade**

Run: `cd backend && ../.venv/bin/alembic -c alembic.ini current`

Expected: command exits 0.

Run: `cd backend && env DATABASE_URL=sqlite:////private/tmp/tradingnoobs_alembic_task5_verify.db ../.venv/bin/alembic -c alembic.ini upgrade head`

Expected: migrations `20260604_0001` through `20260604_0004` execute.

- [x] **Step 4: Update top-level sequencing plan**

Mark Task 5 complete only after trust envelopes, timeline/review inbox, lifecycle/evidence, provider mapping, derived cache, and catalyst filtering are verified.

- [x] **Step 5: Review diff**

Run: `git diff --check`

Expected: no output.

**Progress 2026-06-04:**
- Implemented Task 5 read-model gate: trust-wrapped home timeline/review inbox, lifecycle/evidence detail, V1 read-model endpoints, evidence-linked catalysts, provider symbol mapping/coverage baseline, and derived dashboard/position cache metadata.
- Added Alembic revision `20260604_0004_user_read_models.py`.
- Verification: `cd backend && ../.venv/bin/python -m pytest tests -q` passed with 28 tests; `cd backend && ../.venv/bin/alembic -c alembic.ini current` exited 0; temporary SQLite `alembic upgrade head` executed revisions `20260604_0001`, `20260604_0002`, `20260604_0003`, and `20260604_0004`; `git diff --check` clean.
