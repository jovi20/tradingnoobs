# Trading Noobs 开发任务清单

本文档是当前唯一执行清单，只记录：
- 阶段划分
- 任务项
- 完成状态

设计说明、架构说明和专题细节请查看：
- [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md)
- [market_data_sources.md](./market_data_sources.md)
- [trading-metrics.md](./trading-metrics.md)
- [trading-fields-design.md](./trading-fields-design.md)

---

## Phase 1: 交易规划模块

### 1.1 交易前检查清单
- [x] **后端** 扩展 `Strategy` 模型，添加 `checklist_items`
- [x] **后端** 扩展 `Position` 模型，添加 `checklist_responses` 和 `checklist_completed_at`
- [x] **后端** 更新 `schemas.py` 支持新字段
- [x] **后端** 增加数据库迁移脚本
- [x] **前端** 策略编辑页添加检查清单编辑能力
- [x] **前端** 开仓流程集成检查清单确认
- [ ] **前端** `positions` 列表页显示检查清单完成情况
- [ ] **前端** 看板页显示检查清单完成情况

### 1.2 计划偏移检测
- [x] **后端** `Position` 模型添加 `planned_entry_price`、`planned_stop_loss`、`planned_take_profit`
- [x] **后端** 实现 `calculate_drift()` 或等效偏移分析逻辑
- [x] **后端** 在 `Position` 响应中返回偏移分析
- [x] **前端** 开仓表单添加计划价格输入
- [x] **前端** 持仓详情页显示计划 vs 实际对比

---

## Phase 2: 绩效分析增强

### 2.1 风险调整收益指标
- [x] **后端** 创建 `services/metrics_service.py`
- [x] **后端** 实现 Sharpe Ratio
- [x] **后端** 实现 Sortino Ratio
- [x] **后端** 实现 Calmar Ratio
- [x] **后端** Dashboard API 返回上述指标
- [x] **前端** Dashboard 显示风险调整指标卡片

### 2.2 MAE/MFE 分析
- [x] **后端** `Position` 模型添加 `max_price_during_hold`、`min_price_during_hold`
- [x] **后端** 计算 MAE/MFE 百分比
- [x] **前端** 持仓详情支持录入持仓期间最高/最低价
- [x] **前端** 新增 MAE/MFE 散点图组件

---

## Phase 3: 风控预警系统

### 3.1 组合风险监控
- [ ] **后端** 创建 `services/risk_alert_service.py`
- [ ] **后端** 实现组合风险检查逻辑
- [ ] **后端** 实现单日亏损上限检查
- [ ] **前端** Dashboard 显示当前组合风险

### 3.2 实时预警
- [ ] **后端** 创建 WebSocket 端点
- [ ] **前端** 集成 Toast 预警通知

---

## Phase 4: 数据导入导出

### 4.1 CSV/Excel 批量导入
- [x] **后端** 创建导入端点 `/api/positions/import`
- [x] **后端** 解析 CSV/Excel 文件
- [x] **后端** 实现字段映射和数据验证
- [x] **前端** 实现导入向导 UI
- [ ] **文档** 补充导入模板说明

### 4.2 PDF 报告导出
- [ ] **后端** 集成 PDF 生成库
- [ ] **后端** 创建周报 PDF 模板
- [ ] **前端** 报告页添加导出 PDF 按钮

---

## Phase 5: AI 高级分析中心

### 5.1 AI 分析助手
- [x] **后端** 创建 `services/analytics_service.py`
- [x] **后端** 扩展 `routers/insights.py`，新增 `/api/insights/analyze`
- [x] **后端** 扩展 `llm_service.py`，新增分析型 Prompt
- [x] **前端** 在 Insights 页面新增 AI 分析助手卡片
- [x] **前端** 实现分析类型选择器
- [ ] **前端** 实现日期范围选择器
- [x] **前端** 实现分析结果展示（数据 + AI 结论）

---

## Phase 6: 运维及测试

### 6.1 管理员运维能力
- [ ] **后端** 提供数据库备份触发入口
- [ ] **后端** 提供账户升级为管理员的安全入口
- [ ] **后端** 提供管理员重置账户密码能力

### 6.2 测试与校验
- [ ] **后端** 为市场数据 provider 补充可重复执行的验证方案
- [ ] **后端** 为导入流程补充核心测试
- [ ] **前后端** 为 AI 分析助手补充回归测试或最小验收用例

---

## 完成状态统计

| Phase | 任务数 | 已完成 |
|-------|--------|--------|
| Phase 1 | 13 | 11 |
| Phase 2 | 10 | 10 |
| Phase 3 | 6 | 0 |
| Phase 4 | 8 | 4 |
| Phase 5 | 7 | 6 |
| Phase 6 | 6 | 0 |
| **总计** | **50** | **31** |
