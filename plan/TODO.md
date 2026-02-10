# TradingNoobs 开发任务清单

> 基于 Gap Analysis 生成的开发任务列表

---

## Phase 1: 交易规划模块 ⭐ 高优先级

### 1.1 交易前检查清单（扩展策略模型）
- [x] **后端** 扩展 Strategy 模型，添加 `checklist_items` JSON 字段
- [x] **后端** 扩展 Position 模型，添加 `checklist_responses` 和 `checklist_completed_at` 字段
- [x] **后端** 更新 schemas.py 支持新字段
- [x] **后端** 数据库迁移脚本
- [x] **前端** 策略编辑页添加检查清单编辑 Tab
- [x] **前端** 开仓流程集成检查清单确认
- [ ] **前端** positons页显示检查清单完成情况
- [ ] **前端** 看板页显示检查清单完成情况

### 1.2 计划偏移检测
- [x] **后端** Position 模型添加 `planned_entry_price`, `planned_stop_loss`, `planned_take_profit`
- [x] **后端** 实现 `calculate_drift()` 函数
- [x] **后端** 在 Position 响应中返回偏移分析
- [x] **前端** 开仓表单添加计划价格输入
- [x] **前端** Position 详情页显示计划 vs 实际对比

---

## Phase 2: 绩效分析增强 ⭐ 高优先级

### 2.1 风险调整收益指标
- [x] **后端** 创建 `services/metrics_service.py`
- [x] **后端** 实现 Sharpe Ratio 计算
- [x] **后端** 实现 Sortino Ratio 计算
- [x] **后端** 实现 Calmar Ratio 计算
- [x] **后端** Dashboard API 返回这些指标
- [x] **前端** Dashboard 显示风险调整指标卡片

### 2.2 MAE/MFE 分析
- [x] **后端** Position 模型添加 `max_price_during_hold`, `min_price_during_hold`
- [x] **后端** 计算 MAE/MFE 百分比
- [x] **前端** 持仓详情添加手动输入期间最高/最低价
- [x] **前端** 新增 MAE/MFE 散点图组件

---

## Phase 3: 风控预警系统 🔶 中优先级

### 3.1 组合风险监控
- [ ] **后端** 创建 `services/risk_alert_service.py`
- [ ] **后端** 实现组合风险检查逻辑
- [ ] **后端** 实现单日亏损上限检查
- [ ] **前端** Dashboard 显示当前组合风险

### 3.2 实时预警（可选 WebSocket）
- [ ] **后端** 创建 WebSocket 端点
- [ ] **前端** Toast 通知集成

---

## Phase 4: 数据导入导出 🔶 中优先级

### 4.1 CSV/Excel 批量导入
- [ ] **后端** 创建导入端点 `/api/positions/import`
- [ ] **后端** 解析 CSV/Excel 文件
- [ ] **后端** 字段映射和数据验证
- [ ] **前端** 导入向导 UI
- [ ] **文档** 提供导入模板下载

### 4.2 PDF 报告导出
- [ ] **后端** 集成 PDF 生成库（如 weasyprint）
- [ ] **后端** 创建周报 PDF 模板
- [ ] **前端** 报告页添加"导出 PDF"按钮

---

## Phase 5: AI 高级分析中心 🔵 （与 Insights 页面整合）

> **设计理念**：将高级分析功能与 AI 结合，在现有 Insights 页面中提供"AI 分析助手"模块，用户可选择不同分析类型，AI 生成带结论的分析报告。

### 5.1 AI 分析助手（扩展 Insights 页面）

**新增分析类型：**

| 分析类型 | 描述 | AI 输出 |
|----------|------|---------|
| 📊 持仓时间分析 | 按持仓周期分组统计绩效 | 最佳持仓周期建议、过早/过晚出场模式识别 |
| 📉 连败模式分析 | 分析连续亏损的规律 | 连败原因诊断、心理预警、恢复建议 |
| 🧠 情绪-绩效关联 | 按情绪标签分组统计 | 情绪对盈亏的影响分析、最佳情绪状态识别 |
| ✅ 检查清单效果 | 满足检查项 vs 未满足的胜率对比 | 检查清单有效性评估、优化建议 |
| 🎯 策略表现诊断 | 按策略分析胜率/盈亏比变化 | 策略衰减预警、优化方向 |

