# P10 Progress And Next Development Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the current `dev` branch from a broad platform/frontend migration into a clearly staged next-development queue, then execute the next high-leverage slices without reintroducing legacy coupling.

**Architecture:** Treat P10 as a consolidation phase. Documentation and progress tracking come first, then truth hard-cutover inventory, observability guardrails, frontend API contract boundaries, and finally model modularization once legacy ownership is clear.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, SQLite/PostgreSQL, Next.js 16, React 19, TypeScript, ESLint, Node test runner.

---

## Baseline

Current branch: `dev`
Current HEAD at planning time: `3418a27 docs: mark p9f pushed`
Known untouched user content: `docs/superpowers/demos/`

Recent completed slices:
- P8 upgraded frontend to Next 16 / React 19.
- P9A redesigned Timeline as a decision workbench.
- P9B redesigned Dashboard as a macro workbench.
- P9C redesigned Lifecycle Detail as a truth-first workbench.
- P9D wrapped chart surfaces in schema/freshness/trust boundaries.
- P9E enabled React 19 strict hooks lint globally.
- P9F reduced frontend lint to 0 warnings.

Current strategic boundary:
- `TradingPosition / PositionEvent / AccountLedgerEntry` are the intended truth path.
- `Position / TradeBatch / Transaction / AssetMetadata / DailySnapshot` still exist as legacy, bridge, and migration paths.
- The next major risk is deleting or expanding legacy code without first labeling ownership and migration semantics.

---

## Complete Forward Roadmap

This section is the single forward-plan inventory for all currently planned tasks and features after P9F. Do not treat every item here as one batch. Each major lane should become its own implementation plan before code changes begin.

| Stage | Lane | Planned tasks and features | Depends on | Exit criteria |
|-------|------|----------------------------|------------|---------------|
| P10 | Consolidation and planning | Sync docs, freeze progress, inventory legacy paths, add minimal observability, mark handwritten read-model types, plan model modularization. | P9F complete. | Current docs match `dev`; legacy deletion has an inventory; next code slices are sequenced. |
| P11 | Truth hard cutover | Move ordinary user create/add/reduce/close/review/narrative flows to `TradingPosition / PositionEvent`; make Timeline and Review Inbox pure truth/snapshot-backed; label or remove legacy mutation paths. | P10 legacy inventory. | Legacy `Position / TradeBatch` is no longer the primary write/read path for ordinary users. |
| P12 | Platform contract hardening | Request ID, latency headers, error-code convention, structured logging, release/rollback playbooks, OpenAPI type generation boundary, model modularization. | P10 observability and cutover inventory. | Risky migrations have observability, generated type strategy, and rollback docs. |
| P13 | Risk and review product features | Portfolio risk monitor, daily loss limit checks, risk alert service, notification channel, Dashboard risk display, Timeline/Review Inbox risk cards. | P11 truth/ledger cutover for reliable PnL and exposure. | Users can see current portfolio risk and daily-loss warnings without manual calculation. |
| P14 | Reporting and export | Import template documentation, weekly PDF report backend generation, PDF template, frontend export action, export verification fixtures. | Stable read models and AI artifact outputs. | Users can export a weekly report PDF from stable data sources. |
| P15 | AI analysis workflow | Date range selector, analysis request contract cleanup, artifact-backed analysis history, regression tests for AI assistant flows. | P12 API contract hardening preferred. | Users can run AI analysis over explicit date ranges and revisit auditable outputs. |
| P16 | Market data platform | Split market orchestration from provider adapters, stabilize provider mapping, add repeatable provider validation, expose freshness/degradation metadata. | P12 observability preferred. | Market data failures are explainable, testable, and surfaced with freshness metadata. |
| P17 | Admin and operations | Database backup trigger, secure admin promotion, admin password reset, stale/failed job explanation, safer force-cancel UX, backup/restore drill docs. | P12 observability and admin jobs foundation. | Operators can handle common support tasks from audited admin paths. |
| P18 | Chart renderer migration | Decide final renderer, migrate remaining Recharts renderers, keep `chart.v1` schema stable, add visual/browser smoke coverage. | P9D chart schema wrappers and renderer decision. | Chart renderer can change without changing page data contracts. |
| P19 | Release readiness | Full backend/frontend verification, browser smoke with authenticated state, migration dry run, data backfill rehearsal, release checklist, rollback checklist. | P11-P18 as selected for release scope. | `dev` can be safely reviewed, merged, or released with known rollback paths. |

