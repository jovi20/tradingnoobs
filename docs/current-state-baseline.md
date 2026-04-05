# 当前项目基线（2026-04-05）

> 用途：作为后续架构讨论前的“现状基线”。先回答现在做到了什么、没做到什么、做得好的地方和做得不好的地方，避免把未来设想和当前实现混在一起。

---

## 1. 一句话结论

- `Trading Noobs` 当前已经是一个可用的全栈交易日志与分析产品雏形，不是只停留在页面或接口层的 demo。
- 现阶段更适合定义为“你统一托管的 B2C 个人交易者产品基础版”。
- 距离“高可用、可持续迭代、可商用首发”仍有明显差距，主要短板在工程化、迁移规范、测试、图表扩展方式、市场数据中间层、AI 中台和配置治理。

---

## 2. 已确认已落地的能力

| 能力域 | 当前状态 | 代码与入口 | 备注 |
|--------|----------|------------|------|
| 用户认证 | `已实现` | `backend/routers/auth.py`、`frontend/app/login/page.tsx`、`frontend/app/register/page.tsx` | 支持注册、登录、JWT、当前用户读取 |
| 账户与资金流水 | `已实现` | `backend/routers/accounts.py`、`backend/routers/transactions.py`、`frontend/app/settings/page.tsx`、`frontend/app/settings/accounts/[id]/page.tsx` | 支持账户 CRUD、资金流水、NAV 相关展示 |
| 持仓与批次 | `已实现` | `backend/routers/positions.py`、`frontend/app/positions/*` | 支持建仓、加减仓、平仓、详情页、批次操作、CSV 导出 |
| 策略与检查清单 | `部分实现` | `backend/routers/strategies.py`、`frontend/app/strategies/page.tsx` | 策略 CRUD 和开仓检查清单已落地，但部分列表/看板展示未补齐 |
| 每日页与随笔 | `已实现` | `backend/routers/daily.py`、`backend/routers/journal.py`、`frontend/app/daily/page.tsx` | `Journal` 能力已经集成在 `Daily` 页面中，不是独立前端页面 |
| Dashboard 绩效分析 | `部分实现` | `backend/routers/dashboard.py`、`frontend/app/page.tsx`、`frontend/components/dashboard/*` | 核心统计、Sharpe/Sortino/Calmar、Max Drawdown、MAE/MFE、Sankey 已有，但风险预警未形成独立体系 |
| AI 洞察与分析助手 | `部分实现` | `backend/routers/insights.py`、`backend/services/llm_service.py`、`frontend/app/insights/page.tsx` | 周报、摘要、分析助手、结果持久化已实现；筛选和工程化能力不足 |
| 行情与资产识别 | `已实现` | `backend/services/market_data_service.py`、`backend/services/providers/*`、`backend/routers/market.py` | 已支持多市场行情、历史数据、资产元数据识别和部分回退 |
| 导入导出 | `部分实现` | `backend/services/import_service.py`、`backend/routers/positions.py`、`frontend/app/positions/import/page.tsx` | CSV/Excel 导入与 CSV 模板下载已做，PDF 报告未做 |
| 管理员系统设置 | `部分实现` | `backend/routers/admin.py`、`frontend/app/settings/page.tsx` | 系统级 LLM / Finnhub 配置与 LLM 测试已做，仍缺成熟后台能力 |
| 部署与基础运维 | `部分实现` | `docker-compose.yml`、`Caddyfile`、`backup_db.sh`、`backend/ops/manage_users.py`、`start.sh`、`start.ps1` | 已有 Docker Compose、Caddy、PostgreSQL 备份容器、本地启动脚本、CLI 用户管理，但缺正式运维面板和主应用 CI |

---

## 3. 已确认未完成或明显缺失的能力

