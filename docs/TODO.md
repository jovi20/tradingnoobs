# Trading Noobs 当前任务清单

更新时间：2026-07-25
当前执行分支：`dev`
当前状态：`TRADING_JOURNAL_HARDENING_ACTIVE / NOT_READY_FOR_PRODUCTION`

本文档只记录当前执行批次。唯一 active implementation plan 是 [2026-07-16-dev-trading-journal-development-plan.md](./superpowers/plans/2026-07-16-dev-trading-journal-development-plan.md)；审计来源见 [design-implementation-gap-plan-2026-07-15.md](./design-implementation-gap-plan-2026-07-15.md)。

## 当前结论

- 旧 P0-P19 只代表历史阶段切片归档，不代表产品或生产闭环完成。
- 当前唯一 active lane 是 launch-safe 交易日志；source-bound IBKR statement 文件 Import 属于 M1，在线 Broker Sync、量化、Market Data、AI、PDF 和风险卡不进入首批执行。
- 当前仍是 `NOT_READY_FOR_PRODUCTION`，不得直接部署真实用户环境。
- `JRN-000` 与 `JRN-001` 已完成。JRN-001 的最终 implementation checkpoint `1c382ce` 已通过精确归档全量、双视口浏览器、真实 PostgreSQL 16 验证，并取得同一 SHA 两路全新独立 `APPROVE`；六个更早 checkpoint 均已 supersede，完整历史见 checkpoint record。
- `JRN-001` 不新增 Alembic revision，migration head 继续是 `9cad10111213`；其最终证据必须绑定稳定 scoped checkpoint。
- `JRN-002` 最终 scoped checkpoint `876cda7` 已在无复用 venv/node_modules/npm cache 的精确 SHA 环境通过统一 gate 和本地评审；远端 workflow 与 required-check 证据尚未产生，因此仍不标记 `COMPLETE`。
- `JRN-003` 最终 scoped checkpoint `cacf8c0` 已通过真实 PostgreSQL 16（含 migration downgrade/re-upgrade 与首次限流 bucket 并发竞争）、统一 gate 和本地评审；远端 workflow 与 required-check 证据尚未产生，因此仍不标记 `COMPLETE`。
- `JRN-004` 最终 scoped checkpoint `575c67d` 已通过真实 PostgreSQL 16（含 owner-scoped idempotency migration、并发首次写入与 downgrade/re-upgrade）、477 项后端测试、160 项前端测试和本地评审；评审发现的 nested batch owner resolver 遗漏已修复。远端 workflow 与 required-check 证据尚未产生，因此仍不标记 `COMPLETE`。
- `JRN-005` 最终 scoped checkpoint `2c0e8d0` 已冻结 `JOURNAL_ACCOUNTING_V1`、ADR、posting matrix、错误码和可执行 golden vectors，并通过 481 项后端测试、160 项前端测试与本地评审；当前 ledger 实现仍不符合该合同，属于 JRN-006，且远端 required-check 未关闭。
- IBKR 文件的重复、重叠、增量导入与 correction replay 只在 `JRN-013` 至 `JRN-015` 实现，当前合同冻结不代表功能已落地。
- 本轮不自动 merge 到 `main`、不创建 PR、不打 tag；这些属于后续显式操作。
- 旧 P0-P19 阶段计划已归档到 [superpowers/plans/archive/](./superpowers/plans/archive/)。

## 当前执行批次

| 优先级 | 状态 | 任务 | 退出条件 | 参考 |
|--------|------|------|------|------|
| P0 | `COMPLETE` | `JRN-000` WIP、migration chain 与 checkpoint | 已有逐路径 disposition 和 checkpoint；四个 migration 已进入 `9cad10111213` baseline；optional runtime 默认不可达。 | Active plan Step 0 |
| P0 | `COMPLETE` | `JRN-001` release contract 与 capability ceiling | `1c382ce` 已通过完整验证、真实浏览器门禁与同 SHA 双路独立评审；合同及禁用边界已冻结。 | Active plan M0 |
| P0 | `CHECKPOINT_LOCAL_REVIEW_PASS / REMOTE_CI_PENDING` | `JRN-002` 可复现基线与 PostgreSQL CI | `876cda7` 精确 SHA 干净重建、统一 gate 与本地评审已通过；待远端 workflow 和 required-check 证据关闭。 | Active plan M0 |
| P0 | `CHECKPOINT_LOCAL_REVIEW_PASS / REMOTE_CI_PENDING` | `JRN-003` invite-only auth 与 release secret | `cacf8c0` 已通过精确 SHA 全量 gate 与本地评审；待远端 workflow 和 required-check 证据关闭。 | Active plan M0 |
| P0 | `CHECKPOINT_LOCAL_REVIEW_PASS / REMOTE_CI_PENDING` | `JRN-004` tenant/owner 边界封闭 | `575c67d` 已通过精确 SHA 全量 gate 与本地评审；当前资源两用户矩阵、混合 owner graph、public/internal ID 和 legacy import deny-only 边界通过；待远端 workflow 和 required-check 证据关闭。 | Active plan M0 |
| P0 | `CHECKPOINT_LOCAL_REVIEW_PASS / REMOTE_CI_PENDING` | `JRN-005` 会计 posting matrix 与 golden vectors | `2c0e8d0` 已冻结合同、逐事件矩阵、错误码、golden vectors 和脱敏存量扫描；待远端 workflow 和 required-check 证据关闭。 | Active plan M1 |
| P0 | `BLOCKED_BY_JRN_004_005_REMOTE_CI` | `JRN-006` append-only ledger 与 journal balance 收敛 | 不得开始实现；必须先取得 JRN-004/005 closure，再以全部 JRN-005 vectors 作为验收 oracle。 | Active plan M1 |

JRN-000/001 已完成；JRN-002/003/004/005 的本地 checkpoint 均已通过，但远端 CI/required-check 证据仍未产生。JRN-006 明确等待 JRN-004/005 closure，当前不继续会计实现。source-bound IBKR 实现仍严格等待 JRN-013 至 JRN-015。不得提前做新页面、模型拆分、在线 Broker Sync、Market、AI 或量化功能。

## 暂不做

- 不把完整 gap inventory 当作当前任务队列；只执行 active trading-journal plan。
- 不删除 legacy 表、模型或 API 响应，除非有迁移验证和 rollback 方案。
- 不把 Dashboard 改回默认首页；默认入口继续围绕 Timeline / Review Inbox。
- 不继续把新页面直接绑定 raw legacy DTO。
- 不执行 Market Data、Redis、多 schema、完整 read-model 平台、模型拆分或任何量化主链。
- 不自动 merge、push、PR、tag，除非用户明确要求。

## 验证门

JRN-002 之后，任何进入提交或部署前的整理优先运行统一 gate：

```bash
backend/venv/bin/python scripts/run_journal_baseline_gate.py
```

快速静态检查仍保留：

```bash
git diff --check
bash -n start.sh
```

涉及前端行为时跑：

```bash
cd frontend
npm test
npm run lint
npx tsc --noEmit
npm run build
```
