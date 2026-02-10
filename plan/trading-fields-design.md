# 交易员持仓管理系统 - 开发者字段设计表

本文档提供交易员账户持仓管理系统的数据库字段设计参考，包括字段名、数据类型、示例值、更新频率、数据源等技术细节。

---

## 1. 账户主表（Account Table）

| 字段名 | 数据类型 | 说明 | 示例值 | 更新频率 | 计算依赖 | 备注 |
|--------|---------|------|--------|---------|---------|------|
| account_id | VARCHAR(50) | 账户唯一标识 | "ACC_001" | - | - | 主键 |
| account_name | VARCHAR(100) | 账户名称 | "张三-主账户" | - | - | - |
| equity | DECIMAL(18,2) | 账户权益（净值） | 100000.00 | 实时 | initial_balance + realized_pnl + unrealized_pnl | 含浮动盈亏 |
| balance | DECIMAL(18,2) | 账户余额（现金） | 98500.00 | T+1 | equity - unrealized_pnl | 已结算现金 |
| margin_used | DECIMAL(18,2) | 已用保证金 | 15000.00 | 实时 | 由持仓表汇总 | - |
| margin_available | DECIMAL(18,2) | 可用保证金 | 85000.00 | 实时 | equity - margin_used | - |
| margin_level_pct | DECIMAL(8,4) | 保证金水平(%) | 666.6667 | 实时 | (equity / margin_used) * 100 | 低于200%预警 |
| unrealized_pnl | DECIMAL(18,2) | 未实现盈亏 | 1500.00 | 实时 | 由持仓表汇总 | - |
| realized_pnl_today | DECIMAL(18,2) | 今日已实现盈亏 | 500.00 | 按交易更新 | 由平仓记录汇总 | - |
| realized_pnl_ytd | DECIMAL(18,2) | 年初至今盈亏 | 8500.00 | 按交易更新 | 累计已平仓盈亏 | - |
| commission_ytd | DECIMAL(18,2) | 年初至今总佣金 | 150.00 | 按交易更新 | 累计佣金 | - |
| swap_ytd | DECIMAL(18,2) | 年初至今利息费用 | -80.00 | 每日 | 累计隔夜利息 | 可为正或负 |
| updated_at | TIMESTAMP | 最后更新时间 | 2026-02-09 14:35:22 | 实时 | - | - |

---

## 2. 持仓明细表（Position Table）

| 字段名 | 数据类型 | 说明 | 示例值 | 更新频率 | 计算依赖 | 备注 |
|--------|---------|------|--------|---------|---------|------|
| position_id | VARCHAR(50) | 持仓唯一标识 | "POS_20260209_001" | - | - | 主键 |
| account_id | VARCHAR(50) | 所属账户 | "ACC_001" | - | - | 外键 |
| symbol | VARCHAR(20) | 交易标的代码 | "AAPL", "EURUSD" | - | - | - |
| symbol_name | VARCHAR(100) | 标的名称 | "苹果公司", "欧元兑美元" | - | - | - |
| side | VARCHAR(10) | 方向 | "LONG", "SHORT" | - | - | 多头/空头 |
| quantity | DECIMAL(18,6) | 数量（手数/股） | 100.000000 | 按交易更新 | - | - |
| entry_price | DECIMAL(18,6) | 平均开仓价 | 175.250000 | 按交易更新 | 加权平均 | - |
| current_price | DECIMAL(18,6) | 当前市场价 | 178.500000 | 实时（秒级） | 行情数据源 | - |
| stop_loss_price | DECIMAL(18,6) | 止损价 | 173.000000 | 按需修改 | - | NULL表示未设置 |
| take_profit_price | DECIMAL(18,6) | 止盈价 | 180.000000 | 按需修改 | - | NULL表示未设置 |
| contract_multiplier | DECIMAL(10,2) | 合约乘数 | 1.00 | - | - | 股票=1，期货根据合约 |
| margin_required | DECIMAL(18,2) | 占用保证金 | 3500.00 | 实时 | 根据杠杆和市值 | - |
| unrealized_pnl | DECIMAL(18,2) | 未实现盈亏 | 325.00 | 实时 | (current_price - entry_price) * quantity * side_multiplier | side_multiplier: 多=+1, 空=-1 |
| unrealized_pnl_pct | DECIMAL(8,4) | 盈亏百分比(%) | 1.8571 | 实时 | (unrealized_pnl / (entry_price * quantity)) * 100 | - |
| risk_amount | DECIMAL(18,2) | 单笔风险金额 | 225.00 | 实时 | abs(entry_price - stop_loss_price) * quantity | - |
| risk_pct | DECIMAL(8,4) | 风险占权益(%) | 0.2250 | 实时 | (risk_amount / account_equity) * 100 | - |
| commission | DECIMAL(18,2) | 手续费 | 2.50 | 开仓时 | - | - |
| swap_accumulated | DECIMAL(18,2) | 累计利息 | -1.20 | 每日 | 隔夜持仓利息 | - |
| open_time | TIMESTAMP | 开仓时间 | 2026-02-05 09:30:00 | - | - | - |
| holding_hours | DECIMAL(10,2) | 持仓时长（小时） | 101.08 | 实时 | (current_time - open_time) / 3600 | - |
| strategy_tag | VARCHAR(50) | 策略标签 | "趋势跟踪", "均值回归" | - | - | 可选，用于分组统计 |
| updated_at | TIMESTAMP | 最后更新时间 | 2026-02-09 14:35:22 | 实时 | - | - |

