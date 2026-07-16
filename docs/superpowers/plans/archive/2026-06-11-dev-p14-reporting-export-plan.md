# P14 Reporting And Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users export a weekly trading report PDF from existing weekly report, portfolio, and insight data, while documenting the import template clearly.

**Architecture:** Keep report generation server-side and deterministic. Use the existing weekly report model as the report anchor, add a small PDF rendering service, stream the PDF from Insights routes, and keep frontend export as a thin download action.

**Tech Stack:** FastAPI `StreamingResponse`, SQLAlchemy, ReportLab for PDF V1, existing `WeeklyReport` / Dashboard read models, Next.js 16, TypeScript.

---

## Dependency Decision

Use `reportlab>=4.2.0` for P14 V1 because it is pure-Python friendly and avoids system packages required by HTML-to-PDF renderers such as WeasyPrint.

If ReportLab cannot be installed in the execution environment, stop and switch the plan to HTML export rather than quietly shipping a fake PDF.

## Files Likely To Touch

Backend:
- Modify: `backend/requirements.txt`
- Create: `backend/services/report_export_service.py`
- Modify: `backend/routers/insights.py`
- Test: `backend/tests/test_report_export_service.py`
- Test: `backend/tests/test_insights_report_export.py`
- Test: `backend/tests/test_openapi_contracts.py`

Frontend:
- Modify: `frontend/lib/api.ts`
- Create: `frontend/lib/download.ts`
- Modify: `frontend/app/insights/page.tsx`
- Test: `frontend/tests/insights-report-export.test.mts`

Docs:
- Create: `docs/import-template.md`
- Create: `docs/report-export.md`
- Modify: `docs/TODO.md`
- Modify: `docs/README.md`
- Modify: `docs/superpowers/plans/2026-06-11-dev-p14-reporting-export-plan.md`

## Report Content Contract

Weekly PDF V1 must include:
- Report period.
- Generated timestamp.
- Trades summary.
- Munger evaluation.
- Suggestions.
- Portfolio summary from Dashboard stats when available.
- Risk summary when P13 is complete.
- Evidence footer with source identifiers.

PDF response:
- Endpoint: `GET /api/insights/{report_id}/export/pdf`
- Media type: `application/pdf`
- Header: `Content-Disposition: attachment; filename=tradingnoobs-weekly-report-YYYY-MM-DD.pdf`
- First bytes: `%PDF-`

## Task 1: Document Import Template

**Goal:** make CSV/Excel import expectations clear before adding more export surface.

- [x] Create `docs/import-template.md` with:
  - supported file types: CSV and Excel.
  - exact import template columns from `GET /api/positions/import/template`.
  - two example rows matching the current backend template.
  - validation rules for required fields: time, symbol, direction, action, price, quantity.
  - notes for planned stop loss, strategy, emotion, confidence, reason, commission.
- [x] Add the document to `docs/README.md`.
- [x] Run:

```bash
git diff -- docs/import-template.md docs/README.md
git diff --check
```

- [x] Commit:

```bash
git add docs/import-template.md docs/README.md
git commit -m "docs: document import template"
```

## Task 2: Add PDF Rendering Service

**Goal:** generate a valid PDF bytes object from one `WeeklyReport`.

- [x] Add `reportlab>=4.2.0` to `backend/requirements.txt`.
- [x] Create failing tests in `backend/tests/test_report_export_service.py`:
  - `test_render_weekly_report_pdf_starts_with_pdf_header`
  - `test_render_weekly_report_pdf_includes_report_period_metadata`
  - `test_render_weekly_report_pdf_rejects_report_without_owner`
- [x] Run targeted test and confirm RED:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_report_export_service.py
```

Expected: import failure for `services.report_export_service`.

- [x] Create `backend/services/report_export_service.py` with:
  - `build_weekly_report_pdf(report, portfolio_summary=None, risk_summary=None) -> bytes`
  - `build_report_filename(report) -> str`
  - private text wrapping helper for markdown-ish report fields.
- [x] Run targeted test and confirm GREEN.
- [x] Commit:

```bash
git add backend/requirements.txt backend/services/report_export_service.py backend/tests/test_report_export_service.py
git commit -m "feat: add weekly report pdf renderer"
```

## Task 3: Add Insights PDF Export Endpoint

**Goal:** authenticated users can download their own weekly report PDF.

- [x] Add `GET /api/insights/{report_id}/export/pdf` in `backend/routers/insights.py`.
- [x] Reuse ownership check from `get_weekly_report`.
- [x] Return `404` for missing or cross-user report.
- [x] Return `StreamingResponse` with `application/pdf` and exposed `Content-Disposition`.
- [x] Add tests in `backend/tests/test_insights_report_export.py`:
  - owner can export and receives `%PDF-` bytes.
  - cross-user export is rejected.
  - missing report returns stable error envelope.
- [x] Extend `backend/tests/test_openapi_contracts.py` to assert the route exists.
- [x] Run:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_insights_report_export.py
../.venv313/bin/python -m unittest discover -s tests -p test_openapi_contracts.py
```