| 主题 | 当前判断 | 说明 |
|------|----------|------|
| 风控预警系统 | `未实现` | 没有独立风险服务、预警配置、告警日志、WebSocket 通知链路 |
| PDF 报告导出 | `未实现` | 导出能力仍停留在 CSV |
| AI 计费与额度体系 | `未实现` | 没有套餐、配额、调用计量、成本核算、账单能力 |
| Prompt 管理与版本化 | `未实现` | Prompt 仍主要硬编码在 `backend/services/llm_service.py` |
| AI 任务队列 | `未实现` | 没有异步任务、重试、限流、缓存层和失败补偿 |
| 图表扩展规范 | `未实现` | 图表数据结构仍偏页面/组件定制，新增图表成本较高 |
| 正式迁移体系 | `未实现` | 运行时依赖 `Base.metadata.create_all()`，仓库虽安装 Alembic，但没有维护中的迁移链 |
| 自动化测试体系 | `未实现` | 仓库中没有面向主应用的后端/前端测试目录；现有 `docs/test/*` 更像手工验证脚本 |
| 主应用 CI/CD | `未实现` | `.github/workflows/deploy.yml` 只服务 `website/`，不覆盖当前前后端主应用 |
| 移动端 / App | `未实现` | 当前只有 Web 前端，没有 App 客户端或面向 App 的 API 契约层 |
| 可观测性 | `未实现` | 没有成体系的结构化日志、告警、指标、链路追踪 |

---

## 4. 当前做得比较好的地方

### 4.1 业务主链路已经成形

- 不是“只有表结构”或“只有 UI”，而是前后端贯通了认证、账户、持仓、策略、日报、AI 分析、行情接入和导入导出。
- 对后续架构升级来说，这是很好的基础，因为我们讨论的是“如何把现有产品做稳做清晰”，不是从零搭空中楼阁。

### 4.2 领域建模已经有一定深度

- `Position` + `TradeBatch` + `TradingAccount` + `DailySnapshot` + `AssetMetadata` 这组模型已经比普通 CRUD 项目更贴近交易日志真实业务。
- 后续做风控、回测、组合分析、AI 复盘时，有可复用的数据骨架。

### 4.3 市场数据接入已经有“抽象雏形”

- 行情接入虽然还不够干净，但已经从单一脚本式调用进化到 `MarketDataService + providers/*` 的结构。
- 文档里也专门维护了 [market_data_sources.md](./market_data_sources.md)，这比完全隐式的实现要好很多。

### 4.4 文档意识优于很多同阶段项目

- `DEVELOPER_GUIDE.md`、`market_data_sources.md`、`trading-fields-design.md`、`TODO.md` 已经形成了主文档 + 附录 + 清单的雏形。
- 文档里已经在努力区分“当前已实现”和“未来规划”，这一点值得保留。

### 4.5 部署和本地开发入口已具备基本可用性

- 本地有 `start.sh` / `start.ps1`，线上有 `docker-compose.yml` + `Caddyfile` + `db-backup`。
- 这意味着项目不是只能在作者机器上手动跑起来，已经具备初级交付能力。

---

## 5. 当前做得不好的地方与主要风险

### 5.1 核心能力集中在少数超大文件

下面这些文件已经是明显的架构热点：

| 文件 | 约行数 | 当前问题 |
|------|--------|----------|
| `backend/routers/positions.py` | `1042` | 同时承载列表、详情、创建、批次、分析、导入、导出，多种职责混杂 |
| `backend/routers/dashboard.py` | `669` | 聚合统计、Sankey 组装、快照写入、风险指标混在一个 router 中 |
| `backend/services/market_data_service.py` | `554` | Provider 路由、缓存、元数据补全、LLM 调用、历史数据查询耦合在一起 |
| `backend/services/llm_service.py` | `517` | Prompt、供应商请求、响应解析、不同 AI 用例都堆在同一服务里 |
| `frontend/app/settings/page.tsx` | `674` | 用户设置、管理员设置、账户入口、LLM 测试混在一个页面 |
| `frontend/app/positions/[id]/page.tsx` | `887` | 详情展示、交易批次、分析逻辑集中，后续继续扩展会越来越难维护 |
| `frontend/app/daily/page.tsx` | `614` | 日历、交易汇总、随笔、市场日历合并在同一页面组件 |

这类大文件不是“代码多”本身的问题，而是说明职责边界已经不清晰，后续每加一个功能都更容易牵一发而动全身。

