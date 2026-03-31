# plan 文档索引

`plan/` 目录现在按“主文档 + 附录 + 执行清单 + 历史草案”组织。

## 推荐阅读顺序

1. [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md)
   当前唯一主开发文档，覆盖架构、模块现状、开发入口和附录索引。
2. [TODO.md](./TODO.md)
   当前执行清单，记录阶段、任务和完成度。
3. [market_data_sources.md](./market_data_sources.md)
   市场数据接入附录，说明 provider 路由、配置、限制和排障。
4. [trading-metrics.md](./trading-metrics.md)
   指标算法附录，区分当前已实现、已部分实现和未来规划。
5. [trading-fields-design.md](./trading-fields-design.md)
   数据模型附录，区分当前系统已有字段和 Phase 3+ 扩展设计。

## 历史资料

- [顶层设计.md](./顶层设计.md)
  早期功能蓝图，现已降级为历史草案，不再作为当前实现依据。

## 维护规则

- 新的功能说明先进入主开发文档，再按需要拆到附录。
- 新的开发任务先进入 `TODO.md`。
- 不要在多个文档里维护不同版本的 roadmap 数字。
- 如果某份文档与代码不一致，以代码和主开发文档为准，再回头修正文档。
