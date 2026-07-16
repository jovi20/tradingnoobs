# 周报 PDF 导出历史 Runbook（DISABLED）

原记录时间：2026-06-11

Release boundary 更新：2026-07-17

> `PDF_EXPORT` 和其依赖的 `AI_INSIGHTS` 当前均不属于 JOURNAL Beta 可用面。本文件只保留 P14 代码与测试的历史证据，不是当前用户操作、可用 API 或部署配置说明。相关路由、按钮和 producer 必须保持不可达，直到后续任务重新评审并同时通过 deployment ceiling 与 runtime rollout。

以下内容记录 P14 当时实现的周报 PDF 代码路径、验证方式和限制。保留这些信息不表示当前 Beta 已开放 PDF 下载。

---

## 历史代码接口（当前不可用）

P14 当时保留的后端路径如下；JOURNAL Beta 不应注册或调用它：

```http
GET /api/insights/{report_id}/export/pdf
```

若未来重新启用，需要重新验证以下历史合同：

- 必须登录，且只能导出当前用户自己的周报。
- 缺失或跨用户 report 都返回 `404`，错误响应继续走统一 error envelope。
- 成功响应 `Content-Type` 为 `application/pdf`。
- 成功响应包含 `Content-Disposition: attachment; filename=tradingnoobs-weekly-report-YYYY-MM-DD.pdf`。
- 成功响应暴露 `Access-Control-Expose-Headers: Content-Disposition`，前端可读取文件名。
- PDF 字节以 `%PDF-` 开头。

历史前端代码入口（当前必须隐藏或不可达）：

- 页面：Insights / 周报历史。
- 操作：每一份周报卡片右侧提供 `PDF` 导出按钮。
- 下载文件名优先使用响应 `Content-Disposition`，缺失时 fallback 为 `tradingnoobs-weekly-report-{reportId}.pdf`。

---

## 历史 PDF V1 内容

P14 代码使用 `WeeklyReport` 作为锚点，并包含：

- 报告周期。
- 生成时间戳。
- 交易回顾 `trades_summary`。
- 芒格视角 `munger_evaluation`。
- 改进建议 `suggestions`。
- 轻量组合摘要：总持仓数、打开/关闭持仓数、已实现 PnL。
- P13 风险摘要：风险状态、风险提醒和来源信息。
- Evidence footer：`weekly_reports:{id}`、`users:{id}`、portfolio/risk source refs。

---

## 历史实现依赖

P14 V1 使用 `reportlab>=4.2.0`，已记录在 `backend/requirements.txt`。

选择原因：

- Python 内部直接生成 PDF，不依赖系统级 HTML-to-PDF 包。
- 本地测试和服务端部署路径更可控。
- 输出可通过字节头、报告周期和 evidence footer 做稳定回归测试。

---

## Deferred 代码验证

这些命令只验证保留代码没有腐化，不构成 JOURNAL Beta enablement 或 release approval。

后端目标测试：

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_report_export_service.py
../.venv313/bin/python -m unittest discover -s tests -p test_insights_report_export.py
../.venv313/bin/python -m unittest discover -s tests -p test_openapi_contracts.py
```

前端目标测试：

```bash
cd frontend
node --experimental-strip-types --test tests/insights-report-export.test.mts
./node_modules/.bin/tsc --noEmit --pretty false
npm run lint
```

P14 完成门：

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests
cd ../frontend
./node_modules/.bin/tsc --noEmit --pretty false
npm run lint
node --experimental-strip-types --test tests/*.test.mts
cd ..
git diff --check
git status --short --branch
```

---

## 历史已知限制

- 暂不支持自定义 PDF 主题。
- 暂不嵌入图表图片；图表截图应等 P18 renderer migration 稳定后再设计。
- 暂不附加券商 statement 或原始成交单。
- 暂不支持邮件发送、定时生成或批量导出。
- PDF V1 的中文内容会以安全文本方式输出；更完整的 CJK 字体嵌入可作为后续排版专项处理。
