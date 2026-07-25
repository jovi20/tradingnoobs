# Trading Noobs 当前代码库指南

更新时间：2026-07-17
当前执行分支：`dev`
当前 HEAD：以当前 `dev` 最新提交为准；阶段状态见 [TODO.md](./TODO.md)。

本文档描述当前代码库的真实实现、运行入口、模块边界与开发注意事项。目标架构和未来设计仍以 `docs/superpowers/specs/` 为准；当前任务状态以 [TODO.md](./TODO.md) 为准。

## JOURNAL Beta release boundary

> 当前 release availability 唯一以 [active trading-journal plan](./superpowers/plans/2026-07-16-dev-trading-journal-development-plan.md) 和机器可读 release contract 为准，不能根据源码、旧路由或历史阶段完成记录推断。代码存在不等于 Beta 已启用。

`JRN-000` 已完成 checkpoint；`JRN-001` 当前处于 final verification/review，尚未关闭，也不表示 Beta 已可发布。

- `BROKER_SYNC`、`MARKET`、`AI_INSIGHTS`、`PDF_EXPORT`、`RISK_CARDS` 和 `OPEN_REGISTRATION` 当前均为 `DISABLED / DEFERRED`。对应 API、导航、设置、凭据写入和 job/outbox producer 不属于 JOURNAL Beta 可用面。
- 可选能力必须同时满足外部 deployment allowlist 和数据库 runtime rollout；缺失部署 allowlist 时 ceiling 为空。数据库配置不能扩大 ceiling。
- JOURNAL Beta 不执行 Broker 网络同步，不读取或要求 Broker、行情或 LLM 凭据。
- `IBKR_FLEX_XML_V1` 是 `JRN-013` 至 `JRN-015` 计划实现的本地文件 adapter，不是在线 Broker Sync；重复、重叠、增量确认和 correction replay 截至本次更新均未实现或开放。
- `GENERIC_BOOTSTRAP` 同样尚未实现。`POST /api/positions/import/upload`、`POST /api/positions/import/confirm` 和 `GET /api/positions/import/template` 当前仅由 deny-only stub 返回 `404 FEATURE_DISABLED`，不进入 OpenAPI，也不提供模板、上传、preview 或 confirm；前端没有 Import 入口，直达 `/positions/import` 进入 framework not-found 视图。
- `/register` 路由模块已删除，`/api/auth/register` 也未注册；硬编码共享邀请码不能作为 invite-only onboarding。一次性哈希邀请码、兑换与审计由 `JRN-003` 完成后，才重新开放受控注册路径。

---

## 1. 文档约定

- [superpowers/specs/2026-04-06-platform-foundation-design.md](./superpowers/specs/2026-04-06-platform-foundation-design.md) 是平台底座目标架构来源。
- [superpowers/specs/2026-04-07-frontend-experience-redesign-design.md](./superpowers/specs/2026-04-07-frontend-experience-redesign-design.md) 是前端体验重设计基线。
- [project-summary-and-roadmap.md](./project-summary-and-roadmap.md) 是当前项目描述与后续计划入口。
- [superpowers/plans/archive/2026-04-13-platform-frontend-sequencing-plan.md](./superpowers/plans/archive/2026-04-13-platform-frontend-sequencing-plan.md) 是平台 + 前端迁移顺序历史基线，已归档。
- [TODO.md](./TODO.md) 是当前执行清单。
- [superpowers/plans/2026-07-16-dev-trading-journal-development-plan.md](./superpowers/plans/2026-07-16-dev-trading-journal-development-plan.md) 是当前唯一 active implementation plan。
- [superpowers/plans/archive/2026-06-11-dev-p18-chart-renderer-migration-plan.md](./superpowers/plans/archive/2026-06-11-dev-p18-chart-renderer-migration-plan.md) 已完成并归档，剩余 Recharts renderer 已迁移到内部 SVG renderer，并保持 `chart.v1` 数据契约稳定。
- [superpowers/plans/archive/2026-06-11-dev-p19-release-readiness-plan.md](./superpowers/plans/archive/2026-06-11-dev-p19-release-readiness-plan.md) 是历史 release evidence；当前状态已由全量 gap 审计更新为 `NOT_READY_FOR_PRODUCTION`。
- [release-rollback-playbook.md](./release-rollback-playbook.md) 顶部包含当前 JRN-001 窄化 rollback addendum；其余 P11-P18 内容是已 supersede 的历史记录。
- [vps-dev-parallel-deployment.md](./vps-dev-parallel-deployment.md) 说明已有 main VPS 部署时，如何在同一台 VPS 上隔离部署 `dev` staging。
- [current-state-baseline.md](./current-state-baseline.md) 是 2026-04-05 历史审计快照，不再作为当前实现依据。
- `顶层设计.md` 已降级为历史草案，当前仓库未跟踪。

