# Trading Noobs 平台底座 Implementation Plan（v1）

> 基于补齐后的平台底座 spec v1.1，按“先地基、后能力；先真相、后分析；先一致性、后体验”的顺序拆成可执行工作流。
> 当前默认前提：环境仍处于 pre-production，可直接 hard cutover，不为试运行数据或旧 `Position / TradeBatch` 契约保留兼容层。

---

## 0. 当前进度快照（2026-05-02，再次审查修订）

### 0.1 分支与落地方式

- 当前平台底座改造统一在 `dev` 分支 worktree 内推进。
- `main` 保持原版，用于后续对比评估，不在本轮直接改写。
- 下一次继续业务实现前，需要先建立 `dev` 阶段检查点：记录当前 diff 范围、可运行测试命令、已知阻塞项，避免后续 `main` vs `dev` 评估变成不可读的大 diff。
- 当前进度已经落到项目文件，包括：
  - 本实施计划
  - frontend/backend sequencing plan
  - trust metadata / timeline / lifecycle contracts
  - 后端迁移、认证、平台配置、交易真相初版与前端 timeline-first 改造

### 0.1.1 状态标记规则

- **已完成**：代码路径、测试、契约和页面消费均达到完成定义。
- **Bridge landed**：已有可运行过渡实现，但仍依赖 legacy 表、legacy endpoint 或手动同步，不计入正式完成。
- **部分完成**：契约或基础模型已落地，但缺关键链路、验收测试或用户侧最终路径。
- **未开始**：尚无可执行代码或可验收文档。

### 0.2 阶段状态总览

| Stage | 状态 | 说明 |
| --- | --- | --- |
| Stage 0：冻结与护栏 | 大部分完成 | 命名、用户侧 trust contract、timeline/lifecycle contract、hard cutover 方向已冻结；错误码/日志基础仍未冻结 |
| Stage 1：数据库地基与认证底座 | 大部分完成 | `A2`, `B1`, `B2`, `B3` 已落地；`A1`, `A3`, `B4` 仍未完成 |
| Stage 2：交易真相模型切换 | Bridge landed / C4 部分完成 | `C1` 与 `C2` 已有初版 truth layer 和 legacy sync bridge；`C3` 已有 AccountLedgerEntry 基础 bridge；`C4` 已有 FIFO accounting service 并接入 legacy truth sync、legacy batch router recalculation、positions/dashboard mark-to-market 与 account signed market value；旧 `Position / TradeBatch` 仍是主写路径 |
| Stage 3：异步一致性与用户读模型基础 | 部分完成 / Bridge landed | Timeline/Lifecycle contract 与首版 API 已落地，但 Timeline 仍由 legacy `Position`/旧 AI 表派生；outbox/job/idempotency 仍未开始 |
| Stage 4：市场数据和 analytics 分层 | 未开始 | 仍主要依赖旧 `MarketDataService` 与请求链路内统计 |
| Stage 5：AI / 内容 / 后台运维强化 | 未开始 | 现有 AI 能力仍未迁到独立 schema/workflow |
| Stage 6：测试、发布、硬化 | 进行中 | 已有 migration / router / adapter 级测试，但 release/rollback、恢复演练、阶段 commit/对比边界未建立 |

### 0.3 已完成或已有初版的关键成果