### 5.2 图表层仍然是“接口直连图表库”的做法

- 例如 Sankey 的节点/边数据直接在 `backend/routers/dashboard.py` 中按 Recharts 需要的结构拼装。
- 这会导致“新增一个图，就要从后端聚合、接口结构、前端组件到视觉调试全部重来”，复用性很弱。
- 目前缺少独立的图表数据 schema、图表适配层、图表注册机制。

### 5.3 市场数据层已经出现“服务过胖”

- `MarketDataService` 目前同时负责：
  - 代码模式识别
  - Provider 路由
  - 缓存
  - 资产元数据写入
  - LLM 富分类
  - 历史数据查询
- 这说明它已经不只是“统一入口”，而是开始承担中台、缓存层和业务规则层的混合职责。

### 5.4 AI 相关结构还停留在功能堆叠阶段

- Prompt 硬编码在 `backend/services/llm_service.py`
- 同类配置读取逻辑反复出现
- 目前没有：
  - Prompt 模板目录
  - Prompt 版本管理
  - LLM 供应商抽象
  - 统一 AI 调用审计
  - 使用量统计与成本控制
  - 异步任务与失败重试

如果后面 AI 是付费点，这一层会很快变成系统最关键、也是最脆弱的部分。

### 5.5 数据库演进方式还不适合商用阶段

- `backend/main.py` 启动时直接执行 `Base.metadata.create_all(bind=engine)`
- 仓库里有 `backend/ops/migrate_db.py`，但它是手写式增量脚本，不是正式迁移链
- `backend/requirements.txt` 已安装 `alembic`，但仓库内没有持续维护的 Alembic 迁移目录和版本历史

这意味着：
- 开发期还凑合
- 一旦进入正式上线、多人协作、回滚和审计需求，风险会快速放大

### 5.6 配置边界还不够清楚

- 当前配置分散在环境变量、`SystemSetting`、`UserSettings` 三层
- 某些能力已经开始做分层，例如系统级 `finnhub_api_key` 与 `llm_*`
- 但整体上仍然缺少“哪些配置属于平台、哪些属于用户、哪些只允许环境变量”的统一规则

### 5.7 工程化保障明显不足

- 主应用没有 CI
- 没有主应用自动化测试
- 没有结构化日志
- 代码中仍存在较多 `print(...)`、宽泛 `except:`、静默吞错

这些问题在单人本地开发阶段还能忍，一旦进入线上托管、个人用户真实使用、AI 计费和数据可靠性要求提升，就会成为高风险点。

---

## 6. 本次审计后确认并修正的文档认知

- 前端实际页面不仅有 `positions/[id]`，还包括：
  - `frontend/app/positions/[id]/add-batch/page.tsx`
  - `frontend/app/settings/accounts/[id]/page.tsx`
- `Journal` 能力并不是缺前端，而是集成在 `frontend/app/daily/page.tsx` 中。
- 仓库已经有基础运维脚本：
  - `backend/ops/manage_users.py`
  - `backup_db.sh`
- `backend/.env.example` 当前是存在的，只是内容仍偏最小化开发配置。
- GitHub Actions 当前只有 `website/` 的部署工作流，不代表主应用已经接入 CI/CD。

---

## 7. 适合后续架构讨论的切分方式

基于这次审计，后续架构讨论继续沿这 4 条线拆分是合理的：

1. `平台基础架构`
   用户、权限、设置中心、管理员入口、审计、日志、部署与高可用
2. `市场数据中台`
   多供应商抽象、统一领域模型、缓存、回退、给交易日志与未来回测共用
3. `图表与分析架构`
   图表 schema、数据适配层、组件规范，解决“每新增一个图就全链路重调”
4. `AI 能力中台`
   LLM 抽象、Prompt 管理、任务队列、缓存、计量、付费能力

如果按当前痛点和收益比排序，建议优先讨论：

1. `市场数据中台`
2. `图表与分析架构`
3. `AI 能力中台`
4. `平台基础架构`

原因不是平台基础不重要，而是 2 和 3 已经直接影响你现在继续开发的效率，能最快减少后续技术债。
