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

- [ ] **Step 1: Confirm branch and dirty state**

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

- [ ] **Step 2: Update `TODO.md`**

Replace the early Phase-only list with:
- Current progress snapshot.
- P10A-P10E priorities.
- Medium-term backlog for risk alerts, PDF export, AI date range, market data validation, admin operations, chart renderer migration.
- Explicit non-expansion rules for legacy paths.

- [ ] **Step 3: Update `DEVELOPER_GUIDE.md`**

Ensure it records:
- Next.js 16.2.7 / React 19.2.7.
- Timeline-first `/` behavior.
- Truth path vs legacy path.
- Alembic as the primary migration path.
- Job/outbox/idempotency/business-lock foundation.
- Current verification commands.

- [ ] **Step 4: Update `docs/README.md`**

Ensure it links:
- `DEVELOPER_GUIDE.md`.
- `TODO.md`.
- The platform/frontend sequencing plan.
- The dev checkpoint.
- P8/P9/P10 plans.
- Core specs and appendices.

- [ ] **Step 5: Update top-level sequencing plan status**

Run:

```bash
rg -n "\[ \]|Status:|Current state|Pending|Bridge|partial|Partially" docs/superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md
```

Then adjust only items that are clearly complete from P8-P9F:
- Frontend shell/navigation/workbench status.
- Dashboard/Insights chart schema status.
- React 19 / lint quality status if referenced.
- Keep truth hard-cutover and legacy cleanup unchecked.

- [ ] **Step 6: Verify docs diff**

Run:

```bash
git diff -- docs/TODO.md docs/DEVELOPER_GUIDE.md docs/README.md docs/superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md docs/superpowers/plans/2026-06-10-dev-p10-progress-next-plan.md
```

Expected:
- No accidental changes to `docs/superpowers/demos/`.
- No claim that legacy models are already removed.
- No claim that P10 implementation is complete before verification.

- [ ] **Step 7: Commit docs sync**

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

- [ ] **Step 1: Generate legacy reference scan**

Run:

```bash
rg -n "\b(Position|TradeBatch|Transaction|AssetMetadata|DailySnapshot)\b" backend/routers backend/services frontend/lib frontend/app docs
```

Expected: output includes known legacy paths such as `backend/routers/positions.py`, `backend/routers/dashboard.py`, `backend/routers/timeline.py`, `backend/services/import_service.py`, and `frontend/lib/api.ts`.

- [ ] **Step 2: Generate truth reference scan**

Run:

```bash
rg -n "\b(TradingPosition|PositionEvent|AccountLedgerEntry|AssetMaster|TradeInstrument|DerivedTimelineSnapshot|InsightArtifact)\b" backend/routers backend/services frontend/lib frontend/app docs
```

Expected: output shows current truth routes, lifecycle adapters, timeline snapshots, and insight artifacts.

- [ ] **Step 3: Write inventory document**

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

- [ ] **Step 4: Verify no code changed**

Run:

```bash
git diff --stat
git diff -- backend frontend
```

Expected: only the inventory document changes; backend and frontend diffs are empty.

- [ ] **Step 5: Commit inventory**

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

- [ ] **Step 1: Write middleware tests first**

Create `backend/tests/test_observability.py` with tests for:
- Incoming `X-Request-ID` is reused.
- Missing `X-Request-ID` creates a new id.
- Response includes `X-Request-ID`.
- Response includes `X-Response-Time-Ms`.
- `make_error_code("timeline", "missing_position")` returns `TIMELINE_MISSING_POSITION`.

- [ ] **Step 2: Run tests and confirm they fail**

Run:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_observability.py
```

Expected: fails because `backend/observability.py` and middleware wiring do not exist yet.

- [ ] **Step 3: Implement `backend/observability.py`**

Implementation requirements:
- `make_error_code(namespace: str, error: str) -> str`.
- `get_or_create_request_id(request_id: str | None) -> str`.
- `add_observability_middleware(app) -> None`.
- Middleware must set `X-Request-ID` and `X-Response-Time-Ms`.
- Middleware must not change response body.

- [ ] **Step 4: Register middleware in `backend/main.py`**

Import the helper and register it after CORS setup or immediately before router registration:

```python
from observability import add_observability_middleware

add_observability_middleware(app)
```

- [ ] **Step 5: Run targeted tests**

Run:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_observability.py
```

Expected: tests pass.

- [ ] **Step 6: Run backend full tests**

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

## Task 6: Pick The Next Product Feature Only After P10 Consolidation

**Files:**
- Modify: `docs/TODO.md`
- Optional create: one dedicated plan under `docs/superpowers/plans/`

- [ ] **Step 1: Review P10 completion**

Run:

```bash
rg -n "\[ \]" docs/TODO.md docs/superpowers/plans/2026-06-10-dev-p10-progress-next-plan.md
```

Expected: P10A-P10E status is clear, with no ambiguous half-complete items.

- [ ] **Step 2: Choose exactly one product backlog lane**

Choose one:
- Risk alert system.
- PDF report export.
- AI date range selector.
- Market data provider validation.
- Admin operations.
- Full chart renderer migration.

- [ ] **Step 3: Write a separate plan for the chosen lane**

The selected lane must get its own plan with:
- User-facing goal.
- Files to touch.
- Tests to write first.
- Browser smoke requirements if frontend is touched.
- Commit strategy.

- [ ] **Step 4: Do not start multiple product lanes together**

Before implementation, confirm the selected lane in `TODO.md` and leave the other lanes in backlog.

---

## Acceptance Checklist

- [ ] `TODO.md` accurately shows P10 priorities and medium-term backlog.
- [ ] `DEVELOPER_GUIDE.md` describes current `dev`, not the old main baseline.
- [ ] `docs/README.md` links current plans and specs.
- [ ] Top-level sequencing plan no longer understates P8-P9F progress.
- [ ] Legacy cutover has an inventory before deletion starts.
- [ ] Observability has request id and latency middleware before more risky cutover work.
- [ ] Handwritten frontend read-model types are marked as temporary.
- [ ] Model modularization is planned before `backend/models.py` is split.
- [ ] `docs/superpowers/demos/` remains untouched and uncommitted.

## Verification Log

Record exact command outputs here as P10 tasks are executed.
