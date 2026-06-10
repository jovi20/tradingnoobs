# P10 Legacy Cutover Inventory

**Date:** 2026-06-10
**Branch:** `dev`
**Purpose:** label the current legacy and truth ownership boundaries before any deletion or hard cutover work starts.

## Summary

The `dev` branch already has the core truth path in place, but the legacy path is still a live bridge for several read, import, analytics, and fallback surfaces.

Do not delete `Position / TradeBatch / Transaction / AssetMetadata / DailySnapshot` until each usage below is either moved to a truth-backed read/write path, explicitly retained as migration-only, or covered by a rollback plan.

## Model Inventory

| Symbol | Current role | Evidence | Cutover classification |
|--------|--------------|----------|------------------------|
| `TradingPosition` | Truth position aggregate. | `backend/models.py`, `backend/routers/trading_positions.py`, `backend/services/trading_position_read_service.py`, `backend/services/trading_position_write_service.py` | Primary truth path |
| `PositionEvent` | Truth event stream for OPEN / ADD / REDUCE / CLOSE / REVERSAL / DIVIDEND / MANUAL_ADJUSTMENT. | `backend/models.py`, `backend/routers/trading_positions.py`, `backend/services/trading_position_write_service.py` | Primary truth path |
| `AccountLedgerEntry` | Ledger-backed account cash and position cash effects. | `backend/models.py`, `backend/services/account_ledger_service.py`, `backend/services/trading_position_read_service.py` | Primary truth path |
| `AssetMaster` | New canonical asset layer. | `backend/models.py`, `backend/services/legacy_truth_sync_service.py` | Primary truth path |
| `TradeInstrument` | New instrument layer between asset and position. | `backend/models.py`, `backend/services/legacy_truth_sync_service.py`, `backend/services/trading_position_read_service.py` | Primary truth path |
| `DerivedTimelineSnapshot` | Snapshot-backed derived Timeline events. | `backend/models.py`, `backend/routers/timeline.py`, `backend/services/derived_refresh_handlers.py`, `backend/services/derived_timeline_read_service.py` | Primary truth-derived read path |
| `InsightArtifact` | Auditable AI output unit. | `backend/models.py`, `backend/services/insight_artifact_service.py`, `frontend/lib/insightArtifacts.ts` | Primary artifact path |
| `Position` | Legacy position aggregate. | `backend/routers/positions.py`, `backend/routers/dashboard.py`, `backend/routers/timeline.py`, `backend/services/legacy_truth_sync_service.py` | Migration and fallback path |
| `TradeBatch` | Legacy batch/event representation. | `backend/routers/positions.py`, `backend/services/import_service.py`, `backend/services/llm_service.py`, `frontend/lib/api.ts` | Migration and fallback path |
| `Transaction` | Legacy account transaction. | `backend/routers/transactions.py`, `backend/services/account_ledger_service.py`, `frontend/lib/api.ts` | Bridge path until ledger-only cash flows are complete |
| `AssetMetadata` | Legacy asset metadata cache. | `backend/routers/positions.py`, `backend/services/market_data_service.py`, `frontend/lib/symbolUtils.ts` | Bridge path until asset master ownership is complete |
| `DailySnapshot` | Legacy daily equity snapshot. | `backend/routers/dashboard.py` | Dashboard history bridge |

## Primary Truth Paths

| Area | Current owner | Evidence | Cutover status |
|------|---------------|----------|----------------|
| Single-position lifecycle read model | `TradingPosition / PositionEvent / AccountLedgerEntry` via `trading_position_read_service` | `backend/routers/trading_positions.py`, `backend/services/trading_position_read_service.py`, `frontend/app/positions/[id]/page.tsx` | Primary path exists; legacy fallback still appears when lifecycle cannot be loaded. |
| Truth trade event writes | `PositionEvent` write service | `backend/routers/trading_positions.py`, `backend/services/trading_position_write_service.py`, `frontend/app/positions/[id]/add-batch/page.tsx` | ADD / REDUCE / CLOSE write path exists; final user-flow audit still needed before disabling legacy mutation routes. |
| Truth narrative edits | `PositionEvent` narrative fields | `backend/routers/trading_positions.py`, `frontend/lib/adapters/lifecycle.ts`, `frontend/app/positions/[id]/page.tsx` | Primary detail-page narrative path exists. |
| Ledger-backed cash effects | `AccountLedgerEntry` | `backend/services/account_ledger_service.py`, `backend/services/trading_position_read_service.py` | Ledger is preferred for lifecycle cash effects; legacy `Transaction` still exists for account transaction routes and bridge sync. |
| Truth-to-derived Timeline refresh | `DerivedTimelineSnapshot` | `backend/services/derived_refresh_handlers.py`, `backend/services/derived_timeline_read_service.py`, `backend/routers/timeline.py` | Snapshot mixing and snapshot-only gate exist; default Timeline is not yet hard-cut to truth/snapshot only. |
| Insight artifacts | `InsightRun / InsightArtifact` | `backend/services/insight_artifact_service.py`, `backend/routers/insight_artifacts.py`, `frontend/lib/insightArtifacts.ts` | Artifact-first display path exists; date-range workflow and old markdown fallback cleanup remain. |
| Legacy-to-truth migration bridge | `legacy_truth_sync_service` | `backend/services/legacy_truth_sync_service.py`, `backend/routers/positions.py` | Required bridge until historical legacy rows have a verified migration and rollback story. |

## Migration-Only Legacy Paths

