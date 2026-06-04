# Trading Noobs 平台底座 Implementation Plan（v1）

> 基于补齐后的平台底座 spec v1.1，按“先地基、后能力；先真相、后分析；先一致性、后体验”的顺序拆成可执行工作流。
> 当前默认前提：环境仍处于 pre-production，可直接 hard cutover，不为试运行数据或旧 `Position / TradeBatch` 契约保留兼容层。

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
