# Task 7 AI Chart Audit Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize AI artifact, chart schema, job status, freshness, and release/rollback contracts so frontend AI/chart migration can proceed without unsupported markdown blobs or opaque async work.

**Architecture:** Add auditable `InsightRun` and `InsightArtifact` contracts that can link every AI-visible artifact to evidence refs and trust metadata. Treat chart schemas as schema-first payloads carried by artifacts/read models, not ad-hoc Recharts props. Expose job status and data freshness through V1 read endpoints before relying on async UX. Document release and rollback gates before hard cutover.

**Tech Stack:** FastAPI, SQLAlchemy ORM, Alembic, pytest, FastAPI TestClient, Next.js TypeScript adapters, Tailwind components.

---

## Files And Responsibilities

- Create `backend/tests/test_insight_artifact_service.py`: proves insight runs/artifacts are auditable and evidence-linked.
- Create `backend/tests/test_insight_artifacts_api.py`: proves V1 public-id API exposes runs/artifacts without internal integer ids.
- Modify `backend/models.py`: add `InsightRun` and `InsightArtifact`.
- Create `backend/services/insight_artifact_service.py`: run/artifact creation and read helpers.
- Create `backend/routers/insight_artifacts.py`: `/api/v1/insights/runs` read APIs.
- Modify `backend/main.py`: include V1 insight artifact router.
- Create `backend/alembic/versions/20260604_0005_task7_ai_chart_audit_contracts.py`: persist insight audit tables.
- Create `frontend/lib/insightArtifacts.ts`: TypeScript DTOs and chart schema contract.
- Create `frontend/tests/task7-insight-artifact-contract.tsx`: compile-only frontend contract.
- Create `docs/release/task7-release-rollback-playbook.md`: release, verification, rollback, and cutover notes.
- Modify `docs/superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md`: mark only verified Task 7 gates complete.

---

### Task 7A: Auditable Insight Runs And Artifacts

**Files:**
- Create: `backend/tests/test_insight_artifact_service.py`
- Create: `backend/tests/test_insight_artifacts_api.py`
- Modify: `backend/models.py`
- Create: `backend/services/insight_artifact_service.py`
- Create: `backend/routers/insight_artifacts.py`
- Modify: `backend/main.py`

- [x] **Step 1: Write failing insight artifact service test**

Assert a service can start an `InsightRun`, attach an `InsightArtifact` with `evidence_refs`, `chart_schema`, `trust_meta`, and return artifacts by public run id.

- [x] **Step 2: Run service test and verify RED**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_insight_artifact_service.py::test_insight_run_artifacts_are_auditable_and_evidence_linked -q`

Expected: FAIL because `services.insight_artifact_service` does not exist.

- [x] **Step 3: Implement models and service**

Add ORM models and minimal service methods for `start_run()`, `add_artifact()`, and `get_run_with_artifacts()`.

- [x] **Step 4: Run service test and verify GREEN**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_insight_artifact_service.py::test_insight_run_artifacts_are_auditable_and_evidence_linked -q`

Expected: PASS.

- [x] **Step 5: Write failing V1 API test**

Assert `/api/v1/insights/runs` and `/api/v1/insights/runs/{run_public_id}` return public ids, evidence refs, chart schema, and no internal integer ids.

- [x] **Step 6: Run API test and verify RED**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_insight_artifacts_api.py::test_v1_insight_runs_expose_auditable_artifacts -q`

Expected: FAIL because the router is not registered.

- [x] **Step 7: Implement router**

Add read APIs and register them in `main.py`.

- [x] **Step 8: Run API test and verify GREEN**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_insight_artifacts_api.py::test_v1_insight_runs_expose_auditable_artifacts -q`

Expected: PASS.

### Task 7B: Chart Schema Frontend Contract

**Files:**
- Create: `frontend/lib/insightArtifacts.ts`
- Create: `frontend/tests/task7-insight-artifact-contract.tsx`

- [x] **Step 1: Write failing frontend compile contract**

Import `InsightArtifact`, `ChartSchema`, and `assertSupportedChartSchema`.