- 已接入 Alembic 迁移链，应用启动不再无条件 `create_all()`。
- 用户体系已补 `public_id`, `email_normalized`, `status`, `last_login_at`, `locale`, `timezone`。
- 认证支撑表 `user_credentials`, `user_sessions`, `user_identities`, `auth_tokens` 已落地，并接到登录/登出/鉴权链路。
- 平台配置治理 `platform_settings`, `integration_credentials`, `feature_flags` 已落地，后台已能管理平台级配置。
- 高频用户路由已大面积切到 `public_id`。
- `AssetMaster`, `TradeInstrument`, `TradingPosition`, `PositionEvent` 已有初版 truth schema 与同步服务。
- `AccountLedgerEntry` 已有初版 schema / migration / service；legacy realized PnL 与账户 transaction 会写入 ledger，Lifecycle `cash_effects` 已从 ledger 读取。
- 已有 `/api/trading-positions/{position_public_id}/lifecycle` truth read API，并已收紧为普通用户路径只接受 `TradingPosition.public_id`；legacy bridge `/api/positions/{id}/truth-lifecycle` 保留为迁移/过渡路径。
- 单笔详情页已支持优先用 `TradingPosition.public_id` 直接读取 truth lifecycle 主叙事；已展示 lifecycle `evidence_list` 与 `ai_sidecar`，legacy `Position / TradeBatch` 数据存在时明确标成迁移、校准和回填辅助区块。
- 已新增 truth event 叙事字段写入口 `PATCH /api/trading-positions/{position_public_id}/events/{event_public_id}`，可用 `PositionEvent.public_id` 更新 reason / emotion / confidence / thesis / invalidation / planned exit / sizing / checklist / note 等 C5 字段；前端详情页已有独立 truth narrative 编辑入口，会写入 `PositionEvent` 并刷新 lifecycle read model。
- 已新增 `trading_accounting_service` 的 FIFO 口径核心，覆盖 long/short realized PnL、FIFO lot matching、fee netting、remaining open-lot cost basis、open-position mark-to-market 与 account signed market value；legacy truth sync 已改为从 `PositionEvent` 重放结果推导 truth aggregate、event realized PnL 与 ledger amount，不再盲信 legacy realized_pnl；legacy batch router/import recalculation、positions open-position display、dashboard open-position aggregation 与 account NAV market value 已改用同一服务重算。
- `/api/timeline/home` 已补 bridge 级 `limit` / `cursor` 分页行为，按稳定排序后的 timeline event card 切页，并返回 opaque `next_cursor`。
- 前端默认入口已切到 timeline-first，Dashboard 改为次级入口；后端 Timeline Home 当前仍是 legacy-derived bridge，不视为 truth-backed 首页完成。
- 前端已建立 read-model / adapter 层，并接上 Timeline Home 与 Lifecycle Preview；Lifecycle Preview 当前是 truth bridge 预览，不是最终详情页替代。

### 0.4 当前主要缺口

- 仍未完成真正的 hard cutover：旧 `Position / TradeBatch` 仍是价格、数量、批次和部分复盘的主写模型；详情页已有 truth-first 入口，C5 叙事字段已接到 truth event 写入口，但旧批次价格/数量编辑流尚未切换。
- Timeline Home 当前仍从 legacy `Position`、`AISummary`、`AIAnalysisResult` 派生，不是基于 `TradingPosition / PositionEvent / InsightArtifact` 的最终 read model。
- Lifecycle Detail 用户侧 public_id-only contract 已补回归测试并落地；前端已能展示 evidence / ledger / AI sidecar，但后端 AI sidecar 生成、InsightArtifact 正式写入与最终 evidence 覆盖仍未完成。
- `AccountLedgerEntry` 现金真相基础已建立，但账户余额 read model 尚未完全改成 ledger-derived，dividend / cash adjustment 的正式入口仍需后续补齐。
- Lifecycle `ledger_summary.cash_effects` 已读取 ledger；`total_fees` 的最终 fee 归属、dividend / adjustment 汇总与 AI workflow 写入仍未完成，不能标为最终 evidence/AI sidecar 完成。
- FIFO / fee / FX 口径已有 C4 服务起点并接入 legacy truth sync、legacy batch router/import recalculation、positions open-position display、dashboard mark-to-market 与 account signed market value；账户余额 read model 和部分 analytics/timeline legacy realized PnL 汇总仍未彻底收敛到 truth/ledger-derived。
- outbox / job system / idempotency / job status 仍为空白，后续 derived refresh 没有稳定异步底座。
- Timeline contract 中的 `cursor` / `limit` 已有 bridge 级实现；最终 truth-backed Timeline read model 尚未完成。
- 市场数据分层、provider symbol mapping、derived/materialized analytics 还未开始。
- AI schema / prompt registry / insight workflow / usage metering 仍未进入正式平台化阶段。
- `dev` 分支当前改动量较大且未形成阶段性提交边界，后续对比评估风险上升。

