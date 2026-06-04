# Trading Noobs 平台底座设计（补齐版 v1.1）

> 基于 2026-04-06 平台底座设计与 2026-04-05 项目基线审计补齐，目标是把架构基线推进到“可进入 implementation planning”的粒度。

---

## 1. 文档定位

本版本不是推翻原 spec，而是在保留既有关键决策的前提下，对以下四类内容做补强：

1. 金融真相模型与会计/估值口径
2. 异步一致性与任务幂等
3. 数据域、表族与命名边界
4. AI、认证、安全、可观测性的底座定义

保留不变的核心决策：

- 继续采用 module-first monolith
- PostgreSQL 作为唯一系统事实源
- Redis 负责缓存、幂等辅助与任务协调
- worker 处理重任务
- analytics + chart schema + renderer 分层
- market / derived / content 均视为可回填、可重算数据域

---

## 2. 核心新增设计原则

### 2.1 真相优先级

系统中所有数据分为四个层级：

1. **法律/交易真相层**：用户录入或券商同步得到的原始交易、资金、会话、安全记录
2. **聚合状态层**：当前持仓、账户当前余额、连接当前状态
3. **衍生分析层**：收益曲线、MAE/MFE、Dashboard、AI insight、图表物化
4. **缓存与展示层**：页面缓存、schema cache、短期 quote cache

规则：

- 真相层永远高于聚合态
- 聚合态可由真相层重建
- 衍生层必须可重算
- 缓存层允许直接失效或清空

### 2.2 金融口径必须中心化

以下口径不能散落在 router、service、前端页面或 AI prompt 中，必须由统一领域服务或规则模块定义：

- cost basis method
- realized / unrealized PnL
- fee handling
- FX conversion
- corporate actions
- option lifecycle events
- adjustment / reversal policy

### 2.3 异步触发必须具备事务外一致性

所有“写核心表后再触发异步刷新”的场景，必须采用 **transactional outbox** 模式，避免数据库写入成功但 enqueue 丢失。

---

## 3. 模块与数据域补齐

### 3.1 模块边界（补齐后）

| 模块 | 主要职责 |
|------|----------|
| `core` | config、auth、permissions、sessions、platform settings、feature flags、audit、job orchestration、outbox、observability |
| `trading` | accounts、trade instruments、positions、position events、ledger、strategies、checklists、reviews、notes |
| `market-data` | asset identity、provider adapters、capability registry、orchestrator、quotes、bars、coverage、fetch jobs |
| `analytics` | metrics、chart schemas、read models、materializations、dashboard、risk views |
| `ai` | prompt registry、context builders、workflow orchestration、insight store、usage metering、AI cache |
| `content` | sources、documents、extractions、summaries、symbol linkage |
| `admin` | platform ops、user operations、integration ops、job ops、release/migration views |

### 3.2 数据域（补齐后）

在原六域基础上，**新增 `ai` schema**，形成七域：

- `core`
- `reference`
- `market`
- `derived`
- `audit`
- `content`
- `ai`

### 3.3 各数据域职责（补齐后）

| 数据域 | 含义 | 是否真相层 | 是否可重算 |
|--------|------|------------|------------|
| `core` | 用户交易、账户、认证主体、偏好、连接主体 | 是 | 否 |
| `reference` | 共享主数据、字典、交易所、货币、资产分类、日历 | 否（稳定主数据） | 可回填/低频维护 |
| `market` | quote、日线、分钟线、provider 覆盖与质量状态 | 否 | 是 |
| `derived` | dashboard、read model、聚合缓存、物化图表、组合快照 | 否 | 是 |
| `audit` | 认证事件、配置变更、后台动作、job run、outbox、幂等键 | 追加式真相 | 部分否 |
| `content` | 新闻/文件/SEC 采集与抽取结果 | 否 | 大部分可重抓 |
| `ai` | prompt、版本、run、artifact、usage、cache | 否 | 结果可失效重算 |

---

## 4. 金融真相模型（重点补齐）

### 4.1 交易真相建模原则

交易系统采用：

- **事件真相层**：`position_events`、`account_ledger_entries`
- **聚合状态层**：`trading_positions`、账户当前余额、组合当前净值

规则：

- `position_events` 为交易行为真相，不允许用 UI 聚合状态反写真相
- `trading_positions` 是按规则归并后的生命周期聚合
- 关闭一条 position 不代表删除其 event
- 修正历史优先通过 adjustment / reversal event，而不是静默改旧记录

### 4.2 核心实体关系（补齐后）

