# 交易导入模板说明

原记录时间：2026-06-11

Release boundary 更新：2026-07-17

本文档说明 legacy 通用 CSV/Excel 模板代码及其字段要求。文中路径和行为是实现参考，不单独构成 JOURNAL Beta release approval；最终通用 bootstrap 仍须通过 active plan 的 `JRN-011` 与 release gate。

## Release boundary

- 本模板只描述用户本地上传的通用 CSV/Excel，不访问 Broker 网络，也不读取或保存 Broker、Market 或 LLM 凭据。
- `IBKR_FLEX_XML_V1` source-bound 本地文件 adapter 由 `JRN-013` 至 `JRN-015` 计划实现，截至 2026-07-17 尚未实现。它将使用稳定 execution identity 支持重复、重叠、增量文件和 correction replay，不使用本模板的逐行选择合同。
- 在线 Broker Sync 当前 `DISABLED / DEFERRED`。不要把本地文件导入说明理解为 IBKR Token/Query ID 配置或网络同步入口。
- AI/Insights、PDF 导出和 risk cards 当前同样关闭；导入字段不承诺触发这些 optional capability。

---

## 支持文件类型

- CSV：推荐直接使用系统下载的 `trade_import_template.csv`。
- Excel：支持 `.xls` 和 `.xlsx`。

上传时系统会先解析文件并返回预览结果。只有校验通过的行会在确认导入时写入；如果选择了部分行，只导入已选择且有效的行。

---

## 当前模板列

`GET /api/positions/import/template` 当前输出以下列名，顺序如下：

| 列名 | 是否必填 | 说明 |
|------|----------|------|
| `Time (YYYY-MM-DD HH:MM)` | 是 | 交易发生时间。导入服务会映射为 `date`，例如 `2023-01-01 10:00`。 |
| `Symbol` | 是 | 标的代码。导入时会转为大写，例如 `AAPL`。 |
| `Direction` | 是 | 方向。支持 `LONG` / `SHORT`，也兼容 `BUY` / `SELL`、`L` / `S`。 |
| `Action` | 是 | 动作。开仓/加仓使用 `OPEN`，减仓/平仓使用 `CLOSE`。也兼容 `ENTRY` / `EXIT`、`BUY` / `SELL`、`加仓` / `建仓` / `减仓` / `平仓`。 |
| `Price` | 是 | 成交价格，必须为数字且不能为负数。 |
| `Quantity` | 是 | 成交数量，必须为大于 0 的数字。 |
| `Planned Entry` | 否 | 计划入场价。无法解析为数字时会被忽略。 |
| `Planned SL` | 否 | 计划止损价。无法解析为数字时会被忽略。 |
| `Asset Type` | 否 | 资产类型说明，例如 `Stock`。当前主要作为导入附加信息。 |
| `Strategy` | 否 | 策略名称。若系统中已有同名策略，会关联到该策略；没有同名策略时不会自动创建。 |
| `Emotion` | 否 | 交易情绪记录，例如 `Neutral`、`Happy`。 |
| `Confidence` | 否 | 信心分，建议填写 `1` 到 `5` 的整数；超出范围或无法解析时会被忽略。 |
| `Reason` | 否 | 交易理由、复盘备注或执行原因。 |
| `Commission` | 否 | 手续费，必须能解析为数字；当前会随批次记录解析，后续可用于成本/PnL 细化。 |

---

## 模板示例

当前后端模板包含一行开仓示例和一行减仓/平仓示例：

| Time (YYYY-MM-DD HH:MM) | Symbol | Direction | Action | Price | Quantity | Planned Entry | Planned SL | Asset Type | Strategy | Emotion | Confidence | Reason | Commission |
|-------------------------|--------|-----------|--------|-------|----------|---------------|------------|------------|----------|---------|------------|--------|------------|
| 2023-01-01 10:00 | AAPL | LONG | OPEN | 150.00 | 100 | 148.50 | 145.00 | Stock | Strategy A | Neutral | 4 | Entry Signal | 2.0 |
| 2023-01-05 14:00 | AAPL | LONG | CLOSE | 155.00 | 50 |  |  |  | Strategy A | Happy | 5 | Target Hit | 2.0 |

---

## 必填字段校验规则

- `Time (YYYY-MM-DD HH:MM)` 必须能解析为日期时间；无法解析会返回 `Invalid Date format`。
- `Symbol` 不能为空；为空会返回 `Symbol is required`。
- `Direction` 必须能识别为 `LONG` 或 `SHORT`；无法识别会返回 `Invalid Direction (LONG/SHORT)`。
- `Action` 必须能识别为 `OPEN` 或 `CLOSE`；无法识别会返回 `Invalid Action (OPEN/CLOSE)`。
- `Price` 必须是数字，且不能小于 0；无法解析会返回 `Invalid Price`。
- `Quantity` 必须是大于 0 的数字；无法解析会返回 `Invalid Quantity`。

---

## 可选字段建议

- `Planned Entry` 和 `Planned SL` 用于记录计划价格，不建议用实际成交价替代计划价。
- `Strategy` 建议使用系统中已经存在的策略名称，这样导入后可以自动关联；不存在时系统不会自动创建策略。
- `Emotion`、`Confidence` 和 `Reason` 建议尽量填写，用于人工复盘和日志上下文；当前不承诺 AI 分析或周报生成。
- `Commission` 当前建议填写单行交易对应手续费；未来 canonical 成本口径须按 active plan 的会计合同重新验收，PDF 导出仍为 `DEFERRED`。
