# Trading Noobs P19 Release Readiness Checklist

更新时间：2026-06-11
执行分支：`dev`
P19 evidence HEAD：`cabc857 docs: record authenticated browser smoke`
比较范围：`origin/dev..dev`
当前状态：`P19_COMPLETE_READY_FOR_STAGING_ONLY`

本文档是 P19 发布就绪闸门的证据矩阵。当前结论是 `READY_FOR_STAGING_ONLY`：可以作为 `dev` staging 候选继续推进，但本轮不创建 PR、不 merge 到 `main`、不创建 tag。

---

## 1. Branch And Commit Range

Task 5 decision 前观测到的分支状态：

```text
## dev...origin/dev [ahead 58]
 M frontend/next-env.d.ts
 M frontend/tsconfig.tsbuildinfo
?? docs/superpowers/demos/
```

说明：
- `frontend/next-env.d.ts` 与 `frontend/tsconfig.tsbuildinfo` 是本地前端验证生成项，不纳入 P19 文档提交。
- `docs/superpowers/demos/` 是既有未跟踪用户内容，不纳入 P19 提交。
- 本轮不创建 PR、不 merge 到 `main`、不 tag release，除非用户后续明确要求。

`origin/dev..dev` 提交清单：

```text
d6fe118 docs: complete p18 chart renderer migration gate
e5938b5 chore: remove recharts dependency
fbd5bd5 feat: migrate portfolio sankey to svg renderer
f7f13d7 feat: migrate standard charts to svg renderers
438c164 feat: add internal chart geometry helpers
22c675f test: guard chart renderer imports
3989d51 docs: complete p17 admin operations gate
1ff6303 feat: add admin operations console
ebae744 feat: harden admin job recovery ux
3a2161e feat: add admin user operations
9729589 feat: add admin database backup trigger
8071284 docs: complete p16 market data platform gate
ae50afc feat: show market data freshness metadata
d6f45fa feat: add market data freshness metadata
377a632 feat: normalize market provider adapters
907cb07 feat: add market provider routing contracts
c9bf3f7 fix: await market quote endpoint
cf8b356 docs: complete p15 ai analysis workflow gate
c071a3b feat: add date ranged ai analysis workflow
e1d125f feat: add ai analysis history endpoint
f2fbe63 feat: attach date range evidence to ai analysis artifacts
2f7da40 feat: validate ai analysis date ranges
ebed361 docs: complete p14 reporting export gate
da80ccd feat: add weekly report pdf export action
e8511ae feat: expose weekly report pdf export
1bc6875 feat: add weekly report pdf renderer
71bf0a9 docs: document import template
8d442e7 docs: complete p13 risk review gate
d01749f feat: add risk action cards to timeline
800867a feat: surface risk alerts on dashboard
6b2f26f feat: expose portfolio risk summary
a3a4969 docs: plan p13 through p19 roadmap
755836c docs: complete p12b observability gate
35a6336 chore: replace business prints with structured logs
0643e94 feat: add structured logging helper
cda1a3f feat: add backend error response contract
5c1bd4c docs: complete p12 contract hardening gate
31ab8ef docs: add p11 rollback playbook
1c06a7a chore: add generated contract boundary
ac37043 test: snapshot core api contracts
9af3762 test: freeze frontend legacy dto boundaries
7207fb5 docs: complete p11 hard cutover gate
b06f231 feat: isolate legacy trading controls
2c82e54 feat: default timeline to truth snapshots
715816f feat: guard destructive legacy mutations
e9fbafe feat: protect truth narrative from legacy review writes
a7fa1da feat: sync new positions to truth lifecycle
5a70275 feat: harden truth-first trading writes
410df97 docs: plan p11 truth hard cutover
f4c5abe docs: plan backend model modularization
824d101 docs: mark handwritten read model types
a205e77 feat: add request observability middleware
c4a9b4e docs: inventory legacy truth cutover paths
f86e72e docs: sync dev progress and p10 plan
```

P19 evidence commits after initial scope freeze:

```text
cabc857 docs: record authenticated browser smoke
ec7ddb8 docs: record migration rehearsal
2b2d899 docs: record p19 automated verification
3757df3 docs: start p19 release readiness checklist
```

---

## 2. Included Lanes

本次 P19 release scope 包含 P13-P18 全部已完成 lane：

