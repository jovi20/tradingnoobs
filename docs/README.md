# docs 文档索引

更新时间：2026-07-17
当前执行分支：`dev`

`docs/` 现在按“当前事实 + 后续计划 + 运维 runbook + 历史归档”组织。P0-P19 阶段切片计划已归档到 `docs/superpowers/plans/archive/`；归档只表示该切片收口，不表示上位规格或生产闭环全部完成。

## 推荐阅读顺序

1. [project-summary-and-roadmap.md](./project-summary-and-roadmap.md)
   项目描述、当前状态、后续计划和不做事项。
2. [superpowers/plans/2026-07-16-dev-trading-journal-development-plan.md](./superpowers/plans/2026-07-16-dev-trading-journal-development-plan.md)
   当前唯一 active implementation plan，聚焦 launch-safe 交易日志。
3. [design-implementation-gap-plan-2026-07-15.md](./design-implementation-gap-plan-2026-07-15.md)
   全量设计承诺与当前实现的审计基线、风险登记册和 Gap ID 来源。
4. [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md)
   当前代码库、运行方式、模块边界和开发注意事项。
5. [TODO.md](./TODO.md)
   当前最小任务清单，只记录下一步要做什么。
6. [project-structure-review.md](./project-structure-review.md)
   2026-07-06 项目文件与结构审查记录。
7. [script-inventory.md](./script-inventory.md)
   当前脚本清单、必要性评估和后续维护规则。
8. [release-readiness-checklist.md](./release-readiness-checklist.md)
   P19 历史发布证据矩阵；当前 release profile 以 active trading-journal plan 为准。
9. [release-rollback-playbook.md](./release-rollback-playbook.md)
   P11-P18 truth writes、Timeline snapshot、legacy mutation guard、P13-P18 功能 lane 的发布与回滚手册。
10. [vps-dev-parallel-deployment.md](./vps-dev-parallel-deployment.md)
   已有 main VPS 部署时，如何在同一台 VPS 上隔离部署 `dev` staging。

## 当前计划

| 文档 | 用途 |
|------|------|
| [superpowers/plans/2026-07-16-dev-trading-journal-development-plan.md](./superpowers/plans/2026-07-16-dev-trading-journal-development-plan.md) | 当前唯一 active plan；只推进交易日志正确性、安全、可恢复性和 invite-only Beta。 |
| [design-implementation-gap-plan-2026-07-15.md](./design-implementation-gap-plan-2026-07-15.md) | 全量审计基线与风险登记册；不是逐项照单执行的开发路线。 |
| [TODO.md](./TODO.md) | 当前最小执行清单。 |
| [project-summary-and-roadmap.md](./project-summary-and-roadmap.md) | 项目现状与后续路线图。 |
| [superpowers/plans/README.md](./superpowers/plans/README.md) | 当前计划目录说明。 |
| [superpowers/plans/archive/2026-06-10-dev-p10-legacy-cutover-inventory.md](./superpowers/plans/archive/2026-06-10-dev-p10-legacy-cutover-inventory.md) | Archived supporting inventory：legacy/truth 边界历史参考。 |
| [superpowers/plans/archive/2026-06-10-dev-p10-model-modularization-plan.md](./superpowers/plans/archive/2026-06-10-dev-p10-model-modularization-plan.md) | Archived deferred reference：模型拆分在交易语义稳定前不执行。 |

## Runbook 与专题

| 文档 | 用途 |
|------|------|
| [admin-operations-runbook.md](./admin-operations-runbook.md) | 管理员备份、用户操作、stale job、force-cancel 与恢复演练。 |
| [import-template.md](./import-template.md) | 交易 CSV/Excel 导入模板说明。 |
| [market_data_sources.md](./market_data_sources.md) | 市场数据 provider、路由、配置、限制和排障。 |
| [report-export.md](./report-export.md) | 周报 PDF 导出 runbook。 |
| [script-inventory.md](./script-inventory.md) | 项目脚本清单、保留/删除判断和维护规则。 |
| [trading-fields-design.md](./trading-fields-design.md) | 当前 / 实施中字段边界。 |
| [trading-metrics.md](./trading-metrics.md) | 指标算法与实现状态。 |

## 规格与契约

| 文档 | 用途 |
|------|------|
| [superpowers/specs/2026-04-06-platform-foundation-design.md](./superpowers/specs/2026-04-06-platform-foundation-design.md) | 平台底座目标架构基线。 |
| [superpowers/specs/2026-04-07-frontend-experience-redesign-design.md](./superpowers/specs/2026-04-07-frontend-experience-redesign-design.md) | 前端体验重设计基线。 |
| [superpowers/specs/2026-04-13-user-trust-metadata-contract.md](./superpowers/specs/2026-04-13-user-trust-metadata-contract.md) | 用户可见 trust metadata 契约。 |
| [superpowers/specs/2026-04-13-timeline-review-inbox-contract.md](./superpowers/specs/2026-04-13-timeline-review-inbox-contract.md) | Timeline / Review Inbox 契约。 |
| [superpowers/specs/2026-04-13-lifecycle-detail-contract.md](./superpowers/specs/2026-04-13-lifecycle-detail-contract.md) | Lifecycle Detail 契约。 |
| [trade-record-sync-design.md](./trade-record-sync-design.md) | 通用 bootstrap、IBKR Flex source-bound 文件增量导入与在线 sync 延期边界。 |
| [superpowers/specs/platform-foundation-spec-v1.1-patched.md](./superpowers/specs/platform-foundation-spec-v1.1-patched.md) | 平台底座补丁版规格。 |
| [superpowers/specs/frontend-experience-redesign-spec-v1.1-patched.md](./superpowers/specs/frontend-experience-redesign-spec-v1.1-patched.md) | 前端体验补丁版规格。 |

## 历史归档

| 文档 | 用途 |
|------|------|
| [superpowers/plans/archive/README.md](./superpowers/plans/archive/README.md) | 已完成 P0-P19 阶段计划归档索引。 |
| [current-state-baseline.md](./current-state-baseline.md) | 2026-04-05 历史审计基线，不作为当前实现依据。 |
| [architecture_review.md](./architecture_review.md) | 架构审阅记录。 |
| `顶层设计.md` | 历史草案，当前仓库未跟踪；不作为当前方案依据。 |

## 维护规则

- 当前真实实现维护在 [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md)。
- 当前要做什么维护在 [TODO.md](./TODO.md)。
- 产品方向和中期阶段维护在 [project-summary-and-roadmap.md](./project-summary-and-roadmap.md)；任务顺序与验收维护在 active implementation plan。
- 已完成阶段计划保留在 `docs/superpowers/plans/archive/`，不要再作为当前 active lane。
- 目标架构和契约维护在 `docs/superpowers/specs/`。
- 如果文档与代码不一致，以代码和最新 checkpoint 为准，再同步文档。
