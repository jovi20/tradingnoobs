# Trading Noobs 当前代码库指南

本文档用于描述当前代码库的真实实现、运行入口、模块现状与附录索引，不再承担“目标架构设计稿”的职责。

文档约定：
- [superpowers/specs/2026-04-06-platform-foundation-design.md](./superpowers/specs/2026-04-06-platform-foundation-design.md) 是当前唯一目标架构来源。
- 本文档是当前代码实现与运行方式的说明。
- [current-state-baseline.md](./current-state-baseline.md) 是 2026-04-05 的历史审计基线，不再作为长期主真相来源持续维护。
- [TODO.md](./TODO.md) 是唯一执行清单，只记录任务状态与阶段。
- 专题细节拆分到附录：
  - [market_data_sources.md](./market_data_sources.md)
  - [trading-metrics.md](./trading-metrics.md)
  - [trading-fields-design.md](./trading-fields-design.md)
- [顶层设计.md](./顶层设计.md) 已降级为历史草案，不再作为当前方案依据。

---

## 1. 项目定位与文档约定

`Trading Noobs` 是一个面向交易者的交易日志、复盘与分析系统，当前代码库已经覆盖以下主线能力：
- 多账户交易记录与持仓管理
- 策略管理与交易前检查清单
- 看板统计、MAE/MFE、风险调整收益指标
- AI 周报、随笔摘要与分析助手
- 多市场行情接入与资产元数据识别
- CSV/Excel 导入、CSV 导出、管理员系统设置

本文档默认读者是项目内部开发者。目标不是介绍产品卖点，而是帮助开发者快速回答以下问题：
- 系统现在到底实现到了哪里
- 每个模块由哪些后端路由和前端页面承载
- 数据模型的边界是什么
- 行情、指标、字段设计应该去看哪份附录
- 本地开发和部署入口在哪里

---

## 2. 技术架构与目录职责

### 2.1 技术栈

| 层级 | 当前实现 |
|------|----------|
| 前端 | Next.js 14, React 18, TypeScript, Tailwind CSS, React Query, Recharts |
| 后端 | FastAPI, SQLAlchemy, Pydantic |
| 数据库 | 开发默认 SQLite，部署默认 PostgreSQL |
| 外部服务 | Finnhub, AKShare, Binance, 可配置 OpenAI 兼容 LLM 接口 |
| 部署 | Docker Compose + Caddy |

### 2.2 关键目录

| 路径 | 职责 |
|------|------|
| `backend/main.py` | 后端入口，注册所有 FastAPI router |
| `backend/routers/` | API 路由层，定义接口边界 |
| `backend/services/` | 业务逻辑层，如行情、导入、指标、AI 分析 |
| `backend/models.py` | SQLAlchemy 持久化模型 |
| `backend/schemas.py` | Pydantic 请求/响应模型 |
| `frontend/app/` | Next.js App Router 页面入口 |
| `frontend/components/` | 页面复用组件 |
| `frontend/lib/api.ts` | 前端 API 封装与共享类型 |
| `docs/` | 内部文档、路线图与专题附录 |

### 2.3 运行时结构

后端当前注册的主要路由：
- `/api/auth`
- `/api/accounts`
- `/api/positions`
- `/api/strategies`
- `/api/dashboard`
- `/api/insights`
- `/api/journal`
- `/api/daily`
- `/api/settings`
- `/api/admin`
- `/api/market`
- `/api/accounts/{account_id}/transactions`

前端当前主要页面：
- `/` 看板
- `/positions` 持仓列表
- `/positions/[id]` 持仓详情
- `/positions/[id]/add-batch` 持仓加仓 / 平仓
- `/positions/new` 新建持仓
- `/positions/import` 批量导入
- `/strategies` 策略管理
- `/insights` AI 洞察
- `/daily` 每日总结 + 随笔
- `/settings` 设置总入口
- `/settings/accounts/[id]` 账户详情与资金流水
- `/login` / `/register`

