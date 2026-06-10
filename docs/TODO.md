# Trading Noobs 开发任务清单

更新时间：2026-06-10
当前执行分支：`dev`
P10 起始基线：`3418a27 docs: mark p9f pushed`

本文档是当前唯一执行清单。目标是回答三个问题：
- 现在已经推进到哪里
- 接下来优先做什么
- 哪些早期规划仍未开发

设计说明、架构说明和专题细节请查看：
- [superpowers/specs/2026-04-06-platform-foundation-design.md](./superpowers/specs/2026-04-06-platform-foundation-design.md)
- [superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md](./superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md)
- [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md)
- [market_data_sources.md](./market_data_sources.md)
- [trading-metrics.md](./trading-metrics.md)
- [trading-fields-design.md](./trading-fields-design.md)
- [superpowers/plans/2026-06-10-dev-p10-progress-next-plan.md](./superpowers/plans/2026-06-10-dev-p10-progress-next-plan.md)
- [superpowers/plans/2026-06-10-dev-p10-legacy-cutover-inventory.md](./superpowers/plans/2026-06-10-dev-p10-legacy-cutover-inventory.md)
- [superpowers/plans/2026-06-10-dev-p10-model-modularization-plan.md](./superpowers/plans/2026-06-10-dev-p10-model-modularization-plan.md)
- [superpowers/plans/2026-06-10-dev-p11-truth-hard-cutover-plan.md](./superpowers/plans/2026-06-10-dev-p11-truth-hard-cutover-plan.md)
- [superpowers/plans/2026-06-10-dev-p12-platform-contract-hardening-plan.md](./superpowers/plans/2026-06-10-dev-p12-platform-contract-hardening-plan.md)
- [release-rollback-playbook.md](./release-rollback-playbook.md)

---

## 当前进度快照

| 领域 | 当前状态 | 说明 |
|------|----------|------|
| 平台底座 | `已大幅落地` | Alembic、public_id、auth/session、platform config、feature flags、job/outbox/idempotency/business lock、derived timeline snapshot 已进入 `dev`。 |
| Truth 交易模型 | `P11 硬切代码完成` | `TradingPosition / PositionEvent / AccountLedgerEntry` 已落地；新建仓位已 create-and-sync 到 truth lifecycle，已有仓位加仓/减仓/平仓/复盘/叙事已 truth-first；legacy batch/review/delete 写入在 truth lifecycle 存在时默认被保护为 migration fallback。 |
| Timeline 首页 | `truth/snapshot 默认` | `/` 和 `/timeline` 已转向时间流/复盘工作台；Timeline events 与 Review Inbox 默认使用 `DerivedTimelineSnapshot` / auditable artifacts，`timeline_legacy_mixed_feed_enabled` 是 legacy mixed rollback。 |
| Lifecycle Detail | `truth-first 体验已落地` | 单笔详情已优先展示 truth lifecycle、evidence、AI sidecar；latest active event reversal 走审计 `REVERSAL`，非最新 reversal、`OPEN` reversal、legacy hard delete/batch edit 已被保护为非普通路径。 |
| Dashboard / Insights | `已重构为工作台形态` | Dashboard 保持宏观视图；Insights 已接入 auditable artifact 与 artifact detail；图表已有 schema/freshness 包装。 |
| 前端依赖与质量 | `已完成 P8-P9F` | Next 16 / React 19 已升级；React 19 strict hooks lint 全局启用；前端 lint 已到 0 warning。 |
| 文档状态 | `P12 完成 / P12B 待计划` | P10 文档、legacy inventory、observability、read-model marker、model modularization plan 已落地；P11 hard cutover 与 P12 platform contract hardening 已完成，下一条建议 lane 是 P12B observability/error contract hardening。 |

---

## 当前 Active Lane

- 当前 active lane：P12 Platform contract hardening 已完成。
- 完成计划：[2026-06-10-dev-p12-platform-contract-hardening-plan.md](./superpowers/plans/2026-06-10-dev-p12-platform-contract-hardening-plan.md)。
- 下一条建议 active lane：P12B Observability / error contract hardening，先补统一 error code 接入和结构化日志，再进入风险、PDF、AI 日期范围、市场数据或 admin ops。

### P11 完成状态