---

## 3. 历史交易表（Trade History Table）

| 字段名 | 数据类型 | 说明 | 示例值 | 更新频率 | 计算依赖 | 备注 |
|--------|---------|------|--------|---------|---------|------|
| trade_id | VARCHAR(50) | 交易唯一标识 | "TRD_20260209_005" | - | - | 主键 |
| account_id | VARCHAR(50) | 所属账户 | "ACC_001" | - | - | 外键 |
| symbol | VARCHAR(20) | 交易标的 | "TSLA" | - | - | - |
| side | VARCHAR(10) | 方向 | "LONG", "SHORT" | - | - | - |
| action | VARCHAR(10) | 动作 | "OPEN", "CLOSE" | - | - | 开仓/平仓 |
| quantity | DECIMAL(18,6) | 数量 | 50.000000 | - | - | - |
| price | DECIMAL(18,6) | 成交价 | 245.800000 | - | - | - |
| entry_price | DECIMAL(18,6) | 对应开仓价 | 240.500000 | - | - | 仅平仓记录需要 |
| realized_pnl | DECIMAL(18,2) | 已实现盈亏 | 265.00 | - | (price - entry_price) * quantity * side_multiplier | 仅平仓记录 |
| commission | DECIMAL(18,2) | 手续费 | 2.50 | - | - | - |
| swap | DECIMAL(18,2) | 利息费用 | -0.80 | - | - | 仅平仓记录 |
| net_pnl | DECIMAL(18,2) | 净盈亏 | 261.70 | - | realized_pnl - commission - abs(swap) | 仅平仓记录 |
| holding_hours | DECIMAL(10,2) | 持仓时长（小时） | 72.50 | - | close_time - open_time | 仅平仓记录 |
| open_time | TIMESTAMP | 开仓时间 | 2026-02-06 10:00:00 | - | - | - |
| close_time | TIMESTAMP | 平仓时间 | 2026-02-09 10:30:00 | - | - | 仅平仓记录 |
| strategy_tag | VARCHAR(50) | 策略标签 | "突破交易" | - | - | - |
| created_at | TIMESTAMP | 记录创建时间 | 2026-02-09 10:30:05 | - | - | - |

---

## 4. 账户风险指标表（Account Risk Metrics Table）

| 字段名 | 数据类型 | 说明 | 示例值 | 更新频率 | 计算依赖 | 备注 |
|--------|---------|------|--------|---------|---------|------|
| metric_id | BIGINT | 记录ID | 123456 | - | - | 主键，自增 |
| account_id | VARCHAR(50) | 账户ID | "ACC_001" | - | - | 外键 |
| snapshot_time | TIMESTAMP | 快照时间 | 2026-02-09 14:30:00 | 每小时或每日 | - | - |
| total_positions | INT | 总持仓数 | 8 | 快照时 | COUNT(position_id) | - |
| portfolio_risk_amount | DECIMAL(18,2) | 组合风险金额 | 2500.00 | 快照时 | SUM(risk_amount) | - |
| portfolio_risk_pct | DECIMAL(8,4) | 组合风险占比(%) | 2.5000 | 快照时 | (portfolio_risk_amount / equity) * 100 | - |
| net_exposure | DECIMAL(18,2) | 净敞口金额 | 15000.00 | 快照时 | SUM(side * current_price * quantity) | - |
| net_exposure_pct | DECIMAL(8,4) | 净敞口占比(%) | 15.0000 | 快照时 | (net_exposure / equity) * 100 | - |
| max_drawdown_pct | DECIMAL(8,4) | 最大回撤(%) | -5.2500 | 每日 | 基于equity历史序列 | 负值 |
| var_95_1d | DECIMAL(18,2) | 1日VaR(95%) | 1200.00 | 每日 | 历史模拟法 | - |
| sharpe_ratio_ytd | DECIMAL(8,4) | 年初至今夏普比率 | 1.2500 | 每日 | 收益率序列计算 | - |
| win_rate_ytd | DECIMAL(8,4) | 年初至今胜率(%) | 55.5000 | 按交易更新 | wins / total_trades | - |
| avg_rr_ratio_ytd | DECIMAL(8,4) | 年初至今平均风险回报比 | 2.1500 | 按交易更新 | avg_win / avg_loss | - |
| profit_factor_ytd | DECIMAL(8,4) | 年初至今利润因子 | 1.8500 | 按交易更新 | total_wins / total_losses | - |
| commission_to_profit_ytd | DECIMAL(8,4) | 佣金占盈利比(%) | 1.7647 | 按交易更新 | (commission_ytd / realized_pnl_ytd) * 100 | - |