| Area | Current owner | Why it remains | Delete condition |
|------|---------------|----------------|------------------|
| Legacy position CRUD and batch operations | `backend/routers/positions.py` | Still supports legacy list/detail/export/import, fallback lifecycle bridge, and existing data operations. | P11 moves ordinary create/add/reduce/close/review flows to truth routes; import/export and rollback coverage are verified. |
| Legacy dashboard aggregates | `backend/routers/dashboard.py` | Dashboard still computes parts of stats, open positions, account exposure, and daily snapshot history from `Position / TradeBatch / DailySnapshot`. | Dashboard read models are rebuilt from truth positions, ledger, market values, and derived snapshots. |
| Legacy Timeline fallback | `backend/routers/timeline.py` | Timeline still uses `Position` and old AI summary/result rows alongside `DerivedTimelineSnapshot`. | Snapshot-only path becomes default and has regression coverage for empty, small-data, stale-data, AI, and review-inbox states. |
| Account transaction routes | `backend/routers/transactions.py` | User-facing cash transaction CRUD still writes and reads `Transaction`; ledger bridge keeps `AccountLedgerEntry` aligned. | Account cash UI/API uses ledger-native commands and `Transaction` becomes read-only import history or is migrated. |
| Import service | `backend/services/import_service.py` | Existing CSV/Excel import produces legacy `Position / TradeBatch` rows before bridge sync. | Import writes truth positions/events directly or runs an atomic import-to-truth bridge with idempotent retry behavior. |
| Analytics service | `backend/services/analytics_service.py` | Some analytics still read closed legacy positions and batch emotion/confidence fields. | Analytics contracts read from truth events, artifacts, ledger, and derived read models. |
| LLM weekly/report formatting | `backend/services/llm_service.py` | Weekly report prompts still format legacy batches and positions. | P14/P15 report and AI flows consume artifact-backed, truth-derived read models with explicit date ranges. |
| Market metadata enrichment | `backend/services/market_data_service.py` | `AssetMetadata` remains the legacy symbol metadata cache. | Market data platform owns provider mapping and writes canonical `AssetMaster / TradeInstrument` metadata. |
| Public ID lookup bridge | `backend/services/public_id_service.py` | Legacy public IDs still resolve old positions, batches, and transactions. | Public ID consumers use truth IDs or a documented legacy resolver namespace. |
| Frontend raw legacy DTOs | `frontend/lib/api.ts`, `frontend/lib/adapters/trading.ts`, `frontend/app/positions/page.tsx` | Existing pages still display or adapt `Position / TradeBatch / Transaction`. | New pages use read-model adapters and generated OpenAPI types; old DTOs are isolated to migration tools. |

## Delete Candidates

| File or symbol | Replacement | Required pre-delete verification |
|----------------|-------------|----------------------------------|
| Legacy batch mutation endpoints in `backend/routers/positions.py` | `POST /api/trading-positions/{position_public_id}/events` and reversal/adjustment routes | Regression tests prove ordinary add/reduce/close, idempotent retry, closed-position rejection, and latest-event reversal are truth-only. |
| Legacy whole-position delete behavior | Truth archival, void, or migration-only admin action | Product decision for delete/archive semantics is written, audited, and covered by tests. |
| Legacy review fields on `Position` as ordinary write target | `PositionEvent` narrative/review fields plus `InsightArtifact` evidence | Detail and review inbox write paths no longer patch `Position.trade_review` for ordinary users. |
| Timeline legacy `Position` event builder | `DerivedTimelineSnapshot` plus truth lifecycle read model | Snapshot-only default is enabled, tested, and has rollback feature flag instructions. |
| Dashboard legacy `Position / TradeBatch` aggregate queries | Truth position aggregates, ledger entries, and derived portfolio snapshots | Dashboard contracts match current UI metrics, including account exposure, realized PnL, open market value, and empty/small-data states. |
| Legacy `Transaction` account cash CRUD | Ledger-native account commands | Ledger balance, cash adjustment, opening balance, deposits/withdrawals, and account history tests pass without `Transaction` writes. |
| `AssetMetadata` as primary metadata owner | `AssetMaster / TradeInstrument` plus provider mapping | Import, market data, symbol search, and display-name flows work from canonical asset/instrument tables. |
| `DailySnapshot` as dashboard history source | Portfolio snapshot or derived ledger/market snapshot model | Historical equity, drawdown, return chart, and backfill tests pass on the replacement. |
| `frontend/lib/api.ts` legacy DTO exports as permanent contracts | Generated OpenAPI types plus read-model adapters | Frontend typecheck and lint pass after moving all new user-facing pages away from raw legacy DTO imports. |

## Open Product Decisions

- Historical/non-latest reversal semantics: current truth reversal is intentionally constrained to the latest active event. P11 must decide whether non-latest reversal is forbidden, creates compensating events, or is admin-only.
- `OPEN` reversal / void / archive semantics: current truth path blocks `OPEN` reversal. Product needs a clear distinction between mistaken creation, migration cleanup, and audited position voiding.
- Whole-position delete semantics after truth lifecycle exists: deletion should likely become archive/void for audited positions, while hard delete stays migration/admin-only.
- Legacy import behavior after truth write path is default: decide whether imports write truth directly, write legacy then bridge, or support both with an explicit import mode.
- Legacy batch edit behavior: choose between read-only migration display, compensating truth event, or admin-only correction.
- Account transaction history semantics: decide whether users see ledger entries directly or a curated cash activity read model.
- Asset metadata ownership: decide whether `AssetMetadata` is fully migrated into `AssetMaster / TradeInstrument` or kept as a provider-cache detail behind the new models.

## P11 Starting Point

Recommended first P11 slice:

1. Freeze new user-facing writes to truth routes only.
2. Add tests that fail if ordinary pages call legacy add/reduce/close/review endpoints.
3. Convert Timeline default read path to snapshot/truth-first with a rollback flag.
4. Label remaining legacy UI as migration tools only.
5. Only then start deleting or moving legacy code.