- [x] P11 Task 1A：已有仓位加仓/减仓/平仓不再静默 fallback 到 legacy batch；legacy batch 写入需要显式 `X-Migration-Fallback: legacy-batch-write`。
- [x] P11 Task 1B：全新开仓 create path 已采用 create-and-sync 过渡合同，`POST /api/positions` 返回 `truth_position_public_id`，前端优先跳转 truth detail。
- [x] P11 Task 2：复盘与叙事最终写入 `PositionEvent` / truth lifecycle；legacy review fields 已变成 migration-only。
- [x] P11 Task 3：historical reversal、`OPEN` reversal、archive/void/delete、legacy batch edit 最终语义。
- [x] P11 Task 4：Timeline / Review Inbox 默认 truth/snapshot-backed。
- [x] P11 Task 5：剩余 legacy UI 统一标为 migration tools。
- [x] P11 自动化完成门：后端全量测试、前端 typecheck、lint、Node 测试、`git diff --check` 已通过。
- [ ] P11 受限项：authenticated browser smoke 未完成；本轮只验证了 `/`、`/timeline`、`/login` 可服务，因浏览器未登录被重定向到 `/login`，还需带登录态覆盖 `/positions`、`/positions/[id]`、`/positions/[id]/add-batch`。

### P12 完成状态

- [x] P12 Task 1：冻结 frontend raw legacy DTO import 边界，并用测试锁住 migration/support、create-sync bridge、legacy analytics、adapter boundary。
- [x] P12 Task 2：增加 OpenAPI contract snapshot tests，覆盖 truth lifecycle、Timeline、legacy fallback headers。
- [x] P12 Task 3：建立 `frontend/lib/generated/` 输出边界，为后续 OpenAPI type generation 做好落点。
- [x] P12 Task 4：补 release / rollback playbook，覆盖 truth writes、snapshot Timeline、legacy mutation guards。
- [x] P12 Task 5：完成 P12 全量验证门。

### 下一条建议计划

- [ ] P12B：创建 Observability / error contract hardening plan。
- [ ] P12B：在路由异常处理中实际使用统一 error code。
- [ ] P12B：建立结构化日志策略，逐步替换后端业务路径中的 `print()`。
- [ ] P12B：补最小回归测试，保证错误响应包含稳定 code、request id、可排障信息。

---

## P10：下一阶段优先开发任务

### P10A 文档与进度同步

- [x] 复核 Opus 评审与当前 `dev` 状态，区分有效问题、过期问题和策略冲突。
- [x] 更新 `DEVELOPER_GUIDE.md`，让技术栈、首页形态、数据模型、schema 初始化、已落地能力与 `dev` 一致。
- [x] 更新 `docs/README.md`，补上当前计划、checkpoint、P9/P10 文档入口。
- [x] 更新 sequencing plan，把 P9A-P9F 已完成事项从“待做”转为真实状态。
- [x] 新增 P10 开发计划文档，明确 hard cutover、observability、legacy 清理、后续功能 backlog 的执行顺序。

### P10B Truth hard cutover 设计与执行

- [x] 盘点所有 legacy `Position / TradeBatch / Transaction / AssetMetadata / DailySnapshot` 引用，按 `primary path`、`migration-only`、`delete candidate` 分类。
- [x] 把普通用户新增、加仓、减仓、平仓、复盘、叙事编辑统一到 `TradingPosition / PositionEvent` 路径；新增开仓已 create-and-sync，已有仓位加仓/减仓/平仓已默认 truth-first，复盘/叙事已写入 `PositionEvent` narrative。
- [x] 明确 historical reversal、`OPEN` reversal、whole-position delete、legacy batch edit 的最终产品语义。
- [x] 让 Timeline / Review Inbox 最终读 `TradingPosition / PositionEvent / InsightArtifact / DerivedTimelineSnapshot`，不再依赖 legacy bridge 作为主路径。
- [ ] 完成 hard cutover 后，再删除或隔离旧模型、旧路由、旧 DTO、旧前端 fallback。

### P11 后剩余 delete / isolation candidates

- [ ] `frontend/app/positions/page.tsx` 的 legacy batch expansion：等 truth position list/read model 完成后删除或迁移。
- [ ] `frontend/app/positions/new/page.tsx` 的 raw legacy create DTO：等 truth-native create endpoint 完成后替换。
- [ ] `frontend/app/positions/[id]/add-batch/page.tsx` 的 raw `Position` 依赖：等 truth lifecycle response 提供表单所需数量、币种、账户上下文后替换。
- [ ] `frontend/components/dashboard/MaeMfeScatterPlot.tsx` 与 `frontend/lib/adapters/chart-views.ts` 的 legacy position chart adapter：等 dashboard charts 全部 schema/read-model backed 后删除。
- [ ] `frontend/lib/adapters/trading.ts` 的 legacy DTO adapter：等剩余 migration tools 拆出独立边界后收口。

### P10C 平台可观测性与运维安全