**后端任务：**
- [ ] 创建 `services/analytics_service.py` - 高级分析计算逻辑
- [ ] 扩展 `routers/insights.py` - 新增 `/api/insights/analyze` 端点
- [ ] 扩展 `llm_service.py` - 新增分析类型的 Prompt 模板

**API 设计：**
```python
POST /api/insights/analyze
{
    "analysis_type": "holding_period" | "losing_streak" | "emotion_pnl" | "checklist_effect" | "strategy_health",
    "start_date": "2026-01-01",
    "end_date": "2026-02-01"
}

Response:
{
    "analysis_type": "holding_period",
    "raw_data": {...},        # 原始统计数据
    "ai_insights": "...",     # AI 生成的分析结论
    "created_at": "..."
}
```

**前端任务：**
- [ ] 在 Insights 页面新增 "AI 分析助手" 卡片
- [ ] 分析类型选择器（下拉菜单或 Tab）
- [ ] 日期范围选择器
- [ ] 分析结果展示（数据 + AI 结论）

### 5.2 各分析类型详细设计

#### 📊 持仓时间分析
```python
def analyze_holding_period(positions, db):
    # 分组：<1天, 1-3天, 3-7天, 1-2周, 2周+
    buckets = {"<1天": [], "1-3天": [], ...}
    for p in positions:
        duration = p.close_time - p.open_time
        bucket = get_bucket(duration)
        buckets[bucket].append(p.pnl_percent)
    
    stats = {bucket: {"win_rate": ..., "avg_pnl": ...} for bucket in buckets}
    
    # 调用 AI 生成结论
    ai_prompt = f"根据以下持仓时间分析数据: {stats}, 给出最佳持仓周期建议..."
    return {"raw_data": stats, "ai_insights": await call_llm(ai_prompt)}
```

#### 📉 连败模式分析
```python
def analyze_losing_streaks(positions):
    # 识别连续亏损序列
    streaks = []  # [(start_idx, length, total_loss), ...]
    
    # 分析连败前的共同特征
    common_patterns = {
        "high_emotion": ...,
        "missed_checklist": ...,
        "overtrading": ...
    }
    
    ai_prompt = f"分析以下连败模式: {streaks}, 共同特征: {common_patterns}..."
    return {"raw_data": {...}, "ai_insights": await call_llm(ai_prompt)}
```

#### 🧠 情绪-绩效关联矩阵
```python
def analyze_emotion_pnl(batches):
    # 按情绪分组: 兴奋/平静/焦虑/恐惧/贪婪
    emotion_stats = {}
    for batch in batches:
        emotion = batch.emotion or "未标记"
        emotion_stats[emotion]["trades"].append(batch.pnl)
    
    # 计算各情绪的胜率和平均盈亏
    matrix = {e: {"win_rate": ..., "avg_pnl": ...} for e in emotion_stats}
    
    ai_prompt = f"根据情绪-盈亏矩阵: {matrix}, 分析情绪对交易的影响..."
    return {"raw_data": matrix, "ai_insights": await call_llm(ai_prompt)}
```
## Phase 6 运维及测试任务

### 6.1 管理员端的设置项补充及开发
    现有管理员端可以设置 
        llm API key + endpoints
        Finnhub API
    运维端可以：
        备份数据库
        修改账户类型至管理员
        修改账户密码
---

## 完成状态统计

| Phase | 任务数 | 已完成 |
|-------|--------|--------|
| Phase 1 | 12 | 12 |
| Phase 2 | 10 | 0 |
| Phase 3 | 5 | 0 |
| Phase 4 | 7 | 0 |
| Phase 5 (AI 高级分析) | 10 | 0 |
| **总计** | **44** | **12** |