---

## 3. 核心业务模块现状

状态定义：
- `已实现`：代码和基础前后端流程已经落地，可直接使用
- `部分实现`：主链路已存在，但仍缺关键展示、扩展能力或可配置项
- `规划中`：已进入 TODO，但仓库中尚无完整能力

| 模块 | 状态 | 当前说明 |
|------|------|----------|
| 认证与用户基础 | `已实现` | 注册、登录、JWT 鉴权、当前用户信息读取 |
| 交易账户与资金记录 | `已实现` | 账户 CRUD、实时 NAV 计算、账户交易流水 |
| 持仓与批次管理 | `已实现` | 建仓、加减仓、平仓、持仓详情、批次记录、导出 CSV |
| 策略与检查清单 | `部分实现` | 策略 CRUD、检查清单编辑与开仓确认已完成；部分列表/看板展示仍待补 |
| 计划偏移与执行质量 | `已实现` | 计划入场/止损/止盈、偏移分析、详情页展示 |
| Dashboard 与绩效分析 | `部分实现` | 核心看板、Sharpe/Sortino/Calmar、Max Drawdown、MAE/MFE 已完成；组合风险与预警未完成 |
| Journal / Daily / AI Summary | `已实现` | 随笔已集成到 `Daily` 页面中，每日总结与 AI 摘要主流程已落地 |
| Insights / AI 分析助手 | `部分实现` | 周报、分析助手、结果持久化已实现；日期范围选择器仍缺 |
| 市场数据与资产识别 | `已实现` | A 股 / 港股 / 美股 / Crypto / 外汇 / 基金的行情查询与资产元数据识别已接入 |
| 批量导入导出 | `部分实现` | CSV/Excel 导入与 CSV 模板下载已实现；PDF 导出未完成 |
| 管理员系统设置 | `部分实现` | 系统级 LLM / Finnhub 设置、LLM 连通性测试已实现；CLI 运维脚本已存在，但后台运维能力仍不足 |
| 风控预警系统 | `规划中` | Phase 3 目标，尚未形成独立服务与前端展示 |

### 3.1 当前已落地的核心实现

- `Positions`
  - 路由：`backend/routers/positions.py`
  - 页面：`frontend/app/positions/*`
  - 关键能力：持仓汇总、批次追加、计划偏移分析、MAE/MFE 分析、导入导出
- `Dashboard`
  - 路由：`backend/routers/dashboard.py`
  - 页面：`frontend/app/page.tsx`
  - 关键能力：资产分布、收益统计、风险调整收益指标、权益曲线、MAE/MFE 图表
- `Insights`
  - 路由：`backend/routers/insights.py`
  - 页面：`frontend/app/insights/page.tsx`
  - 关键能力：周报生成、AI 摘要、分析助手、分析结果缓存与持久化
- `Market Data`
  - 服务：`backend/services/market_data_service.py`
  - Provider：`backend/services/providers/*`
  - 关键能力：行情路由、缓存、回退、资产元数据探测

### 3.2 当前主要未完成项

以 [TODO.md](./TODO.md) 为准，当前开发重心仍集中在：
- Phase 3：组合风险监控、单日亏损上限、实时预警
- Phase 4：PDF 报告导出
- Phase 5：AI 分析助手的日期范围选择与进一步完善
- Phase 6：管理员运维能力补齐

---

## 4. 数据模型与关键接口边界

完整字段请以 [trading-fields-design.md](./trading-fields-design.md)、`backend/models.py`、`backend/schemas.py` 为准。这里仅描述当前实现的核心边界，避免把未来设计误当成现状。

### 4.1 当前核心实体

