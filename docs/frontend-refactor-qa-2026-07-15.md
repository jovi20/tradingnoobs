# Frontend Refactor QA Report - 2026-07-15

> **SUPERSEDED（2026-07-17）**：本文是 2026-07-15 的历史前端回归记录，不是当前交易日志 Beta 的可用功能或验收清单。`JRN-001` 已将 arbitrary manual cash adjustment 排除在 release contract 外；当前前端不得提供该写入入口，纠错只能走关联 reversal/void。

## Summary

- Environment: local Next.js 16.2.7 + FastAPI + SQLite
- Account: `test@example.com` (admin)
- Browser coverage: desktop 1440x900 and mobile 390x844
- Automated checks:
  - Frontend Node tests: 140 passed
  - Frontend TypeScript: passed
  - Frontend ESLint: passed
  - Backend pytest suite: 294 passed
  - Alembic current revision from repository root and `backend/`: `9cad10111213 (head)`
- Browser flows covered: login/logout, invalid login, invalid invite registration, timeline, dashboard, positions list, position create, checklist, add/close event, position detail, strategies create/edit, calendar journal, import account selection/template request, insights configuration error, settings save, account create/update, cash transaction, command palette, admin ops, backup, platform configuration, and responsive layout.
- External IBKR, Binance, LLM calls and import confirmation with a real uploaded workbook were not executed because the local environment has no credentials or user-supplied import file.

## Resolution Update

All nine original findings are fixed and verified on 2026-07-15.

| Bug | Status | Verification |
| --- | --- | --- |
| QA-001 | Fixed | Account PATCH accepts metadata only; saving the note did not add a ledger row or change cash. A normal `+1040 USD` compensating deposit restored cash while retaining the original `-1040` audit row. |
| QA-002 | Superseded | 当时验证了 truth narrative 与 cash adjustment dialog；JRN-001 现只保留 truth narrative，cash adjustment 写入入口已移除。 |
| QA-003 | Fixed | List, dashboard, detail, and close form agree on AAPL remaining quantity `1` and average price `110`; the close limit is `1`. |
| QA-004 | Fixed | Create and event flows use the legacy position public ID as the canonical browser route; truth UUIDs resolve back to it. |
| QA-005 | Fixed | Local startup runs Alembic before the API; SQLite URLs resolve consistently from `backend/`. |
| QA-006 | Fixed | Desktop navigation shows a separated `管理` section with `运维` and `任务`. |
| QA-007 | Fixed | Confirmed icon-only controls now have accessible names, including mobile admin navigation and calendar dates. |
| QA-008 | Fixed | Invalid login displays `邮箱或密码错误` in an accessible alert; unknown English API errors use Chinese fallbacks. |
| QA-009 | Fixed | `backend/requirements-dev.txt` declares pytest and the documented pytest command passes. |

## Bugs

### QA-001 - P0 - Editing account metadata can silently erase cash

Steps:

1. Create an account with zero cash.
2. Add a `1000 USD` deposit from the account detail page.
3. Confirm Available Cash becomes `1000` (the ledger read model was `1040` after realized PnL).
4. Change only the account note and click `更新基本信息`.

Actual:

- `refreshData()` refreshes `account` and transactions but leaves the edit `form` stale.
- Saving the note submits the stale `cash_balance=0` from the form.
- The backend treats it as an intentional cash calibration and writes a `-1040 USD` `CASH_ADJUSTMENT` ledger entry.
- Available Cash becomes `0` while the original `1000 USD` deposit remains in transaction history.

Database evidence from this run:

```text
DEPOSIT          +1000  TRANSACTION
REALIZED_PNL       +40  POSITION_EVENT
CASH_ADJUSTMENT  -1040  MANUAL_CASH_ADJUSTMENT
```

Expected:

- Editing name, broker, type, currency, or note must not submit or mutate cash fields.
- 当前 Beta 不提供 manual cash/NAV calibration；资金或交易纠错必须走 release contract 允许的关联 reversal/void。

Code references:

- `frontend/app/(product)/settings/accounts/[id]/page.tsx:45`
- `frontend/app/(product)/settings/accounts/[id]/page.tsx:87`
- `frontend/app/(product)/settings/accounts/[id]/page.tsx:114`
- `backend/routers/accounts.py:191`

### QA-002 - P1 - Truth lifecycle actions render as clickable but do nothing

Steps:

1. Create a new position.
2. Open its detail page.
3. Click `编辑 truth narrative`（历史版本还包含 `记录 cash adjustment`，该入口已由 JRN-001 移除）。

