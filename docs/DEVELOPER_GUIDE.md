# Trading Noobs 当前代码库指南

更新时间：2026-07-16
当前执行分支：`dev`
当前 HEAD：以当前 `dev` 最新提交为准；阶段状态见 [TODO.md](./TODO.md)。

本文档描述当前代码库的真实实现、运行入口、模块边界与开发注意事项。目标架构和未来设计仍以 `docs/superpowers/specs/` 为准；当前任务状态以 [TODO.md](./TODO.md) 为准。

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
- [release-rollback-playbook.md](./release-rollback-playbook.md) 是 truth writes、Timeline snapshot、legacy mutation guard 的发布与回滚手册。
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
| 外部服务 | Finnhub, AKShare, Binance, 可配置 OpenAI 兼容 LLM 接口 |
| 部署 | Docker Compose + Caddy；同机 main/dev 并行部署见 [vps-dev-parallel-deployment.md](./vps-dev-parallel-deployment.md) |
| 可观测性 | `X-Request-ID`、`X-Response-Time-Ms`、统一错误 `error.code/message/request_id/status_code` envelope、`tradingnoobs.*` 结构化日志 helper |

---

## 3. 关键目录

| 路径 | 职责 |
|------|------|
| `backend/main.py` | 后端入口，注册 FastAPI router，并在 lifespan 中执行受控 schema bootstrap |
| `backend/alembic/` | Alembic 配置与迁移链 |
| `backend/routers/` | API 路由层，包含 legacy 路由、truth 路由、timeline、admin jobs、insight artifacts |
| `backend/services/` | 业务逻辑层，包含 truth sync/accounting、job/outbox/idempotency、chart schema、market data |
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

后端当前主要 API：
- `/api/auth`
- `/api/accounts`
- `/api/accounts/{account_id}/transactions`
- `/api/positions`：legacy 持仓/批次路径，当前保留为迁移与 fallback 路径；新建仓位会立即同步 `TradingPosition` 并返回 `truth_position_public_id`，当 legacy position 已有 truth lifecycle 时，普通 legacy batch create 默认拒绝，只有显式 `X-Migration-Fallback: legacy-batch-write` 才允许迁移回退写入；legacy review 字段写入默认拒绝，只有显式 `X-Migration-Fallback: legacy-review-write` 才允许迁移修正；legacy position hard delete 默认拒绝，只有显式 `X-Migration-Fallback: legacy-position-delete` 才允许迁移清理；legacy batch edit/delete 默认拒绝，只有显式 `X-Migration-Fallback: legacy-batch-edit` 才允许迁移修正。
- `/api/trading-positions`：truth lifecycle、truth event write、dividend、manual adjustment、latest-event reversal。
- `/api/timeline/home`：Timeline 首页 read model，默认 `SNAPSHOT_ONLY`，由 `DerivedTimelineSnapshot` 与 auditable insight artifacts 驱动；`timeline_legacy_mixed_feed_enabled` 可作为 rollback flag 恢复 legacy mixed feed。
- `/api/dashboard`
- `/api/insights`
- `/api/insights/analyze/history`
- `/api/v1/insights/runs`
- `/api/v1/insights/artifacts`
- `/api/admin/jobs`
- `/api/admin/ops/backups`
- `/api/admin/users/{user_public_id}/promote`
- `/api/admin/users/{user_public_id}/reset-password`
- `/api/admin/platform/*`
- `/api/market`
- `/api/strategies`
- `/api/daily`
- `/api/journal`
- `/api/settings`

前端当前主要页面：
- `/`：默认入口，已转向 timeline-first，而不是旧 Dashboard-first。
- `/timeline`：Timeline / Review Inbox 决策工作台。
- `/dashboard`：宏观 Dashboard 工作台。
- `/positions`
- `/positions/new`
- `/positions/import`
- `/positions/[id]`
- `/positions/[id]/add-batch`
- `/insights`
- `/insights/[artifactId]`
- `/admin/jobs`
- `/admin/ops`
- `/settings`
- `/settings/accounts/[id]`
- `/strategies`
- `/daily`
- `/login`
- `/register`

前端 legacy DTO 边界：
- 新功能不应直接从 `frontend/lib/api.ts` 引入 legacy `Position` / `TradeBatch` / `BatchCreate` / `Transaction`。
- 当前允许的 raw legacy DTO 使用范围必须落在以下 allowlist 分组。
- `migration_ui`：`app/(product)/positions/[id]/add-batch/page.tsx`、`app/(product)/positions/page.tsx`。
- `create_sync_bridge`：`app/(product)/positions/new/page.tsx`。
- `legacy_analytics`：`components/dashboard/MaeMfeScatterPlot.tsx`、`lib/adapters/chart-views.ts`。
- `adapter_boundary`：`lib/adapters/trading.ts`。
- `frontend/tests/legacy-ui-boundaries.test.mts` 会阻止 raw legacy trading DTO import 继续扩散。

