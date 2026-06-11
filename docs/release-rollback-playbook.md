# Release And Rollback Playbook

更新时间：2026-06-11
当前执行分支：`dev`

本 playbook 记录 P11-P18 后的可操作发布与回滚边界。目标不是替代测试，而是在发布窗口里快速判断“正常路径是什么、先切哪个开关、最后才回滚哪段提交”。

---

## Truth Writes

正常路径：
- 新建仓位仍经过 `POST /api/positions` 的 create-and-sync 过渡合同，并返回 `truth_position_public_id`。
- 已有仓位的加仓、减仓、平仓走 `POST /api/trading-positions/{position_public_id}/events`。
- 复盘与叙事写入走 `PATCH /api/trading-positions/{position_public_id}/events/{event_public_id}/narrative`。
- 前端普通操作不应调用 legacy batch/review 写入，除非明确处于 migration/support fallback。

迁移 fallback：
- `legacy-batch-write` 只用于 legacy batch create 迁移补录。
- `legacy-review-write` 只用于 legacy `Position.trade_review / lessons / rating` 迁移修正。

安全回滚顺序：
- 先确认 `frontend/tests/legacy-ui-boundaries.test.mts` 没有被绕过，避免新页面继续扩张 legacy DTO。
- 如用户操作被阻塞，优先临时切回迁移/support 操作入口，而不是扩大普通 legacy 写路径。
- 如必须回滚代码，按最新到最旧逐个回滚 P11 行为提交并逐步验证：`b06f231`、`715816f`、`e9fbafe`、`a7fa1da`、`5a70275`。
- 每回滚一段后至少运行 truth lifecycle、legacy bridge、frontend boundary 三组回归。

---

## Timeline Snapshot Rollback

正常模式：
- `/api/timeline/home` 默认是 `SNAPSHOT_ONLY`。
- Timeline events 与 Review Inbox 默认从 `DerivedTimelineSnapshot`、truth lifecycle、auditable insight artifacts 读取。
- UI 正常标签应显示 `Snapshot-first truth/snapshot read model`。

回滚开关：
- 启用 feature flag `timeline_legacy_mixed_feed_enabled` 可恢复 legacy mixed feed。
- 回滚后 UI 应显示 `Legacy mixed fallback enabled`，让用户和排障人员知道当前不是默认 truth/snapshot 模式。

安全回滚顺序：
- 先启用 `timeline_legacy_mixed_feed_enabled`，不要先删除 snapshot 数据或修改 derived refresh。
- 验证 `/api/timeline/home`、`/`、`/timeline` 仍能加载，并确认 Review Inbox 没有丢失关键行动卡片。
- 如果 feature flag 不能恢复，再按需回滚 `2c82e54 feat: default timeline to truth snapshots`。
- 浏览器验证需要登录态；若未登录只覆盖到 `/login`，不能视为完整 Timeline smoke。

---

## Legacy Mutation Guards

以下 header 只能用于 migration/support，不是普通产品路径：
- `legacy-batch-write`：允许 legacy batch create 迁移补录。
- `legacy-review-write`：允许 legacy review 字段迁移修正。
- `legacy-position-delete`：允许 legacy position hard delete 迁移清理。
- `legacy-batch-edit`：允许 legacy batch edit/delete 迁移修正。

默认保护：
- truth lifecycle 存在时，普通 legacy batch create、legacy review write、position hard delete、batch edit/delete 应返回 `409`。
- `DELETE /api/positions/{position_id}` 不应成为 audited truth lifecycle 的普通删除方式。
- legacy batch edit/delete 不应替代 truth event reversal、manual adjustment 或未来 compensating event UX。

安全回滚顺序：
- 先确认是否只是 migration/support 操作缺少正确 header。
- 再确认用户是否实际应走 truth route 或 narrative route。
- 只有历史数据清理确实被阻塞时，才在受控调用里使用对应 `X-Migration-Fallback` 值。
- 如必须回滚 guard，逐个回滚 `715816f`、`e9fbafe` 或 `5a70275` 的相关保护，并保留 P12 OpenAPI contract tests，避免 header 文档消失。

---

## Risk Review Features

正常路径：
- Dashboard 展示组合风险摘要与风险提醒。
- Timeline / Review Inbox 展示风险行动卡。
- P13 V1 不依赖 SSE/WebSocket，风险提醒来自现有 API/read-model。