| 实体 | 当前作用 |
|------|----------|
| `User` | 用户主体，关联策略、账户、持仓、周报、设置 |
| `TradingAccount` | 交易账户标签，存放券商、币种、初始资金、现金余额 |
| `Transaction` | 账户层资金流水，如入金、出金、费用、利息 |
| `Strategy` | 策略定义，包含规则文本与 `checklist_items` |
| `Position` | 持仓汇总记录，承载方向、状态、计划价、复盘信息、MAE/MFE |
| `TradeBatch` | 单笔建仓/加仓/减仓/平仓批次，包含情绪、原因、信心、退出 PnL |
| `AssetMetadata` | 资产元数据，承载市场、核心类型、币种、风险级别等 |
| `DailySnapshot` | 每日权益快照，为 PnL 历史和部分风险指标提供基础 |
| `DailySummary` | 每日总结 |
| `JournalEntry` | 用户随笔 |
| `AISummary` | AI 周度摘要结果 |
| `WeeklyReport` | AI 周报 |
| `AIAnalysisResult` | AI 分析助手结果缓存与持久化 |
| `UserSettings` | 用户级显示与 API 偏好设置 |
| `SystemSetting` | 管理员级全局设置，如 LLM/Finnhub Key |

### 4.2 当前 API 边界

当前更适合作为系统边界理解的接口：
- `POST /api/positions`
  - 创建持仓，并同时写入首个 entry batch
  - 支持策略、检查清单、计划价格
- `POST /api/positions/{id}/batches`
  - 追加交易批次，驱动持仓状态和已实现盈亏变化
- `GET /api/dashboard/stats`
  - 返回首页看板聚合统计与风险调整指标
- `POST /api/insights/analyze`
  - 返回高级分析结果，并持久化到 `AIAnalysisResult`
- `POST /api/positions/import/upload`
  - 解析 CSV/Excel 并生成预览
- `POST /api/positions/import/confirm`
  - 按选中行正式写入持仓与批次

### 4.3 当前设计边界

- 当前系统的“持仓”是聚合概念，真实的成交行为通过 `TradeBatch` 承载。
- 当前风险指标以 Dashboard 聚合计算为主，还没有独立的风险快照表或预警表实现。
- 当前分析助手已经有结果持久化，但还不是完整分析平台；它依赖现有持仓和批次数据。
- 字段附录中涉及的账户风险表、相关性矩阵表、预警表属于未来设计，不代表已落库。

---

## 5. 市场数据接入概览

详细 provider 说明请查看 [market_data_sources.md](./market_data_sources.md)。这里只保留开发中最常用的概览。

| 资产类别 | 当前主来源 | 主要配置 | 当前说明 |
|----------|------------|----------|----------|
| A 股 | AKShare | 无需 Key | 主要通过 `akshare_provider.py` 获取，必要时回退 YFinance |
| 港股 | AKShare / akshare-one | 无需 Key | 5 位港股代码或 HK 交易所路由到港股逻辑 |
| 美股 | Finnhub | `SystemSetting.finnhub_api_key` | 主来源为 Finnhub，部分历史/兜底逻辑会使用 YFinance |
| 加密货币 | Binance | 公共行情无需 Key | `binance-connector` 获取 ticker 与 K 线 |
| 基金 | AKShare | 无需 Key | ETF、LOF、场外基金按代码模式和 AKShare 接口处理 |
| 外汇 | AKShare | 无需 Key | 6 位字母对默认识别为外汇，存在回退逻辑 |
| 资产元数据 | 规则 + LLM | `SystemSetting.llm_*` | 用于补全 `AssetMetadata`，不是行情主来源 |

开发时需要注意：
- `MarketDataService` 内部有 60 秒级缓存。
- AKShare provider 会主动清理代理环境变量，避免访问国内源异常。
- Finnhub Key 读取自系统设置，不是用户设置。
- 行情接入说明必须与代码实现保持一致，禁止在文档中写“理想供应商”。

---

## 6. 开发环境与本地启动

### 6.1 前置要求