---

## 2. 当前技术栈

| 层级 | 当前实现 |
|------|----------|
| 前端 | Next.js 16.2.7, React 19.2.7, TypeScript 5, Tailwind CSS, React Query 5 |
| 图表 | 内部 SVG renderer；前端已建立 `chart.v1` schema、`ChartFrame`、freshness/trust 包装，`recharts` 依赖已移除 |
| 后端 | FastAPI, SQLAlchemy, Pydantic |
| 数据库 | 开发默认 SQLite，部署默认 PostgreSQL |
| 迁移 | Alembic revision chain 是主迁移路径；开发启动仍有受保护的 schema bootstrap |
| 异步与派生 | 本地 DB job worker、outbox relay、idempotency、business lock、derived timeline snapshot |
| 外部服务 | Provider/LLM adapter 代码仍存在，但 JOURNAL Beta 不调用外部 Broker、行情或 LLM 服务，也不要求其凭据 |
| 部署 | Docker Compose + Caddy；同机 main/dev 并行部署见 [vps-dev-parallel-deployment.md](./vps-dev-parallel-deployment.md) |
| 可观测性 | `X-Request-ID`、`X-Response-Time-Ms`、统一错误 `error.code/message/request_id/status_code` envelope、`tradingnoobs.*` 结构化日志 helper |

---

## 3. 关键目录

| 路径 | 职责 |
|------|------|
| `backend/main.py` | 后端入口，注册 FastAPI router，并在 lifespan 中执行受控 schema bootstrap |
| `backend/alembic/` | Alembic 配置与迁移链 |
| `backend/routers/` | API 路由层；部分 Broker/Market/Insights 等 optional router 代码为 `DISABLED / DEFERRED`，不能据此判断 Beta 可达性 |
| `backend/services/` | 业务逻辑层，包含 truth sync/accounting、job/outbox/idempotency、chart schema；provider、AI、risk、PDF 代码不属于当前 Beta 可用面 |
| `backend/models.py` | 当前仍是单文件 SQLAlchemy 模型；拆分在 active journal plan 中标记为 `DEFERRED_BY_SCOPE` |
| `backend/schemas.py` | Pydantic 请求/响应模型 |
| `frontend/app/` | Next.js App Router 页面入口 |
| `frontend/components/` | 页面级与领域组件，包括 timeline/dashboard/lifecycle/admin/ui primitives |
| `frontend/lib/api.ts` | 当前前端 API client；后续不再扩为长期 DTO 契约层 |
| `frontend/lib/read-models.ts` | 当前手写 read model 类型；后续计划迁到 OpenAPI 生成类型 |
| `frontend/lib/adapters/` | 前端 read-model/domain adapter 层 |
| `docs/superpowers/plans/` | 当前仍有效的后续参考计划；已完成阶段计划在 `docs/superpowers/plans/archive/` |
| `docs/superpowers/specs/` | 架构、契约和设计基线 |

---

## 4. 当前运行时结构