安全回滚顺序：
- 如果风险提醒误报，优先在前端隐藏风险行动卡或降级展示，不要删除底层风险计算测试。
- 如果 Dashboard 风险栏阻塞页面加载，先回滚 UI 接入提交 `800867a` 或 `d01749f`，保留后端风险 API 以便继续排障。
- 验证 Dashboard、Timeline、risk alert adapter tests 仍通过。

---

## Reporting And PDF Export

正常路径：
- Insights 周报 PDF 通过后端 PDF renderer 生成。
- 前端导出按钮只调用既有 export API，不直接拼装 PDF。
- 导入模板说明是用户可见操作说明，不承担自动导入校验。

安全回滚顺序：
- 如果 PDF 生成失败，优先返回用户可读错误并保留页面可用性。
- 如果导出接口阻塞 Insights，先回滚前端导出按钮提交 `da80ccd`，再排查后端 renderer。
- 如必须禁用 PDF，保留导入模板文档与非 PDF Insights 功能。

---

## AI Analysis Workflow

正常路径：
- `/api/insights/analyze` 要求 `start_date` 与 `end_date` 同时提供或同时省略。
- 分析 artifact 写入 date-range refs、source refs、evidence refs。
- `/api/insights/analyze/history` 支持前端近期分析复访。

安全回滚顺序：
- 如果日期范围校验导致误拒绝，优先修正校验边界，不要绕过 P12B 标准错误 envelope。
- 如果 history 复访异常，先隐藏近期分析列表，保留 artifact detail 与 analyze endpoint。
- 如 LLM 未配置，应该显示可解释错误，不应阻塞 Insights 主页面加载。

---

## Market Data Platform

正常路径：
- Provider router 决定 A 股 / 港股 / 美股 / Crypto / 外汇 / 基金路由。
- Normalized adapters 输出统一 quote metadata。
- 前端展示 freshness/degradation 标签，而不是把 degraded 数据伪装成 fresh。

安全回滚顺序：
- 如果单个 provider 失败，优先使用 provider fallback 与 degraded metadata。
- 如果 provider routing 全局异常，回滚 `907cb07` / `377a632` 相关路由与 adapter 变更，并保留测试中已知 degraded 行为。
- 没有 API key 或外部网络失败时，不应视为代码发布失败；应记录为环境限制。

---

## Admin Operations

正常路径：
- `/api/admin/ops/backups` 提供受控备份触发。
- 管理员晋升和密码重置走 audited admin endpoint。
- Job recovery UI 对 stale / failed / force-cancel 给出解释和 typed confirmation。

安全回滚顺序：
- 如果 backup provider 未配置，预期返回 `409 BACKUP_PROVIDER_NOT_CONFIGURED`，不要把它当成 500。
- 如果用户操作风险过高，先隐藏 `/admin/ops` 前端入口，保留后端 endpoint 供受控运维调用。
- 密码重置不得记录临时密码；如发现日志泄露风险，立即回滚相关提交并轮换受影响凭据。

---

## Chart Renderer Migration

正常路径：
- 前端图表使用内部 SVG renderer。
- `chart.v1` schema、`ChartFrame`、freshness/trust 包装保持稳定。
- `recharts` 依赖已从 package files 移除，静态测试阻止 Recharts import 回流。

安全回滚顺序：
- 如果内部 SVG renderer 出现单图问题，优先修复对应 renderer 或降级为空状态，不要重新引入新的图表依赖。
- 如果必须回滚 P18，按最新到最旧回滚 `e5938b5`、`fbd5bd5`、`f7f13d7`、`438c164`、`22c675f`，并重新运行 frontend install/typecheck/lint/Node tests。
- 回滚 Recharts 依赖时必须同时恢复 package lock，不能只改 `package.json`。

---

## Verification

发布或回滚后至少运行：

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_openapi_contracts.py
../.venv313/bin/python -m unittest discover -s tests -p test_position_truth_bridge_router.py
../.venv313/bin/python -m unittest discover -s tests -p test_trading_position_lifecycle_router.py
../.venv313/bin/python -m unittest discover -s tests -p test_timeline_home_router.py
cd ../frontend
node --experimental-strip-types --test tests/legacy-ui-boundaries.test.mts tests/generated-contracts.test.mts
./node_modules/.bin/tsc --noEmit --pretty false
npm run lint
```