### 0.5 接下来建议执行顺序

1. 先完成计划修正与 `dev` 检查点：记录 bridge 状态、可运行验证命令、阶段性 diff 边界，为后续 `main` vs `dev` 评估做准备。
2. 在 `dev` 上形成阶段性提交边界，避免 C1-C3 与前端桥接继续扩大成不可读 diff。
3. 继续推进 `C2 + C5` hard cutover：详情页 UI 的叙事字段编辑已接到 truth event 写入口；下一步应先完成 C4 accounting service，再把价格/数量/批次操作从 legacy `Position / TradeBatch` 迁到 `TradingPosition / PositionEvent` 写路径。当前旧控件已明确标成迁移工具，但仍不是最终 truth 写路径。
4. 继续完成 `C4`：清理账户余额 read model，把它进一步收敛到 ledger-derived；随后再把价格/数量/batch 写操作迁往 truth 写路径。
5. 再推进 `D1 -> D3`，先把 outbox、job model、idempotency 补齐，再做任何重 derived 刷新。
6. 在异步底座具备后推进 `E1`, `E2`, `F1`, `F4`，把市场数据编排和 dashboard/detail 派生读路径迁出请求链路。
7. 等上述链路稳定后，再进入 `G` 与 `H3/H5`，补齐 AI 平台化、运维健康面板和发布恢复流程。

---

## 1. 执行原则

1. **先冻结真相层，再扩读模型**
2. **先上正式迁移链，再做大规模表改造**
3. **先补事务外一致性，再依赖异步刷新**
4. **先建立 schema-first 契约，再换图表实现**
5. **先把 AI 变成可审计 workflow，再扩更多分析能力**
6. **每一阶段都必须可回滚、可观测、可测试**
7. **当前阶段允许 hard cutover，但要一次性切干净，不保留半新半旧兼容层**

---

## 2. 交付泳道

- `A. Schema & Migration`
- `B. Core/Auth/Security`
- `C. Trading Truth Model`
- `D. Jobs/Outbox/Async`
- `E. Market Data`
- `F. Analytics & Chart Schema`
- `G. AI Platform`
- `H. Admin/Ops/Observability/QA`
- `I. Frontend Contract Alignment`

---

## 3. 依赖顺序

### Stage 0：冻结与护栏
先完成：

- 架构命名冻结
- 迁移纪律冻结
- 错误码/日志基础冻结
- 核心模型切换策略冻结
- pre-production hard cutover 策略冻结

### Stage 1：数据库地基与认证底座
先完成：

- Alembic 正式启用
- schema 建立
- users/auth/session/public_id
- platform settings / credentials / feature flags

### Stage 2：交易真相模型切换
先完成：

- AssetMaster / TradeInstrument
- TradingPosition / PositionEvent / AccountLedgerEntry
- 成本法 / PnL / FX 口径服务
- 导入/IBKR 映射到新真相层
- 旧 `Position / TradeBatch` 语义入口下线

### Stage 3：异步一致性与用户读模型基础
先完成：

- outbox
- job system
- timeline / review inbox / lifecycle detail read models
- 用户侧统一 response envelope：`public_id`, `as_of`, `freshness`, `source`, `maturity`, `value_status`
- dashboard / position metrics refresh
- market warmup trigger

### Stage 4：市场数据和 analytics 分层
先完成：

- provider_symbol_mapping
- orchestrator 拆分
- chart schema / registry
- 读模型与物化迁移

### Stage 5：AI / 内容 / 后台运维强化
先完成：

- ai schema
- prompt registry
- insight run lifecycle
- admin jobs/ai/market ops

### Stage 6：测试、发布、硬化
持续贯穿，但在末段补齐：

