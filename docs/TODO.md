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
- `JRN-002` 至 `JRN-005` 已完成：最终 scoped checkpoint `876cda7`、`cacf8c0`、`575c67d`、`2c0e8d0` 均为远端验证提交 `68532b8` 的祖先；GitHub Actions run `30151924998` 的 `journal-baseline` job `89663633330` 与 artifact `8617918462` 成功。
- GitHub ruleset `main-journal-baseline`（ID `19728078`）为 `Active`，仅目标 `refs/heads/main`，要求 GitHub Actions `journal-baseline`；`dev` 不受该 ruleset 限制。
- `JRN-006` 已在本地实现 `JOURNAL_ACCOUNTING_V1`：migration head 为 `c3d4e5f6a7b8`，append-only、posting uniqueness、ledger replay、存量隔离、accounting health 与降级 UI 已通过统一 PostgreSQL 门禁；尚待 scoped checkpoint、精确 SHA 重验和远端 CI 后关闭。
- IBKR 文件的重复、重叠、增量导入与 correction replay 只在 `JRN-013` 至 `JRN-015` 实现，当前合同冻结不代表功能已落地。
- 本轮不自动 merge 到 `main`、不创建 PR、不打 tag；这些属于后续显式操作。
- 旧 P0-P19 阶段计划已归档到 [superpowers/plans/archive/](./superpowers/plans/archive/)。

## 当前执行批次

| 优先级 | 状态 | 任务 | 退出条件 | 参考 |
|--------|------|------|------|------|
| P0 | `COMPLETE` | `JRN-000` WIP、migration chain 与 checkpoint | 已有逐路径 disposition 和 checkpoint；四个 migration 已进入 `9cad10111213` baseline；optional runtime 默认不可达。 | Active plan Step 0 |
| P0 | `COMPLETE` | `JRN-001` release contract 与 capability ceiling | `1c382ce` 已通过完整验证、真实浏览器门禁与同 SHA 双路独立评审；合同及禁用边界已冻结。 | Active plan M0 |
| P0 | `COMPLETE` | `JRN-002` 可复现基线与 PostgreSQL CI | `876cda7` 精确 SHA 干净重建、统一 gate、本地评审、远端 workflow、artifact 与 main required-check 证据均已关闭。 | Active plan M0 |
| P0 | `COMPLETE` | `JRN-003` invite-only auth 与 release secret | `cacf8c0` 已通过精确 SHA 全量 gate、本地评审及共同远端验证提交 `68532b8` 的 required check。 | Active plan M0 |
| P0 | `COMPLETE` | `JRN-004` tenant/owner 边界封闭 | `575c67d` 的两用户矩阵、混合 owner graph、public/internal ID 和 legacy import deny-only 边界已通过，并取得远端 CI 与 required-check 证据。 | Active plan M0 |
| P0 | `COMPLETE` | `JRN-005` 会计 posting matrix 与 golden vectors | `2c0e8d0` 已冻结合同、逐事件矩阵、错误码、golden vectors 和脱敏存量扫描，并取得远端 CI 与 required-check 证据。 | Active plan M1 |
| P0 | `IN_PROGRESS` | `JRN-006` append-only ledger 与 journal balance 收敛 | 本地实现与统一 gate 已通过；待 scoped checkpoint、精确 SHA 重验、远端 `journal-baseline` 和 evidence record。 | Active plan M1 |

JRN-000 至 JRN-005 已完成。JRN-006 已通过本地实现门禁但尚未形成远端闭环；产品整体仍为 `NOT_READY_FOR_PRODUCTION`。source-bound IBKR 实现仍严格等待 JRN-013 至 JRN-015。不得提前做新页面、模型拆分、在线 Broker Sync、Market、AI 或量化功能。

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
