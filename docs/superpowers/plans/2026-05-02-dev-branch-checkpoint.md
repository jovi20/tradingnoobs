# Dev Branch Checkpoint - 2026-05-02

Last refreshed: 2026-06-08

## Branch

- Worktree: `/Users/a1/vibecoding/tradingnoobs/.worktrees/docs-platform-frontend-contracts`
- Current branch: `dev`
- Baseline branch kept for comparison: `main`
- Stage boundary commit: `e4c6544 feat: land platform foundation and frontend read models`
- Implementation HEAD before the 2026-05-25 docs-only checkpoint refresh: `d4ff1a5 fix: clear job schedule on claim`
- Current implementation HEAD after the 2026-06-08 P8 dependency-hardening refresh: `facdf3e chore: upgrade frontend to next 16`
- Current `main...dev` committed diff should be reviewed from `main` to current `dev`; use focused diffs by area and the stage boundary below to avoid treating the full branch as one undifferentiated patch.

## Current Working Tree Shape

- Stage boundary committed files include:
  - Alembic setup and revisions
  - Backend bootstrap, timeline, trading position, platform config, public id, ledger, and truth sync services
  - Backend tests
- Platform/frontend contract docs
- Timeline/dashboard/settings/position frontend domain components
- Frontend read models, adapters, and adapter tests

Committed implementation diff summary before this docs-only checkpoint refresh:

```text
142 files changed, 22079 insertions(+), 1165 deletions(-)
```

Recent focused commits since the previous checkpoint refresh:

- `facdf3e chore: upgrade frontend to next 16`
- `18a625d docs: record next 16 upgrade baseline`
- `160c4f0 docs: add dev p8 next 16 upgrade plan`
- `61ed189 feat: integrate auditable insight artifacts into dev`
- `d299bb3 feat: idempotently generate weekly reports`
- `74753af feat: idempotently generate AI summaries`
- `3b2d0ea feat: idempotently run AI analysis`
- `0e69508 fix: avoid legacy timeline checks in snapshot-only mode`
- `d4ff1a5 fix: clear job schedule on claim`
- `49b736c docs: refresh idempotency test count`
- `fe04498 fix: restart expired idempotency keys`
- `e434d69 fix: combine feature flag targets with rollouts`
- `9e1938c docs: refresh rollout gate test count`
- `d600780 feat: apply stable feature flag rollouts`
- `4e79e1d docs: refresh actor-target gate test counts`
- `cbd7f41 feat: target timeline feature flags by actor`
- `cb013d6 docs: refresh feature flag service test count`
- `6ee92bc refactor: centralize feature flag resolution`
- `a8e234d docs: refresh timeline quality gate counts`
- `d9c9da4 fix: honor timeline snapshot flag expiry`
- `58a5286 docs: refresh dev checkpoint verification counts`
- `fdc5043 feat: support dividend account-currency fx`
- `ea40603 fix: summarize ledger totals in account currency`
- `f644098 feat: gate timeline snapshot-only feed`

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
Ran 132 tests in 8.800s
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
Ran 24 tests in 1.951s
OK
```

Scope covered:

- Lifecycle read route remains `TradingPosition.public_id` only.
- Truth event narrative PATCH uses `TradingPosition.public_id` + `PositionEvent.public_id`.
- Narrative / C5 fields update on `position_events` and return an updated lifecycle envelope with `meta.source = MANUAL`.
- Truth dividend write creates `PositionEvent(DIVIDEND)`, links `AccountLedgerEntry(DIVIDEND)`, returns `ledger_summary.total_dividends`, and supports optional `Idempotency-Key` replay/conflict behavior to avoid duplicate dividend ledger writes.
- Truth manual adjustment write creates `PositionEvent(MANUAL_ADJUSTMENT)`, links `AccountLedgerEntry(CASH_ADJUSTMENT)`, returns `ledger_summary.total_adjustments`, leaves FIFO quantity / realized PnL unchanged, rejects zero-amount no-op adjustments without mutating events or ledger entries, and supports optional `Idempotency-Key` replay/conflict behavior to avoid duplicate cash ledger writes.
- Truth trade event write covers `REDUCE` and full `CLOSE`: it appends trade `PositionEvent`s, replays FIFO, updates truth aggregate realized PnL/fees/status, links `AccountLedgerEntry(REALIZED_PNL)`, returns the updated lifecycle, and rejects partial `CLOSE` with 422 before mutating events.
- Truth trade event writes now append a transactional `OutboxEvent` in the same DB transaction so derived refresh work has a durable enqueue signal.
- Truth trade event writes now accept an optional `Idempotency-Key`: same user/key/position/payload replays the completed lifecycle response without duplicating `PositionEvent` or `OutboxEvent`; same key with a different payload returns 409.
- Truth trade event write covers `ADD`: it appends `PositionEvent(ADD)`, replays FIFO into the position aggregate, and does not create a cash ledger entry when there is no realized PnL.
- Truth trade event reversal covers latest active `ADD / REDUCE / CLOSE` events: it appends `PositionEvent(REVERSAL)`, keeps the original event for audit, excludes the reversed event from FIFO replay, writes an offsetting realized PnL ledger entry when needed, rejects duplicate reversals, rejects non-latest active trade events, and blocks `OPEN` reversal until position void/archive semantics exist.
- Closed truth positions reject additional trade events such as `ADD` with 422 before mutating events.
- Internal numeric event ids are rejected by the truth event write route.

Timeline cursor/limit and snapshot-only quality-gate regression:

```bash
cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_timeline_home_router.py
```

Result:

```text
Ran 15 tests in 1.281s
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
idempotency service: 4 OK
outbox models: 4 OK
outbox relay CLI: 2 OK
job worker CLI: 4 OK
derived refresh handlers: 1 OK
derived timeline read service: 1 OK
admin jobs API: 7 OK
alembic chain: 1 OK
```

Scope covered:

- D1 job foundation has `JobDefinition`, `JobRun`, `JobRunEvent`, and `IdempotencyKey` SQLAlchemy models.
- Alembic head creates `job_definitions`, `job_runs`, `job_run_events`, and `idempotency_keys`.
- Job runs can persist status, retry policy, payload, queued event trail, and idempotency-key linkage.
- D3 business lock foundation has `BusinessLock` / `business_locks` model, migration, and service coverage for active-owner exclusion, expired lock takeover, and owner-validated release.
- D3 idempotency foundation has `idempotency_service` coverage for canonical request hashing, same-key/same-payload replay, same-key/different-payload rejection, completed response storage on `IdempotencyKey`, and expired-key restart semantics.
- D3 minimum job execution service can claim due queued/retrying jobs, clear their scheduling timestamp, lock them to a worker, heartbeat running locks, recover stale running locks into the same retry/final-fail state machine, acquire/release payload-declared business locks, retry when a business lock is unavailable without executing the handler, increment attempt count, record start events, dispatch registered handlers by `JobDefinition.key`, complete jobs successfully, schedule retries, and mark exhausted jobs failed.
- D3 local DB worker CLI can optionally recover stale running jobs before processing, process a bounded batch of due jobs, commit each processed job, rollback/close on failure, and consume a queued job produced by outbox relay through a registered handler while releasing the derived timeline business lock.
- D3 `derived.timeline.refresh` handler can read the truth lifecycle for a `trading_position_public_id`, return an auditable refresh result summary for the job run, and upsert a minimal `DerivedTimelineSnapshot` row keyed by `user_id + trading_position_public_id`.
- D3 derived timeline materialization foundation has `DerivedTimelineSnapshot` / `derived_timeline_snapshots` model, migration, write-handler coverage, and a small read service for listing recent snapshots; `/api/timeline/home` now mixes materialized snapshot events into the existing legacy bridge feed using truth event type and truth event occurred_at.
- Timeline Home now has a pre-hard-cut `timeline_snapshot_only_enabled` feature flag: when enabled, unexpired, and targeted to the current user or included by stable `rollout_percentage`, `/api/timeline/home` returns only `DerivedTimelineSnapshot` materialized timeline events, hides legacy position/AI/system timeline events, and skips legacy quote stale checks plus LLM config exception building; absence/disabled/expired/untargeted/outside-rollout keeps the default mixed bridge feed.
- Platform config runtime now has a shared `get_feature_flag_enabled` service helper for enabled/expired/additive-actor-target/stable-rollout flag resolution; Timeline Home uses this instead of a router-local flag check.
- D4 admin job API can list jobs by status/queue, read a job detail with definition, payload, result, error, timing/lock fields, associated business locks, and event history, requeue failed/retrying jobs for immediate execution, and cancel queued/retrying jobs while rejecting unsafe completed/running status transitions.
- D2 outbox foundation has `OutboxEvent` SQLAlchemy model and `outbox_events` migration.
- Outbox events can persist aggregate reference, event type, queue, dedupe key, dispatch payload, pending status, and attempt metadata.
- Outbox relay service can turn pending outbox rows into queued `JobRun`s with a status event and idempotency-key record, then mark the outbox row `PUBLISHED`.
- Outbox relay service now records per-event failure metadata: failed relay attempts are isolated with a nested transaction, keep the row retryable as `PENDING`, increment `attempt_count`, store `last_error`, schedule the next `available_at`, and move to `FAILED` after the relay attempt limit.
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
lifecycle router: 24 OK
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
- Truth position dividend write path creates a `PositionEvent(DIVIDEND)` and linked `AccountLedgerEntry(DIVIDEND)`, supports `fx_rate_to_account_ccy`, supports optional `Idempotency-Key` replay/conflict behavior, then returns an updated lifecycle with account-currency `ledger_summary.total_dividends`.
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

## 2026-06-05 Dev Integration Refresh

This refresh records the user-confirmed branch target: work lands on `dev`, not through a PR to `main`.

- Mistaken PR-to-main path was closed: `https://github.com/jovi20/tradingnoobs/pull/1`
- Local `dev` was updated with native dev-architecture adaptations instead of force-merging the older execution branch.
- `origin/dev` now tracks local `dev` at `61ed189f4d64688e7955f577dc7f2ae5d3a77d01`.
- The temporary `frontend/node_modules` symlink used for local frontend verification was removed after verification.
- Remaining local untracked content is `docs/superpowers/demos/`; it is pre-existing/user content and should stay untouched unless explicitly requested.