### Planned Feature Inventory

| Feature / function | Current state | Target state | Dedicated plan to create |
|--------------------|---------------|--------------|--------------------------|
| Legacy truth cutover | Bridge/fallback exists. | Ordinary user flows use truth models as primary path. | `2026-06-10-dev-p10-legacy-cutover-inventory.md`, then a P11 implementation plan. |
| Timeline final read model | Snapshot-first with bridge/rollback support. | Pure truth/snapshot-backed default without legacy primary dependency. | P11 Timeline read-model cutover plan. |
| Lifecycle final mutation semantics | Truth-first for ordinary actions; some legacy migration controls remain. | Clear semantics for historical reversal, `OPEN` reversal, delete/archive, and migration-only controls. | P11 Lifecycle mutation semantics plan. |
| Account ledger completion | Ledger-preferred with legacy fallback. | Account cash and read models fully ledger-derived where history is complete. | P11/P12 ledger cutover plan. |
| Observability | Minimal middleware landed in P10C. | `X-Request-ID`, `X-Response-Time-Ms`, and error-code helper exist; structured logging and route-level error-code adoption remain follow-up work. | P12 platform contract hardening plan. |
| OpenAPI frontend types | `frontend/lib/read-models.ts` is handwritten. | Generated OpenAPI types with stable import boundaries. | P12 API contract generation plan. |
| Backend model modularization | `backend/models.py` is still monolithic. | `backend/models/` package with compatibility exports. | P10E/P12 model modularization plan. |
| Risk alerts | Planned, not implemented. | Risk service, daily loss checks, alert surfaces. | P13 risk alert implementation plan. |
| PDF report export | Planned, not implemented. | Weekly PDF generation and export button. | P14 PDF report implementation plan. |
| AI date range selector | Analysis flow exists; date range UX missing. | Explicit date-range analysis and regression tests. | P15 AI analysis workflow plan. |
| Market provider validation | Providers exist; validation is ad hoc. | Repeatable provider tests and freshness/degradation metadata. | P16 market data platform plan. |
| Admin backup and user ops | CLI/support paths exist; admin UI/API incomplete. | Audited backup trigger, admin promotion, password reset. | P17 admin operations plan. |
| Full chart renderer migration | Recharts renderers remain behind schema wrappers. | Final renderer chosen and migrated if product still wants it. | P18 chart renderer migration plan. |
| Release/rollback readiness | Partial checkpoint records exist. | Release checklist, migration dry run, rollback drill. | P19 release readiness plan. |

### Execution Rules For The Forward Roadmap

- Finish P10 consolidation before deleting legacy code.
- Create one dedicated implementation plan per feature lane before touching code.
- Do not execute P13-P18 in parallel with P11 truth cutover unless their data dependencies are isolated.
- Do not remove legacy tables, models, or API responses until migration-only users and fallback paths are documented.
- Do not add new raw DTO coupling to `frontend/lib/api.ts`; new user-facing pages should prefer read-model adapters.
- Every implementation lane needs a verification block with backend tests, frontend tests, TypeScript, lint, build, and browser smoke when UI changes.

---

## File Structure

P10 should touch these files in this order:

- `docs/TODO.md`: current execution queue and backlog.
- `docs/DEVELOPER_GUIDE.md`: current implementation truth.
- `docs/README.md`: documentation navigation.
- `docs/superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md`: top-level sequencing status.
- `docs/superpowers/plans/2026-06-10-dev-p10-progress-next-plan.md`: this plan and execution log.
- `frontend/lib/read-models.ts`: short-term warning comment for handwritten read-model types.
- `backend/main.py`: observability middleware registration if P10C starts.
- `backend/observability.py`: request id, latency, and error-code helpers if P10C starts.
- `backend/tests/test_observability.py`: observability tests if P10C starts.
- `backend/models.py` or future `backend/models/`: do not split until P10E and only after P10B inventory is complete.

---

## Task 1: Sync Current Progress Documentation