- migration tests
- integration tests
- release/rollback workflow
- backup/restore drill

---

## 4. 详细任务清单

## A. Schema & Migration

### A1. 建立多 schema PostgreSQL 基线
**优先级：P0**

任务：

- 新建 schema：`core`, `reference`, `market`, `derived`, `audit`, `content`, `ai`
- 配置 ORM metadata 支持 schema
- 统一命名规则：表名蛇形、主键 bigint、外部 public_id uuid

完成定义：

- 数据库可通过正式迁移一键建出七域空骨架
- 本地/测试/生产环境 migration 路径一致

### A2. 接入 Alembic 正式迁移链
**优先级：P0**

任务：

- 初始化正式 `alembic/versions`
- `env.py` 启用 `include_schemas=True`
- 建立迁移模板与 review 规范
- 停止线上 `create_all()`

完成定义：

- 空库可 `upgrade head`
- 现有库可通过迁移链升级
- 应用启动路径不再自动建表

### A3. 建立 expand/migrate/contract 模板
**优先级：P0**

任务：

- 明确 rename/拆表/字段切换模板
- 设计 backfill job 模板
- 设计 migration event 审计记录
- 明确当前阶段为 pre-production hard cutover，可对试运行库直接替换旧核心表与旧接口契约

完成定义：

- 当前阶段的直接切换与未来正式生产阶段的渐进式 rollout 边界清晰

---

## B. Core/Auth/Security

### B1. users 表重构
**优先级：P0**

任务：

- 新增 `public_id`, `status`, `email_normalized`, `last_login_at`, `locale`, `timezone`
- 补唯一索引与状态约束
- 用户侧 API 与前端路由默认切到 `public_id`

完成定义：

- API 默认可返回 public_id
- email 查询统一走 normalized 字段
- 普通用户接口与页面不再依赖内部自增 id

### B2. 认证支撑表落地
**优先级：P0**

任务：

- 新建 `user_credentials`
- 新建 `user_sessions`
- 新建 `user_identities`
- 新建 `auth_tokens`

完成定义：

- 登录/登出/会话失效路径可追踪
- 后续邮箱验证、密码重置、SSO 有表结构挂点

### B3. 平台配置与凭据治理
**优先级：P0**

任务：

- 新建 `platform_settings`
- 新建 `integration_credentials`
- 新建 `feature_flags`
- 建立敏感配置掩码返回策略

完成定义：

- 平台配置、用户偏好、环境变量边界清晰
- 后台可以改非敏感平台配置并留下审计

### B4. 安全事件审计
**优先级：P1**

任务：

- 新建 `audit.auth_events`
- 登录失败、密码重置、token 撤销全写审计
- Auth 端点限流接 Redis

完成定义：

- 用户安全动作均可追踪
- 暴力尝试可被限制

---

## C. Trading Truth Model

### C1. 引入 AssetMaster / TradeInstrument
**优先级：P0**

任务：

- 新建 `reference.asset_master`
- 新建 `reference.trade_instruments`
- 将现有 `AssetMetadata` 能力收敛进新 reference 模型，不保留旧命名兼容层
- 建立 instrument type enum：`SPOT`, `EQUITY_OPTION`

完成定义：

- 现货与股票期权可在统一模型下建模
- provider symbol 不再和资产主体混用

### C2. Position 模型切换为 TradingPosition + PositionEvent
**优先级：P0**

任务：

- 定义 `trading_positions`
- 定义 `position_events`
- 明确事件类型与状态流转
- 前后端直接切到新模型与新命名
- 下线旧 `Position` / `TradeBatch` 语义入口与 DTO

完成定义：

- 一次完整生命周期可由 events 重放
- UI 不再直接依赖旧批次模型语义
- 系统不再保留旧模型兼容层

### C3. 引入 AccountLedgerEntry
**优先级：P0**

任务：

- 资金流水与持仓事件解耦
- 关联 deposit/withdraw/dividend/fee/cash adjustment
- 与 position event 建立可选关联
- 明确 `dividend / fee / cash adjustment` 以 `AccountLedgerEntry` 为现金真相，不双写两份真相

