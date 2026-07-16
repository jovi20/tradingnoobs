# Trading Noobs 项目描述与后续计划

更新时间：2026-07-17
当前分支：`dev`
当前状态：`TRADING_JOURNAL_HARDENING_ACTIVE / NOT_READY_FOR_PRODUCTION`

Trading Noobs 是一个交易记录、复盘、风控和分析系统。它面向主动交易用户，核心目标是把交易从“流水记录”提升为可复盘、可审计、可导出、可追踪风险的决策工作台。

当前实施以 [Trading Journal Launch-Safe Development Plan](./superpowers/plans/2026-07-16-dev-trading-journal-development-plan.md) 为准；完整 gap 文档只作为审计基线和风险登记册。

## 项目定位

当前系统采用前后端分离架构：

| 层级 | 当前实现 |
|------|----------|
| 前端 | Next.js 16、React 19、TypeScript、Tailwind CSS、React Query。 |
| 后端 | FastAPI、SQLAlchemy、Pydantic、Alembic。 |
| 数据库 | 本地默认 SQLite，部署默认 PostgreSQL。 |
| 图表 | 内部 SVG renderer，使用稳定 `chart.v1` schema。 |
| 部署 | Docker Compose + Caddy；支持 main/dev 在同一台 VPS 上并行部署。 |
| 可观测性 | request id、响应耗时、统一错误 envelope、结构化日志 helper。 |

## 当前产品形态

| 模块 | 当前状态 |
|------|----------|
| Timeline / Review Inbox | 默认首页和主要工作台；交易/复盘主链保留，风险卡在 Beta 默认关闭。 |
| Lifecycle Detail | 单笔交易生命周期详情；事件、证据和纠错保留，AI sidecar 在 Beta 默认关闭。 |
| Dashboard | 宏观视图代码切片已存在；Beta 只启用可对账的基础指标，风险卡默认关闭。 |
| Positions | 已有 truth bridge 和部分 truth event 写入；普通 OPEN 仍是 legacy-first create-and-sync，待 `JRN-007/008` 收敛。 |
| Insights / AI | 代码切片存在；Beta 标记为 `DEFERRED_BY_SCOPE` 并默认关闭。 |
| Market Data | last-known quote 与日线代码切片存在；交易日志 Beta 的按需和自动行情全部标为 `DEFERRED_BY_SCOPE`。 |
| Admin Operations | Beta 只保留用户支持、jobs 与必要 ops；不扩完整 Admin route family。 |
| Reporting / Import | 通用一次性 bootstrap 与 `IBKR_FLEX_XML_V1` source-bound 文件增量 Import 是 active plan 核心任务；在线 Broker Sync 与 PDF 默认关闭。 |

## 历史阶段切片

P0-P19 阶段计划已经归档，详见 [superpowers/plans/archive/README.md](./superpowers/plans/archive/README.md)。归档只表示对应切片收口，不表示产品能力、数据正确性或生产闭环全部完成。

关键完成点：

- P8-P9F：Next 16 / React 19 升级、Timeline-first 前端、Dashboard/Lifecycle 工作台、chart schema/freshness 包装、strict lint。
- P10-P12B：truth/legacy 边界盘点、P11 truth hard cutover、OpenAPI/legacy DTO 边界、request observability、统一错误契约、rollback playbook。
- P13-P18：风险提醒、报告导出、AI 分析、市场数据平台、管理员运维、内部 SVG 图表 renderer。
- P19：曾形成一组本地 release evidence；该历史 `READY_FOR_STAGING_ONLY` 已被后续全量 gap 审计取代。

## 当前风险与约束

| 风险 | 说明 | 当前策略 |
|------|------|----------|
| 当前 WIP 尚未冻结 | Broker/Market、frontend 重构、迁移和 journal 变更混在大型 dirty tree；四个新 migration 仍未跟踪。 | `JRN-000` 先分类 checkpoint，并采用 `IN_CHAIN_DISABLED` 的 `9cad10111213` migration baseline。 |
| 交易日志仍有发布阻断 | 导入、账务、现金硬删除、凭据、双写和恢复证据尚未闭环。 | 只执行当前 trading-journal active plan，完成后再进入 invite-only Beta 决策。 |
| legacy 路径仍存在 | `Position / TradeBatch / Transaction / AssetMetadata / DailySnapshot` 仍支撑部分迁移、fallback、Dashboard、导入和账户流水路径。 | 先隔离和标记边界，再逐步删除。 |
| `backend/models.py` 仍集中 | 模型还没有物理拆分。 | `DEFERRED_BY_SCOPE`；等会计和 truth/legacy 语义稳定后再评估。 |
| 前端 raw legacy DTO 仍有 allowlist | 部分页面还使用 legacy DTO 作为 migration/support 或 bridge。 | 新页面不继续扩张 raw DTO；逐步迁到 read-model adapter/generated contracts。 |
| Staging 还未实际部署验证 | 历史 P19 本地证据不能证明真实 PostgreSQL/backup。 | 先完成 M0-M2；真实 staging 是 `JRN-021`。 |
| 主应用 CI/CD 尚未建立 | 已删除旧 GitHub Pages workflow；当前还没有覆盖 backend/frontend 的真实 CI/CD。 | `JRN-002` 当前 P0 mandatory。 |

## 后续路线图

1. `WIP_BASELINE`：分类当前 dirty tree，固定 `9cad10111213` migration baseline 和 optional-code disposition，形成可复验 checkpoint。
2. `SAFE_BASELINE`：冻结 invite-only、单币种交易日志范围，建立强制 feature gates、PostgreSQL CI 和租户/安全边界。
3. `DATA_SAFE`：完成单币种会计、canonical 单事务写入、不可变现金/交易纠错、通用 bootstrap 和 source-bound 重叠增量 Import。
4. `JOURNAL_COMPLETE`：让 derived view 达到 freshness/recovery 结果门，统一 Timeline/Lifecycle/realized Dashboard，并交付 canonical 数据导出；worker 只可作为非权威加速器。
5. `BETA_READY`：完成生产 migration gate、PostgreSQL backup/restore、真实 staging 和浏览器主链验收。
6. 在线 Broker Sync、Market Data、风险、AI 和 PDF 作为独立 optional train，在各自启用门通过后再开放；在线 Broker 未来复用已验证的 source binding/canonical confirm。

## 不做事项

- 不把已完成 P0-P19 计划继续当作 active lane。
- 不在交易日志 active plan 和真实 staging 通过前宣布 production ready。
- 不直接删除 legacy 模型或 API，除非 replacement、migration、rollback 都明确。
- 不继续扩大 `frontend/lib/api.ts` 的 raw DTO 责任。
- 不用未来量化、Redis、多 schema 或模型拆分扩大当前发布范围。
- 不把历史计划文件从 archive 中删除；它们仍是决策证据。
