# Dev Branch Checkpoint - 2026-05-02

## Branch

- Worktree: `/Users/a1/vibecoding/tradingnoobs/.worktrees/docs-platform-frontend-contracts`
- Current branch: `dev`
- Baseline branch kept for comparison: `main`
- Stage boundary commit: `e4c6544 feat: land platform foundation and frontend read models`
- Current `main...dev` committed diff: review from `main` to current `dev`; use focused diffs by area and the stage boundary below to avoid treating the full branch as one undifferentiated patch.

## Current Working Tree Shape

- Stage boundary committed files include:
  - Alembic setup and revisions
  - Backend bootstrap, timeline, trading position, platform config, public id, ledger, and truth sync services
  - Backend tests
  - Platform/frontend contract docs
  - Timeline/dashboard/settings/position frontend domain components
  - Frontend read models, adapters, and adapter tests

Committed diff summary at checkpoint:

```text
103 files changed, 13132 insertions(+), 1005 deletions(-)
```

## Verification

Frontend adapter/helper tests:

```bash
node --experimental-strip-types --test frontend/tests/*.test.mts
```

Result:

```text
tests 29
pass 29
fail 0
```

Known warning:

```text
MODULE_TYPELESS_PACKAGE_JSON
```

Backend unittest discovery with system Python:

```bash
cd backend && python -m unittest discover tests
```

Result:

```text
FAILED (errors=14)
```

Reason:

- Current Python environment is missing backend dependencies, including `fastapi`, `sqlalchemy`, and `email-validator`.
- This is an environment/dependency blocker, not yet evidence of backend behavior failure.

Backend unittest discovery with project venv:

```bash
cd backend && ../.venv313/bin/python -m unittest discover -s tests
```

Result:

```text
Ran 95 tests in 7.008s
OK
LLM Test Success: {'ok': True}
```

Known warning:

```text
yfinance/Yahoo DNS warnings for guce.yahoo.com in sandboxed network conditions; tests still passed.
```

Lifecycle public-id-only regression:

```bash
cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_trading_position_lifecycle_router.py
```

Result:

```text
Ran 16 tests in 1.253s
OK
```

Scope covered:

- Lifecycle read route remains `TradingPosition.public_id` only.
- Truth event narrative PATCH uses `TradingPosition.public_id` + `PositionEvent.public_id`.
- Narrative / C5 fields update on `position_events` and return an updated lifecycle envelope with `meta.source = MANUAL`.
- Truth dividend write creates `PositionEvent(DIVIDEND)`, links `AccountLedgerEntry(DIVIDEND)`, and returns `ledger_summary.total_dividends`.
- Truth manual adjustment write creates `PositionEvent(MANUAL_ADJUSTMENT)`, links `AccountLedgerEntry(CASH_ADJUSTMENT)`, returns `ledger_summary.total_adjustments`, leaves FIFO quantity / realized PnL unchanged, and rejects zero-amount no-op adjustments without mutating events or ledger entries.
- Truth trade event write covers `REDUCE` and full `CLOSE`: it appends trade `PositionEvent`s, replays FIFO, updates truth aggregate realized PnL/fees/status, links `AccountLedgerEntry(REALIZED_PNL)`, returns the updated lifecycle, and rejects partial `CLOSE` with 422 before mutating events.
- Truth trade event writes now append a transactional `OutboxEvent` in the same DB transaction so derived refresh work has a durable enqueue signal.
- Truth trade event write covers `ADD`: it appends `PositionEvent(ADD)`, replays FIFO into the position aggregate, and does not create a cash ledger entry when there is no realized PnL.
- Truth trade event reversal covers latest active `ADD / REDUCE / CLOSE` events: it appends `PositionEvent(REVERSAL)`, keeps the original event for audit, excludes the reversed event from FIFO replay, writes an offsetting realized PnL ledger entry when needed, rejects duplicate reversals, rejects non-latest active trade events, and blocks `OPEN` reversal until position void/archive semantics exist.
- Closed truth positions reject additional trade events such as `ADD` with 422 before mutating events.
- Internal numeric event ids are rejected by the truth event write route.

Timeline cursor/limit regression:

```bash
cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_timeline_home_router.py
```

Result:

```text
Ran 10 tests in 0.634s
OK
```

C3 AccountLedgerEntry regressions:

```bash
cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_trading_truth_models.py
cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_legacy_truth_sync.py
cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_trading_position_lifecycle_router.py
cd backend && ../.venv313/bin/python -m unittest discover -s tests -p 'test_public_id_*routes.py'
cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_alembic_chain.py
```

Result:

```text
truth models: 1 OK
legacy truth sync: 4 OK
lifecycle router: 2 OK
public-id route group: 7 OK
alembic chain: 1 OK
```