完成定义：

- 账户级净值和持仓级盈亏可以分开计算与对账
- 现金余额计算来源单一清晰

### C4. 口径中心化服务
**优先级：P0**

任务：

- 新建 `trading accounting service`
- 实现 FIFO 成本法
- 明确 realized/unrealized 计算边界
- 明确 fee/FX 归属
- 当前阶段直接废弃旧平均成本实现，不保留历史兼容

完成定义：

- PnL 计算不再散落 router/service/frontend
- 同一条交易在各页面口径一致
- V1 口径从第一天起即为 FIFO

### C5. 决策质量字段补齐（前端阻塞项）
**优先级：P0**

任务：

在 `position_events` 增加：

- thesis
- edge_source
- disconfirming_evidence
- invalidation_rule
- expected_holding_period
- planned_exit_rule
- sizing_rationale
- checklist_snapshot
- 明确 `thesis`, `invalidation_rule`, `sizing_rationale`, `checklist_snapshot` 为 Timeline / Review Inbox / Lifecycle Detail / AI sidecar 首批必需字段，不能后置到纯体验增强阶段

完成定义：

- AI 与 analytics 能直接分析决策质量而不只是盈亏结果
- 前端 Phase 2 / Phase 3 不需要再依赖旧 note 字段和页面拼装逻辑来补叙事

### C6. 公司行为与修正策略
**优先级：P1**

任务：

- 支持 split/dividend/symbol change 基础事件
- 建立 reversal / manual adjustment 规则
- 禁止静默改历史真相

完成定义：

- 历史修正有审计、有事件、有回放能力

---

## D. Jobs/Outbox/Async

### D1. 统一 job model
**优先级：P0**

任务：

- 新建 `job_definitions`, `job_runs`, `job_run_events`, `idempotency_keys`
- 统一状态机与 retry policy
- 替代零散后台任务记录

完成定义：

- 所有异步任务都能在统一表与后台里看到

### D2. 落地 transactional outbox
**优先级：P0**

任务：

- 新建 `outbox_events`
- 业务事务中同时写 outbox
- 独立 relay 将 outbox 投递 Redis
- worker 消费 Redis job

完成定义：

- 交易/导入/同步成功后不会因为 enqueue 丢失导致派生状态不刷新

### D3. 并发与幂等规则
**优先级：P0**

任务：

- 实现 asset/timeframe、broker connection、content source、AI scope 级锁
- 导入、手动同步、AI 触发支持 idempotency key

完成定义：

- 重试安全
- 不会对同一对象并发重复跑重任务

### D4. 任务状态查询 API
**优先级：P1**

任务：

- 新建 job read API
- 前端可看到 queued/running/failed/completed
- 失败原因与重试历史可查

完成定义：

- 用户与管理员都能理解后台工作进度

---

## E. Market Data

### E1. 拆 MarketDataService 为三层
**优先级：P0**

任务：

- adapter 层：上游 provider API 调用与字段映射
- capability registry：provider 覆盖能力矩阵
- orchestrator：选择、fallback、缓存、落库、质量状态

完成定义：

- 现有胖服务职责拆清
- 新 provider 接入不再改一堆业务逻辑

### E2. provider_symbol_mapping 与 coverage 模型
**优先级：P0**

任务：

- 落 `provider_symbol_mappings`
- 落 `market_data_coverage`
- 建 asset lazy-load 流程
- `provider_symbol_mappings` 同时支持 asset-level 与 instrument-level 映射，期权强制 instrument-level

完成定义：

- 资产主体、交易工具、provider symbol 三层彻底分离
- 不会把“属于 AAPL”误当成“就是某一个 AAPL 期权合约”

### E3. quote / daily / intraday 表落地
**优先级：P1**

任务：

- 新建 `quote_snapshots`
- 新建 `price_bars_daily`
- 新建 `price_bars_intraday`
- 设计分区与 retention 基线