Additional scope landed in `61ed189`:

- Added auditable AI insight models: `InsightRun` and `InsightArtifact`.
- Added `backend/services/insight_artifact_service.py` and V1 read routes under `/api/v1/insights/runs`.
- Bridged `/api/insights/summary/generate` and `/api/insights/analyze` into audited artifact creation.
- Updated Timeline to prefer artifact-backed AI events.
- Updated lifecycle AI sidecar sourcing from matching artifacts.
- Added frontend artifact types, API client, hook, and evidence-linked sidecar component.
- Integrated the sidecar into Timeline and Insights while keeping legacy AI markdown as read-only migration content.
- Removed the Google `Inter` dependency so local frontend builds do not depend on fetching Google font assets.

Recorded verification from the `61ed189` integration slice:

```text
backend/tests: 135 passed, 20 warnings
frontend tsc --noEmit --pretty false: passed
frontend npm run build: passed
alembic current: exit 0
alembic upgrade head on temp SQLite DB: reached 5e6f7a8b9cad
git diff --check: clean
```

Execution plan created for the next slices:

- `docs/superpowers/plans/2026-06-05-dev-p0-p4-execution-plan.md`

## Current Plan State

- Timeline and lifecycle user-facing paths are explicitly marked as `Bridge landed / partial`.
- `InsightRun / InsightArtifact` is no longer a future-only Task 7 item; it is now the landed auditable AI foundation that Timeline, Lifecycle, and Insights should consume.
- The next execution path is P0-P4: refresh planning truth, harden Timeline Home truth/snapshot contracts, finish Lifecycle Detail cutover, harden async operations, then prepare Dashboard/Insights schema-first migration.
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
- Truth trade event write slice started: `POST /api/trading-positions/{position_public_id}/events` can append manual `ADD / REDUCE / CLOSE` events to an existing `TradingPosition`; current regression covers `ADD` FIFO replay without cash ledger, `REDUCE` FIFO replay, full `CLOSE` status transition, partial `CLOSE` 422, closed-position `ADD` rejection, realized PnL ledger sync, optional `Idempotency-Key` replay/conflict behavior, and latest active event reversal through `POST /api/trading-positions/{position_public_id}/events/{event_public_id}/reverse`.
- Truth manual adjustment slice started: `POST /api/trading-positions/{position_public_id}/adjustments` can append position-level cash adjustments without touching FIFO quantities or realized PnL; optional `Idempotency-Key` replay prevents retry-driven duplicate `CASH_ADJUSTMENT` ledger writes and conflicting payload reuse returns 409.
- Lifecycle ledger summary totals for ledger-backed dividends/adjustments now aggregate `amount_account_ccy`, with original `amount` as a fallback for older rows; manual adjustment regressions cover non-account-currency adjustments.
- D1/D2/D3/D4 async foundation started: unified job definition/run/event/idempotency-key tables, outbox event table/model, business lock table/model, derived timeline snapshot table/model/read service, and reusable idempotency service are landed; truth position event creation writes durable outbox rows in the same transaction; DB relay can create queued job runs from pending outbox rows, resume safely when an idempotency key already points at an existing job run, and record per-event failure metadata for retry/debugging; truth trade event, dividend, manual adjustment, `/api/insights/analyze`, `/api/insights/summary/generate`, and `/api/insights/generate` writes now use optional request idempotency to prevent duplicate `ADD / REDUCE / CLOSE` writes, duplicate `DIVIDEND` ledger writes, duplicate `CASH_ADJUSTMENT` ledger writes, duplicate AI analysis result writes, retry-driven duplicate daily AI summary errors, and retry-driven duplicate weekly report errors during client retry; truth-derived relay jobs now carry default trading-position refresh locks; local relay CLI can run one bounded relay batch; job execution service can claim, heartbeat, recover stale running jobs, acquire/release payload-declared business locks, dispatch handlers, complete, retry, fail, requeue, and cancel job runs; local DB worker CLI can process bounded due-job batches and optionally recover timed-out running locks before consuming; `derived.timeline.refresh` handler can produce truth lifecycle refresh summaries and upsert `DerivedTimelineSnapshot`; `/api/timeline/home` can mix snapshot-backed derived events into the existing feed and can be switched to snapshot-only with `timeline_snapshot_only_enabled`, and that snapshot-only path now avoids legacy quote stale / LLM config exception builders; admin job API and `/admin/jobs` frontend expose list/detail/business-locks/requeue/cancel status. Redis queue, default Timeline Home snapshot-only hard cut, systematic business-lock/idempotency wiring beyond timeline refresh/outbox, and running interrupt/force-cancel semantics are not connected yet.
- The next implementation slice should preferably stay in the D3/D4 hardening lane before expanding into new domains: broaden idempotency/business-lock wiring beyond timeline refresh, define safe running interrupt/force-cancel semantics, and prepare the Timeline Home snapshot-only hard cut.
- Historical/non-latest reversal remains intentionally blocked until its UX and accounting rules are explicit; `OPEN` reversal remains blocked until void/archive semantics exist.
- If we decide to leave truth/async foundation for a new domain, the cleanest next starts are Stage 4 market data provider mapping/orchestration or Stage 5 AI schema/prompt registry/usage-metering foundations.