---

## 5. 持仓相关性矩阵表（Position Correlation Table）

| 字段名 | 数据类型 | 说明 | 示例值 | 更新频率 | 计算依赖 | 备注 |
|--------|---------|------|--------|---------|---------|------|
| correlation_id | BIGINT | 记录ID | 789 | - | - | 主键，自增 |
| account_id | VARCHAR(50) | 账户ID | "ACC_001" | - | - | 外键 |
| symbol_a | VARCHAR(20) | 标的A | "AAPL" | - | - | - |
| symbol_b | VARCHAR(20) | 标的B | "MSFT" | - | - | - |
| correlation_coef | DECIMAL(8,6) | 相关系数 | 0.725000 | 每日 | 过去N日收益率皮尔逊相关 | -1到+1 |
| lookback_days | INT | 回溯天数 | 60 | - | - | 计算相关性的数据窗口 |
| calculated_at | TIMESTAMP | 计算时间 | 2026-02-09 00:05:00 | 每日 | - | - |

---

## 6. 行情快照表（Market Data Snapshot）

| 字段名 | 数据类型 | 说明 | 示例值 | 更新频率 | 数据源 | 备注 |
|--------|---------|------|--------|---------|--------|------|
| snapshot_id | BIGINT | 快照ID | 456789 | - | - | 主键，自增 |
| symbol | VARCHAR(20) | 标的代码 | "AAPL" | - | - | - |
| bid_price | DECIMAL(18,6) | 买一价 | 178.450000 | 实时（秒级） | 行情接口 | - |
| ask_price | DECIMAL(18,6) | 卖一价 | 178.500000 | 实时（秒级） | 行情接口 | - |
| last_price | DECIMAL(18,6) | 最新成交价 | 178.480000 | 实时（秒级） | 行情接口 | - |
| volume | BIGINT | 成交量 | 12345678 | 实时 | 行情接口 | - |
| timestamp | TIMESTAMP | 行情时间 | 2026-02-09 14:35:20 | 实时 | 行情接口 | - |

---

## 7. 预警配置表（Alert Config Table）

| 字段名 | 数据类型 | 说明 | 示例值 | 更新频率 | 备注 |
|--------|---------|------|--------|---------|------|
| alert_id | BIGINT | 预警ID | 1 | - | 主键，自增 |
| account_id | VARCHAR(50) | 账户ID | "ACC_001" | - | 外键 |
| metric_name | VARCHAR(50) | 指标名称 | "portfolio_risk_pct" | - | 对应风险指标字段 |
| threshold_value | DECIMAL(18,6) | 阈值 | 8.0000 | 可配置 | - |
| comparison_operator | VARCHAR(10) | 比较运算符 | ">", "<", ">=", "<=" | - | - |
| alert_level | VARCHAR(20) | 预警级别 | "WARNING", "CRITICAL" | - | - |
| notification_method | VARCHAR(50) | 通知方式 | "EMAIL", "SMS", "WEBHOOK" | - | 可多选，逗号分隔 |
| is_active | BOOLEAN | 是否启用 | TRUE | 可配置 | - |
| created_at | TIMESTAMP | 创建时间 | 2026-01-01 08:00:00 | - | - |

---

## 8. 预警触发记录表（Alert Log Table）

