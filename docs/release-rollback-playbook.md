# Release And Rollback Playbook

> **范围说明（2026-07-17）**：只有下面的 JRN-000/JRN-001 rollback addendum 属于当前收口边界；其余 P11-P18 内容是 `SUPERSEDED` 历史记录，不能作为当前交易日志 Beta 的启用或凭据配置 runbook。当前唯一 active plan 是 [2026-07-16 trading-journal plan](./superpowers/plans/2026-07-16-dev-trading-journal-development-plan.md)。

当前 addendum 更新：2026-07-17
历史正文更新时间：2026-06-11
当前执行分支：`dev`

## JRN-000/JRN-001 Current Rollback Addendum

当前状态：`JRN-000 COMPLETE`；`JRN-001 FINAL_VERIFICATION_REVIEW`。JRN-001 尚未完成，也不表示 Beta 已可发布。

- JRN-000 已固定 Alembic baseline head `9cad10111213`。JRN-001 不新增 Alembic revision，因此回退 JRN-001 不执行 schema downgrade，也不能改写 JRN-000 migration chain。
- 回退前先让 `DEPLOYMENT_CAPABILITY_ALLOWLIST` 保持为空，并保持 Broker network sync、Market、AI/Insights、PDF、risk cards 和 open registration 全部 hard-off。runtime flag 不能作为扩大 ceiling 的回退手段。
- JRN-001 的机器合同 `backend/app_config/journal_beta_v1.json`、严格 loader、ADR、frontend generator 与 `frontend/lib/generated/release-contract.ts` 必须锁步回退；不得只回退生成文件或只回退后端合同。
- 回退 JRN-011 时必须成组关闭 template、upload、session read 和 `/positions/import` UI，并恢复 confirm-only 之外的完整 deny-only boundary；不得把路由切回 legacy in-memory Import handler。正常 JRN-011 状态只开放持久 preview，confirm 继续 hard-off。
- 回退 JRN-001 不得恢复普通 `/api/positions` 路由上的 `X-Migration-Fallback` 信任式绕过，也不得恢复 `?migrationFallback=1` 前端入口。legacy review、position hard delete 与 batch create/edit/delete 在普通产品面保持 fail-closed；真正的迁移 mutation 必须等待受审计的 admin/CLI namespace，不能以客户端自报 header 代替。
- 回退 JRN-001 不得恢复 `GET /api/positions/{id}/truth-lifecycle` 的惰性 legacy backfill。缺少 truth 时读取保持 not-found 和零 flush/commit；任何 explicit sync 在写入 asset、event 或 ledger 前都必须复验 legacy Position、TradingPosition 与 TradingAccount 的 owner/account 一致性。
- capability router/secret/job/outbox 与 journal-only UI/API DTO 也必须按 scoped checkpoint 边界成组回退，避免出现 API、OpenAPI、前端和 producer 半开状态。
- 回退后至少重跑：已知 optional path 的 `404 FEATURE_DISABLED`、未知 path 普通 404、JOURNAL Beta OpenAPI 不包含 optional route/DTO、Admin 与普通 settings secret 写入拒绝、Market/optional job 不领取且零新增 job/outbox side effect，以及 frontend navigation/settings/dashboard/timeline/lifecycle hard-off smoke。
- 工作树中 deployment workflow、migration/start/backup 脚本的用户处置不属于 JRN-001 checkpoint，不能在回退记录中宣称为 JRN-001 成果或随 JRN-001 自动还原。
- `IBKR_FLEX_XML_V1` 的重复、重叠、增量确认和 correction replay 只在 JRN-013 至 JRN-015 实现；JRN-001 回退只处理冻结合同与 capability boundary，不回退尚不存在的 Import 实现。

---

## Historical P11-P18 Playbook（SUPERSEDED）

本 playbook 记录 P11-P18 后的可操作发布与回滚边界。目标不是替代测试，而是在发布窗口里快速判断“正常路径是什么、先切哪个开关、最后才回滚哪段提交”。

---

## Truth Writes

正常路径：
- 新建仓位仍经过 `POST /api/positions` 的 create-and-sync 过渡合同，并返回 `truth_position_public_id`。
- 已有仓位的加仓、减仓、平仓走 `POST /api/trading-positions/{position_public_id}/events`。
- 复盘与叙事写入走 `PATCH /api/trading-positions/{position_public_id}/events/{event_public_id}/narrative`。
- 前端普通操作不得调用 legacy batch/review mutation；public legacy mutation 对已有 owner 资源稳定返回 `409`，不存在 migration/support header 例外。

历史迁移说明（已废止）：
- P11/P12 曾设计由客户端 header 自报 migration intent；该设计已废止，旧 token 不再列为可操作值，也不能授予权限。
- 真正的 legacy migration mutation 必须等待 owner-bound、强制 reason、可审计的 admin/CLI namespace；该 namespace 当前尚未实现。

安全回滚顺序：
- 先确认 `frontend/tests/legacy-ui-boundaries.test.mts` 没有被绕过，避免新页面继续扩张 legacy DTO。
- 用户操作被阻塞时只能改走 canonical truth/narrative route；不得恢复 migration/support UI、query 或 header 绕过。
- 代码回滚也必须保留 public legacy mutation 的 fail-closed 边界，不能通过回滚旧行为提交重新开放写路径。
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

当前修正（覆盖本历史章节的旧设计）：
- public legacy review、position hard delete、batch create/edit/delete 没有可用的 migration fallback token；`X-Migration-Fallback` 的任何客户端值都无效。
- 旧 token 名称不再作为调用指南保留，不能通过 header、query、runtime flag 或数据库配置恢复。
- 受审计的 admin/CLI migration namespace 尚未实现；在它完成 owner 校验、强制 reason 和 audit 前，历史数据清理不能绕过 public guard。

默认保护：
- 对 owner 已验证且资源存在的请求，legacy batch create、legacy review/position update、position hard delete、batch edit/delete 均稳定返回 `409`，不因 truth lifecycle 是否存在而改变；非 owner 目标继续返回 `404`。
- `DELETE /api/positions/{position_id}` 不应成为 audited truth lifecycle 的普通删除方式。
- legacy batch edit/delete 不应替代 truth event reversal、manual adjustment 或未来 compensating event UX。

安全回滚顺序：
- 确认用户是否应走 canonical truth route、narrative route、reversal 或未来 void/archive UX。
- 不得把缺少 migration 工具解释为可以恢复 public header bypass；需要迁移时先实现并评审独立 admin/CLI namespace。
- 如必须回滚其他 JRN-001 代码，仍须保留本 guard、OpenAPI 无 fallback header 以及对应回归测试。

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
- 通用模板、持久 upload/preview 与一次性 canonical confirm 已由 JRN-011/012 提供；preview 不写任何财务事实，confirm 通过 canonical writer 单事务 replay。历史 legacy parser 只保留为不可达参考。

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