## Next Checkpoint Criteria

- Backend test environment can run targeted and full unittest checks through `.venv313`.
- Public-id-only lifecycle behavior has a failing test first, then passing implementation.
- Timeline `limit` / `cursor` behavior has a failing test first, then passing implementation.
- C3 AccountLedgerEntry foundation has model, migration, sync, route, and lifecycle regressions.
- C4 FIFO accounting service has pure service, legacy truth sync, legacy batch router/import recalculation, positions open-position, dashboard mark-to-market, account signed market value, ledger-derived cash read-model, opening-balance ledger write, manual cash-adjustment write, dividend ledger write, ADD/REDUCE/CLOSE truth trade-event write regressions, latest active trade-event reversal regressions, guarded frontend reversal exposure, and position-level manual adjustment regressions plus frontend entry; ledger-backed lifecycle totals use account-currency amounts; frontend add/reduce/close creation is truth-first with legacy fallback, legacy batch edit is read-only and whole-position delete is protected when truth lifecycle exists.
- C2 + C5 truth-first detail entry plus evidence/AI sidecar display has frontend adapter regressions and a documented build limitation if frontend dependencies are absent.
- C2 + C5 truth event narrative write route has backend router regressions and an explicit boundary: narrative fields stay on the narrative PATCH route; price/quantity/PnL recalculation belongs to the trade-event POST route.
- D1 unified job model, D2 outbox event schema/relay/CLI, and D3 minimum job execution state machine plus local DB worker CLI/handler have migration/model/service regressions, including relay crash-resume idempotency, relay failure metadata/retry scheduling, truth trade event request idempotency, dividend request idempotency, manual adjustment request idempotency, AI analyze request idempotency, AI summary request idempotency, weekly report request idempotency, outbox-to-worker local dispatch, heartbeat lock refresh, stale running recovery, business lock acquire/release, handler skip/retry on lock contention, reusable request idempotency service behavior including expired-key restart, `DerivedTimelineSnapshot` upsert from `derived.timeline.refresh`, Timeline Home snapshot event mixing, truth event type preservation, truth event occurred_at ordering, user isolation, and the `timeline_snapshot_only_enabled` snapshot-only quality gate including expiry, actor-target, stable-rollout handling, and legacy exception-builder bypass; Redis worker, default Timeline Home snapshot-only hard cut, and systematic D3 business-lock/idempotent execution wiring remain pending.
- Frontend adapter tests remain green.
- Stage boundary commit exists on `dev`; next checkpoint should record each focused slice commit separately for `main` vs `dev` review.