C/D async foundation regressions:

```bash
cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_job_models.py
cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_outbox_models.py
cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_alembic_chain.py
```

Result:

```text
job models: 2 OK
job service: 13 OK
business lock service: 3 OK
idempotency service: 3 OK
outbox models: 3 OK
outbox relay CLI: 2 OK
job worker CLI: 4 OK
derived refresh handlers: 1 OK
admin jobs API: 7 OK
alembic chain: 1 OK
```

Scope covered:

- D1 job foundation has `JobDefinition`, `JobRun`, `JobRunEvent`, and `IdempotencyKey` SQLAlchemy models.
- Alembic head creates `job_definitions`, `job_runs`, `job_run_events`, and `idempotency_keys`.
- Job runs can persist status, retry policy, payload, queued event trail, and idempotency-key linkage.
- D3 business lock foundation has `BusinessLock` / `business_locks` model, migration, and service coverage for active-owner exclusion, expired lock takeover, and owner-validated release.
- D3 idempotency foundation has `idempotency_service` coverage for canonical request hashing, same-key/same-payload replay, same-key/different-payload rejection, and completed response storage on `IdempotencyKey`.
- D3 minimum job execution service can claim due queued/retrying jobs, lock them to a worker, heartbeat running locks, recover stale running locks into the same retry/final-fail state machine, acquire/release payload-declared business locks, retry when a business lock is unavailable without executing the handler, increment attempt count, record start events, dispatch registered handlers by `JobDefinition.key`, complete jobs successfully, schedule retries, and mark exhausted jobs failed.
- D3 local DB worker CLI can optionally recover stale running jobs before processing, process a bounded batch of due jobs, commit each processed job, rollback/close on failure, and consume a queued job produced by outbox relay through a registered handler while releasing the derived timeline business lock.
- D3 `derived.timeline.refresh` bridge handler can read the truth lifecycle for a `trading_position_public_id` and return an auditable refresh result summary for the job run.
- D4 admin job API can list jobs by status/queue, read a job detail with definition, payload, result, error, timing/lock fields, and event history, requeue failed/retrying jobs for immediate execution, and cancel queued/retrying jobs while rejecting unsafe completed/running status transitions.
- D2 outbox foundation has `OutboxEvent` SQLAlchemy model and `outbox_events` migration.
- Outbox events can persist aggregate reference, event type, queue, dedupe key, dispatch payload, pending status, and attempt metadata.
- Outbox relay service can turn pending outbox rows into queued `JobRun`s with a status event and idempotency-key record, then mark the outbox row `PUBLISHED`.
- Truth-derived outbox relay now adds a default `derived.timeline.refresh` business lock keyed by `trading_position_public_id`, so worker execution can avoid concurrent refreshes for the same trading position.
- Outbox relay crash-resume path reuses an existing `IdempotencyKey`/`JobRun` instead of creating duplicates, while still marking the pending outbox row `PUBLISHED` and recording a relay attempt.
- Outbox relay CLI can run one DB relay batch with a configurable limit, commit successful relays, and rollback/close the session on failure.

C4 FIFO accounting service regressions:

```bash
cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_trading_accounting_service.py
cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_legacy_truth_sync.py
cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_position_accounting_recalculation.py
cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_public_id_leaf_routes.py
cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_public_id_routes.py
cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_trading_position_lifecycle_router.py
```

Result:

```text
accounting service: 4 OK
legacy truth sync: 5 OK
legacy batch router recalculation: 1 OK
public-id leaf routes: 2 OK
lifecycle router: 16 OK
public-id route group: 6 OK
```

Scope covered:

- FIFO lot matching for long and short positions.
- Summary-level fee netting.
- Legacy truth sync derives truth aggregate PnL, event realized PnL, and ledger amount from FIFO event replay instead of legacy `realized_pnl`.
- Legacy `Position / TradeBatch` recalculation now uses the same FIFO service for batch PnL, open quantity, realized PnL, and remaining open-lot cost basis.
- Open-position mark-to-market helper covers long/short unrealized PnL, market value, change percent, and display FX conversion; positions and dashboard routes now call it instead of local hand-written formulas.
- Import confirmation no longer precomputes exit PnL before recalculation; batch PnL is assigned by the centralized FIFO path.
- Account route market value/NAV now uses signed mark-to-market values so short positions enter account equity as liabilities.
- Account and dashboard cash read paths now prefer `initial_balance + AccountLedgerEntry` when an opening balance exists, with legacy `cash_balance` fallback for accounts that do not yet have complete ledger history.
- Account create now writes an `OPENING_BALANCE` `AccountLedgerEntry` for non-zero `initial_balance`, and the cash read model uses that ledger entry without double-counting `initial_balance`.
- Account cash balance PATCH now writes a `MANUAL_CASH_ADJUSTMENT` `AccountLedgerEntry` delta and returns the ledger-derived target balance.
- Truth position dividend write path creates a `PositionEvent(DIVIDEND)` and linked `AccountLedgerEntry(DIVIDEND)`, then returns an updated lifecycle with `ledger_summary.total_dividends`.
- Truth position manual adjustment write path creates a `PositionEvent(MANUAL_ADJUSTMENT)` and linked `AccountLedgerEntry(CASH_ADJUSTMENT)`, then returns an updated lifecycle with `ledger_summary.total_adjustments`.
- Truth position trade event write path covers manual `REDUCE` and full `CLOSE`, replaying FIFO into `TradingPosition` aggregates/status and syncing realized PnL into `AccountLedgerEntry(REALIZED_PNL)`.
- Truth position latest-event reversal path preserves audit trail and replays FIFO without the reversed event, while realized PnL ledger effects are offset through a separate `REVERSAL` event ledger entry.