---

## 5. 核心业务模块现状

| 模块 | 状态 | 当前说明 |
|------|------|----------|
| 认证与用户基础 | `已实现` | 注册、登录、JWT、session/token 跟踪、public_id 支持已落地。 |
| 平台配置 | `已实现 / 继续扩展` | Platform settings、integration credentials、feature flags、admin API 已落地。 |
| 交易账户与资金记录 | `桥接完成 / 继续收敛` | `AccountLedgerEntry` 已落地，账户现金读模型已优先使用 ledger；legacy transaction 路径仍存在。 |
| Trading truth model | `桥接完成 / 硬切推进中` | `TradingPosition / PositionEvent / AccountLedgerEntry`、FIFO、truth lifecycle、truth-first add/reduce/close、truth narrative、latest active event reversal 已落地；新建仓位会 create-and-sync 到 truth lifecycle，已有仓位的普通加仓/减仓/平仓/复盘/叙事不再静默写 legacy 字段。 |
| Legacy 持仓路径 | `迁移期保留 / 写入受保护` | `Position / TradeBatch / Transaction / AssetMetadata / DailySnapshot` 仍被部分路由、导入、Dashboard、Timeline fallback 使用；truth lifecycle 存在时 legacy batch create、review write、position hard delete、batch edit/delete 都需要显式 migration fallback header。 |
| Timeline 首页 | `truth/snapshot 默认` | Timeline / Review Inbox 已是产品中心；Timeline events 与 Review Inbox 默认使用 `DerivedTimelineSnapshot` / auditable insight artifacts，legacy mixed feed 只作为 rollback。 |
| Lifecycle Detail | `truth-first 已落地` | 单笔详情已展示 truth lifecycle、evidence、ledger cash effects、AI sidecar；canonical review lives in `PositionEvent` narrative，legacy review 只作为 migration context 展示；latest active event reversal 会追加 `REVERSAL`，非最新 reversal 和 `OPEN` reversal 暂拒绝，直到补偿事件或 void/archive UX 明确。 |
| Dashboard | `宏观视图已重构` | 已从默认首页退到宏观视图；chart schema/freshness/trust 包装已接入。 |
| Insights / AI | `artifact-first 已落地` | `InsightRun / InsightArtifact`、artifact detail、证据链接展示已落地；AI 分析请求支持成对日期范围、366 天上限校验，artifact payload/source refs/evidence refs 会写入 `date-range:<start>:<end>`，`/api/insights/analyze/history` 支持复访近期分析。 |
| 异步任务 | `基础已落地` | Job model、outbox relay、worker CLI、business lock、idempotency、admin jobs UI/API 已落地。 |
| 管理员运维 | `P17 已落地` | `/api/admin/ops/backups`、管理员晋升、密码重置、stale/failed job recovery metadata、force-cancel typed confirmation 和 `/admin/ops` 控制台已完成；PostgreSQL backup provider 未配置时返回 `409 BACKUP_PROVIDER_NOT_CONFIGURED`。 |
| 市场数据 | `大型 WIP / Beta hard-off` | 类型化 provider registry、报价/日线、mapping、水位、job handlers 与前端 freshness 代码存在于当前未冻结 WIP，但尚未形成 JRN-000 checkpoint；交易日志 Beta 必须由 deny stub 关闭 route/secret/job/UI，不能描述为已发布能力。 |
| 风控预警 | `P13 已落地` | 组合风险、单日亏损上限、风险提醒、Dashboard 风险栏与 Timeline/Review Inbox 风险行动卡已完成 V1；不含 SSE/WebSocket。 |
| PDF 导出 | `P14 已落地` | 导入模板说明、周报 PDF 渲染服务、Insights PDF 导出接口、前端导出按钮和导出 runbook 已完成。 |