- `User 1:N TradingAccount`
- `User 1:N TradingStrategy`
- `AssetMaster 1:N TradeInstrument`
- `TradeInstrument 1:N TradingPosition`
- `TradingPosition 1:N PositionEvent`
- `TradingAccount 1:N AccountLedgerEntry`
- `TradingPosition 0..N : 0..N TradingStrategy`（V1 可先 0..1）

### 4.3 核心表补齐建议

#### `core.trading_positions`

建议至少包含：

- `id`
- `user_id`
- `account_id`
- `instrument_id`
- `status` (`OPEN` / `CLOSED` / `ARCHIVED` / `ERROR`)
- `side` (`LONG` / `SHORT`)
- `opened_at`
- `closed_at`
- `opening_event_id`
- `closing_event_id`
- `base_currency`
- `cost_basis_method`
- `quantity_opened`
- `quantity_closed`
- `avg_open_price`
- `avg_close_price`
- `realized_pnl_gross`
- `realized_pnl_net`
- `total_fees`
- `holding_period_seconds`
- `created_at`
- `updated_at`
- `deleted_at`（软删除）

#### `core.position_events`

建议至少包含：

- `id`
- `user_id`
- `position_id`
- `account_id`
- `instrument_id`
- `event_type`
- `event_time`
- `side_effect`
- `quantity`
- `price`
- `currency`
- `gross_amount`
- `fee_amount`
- `fee_currency`
- `fx_rate_to_account_ccy`
- `realized_pnl_gross`
- `realized_pnl_net`
- `broker_exec_id`
- `external_order_id`
- `input_source`
- `source_run_id`
- `reason`
- `emotion`
- `confidence`
- `thesis`
- `edge_source`
- `disconfirming_evidence`
- `invalidation_rule`
- `expected_holding_period`
- `planned_exit_rule`
- `sizing_rationale`
- `checklist_snapshot`
- `note`
- `is_adjustment`
- `reverses_event_id`
- `created_at`
- `updated_at`

#### `core.account_ledger_entries`

建议至少包含：

- `id`
- `user_id`
- `account_id`
- `entry_type`
- `entry_time`
- `amount`
- `currency`
- `fx_rate_to_account_ccy`
- `amount_in_account_ccy`
- `related_position_id`
- `related_event_id`
- `source_type`
- `source_ref`
- `note`
- `created_at`

### 4.4 PositionEvent 事件类型标准化

V1 统一支持以下事件类型：

- `OPEN`
- `ADD`
- `REDUCE`
- `CLOSE`
- `DIVIDEND`
- `FEE`
- `CASH_ADJUSTMENT`
- `STOCK_SPLIT`
- `TRANSFER_IN`
- `TRANSFER_OUT`
- `OPTION_EXERCISE`
- `OPTION_ASSIGNMENT`
- `OPTION_EXPIRY`
- `REVERSAL`
- `MANUAL_ADJUSTMENT`

规则：

- 只有 `REDUCE` / `CLOSE` / `OPTION_EXERCISE` / `OPTION_ASSIGNMENT` / `OPTION_EXPIRY` 等会确认 realized PnL
- `DIVIDEND` 进入 ledger，不直接改变 position quantity
- `STOCK_SPLIT` 改 quantity 与 unit cost，不直接产生 realized PnL

### 4.5 成本法与盈亏口径

V1 明确支持：

- 默认成本法：`FIFO`
- 预留：`AVERAGE_COST`
- V1 不启用 `LIFO`

规则：

- 成本法按账户或税务区域可配置，但单条 `TradingPosition` 一旦建立，不允许中途切换
- `realized_pnl_gross = close proceeds - matched cost basis`
- `realized_pnl_net = realized_pnl_gross - allocated fees - taxes(if modeled)`
- `unrealized_pnl` 不落入 `core` 真相表，属于 `derived`
- 所有展示层必须显式区分 gross / net

### 4.6 多币种与 FX 规则

系统区分：

- `instrument_quote_currency`
- `account_base_currency`
- `user_display_currency`

规则：

- 真相层保留原币种金额
- 如有换算，必须保留换算汇率和换算时间基准
- `account_ledger_entries` 与 `position_events` 的金额都允许保留原币 + account_ccy 对应值
- 用户切换显示币种时只影响展示和 derived 层，不反写 core

### 4.7 公司行为规则

V1 明确支持：

- `stock_split`
- `cash_dividend`
- `symbol_change`
- `delisting`

V1 仅记录但不深度自动化支持：

- spin-off
- merger with stock consideration
- rights issue

规则：