C2 + C5 truth-first detail entry and evidence/AI sidecar regression:

```bash
node --experimental-strip-types --test frontend/tests/*.test.mts
```

Result:

```text
tests 29
pass 29
fail 0
```

Scope covered:

- Single-trade detail can prefer `TradingPosition.public_id` lifecycle data.
- Lifecycle adapter exposes auditable evidence and AI sidecar summaries.
- Lifecycle adapter exposes a truth narrative draft that targets the `thesis_block.source_event_public_id` event for edits.
- Truth detail UI renders `evidence_list` and `ai_sidecar` as first-class sections when present.
- Detail UI exposes a separate truth narrative editor that writes C5 narrative fields to `PositionEvent` and refreshes lifecycle.
- Frontend API client exposes `createTradingPositionTradeEvent`, and batch form mapping sends ENTRY as `ADD`, partial EXIT as `REDUCE`, and full EXIT as `CLOSE`.
- `add-batch` and new-position existing-holding add flows write `TradingPosition / PositionEvent` first when a truth lifecycle can be resolved, with legacy batch fallback for migration data.
- Legacy `Position / TradeBatch` detail edit controls become read-only migration badges when truth lifecycle is available; backend latest-event reversal and guarded frontend exposure now exist, while broader historical reversal and manual adjustment semantics still need a follow-up slice.
- Legacy whole-position delete is disabled once truth lifecycle is available, so destructive mutation waits for a formal truth reversal/adjustment operation.
- Frontend API client exposes `reverseTradingPositionTradeEvent`, lifecycle adapter exposes `getLifecycleReversalAction`, and the detail page only enables reversal for the latest unreversed `ADD / REDUCE / CLOSE` event surfaced by the truth lifecycle.
- Frontend API client exposes `createTradingPositionManualAdjustment`, and the detail page can record position-level cash adjustments into the truth adjustment route without touching FIFO or realized PnL.
- D4 frontend admin jobs slice exposes `adminAPI.listJobs/getJob/requeueJob/cancelJob`, admin job adapter regressions for status counts/actions, and `/admin/jobs` control-room UI for list/detail/requeue/cancel.

Build limitation:

```bash
cd frontend && npm run build
```

Result:

```text
next: command not found
```

Reason:

- This dev worktree does not currently have `frontend/node_modules` with the Next.js binary installed.

Diff hygiene:

```bash
git diff --check
```

Result:

```text
OK
```

## Current Plan State