Actual:

- The buttons receive focus, but no modal appears.
- `LifecycleWorkbench` renders whenever `truthLifecycle` exists, but `LifecycleModals` is nested inside the `position && !truthLifecycle` legacy-only branch.
- The actions are therefore unavailable precisely when the truth lifecycle is active.

Expected:

- 当前只要求 truth narrative modal 在 truth lifecycle 下可用；cash adjustment modal 不得存在。

Code references:

- `frontend/app/(product)/positions/[id]/page.tsx:492`
- `frontend/app/(product)/positions/[id]/page.tsx:522`
- `frontend/app/(product)/positions/[id]/page.tsx:984`

### QA-003 - P1 - Truth and legacy quantities diverge after add/close events

Steps and evidence:

1. Create AAPL with quantity `2` at `100`.
2. Add `1` at `110` through the truth event path.
3. Truth lifecycle shows Opened `3`, but the add/close page still shows `当前持有 2` and limits close quantity to `2`.
4. Close `2` at `120`.
5. Truth lifecycle correctly shows Opened `3`, Closed `2`, remaining open `1`, realized net `40`.
6. Positions list and Dashboard still show quantity `2`, average `100`, unrealized PnL `429.72`, and total PnL `430` from the stale legacy position.

Actual:

- Truth writes do not update the legacy `Position` quantity, while major product read surfaces still use that legacy record.
- The close form validates and sets HTML `max` from `position.total_quantity` instead of truth lifecycle open quantity.

Expected:

- All user-facing quantities, close limits, exposure, PnL, list cards, and Dashboard aggregates must use one canonical read model after truth cutover.

Code references:

- `frontend/app/(product)/positions/[id]/add-batch/page.tsx:89`
- `frontend/app/(product)/positions/[id]/add-batch/page.tsx:109`
- `frontend/app/(product)/positions/[id]/add-batch/page.tsx:162`
- `frontend/app/(product)/positions/[id]/add-batch/page.tsx:246`
- `backend/routers/positions.py:267`

### QA-004 - P1 - Create and event-write redirects use an incompatible route ID

Steps:

1. Create a position or submit an add/close event.
2. Observe the redirect to `/positions/{truth_position_public_id}`.

Actual:

- Detail loading requests `/api/positions/{truth_public_id}` and receives `404` before the truth lifecycle request succeeds.
- The resulting truth-only page has no legacy-backed `加/平仓` link.
- Timeline/Daily/Dashboard links instead use the legacy position public ID, producing a different version of the same detail page.

Expected:

- A single public route identifier should resolve both legacy bridge data and truth lifecycle data, or detail actions must be fully truth-native.

Code references:

- `frontend/app/(product)/positions/new/page.tsx:223`
- `frontend/app/(product)/positions/[id]/add-batch/page.tsx:109`
- `frontend/app/(product)/positions/[id]/page.tsx:516`

### QA-005 - P1 - Local startup does not migrate an existing SQLite database

Steps:

1. Start an existing local database with `./start.sh --skip-install` after adding new columns.
2. Log in and load settings.

Actual:

- Startup launches Uvicorn directly without `alembic upgrade head`.
- `GET /api/settings` failed with `sqlite3.OperationalError: no such column: user_settings.ibkr_flex_query_id` until the database was manually repaired.
- The documented root-level Alembic command and the app use a relative `sqlite:///./tradingnoobs.db` from different working directories, which can target different database files.

Expected:

- Local startup should run a migration preflight against the exact database URL used by Uvicorn, or fail with an actionable schema-version error.

Code references:

- `start.sh:281`
- `backend/alembic/env.py:23`
- `README.md:93`

### QA-006 - P2 - Admin navigation items are calculated and then discarded

Actual:

- `getVisibleNavigationItems('admin')` returns `运维` and `任务`.
- Desktop `AppSidebar` filters only `product` and `settings`, never rendering `ops`.
- Mobile intentionally removes `ops` as well.
- Admin pages remain reachable through command search and Settings, but not through normal product navigation.

Expected:

- Render a visibly separated admin/ops section on desktop, consistent with the navigation contract and tests.

Code references:

- `frontend/lib/navigation.ts:20`
- `frontend/components/navigation/AppSidebar.tsx:30`
- `frontend/components/navigation/MobileBottomNav.tsx:28`

### QA-007 - P2 - Icon-only controls lack accessible names

Confirmed examples from browser accessibility snapshots:

