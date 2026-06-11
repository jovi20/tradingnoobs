# P17 Admin Operations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give operators safe admin paths for database backup, user administration, and job recovery without relying on ad hoc shell access.

**Architecture:** Keep dangerous operations behind existing `get_current_admin`. Use small backend services for backup and user ops, return auditable responses, and make the frontend add confirmation friction before force-cancel or credential-impacting actions.

**Tech Stack:** FastAPI, SQLAlchemy, existing auth/admin router, existing job service, bcrypt password hashing via `auth_service`, Next.js 16, React 19, TypeScript.

---

## Files Likely To Touch

Backend:
- Create: `backend/services/backup_service.py`
- Create: `backend/services/admin_user_service.py`
- Modify: `backend/routers/admin.py`
- Modify: `backend/schemas.py`
- Test: `backend/tests/test_admin_operations_api.py`
- Test: `backend/tests/test_admin_jobs_api.py`
- Test: `backend/tests/test_openapi_contracts.py`

Frontend:
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/lib/navigation.ts`
- Create: `frontend/lib/adapters/admin-ops.ts`
- Create: `frontend/app/admin/ops/page.tsx`
- Modify: `frontend/components/admin/domain/AdminJobsConsole.tsx`
- Test: `frontend/tests/admin-ops-adapter.test.mts`
- Test: `frontend/tests/admin-jobs-adapter.test.mts`

Docs:
- Create: `docs/admin-operations-runbook.md`
- Modify: `docs/TODO.md`
- Modify: `docs/DEVELOPER_GUIDE.md`
- Modify: `docs/superpowers/plans/2026-06-11-dev-p17-admin-operations-plan.md`

## Security Rules

- Every endpoint must require `get_current_admin`.
- Admin promotion must be explicit and cannot demote users in P17.
- Password reset must generate a temporary password and invalidate current sessions if session invalidation is available; if session invalidation is not available, the response must warn that active sessions remain valid.
- Backup V1 supports SQLite file copy. PostgreSQL returns `409 BACKUP_PROVIDER_NOT_CONFIGURED` unless a configured backup command exists.
- Force-cancel UI must require typed confirmation `FORCE CANCEL`.

## Task 1: Add Database Backup Service And Endpoint

**Goal:** admins can trigger a local SQLite backup with an auditable response.

- [ ] Create tests in `backend/tests/test_admin_operations_api.py`:
  - `test_admin_can_trigger_sqlite_backup`
  - `test_non_admin_cannot_trigger_backup`
  - `test_postgres_backup_returns_provider_not_configured`
- [ ] Create `backend/services/backup_service.py` with:
  - `detect_database_backend(database_url)`.
  - `create_sqlite_backup(database_url, backup_dir, now)`.
  - `trigger_database_backup(database_url, backup_dir="backend/backups")`.
- [ ] Add schemas in `backend/schemas.py`:
  - `AdminBackupResponse`
  - `AdminOperationStatus`
- [ ] Add `POST /api/admin/ops/backups` to `backend/routers/admin.py`.
- [ ] Return fields:
  - `status`
  - `backup_id`
  - `path`
  - `database_backend`
  - `created_at`
  - `message`
- [ ] Run:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_admin_operations_api.py
```

- [ ] Commit:

```bash
git add backend/services/backup_service.py backend/routers/admin.py backend/schemas.py backend/tests/test_admin_operations_api.py
git commit -m "feat: add admin database backup trigger"
```

## Task 2: Add Secure Admin User Operations

**Goal:** admins can promote a user and reset a password through audited endpoints.

- [ ] Extend `backend/tests/test_admin_operations_api.py` with:
  - `test_admin_can_promote_user_by_public_id`
  - `test_promote_missing_user_returns_404`
  - `test_admin_can_reset_user_password`
  - `test_password_reset_updates_user_credential_hash`
  - `test_non_admin_cannot_reset_password`
- [ ] Create `backend/services/admin_user_service.py` with:
  - `promote_user_to_admin(db, user_public_id, actor_user)`.
  - `generate_temporary_password(length=18)`.
  - `reset_user_password(db, user_public_id, actor_user)`.
- [ ] Use `services.auth_service.get_password_hash`.
- [ ] Add endpoints:
  - `POST /api/admin/users/{user_public_id}/promote`
  - `POST /api/admin/users/{user_public_id}/reset-password`