**Files:**
- Modify: `docs/TODO.md`
- Modify: `docs/DEVELOPER_GUIDE.md`
- Modify: `docs/README.md`
- Modify: `docs/superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md`
- Modify: `docs/superpowers/plans/2026-06-10-dev-p10-progress-next-plan.md`

- [x] **Step 1: Confirm branch and dirty state**

Run:

```bash
git status --short --branch
git log -1 --oneline
```

Expected:

```text
## dev...origin/dev
?? docs/superpowers/demos/
3418a27 docs: mark p9f pushed
```

If there are additional user changes, inspect them before editing and do not overwrite unrelated work.

- [x] **Step 2: Update `TODO.md`**

Replace the early Phase-only list with:
- Current progress snapshot.
- P10A-P10E priorities.
- Medium-term backlog for risk alerts, PDF export, AI date range, market data validation, admin operations, chart renderer migration.
- Explicit non-expansion rules for legacy paths.

- [x] **Step 3: Update `DEVELOPER_GUIDE.md`**

Ensure it records:
- Next.js 16.2.7 / React 19.2.7.
- Timeline-first `/` behavior.
- Truth path vs legacy path.
- Alembic as the primary migration path.
- Job/outbox/idempotency/business-lock foundation.
- Current verification commands.

- [x] **Step 4: Update `docs/README.md`**

Ensure it links:
- `DEVELOPER_GUIDE.md`.
- `TODO.md`.
- The platform/frontend sequencing plan.
- The dev checkpoint.
- P8/P9/P10 plans.
- Core specs and appendices.

- [x] **Step 5: Update top-level sequencing plan status**

Run:

```bash
rg -n "\[ \]|Status:|Current state|Pending|Bridge|partial|Partially" docs/superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md
```

Then adjust only items that are clearly complete from P8-P9F:
- Frontend shell/navigation/workbench status.
- Dashboard/Insights chart schema status.
- React 19 / lint quality status if referenced.
- Keep truth hard-cutover and legacy cleanup unchecked.

- [x] **Step 6: Verify docs diff**

Run:

```bash
git diff -- docs/TODO.md docs/DEVELOPER_GUIDE.md docs/README.md docs/superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md docs/superpowers/plans/2026-06-10-dev-p10-progress-next-plan.md
```

Expected:
- No accidental changes to `docs/superpowers/demos/`.
- No claim that legacy models are already removed.
- No claim that P10 implementation is complete before verification.

- [x] **Step 7: Commit docs sync**

Run:

```bash
git add docs/TODO.md docs/DEVELOPER_GUIDE.md docs/README.md docs/superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md docs/superpowers/plans/2026-06-10-dev-p10-progress-next-plan.md
git commit -m "docs: sync dev progress and p10 plan"
```

Expected: commit succeeds on `dev`. Do not stage `docs/superpowers/demos/`.

---

## Task 2: Build Legacy Cutover Inventory Before Code Deletion

**Files:**
- Create: `docs/superpowers/plans/2026-06-10-dev-p10-legacy-cutover-inventory.md`
- Read-only scan: `backend/models.py`
- Read-only scan: `backend/routers/`
- Read-only scan: `backend/services/`
- Read-only scan: `frontend/lib/`
- Read-only scan: `frontend/app/`

- [x] **Step 1: Generate legacy reference scan**

Run:

```bash
rg -n "\b(Position|TradeBatch|Transaction|AssetMetadata|DailySnapshot)\b" backend/routers backend/services frontend/lib frontend/app docs
```

Expected: output includes known legacy paths such as `backend/routers/positions.py`, `backend/routers/dashboard.py`, `backend/routers/timeline.py`, `backend/services/import_service.py`, and `frontend/lib/api.ts`.

- [x] **Step 2: Generate truth reference scan**

Run:

```bash
rg -n "\b(TradingPosition|PositionEvent|AccountLedgerEntry|AssetMaster|TradeInstrument|DerivedTimelineSnapshot|InsightArtifact)\b" backend/routers backend/services frontend/lib frontend/app docs
```

Expected: output shows current truth routes, lifecycle adapters, timeline snapshots, and insight artifacts.

- [x] **Step 3: Write inventory document**

Create `docs/superpowers/plans/2026-06-10-dev-p10-legacy-cutover-inventory.md` with these sections:

```markdown
# P10 Legacy Cutover Inventory

## Primary Truth Paths

| Area | Current owner | Evidence | Cutover status |
|------|---------------|----------|----------------|

## Migration-Only Legacy Paths

| Area | Current owner | Why it remains | Delete condition |
|------|---------------|----------------|------------------|

## Delete Candidates

| File or symbol | Replacement | Required pre-delete verification |
|----------------|-------------|----------------------------------|

## Open Product Decisions

- Historical/non-latest reversal semantics.
- OPEN reversal / void / archive semantics.
- Whole-position delete semantics after truth lifecycle exists.
- Legacy import behavior after truth write path is default.
```

- [x] **Step 4: Verify no code changed**

Run:

```bash
git diff --stat
git diff -- backend frontend
```

Expected: only the inventory document changes; backend and frontend diffs are empty.

- [x] **Step 5: Commit inventory**

Run:

```bash
git add docs/superpowers/plans/2026-06-10-dev-p10-legacy-cutover-inventory.md
git commit -m "docs: inventory legacy truth cutover paths"
```

---

## Task 3: Add Minimal Observability Middleware

**Files:**
- Create: `backend/observability.py`
- Modify: `backend/main.py`
- Create or modify: `backend/tests/test_observability.py`
- Modify: `docs/TODO.md`
- Modify: `docs/superpowers/plans/2026-06-10-dev-p10-progress-next-plan.md`

- [x] **Step 1: Write middleware tests first**

Create `backend/tests/test_observability.py` with tests for:
- Incoming `X-Request-ID` is reused.
- Missing `X-Request-ID` creates a new id.
- Response includes `X-Request-ID`.
- Response includes `X-Response-Time-Ms`.
- `make_error_code("timeline", "missing_position")` returns `TIMELINE_MISSING_POSITION`.

- [x] **Step 2: Run tests and confirm they fail**

Run:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_observability.py
```

Expected: fails because `backend/observability.py` and middleware wiring do not exist yet.

- [x] **Step 3: Implement `backend/observability.py`**

Implementation requirements:
- `make_error_code(namespace: str, error: str) -> str`.
- `get_or_create_request_id(request_id: str | None) -> str`.
- `add_observability_middleware(app) -> None`.
- Middleware must set `X-Request-ID` and `X-Response-Time-Ms`.
- Middleware must not change response body.

- [x] **Step 4: Register middleware in `backend/main.py`**

Import the helper and register it after CORS setup or immediately before router registration:

```python
from observability import add_observability_middleware

add_observability_middleware(app)
```

- [x] **Step 5: Run targeted tests**

Run:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_observability.py
```

Expected: tests pass.

- [x] **Step 6: Run backend full tests**

Run:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests
```

Expected: full backend tests pass. If known network warnings appear, record them without hiding failures.

- [ ] **Step 7: Commit observability slice**

Run:

```bash
git add backend/observability.py backend/main.py backend/tests/test_observability.py docs/TODO.md docs/superpowers/plans/2026-06-10-dev-p10-progress-next-plan.md
git commit -m "feat: add request observability middleware"
```

---

## Task 4: Mark Frontend Read Models As Temporary Handwritten Types

**Files:**
- Modify: `frontend/lib/read-models.ts`
- Modify: `docs/TODO.md`
- Modify: `docs/superpowers/plans/2026-06-10-dev-p10-progress-next-plan.md`

- [ ] **Step 1: Add warning comment**

Add this comment at the top of `frontend/lib/read-models.ts`:

```ts
// Handwritten read-model types. Replace with generated OpenAPI types once backend contracts stabilize.
```

- [ ] **Step 2: Run frontend type and lint checks**

Run:

```bash
cd frontend
./node_modules/.bin/tsc --noEmit --pretty false
npm run lint
```

Expected: both commands exit 0.

- [ ] **Step 3: Commit read-model marker**

Run:

```bash
git add frontend/lib/read-models.ts docs/TODO.md docs/superpowers/plans/2026-06-10-dev-p10-progress-next-plan.md
git commit -m "docs: mark handwritten read model types"
```

---

## Task 5: Decide Backend Model Modularization Boundary

**Files:**
- Create: `docs/superpowers/plans/2026-06-10-dev-p10-model-modularization-plan.md`
- Read-only scan: `backend/models.py`
- Read-only scan: `backend/**/*.py`

- [ ] **Step 1: Count current import surface**

Run:

```bash
rg -n "from models import|import models" backend
wc -l backend/models.py
```

Expected:
- Many `from models import ...` references remain.
- `backend/models.py` is close to 1000 lines.

- [ ] **Step 2: Write modularization plan**

Create `docs/superpowers/plans/2026-06-10-dev-p10-model-modularization-plan.md` with:
- Target module layout.
- Compatibility strategy using `backend/models/__init__.py`.
- Explicit statement that code split should happen after P10B inventory.
- Test command list.
- Rollback strategy.

Recommended target layout:

```text
backend/models/
  __init__.py
  base.py
  core.py
  trading_truth.py
  platform.py
  analytics.py
  ai.py
  legacy.py