## 2026-06-05 Dev P0-P4 Completion

Branch target remained `dev`; no PR to `main` was created.

Completed stage commits:

- P0: `5c60523 docs: refresh dev p0 p4 execution plan`
- P1: `0c103f5 feat: harden timeline snapshot home contract`
- P2: `d1cbb44 feat: complete truth lifecycle detail cutover`
- P3: `344de3e feat: harden async job operations`
- P4: `c626e2c feat: prepare dashboard insights schema contracts`

Scope completed:

- Timeline Home snapshot-only readiness now includes artifact-backed AI events, trust metadata, audited artifact hrefs, and snapshot-only empty feed behavior.
- Lifecycle Detail is truth-first for ordinary detail behavior; legacy review/batch/delete paths are labeled or disabled as migration tools when truth lifecycle exists.
- Async job operations now distinguish normal queued/retrying cancel from explicit running force-cancel, with lock release and admin UI/API coverage.
- Dashboard now exposes schema-first `chart.v1` chart payloads while retaining legacy allocation arrays for bridge compatibility.
- Insights now reuses the same chart schema builder for analysis artifacts, and frontend AI cards use artifact summaries/evidence/source refs as the primary auditable presentation path.

Verification recorded during the stages:

```text
P1 backend timeline/derived: 17 passed
P1 frontend node tests: 30 passed
P2 backend lifecycle/artifact: 27 passed
P2 frontend node tests: 31 passed
P3 backend job/admin/business-lock: 25 passed
P3 frontend node tests: 31 passed
P4 backend full tests: 141 passed, 20 warnings
P4 frontend node tests: 36 passed
P4 frontend tsc --noEmit --pretty false: passed
P4 frontend npm run build: passed
P4 git diff --check: clean
```

