# Trading Noobs 当前任务清单

更新时间：2026-07-17
当前执行分支：`dev`
当前状态：`TRADING_JOURNAL_HARDENING_ACTIVE / NOT_READY_FOR_PRODUCTION`

本文档只记录当前执行批次。唯一 active implementation plan 是 [2026-07-16-dev-trading-journal-development-plan.md](./superpowers/plans/2026-07-16-dev-trading-journal-development-plan.md)；审计来源见 [design-implementation-gap-plan-2026-07-15.md](./design-implementation-gap-plan-2026-07-15.md)。

## 当前结论

- 旧 P0-P19 只代表历史阶段切片归档，不代表产品或生产闭环完成。
- 当前唯一 active lane 是 launch-safe 交易日志；source-bound IBKR statement 文件 Import 属于 M1，在线 Broker Sync、量化、Market Data、AI、PDF 和风险卡不进入首批执行。
- 当前仍是 `NOT_READY_FOR_PRODUCTION`，不得直接部署真实用户环境。
- `JRN-000` 已完成 checkpoint；`JRN-001` 的 `cf4766de`、`7ec29b1` 与 `8b5f37d` checkpoint 均已因独立 `CHANGES_REQUIRED` supersede。新 checkpoint `07d4012` 已完成精确归档全量验证与真实 PostgreSQL 16 验证，正在等待同一 SHA 的全新独立评审，尚未完成。
- `JRN-001` 不新增 Alembic revision，migration head 继续是 `9cad10111213`；其最终证据必须绑定稳定 scoped checkpoint。
- IBKR 文件的重复、重叠、增量导入与 correction replay 只在 `JRN-013` 至 `JRN-015` 实现，当前合同冻结不代表功能已落地。
- 本轮不自动 merge 到 `main`、不创建 PR、不打 tag；这些属于后续显式操作。
- 旧 P0-P19 阶段计划已归档到 [superpowers/plans/archive/](./superpowers/plans/archive/)。

## 当前执行批次

| 优先级 | 状态 | 任务 | 退出条件 | 参考 |
|--------|------|------|------|------|
| P0 | `COMPLETE` | `JRN-000` WIP、migration chain 与 checkpoint | 已有逐路径 disposition 和 checkpoint；四个 migration 已进入 `9cad10111213` baseline；optional runtime 默认不可达。 | Active plan Step 0 |
| P0 | `FINAL_VERIFICATION_REVIEW` | `JRN-001` release contract 与 capability ceiling | 冻结币种/标的/事件/Import gate 合同；禁用能力和未实现 Import 不可由 API、Admin flag、secret、job 或旧 UI 绕过；replacement checkpoint 必须通过完整验证、真实浏览器门禁与同 SHA 独立评审。 | Active plan M0 |
| P0 | `PENDING_JRN_001` | `JRN-002` 可复现基线与 PostgreSQL CI | 干净环境、本地/CI 同命令、PostgreSQL 空库 migration 与 integration 可重跑。 | Active plan M0 |
| P0 | `PENDING_JRN_001` | `JRN-003` invite-only auth 与 release secret | 一次性邀请码、限流、弱密钥 fail-fast；普通 setting 无明文 Broker/Market/LLM secret。 | Active plan M0 |
| P0 | `PENDING_JRN_002_003` | `JRN-004` tenant/owner 边界封闭 | 当前 account/strategy/position/event/ledger/note/idempotency 两用户矩阵无越权；legacy import 已 owner-guard 或关闭；future resource harness 冻结。 | Active plan M0 |

JRN-000 已完成；当前只收口 JRN-001 的稳定 checkpoint、最终验证和独立评审。JRN-001 批准后，JRN-002/003 可并行，JRN-004 后收口。五项全部通过后，按 active plan 进入会计、canonical writer、不可变纠错和通用 bootstrap；source-bound IBKR 实现仍严格等待 JRN-013 至 JRN-015。不得提前做新页面、模型拆分、在线 Broker Sync、Market、AI 或量化功能。

## 暂不做

- 不把完整 gap inventory 当作当前任务队列；只执行 active trading-journal plan。
- 不删除 legacy 表、模型或 API 响应，除非有迁移验证和 rollback 方案。
- 不把 Dashboard 改回默认首页；默认入口继续围绕 Timeline / Review Inbox。
- 不继续把新页面直接绑定 raw legacy DTO。
- 不执行 Market Data、Redis、多 schema、完整 read-model 平台、模型拆分或任何量化主链。
- 不自动 merge、push、PR、tag，除非用户明确要求。

## 验证门

任何进入提交或部署前的整理至少跑：

```bash
git diff --check
bash -n start.sh
```

涉及后端行为时跑：

```bash
cd backend
venv/bin/python -m pytest -q
```

涉及前端行为时跑：

```bash
cd frontend
npm test
npm run lint
npx tsc --noEmit
npm run build
```