- 公司行为作为 reference/market 输入，作用到 core 时必须产生可审计事件或批量修正 run
- 不能静默修改用户历史事件

### 4.8 股票期权边界（进一步写死）

V1 支持：

- 股票期权工具识别与录入
- 期权开平仓
- 行权 / 指派 / 到期事件
- 已实现盈亏
- 依据 underlying 现价进行内在价值估算

V1 不支持：

- 期权实时行情
- 期权 Greeks
- 期权历史 K 线
- 期权 MAE/MFE
- 组合保证金风险引擎

---

## 5. 资产、工具、标识模型（补齐）

### 5.1 三层模型必须严格区分

#### `reference.asset_master`
表示经济实体 / underlying / 上市资产主体。

示例：

- `NASDAQ:AAPL`
- `HKEX:9988`
- `SZSE:159919`
- `CRYPTO:BTCUSDT`

#### `reference.trade_instruments`
表示用户可实际交易的工具实例。

示例：

- `AAPL Spot`
- `AAPL 2026-06-19 200C`

#### `market.provider_symbol_mappings`
表示 provider 侧 symbol、market code、coverage、路由映射。

### 5.2 参考表补齐建议

#### `reference.asset_master`

- `id`
- `canonical_code`
- `display_symbol`
- `name`
- `asset_type`
- `listing_exchange_id`
- `quote_currency`
- `country_code`
- `status`
- `sector`
- `industry`
- `metadata_json`

#### `reference.trade_instruments`

- `id`
- `asset_id`
- `instrument_type` (`SPOT`, `EQUITY_OPTION`)
- `display_name`
- `contract_symbol`
- `option_type`
- `strike_price`
- `expiration_date`
- `multiplier`
- `settlement_type`
- `status`

#### `market.provider_symbol_mappings`

- `id`
- `asset_id`
- `provider_key`
- `provider_symbol`
- `provider_market`
- `capabilities_json`
- `quality_status`
- `first_seen_at`
- `last_verified_at`

---

## 6. 数据域表策略（补齐版）

### 6.1 `core`

- `users`
- `user_preferences`
- `user_credentials`
- `user_sessions`
- `user_identities`
- `auth_tokens`
- `platform_settings`
- `integration_credentials`
- `feature_flags`
- `trading_accounts`
- `broker_connections`
- `external_accounts`
- `account_sync_profiles`
- `external_trade_mappings`
- `trading_positions`
- `position_events`
- `account_ledger_entries`
- `trading_strategies`
- `strategy_checklists`
- `trading_day_reviews`
- `daily_notes`

### 6.2 `reference`

- `asset_master`
- `trade_instruments`
- `asset_aliases`
- `exchanges`
- `currencies`
- `asset_classifications`
- `market_calendars`

### 6.3 `market`

- `provider_symbol_mappings`
- `quote_snapshots`
- `price_bars_daily`
- `price_bars_intraday`
- `market_data_coverage`
- `market_fetch_jobs`
- `market_source_status`

### 6.4 `derived`

- `portfolio_snapshots`
- `dashboard_cache`
- `chart_materializations`
- `risk_views`
- `analysis_results`
- `position_metrics`
- `asset_performance_rollups`

### 6.5 `audit`

- `audit_logs`
- `admin_actions`
- `auth_events`
- `job_definitions`
- `job_runs`
- `job_run_events`
- `idempotency_keys`
- `outbox_events`
- `release_events`
- `migration_events`

### 6.6 `content`

- `content_sources`
- `content_documents`
- `content_document_assets`
- `content_ingestion_jobs`
- `content_extractions`
- `content_summaries`
- `content_symbol_links`

### 6.7 `ai`

- `ai_providers`
- `prompt_templates`
- `prompt_template_versions`
- `insight_runs`
- `insight_artifacts`
- `ai_usage_records`
- `ai_cache_entries`
- `ai_workflow_definitions`

---

## 7. 异步一致性与任务系统（重点补齐）

### 7.1 Transactional Outbox

所有以下操作，在提交数据库事务时必须同时写入 `audit.outbox_events`：

- position / ledger 变更后触发 dashboard refresh
- 新资产进入系统后触发 market warmup
- IBKR 同步写入后触发 reconcile / refresh
- AI 分析请求入队
- 内容采集后触发 extraction / summarization

#### `audit.outbox_events`
建议字段：

- `id`
- `event_type`
- `aggregate_type`
- `aggregate_id`
- `tenant_user_id`
- `payload_json`
- `idempotency_key`
- `status` (`PENDING`, `DISPATCHED`, `FAILED`, `DEAD`)
- `available_at`
- `dispatched_at`
- `failure_count`
- `last_error`
- `created_at`