```

- [ ] **Step 3: Commit modularization plan only**

Run:

```bash
git add docs/superpowers/plans/2026-06-10-dev-p10-model-modularization-plan.md
git commit -m "docs: plan backend model modularization"
```

Do not split `backend/models.py` in the same slice as the plan.

---

## Task 6: Convert Planned Feature Lanes Into Dedicated Plans

**Files:**
- Modify: `docs/TODO.md`
- Create one dedicated plan per selected lane under `docs/superpowers/plans/`

- [ ] **Step 1: Review P10 completion**

Run:

```bash
rg -n "\[ \]" docs/TODO.md docs/superpowers/plans/2026-06-10-dev-p10-progress-next-plan.md
```

Expected: P10A-P10E status is clear, with no ambiguous half-complete items.

- [ ] **Step 2: Confirm all planned feature lanes are listed**

The forward roadmap must include these lanes:
- P11 Truth hard cutover.
- P12 Platform contract hardening.
- P13 Risk alerts and risk review surfaces.
- P14 PDF report export.
- P15 AI analysis workflow and date ranges.
- P16 Market data platform validation.
- P17 Admin and operations.
- P18 Chart renderer migration.
- P19 Release readiness.

- [ ] **Step 3: Write the next dedicated plan in sequence**

Start with the earliest incomplete lane that is not blocked by product decisions. The dedicated lane plan must include:
- User-facing goal.
- Files to touch.
- Tests to write first.
- Browser smoke requirements if frontend is touched.
- Commit strategy.
- Rollback or stop condition.

- [ ] **Step 4: Keep execution single-lane**

Before implementation, confirm the active lane in `TODO.md`. Leave later lanes in backlog until the active lane is verified and committed.

---

## Acceptance Checklist

- [ ] `TODO.md` accurately shows P10 priorities and medium-term backlog.
- [ ] `DEVELOPER_GUIDE.md` describes current `dev`, not the old main baseline.
- [ ] `docs/README.md` links current plans and specs.
- [ ] Top-level sequencing plan no longer understates P8-P9F progress.
- [x] Legacy cutover has an inventory before deletion starts.
- [x] Observability has request id and latency middleware before more risky cutover work.
- [ ] Handwritten frontend read-model types are marked as temporary.
- [ ] Model modularization is planned before `backend/models.py` is split.
- [ ] `docs/superpowers/demos/` remains untouched and uncommitted.

## Verification Log

- 2026-06-10 P10A docs sync: `git diff --check` exited 0 for tracked documentation changes.
- 2026-06-10 P10A docs sync: trailing-whitespace scan across updated docs and the new P10 plan exited 0 after cleanup.
- 2026-06-10 P10A docs sync: old-version scan found no stale frontend-version or Alembic-not-stable wording; `Dashboard-first` appears only as a contrast in the current-state guide.
- 2026-06-10 P10B inventory: legacy/truth reference scans completed; `docs/superpowers/plans/2026-06-10-dev-p10-legacy-cutover-inventory.md` created and committed in `c4a9b4e`.
- 2026-06-10 P10B inventory: `git diff -- backend frontend` exited 0 before the inventory commit.
- 2026-06-10 P10C observability RED: `../.venv313/bin/python -m unittest discover -s tests -p test_observability.py` failed with `ModuleNotFoundError: No module named 'observability'`.
- 2026-06-10 P10C observability GREEN: targeted observability tests ran 4 tests and passed.
- 2026-06-10 P10C observability regression: full backend unittest discovery ran 150 tests and passed; output included a Yahoo DNS warning from market-data-related code.
