# docs 文档索引

更新时间：2026-06-11
当前执行分支：`dev`

`docs/` 目录按“目标架构 + 当前实现 + 执行清单 + 阶段计划 + 历史基线 + 专题附录”组织。

---

## 推荐阅读顺序

1. [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md)
   当前代码库与运行方式说明，回答“现在实际实现到了哪里”。
2. [TODO.md](./TODO.md)
   当前唯一执行清单，记录 P10 之后的优先级和仍未开发的 backlog。
3. [release-readiness-checklist.md](./release-readiness-checklist.md)
   P19 release readiness 证据矩阵，当前决策为 `READY_FOR_STAGING_ONLY`。
4. [release-rollback-playbook.md](./release-rollback-playbook.md)
   P11-P18 后 truth writes、Timeline snapshot、legacy mutation guard、P13-P18 功能 lane 的发布与回滚手册。
5. [vps-dev-parallel-deployment.md](./vps-dev-parallel-deployment.md)
   已有 main VPS 部署时，如何在同一台 VPS 上隔离部署 `dev` staging。
6. [import-template.md](./import-template.md)
   交易 CSV/Excel 导入模板说明，覆盖当前模板列、示例行和必填字段校验规则。
7. [report-export.md](./report-export.md)
   周报 PDF 导出 runbook，覆盖接口、V1 内容、ReportLab 依赖、验证命令和已知限制。
8. [admin-operations-runbook.md](./admin-operations-runbook.md)
   管理员备份、用户操作、stale job、force-cancel 与恢复演练 runbook。
9. [superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md](./superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md)
   平台底座与前端重设计的总 sequencing plan。
10. [superpowers/plans/2026-05-02-dev-branch-checkpoint.md](./superpowers/plans/2026-05-02-dev-branch-checkpoint.md)
   `dev` 分支阶段 checkpoint 与验收记录。
11. [superpowers/specs/2026-04-06-platform-foundation-design.md](./superpowers/specs/2026-04-06-platform-foundation-design.md)
   平台底座目标架构基线。
12. [superpowers/specs/2026-04-07-frontend-experience-redesign-design.md](./superpowers/specs/2026-04-07-frontend-experience-redesign-design.md)
   前端体验重设计基线。
13. 专题附录：
   [market_data_sources.md](./market_data_sources.md),
   [trading-metrics.md](./trading-metrics.md),
   [trading-fields-design.md](./trading-fields-design.md)

---

## 当前阶段计划

| 文档 | 用途 |
|------|------|
| [2026-06-11-dev-p13-risk-review-product-plan.md](./superpowers/plans/2026-06-11-dev-p13-risk-review-product-plan.md) | P13 risk/review product features 专项计划，已完成；负责组合风险监控、单日亏损提醒、Dashboard 风险展示和 Timeline/Review Inbox 风险行动卡。 |
| [2026-06-11-dev-p14-reporting-export-plan.md](./superpowers/plans/2026-06-11-dev-p14-reporting-export-plan.md) | P14 reporting/export 专项计划，负责导入模板文档、周报 PDF 后端生成、前端导出动作和验证夹具。 |
| [2026-06-11-dev-p15-ai-analysis-workflow-plan.md](./superpowers/plans/2026-06-11-dev-p15-ai-analysis-workflow-plan.md) | P15 AI analysis workflow 专项计划，负责日期范围选择、分析契约收敛、artifact-backed history 和回归测试。 |
| [2026-06-11-dev-p16-market-data-platform-plan.md](./superpowers/plans/2026-06-11-dev-p16-market-data-platform-plan.md) | P16 market data platform 专项计划，负责 provider orchestration 拆分、行情 freshness/degradation 元数据和可重复 provider 验证。 |
| [2026-06-11-dev-p17-admin-operations-plan.md](./superpowers/plans/2026-06-11-dev-p17-admin-operations-plan.md) | P17 admin operations 专项计划，已完成；负责备份触发、管理员晋升、密码重置、stale/failed job 解释和 force-cancel 防护。 |
| [2026-06-11-dev-p18-chart-renderer-migration-plan.md](./superpowers/plans/2026-06-11-dev-p18-chart-renderer-migration-plan.md) | P18 chart renderer migration 专项计划，已完成；剩余 Recharts renderer 已迁移到内部 SVG renderer，并保持 `chart.v1` 数据契约稳定。 |
| [2026-06-11-dev-p19-release-readiness-plan.md](./superpowers/plans/2026-06-11-dev-p19-release-readiness-plan.md) | P19 release readiness 专项计划，已完成；当前 release decision 为 `READY_FOR_STAGING_ONLY`。 |
| [2026-06-11-dev-p12b-observability-error-contract-plan.md](./superpowers/plans/2026-06-11-dev-p12b-observability-error-contract-plan.md) | P12B observability/error contract hardening 专项计划，已完成。 |
| [2026-06-10-dev-p12-platform-contract-hardening-plan.md](./superpowers/plans/2026-06-10-dev-p12-platform-contract-hardening-plan.md) | P12 platform contract hardening 专项计划，已完成；后续 P12B observability/error contract hardening 也已完成。 |
| [2026-06-10-dev-p11-truth-hard-cutover-plan.md](./superpowers/plans/2026-06-10-dev-p11-truth-hard-cutover-plan.md) | P11 truth hard cutover 专项计划，记录 truth-first writes、snapshot Timeline、legacy migration guard 的完成门。 |
| [2026-06-10-dev-p10-progress-next-plan.md](./superpowers/plans/2026-06-10-dev-p10-progress-next-plan.md) | 下一阶段 P10 文档同步、truth hard cutover、observability、API 契约和模型拆分计划。 |
| [2026-06-10-dev-p10-legacy-cutover-inventory.md](./superpowers/plans/2026-06-10-dev-p10-legacy-cutover-inventory.md) | P10 legacy/truth cutover inventory，标记 primary truth、migration-only、delete candidate 和开放产品决策。 |
| [2026-06-10-dev-p10-model-modularization-plan.md](./superpowers/plans/2026-06-10-dev-p10-model-modularization-plan.md) | P10 backend model modularization 计划，定义 `backend/models/` 拆分边界和兼容 re-export 策略。 |
| [2026-06-10-dev-p9f-zero-lint-warning-cleanup-plan.md](./superpowers/plans/2026-06-10-dev-p9f-zero-lint-warning-cleanup-plan.md) | P9F 前端 lint 0 warning 收尾记录。 |
| [2026-06-10-dev-p9e-react19-strict-lint-cleanup-plan.md](./superpowers/plans/2026-06-10-dev-p9e-react19-strict-lint-cleanup-plan.md) | P9E React 19 strict hooks lint 全局启用记录。 |
| [2026-06-10-dev-p9d-chart-schema-freshness-migration-plan.md](./superpowers/plans/2026-06-10-dev-p9d-chart-schema-freshness-migration-plan.md) | P9D chart schema/freshness/ChartFrame 迁移记录。 |
| [2026-06-09-dev-p9c-lifecycle-detail-workbench-plan.md](./superpowers/plans/2026-06-09-dev-p9c-lifecycle-detail-workbench-plan.md) | P9C Lifecycle Detail 工作台记录。 |
| [2026-06-09-dev-p9b-dashboard-workbench-plan.md](./superpowers/plans/2026-06-09-dev-p9b-dashboard-workbench-plan.md) | P9B Dashboard 工作台记录。 |
| [2026-06-09-dev-p9a-frontend-workbench-plan.md](./superpowers/plans/2026-06-09-dev-p9a-frontend-workbench-plan.md) | P9A Timeline-first 前端工作台记录。 |
| [2026-06-06-dev-p8-next16-upgrade-plan.md](./superpowers/plans/2026-06-06-dev-p8-next16-upgrade-plan.md) | P8 Next 16 / React 19 升级记录。 |
| [2026-06-05-dev-p5-p7-execution-plan.md](./superpowers/plans/2026-06-05-dev-p5-p7-execution-plan.md) | P5-P7 dependency、timeline snapshot、insight artifact 记录。 |
| [2026-06-05-dev-p0-p4-execution-plan.md](./superpowers/plans/2026-06-05-dev-p0-p4-execution-plan.md) | P0-P4 平台/前端契约落地记录。 |