- Python 3.10+
- Node.js 18+
- npm
- 可选：Docker / Docker Compose

### 6.2 推荐启动方式

Windows 推荐直接使用根目录脚本：

```powershell
./start.ps1
```

Linux / macOS 可参考：

```bash
./start.sh
```

`start.ps1` 会做这些事情：
- 检查 Python 与 Node
- 自动创建 `backend/venv`
- 安装后端依赖
- 如果 `backend/.env` 不存在则自动创建默认开发配置
- 安装前端依赖
- 分别启动后端和前端

### 6.3 手动启动方式

后端：

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

前端：

```bash
cd frontend
npm install
npm run dev
```

默认访问地址：
- 前端：`http://localhost:3000`
- 后端：`http://localhost:8000`
- OpenAPI：`http://localhost:8000/docs`

### 6.4 本地配置说明

后端配置入口：`backend/config.py`

当前最常用环境变量：
- `DATABASE_URL`
- `SECRET_KEY`
- `CORS_ORIGINS`
- `LLM_API_URL`
- `LLM_API_KEY`
- `LLM_MODEL`

注意：
- 仓库当前有 `backend/.env.example`，但内容仍偏最小化开发配置；生产环境仍应以显式环境变量或部署配置为准。
- 生产环境变量更多由 `docker-compose.yml` 注入。
- 当前数据库 schema 主要由 `Base.metadata.create_all()` 和 `backend/ops/migrate_db.py` 维护；虽然依赖中已安装 `alembic`，但仓库内还没有稳定维护的 Alembic 迁移链。

### 6.5 部署入口

主部署入口仍然是：
- `docker-compose.yml`
- `Caddyfile`

当前文档范围不展开详细运维手册，仅保留这两个事实：
- 生产默认使用 PostgreSQL
- Caddy 负责统一对外暴露前后端服务

---

## 7. 当前开发状态与路线图

执行细节以 [TODO.md](./TODO.md) 为准，这里只保留阶段级摘要，避免维护第二套路线图。

| 阶段 | 当前状态 | 说明 |
|------|----------|------|
| Phase 1 交易规划模块 | `部分完成` | 后端、开仓清单、计划偏移已落地；部分列表/看板展示待补 |
| Phase 2 绩效分析增强 | `已实现` | 风险调整收益指标和 MAE/MFE 已进入主流程 |
| Phase 3 风控预警系统 | `规划中` | 尚未建立风险预警服务与前端面板 |
| Phase 4 数据导入导出 | `部分完成` | CSV/Excel 导入已完成，PDF 导出未做 |
| Phase 5 AI 高级分析中心 | `部分完成` | 分析助手主链路已落地，仍需补日期范围等体验层功能 |
| Phase 6 运维及测试任务 | `规划中` | 管理员运维能力与配套测试仍需梳理 |

路线图使用规则：
- 是否已完成，以代码和 `TODO.md` 勾选项共同判断
- 本文档不维护独立任务数量
- 任何新增 Phase 或模块，先更新 `TODO.md`，再同步本节摘要

---

## 8. 文档索引与附录链接

建议阅读顺序：
1. [superpowers/specs/2026-04-06-platform-foundation-design.md](./superpowers/specs/2026-04-06-platform-foundation-design.md)：目标架构与设计结论
2. 本文档：当前代码实现、现状与开发入口
3. [TODO.md](./TODO.md)：当前任务与阶段状态
4. [market_data_sources.md](./market_data_sources.md)：当前行情接入与 provider 说明
5. [trading-metrics.md](./trading-metrics.md)：指标算法与实现状态
6. [trading-fields-design.md](./trading-fields-design.md)：当前 / 实施中的字段边界

维护原则：
- `spec` 负责“目标架构与未来设计”
- 本文档负责“当前真实实现与运行方式”
- `TODO` 负责“当前要做什么”
- 附录负责“专题细节”
- 历史基线只保留背景与审计价值