| Lane | 状态 | 关键提交 | 发布范围说明 |
|------|------|----------|--------------|
| P13 Risk Review Product Features | `INCLUDED_COMPLETE` | `6b2f26f`、`800867a`、`d01749f`、`8d442e7` | 组合风险、单日亏损上限、Dashboard 风险栏、Timeline/Review Inbox 风险行动卡。 |
| P14 Reporting And Export | `INCLUDED_COMPLETE` | `71bf0a9`、`1bc6875`、`e8511ae`、`da80ccd`、`ebed361` | 导入模板说明、周报 PDF 渲染、Insights PDF 导出接口与前端操作。 |
| P15 AI Analysis Workflow | `INCLUDED_COMPLETE` | `2f7da40`、`f2fbe63`、`e1d125f`、`c071a3b`、`cf8b356` | 日期范围校验、artifact evidence refs、分析历史接口、Insights 复访入口。 |
| P16 Market Data Platform | `INCLUDED_COMPLETE` | `907cb07`、`377a632`、`d6f45fa`、`ae50afc`、`8071284` | provider routing、normalized adapters、quote freshness/degradation metadata、前端 freshness 标签。 |
| P17 Admin Operations | `INCLUDED_COMPLETE` | `9729589`、`3a2161e`、`ebae744`、`1ff6303`、`3989d51` | 数据库备份触发、管理员晋升、密码重置、job recovery UX、`/admin/ops`。 |
| P18 Chart Renderer Migration | `INCLUDED_COMPLETE` | `22c675f`、`438c164`、`f7f13d7`、`fbd5bd5`、`e5938b5`、`d6fe118` | Recharts import guard、内部 SVG renderer、Portfolio Sankey SVG、`recharts` 依赖移除。 |

Prerequisite scope also present in the same commit range:
- P11 truth hard cutover gate.
- P12 platform contract hardening.
- P12B observability and error contract hardening.
- P10 progress/docs/model modularization planning.

## 3. Excluded Lanes

No P13-P18 lane is intentionally excluded from this release-readiness gate.

Not included as release-ready feature work:
- P10B final legacy model/route/DTO deletion remains future cleanup.
- P10D remaining API DTO contraction remains future cleanup.
- P10E physical `backend/models.py` split remains future cleanup.

---

## 4. Verification Evidence

Current evidence carried into P19:
- P18 completion gate ran backend full suite: 222 tests OK.
- P18 completion gate ran frontend typecheck: exit 0.
- P18 completion gate ran frontend lint: exit 0.
- P18 completion gate ran frontend Node tests: 119 tests OK.
- P18 completion gate ran static Recharts scan: no Recharts import/dependency matches.
- P18 completion gate ran `git diff --check`: exit 0.

P19 Task 2 fresh release-gate evidence:
- Backend full suite: `../.venv313/bin/python -m unittest discover -s tests` ran 222 tests OK.
- Frontend typecheck: `./node_modules/.bin/tsc --noEmit --pretty false` exited 0.
- Frontend lint: `npm run lint` exited 0.
- Frontend Node tests: `node --experimental-strip-types --test tests/*.test.mts` ran 119 tests OK.
- Whitespace check: `git diff --check` exited 0.
- Status check:

```text
## dev...origin/dev [ahead 55]
 M frontend/next-env.d.ts
 M frontend/tsconfig.tsbuildinfo
?? docs/superpowers/demos/
```

Interpretation:
- The automated verification gate is green at P19 Task 2.
- The remaining dirty files are known local generated/user-content items and must remain unstaged.

Known benign warnings to track:
- Backend market tests may warn about offline provider fallback or Yahoo/YFinance DNS resolution.
- Frontend Node tests may warn about `MODULE_TYPELESS_PACKAGE_JSON`.

---

## 5. Migration Evidence

Current status: `P19_TASK_3_PASSED`.

Targeted migration/backfill rehearsal:
- Alembic chain: `../.venv313/bin/python -m unittest discover -s tests -p test_alembic_chain.py` ran 1 test OK.
- Truth sync/backfill: `../.venv313/bin/python -m unittest discover -s tests -p test_legacy_truth_sync.py` ran 5 tests OK.
- Derived refresh handlers: `../.venv313/bin/python -m unittest discover -s tests -p test_derived_refresh_handlers.py` ran 1 test OK.
- Derived timeline read service: `../.venv313/bin/python -m unittest discover -s tests -p test_derived_timeline_read_service.py` ran 1 test OK.

Release migration command order:
1. Trigger or take a database backup before schema/data changes.
2. Run Alembic upgrade using the deployment standard migration command for the target environment.
3. Run or verify truth sync/backfill path for legacy positions using the test-backed `legacy_truth_sync` service path.
4. Run or verify derived timeline refresh handlers to rebuild `DerivedTimelineSnapshot` data.
5. Smoke `/api/timeline/home`, `/`, `/timeline`, `/dashboard`, `/positions`, and `/insights` with authenticated state.
6. Keep `timeline_legacy_mixed_feed_enabled` available as the first Timeline rollback lever.

Rollback playbook update:
- [release-rollback-playbook.md](./release-rollback-playbook.md) now covers P13 risk review, P14 reporting/PDF, P15 AI analysis workflow, P16 market data platform, P17 admin operations, and P18 chart renderer migration.

---

## 6. Browser Smoke Evidence

Current evidence carried into P19:
- P18 authenticated smoke used isolated local SQLite and temporary user `p18-smoke-20260611@example.com`.
- `/timeline` loaded after login with authenticated navigation.
- `/dashboard` loaded chart cards in empty-data state with SVG output and no browser console errors.
- `/insights` loaded after clean reload with no `Failed to fetch` state and no browser console errors.
- Mobile 390px viewport showed no horizontal overflow on `/dashboard` or `/insights`.

