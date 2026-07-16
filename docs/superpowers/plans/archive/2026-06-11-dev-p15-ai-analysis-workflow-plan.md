# P15 AI Analysis Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make AI analysis explicitly date-ranged, contract-tested, and revisit-able through auditable insight artifacts.

**Architecture:** Preserve the existing `/api/insights/analyze` endpoint and `AnalyticsService.analyze(start_date, end_date)` capability, but harden validation and artifact metadata. Add frontend date controls and a small history view that points users to generated artifact details instead of only transient in-page output.

**Tech Stack:** FastAPI, Pydantic validation, SQLAlchemy, existing `InsightRun` / `InsightArtifact`, Next.js 16, React 19, TypeScript, Node test runner.

---

## Current Baseline

Already exists:
- `backend/schemas.py` has `AnalysisRequest.start_date` and `AnalysisRequest.end_date`.
- `backend/services/analytics_service.py` accepts date range parameters.
- `backend/routers/insights.py` persists `AIAnalysisResult` and creates an `InsightArtifact`.
- `frontend/lib/api.ts` sends `AnalysisRequest`.

Missing:
- Date range validation.
- Frontend date range selection.
- Date range included in artifact `input_refs`, `payload`, and evidence refs.
- Analysis history that is easy to revisit from the UI.
- Regression tests covering date ranges and artifacts together.

## Files Likely To Touch

Backend:
- Modify: `backend/schemas.py`
- Modify: `backend/routers/insights.py`
- Modify: `backend/services/analytics_service.py`
- Test: `backend/tests/test_insights_analysis_workflow.py`
- Test: `backend/tests/test_insight_artifacts_api.py`
- Test: `backend/tests/test_openapi_contracts.py`

Frontend:
- Modify: `frontend/lib/api.ts`
- Create: `frontend/lib/adapters/analysis.ts`
- Modify: `frontend/app/insights/page.tsx`
- Modify: `frontend/components/insights/AnalysisAssistant.tsx`
- Test: `frontend/tests/analysis-adapter.test.mts`
- Test: `frontend/tests/insight-artifact-client.test.mts`

Docs:
- Modify: `docs/TODO.md`
- Modify: `docs/DEVELOPER_GUIDE.md`
- Modify: `docs/superpowers/plans/2026-06-11-dev-p15-ai-analysis-workflow-plan.md`

## Contract Rules

Date range rules:
- `start_date` and `end_date` are optional as a pair.
- If only one side is supplied, return `422`.
- If `start_date > end_date`, return `422`.
- If the range is longer than 366 days, return `422`.
- Date range is inclusive.

Artifact rules:
- `run.input_refs` includes `analysis:<type>` and `date-range:<start>:<end>` when a range is provided.
- Artifact payload includes `analysis_type`, `date_range`, `analysis_result_id`, and `raw_data`.
- Evidence refs include the same date range marker.

## Task 1: Harden Backend Analysis Contract

**Goal:** invalid date ranges fail before analytics or LLM work starts.

- [x] Add failing tests in `backend/tests/test_insights_analysis_workflow.py`:
  - `test_analysis_rejects_start_date_without_end_date`
  - `test_analysis_rejects_end_date_without_start_date`
  - `test_analysis_rejects_reversed_date_range`
  - `test_analysis_rejects_range_longer_than_366_days`
  - `test_analysis_accepts_valid_date_range`
- [x] Run targeted test and confirm RED:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_insights_analysis_workflow.py
```

- [x] Add Pydantic validation to `AnalysisRequest` in `backend/schemas.py`.
- [x] Ensure validation errors return the existing P12B error envelope with `VALIDATION_REQUEST_INVALID`.
- [x] Run targeted test and confirm GREEN.
- [x] Commit:

```bash
git add backend/schemas.py backend/tests/test_insights_analysis_workflow.py
git commit -m "feat: validate ai analysis date ranges"
```

## Task 2: Persist Date Range In Artifact Evidence

**Goal:** every generated analysis artifact explains the exact input window.

- [x] Extend `_create_insight_artifact_for_analysis(...)` in `backend/routers/insights.py` to accept `start_date` and `end_date`.
- [x] Add helper `_analysis_input_refs(analysis_type, start_date, end_date)` returning deterministic refs.
- [x] Add helper `_analysis_date_range_payload(start_date, end_date)` returning:

```json
{
  "start_date": "2026-06-01",
  "end_date": "2026-06-11",
  "label": "2026-06-01 to 2026-06-11"
}
```

- [x] Store the date range payload in artifact payload under `date_range`.
- [x] Add backend tests:
  - generated `InsightRun.input_refs` contains date range.
  - artifact payload contains date range.
  - artifact trust source refs contain date range.
- [x] Run:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_insights_analysis_workflow.py
../.venv313/bin/python -m unittest discover -s tests -p test_insight_artifacts_api.py
```

- [x] Commit:

```bash
git add backend/routers/insights.py backend/tests/test_insights_analysis_workflow.py backend/tests/test_insight_artifacts_api.py
git commit -m "feat: attach date range evidence to ai analysis artifacts"
```

## Task 3: Add Analysis History Endpoint

**Goal:** the Insights page can show recent auditable analysis outputs without scraping artifact detail pages.

- [x] Add `GET /api/insights/analyze/history` to `backend/routers/insights.py`.
- [x] Query `InsightRun` through `InsightArtifactService` or direct SQLAlchemy joins scoped to current user.
- [x] Support query params:
  - `analysis_type`
  - `limit` with default `20`, min `1`, max `50`
- [x] Response item fields:
  - `run_public_id`
  - `artifact_public_id`
  - `analysis_type`
  - `title`
  - `summary`
  - `created_at`
  - `date_range`
  - `href`
- [x] Add tests in `backend/tests/test_insights_analysis_workflow.py`:
  - history lists only current user's artifacts.
  - `analysis_type` filter works.
  - limit is enforced.
- [x] Extend `backend/tests/test_openapi_contracts.py`.
- [x] Run:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_insights_analysis_workflow.py
../.venv313/bin/python -m unittest discover -s tests -p test_openapi_contracts.py
```

- [x] Commit:

```bash
git add backend/routers/insights.py backend/tests/test_insights_analysis_workflow.py backend/tests/test_openapi_contracts.py
git commit -m "feat: add ai analysis history endpoint"
```

## Task 4: Add Frontend Date Range And History

**Goal:** users can run a bounded analysis and revisit past outputs.

- [x] Extend frontend types in `frontend/lib/api.ts`:
  - `AnalysisHistoryItem`
  - `insightsAPI.listAnalysisHistory(token, params)`
- [x] Create `frontend/lib/adapters/analysis.ts` with:
  - `getDefaultAnalysisDateRange(now)` returning last 30 calendar days.
  - `validateAnalysisDateRange(startDate, endDate)` mirroring backend rules.
  - `formatAnalysisDateRangeLabel(...)`.
- [x] Update `frontend/app/insights/page.tsx`:
  - add start/end date inputs near the analysis controls.
  - send `start_date` and `end_date` to `insightsAPI.analyze`.
  - show the selected date label beside results.
  - fetch and render recent history cards linking to `/insights/{artifact_public_id}`.
- [x] Update `frontend/components/insights/AnalysisAssistant.tsx` or replace its usage so it does not remain a date-range-less duplicate flow.
- [x] Add tests:
  - `frontend/tests/analysis-adapter.test.mts` covers default range and validation.
  - `frontend/tests/insight-artifact-client.test.mts` covers history href mapping if client utilities are changed.
- [x] Run:

```bash
cd frontend
node --experimental-strip-types --test tests/analysis-adapter.test.mts tests/insight-artifact-client.test.mts
./node_modules/.bin/tsc --noEmit --pretty false
```

- [x] Commit:

```bash
git add frontend/lib/api.ts frontend/lib/adapters/analysis.ts frontend/app/insights/page.tsx frontend/components/insights/AnalysisAssistant.tsx frontend/tests/analysis-adapter.test.mts frontend/tests/insight-artifact-client.test.mts
git commit -m "feat: add date ranged ai analysis workflow"
```

## Task 5: P15 Completion Gate

- [x] Backend analysis workflow tests pass.
- [x] Insight artifact tests pass.
- [x] Frontend analysis adapter tests pass.
- [x] Full backend tests pass.
- [x] Frontend typecheck, lint, and Node tests pass.
- [x] Authenticated browser smoke covers `/insights` and one `/insights/{artifactId}` detail.
- [x] `docs/TODO.md` marks P15 complete and P16 as next lane.

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

- Task 1 committed as `2f7da40 feat: validate ai analysis date ranges`.
- Task 2 committed as `f2fbe63 feat: attach date range evidence to ai analysis artifacts`.
- Task 3 committed as `e1d125f feat: add ai analysis history endpoint`.
- Task 4 committed as `c071a3b feat: add date ranged ai analysis workflow`.
- Verification completed during P15 execution:
  - Backend full test suite: 196 tests passed.
  - Frontend typecheck: passed.
  - Frontend lint: passed.
  - Frontend Node tests: 106 tests passed.
  - Authenticated browser smoke: `/insights` showed default range `2026-05-13` to `2026-06-11`, recent analysis history, and `P15 Smoke Strategy Health`; `/insights/df8c3544-26b2-40d3-982f-32c49bd6420e` showed summary, legacy markdown, evidence refs, source refs, and `date-range:2026-06-01:2026-06-11` with no new browser errors.
- P15 completion docs updated to mark P16 as the next active lane.

## Stop Conditions

- Stop before changing analysis types or prompt semantics.
- Stop before moving analytics off legacy `Position` data; that deserves a separate truth-native analytics lane.
- Stop before adding scheduled AI analysis.
- Stop if duplicate analysis UI paths cannot be consolidated without breaking the current Insights page.