Final verification before closeout:

```text
git diff --check: clean
backend/tests: 141 passed, 20 warnings
frontend tsc --noEmit --pretty false: passed
frontend npm run build: passed
alembic upgrade head on /private/tmp/tradingnoobs_dev_p0_p4_final.db: reached 5e6f7a8b9cad
```

Dependency note:

- `npm ci` was required in `frontend/` to restore local verification dependencies.
- npm reported `next@14.1.0` as deprecated for a security update and reported 4 audit vulnerabilities; this is a dependency maintenance follow-up, not part of the P0-P4 contract work.

Remaining migration-only / intentionally blocked paths:

- Legacy lifecycle and legacy AI markdown surfaces remain read-only or migration-only fallbacks.
- Legacy batch edit/delete controls remain protected when truth lifecycle exists.
- Historical/non-latest reversal and `OPEN` reversal remain blocked until accounting and audit semantics are designed.
- `docs/superpowers/demos/` remains untracked user content and was not touched.

## 2026-06-05 P5 Dependency Security Decision

P5 non-major dependency remediation was started from `1a5b97a docs: add dev p5 p7 execution plan`.

Actions applied locally:

- `npm install next@14.2.35`
- `npm install --save-dev postcss@^8.5.10`
- `npm audit fix`

Audit progress:

```text
Baseline: 4 vulnerabilities (1 critical, 2 high, 1 moderate)
After non-major remediation: 2 vulnerabilities (1 high, 1 moderate)
Resolved from audit output: lodash, picomatch, direct postcss, critical Next advisory set
```

Remaining audit entries:

- `next` severity `high`; npm reports `fixAvailable` as `next@16.2.7` with `isSemVerMajor: true`.
- Nested `next/node_modules/postcss` severity `moderate`; npm reports the same `next@16.2.7` semver-major fix path.

Representative remaining advisory URLs from `npm audit --json`:

- `https://github.com/advisories/GHSA-9g9p-9gw9-jx7f`
- `https://github.com/advisories/GHSA-h25m-26qc-wcjf`
- `https://github.com/advisories/GHSA-ggv3-7p47-pfv8`
- `https://github.com/advisories/GHSA-3x4c-7xq6-9pq8`
- `https://github.com/advisories/GHSA-q4gf-8mx6-v5v3`
- `https://github.com/advisories/GHSA-8h8q-6873-q5fj`
- `https://github.com/advisories/GHSA-3g8h-86w9-wvmq`
- `https://github.com/advisories/GHSA-ffhc-5mcf-pf4q`
- `https://github.com/advisories/GHSA-vfv6-92ff-j949`
- `https://github.com/advisories/GHSA-gx5p-jg67-6x7h`
- `https://github.com/advisories/GHSA-h64f-5h5j-jqjh`
- `https://github.com/advisories/GHSA-c4j6-fc7j-m34r`
- `https://github.com/advisories/GHSA-wfc6-r584-vfw7`
- `https://github.com/advisories/GHSA-36qx-fr4f-26g5`
- `https://github.com/advisories/GHSA-qx2v-qp2m-jg93`

Decision:

- Temporarily accept the remaining Next/PostCSS audit findings because npm only offers a semver-major `next@16.2.7` fix path.
- Continue P6/P7 on the existing Next 14 line after frontend behavior verification.
- Treat the Next 16 / React migration as a separate dependency-hardening task rather than silently expanding P5.

## 2026-06-05 P5-P7 Dev Completion

Stage commits pushed to `origin/dev`:

- `c8fe99c chore: resolve frontend dependency audit findings`
- `e2fd08b feat: default timeline home to snapshot source`
- `7991ce9 feat: expose auditable insight artifact details`
- `bb3d851 feat: add auditable insight artifact detail UI`

Scope completed:

- P5 upgraded the frontend non-major dependency path to `next@14.2.35` and `postcss@^8.5.15`, removed the resolved lodash/picomatch/direct PostCSS audit findings, and recorded the remaining semver-major-only Next/PostCSS advisories.
- P6 made Timeline Home snapshot-first by default and added `timeline_legacy_mixed_feed_enabled` as the explicit mixed-feed rollback flag.
- P7 added user-scoped artifact detail reads at `/api/v1/insights/artifacts/{artifact_public_id}`, frontend artifact detail client/hook support, `/insights/[artifactId]`, an auditable artifact detail card, and Dashboard schema/trust/empty-state metadata display.

Final P5-P7 verification:

```text
git diff --check: clean
backend unittest discovery: 146 tests passed
frontend npm audit --json: 2 accepted remaining vulnerabilities (next high, nested next/node_modules/postcss moderate); both fixAvailable next@16.2.7 isSemVerMajor true
frontend node --experimental-strip-types --test tests/*.test.mts: 41 tests passed
frontend ./node_modules/.bin/tsc --noEmit --pretty false: passed
frontend npm run build: passed; build output included /insights/[artifactId]
alembic upgrade head on /private/tmp/tradingnoobs_dev_p5_p7_final_20260605_retry.db: reached 5e6f7a8b9cad
```

Remaining follow-ups:

- Next 16 / React migration remains a separate dependency-hardening task because npm reports it as the only available fix for the remaining Next/PostCSS advisories.
- `docs/superpowers/demos/` remains untracked user content and was not touched.

## 2026-06-08 P8 Next 16 Dependency Hardening

Stage commits pushed to `origin/dev`:

- `160c4f0 docs: add dev p8 next 16 upgrade plan`
- `18a625d docs: record next 16 upgrade baseline`
- `facdf3e chore: upgrade frontend to next 16`

Scope completed:

- Upgraded frontend framework line to `next@^16.2.7`, `react@^19.2.7`, and `react-dom@^19.2.7`.
- Upgraded React type packages to `@types/react@^19.2.17` and `@types/react-dom@^19.2.3`.
- Upgraded `lucide-react` to `^1.17.0` for React 19 peer compatibility.
- Added a PostCSS override to `^8.5.15`, resolving the nested Next/PostCSS audit finding.
- Migrated `/insights/[artifactId]` and `/settings/accounts/[id]` client pages from page prop params to `useParams()`.
- Migrated lint from removed `next lint` to ESLint CLI with `eslint-config-next`.
- Deferred broad React 19 lint-hardening rules `react-hooks/purity` and `react-hooks/set-state-in-effect` in config; final lint exits 0 with 6 existing warnings.

Final P8 verification:

```text
git diff --check: clean
frontend npm audit --json: 0 vulnerabilities
frontend node --experimental-strip-types --test tests/*.test.mts: 41 tests passed
frontend ./node_modules/.bin/tsc --noEmit --pretty false: passed
frontend npm run lint: passed with 6 warnings
frontend npm run build: passed on Next 16.2.7; build output included /insights/[artifactId], /positions/[id], /positions/[id]/add-batch, and /settings/accounts/[id]
backend unittest discovery: 146 tests passed
alembic upgrade head on /private/tmp/tradingnoobs_dev_p8_next16_final.db: reached 5e6f7a8b9cad
```

Known notes:

- Next 16 build warns that Turbopack inferred `/Users/a1` as workspace root because multiple lockfiles exist; this warning did not block production build.
- Backend tests emitted the known Yahoo/yfinance DNS warning under restricted network conditions and still passed.
- `docs/superpowers/demos/` remains untracked user content and was not touched.