### 5.1 Insights AI 日期范围与复访契约

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
| `PositionEvent` | 新交易事件流，承载 OPEN / ADD / REDUCE / CLOSE / REVERSAL / DIVIDEND / MANUAL_ADJUSTMENT 等事实。 |
| `AccountLedgerEntry` | 账户资金真相来源，承载 opening balance、realized PnL、dividend、manual cash adjustment 等。 |
| `AssetMaster` | 新资产主数据。 |
| `TradeInstrument` | 新交易标的 / instrument 层。 |
| `DerivedTimelineSnapshot` | 派生 Timeline 事件快照。 |
| `InsightRun` / `InsightArtifact` | 可审计 AI 产物与展示单元。 |
| `JobDefinition` / `JobRun` / `JobRunEvent` | 本地异步任务模型。 |
| `OutboxEvent` | 事务性 outbox 事件。 |
| `IdempotencyKey` | 请求与 outbox relay 幂等记录。 |
| `BusinessLock` | 后台任务互斥锁。 |
| `PlatformSetting` / `FeatureFlag` | 平台配置与功能开关。 |

### 6.2 Legacy / 迁移期路径

| 实体 | 当前作用 |
|------|----------|
| `Position` | 旧持仓汇总，仍被 legacy positions、dashboard、timeline bridge、导入等路径使用；`trade_review`、`lessons`、`rating` 和 hard delete 在 truth lifecycle 存在后只作为 migration/support context。 |
| `TradeBatch` | 旧建仓/加仓/减仓/平仓批次，仍是部分 migration/fallback 路径的数据源；truth lifecycle 存在后不再作为普通用户加仓/减仓/平仓默认写路径，旧 batch edit/delete 也只允许显式迁移修正。 |
| `Transaction` | 旧账户流水，当前和 `AccountLedgerEntry` 并存。 |
| `AssetMetadata` | 旧资产元数据，仍被 legacy market/positions 逻辑使用。 |
| `DailySnapshot` | 旧每日权益快照，仍被部分 dashboard 历史数据路径使用。 |

P10 的关键目标不是马上删除 legacy，而是先把它们标为 `primary path`、`migration-only` 或 `delete candidate`，再安全清理。

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

- Python 3.10+
- Node.js 20+ 更稳妥；前端依赖使用 Next 16 / React 19
- npm
- 可选：Docker / Docker Compose

### 8.2 后端

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

默认后端地址：
- API：`http://localhost:8000`
- OpenAPI：`http://localhost:8000/docs`

### 8.3 前端

```bash
cd frontend
npm install
npm run dev
```

默认前端地址：
- `http://localhost:3000`

### 8.4 常用环境变量

后端配置入口：`backend/config.py`

- `DATABASE_URL`
- `SECRET_KEY`
- `CORS_ORIGINS`
- `LLM_API_URL`
- `LLM_API_KEY`
- `LLM_MODEL`
- `FINNHUB_API_KEY`
- `BINANCE_API_KEY`
- `BINANCE_API_SECRET`
- `ENV_NAME`
- `AUTO_CREATE_SCHEMA`

---

## 9. 常用验证命令

后端测试：

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests
```

前端测试：

```bash
cd frontend
node --experimental-strip-types --test tests/*.test.mts
```

前端类型检查：

```bash
cd frontend
./node_modules/.bin/tsc --noEmit --pretty false
```

前端 lint：

```bash
cd frontend
npm run lint
```

前端生产构建：

```bash
cd frontend
npm run build
```

注意：Next 16 / Turbopack 在受限沙箱里可能因为创建进程或绑定端口失败；如果失败原因是沙箱限制，需要按当前权限流程请求提升后重跑。

---

## 10. 当前后续开发重点

优先级以 [TODO.md](./TODO.md) 为准。当前建议顺序：

1. `JRN-000`：分类并 checkpoint 当前 WIP，固定 `9cad10111213` migration baseline 与 Broker/Market default-off disposition。
2. `JRN-001`：冻结币种/标的/事件 release contract，并建立不可由 Admin 绕过的 deployment capability ceiling。
3. `JRN-002`：固定运行环境并建立 PostgreSQL mandatory CI。
4. `JRN-003`：关闭硬编码邀请和明文 Broker/Market/LLM release secret，完成 invite-only auth。
5. `JRN-004`：补齐当前 account/strategy/position/event/ledger/note/idempotency 的 owner/tenant 负向边界，关闭 legacy import 越权面并冻结 future-resource harness；Import/source 新模型由各自创建任务验证。
6. Step 0/M0 通过后再执行会计、canonical writer、通用 bootstrap 和 source-bound Import；真实 staging 位于 `JRN-021`，不是当前第一步。

---

## 11. 维护原则

- `specs/` 负责目标架构与未来设计。
- `plans/` 负责分阶段实施和验收记录。
- `TODO.md` 负责当前任务队列。
- `DEVELOPER_GUIDE.md` 负责当前真实实现。
- 如果文档与代码不一致，以代码和最新 checkpoint 为准，再回头修正文档。
- `docs/superpowers/demos/` 是未跟踪用户内容，除非用户明确要求，否则不要修改或提交。
