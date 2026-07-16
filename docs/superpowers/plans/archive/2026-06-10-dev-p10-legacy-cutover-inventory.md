# P10 Legacy Cutover Inventory

**Date:** 2026-06-10
**Branch:** `dev`
**Status:** `ARCHIVED_SUPPORTING_INVENTORY`; current execution is governed by `../2026-07-16-dev-trading-journal-development-plan.md`.
**Purpose:** label the current legacy and truth ownership boundaries before any deletion or hard cutover work starts.

## Summary

The `dev` branch has the core truth path in place. After P11, ordinary create/add/reduce/close/review/narrative flows are truth-first, Timeline/Review Inbox default to truth snapshots, and legacy trading mutations are protected behind explicit migration fallback labels.

Do not delete `Position / TradeBatch / Transaction / AssetMetadata / DailySnapshot` until each remaining usage below is either moved to a truth-backed read/write path, explicitly retained as migration-only, or covered by a rollback plan.

## Post-P11 Update

- Ordinary position creation still enters through `POST /api/positions`, but now uses a create-and-sync contract and returns `truth_position_public_id`.
- Ordinary add/reduce/close flows use `TradingPosition / PositionEvent`; legacy batch create requires `X-Migration-Fallback: legacy-batch-write` once a truth lifecycle exists.
- Ordinary review/narrative writes use `PositionEvent` narrative fields; legacy review writes require `X-Migration-Fallback: legacy-review-write` once a truth lifecycle exists.
- Legacy whole-position hard delete requires `X-Migration-Fallback: legacy-position-delete` once a truth lifecycle exists.
- Legacy batch edit/delete requires `X-Migration-Fallback: legacy-batch-edit` once a truth lifecycle exists.
- `/api/timeline/home` defaults to `SNAPSHOT_ONLY`; `timeline_legacy_mixed_feed_enabled` is the rollback flag for the mixed legacy feed.
- Remaining raw frontend legacy DTO imports are locked by `frontend/tests/legacy-ui-boundaries.test.mts` to migration/support, create-and-sync bridge, and legacy analytics adapter files.

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
| `Position` | Legacy position aggregate. | `backend/routers/positions.py`, `backend/routers/dashboard.py`, `backend/routers/timeline.py`, `backend/services/legacy_truth_sync_service.py` | Migration/support path; ordinary writes protected after P11 |
| `TradeBatch` | Legacy batch/event representation. | `backend/routers/positions.py`, `backend/services/import_service.py`, `backend/services/llm_service.py`, `frontend/lib/api.ts` | Migration/support path; ordinary batch mutations protected after P11 |
| `Transaction` | Legacy account transaction. | `backend/routers/transactions.py`, `backend/services/account_ledger_service.py`, `frontend/lib/api.ts` | Bridge path until ledger-only cash flows are complete |
| `AssetMetadata` | Legacy asset metadata cache. | `backend/routers/positions.py`, `backend/services/market_data_service.py`, `frontend/lib/symbolUtils.ts` | Bridge path until asset master ownership is complete |
| `DailySnapshot` | Legacy daily equity snapshot. | `backend/routers/dashboard.py` | Dashboard history bridge |

## Primary Truth Paths

| Area | Current owner | Evidence | Cutover status |
|------|---------------|----------|----------------|
| Single-position lifecycle read model | `TradingPosition / PositionEvent / AccountLedgerEntry` via `trading_position_read_service` | `backend/routers/trading_positions.py`, `backend/services/trading_position_read_service.py`, `frontend/app/positions/[id]/page.tsx` | Primary path exists; legacy fallback still appears when lifecycle cannot be loaded. |
| Truth trade event writes | `PositionEvent` write service | `backend/routers/trading_positions.py`, `backend/services/trading_position_write_service.py`, `frontend/app/positions/[id]/add-batch/page.tsx` | ADD / REDUCE / CLOSE ordinary write path is primary; legacy batch writes are migration-only when truth lifecycle exists. |
| Truth narrative edits | `PositionEvent` narrative fields | `backend/routers/trading_positions.py`, `frontend/lib/adapters/lifecycle.ts`, `frontend/app/positions/[id]/page.tsx` | Primary detail-page narrative path; legacy `Position.trade_review / lessons / rating` writes are migration-only when truth lifecycle exists. |
| Ledger-backed cash effects | `AccountLedgerEntry` | `backend/services/account_ledger_service.py`, `backend/services/trading_position_read_service.py` | Ledger is preferred for lifecycle cash effects; legacy `Transaction` still exists for account transaction routes and bridge sync. |
| Truth-to-derived Timeline refresh | `DerivedTimelineSnapshot` | `backend/services/derived_refresh_handlers.py`, `backend/services/derived_timeline_read_service.py`, `backend/routers/timeline.py` | Default Timeline and Review Inbox are snapshot/truth-backed; legacy mixed feed is rollback-only. |
| Insight artifacts | `InsightRun / InsightArtifact` | `backend/services/insight_artifact_service.py`, `backend/routers/insight_artifacts.py`, `frontend/lib/insightArtifacts.ts` | Artifact-first display path exists; date-range workflow and old markdown fallback cleanup remain. |
| Legacy-to-truth migration bridge | `legacy_truth_sync_service` | `backend/services/legacy_truth_sync_service.py`, `backend/routers/positions.py` | Required bridge until historical legacy rows have a verified migration and rollback story. |

## Migration-Only Legacy Paths