完成定义：

- 日线长期保留
- 分钟线只对开放仓位标的 active-tracking

### E4. 新标的 warmup 流程
**优先级：P1**

任务：

- 首次识别资产 -> 生成/补齐 asset_master
- 拉取 profile + latest quote
- 异步预热 6-12 月日线
- 开放仓位触发 intraday tracking

完成定义：

- 首次使用受支持标的时的体验一致

---

## F. Analytics & Chart Schema

### F1. analytics 模块独立化
**优先级：P0**

任务：

- 从 router/service 中抽 `read model queries`
- 抽 `metric builders`
- 抽 `presentation adapters`

完成定义：

- dashboard、position detail 不再在 router 里现场拼复杂统计

### F2. chart schema & registry
**优先级：P0**

任务：

- 定义 chart schema 外壳
- 建 chart registry
- 定义 input contract / freshness / cache policy

完成定义：

- 新增图表时走统一注册流程
- 不直接输出某图表库的私有数据结构

### F3. ECharts renderer 层
**优先级：P1**

任务：

- 建立 schema -> ECharts option 转换器
- 做主题适配与 i18n hook
- 替换现有 dashboard/position detail 中耦合较重的图

完成定义：

- Web 图表统一渲染栈
- 为未来 App 端保留 schema 复用可能

### F4. Derived 刷新落地
**优先级：P1**

任务：

- `dashboard_cache`
- `position_metrics`
- `portfolio_snapshots`
- `chart_materializations`
- `risk_views`

完成定义：

- 高成本查询从请求链路迁出
- Dashboard 与详情页可接受延迟但口径稳定

---

## G. AI Platform

### G1. AI schema 落地
**优先级：P1**

任务：

- 新建 `ai_providers`
- 新建 `prompt_templates`
- 新建 `prompt_template_versions`
- 新建 `insight_runs`, `insight_artifacts`, `ai_usage_records`, `ai_cache_entries`

完成定义：

- AI 运行数据不再混杂在通用表中

### G2. prompt registry + versioning
**优先级：P1**

任务：

- 平台维护 prompt 模板
- 明确变量定义、输出 schema、版本发布/回滚
- 管理员测试运行与审计

完成定义：

- prompt 不再硬编码在单个 service 文件里

### G3. AI workflow orchestration
**优先级：P1**

任务：

优先工作流：

- weekly_insight_report
- journal_digest
- position_review
- strategy_health
- losing_streak_analysis
- emotion_pnl_analysis
- checklist_effect_analysis

完成定义：

- 每个 workflow 有输入、输出、版本、缓存与可见性策略

### G4. AI usage & cost metering
**优先级：P2**

任务：

- 记录 token/cost/latency
- 标记 cache hit/miss
- 预留套餐与额度能力挂点

完成定义：

- AI 商业化与控成本具备底座

---

## H. Admin/Ops/Observability/QA

### H1. 结构化日志与错误码
**优先级：P0**

任务：

- 全面替换 `print()`
- 错误码分层：auth/trading/market/analytics/ai/content/platform
- 请求日志、任务日志、provider 日志统一字段

完成定义：

- 排障不再依赖手工 grep 与模糊文本

### H2. 后台入口重构
**优先级：P1**

任务：

- 用户设置页与管理员后台解耦
- 建 `/admin/platform`, `/admin/users`, `/admin/jobs`, `/admin/market-data`, `/admin/ai`, `/admin/ops`

完成定义：

- 用户不再在同一设置页里混看到管理员能力

### H3. Data freshness / provider health / job health
**优先级：P1**

任务：

- provider health 看板
- data freshness 看板
- queue/job 积压与失败看板

完成定义：

- 能从系统内部直接看到“哪里旧了、哪里挂了、哪里堵了”

### H4. 测试基线
**优先级：P0**

任务：

- 单元测试：PnL、生命周期、FX、market resolution、chart schema、AI output schema
- 集成测试：认证、创建交易、导入幂等、outbox->job->derived、AI workflow happy/fail path
- 迁移测试：upgrade head、旧库升级