| 字段名 | 数据类型 | 说明 | 示例值 | 更新频率 | 备注 |
|--------|---------|------|--------|---------|------|
| log_id | BIGINT | 日志ID | 9876 | - | 主键，自增 |
| alert_id | BIGINT | 预警配置ID | 1 | - | 外键 |
| account_id | VARCHAR(50) | 账户ID | "ACC_001" | - | 外键 |
| metric_name | VARCHAR(50) | 触发指标 | "portfolio_risk_pct" | - | - |
| current_value | DECIMAL(18,6) | 当前值 | 8.5000 | 触发时 | - |
| threshold_value | DECIMAL(18,6) | 阈值 | 8.0000 | 触发时 | - |
| alert_level | VARCHAR(20) | 预警级别 | "WARNING" | 触发时 | - |
| message | TEXT | 预警消息 | "组合风险超过8%阈值" | 触发时 | - |
| notified | BOOLEAN | 是否已通知 | TRUE | - | - |
| triggered_at | TIMESTAMP | 触发时间 | 2026-02-09 14:35:25 | 触发时 | - |

---

## 技术实施建议

### 数据库选型
- **关系型数据库**（PostgreSQL / MySQL）：适用于账户、持仓、交易历史等结构化数据
- **时序数据库**（InfluxDB / TimescaleDB）：适用于行情快照、风险指标时间序列
- **缓存层**（Redis）：存储实时行情、账户快照，减少数据库压力

### 索引设计
```sql
-- 账户表
CREATE INDEX idx_account_updated ON account(updated_at);

-- 持仓表
CREATE INDEX idx_position_account ON position(account_id);
CREATE INDEX idx_position_symbol ON position(symbol);
CREATE INDEX idx_position_side ON position(side);
CREATE INDEX idx_position_open_time ON position(open_time);

-- 历史交易表
CREATE INDEX idx_trade_account_time ON trade_history(account_id, close_time);
CREATE INDEX idx_trade_symbol ON trade_history(symbol);
CREATE INDEX idx_trade_strategy ON trade_history(strategy_tag);

-- 风险指标表
CREATE INDEX idx_risk_account_time ON account_risk_metrics(account_id, snapshot_time);
```

### API 响应示例（JSON格式）

**获取账户概览 API：GET /api/v1/account/{account_id}/overview**
```json
{
  "account_id": "ACC_001",
  "equity": 100000.00,
  "margin_level_pct": 666.67,
  "unrealized_pnl": 1500.00,
  "realized_pnl_ytd": 8500.00,
  "portfolio_risk_pct": 2.50,
  "positions_count": 8,
  "alerts": [
    {
      "level": "WARNING",
      "message": "持仓AAPL无止损设置",
      "timestamp": "2026-02-09T14:35:22Z"
    }
  ],
  "updated_at": "2026-02-09T14:35:22Z"
}
```

**获取持仓列表 API：GET /api/v1/account/{account_id}/positions**
```json
{
  "positions": [
    {
      "position_id": "POS_20260209_001",
      "symbol": "AAPL",
      "side": "LONG",
      "quantity": 100,
      "entry_price": 175.25,
      "current_price": 178.50,
      "unrealized_pnl": 325.00,
      "unrealized_pnl_pct": 1.86,
      "risk_pct": 0.23,
      "holding_hours": 101.08
    }
  ],
  "summary": {
    "total_positions": 8,
    "total_unrealized_pnl": 1500.00,
    "portfolio_risk_pct": 2.50
  }
}
```

### 实时计算 vs 预计算
- **实时计算**：unrealized_pnl、current_price、margin_level等高频变化指标
- **预计算（定时任务）**：
  - 每小时：相关性矩阵
  - 每日收盘后：最大回撤、夏普比率、胜率等历史统计指标
  - 每周：长期趋势分析报告

### 数据保留策略
- **持仓明细**：保留至平仓，归档到历史交易表
- **行情快照**：保留60天实时数据，之后降采样为日线保留5年
- **风险指标快照**：日级数据保留3年
- **预警日志**：保留1年

---

## 扩展字段建议

根据业务需求，可扩展以下字段：

### 持仓表扩展
- `leverage`: 杠杆倍数（如外汇、期货）
- `order_id`: 关联订单ID（多笔订单合并为一个持仓时）
- `parent_strategy_id`: 父策略ID（用于策略组合管理）
- `notes`: 交易员备注

### 账户表扩展
- `risk_limit_daily`: 每日损失熔断线
- `max_positions`: 最大持仓数限制
- `allowed_symbols`: 允许交易的标的白名单（JSON）

### 新增表：每日权益曲线表
用于存储账户每日收盘权益，方便计算回撤等指标：

| 字段名 | 数据类型 | 说明 |
|--------|---------|------|
| account_id | VARCHAR(50) | 账户ID |
| date | DATE | 日期 |
| equity_eod | DECIMAL(18,2) | 收盘权益 |
| daily_return | DECIMAL(10,6) | 当日收益率 |
| cumulative_return | DECIMAL(10,6) | 累计收益率 |

该表可用于生成权益曲线图、计算历史波动率等。