### 7.2 统一任务模型

统一采用：

- `audit.job_definitions`
- `audit.job_runs`
- `audit.job_run_events`

废弃或不再新增：

- `job_executions` 这类重复命名

### 7.3 任务幂等与并发控制

必须落地以下约束：

- 同一 `asset_id + timeframe + range` 的 market backfill 不能并发
- 同一 `broker_connection_id` 的 sync 不能并发
- 同一 `content_source_id` 的 ingestion 不能并发
- 同一 `user_id + analysis_type + scope + input_hash` 的 AI run 不能并发

### 7.4 Retry / Dead-letter 规则

- `interactive jobs`：少量快速重试，失败后立即可见
- `scheduled jobs`：指数退避
- `pipeline jobs`：分步骤记录 stage
- 连续失败达到阈值后进入 `DEAD`，后台可人工 replay

---

## 8. 图表与 analytics（补齐）

### 8.1 Chart Schema 必须版本化

统一外壳保留原 spec，但新增：

- `coverage`
- `freshness`
- `generated_at`
- `source_refs`
- `warnings`

### 8.2 Chart Registry 补齐注册约束

每张图至少注册：

- `chart_id`
- `chart_type`
- `schema_version`
- `domain_scope`
- `entity_scope`
- `input_contract`
- `permission_scope`
- `analytics_builder_key`
- `renderer_key`
- `cache_policy`
- `freshness_sla`

### 8.3 Analytics 输出边界

下列结果属于 `derived`：

- equity curve
- rolling drawdown
- MAE/MFE
- emotion vs pnl
- checklist effect analysis
- strategy health rollup
- sankey materialization

规则：

- 任何复杂结果都不能让 router 直接拼图表库结构
- API 只输出 domain response 或 chart schema
- 前端 renderer 再转成 ECharts option

---

## 9. AI 中台（补齐）

### 9.1 AI 数据域独立

AI 相关表统一进入 `ai` schema，不混放 `derived` 或 `audit`。

### 9.2 AI run 生命周期

- `QUEUED`
- `PREPARING_CONTEXT`
- `RUNNING`
- `POST_PROCESSING`
- `COMPLETED`
- `FAILED`
- `CANCELLED`
- `EXPIRED`

### 9.3 输出契约

所有 AI workflow 必须定义：

- `workflow_key`
- `input_schema_version`
- `prompt_template_version`
- `output_schema_version`
- `post_processor_key`
- `cache_policy`
- `visibility_scope`

### 9.4 AI 审计与计量

必须记录：

- 谁触发了 run
- 使用了哪个 provider/model
- 使用了哪个 prompt version
- token / cost / latency
- 是否命中缓存
- 结果是否过期

### 9.5 AI 与用户隐私边界

- 禁止跨用户复用私有结果缓存
- 禁止把其他用户真实数据作为 few-shot 示例
- prompt preview / test run 默认使用脱敏或示例数据

---

## 10. 认证、安全与平台治理（补齐）

### 10.1 用户与认证模型

保留 `core.users`，新增：

- `core.user_credentials`
- `core.user_sessions`
- `core.user_identities`
- `core.auth_tokens`

### 10.2 `core.users` 最小补齐字段

- `id` bigint
- `public_id` uuid
- `email`
- `email_normalized`
- `status`
- `locale`
- `timezone`
- `last_login_at`
- `created_at`
- `updated_at`

### 10.3 安全事件审计

`audit.auth_events` 至少记录：

- register
- login success/fail
- logout
- password reset requested/completed
- email verify requested/completed
- suspicious session revoked

### 10.4 平台配置与密钥治理

#### `core.platform_settings`
仅存放非敏感且可运营配置。

#### `core.integration_credentials`
单独建模，密文存储，后台仅掩码显示。

建议分层：

- environment config
- platform settings
- integration credentials
- user preferences

### 10.5 Feature flags

建议单表：

- `core.feature_flags`

至少支持：

- global on/off
- actor targeting
- percentage rollout
- expires_at
- audit trail

---

## 11. 可观测性与错误模型（补齐）

### 11.1 结构化日志必须进入 Phase 1

统一字段建议：

- `timestamp`
- `level`
- `service`
- `module`
- `event`
- `request_id`
- `user_id`
- `job_run_id`
- `provider_key`
- `error_code`
- `latency_ms`
- `payload_size`

### 11.2 统一错误码分层

