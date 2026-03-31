# 数据模型附录

本文档用于说明：
- 当前系统已经存在的主要持久化模型与关键字段
- 当前接口中存在但非持久化的计算字段
- Phase 3+ 以后可能引入的扩展表与字段

权威来源：
- 持久化模型：`backend/models.py`
- 请求响应模型：`backend/schemas.py`

如果文档与代码不一致，以代码为准，再更新本文档。

---

## 1. 当前系统已有模型

### 1.1 用户与配置

| 模型 | 当前关键字段 | 说明 |
|------|--------------|------|
| `User` | `email`, `username`, `hashed_password`, `is_active`, `created_at` | 用户主体 |
| `UserSettings` | `theme`, `up_color`, `display_currency`, `ibkr_*`, `binance_*`, `finnhub_api_key`, `llm_*` | 用户级偏好和 API 设置 |
| `SystemSetting` | `key`, `value`, `description`, `updated_at` | 管理员级全局配置，目前承担 Finnhub / LLM 等系统设置 |

说明：
- 行情主服务读取的 Finnhub Key 当前来自 `SystemSetting`
- `UserSettings` 和 `SystemSetting` 有部分字段语义相近，但层级不同

### 1.2 策略与复盘

| 模型 | 当前关键字段 | 说明 |
|------|--------------|------|
| `Strategy` | `name`, `description`, `entry_rules`, `exit_rules`, `risk_rules`, `symbols`, `status`, `checklist_items` | 策略定义，已支持检查清单 |
| `DailySummary` | `date`, `market_mood`, `personal_mood`, `summary` | 每日总结 |
| `JournalEntry` | `date`, `content` | 用户随笔，每天多条 |
| `AISummary` | `date`, `content`, `created_at` | AI 摘要结果 |
| `WeeklyReport` | `week_start`, `week_end`, `trades_summary`, `munger_evaluation`, `suggestions` | AI 周报 |
| `AIAnalysisResult` | `analysis_type`, `raw_data`, `ai_insights`, `created_at` | AI 分析助手结果持久化 |

### 1.3 账户、资金与快照

| 模型 | 当前关键字段 | 说明 |
|------|--------------|------|
| `TradingAccount` | `name`, `broker`, `account_type`, `currency`, `initial_balance`, `cash_balance`, `current_balance`, `description`, `is_active` | 交易账户主体 |
| `Transaction` | `account_id`, `type`, `amount`, `currency`, `date`, `description` | 入金、出金、费用、利息等流水 |
| `DailySnapshot` | `date`, `total_equity`, `total_assets`, `total_liabilities`, `net_transfers` | 每日资产快照，为历史收益和回撤提供基础 |

说明：
- `TradingAccount` 当前没有完整的保证金字段体系
- 账户实时 `market_value` / `total_equity` 主要在 API 层动态计算

### 1.4 持仓与交易批次

| 模型 | 当前关键字段 | 说明 |
|------|--------------|------|
| `Position` | `account_id`, `strategy_id`, `symbol`, `exchange`, `asset_type`, `direction`, `status`, `total_quantity`, `average_entry_price`, `realized_pnl`, `opened_at`, `closed_at` | 持仓聚合主表 |
| `Position` 扩展 | `trade_review`, `screenshots`, `lessons`, `rating` | 平仓后的复盘信息 |
| `Position` Phase 1 | `checklist_responses`, `checklist_completed_at`, `planned_entry_price`, `planned_stop_loss`, `planned_take_profit` | 检查清单与计划偏移 |
| `Position` Phase 2 | `max_price_during_hold`, `min_price_during_hold` | MAE/MFE 基础字段 |
| `TradeBatch` | `position_id`, `type`, `price`, `quantity`, `time`, `reason`, `emotion`, `confidence`, `pnl` | 建仓/加减仓/平仓的细粒度记录 |
| `AssetMetadata` | `symbol`, `name`, `core_type`, `market`, `currency`, `sector`, `risk_level`, `instrument` | 资产元数据补全表 |

