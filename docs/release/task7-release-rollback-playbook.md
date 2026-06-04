# Task 7 AI/Chart Audit Release And Rollback Playbook

## Scope

This playbook covers the Task 7 contract release for auditable AI artifacts, schema-first chart payloads, job status visibility, and data freshness gates.

## Preflight

- Confirm backend migrations apply from an empty database: `cd backend && env DATABASE_URL=sqlite:////private/tmp/tradingnoobs_task7_preflight.db ../.venv/bin/alembic -c alembic.ini upgrade head`.
- Confirm backend tests pass: `cd backend && ../.venv/bin/python -m pytest tests -q`.
- Confirm frontend builds: `cd frontend && npm run build`.
- Confirm no whitespace errors: `git diff --check`.

## Release Steps

1. Apply Alembic migrations through `20260604_0005`.
2. Deploy backend with `/api/v1/insights/runs` read APIs available.
3. Deploy frontend chart/insight DTO contracts before rendering AI sidecars from live artifacts.
4. Keep legacy `/api/insights` read paths available until auditable artifact adoption is verified.
5. Do not render raw AI markdown unless the response is wrapped as an `InsightArtifact` with `trust_meta` and `evidence_refs`.

## Runtime Verification

- Fetch an insight run list and confirm every item has `public_id`, `run_type`, `status`, and no internal `id`.
- Fetch an insight run detail and confirm artifacts include `public_id`, `artifact_type`, `summary`, `evidence_refs`, optional `chart_schema`, and `trust_meta`.
- Confirm supported chart schemas use `schema_version: chart.v1` and one of `bar`, `line`, `scatter`, or `sankey`.
- Confirm job run status responses include public event lines and omit internal ids.

## Rollback

1. Disable frontend use of `/api/v1/insights/runs` and fall back to legacy `/api/insights` pages.
2. Stop new insight artifact writes before downgrading.
3. If database rollback is required, run Alembic downgrade from `20260604_0005` to `20260604_0004` after exporting any needed artifact records.
4. Keep Task 5 read models and Task 6 timeline/lifecycle pages intact; they do not depend on `insight_runs`.

## Cutover Rule

AI sidecars can move from placeholder/legacy content to live artifacts only when the run detail endpoint returns artifact evidence refs, trust metadata, and any chart schema validates against `chart.v1`.