P19 Task 4 release-grade authenticated browser smoke:
- Smoke environment: isolated local SQLite database at `/private/tmp/tradingnoobs_p19_smoke_20260611.db`, backend on `127.0.0.1:8000`, frontend on `localhost:51559`.
- Fixture user: `p19-smoke-user-20260611@example.com`.
- Fixture admin: `p19-smoke-admin-20260611@example.com`.
- Fixture data: one USD smoke account and one open AAPL long position with legacy public id `cd001766-034e-41af-b5d0-fabb11852a00`.

| Route | Result | Visible primary content | Console / fetch status |
|-------|--------|-------------------------|------------------------|
| `/` | `PASS` | Redirected to Timeline-first home, Review Inbox, AAPL risk action context. | No browser console errors; no `Failed to fetch`. |
| `/timeline` | `PASS` | 决策时间流, 主时间线, Review Inbox with AAPL concentration alert. | No browser console errors; no `Failed to fetch`. |
| `/dashboard` | `PASS` | Macro Command Center, 资金曲线, 风险预警, AAPL allocation/risk content. | No browser console errors; no `Failed to fetch`. |
| `/positions` | `PASS` | 交易记录 with AAPL, P19 Smoke Account, open position PnL. | No browser console errors; no `Failed to fetch`. |
| `/positions/cd001766-034e-41af-b5d0-fabb11852a00` | `PASS` | AAPL lifecycle detail, event spine, evidence/cash sections. | No browser console errors; no `Failed to fetch`. |
| `/positions/cd001766-034e-41af-b5d0-fabb11852a00/add-batch?type=ENTRY` | `PASS` | 加仓 / 平仓 form with truth write path explanation. | No browser console errors; no `Failed to fetch`. |
| `/positions/new` | `PASS` | 新增交易 form with P19 Smoke Account selectable. | No browser console errors; no `Failed to fetch`. |
| `/insights` | `PASS` | AI 洞察, Auditable Insight Artifacts, AI 分析助手, 周报历史. | No browser console errors; no `Failed to fetch`. |
| `/settings` | `PASS` | 设置, 实盘账户管理, P19 Smoke Account, appearance/data sections. | No browser console errors; no `Failed to fetch`. |
| `/admin/jobs` | `PASS` | 后台任务控制台, job status cards, empty job list as admin. | No browser console errors; no `Failed to fetch`. |

Important observation:
- `/dashboard`, `/positions`, and `/positions/new` needed a longer post-load wait than the first pass to let account/position data settle. After recheck, all three routes showed expected primary content and no browser errors.

---

## 7. Rollback Steps

Current source of truth:
- [release-rollback-playbook.md](./release-rollback-playbook.md)

Rollback coverage confirmed in P19 Task 3 for included lanes:
- Truth writes and legacy mutation guards.
- Timeline snapshot fallback.
- P13 risk alerts display/read-model behavior.
- P14 PDF export failure handling.
- P15 AI analysis workflow/artifacts.
- P16 market provider routing/freshness fallback.
- P17 admin backup/user operations safety.
- P18 internal SVG chart renderer and Recharts dependency removal.

---

## 8. Known Residual Risks

- External market data live provider validation depends on network/API keys; P16 has repeatable provider-routing tests but live provider quality remains environment-dependent.
- PostgreSQL backup provider behavior requires production-like database configuration; SQLite backup path is covered locally.
- Generated local files remain dirty after frontend checks and must not be staged unless intentionally regenerated.
- P10B/P10D/P10E remaining cleanup items are intentionally not included as release-ready feature work.
- No PR, merge, release tag, or push is performed by this checklist.

---

## 9. Release Decision

Current decision: `READY_FOR_STAGING_ONLY`.

Rationale:
- P13-P18 scope is frozen and included.
- Full backend/frontend automated verification passed in P19 Task 2.
- Alembic, truth sync/backfill, and derived timeline refresh rehearsal tests passed in P19 Task 3.
- Authenticated browser release smoke passed across product and admin routes in P19 Task 4.
- Rollback playbook covers P11-P18 release levers.
- Staging-only is the safer decision because production backup/provider credentials, merge/tag timing, and remote push are operational decisions outside this local checklist.

Staging decision details:
- Merge target: keep current work on `dev` until the user explicitly asks to merge.
- Backup command: use `/api/admin/ops/backups` or the production database backup procedure before any deployment migration.
- Release tag candidate: `p19-dev-readiness-20260611` if staging acceptance later approves tagging.
- Rollback first levers: database restore, `timeline_legacy_mixed_feed_enabled`, provider fallback/degraded metadata, hiding risky admin/UI entry points, and commit-level rollback per [release-rollback-playbook.md](./release-rollback-playbook.md).
- Next action after this checklist: push `dev` when the user asks to publish these commits to remote; do not create PR unless explicitly requested.
