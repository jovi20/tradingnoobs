# P19 Release Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the completed `dev` scope into a release-ready branch with verified migrations, authenticated browser smoke, and explicit rollback paths.

**Architecture:** Treat P19 as a release gate, not a feature lane. It should gather evidence, run migration/backfill rehearsals, document remaining risks, and only then decide whether to merge, tag, or keep `dev` as a staging branch.

**Tech Stack:** Git, Alembic, FastAPI unittest suite, Next.js 16, React 19, Node test runner, in-app browser smoke, existing release rollback playbook.

---

## Release Scope Rule

P19 can be run after any chosen subset of P13-P18. The release checklist must explicitly say which lanes are included:
- P13 Risk Review Product Features
- P14 Reporting And Export
- P15 AI Analysis Workflow
- P16 Market Data Platform
- P17 Admin Operations
- P18 Chart Renderer Migration

If a lane is skipped, the release checklist must mark it as excluded with the reason.

## Files Likely To Touch

Docs:
- Create: `docs/release-readiness-checklist.md`
- Modify: `docs/release-rollback-playbook.md`
- Modify: `docs/TODO.md`
- Modify: `docs/README.md`
- Modify: `docs/superpowers/plans/2026-06-11-dev-p19-release-readiness-plan.md`

Backend / Ops:
- Modify if needed: `backend/ops/`
- Test-only or script if needed: `backend/tests/test_alembic_chain.py`

Frontend:
- Modify only if smoke reveals release-blocking UI issues.

## Task 1: Freeze Release Scope And Evidence Matrix

**Goal:** create one checklist that says exactly what is in the release.

- [x] Create `docs/release-readiness-checklist.md` with sections:
  - release branch and commit range.
  - included lanes.
  - excluded lanes.
  - verification evidence.
  - migration evidence.
  - browser smoke evidence.
  - rollback steps.
  - known residual risks.
- [x] Record current branch and commit:

```bash
git status --short --branch
git log -1 --oneline
git log --oneline origin/dev..dev
```

- [x] Record the exact P13-P18 lane completion states from `docs/TODO.md`.
- [x] Commit:

```bash
git add docs/release-readiness-checklist.md docs/TODO.md
git commit -m "docs: start p19 release readiness checklist"
```

## Task 2: Full Automated Verification

**Goal:** prove backend and frontend tests pass from a clean working tree except documented untracked user content.

- [x] Run backend tests:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests
```

- [x] Run frontend typecheck:

```bash
cd frontend
./node_modules/.bin/tsc --noEmit --pretty false
```

- [x] Run frontend lint:

```bash
cd frontend
npm run lint
```

- [x] Run frontend Node tests:

```bash
cd frontend
node --experimental-strip-types --test tests/*.test.mts
```

- [x] Run whitespace and status checks:

```bash
git diff --check
git status --short --branch
```

- [x] Paste summarized results into `docs/release-readiness-checklist.md`, including known benign warnings.
- [x] Commit:

```bash
git add docs/release-readiness-checklist.md
git commit -m "docs: record p19 automated verification"
```

## Task 3: Migration And Backfill Rehearsal

**Goal:** verify schema and derived-data paths can be reproduced without guessing.

- [x] Run Alembic chain tests:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_alembic_chain.py
```

- [x] Run targeted tests for truth/snapshot/backfill paths:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_legacy_truth_sync.py
../.venv313/bin/python -m unittest discover -s tests -p test_derived_refresh_handlers.py
../.venv313/bin/python -m unittest discover -s tests -p test_derived_timeline_read_service.py
```

- [x] Document migration command order in `docs/release-readiness-checklist.md`:
  - database backup.
  - Alembic upgrade.
  - truth sync/backfill command or test-backed service path.
  - derived timeline refresh.
  - smoke check.
- [x] Update `docs/release-rollback-playbook.md` if any rollback step is missing for included lanes.
- [x] Commit:

```bash
git add docs/release-readiness-checklist.md docs/release-rollback-playbook.md
git commit -m "docs: record migration rehearsal"
```

## Task 4: Authenticated Browser Smoke

**Goal:** verify the real app flows after login, including the P11 blocker that remains open.

- [x] Start backend and frontend using the normal local commands for this repo.
- [x] Log into the app with a test user.
- [x] Smoke these routes:
  - `/`
  - `/timeline`
  - `/dashboard`
  - `/positions`
  - `/positions/[id]`
  - `/positions/[id]/add-batch`
  - `/positions/new`
  - `/insights`
  - `/settings`
  - `/admin/jobs` as admin.
- [x] For each route, record:
  - loaded or failed.
  - visible primary content.
  - console errors.
  - network errors.
- [x] If a blocking issue appears, fix it in a separate commit before continuing.
- [x] Update `docs/release-readiness-checklist.md` with smoke evidence.
- [x] Commit:

```bash
git add docs/release-readiness-checklist.md
git commit -m "docs: record authenticated browser smoke"
```

## Task 5: Release Decision And Rollback Drill

**Goal:** make the final release decision explicit.

- [ ] In `docs/release-readiness-checklist.md`, add one release decision:
  - `READY_TO_MERGE`
  - `READY_FOR_STAGING_ONLY`
  - `BLOCKED`
- [ ] If `BLOCKED`, list exact blockers and owners.
- [ ] If ready, document:
  - merge target.
  - backup file or backup command.
  - release tag candidate.
  - rollback feature flags and commands.
- [ ] Re-run:

```bash
git diff --check
git status --short --branch
```

- [ ] Commit:

```bash
git add docs/release-readiness-checklist.md docs/TODO.md docs/README.md docs/superpowers/plans/2026-06-11-dev-p19-release-readiness-plan.md
git commit -m "docs: complete p19 release readiness gate"
```

## Stop Conditions

- Stop before merging to `main` unless the user explicitly asks for merge.
- Stop before creating a PR unless the user explicitly asks for PR.
- Stop before tagging a release unless the checklist decision is `READY_TO_MERGE` or `READY_FOR_STAGING_ONLY`.
- Stop if authenticated browser smoke cannot be completed; record it as a blocker instead of calling release ready.