完成定义：

- 主干功能可自动回归

### H5. 发布与恢复流程
**优先级：P1**

任务：

- release checklist
- migration checklist
- rollback checklist
- backup/restore 演练记录模板

完成定义：

- 每次发布、迁移、回滚都有固定动作模板

---

## I. Frontend Contract Alignment

### I1. 用户侧响应元协议与 Trust Metadata
**优先级：P0**

任务：

- 冻结文档：`docs/superpowers/specs/2026-04-13-user-trust-metadata-contract.md`
- 为用户侧 read model 统一 envelope，固定输出 `as_of`
- 冻结 `freshness` 枚举：`FRESH`, `DELAYED`, `STALE`, `DEGRADED`
- 冻结 `source` 枚举：`MANUAL`, `IMPORTED`, `SYNCED`, `DERIVED`, `AI_GENERATED`
- 冻结 `maturity` 枚举：`INSUFFICIENT_SAMPLE`, `EARLY_SIGNAL`, `STABLE`
- 冻结 `value_status` 枚举：`ESTIMATED`, `FINAL`

完成定义：

- 前端 freshness banner / source badge / maturity pill 可复用于 timeline、dashboard、insights
- 新页面不再各自发明一套数据质量字段和解释文案

### I2. Timeline + Review Inbox 读模型契约
**优先级：P0**

任务：

- 冻结文档：`docs/superpowers/specs/2026-04-13-timeline-review-inbox-contract.md`
- 定义首页聚合查询与 API，返回顶部摘要、Review Inbox、主时间线、右侧上下文所需数据
- 冻结首页时间线事件类型集合：`OPEN`, `ADD`, `REDUCE`, `CLOSE`, `REVIEW_COMPLETED`, `AI_INSIGHT`, `CHECKLIST_MISS`, `LOSING_STREAK_ALERT`, `DATA_STALE`, `SYNC_EXCEPTION`
- 定义 Review Inbox item contract：`kind`, `severity`, `summary`, `reason`, `recommended_action`, `linked_object_public_id`
- 首页对象和事件默认使用 `public_id` 深链，不再暴露内部自增 id 作为前端主路由键

完成定义：

- 前端 Phase 2 能直接实现 timeline-first 首页
- 首页不需要再从 position / event / raw insight 多接口现场拼装

### I3. Lifecycle Detail + Evidence 读模型契约
**优先级：P0**

任务：

- 冻结文档：`docs/superpowers/specs/2026-04-13-lifecycle-detail-contract.md`
- 定义单笔详情 API，按 `TradingPosition.public_id` 返回完整生命周期线程
- 冻结线程节点集合：`OPEN`, `ADD`, `REDUCE`, `CLOSE`, `REVIEW`, `AI_CONCLUSION`
- 返回 thesis、invalidation、planned exit、sizing rationale、checklist snapshot、execution drift、PnL basis、ledger summary、evidence links
- AI sidecar 通过 `insight_run_id` / `insight_artifact_id` 与支撑证据建立可回跳引用

完成定义：

- 前端 Phase 3 可以做生命周期详情和 evidence-first AI sidecar
- 单笔详情不再依赖旧 `Position + TradeBatch` DTO 反推交易故事

### I4. 前端实施 Gate 对齐
**优先级：P1**

任务：

- 定义 frontend Phase 1 可在包 0 / 包 1 并行启动，范围限于 shell / navigation / tokens / primitives / adapter skeleton
- 定义 frontend Phase 2 依赖：包 2 + I1 + I2
- 定义 frontend Phase 3 依赖：包 2 + C5 + I3
- 定义 frontend Phase 4 依赖：包 3 + G1 / G3

完成定义：

- 设计系统与页面迁移的并行窗口明确
- 团队不会误把 Dashboard-first 重构当成当前主线路

---

## 5. 建议的第一批落地包（按收益/风险排序）

### 包 0：联合冻结与 Contract 包

