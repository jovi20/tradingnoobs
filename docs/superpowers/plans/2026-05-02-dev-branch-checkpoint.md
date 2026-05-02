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
tests 23
pass 23
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
Ran 68 tests in 5.239s
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
Ran 14 tests in 1.040s
OK
```

Scope covered:

- Lifecycle read route remains `TradingPosition.public_id` only.
- Truth event narrative PATCH uses `TradingPosition.public_id` + `PositionEvent.public_id`.
- Narrative / C5 fields update on `position_events` and return an updated lifecycle envelope with `meta.source = MANUAL`.
- Truth dividend write creates `PositionEvent(DIVIDEND)`, links `AccountLedgerEntry(DIVIDEND)`, and returns `ledger_summary.total_dividends`.
- Truth trade event write covers `REDUCE` and full `CLOSE`: it appends trade `PositionEvent`s, replays FIFO, updates truth aggregate realized PnL/fees/status, links `AccountLedgerEntry(REALIZED_PNL)`, returns the updated lifecycle, and rejects partial `CLOSE` with 422 before mutating events.
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
lifecycle router: 14 OK
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
- Truth position trade event write path covers manual `REDUCE` and full `CLOSE`, replaying FIFO into `TradingPosition` aggregates/status and syncing realized PnL into `AccountLedgerEntry(REALIZED_PNL)`.
- Truth position latest-event reversal path preserves audit trail and replays FIFO without the reversed event, while realized PnL ledger effects are offset through a separate `REVERSAL` event ledger entry.

C2 + C5 truth-first detail entry and evidence/AI sidecar regression:

```bash
node --experimental-strip-types --test frontend/tests/*.test.mts
```

Result:

```text
tests 23
pass 23
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
- Legacy review/batch/MAE controls are still present only as migration tools; batch edit is read-only and whole-position delete is protected when truth lifecycle is available, while guarded frontend latest-event reversal exposure is now wired and manual adjustment semantics still need follow-up.
- Truth trade event write slice started: `POST /api/trading-positions/{position_public_id}/events` can append manual `ADD / REDUCE / CLOSE` events to an existing `TradingPosition`; current regression covers `ADD` FIFO replay without cash ledger, `REDUCE` FIFO replay, full `CLOSE` status transition, partial `CLOSE` 422, closed-position `ADD` rejection, realized PnL ledger sync, and latest active event reversal through `POST /api/trading-positions/{position_public_id}/events/{event_public_id}/reverse`.
- The next implementation slice should implement formal manual adjustment semantics; broader historical/non-latest reversal remains intentionally blocked until its UX and accounting rules are explicit.

## Next Checkpoint Criteria

- Backend test environment can run targeted and full unittest checks through `.venv313`.
- Public-id-only lifecycle behavior has a failing test first, then passing implementation.
- Timeline `limit` / `cursor` behavior has a failing test first, then passing implementation.
- C3 AccountLedgerEntry foundation has model, migration, sync, route, and lifecycle regressions.
- C4 FIFO accounting service has pure service, legacy truth sync, legacy batch router/import recalculation, positions open-position, dashboard mark-to-market, account signed market value, ledger-derived cash read-model, opening-balance ledger write, manual cash-adjustment write, dividend ledger write, ADD/REDUCE/CLOSE truth trade-event write regressions, latest active trade-event reversal regressions, and guarded frontend reversal exposure; frontend add/reduce/close creation is truth-first with legacy fallback, legacy batch edit is read-only and whole-position delete is protected when truth lifecycle exists, while manual adjustment semantics remain pending.
- C2 + C5 truth-first detail entry plus evidence/AI sidecar display has frontend adapter regressions and a documented build limitation if frontend dependencies are absent.
- C2 + C5 truth event narrative write route has backend router regressions and an explicit boundary: narrative fields stay on the narrative PATCH route; price/quantity/PnL recalculation belongs to the trade-event POST route.
- Frontend adapter tests remain green.
- Stage boundary commit exists on `dev`; next checkpoint should record each focused slice commit separately for `main` vs `dev` review.