- Timeline and lifecycle user-facing paths are explicitly marked as `Bridge landed / partial`.
- `/api/trading-positions/{position_public_id}/lifecycle` is now public_id-only for ordinary user paths.
- `/api/positions/{id}/truth-lifecycle` remains labeled as the legacy migration bridge.
- `/api/timeline/home` now has bridge-level `limit` / `cursor` support over stabilized timeline event cards.
- `AccountLedgerEntry` foundation is landed with migration, legacy realized PnL bridge, transaction cash bridge, and lifecycle `cash_effects` consumption.
- Account cash balance/read models now have a ledger-derived read path for accounts with an opening balance; account create writes formal opening-balance ledger entries, account cash PATCH writes manual cash-adjustment entries, and truth position dividend writes create dividend ledger entries.
- C4 FIFO core is started: `trading_accounting_service` handles long/short FIFO realized PnL, fee netting, remaining open-lot cost basis, mark-to-market unrealized calculations, and signed account market values; legacy truth sync, legacy batch router/import recalculation, positions open-position display, dashboard open-position aggregation, account NAV routes, cash read models, account opening-balance writes, manual cash-adjustment writes, truth dividend writes, and the first truth trade event write route now use centralized accounting/ledger helpers.
- Post-boundary `C2 + C5` slice continued: single-trade detail can load `TradingPosition.public_id` lifecycle directly, render truth lifecycle as the primary narrative, surface evidence refs, and show AI sidecar artifacts when the backend returns them.
- Truth event narrative write slice added: `PATCH /api/trading-positions/{position_public_id}/events/{event_public_id}` updates reason / emotion / confidence / thesis / invalidation / planned exit / sizing / checklist / note on `PositionEvent`; frontend API client exposes `updateTradingPositionEventNarrative`, and detail UI now has a dedicated truth narrative editor using it.
- Frontend trade event write slice started: `add-batch` and new-position existing-holding add flows resolve truth lifecycle and call `POST /api/trading-positions/{position_public_id}/events`; unresolved migration data falls back to legacy batch routes.
- Legacy review/batch/MAE controls are still present only as migration tools; batch edit is read-only and whole-position delete is protected when truth lifecycle is available, while guarded frontend latest-event reversal exposure and position-level manual adjustment entry are wired.
- Truth trade event write slice started: `POST /api/trading-positions/{position_public_id}/events` can append manual `ADD / REDUCE / CLOSE` events to an existing `TradingPosition`; current regression covers `ADD` FIFO replay without cash ledger, `REDUCE` FIFO replay, full `CLOSE` status transition, partial `CLOSE` 422, closed-position `ADD` rejection, realized PnL ledger sync, and latest active event reversal through `POST /api/trading-positions/{position_public_id}/events/{event_public_id}/reverse`.
- Truth manual adjustment slice started: `POST /api/trading-positions/{position_public_id}/adjustments` can append position-level cash adjustments without touching FIFO quantities or realized PnL.
- D1/D2/D3/D4 async foundation started: unified job definition/run/event/idempotency-key tables, outbox event table/model, business lock table/model, and reusable idempotency service are landed; truth position event creation writes durable outbox rows in the same transaction; DB relay can create queued job runs from pending outbox rows and resume safely when an idempotency key already points at an existing job run; truth-derived relay jobs now carry default trading-position refresh locks; local relay CLI can run one bounded relay batch; job execution service can claim, heartbeat, recover stale running jobs, acquire/release payload-declared business locks, dispatch handlers, complete, retry, fail, requeue, and cancel job runs; local DB worker CLI can process bounded due-job batches and optionally recover timed-out running locks before consuming; `derived.timeline.refresh` bridge handler can produce truth lifecycle refresh summaries; admin job API and `/admin/jobs` frontend expose list/detail/requeue/cancel status. Redis queue, final derived materialization, systematic business-lock/idempotency wiring beyond timeline refresh/outbox, and running interrupt/force-cancel semantics are not connected yet.
- The next implementation slice should either harden manual adjustment edge cases or move into broader historical/non-latest reversal design; non-latest reversal remains intentionally blocked until its UX and accounting rules are explicit.

## Next Checkpoint Criteria

- Backend test environment can run targeted and full unittest checks through `.venv313`.
- Public-id-only lifecycle behavior has a failing test first, then passing implementation.
- Timeline `limit` / `cursor` behavior has a failing test first, then passing implementation.
- C3 AccountLedgerEntry foundation has model, migration, sync, route, and lifecycle regressions.
- C4 FIFO accounting service has pure service, legacy truth sync, legacy batch router/import recalculation, positions open-position, dashboard mark-to-market, account signed market value, ledger-derived cash read-model, opening-balance ledger write, manual cash-adjustment write, dividend ledger write, ADD/REDUCE/CLOSE truth trade-event write regressions, latest active trade-event reversal regressions, guarded frontend reversal exposure, and position-level manual adjustment regressions plus frontend entry; frontend add/reduce/close creation is truth-first with legacy fallback, legacy batch edit is read-only and whole-position delete is protected when truth lifecycle exists.
- C2 + C5 truth-first detail entry plus evidence/AI sidecar display has frontend adapter regressions and a documented build limitation if frontend dependencies are absent.
- C2 + C5 truth event narrative write route has backend router regressions and an explicit boundary: narrative fields stay on the narrative PATCH route; price/quantity/PnL recalculation belongs to the trade-event POST route.
- D1 unified job model, D2 outbox event schema/relay/CLI, and D3 minimum job execution state machine plus local DB worker CLI/bridge handler have migration/model/service regressions, including relay crash-resume idempotency, outbox-to-worker local dispatch, heartbeat lock refresh, stale running recovery, business lock acquire/release, handler skip/retry on lock contention, and reusable request idempotency service behavior; Redis worker, final derived materialization, and systematic D3 business-lock/idempotent execution wiring remain pending.
- Frontend adapter tests remain green.
- Stage boundary commit exists on `dev`; next checkpoint should record each focused slice commit separately for `main` vs `dev` review.