- [x] **Step 2: Run TypeScript and verify RED**

Run: `cd frontend && ./node_modules/.bin/tsc --noEmit --pretty false`

Expected: FAIL because the frontend contract does not exist.

- [x] **Step 3: Implement frontend DTO/schema helpers**

Define schema-first chart types and a narrow validator for `bar`, `line`, `scatter`, and `sankey`.

- [x] **Step 4: Run TypeScript and verify GREEN**

Run: `cd frontend && ./node_modules/.bin/tsc --noEmit --pretty false`

Expected: PASS.

### Task 7C: Migration, Job/Freshness Visibility, And Playbook

**Files:**
- Create: `backend/alembic/versions/20260604_0005_task7_ai_chart_audit_contracts.py`
- Modify: `backend/services/job_service.py`
- Create: `docs/release/task7-release-rollback-playbook.md`

- [x] **Step 1: Add Alembic migration**

Create `insight_runs` and `insight_artifacts` tables.

- [x] **Step 2: Add job status read helpers**

Expose job status and event lines through `JobService.get_job_run_status(job_run_public_id)`.

- [x] **Step 3: Write release/rollback playbook**

Document preflight, migration, frontend cutover, rollback, and verification commands.

### Task 7D: Full Verification And Plan Update

**Files:**
- Modify: `docs/superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md`
- Modify: `docs/superpowers/plans/2026-06-04-task7-ai-chart-audit-contracts-implementation-plan.md`

- [x] **Step 1: Run backend tests**

Run: `cd backend && ../.venv/bin/python -m pytest tests -q`

Expected: PASS.

- [x] **Step 2: Run frontend build**

Run: `cd frontend && npm run build`

Expected: PASS.

- [x] **Step 3: Run Alembic smoke and upgrade**

Run: `cd backend && ../.venv/bin/alembic -c alembic.ini current`

Expected: exits 0.

Run: `cd backend && env DATABASE_URL=sqlite:////private/tmp/tradingnoobs_alembic_task7_verify.db ../.venv/bin/alembic -c alembic.ini upgrade head`

Expected: migrations `20260604_0001` through `20260604_0005` execute.

- [x] **Step 4: Review diff**

Run: `git diff --check`

Expected: no output.

- [x] **Step 5: Update plans**

Mark Task 7 gates complete only after auditable insights, chart schema contract, job visibility helper, playbook, migrations, backend tests, frontend build, and diff check are verified.

**Progress 2026-06-04 Task 7 completion:**
- Added auditable `InsightRun` / `InsightArtifact` ORM models, service helpers, V1 read router, and Alembic revision `20260604_0005_task7_ai_chart_audit_contracts.py`.
- Added backend service/API coverage for evidence-linked artifacts with public ids and no exposed internal integer ids.
- Added frontend `InsightRun`, `InsightArtifact`, and `chart.v1` DTO/schema helpers plus compile contracts for supported `bar`, `line`, `scatter`, and `sankey` schemas.
- Added `JobService.get_job_run_status(job_run_public_id)` coverage for async job visibility.
- Added `docs/release/task7-release-rollback-playbook.md` with preflight, migration, frontend cutover, rollback, and verification notes.
- Added the Task 6 AI sidecar follow-through: `EvidenceLinkedInsightSidecar`, V1 insight artifact client/hook, homepage and lifecycle sidecar placement, and `/insights` auditable artifact stream with legacy AI markdown downgraded to clearly marked read-only text.
- Verification: `cd backend && ../.venv/bin/python -m pytest tests -q` passed with 31 tests; `cd frontend && ./node_modules/.bin/tsc --noEmit --pretty false` passed; `cd frontend && npm run build` passed; `cd backend && ../.venv/bin/alembic -c alembic.ini current` exited 0; temporary SQLite `alembic upgrade head` executed revisions `20260604_0001` through `20260604_0005`; `git diff --check` clean.
- Browser smoke: `http://localhost:3000` rendered Timeline + Review Inbox with the auditable AI sidecar empty state. `/insights` requires an authenticated token before the full page renders, so browser verification there was limited to build/type coverage.