- [x] Commit:

```bash
git add backend/routers/insights.py backend/tests/test_insights_report_export.py backend/tests/test_openapi_contracts.py
git commit -m "feat: expose weekly report pdf export"
```

## Task 4: Add Frontend Export Action

**Goal:** users can export from the Insights report list without understanding API URLs.

- [x] Add `downloadBlob(filename, blob)` helper in `frontend/lib/download.ts`.
- [x] Add `insightsAPI.exportWeeklyReportPdf(token, reportId)` to `frontend/lib/api.ts`.
- [x] In `frontend/app/insights/page.tsx`, add an export button to each weekly report row.
- [x] Show per-report export loading state and surface failure as a small inline error.
- [x] Add frontend test `frontend/tests/insights-report-export.test.mts` covering:
  - API path is `/api/insights/{id}/export/pdf`.
  - helper uses filename from `Content-Disposition` when present.
  - fallback filename is stable when the header is absent.
- [x] Run:

```bash
cd frontend
node --experimental-strip-types --test tests/insights-report-export.test.mts
./node_modules/.bin/tsc --noEmit --pretty false
```

- [x] Commit:

```bash
git add frontend/lib/api.ts frontend/lib/download.ts frontend/app/insights/page.tsx frontend/tests/insights-report-export.test.mts
git commit -m "feat: add weekly report pdf export action"
```

## Task 5: Add Export Runbook And Completion Gate

- [x] Create `docs/report-export.md` documenting:
  - PDF endpoint.
  - current V1 content.
  - dependency on ReportLab.
  - local verification steps.
  - known limitations: no custom theme, no chart images, no broker statement attachment.
- [x] Add `docs/report-export.md` to `docs/README.md`.
- [x] Update `docs/TODO.md` with P14 completion status and P15 as next lane.
- [x] Run final verification:

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

- [x] Commit:

```bash
git add docs/report-export.md docs/README.md docs/TODO.md docs/superpowers/plans/2026-06-11-dev-p14-reporting-export-plan.md
git commit -m "docs: complete p14 reporting export gate"
```

## Stop Conditions

- Stop before adding chart screenshots to PDF; that belongs after P18 renderer migration.
- Stop before adding email delivery or scheduled reports.
- Stop before exporting reports for another user.
- Stop if PDF generation requires system packages that are not available in the deployment image.

## Execution Log

Completed on `dev` on 2026-06-11.

Commits:

- `71bf0a9 docs: document import template`
- `1bc6875 feat: add weekly report pdf renderer`
- `e8511ae feat: expose weekly report pdf export`
- `da80ccd feat: add weekly report pdf export action`
- Final documentation gate: `docs: complete p14 reporting export gate`

Verification:

- `backend`: `../.venv313/bin/python -m unittest discover -s tests -p test_report_export_service.py` passed, 3 tests.
- `backend`: `../.venv313/bin/python -m unittest discover -s tests -p test_insights_report_export.py` passed, 3 tests.
- `backend`: `../.venv313/bin/python -m unittest discover -s tests -p test_openapi_contracts.py` passed, 3 tests.
- `frontend`: `node --experimental-strip-types --test tests/insights-report-export.test.mts` passed, 3 tests.
- `frontend`: `./node_modules/.bin/tsc --noEmit --pretty false` passed.
- `frontend`: `npm run lint` passed.
- Final backend gate: `../.venv313/bin/python -m unittest discover -s tests` passed, 185 tests. Existing market-data DNS warning for `MSFT` / `guce.yahoo.com` was observed but did not fail tests.
- Final frontend gate: typecheck passed, lint passed, `node --experimental-strip-types --test tests/*.test.mts` passed, 102 tests. Existing `MODULE_TYPELESS_PACKAGE_JSON` warnings were observed.
- `git diff --check` passed.