- Strategy edit and delete buttons are both unnamed.
- Transaction delete is unnamed.
- Position row action, calendar previous/next month, insight refresh/close, lifecycle modal close, and several back buttons are unnamed.
- The mobile account menu trigger becomes unnamed because the email is hidden below `lg` and no `aria-label` is provided.

Impact:

- Keyboard and screen-reader users cannot distinguish actions.
- Automated browser testing must rely on source order or DOM node IDs.

Code references:

- `frontend/app/(product)/strategies/page.tsx:55`
- `frontend/components/TransactionList.tsx:98`
- `frontend/components/navigation/AppTopBar.tsx:41`
- `frontend/components/positions/lifecycle/LifecycleModals.tsx:44`

### QA-008 - P3 - Chinese authentication UI exposes raw English API errors

Observed:

- Invalid login displays `Incorrect email or password`.
- Invalid invite displays `Invalid invitation code`.

Expected:

- Map API error codes to localized user-facing messages and expose the error container as an accessible alert.

Code references:

- `frontend/app/(auth)/login/page.tsx:23`
- `frontend/app/(auth)/register/page.tsx:42`

### QA-009 - P2 - Documented backend test command is not reproducible

Actual:

- README instructs `pytest`.
- `backend/requirements.txt` does not declare `pytest`, and the prepared virtual environment has no pytest module.
- `python -m unittest discover` was able to run 239 tests, but that is not the documented command and may not cover pytest-specific fixtures.

Expected:

- Add a development/test requirements file or dependency group and document the exact reproducible command.

Code references:

- `README.md:74`
- `backend/requirements.txt:1`

## Follow-up Bugs Found During Fix Verification

### QA-010 - P1 - Transient auth initialization failures clear a valid login

- Actual: any `/api/auth/me` fetch error removed the stored token, including a navigation-aborted request while the server session was still active.
- Fix: API errors retain HTTP status; only explicit `401` or `403` responses invalidate the stored session.
- Verification: unit coverage distinguishes authentication responses from network/5xx failures; normal page-by-page mobile navigation retained the session.

### QA-011 - P2 - Admin operations page overflows on mobile

- Actual: at `390px`, the two-column workbench's intrinsic grid width expanded the document to `433px`.
- Fix: the base grid track now uses `minmax(0, 1fr)` and both child columns allow shrinking.
- Verification: the admin page now measures `390px` viewport / `380px` document width with no horizontal overflow.

### QA-012 - P2 - A successful transaction remains armed for duplicate submission

- Actual: amount and note remained populated after adding a transaction.
- Fix: successful submission clears amount and description and refreshes the transaction timestamp.
- Verification: source regression coverage and account browser flow pass.

### QA-013 - P3 - Lifecycle detail duplicates headings and leaks implementation copy

- Actual: the truth page displayed two AAPL headers, duplicate `持仓中` badges, raw event enums, `股票 / null`, and mixed implementation notes.
- Fix: the lifecycle workbench owns one canonical header, labels are localized, duplicate statuses collapse, and empty metadata is omitted.
- Verification: desktop and mobile screenshots show one header, Chinese event badges, and no `null` text.

## Passed Browser Flows

- Authentication: logout, valid login, invalid password, invalid invite.
- Account: create, read detail, create cash transaction, update metadata without changing cash, and restore the QA ledger through an explicit compensating transaction.
- Strategy: create with required checklist item and edit.
- Trading: create with checklist, truth add event, truth reduce event, detail loading.
- Calendar: position rendering and journal creation.
- Import: account selection and template endpoint returned `200` with attachment response.
- Insights: dimension selection and clear no-LLM configuration feedback.
- Settings: preference save and restore.
- Admin: ops summary, user panel, job empty state, SQLite backup, platform configuration panel.
- Global command palette: open, filter, close.
- Responsive: no document-level horizontal overflow at 1440x900 or 390x844 on tested core pages.

## Test Data Left For Reproduction

- Account: `QA 测试账户`
- Strategy: `QA 趋势策略`
- Position: AAPL, truth opened `3`, reduced `2`, remaining `1`
- Journal: `QA 日历随笔功能验收`
- Transaction: `QA 入金验收` (`1000 USD`)
- Compensating transaction: `QA-001 资金误调补偿（保留原审计记录）` (`1040 USD`)
- Backup: `backend/backups/sqlite-20260715T121930964204Z.db`
- The account cash ledger retains the destructive `-1040` adjustment and the explicit `+1040` compensating deposit; the resulting ledger cash balance is `1040 USD`.