后端 JOURNAL Beta 核心 API 面：
- `/api/auth`
- `/api/accounts`
- `/api/accounts/{account_id}/transactions`
- `/api/positions`：legacy 持仓/批次读取与 create-and-sync 过渡路径；新建仓位会立即同步 `TradingPosition` 并返回 `truth_position_public_id`。已有 legacy 行缺少 canonical truth 时，`GET /api/positions/{id}/truth-lifecycle` 只返回 not-found，不得在读取中触发 backfill、flush 或 commit；迁移必须由后续显式受审计流程执行。普通产品面上的 legacy review `PATCH /api/positions/{position_id}`、position hard delete `DELETE /api/positions/{position_id}`、batch create `POST /api/positions/{position_id}/batches` 以及 batch edit/delete `PATCH|DELETE /api/positions/batches/{batch_id}` 全部 fail-closed：对 owner 已验证且资源存在的请求稳定返回 `409`，不因 truth lifecycle 是否存在而改变。任何 `X-Migration-Fallback` header 或历史 token 都不能绕过；`X-Migration-Fallback` 不在 OpenAPI 中且不能授予迁移权限。受审计的 admin/CLI migration namespace 尚未实现，不能用隐藏 query/header 代替。
- `/api/trading-positions`：truth lifecycle、允许的 truth trade event write、同币种 dividend 和 latest-event reversal；`manual adjustment` 兼容路径在 Beta 稳定拒绝且不写事实。
- `/api/timeline/home`：Timeline 首页 read model，默认 `SNAPSHOT_ONLY`，由 `DerivedTimelineSnapshot` 驱动；optional AI artifact feed 不属于当前 Beta 可用面。
- `/api/dashboard`
- `/api/admin/jobs`
- `/api/admin/ops/backups`
- `/api/admin/users/{user_public_id}/promote`
- `/api/admin/users/{user_public_id}/reset-password`
- `/api/strategies`
- `/api/daily`
- `/api/journal`
- `/api/settings`

源码中仍可见 Broker Sync、Market、Insights/AI、PDF export、risk cards、open registration 和 provider credential 路径；它们都是 `DISABLED / DEFERRED` optional surfaces，不是可调用 API 清单，也不得出现在 JOURNAL Beta OpenAPI、导航或普通设置中。

前端当前主要页面：
- `/`：默认入口，已转向 timeline-first，而不是旧 Dashboard-first。
- `/timeline`：Timeline / Review Inbox 决策工作台。
- `/dashboard`：宏观 Dashboard 工作台。
- `/positions`
- `/positions/new`
- `/positions/[id]`
- `/positions/[id]/add-batch`
- `/admin/jobs`
- `/admin/ops`
- `/settings`
- `/settings/accounts/[id]`
- `/strategies`
- `/daily`
- `/login`

`/positions/import` 只是调用 `notFound()` 的禁用壳，不是当前主要页面或可用 Import UI。`/insights`、风险卡和 PDF 导出代码可能仍留在仓库中，但当前必须隐藏或不可达；`/register` 页面路由模块已删除。

前端 legacy DTO 边界：
- 新功能不应直接从 `frontend/lib/api.ts` 引入 legacy `Position` / `TradeBatch` / `BatchCreate` / `Transaction`。
- 当前允许的 raw legacy DTO 使用范围必须落在以下 allowlist 分组。
- `migration_ui`：`app/(product)/positions/[id]/add-batch/page.tsx`、`app/(product)/positions/page.tsx`。
- `create_sync_bridge`：`app/(product)/positions/new/page.tsx`。
- `legacy_analytics`：`components/dashboard/MaeMfeScatterPlot.tsx`。其数据适配器只接受 MARKET capability 的独立分析 DTO，不再依赖 journal `Position` DTO。
- `adapter_boundary`：`lib/adapters/trading.ts`。
- `frontend/tests/legacy-ui-boundaries.test.mts` 会阻止 raw legacy trading DTO import 继续扩散。
- 这些 allowlist 只限制 DTO import 位置，不为任何 public legacy mutation 提供 migration fallback 权限。

---

## 5. 核心业务模块现状