说明：
- 当前系统中，“持仓”是聚合实体，“批次”才是实际交易动作粒度
- `planned_take_profit` 当前为 JSON，不是结构化子表
- `screenshots` 与 `lessons` 当前也采用 JSON 列

---

## 2. 当前接口中的非持久化计算字段

以下字段会在 API 响应中出现，但并不一定直接存储在数据库中：

| 字段 | 位置 | 说明 |
|------|------|------|
| `current_price` | `PositionResponse` | 实时行情填充 |
| `unrealized_pnl` | `PositionResponse` | 基于实时价格计算 |
| `drift_analysis` | `PositionResponse` | 计划价与实际执行的偏移分析 |
| `market_value` | `TradingAccountResponse` | 账户开放持仓实时市值 |
| `total_equity` | `TradingAccountResponse` | 账户实时净值 |
| `asset_allocation` / `market_allocation` 等 | `DashboardStats` | 看板聚合数据 |

这类字段的维护原则：
- 若只用于展示或实时计算，不应轻易下沉为持久化列
- 若需要历史追踪、预警或报表重算，再考虑正式持久化

---

## 3. 当前 schema 还没有的扩展设计

以下内容来自旧字段设计稿，但当前代码库尚未实现，应该视为 Phase 3+ 的目标模型，不可误写为现状。

### 3.1 账户风险指标表

建议状态：`未来扩展`

目标用途：
- 持久化组合风险、净敞口、VaR、回撤、利润因子等风险快照

建议字段：
- `account_id`
- `snapshot_time`
- `portfolio_risk_amount`
- `portfolio_risk_pct`
- `net_exposure`
- `net_exposure_pct`
- `var_95_1d`
- `profit_factor_ytd`
- `commission_to_profit_ytd`

当前缺口：
- 还没有独立风险快照表
- 相关指标主要在 Dashboard 层临时聚合

### 3.2 持仓相关性矩阵表

建议状态：`未来扩展`

目标用途：
- 保存标的之间的相关系数，支持组合集中度分析与预警

建议字段：
- `account_id`
- `symbol_a`
- `symbol_b`
- `correlation_coef`
- `lookback_days`
- `calculated_at`

当前缺口：
- 没有历史相关性计算任务
- 没有持久化矩阵模型

### 3.3 预警配置与触发日志

建议状态：`未来扩展`

目标用途：
- 支持 Phase 3 风控预警系统

建议拆分为两类表：
- `AlertConfig`
  - `account_id`
  - `metric_name`
  - `threshold_value`
  - `comparison_operator`
  - `alert_level`
  - `notification_method`
  - `is_active`
- `AlertLog`
  - `alert_id`
  - `account_id`
  - `metric_name`
  - `current_value`
  - `threshold_value`
  - `message`
  - `notified`
  - `triggered_at`

当前缺口：
- 还没有风险服务
- 还没有 WebSocket/Toast 预警链路

### 3.4 保证金与账户层扩展字段

建议状态：`未来扩展`

旧稿中提到但当前未落库的字段：
- `margin_used`
- `margin_available`
- `margin_level_pct`
- `risk_limit_daily`
- `max_positions`
- `allowed_symbols`

说明：
- 当前项目更偏交易日志与分析，而非完整券商级风控账务系统
- 如果后续进入保证金交易和账户风控，建议基于账户风险指标表一并设计

---

## 4. 推荐的扩展原则

- 先区分“实时计算字段”和“必须持久化字段”。
- 只有满足以下任一条件，才建议新增数据库列或新表：
  - 需要历史追踪
  - 需要做预警触发
  - 需要做报表重算
  - 需要跨页面复用且计算代价高
- 未来新增表时，优先沿用当前已有主键与外键关系：
  - `user_id`
  - `account_id`
  - `position_id`
  - `strategy_id`

---

## 5. 维护规则

- 本附录描述“字段边界”，不承担完整 ER 图职责。
- 当前字段改动后，优先更新 `backend/models.py`、`backend/schemas.py`，再同步本文档。
- 如果某项字段仍未落库，必须明确标记为“未来扩展”，不能混入现状表格。