| Area | Current owner | Why it remains | Delete condition |
|------|---------------|----------------|------------------|
| Legacy position CRUD and batch operations | `backend/routers/positions.py` | Still supports legacy list/detail/export/import, fallback lifecycle bridge, and migration corrections. | Truth-native create/import/list read models replace the remaining bridge usage; rollback headers are no longer needed for normal ops. |
| Legacy dashboard aggregates | `backend/routers/dashboard.py` | Dashboard still computes parts of stats, open positions, account exposure, and daily snapshot history from `Position / TradeBatch / DailySnapshot`. | Dashboard read models are rebuilt from truth positions, ledger, market values, and derived snapshots. |
| Legacy Timeline fallback | `backend/routers/timeline.py` | Mixed legacy feed remains available behind `timeline_legacy_mixed_feed_enabled`. | Rollback flag is unused in normal operation for a release window, then legacy builders can move to migration/admin tooling or be deleted. |
| Account transaction routes | `backend/routers/transactions.py` | User-facing cash transaction CRUD still writes and reads `Transaction`; ledger bridge keeps `AccountLedgerEntry` aligned. | Account cash UI/API uses ledger-native commands and `Transaction` becomes read-only import history or is migrated. |
| Import service | `backend/services/import_service.py` | Existing CSV/Excel import produces legacy `Position / TradeBatch` rows before bridge sync. | Import writes truth positions/events directly or runs an atomic import-to-truth bridge with idempotent retry behavior. |
| Analytics service | `backend/services/analytics_service.py` | Some analytics still read closed legacy positions and batch emotion/confidence fields. | Analytics contracts read from truth events, artifacts, ledger, and derived read models. |
| LLM weekly/report formatting | `backend/services/llm_service.py` | Weekly report prompts still format legacy batches and positions. | P14/P15 report and AI flows consume artifact-backed, truth-derived read models with explicit date ranges. |
| Market metadata enrichment | `backend/services/market_data_service.py` | `AssetMetadata` remains the legacy symbol metadata cache. | Market data platform owns provider mapping and writes canonical `AssetMaster / TradeInstrument` metadata. |
| Public ID lookup bridge | `backend/services/public_id_service.py` | Legacy public IDs still resolve old positions, batches, and transactions. | Public ID consumers use truth IDs or a documented legacy resolver namespace. |
| Frontend raw legacy DTOs | `frontend/lib/api.ts`, `frontend/lib/adapters/trading.ts`, `frontend/app/positions/page.tsx`, `frontend/app/positions/[id]/add-batch/page.tsx`, `frontend/app/positions/new/page.tsx`, legacy dashboard chart adapters | Existing pages still display or adapt `Position / TradeBatch / BatchCreate` for migration/support, create-and-sync bridge, and legacy analytics. | P12/P13 introduces generated contracts/read-model adapters, then remaining raw imports are removed or moved under migration-only modules. |

## Delete Candidates

| File or symbol | Replacement | Required pre-delete verification |
|----------------|-------------|----------------------------------|
| Legacy batch mutation endpoints in `backend/routers/positions.py` | `POST /api/trading-positions/{position_public_id}/events` and reversal/adjustment routes | P11 guards are in place; after import/export migration coverage, delete or move legacy mutation endpoints to migration/admin routes. |
| Legacy whole-position delete behavior | Truth archival, void, or migration-only admin action | P11 guards are in place; implement audited archive/void UX before removing hard-delete fallback. |
| Legacy review fields on `Position` as ordinary write target | `PositionEvent` narrative/review fields plus `InsightArtifact` evidence | P11 guards are in place; delete ordinary frontend write affordances and keep fields read-only until data migration completes. |
| Timeline legacy `Position` event builder | `DerivedTimelineSnapshot` plus truth lifecycle read model | P11 snapshot default is enabled and tested; delete after rollback window and browser smoke with authenticated seed data. |
| Dashboard legacy `Position / TradeBatch` aggregate queries | Truth position aggregates, ledger entries, and derived portfolio snapshots | Dashboard contracts match current UI metrics, including account exposure, realized PnL, open market value, and empty/small-data states. |
| Legacy `Transaction` account cash CRUD | Ledger-native account commands | Ledger balance, cash adjustment, opening balance, deposits/withdrawals, and account history tests pass without `Transaction` writes. |
| `AssetMetadata` as primary metadata owner | `AssetMaster / TradeInstrument` plus provider mapping | Import, market data, symbol search, and display-name flows work from canonical asset/instrument tables. |
| `DailySnapshot` as dashboard history source | Portfolio snapshot or derived ledger/market snapshot model | Historical equity, drawdown, return chart, and backfill tests pass on the replacement. |
| `frontend/lib/api.ts` legacy DTO exports as permanent contracts | Generated OpenAPI types plus read-model adapters | Frontend typecheck and lint pass after moving all new user-facing pages away from raw legacy DTO imports. |

## Open Product Decisions

- Audited archive/void UX: P11 decided not to hard-delete truth lifecycles or reverse `OPEN`; P12+ should define the user-facing archive/void action and permissions.
- Non-latest reversal compensating UX: P11 rejects non-latest active reversal for ordinary users; P12+ can define a compensating-event workflow if needed.
- Legacy import behavior after truth write path is default: decide whether imports write truth directly, write legacy then bridge, or support both with an explicit import mode.
- Account transaction history semantics: decide whether users see ledger entries directly or a curated cash activity read model.
- Asset metadata ownership: decide whether `AssetMetadata` is fully migrated into `AssetMaster / TradeInstrument` or kept as a provider-cache detail behind the new models.

## P12 Starting Point

Recommended first P12 slice:

1. Introduce contract hardening around OpenAPI/generated frontend types.
2. Draw a clear boundary between product read models and migration/support DTOs.
3. Add release/rollback playbooks for truth writes, snapshot Timeline, and migration fallback headers.
4. Only then start deleting or moving legacy code.