| 模块 | 状态 | 当前说明 |
|------|------|----------|
| 认证与用户基础 | `部分实现 / invite-only 收敛中` | 登录、JWT、session/token 跟踪和 public_id 代码已落地；公开注册为 `DISABLED`，invite-only 与 recovery 发布闭环由 `JRN-003` 完成。 |
| 平台配置 | `核心存在 / optional secret hard-off` | FeatureFlag 等基础代码存在；Broker、Market、LLM 的普通设置、凭据写入与测试入口在 JOURNAL Beta 关闭。 |
| 交易账户与资金记录 | `桥接完成 / 继续收敛` | `AccountLedgerEntry` 已落地，账户现金读模型已优先使用 ledger；legacy transaction 路径仍存在。 |
| Trading truth model | `桥接完成 / 硬切推进中` | `TradingPosition / PositionEvent / AccountLedgerEntry`、FIFO、truth lifecycle、truth-first add/reduce/close、truth narrative、latest active event reversal 已落地；新建仓位会 create-and-sync 到 truth lifecycle，已有仓位的普通加仓/减仓/平仓/复盘/叙事不再静默写 legacy 字段。 |
| Legacy 持仓路径 | `迁移期保留 / public mutation hard-off` | `Position / TradeBatch / Transaction / AssetMetadata / DailySnapshot` 仍被部分读取、create-and-sync bridge、Dashboard 和 Timeline fallback 使用；未注册的历史 Import parser 也仍引用其中部分模型，但不是可达路径。public legacy review、position hard delete 与 batch create/edit/delete 对已有 owner 资源稳定返回 `409`，任何 migration fallback header 都不能解锁。 |
| Timeline 首页 | `truth/snapshot 默认` | Timeline / Review Inbox 已是产品中心，核心事件使用 `DerivedTimelineSnapshot`；AI artifact feed 代码当前 hard-off，legacy mixed feed 只作为 rollback。 |
| Lifecycle Detail | `truth-first 已落地` | 单笔详情展示 truth lifecycle、evidence 和 ledger cash effects；AI sidecar 代码在 JOURNAL Beta 隐藏。canonical review lives in `PositionEvent` narrative，legacy review 只作为 migration context 展示；latest active event reversal 会追加 `REVERSAL`，非最新 reversal 和 `OPEN` reversal 暂拒绝，直到补偿事件或 void/archive UX 明确。 |
| Dashboard | `宏观视图已重构` | 已从默认首页退到宏观视图；chart schema/freshness/trust 包装已接入。 |
| Insights / AI | `代码存在 / Beta hard-off` | 历史 artifact-first、LLM 和页面代码保留为 deferred implementation evidence；API、UI、凭据和 job producer 当前关闭，不能描述为 Beta 已落地能力。 |
| 异步任务 | `基础已落地` | Job model、outbox relay、worker CLI、business lock、idempotency、admin jobs UI/API 已落地。 |
| 管理员运维 | `P17 已落地` | `/api/admin/ops/backups`、管理员晋升、密码重置、stale/failed job recovery metadata、force-cancel typed confirmation 和 `/admin/ops` 控制台已完成；PostgreSQL backup provider 未配置时返回 `409 BACKUP_PROVIDER_NOT_CONFIGURED`。 |
| 市场数据 | `代码已 checkpoint / Beta hard-off` | JRN-000 已记录 optional-code disposition；类型化 provider registry、报价/日线、mapping、水位、job handlers 与前端 freshness 代码存在不表示已发布。交易日志 Beta 由 capability boundary 关闭 route/secret/job/UI。 |
| Broker 同步 | `Beta hard-off` | 在线同步、网络访问、Token/credential 保存和后台 sync job 均关闭。`IBKR_FLEX_XML_V1` 仅是 `JRN-013` 至 `JRN-015` 计划中的本地文件 adapter，目前未实现。 |
| 风控预警 | `代码存在 / Beta hard-off` | 历史 P13 risk card 代码不属于 JOURNAL Beta 可用面；相关 API、Dashboard/Timeline 卡片和后台 producer 必须关闭。 |
| PDF 导出 | `代码存在 / Beta hard-off` | 历史 P14 renderer、接口、按钮和 runbook 仅作为 deferred evidence；JOURNAL Beta 不开放 PDF 下载。 |

### 5.1 Insights AI 历史代码契约（DISABLED）

> 本节只记录保留代码的历史契约，供未来重新评审；当前端点和页面不得注册、展示或作为可用功能宣传。