- Stage 0 冻结事项
- I1
- I4

目标：

- 先把跨端命名、trust metadata 和前端启动边界写死
- 避免前后端各自开工后再回头重构接口与页面语义

### 包 1：必须先做的地基包

- A1, A2, A3
- B1, B2, B3
- H1, H4

目标：

- 停止无纪律 schema 演进
- 补齐认证/配置/日志最小底座

### 包 2：交易真相包

- C1, C2, C3, C4, C5
- D1, D2, D3

目标：

- 建立新的交易真相层
- 让异步刷新具备事务外一致性
- 提前把首页与生命周期详情所需的叙事字段并入真相层

### 包 3：用户读模型、市场与分析包

- I2, I3
- E1, E2
- F1, F2
- F4

目标：

- 把 timeline / lifecycle / dashboard 的用户读模型先稳定下来
- 把胖 router / 胖 service 的主要复杂度抽出来
- 让 dashboard / 图表开始基于稳定契约

### 包 4：体验增强包

- C6
- E3, E4
- F3
- H2, H3

目标：

- 做出更强的决策质量分析与运营可见性

### 包 5：AI 中台包

- G1, G2, G3
- D4
- H5

目标：

- AI 从“功能堆叠”升级为“可审计 workflow 平台”

---

## 6. 建议的代码目录演进方向

### backend

- `app/core/`
- `app/modules/trading/`
- `app/modules/market/`
- `app/modules/analytics/`
- `app/modules/ai/`
- `app/modules/content/`
- `app/modules/admin/`
- `app/jobs/`
- `app/outbox/`
- `app/db/`
- `app/schemas/`

### frontend

- `app/(user)/settings/...`
- `app/(admin)/admin/...`
- `features/trading/...`
- `features/dashboard/...`
- `features/analytics/...`
- `features/ai/...`
- `components/charts/renderers/...`
- `components/charts/registry/...`

---

## 7. 每个阶段的完成检查

### 架构层完成标志

- 新 schema 已落库
- Alembic 已成为唯一 schema 入口
- 关键命名已切换
- outbox/job 已接管异步一致性
- analytics/chart schema 已脱离 router 拼装
- AI 已能按 workflow/version/run 审计

### 产品层完成标志

- 用户首页 timeline + review inbox 可稳定刷新，并显示 freshness / source / maturity
- 单笔详情页可还原完整 lifecycle thread，并能下钻到 evidence / AI artifact
- 用户创建/编辑交易后 dashboard 能稳定刷新
- 导入重试不会产生重复交易
- 首次接入标的可自动建立资产与预热流程
- AI 结果可回溯到输入与 prompt version
- 后台可看到 provider/job/data freshness 状态

---

## 8. 不建议在当前阶段插队的事项

- 微服务化
- Kafka 化
- 全面时序数据库替换
- 期权行情中台
- 重型实时风控引擎
- 用户自定义 prompt 平台
- 复杂多租户组织模型

---

## 9. 进入开发前的冻结清单

在真正开始改代码前，建议先把以下内容作为书面冻结项：

- 七域 schema 名称
- TradingPosition / PositionEvent / AccountLedgerEntry 命名
- AssetMaster / TradeInstrument / provider_symbol_mapping 三层关系
- FIFO 为 V1 默认成本法
- `outbox_events` 为必选项
- chart schema-first 为必选项
- AI prompt 平台维护、普通用户不自定义
- API 默认对外暴露 public_id
- `DIVIDEND / FEE / CASH_ADJUSTMENT` 以 ledger 为现金真相
- `provider_symbol_mappings` 支持 instrument-level 映射
- 首页 `timeline + review inbox` 读模型契约冻结
- 单笔 `lifecycle detail + evidence` 读模型契约冻结
- 用户侧 read model 固定携带 `as_of / freshness / source / maturity / value_status`
- frontend Phase 1 / 2 / 3 / 4 的 backend gate 固定
- 当前阶段允许 hard cutover，不保留旧 Position / TradeBatch 兼容层
