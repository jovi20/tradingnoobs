# 指标算法附录

本文档只保留会直接指导实现、排查或验证的指标说明，并为每个指标标注当前状态：
- `当前已实现`
- `已部分实现`
- `未来规划`

如果文档与代码不一致，以 `backend/routers/dashboard.py`、`backend/services/metrics_service.py`、`backend/routers/positions.py` 为准。

---

## 1. 当前已实现

### 1.1 未实现盈亏（Unrealized P&L）

状态：`当前已实现`

当前用途：
- 首页看板
- 持仓列表 / 详情
- 账户净值估算

基础公式：

\[
Unrealized\ PnL = (P_{current} - P_{entry}) \times Q \times side\_multiplier
\]

其中：
- 多头 `side_multiplier = 1`
- 空头 `side_multiplier = -1`

实现说明：
- 实时价格来自 `MarketDataService`
- 聚合逻辑主要位于 Dashboard 与账户路由

### 1.2 胜率（Win Rate）

状态：`当前已实现`

基础公式：

\[
WinRate = \frac{Winning\ Trades}{Total\ Closed\ Trades}
\]

实现说明：
- Dashboard 统计已平仓结果
- AI 分析助手的分组统计也会复用胜率概念

### 1.3 日收益序列（Daily Returns）

状态：`当前已实现`

基础公式：

\[
R_t = \frac{E_t - E_{t-1}}{E_{t-1}}
\]

其中：
- \(E_t\) 为 `DailySnapshot.total_equity`

实现说明：
- `MetricsService.calculate_daily_returns`
- 作为 Sharpe / Sortino / Calmar / Max Drawdown 的前置数据

### 1.4 最大回撤（Max Drawdown）

状态：`当前已实现`

基础公式：

\[
Peak_t = \max(E_1, \dots, E_t)
\]

\[
DD_t = \frac{E_t - Peak_t}{Peak_t}
\]

\[
MaxDrawdown = \min(DD_t)
\]

实现说明：
- `MetricsService.calculate_max_drawdown`
- Dashboard 已返回 `max_drawdown`

### 1.5 夏普比率（Sharpe Ratio）

状态：`当前已实现`

基础公式：

\[
Sharpe = \frac{\bar{R} - R_f}{\sigma_R}
\]

当前实现约束：
- 当前实现使用日收益序列
- 风险自由利率简化处理
- 返回值按年化口径输出

实现入口：
- `backend/services/metrics_service.py`
- `backend/routers/dashboard.py`

### 1.6 索提诺比率（Sortino Ratio）

状态：`当前已实现`

基础公式：

\[
Sortino = \frac{\bar{R} - R_f}{\sigma_{downside}}
\]

实现说明：
- 仅使用下行波动率
- 已在 Dashboard 返回

### 1.7 Calmar Ratio

状态：`当前已实现`

基础公式：

\[
Calmar = \frac{Annualized\ Return}{MaxDrawdown}
\]

实现说明：
- 当前通过 CAGR 与 Max Drawdown 组合计算
- 已在 Dashboard 返回

### 1.8 MAE / MFE

状态：`当前已实现`

定义：
- `MAE`：持仓期间最大不利波动
- `MFE`：持仓期间最大有利波动

基础百分比公式：

\[
MAE\% = \frac{P_{min/max} - P_{entry}}{P_{entry}} \times 100
\]

\[
MFE\% = \frac{P_{max/min} - P_{entry}}{P_{entry}} \times 100
\]

说明：
- 多空方向会影响 `max_price_during_hold` 与 `min_price_during_hold` 的解释
- 当前支持持仓详情展示和 Dashboard 散点图

### 1.9 持仓时间分组绩效

状态：`当前已实现`

当前用途：
- AI 分析助手 `holding_period`

分桶逻辑：
- 日内 `<1d`
- `1-3d`
- `3-7d`
- `1-2w`
- `2w+`

分组统计输出：
- `count`
- `avg_pnl`
- `total_pnl`
- `win_rate`

---

## 2. 已部分实现

### 2.1 账户净值（NAV / Total Equity）

状态：`已部分实现`

基础公式：

\[
NAV = Cash + Market\ Value
\]

说明：
- 当前账户页会根据开放持仓和实时价格估算 `market_value` 与 `total_equity`
- 但没有独立完整的账户级风险表

### 2.2 净敞口（Net Exposure）