- `POST /api/insights/analyze` 的 `start_date` 与 `end_date` 必须同时提供或同时省略。
- 日期范围是 inclusive；`start_date > end_date` 或超过 366 天会返回 P12B 标准错误 envelope。
- 生成 artifact 时，`InsightRun.input_refs`、artifact evidence refs、trust source refs 和 payload `date_range` 都会包含同一个范围标记。
- `GET /api/insights/analyze/history?limit=5` 返回当前用户近期分析 artifact，前端 `/insights` 会展示为“近期分析记录”，并链接到 `/insights/{artifact_public_id}`。
- 前端日期默认范围由 `frontend/lib/adapters/analysis.ts` 计算，为当前日期向前 30 个 calendar day inclusive。

---

## 6. 数据模型边界

当前模型仍集中在 `backend/models.py`。模型拆分在会计和 truth/legacy 语义稳定前保持 `DEFERRED_BY_SCOPE`；以后执行时仍需保持 `from models import ...` 兼容路径。

### 6.1 Truth / 新主路径

| 实体 | 当前作用 |
|------|----------|
| `TradingPosition` | 新交易真相聚合，承载 position-level 状态、数量、PnL、费用。 |
| `PositionEvent` | 新交易事件流，承载 release contract 允许的 OPEN / ADD / REDUCE / CLOSE / REVERSAL / DIVIDEND 等事实；存量 `MANUAL_ADJUSTMENT` 只作历史兼容读取。 |
| `AccountLedgerEntry` | 账户 journal balance 的事实来源，承载 opening balance、realized PnL、dividend 及 release contract 允许的资金事件；存量 `CASH_ADJUSTMENT` 只作历史兼容读取，Beta 不提供新增入口。 |
| `AssetMaster` | 新资产主数据。 |
| `TradeInstrument` | 新交易标的 / instrument 层。 |
| `DerivedTimelineSnapshot` | 派生 Timeline 事件快照。 |
| `InsightRun` / `InsightArtifact` | 保留的可审计 AI 产物模型；AI capability 当前 `DISABLED / DEFERRED`。 |
| `JobDefinition` / `JobRun` / `JobRunEvent` | 本地异步任务模型。 |
| `OutboxEvent` | 事务性 outbox 事件。 |
| `IdempotencyKey` | 请求与 outbox relay 幂等记录。 |
| `BusinessLock` | 后台任务互斥锁。 |
| `PlatformSetting` / `FeatureFlag` | 平台配置与功能开关。 |

### 6.2 Legacy / 迁移期路径

| 实体 | 当前作用 |
|------|----------|
| `Position` | 旧持仓汇总，仍被 legacy positions 读取、create-and-sync bridge、Dashboard 和 Timeline bridge 使用；未注册的历史 Import parser 也引用该模型。public `PATCH` 的 legacy review/position 字段与 hard delete 对已有 owner 资源稳定返回 `409`，没有 header bypass。 |
| `TradeBatch` | 旧建仓/加仓/减仓/平仓批次，仍作为部分只读 bridge 的数据源。public batch create/edit/delete 对已有 owner 资源稳定返回 `409`；未来迁移 mutation 必须进入尚未实现的受审计 admin/CLI namespace。 |
| `Transaction` | 旧账户流水，当前和 `AccountLedgerEntry` 并存。 |
| `AssetMetadata` | 旧资产元数据，仍被 legacy market/positions 逻辑使用。 |
| `DailySnapshot` | 旧每日权益快照，仍被部分 dashboard 历史数据路径使用。 |

legacy 代码不会在 replacement、migration 和 rollback 明确前直接删除；但“代码保留”不等于 public mutation 可用。当前只能把保留面标为只读 bridge、create-and-sync bridge、unregistered historical reference 或 delete candidate，不能把普通产品路由称为 migration fallback。

---

## 7. Schema 与迁移

- Alembic revision chain 已存在，且是 schema 演进的主路径。
- `backend/main.py` 通过 `bootstrap_schema_if_enabled(...)` 执行受控 schema bootstrap。
- `backend/app_bootstrap.py` 默认在非 production 环境允许自动 create_all，在 production 环境默认关闭，除非显式配置。
- `backend/tests/test_schema_bootstrap.py` 覆盖了 production/development 默认行为和显式开关。
- 老的 `backend/ops/migrate_db.py` 已删除；新增 schema 变更只走 Alembic revision。

---

## 8. 本地开发入口

