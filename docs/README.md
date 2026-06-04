# docs 文档索引

`docs/` 目录现在按“目标架构 + 当前实现 + 当前执行计划 + legacy backlog + 历史基线 + 专题附录”组织。

## 推荐阅读顺序

1. [superpowers/specs/2026-04-06-platform-foundation-design.md](./superpowers/specs/2026-04-06-platform-foundation-design.md)
   当前唯一的目标架构文档，沉淀平台底座、数据库分层、市场数据中台、图表架构、账户配置、AI 中台等设计结论。
2. [superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md](./superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md)
   当前执行计划，定义平台底座与前端重构的交付顺序、前端 gate 和禁止提前启动的事项。
3. [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md)
   当前代码库与运行方式说明，重点回答“仓库现在怎么组织、怎么启动、目前实现到了哪里”。
4. [TODO.md](./TODO.md)
   Legacy backlog，记录架构收敛前功能清单和历史完成度，不再作为新增开发任务的唯一入口。
5. [current-state-baseline.md](./current-state-baseline.md)
   2026-04-05 的历史审计基线，记录架构收敛前的仓库现状、优点与短板，适合回看设计背景。
6. [market_data_sources.md](./market_data_sources.md)
   市场数据接入附录，说明 provider 路由、配置、限制和排障。
7. [trading-metrics.md](./trading-metrics.md)
   指标算法附录，区分当前已实现、已部分实现和未来规划。
8. [trading-fields-design.md](./trading-fields-design.md)
   数据模型附录，区分当前系统已有字段和 Phase 3+ 扩展设计。

## 维护规则

- 目标架构和未来设计只维护在 `specs/` 下的架构文档中。
- 当前跨后端/前端的交付顺序维护在 `superpowers/plans/` 下的 sequencing plan 中。
- 当前代码实现、运行入口和现状说明维护在 `DEVELOPER_GUIDE.md`。
- 新的开发任务先进入当前 sequencing plan，旧功能 backlog 可在 `TODO.md` 中保留引用。
- `current-state-baseline.md` 视为历史快照，不作为长期主真相来源持续维护。
- 不要在多个文档里维护不同版本的 roadmap 数字。
- 如果某份文档与代码不一致，以代码和“当前实现类文档”为准，再回头修正文档。
