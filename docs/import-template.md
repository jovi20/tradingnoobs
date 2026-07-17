# 历史通用交易导入字段参考（DISABLED）

原记录时间：2026-06-11

Release boundary 更新：2026-07-17

`GENERIC_BOOTSTRAP` 尚未实现。本文只保存 **Historical unregistered legacy parser reference**（历史、未注册的 legacy parser 参考），用于 `JRN-011`/`JRN-012` 重新设计 owner-bound 持久会话和 canonical confirm 时核对旧字段；它不是当前用户指南、可调用接口合同或未来模板承诺。

## 当前 release boundary

- 当前只注册以下 deny-only stub：`POST /api/positions/import/upload`、`POST /api/positions/import/confirm` 和 `GET /api/positions/import/template`。三条路径均仅返回 `404 FEATURE_DISABLED`，不进入 OpenAPI，也不调用保留的 legacy handler。
- JOURNAL Beta 当前不提供通用导入模板下载、文件上传、preview 或 confirm，不会由这些路径产生任何财务写入。前端没有 Import 入口；直达 `/positions/import` 进入 framework not-found 视图，它不是当前主要页面。
- `GENERIC_BOOTSTRAP` 只有在 active plan 的 `JRN-011`/`JRN-012` 实现并通过 release gate 后才能按新合同开放；保留代码中的文件类型、字段、样例和错误字符串不能证明该能力存在。
- 历史字段参考只涉及用户本地文件，不访问 Broker 网络，也不读取或保存 Broker、Market 或 LLM 凭据。
- `IBKR_FLEX_XML_V1` source-bound 本地文件 adapter 由 `JRN-013` 至 `JRN-015` 计划实现，截至 2026-07-17 尚未实现。它将使用稳定 execution identity 支持重复、重叠、增量文件和 correction replay，不使用本模板的逐行选择合同。
- 在线 Broker Sync 当前 `DISABLED / DEFERRED`。不要把本地文件导入说明理解为 IBKR Token/Query ID 配置或网络同步入口。
- AI/Insights、PDF 导出和 risk cards 当前同样关闭；导入字段不承诺触发这些 optional capability。

---

## 历史 parser 文件分支

- 保留的未注册代码包含 CSV 解析分支，并曾使用 `trade_import_template.csv` 作为下载文件名。
- 保留的未注册代码还包含 `.xls` 和 `.xlsx` 解析分支。

这些分支没有当前可达入口，也没有 owner-bound `ImportSession`、持久 preview 或 canonical confirm 合同。用户不能从当前应用下载该历史文件、提交文件或确认其中任意行。

---

## 历史字段表

下表抄录未注册 legacy parser/template 代码中的旧列名和旧解释，仅供迁移设计核对。它不是 `GET /api/positions/import/template` 的当前响应，也不是 `GENERIC_BOOTSTRAP` 的最终 schema。

| 列名 | 是否必填 | 说明 |
|------|----------|------|
| `Time (YYYY-MM-DD HH:MM)` | 是 | 旧 parser 曾把该值映射为 `date`，例如 `2023-01-01 10:00`。 |
| `Symbol` | 是 | 旧 parser 曾把标的代码转为大写，例如 `AAPL`。 |
| `Direction` | 是 | 旧 parser 曾识别 `LONG` / `SHORT`、`BUY` / `SELL` 和 `L` / `S`。 |
| `Action` | 是 | 旧 parser 曾把 `OPEN` / `ENTRY` / `BUY` / `加仓` / `建仓` 解释为开仓或加仓，把 `CLOSE` / `EXIT` / `SELL` / `减仓` / `平仓` 解释为减仓或平仓。 |
| `Price` | 是 | 旧 parser 曾要求成交价格可解析为数字且非负。 |
| `Quantity` | 是 | 旧 parser 曾要求成交数量可解析为大于 0 的数字。 |
| `Planned Entry` | 否 | 旧 parser 曾把计划入场价视为可选数字，并忽略无法解析的值。 |
| `Planned SL` | 否 | 旧 parser 曾把计划止损价视为可选数字，并忽略无法解析的值。 |
| `Asset Type` | 否 | 旧 parser 曾把例如 `Stock` 的值当作可选附加文本，不是 canonical asset identity。 |
| `Strategy` | 否 | 旧 parser 曾尝试关联同名策略，不创建缺失策略。 |
| `Emotion` | 否 | 旧 parser 曾把例如 `Neutral`、`Happy` 的值当作可选情绪文本。 |
| `Confidence` | 否 | 旧 parser 曾接受 `1` 到 `5` 的可选整数，并忽略超出范围或无法解析的值。 |
| `Reason` | 否 | 旧 parser 曾把该值当作可选交易理由、复盘备注或执行原因。 |
| `Commission` | 否 | 旧 parser 曾尝试把可解析数字放入批次中间数据；这不构成 canonical fee 或 PnL 保证。 |

---

## 历史样例行

保留代码中曾包含一行开仓样例和一行减仓/平仓样例：

| Time (YYYY-MM-DD HH:MM) | Symbol | Direction | Action | Price | Quantity | Planned Entry | Planned SL | Asset Type | Strategy | Emotion | Confidence | Reason | Commission |
|-------------------------|--------|-----------|--------|-------|----------|---------------|------------|------------|----------|---------|------------|--------|------------|
| 2023-01-01 10:00 | AAPL | LONG | OPEN | 150.00 | 100 | 148.50 | 145.00 | Stock | Strategy A | Neutral | 4 | Entry Signal | 2.0 |
| 2023-01-05 14:00 | AAPL | LONG | CLOSE | 155.00 | 50 |  |  |  | Strategy A | Happy | 5 | Target Hit | 2.0 |

---

## 历史校验字符串

- 旧 parser 为无法解析的时间保留了 `Invalid Date format`。
- 旧 parser 为缺失标的保留了 `Symbol is required`。
- 旧 parser 为无法识别的方向保留了 `Invalid Direction (LONG/SHORT)`。
- 旧 parser 为无法识别的动作保留了 `Invalid Action (OPEN/CLOSE)`。
- 旧 parser 为非数字或负价格保留了 `Invalid Price`。
- 旧 parser 为非正数量保留了 `Invalid Quantity`。

这些字符串不能通过当前 deny-only API 触发；`JRN-011`/`JRN-012` 必须重新冻结统一错误 envelope，不能把它们直接当成新合同。

---

## 后续实现审查点

- `Planned Entry`、`Planned SL`、`Strategy`、`Emotion`、`Confidence` 和 `Reason` 是否进入新 schema，须由 `JRN-011`/`JRN-012` 结合 canonical event/narrative 合同重新决定。
- `Commission` 必须按 active plan 的单 event 聚合 fee 和 canonical accounting 合同实现，不能沿用旧批次中间数据作为财务真值。
- 新实现必须满足 owner-bound 持久会话、限额、幂等、原子 confirm 和可审计终态；在这些 gate 关闭前，本页不能恢复为用户操作说明。