---

## 规格与契约

| 文档 | 用途 |
|------|------|
| [2026-04-13-user-trust-metadata-contract.md](./superpowers/specs/2026-04-13-user-trust-metadata-contract.md) | 用户可见 trust metadata 契约。 |
| [2026-04-13-timeline-review-inbox-contract.md](./superpowers/specs/2026-04-13-timeline-review-inbox-contract.md) | Timeline / Review Inbox 契约。 |
| [2026-04-13-lifecycle-detail-contract.md](./superpowers/specs/2026-04-13-lifecycle-detail-contract.md) | Lifecycle Detail 契约。 |
| [platform-foundation-spec-v1.1-patched.md](./superpowers/specs/platform-foundation-spec-v1.1-patched.md) | 平台底座补丁版规格。 |
| [frontend-experience-redesign-spec-v1.1-patched.md](./superpowers/specs/frontend-experience-redesign-spec-v1.1-patched.md) | 前端体验补丁版规格。 |
| [platform-foundation-implementation-plan-v1.md](./superpowers/specs/platform-foundation-implementation-plan-v1.md) | 平台底座早期实施规划。 |

---

## 历史与附录

| 文档 | 用途 |
|------|------|
| [current-state-baseline.md](./current-state-baseline.md) | 2026-04-05 历史审计基线。 |
| [architecture_review.md](./architecture_review.md) | 架构审阅记录。 |
| [import-template.md](./import-template.md) | 交易 CSV/Excel 导入模板说明，覆盖模板列、示例行、必填校验和可选字段建议。 |
| [report-export.md](./report-export.md) | 周报 PDF 导出 runbook，覆盖接口、V1 内容、依赖、验证命令和限制。 |
| [admin-operations-runbook.md](./admin-operations-runbook.md) | 管理员备份、用户操作、stale job、force-cancel 与恢复演练 runbook。 |
| [release-readiness-checklist.md](./release-readiness-checklist.md) | P19 发布就绪证据矩阵与 staging-only 决策记录。 |
| [vps-dev-parallel-deployment.md](./vps-dev-parallel-deployment.md) | 同一台 VPS 上 main 与 dev staging 并行部署指南，覆盖 Compose override、Caddy 反代、独立数据库和验证步骤。 |
| [market_data_sources.md](./market_data_sources.md) | 市场数据 provider、路由、配置、限制和排障。 |
| [trading-metrics.md](./trading-metrics.md) | 指标算法与实现状态。 |
| [trading-fields-design.md](./trading-fields-design.md) | 当前 / 实施中字段边界。 |
| [顶层设计.md](./顶层设计.md) | 历史草案，不作为当前方案依据。 |

---

## 维护规则

- 当前真实实现维护在 `DEVELOPER_GUIDE.md`。
- 当前要做什么维护在 `TODO.md`。
- 分阶段实施和验收记录维护在 `docs/superpowers/plans/`。
- 目标架构和契约维护在 `docs/superpowers/specs/`。
- 不要在多个文档里维护互相冲突的 roadmap 数字。
- 如果文档与代码不一致，以代码和最新 checkpoint 为准，再同步文档。
- `docs/superpowers/demos/` 是未跟踪用户内容，除非用户明确要求，否则不要修改或提交。