- [x] 增加请求级 `X-Request-ID`。
- [x] 增加请求耗时 `X-Response-Time-Ms`。
- [x] 冻结 error code 命名规则，新增 `make_error_code(namespace, error)` helper。
- [ ] 在路由异常处理中实际使用统一 error code。
- [ ] 建立结构化日志策略，逐步替换后端业务路径中的 `print()`。
- [x] 补 release / rollback playbook，特别是 truth hard cutover 和 derived snapshot 切换；详见 [release-rollback-playbook.md](./release-rollback-playbook.md)。

### P10D 前端 API 契约收敛

- [x] 给 `frontend/lib/read-models.ts` 标记“手写类型，后续由 OpenAPI 生成替换”。
- [ ] 停止继续扩张 `frontend/lib/api.ts` 作为永久 DTO 层。
- [x] 规划 OpenAPI type generation 输出路径和导入边界；P12 Task 1-3 已完成。
- [ ] 将新页面尽量绑定 read-model adapter，而不是直接绑定 raw API DTO。

### P10E 模型与服务模块化

- [x] 在 truth hard cutover 边界清楚后，规划 `backend/models.py` 拆分。
- [x] 保留 `models/__init__.py` re-export 兼容层，避免一次性打断大量 `from models import ...`。
- [x] 优先拆出 core/auth、trading truth、platform/job/outbox、analytics/read-model、legacy migration 五类边界。

---

## 中期功能 backlog

这些是早期已规划但尚未完整开发的产品能力。建议在 P10 hard cutover 稳定后再排期。

### 风控预警系统

- [ ] 后端创建 `services/risk_alert_service.py`。
- [ ] 后端实现组合风险检查逻辑。
- [ ] 后端实现单日亏损上限检查。
- [ ] 前端 Dashboard 显示当前组合风险。
- [ ] 后端提供实时通知通道；V1 可优先评估 SSE，只有需要双向交互时再上 WebSocket。
- [ ] 前端集成 Toast 或工作台内预警通知。

### 数据导入导出

- [x] 后端创建导入端点 `/api/positions/import`。
- [x] 后端解析 CSV/Excel 文件。
- [x] 后端实现字段映射和数据验证。
- [x] 前端实现导入向导 UI。
- [ ] 文档补充导入模板说明。
- [ ] 后端集成 PDF 生成库。
- [ ] 后端创建周报 PDF 模板。
- [ ] 前端报告页添加导出 PDF 按钮。

### AI 分析助手

- [x] 后端创建 `services/analytics_service.py`。
- [x] 后端扩展 `routers/insights.py`，新增 `/api/insights/analyze`。
- [x] 后端扩展 `llm_service.py`，新增分析型 Prompt。
- [x] 前端在 Insights 页面新增 AI 分析助手卡片。
- [x] 前端实现分析类型选择器。
- [x] 前端实现分析结果展示。
- [ ] 前端实现日期范围选择器。
- [ ] 前后端补 AI 分析助手回归测试或最小验收用例。

### 市场数据与验证

- [ ] 拆分 market orchestration 与 provider adapter。
- [ ] 稳定 provider mapping，明确 A 股 / 港股 / 美股 / Crypto / 外汇 / 基金路由规则。
- [ ] 为市场数据 provider 补充可重复执行的验证方案。
- [ ] 明确行情降级、缓存、错误显示和 freshness 元数据规则。

### 管理员运维能力

- [ ] 后端提供数据库备份触发入口。
- [ ] 后端提供账户升级为管理员的安全入口。
- [ ] 后端提供管理员重置账户密码能力。
- [ ] Admin Jobs 页面继续扩展 stale / failed / force-cancel 的解释和操作保护。

### 图表渲染迁移

- [x] 建立 `chart.v1` schema 与 freshness/trust 包装。
- [x] Dashboard / Insights 主要图表接入共享 `ChartFrame`。
- [ ] 如果确认“彻底去 Recharts”，再把剩余 Recharts renderer 迁移到目标图表引擎。
- [ ] 迁移前先确认 ECharts、Canvas、自研 SVG 或其他 renderer 的产品目标，避免为迁移而迁移。

---

## 暂不扩张原则

- 不继续把新页面绑定到 legacy `Position / TradeBatch` 主路径。
- 不把 `frontend/lib/api.ts` 继续扩成长期契约层。
- 不在 truth hard cutover 前删除 legacy 模型；先标记迁移边界，再安全清理。
- 不把 Dashboard 重新做回默认首页；默认入口继续围绕 Timeline / Review Inbox。
- 不在 observability 和 rollback 边界不清楚时进行不可逆数据迁移。