- `auth.*`
- `trading.*`
- `market.*`
- `analytics.*`
- `ai.*`
- `content.*`
- `platform.*`

示例：

- `market.unsupported_instrument`
- `market.coverage_not_ready`
- `trading.invalid_position_transition`
- `ai.provider_unavailable`
- `platform.rate_limited`

### 11.3 数据新鲜度信号

关键对象都应带 freshness：

- quote
- asset profile
- chart materialization
- AI insight
- content summary

---

## 12. API 与契约规则（补齐）

### 12.1 API versioning

继续统一：

- `/api/v1/...`

并额外明确：

- REST version
- chart schema version
- AI output schema version
- import template version

### 12.2 对外 ID 策略

- 内部 join 优先 bigint
- 对外 API 默认使用 `public_id`
- 管理后台可显示内部 id，但普通用户接口不暴露内部自增 id

### 12.3 幂等接口

以下写接口必须支持 idempotency key：

- create/edit position event
- import positions
- trigger AI analysis
- trigger manual sync
- upload content document

---

## 13. Derived 刷新矩阵（补齐）

| 结果 | 触发条件 | 延迟容忍 | 写入位置 |
|------|----------|----------|----------|
| `portfolio_snapshots` | 每日定时 + 手动重建 | `T+1` | `derived` |
| `dashboard_cache` | position/ledger 事件后 outbox 触发 | `< 5 min` | `derived` |
| `chart_materializations` | 按需生成 + TTL 缓存 | `< 10 min` | `derived` |
| `position_metrics` | position 事件变化后 | `< 5 min` | `derived` |
| `analysis_results` | analytics job 完成 | 任务级 | `derived` |
| `insight_artifacts` | AI run 完成 | 任务级 | `ai` |
| `risk_views` | 定时 + 关键事件后 | `< 15 min` | `derived` |

---

## 14. 迁移纪律（进一步写死）

### 14.1 禁止事项

- 禁止线上依赖 `create_all()` 演进 schema
- 禁止手写不可追踪 SQL 脚本替代正式迁移链
- 禁止跨多个 feature 分支同时改同一批核心表而无迁移序列治理

### 14.2 必须执行

- 单一 Alembic env + include_schemas
- 每次迁移必须标记影响域
- 核心表 rename/拆分必须有 expand -> backfill -> switch -> contract 方案
- 发布流水必须显式区分：app deploy / migration / rollback

---

## 15. 测试基线（补齐）

### 15.1 后端最小必测

- cost basis / realized pnl
- position lifecycle transitions
- ledger reconciliation
- IBKR exec idempotency
- market symbol resolution
- chart schema validation
- AI output schema validation

### 15.2 集成测试最小集

- login/register/session revoke
- create position -> outbox -> job -> derived refresh
- import trade file -> idempotent replay
- bootstrap market asset -> warmup workflow
- AI weekly report happy path / provider failure path

### 15.3 迁移测试

- 空库升级到最新
- 当前生产快照升级到最新
- downgrade only for supported windows

---

## 16. 本版明确新增的关键决策

1. 新增 `ai` schema，AI 运行数据不再混放其他域
2. 统一 job 模型为 `job_definitions / job_runs / job_run_events`
3. 增加 `outbox_events`，补齐事务外一致性
4. 明确 `AssetMaster / TradeInstrument / provider_symbol_mapping` 三层分离
5. 明确 PositionEvent 事件类型集合与 realized/unrealized PnL 归属
6. 明确多币种与 FX 保留规则
7. 明确公司行为必须通过可审计事件或修正 run 生效
8. 在交易日志中补齐 thesis / invalidation / checklist snapshot 等“决策质量”字段
9. 明确对外 API 以 `public_id` 为默认标识
10. 将结构化日志、错误码、数据新鲜度信号提升到 Phase 1

---

## 17. 进入 implementation planning 前的冻结项

在进入 implementation planning 之前，以下内容建议视为**架构冻结**：

- 单体部署形态不变
- PostgreSQL + Redis + worker 形态不变
- 七域 schema 方案冻结
- TradingPosition / PositionEvent / AccountLedgerEntry 命名冻结
- AssetMaster / TradeInstrument / provider_symbol_mapping 三层模型冻结
- FIFO 为 V1 默认成本法冻结
- transactional outbox 为必选项冻结
- chart schema-first 方案冻结
- AI prompt 由平台维护、普通用户不自定义冻结

而以下内容可以留到 implementation planning 再落细：

- worker 具体库选型
- 凭据加密具体实现
- chart schema JSON 格式细节
- AI provider 初始白名单
- 具体 migration rollout 顺序