### 8.1 前置要求

- Python 3.13.5（见 `.python-version`）
- Node.js 24.18.0 与 npm 11.16.0（见 `.node-version` 和 `frontend/package.json`）
- PostgreSQL 16；完整 JRN-002 gate 未提供连接串时会启动本机临时 PostgreSQL
- 可选：Docker / Docker Compose

### 8.2 后端

```bash
cd backend
python -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip==26.1.2
python -m pip install --require-hashes -r requirements-ci.lock.txt
uvicorn main:app --reload --no-access-log
```

默认后端地址：
- API：`http://localhost:8000`
- OpenAPI：`http://localhost:8000/docs`

### 8.3 前端

```bash
cd frontend
npm ci
npm run dev
```

默认前端地址：
- `http://localhost:3000`

### 8.4 常用环境变量

后端配置入口：`backend/config.py`

- `DATABASE_URL`
- `SECRET_KEY`
- `CORS_ORIGINS`
- `ENV_NAME`
- `AUTO_CREATE_SCHEMA`
- `DEPLOYMENT_CAPABILITY_ALLOWLIST`：JOURNAL Beta 缺失或保持为空；它是部署 ceiling，不得写入业务数据库。

Broker、Market 和 LLM provider 的历史环境变量仍可能被代码识别，但不属于 JOURNAL Beta 配置合同；不要为当前 profile 配置或分发这些凭据。

---

## 9. 常用验证命令

JRN-002 本地与 CI 使用同一个完整 gate。若未设置 `JRN002_POSTGRES_URL`，本地必须提供 PostgreSQL 16 的 `initdb` 和 `pg_ctl`：

```bash
backend/venv/bin/python scripts/run_journal_baseline_gate.py
```

结果摘要写入忽略目录 `.artifacts/jrn002/gate-summary.json`，包含 commit、工作树状态、Python/Node/npm/PostgreSQL 版本及逐项结果。
本地默认扫描 `HEAD^..HEAD` 的新增 secret；需要验证更长 checkpoint 范围时设置
`JRN002_SECRET_SCAN_BASE` 和 `JRN002_SECRET_SCAN_HEAD`。CI 会按 PR base/head 或 push before/head
显式传入 exact-SHA 范围。

只运行后端测试：

```bash
PYTHONPATH=backend backend/venv/bin/python -m pytest backend/tests
```

只运行前端门禁：

```bash
cd frontend
npm run check:release-contract
npm test
npm run typecheck
npm run lint
npm run build
```

OpenAPI 发生有意变更时，重新生成并审阅基线快照：

```bash
backend/venv/bin/python backend/scripts/generate_openapi_snapshot.py
```

---

## 10. 当前后续开发重点

优先级以 [TODO.md](./TODO.md) 为准。当前建议顺序：

1. `JRN-000`：已完成 checkpoint，固定 `9cad10111213` migration baseline 与 Broker/Market default-off disposition。
2. `JRN-001`：正在 final verification/review；通过稳定 checkpoint 和独立评审前不得标记完成。
3. JRN-001 批准后，`JRN-002` 固定运行环境并建立 PostgreSQL mandatory CI，`JRN-003` 完成 invite-only auth 与 release secret 治理。
4. `JRN-004`：补齐当前 account/strategy/position/event/ledger/note/idempotency 的 owner/tenant 负向边界，关闭 legacy import 越权面并冻结 future-resource harness；Import/source 新模型由各自创建任务验证。
5. Step 0/M0 通过后再执行会计、canonical writer、通用 bootstrap；IBKR source-bound 重复、重叠、增量与 correction replay 只在 `JRN-013` 至 `JRN-015` 实现。真实 staging 位于 `JRN-021`。

---

## 11. 维护原则

- `specs/` 负责目标架构与未来设计。
- `plans/` 负责分阶段实施和验收记录。
- `TODO.md` 负责当前任务队列。
- `DEVELOPER_GUIDE.md` 负责当前真实实现。
- 如果文档与代码不一致，以代码和最新 checkpoint 为准，再回头修正文档。
- `docs/superpowers/demos/` 是未跟踪用户内容，除非用户明确要求，否则不要修改或提交。