- [ ] Return the temporary password only once in the reset response.
- [ ] Add structured log events for promotion and password reset.
- [ ] Run:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_admin_operations_api.py
```

- [ ] Commit:

```bash
git add backend/services/admin_user_service.py backend/routers/admin.py backend/schemas.py backend/tests/test_admin_operations_api.py
git commit -m "feat: add admin user operations"
```

## Task 3: Improve Job Failure And Force-Cancel Safety

**Goal:** operators understand stale/failed jobs and cannot force-cancel by accident.

- [ ] Extend `_job_run_summary` and `_job_run_detail` in `backend/routers/admin.py` with:
  - `stale_reason`
  - `recommended_action`
  - `force_cancel_warning`
- [ ] Define stale logic:
  - `RUNNING` and `locked_at` older than `timeout_seconds` from job definition means stale.
  - if no timeout exists, use 30 minutes.
- [ ] Extend `backend/tests/test_admin_jobs_api.py`:
  - stale running job returns stale reason.
  - failed job returns recommended action `REQUEUE`.
  - force-cancel releases active locks and records warning metadata.
- [ ] Update `frontend/lib/adapters/admin-jobs.ts` and `frontend/components/admin/domain/AdminJobsConsole.tsx`:
  - show stale reason.
  - show recommended action.
  - require typing `FORCE CANCEL` before calling `onForceCancelJob`.
- [ ] Run:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_admin_jobs_api.py
cd ../frontend
node --experimental-strip-types --test tests/admin-jobs-adapter.test.mts
```

- [ ] Commit:

```bash
git add backend/routers/admin.py backend/tests/test_admin_jobs_api.py frontend/lib/adapters/admin-jobs.ts frontend/components/admin/domain/AdminJobsConsole.tsx frontend/tests/admin-jobs-adapter.test.mts
git commit -m "feat: harden admin job recovery ux"
```

## Task 4: Add Admin Operations Page

**Goal:** backup and user ops are discoverable from the app for admins.

- [ ] Extend `frontend/lib/api.ts` with:
  - `adminAPI.triggerBackup(token)`
  - `adminAPI.promoteUser(token, userPublicId)`
  - `adminAPI.resetUserPassword(token, userPublicId)`
- [ ] Create `frontend/lib/adapters/admin-ops.ts` with formatting helpers for backup result and temporary password notice.
- [ ] Add `/admin/ops` page in `frontend/app/admin/ops/page.tsx`.
- [ ] Add navigation item in `frontend/lib/navigation.ts` for admin users.
- [ ] Add tests in `frontend/tests/admin-ops-adapter.test.mts`.
- [ ] Run:

```bash
cd frontend
node --experimental-strip-types --test tests/admin-ops-adapter.test.mts tests/navigation.test.mts
./node_modules/.bin/tsc --noEmit --pretty false
```

- [ ] Commit:

```bash
git add frontend/lib/api.ts frontend/lib/adapters/admin-ops.ts frontend/app/admin/ops/page.tsx frontend/lib/navigation.ts frontend/tests/admin-ops-adapter.test.mts frontend/tests/navigation.test.mts
git commit -m "feat: add admin operations console"
```

## Task 5: Add Operations Runbook And Completion Gate

- [ ] Create `docs/admin-operations-runbook.md` documenting:
  - backup behavior for SQLite and PostgreSQL.
  - admin promotion process.
  - password reset process.
  - stale job explanation.
  - force-cancel risks and required confirmation.
  - restore drill outline.
- [ ] Add docs link to `docs/README.md`.
- [ ] Update `docs/TODO.md` with P17 completion status and P18 as next lane.
- [ ] Run final verification:

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

- [ ] Commit:

```bash
git add docs/admin-operations-runbook.md docs/README.md docs/TODO.md docs/superpowers/plans/2026-06-11-dev-p17-admin-operations-plan.md
git commit -m "docs: complete p17 admin operations gate"
```

## Stop Conditions

- Stop before exposing backup downloads from the browser.
- Stop before adding demotion or account deletion.
- Stop before logging temporary passwords.
- Stop if PostgreSQL backup support would require shell execution without an explicit configured command.