状态：`已部分实现`

基础公式：

\[
NetExposure = \sum s_i \times Q_i \times P_i
\]

说明：
- 当前账户与看板内部已存在市场价值和多空处理逻辑
- 但没有作为独立指标稳定暴露给前端，也没有形成快照表

### 2.3 计划止损风险百分比

状态：`已部分实现`

当前用途：
- 持仓详情中的 `drift_analysis.stop_loss_risk_pct`

基础公式：

\[
Risk\% = \frac{|P_{entry} - P_{stop}|}{P_{entry}} \times 100
\]

说明：
- 当前只服务于计划偏移分析
- 还不是统一的组合风险口径

### 2.4 佣金与费用统计

状态：`部分实现 / Import fee 未实现`

说明：
- `GENERIC_BOOTSTRAP` 尚未实现；三条 legacy Import API 当前仅返回 `404 FEATURE_DISABLED` 且不进入 OpenAPI。
- 未注册 legacy parser 代码中保留的 `commission` 解析分支只是一项 historical reference，不是当前 Import 路径，也不会产生 canonical fee 写入。
- 交易流水支持费用类 `Transaction`
- `JRN-011`/`JRN-012` 必须按单 event 聚合 fee 与 canonical accounting 合同重新实现通用 Import；系统也尚未形成统一的年度费用指标面板。

### 2.5 AI 分析助手中的策略/情绪/检查清单分组指标

状态：`已部分实现`

当前输出：
- `count`
- `avg_pnl`
- `win_rate`

说明：
- 已用于 `strategy_health`、`emotion_pnl`、`checklist_effect`
- 还没有形成更完整的稳定性指标，如 profit factor、R-multiple 分布

---

## 3. 未来规划

### 3.1 单笔风险（Risk per Trade）

状态：`未来规划`

目标公式：

\[
Risk_{money} = |P_{entry} - P_{stop}| \times Q \times M
\]

\[
Risk_{\%} = \frac{Risk_{money}}{Equity}
\]

当前缺口：
- 没有统一持久化字段
- 没有在所有持仓上稳定计算和展示

### 3.2 组合风险 / 账户热度（Portfolio Risk / Heat）

状态：`未来规划`

目标公式：

\[
PortfolioRisk = \sum Risk_{money, i}
\]

\[
PortfolioRisk\% = \frac{PortfolioRisk}{Equity}
\]

对应路线图：
- `TODO.md` Phase 3

### 3.3 VaR（Value at Risk）

状态：`未来规划`

目标思路：
- 基于历史收益分布或历史模拟法

当前缺口：
- 没有风险时间序列模型
- 没有单独风险快照持久化

### 3.4 相关性矩阵（Correlation Matrix）

状态：`未来规划`

目标公式：

\[
Corr(A, B) = \frac{Cov(A, B)}{\sigma_A \sigma_B}
\]

当前缺口：
- 没有相关性持久化表
- 没有稳定的历史价格窗口管理

### 3.5 利润因子（Profit Factor）

状态：`未来规划`

目标公式：

\[
ProfitFactor = \frac{Gross\ Profit}{|Gross\ Loss|}
\]

### 3.6 佣金占收益比

状态：`未来规划`

目标公式：

\[
CommissionToProfit = \frac{Commission}{Realized\ Profit}
\]

### 3.7 保证金相关指标

状态：`未来规划`

包括：
- `margin_used`
- `margin_available`
- `margin_level_pct`

说明：
- 当前账户模型里没有形成完整的保证金交易计算链路

---

## 4. 指标与代码映射

| 指标组 | 当前主要代码位置 |
|--------|------------------|
| 风险调整收益指标 | `backend/services/metrics_service.py` |
| Dashboard 汇总返回 | `backend/routers/dashboard.py` |
| MAE/MFE 计算与展示 | `backend/routers/positions.py` / `frontend/components/dashboard/MaeMfeScatterPlot.tsx` |
| AI 分析助手分组统计 | `backend/services/analytics_service.py` |
| 持仓计划偏移风险 | `backend/routers/positions.py` |

---

## 5. 使用规则

- 新增指标时，先确定它属于“当前已实现 / 已部分实现 / 未来规划”哪一类。
- 如果指标已经对外返回，必须在本附录中给出最小公式与代码入口。
- 如果指标只是产品设想，不要写成“当前字段”或“当前看板指标”。
