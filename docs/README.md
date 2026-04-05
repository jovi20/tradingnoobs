# docs 文档索引

`docs/` 目录现在按“主文档 + 现状基线 + 附录 + 执行清单 + 历史草案”组织。

## 推荐阅读顺序

1. [current-state-baseline.md](./current-state-baseline.md)
   当前代码审计基线，集中说明已经做了什么、没做什么、做得好的地方和当前短板，适合进入架构讨论前先统一认知。
2. [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md)
   当前唯一主开发文档，覆盖架构、模块现状、开发入口和附录索引。
3. [TODO.md](./TODO.md)
   当前执行清单，记录阶段、任务和完成度。
4. [superpowers/specs/2026-04-06-platform-foundation-design.md](./superpowers/specs/2026-04-06-platform-foundation-design.md)
   当前架构设计稿，沉淀本轮关于平台底座、数据库分层、命名调整、认证框架和横切能力的设计结论。
5. [market_data_sources.md](./market_data_sources.md)
   市场数据接入附录，说明 provider 路由、配置、限制和排障。
6. [trading-metrics.md](./trading-metrics.md)
   指标算法附录，区分当前已实现、已部分实现和未来规划。
7. [trading-fields-design.md](./trading-fields-design.md)
   数据模型附录，区分当前系统已有字段和 Phase 3+ 扩展设计。

## 维护规则

- 新的功能说明先进入主开发文档，再按需要拆到附录。
- 新的开发任务先进入 `TODO.md`。
- 不要在多个文档里维护不同版本的 roadmap 数字。
- 如果某份文档与代码不一致，以代码和主开发文档为准，再回头修正文档。
