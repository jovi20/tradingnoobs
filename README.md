# Trading Noobs

Trading Noobs 是一个交易记录、复盘和分析系统。当前 `dev` 分支采用前后端分离结构：后端提供 FastAPI API、交易 truth model、异步任务和运维能力；前端提供 Next.js 工作台体验。

更新时间：2026-07-06
当前分支：`dev`

## 快速入口

| 入口 | 说明 |
|------|------|
| [docs/README.md](./docs/README.md) | 文档索引和推荐阅读顺序。 |
| [docs/DEVELOPER_GUIDE.md](./docs/DEVELOPER_GUIDE.md) | 当前真实实现、运行入口、模块边界和开发注意事项。 |
| [docs/project-summary-and-roadmap.md](./docs/project-summary-and-roadmap.md) | 项目描述、当前状态、风险约束和后续路线图。 |
| [docs/TODO.md](./docs/TODO.md) | 当前最小执行清单。 |
| [docs/project-structure-review.md](./docs/project-structure-review.md) | 2026-07-06 项目文件和结构审查整理记录。 |
| [backend/README.md](./backend/README.md) | 后端本地开发、迁移和测试说明。 |
| [frontend/README.md](./frontend/README.md) | 前端本地开发、目录结构和维护边界说明。 |

## 项目结构

```text
.
├── backend/          # FastAPI 后端、SQLAlchemy 模型、Alembic 迁移、服务和测试
├── frontend/         # Next.js 前端、页面、组件、adapter、图表 renderer 和测试
├── docs/             # 当前指南、计划、规格、runbook 和发布记录
├── .github/          # GitHub Actions 配置
├── docker-compose.yml
├── Caddyfile
└── start.sh          # macOS/Linux 本地启动
```

## 本地运行

一键启动前后端：

```bash
./start.sh
```

常用脚本参数：

```bash
./start.sh --skip-install
./start.sh --backend-only --backend-port 8001
```

手动启动后端：

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
alembic -c alembic.ini upgrade head
uvicorn main:app --reload
```

手动启动前端：

```bash
cd frontend
npm install
npm run dev
```

默认地址：

| 服务 | 地址 |
|------|------|
| 前端 | `http://localhost:3000` |
| 后端 | `http://localhost:8000` |
| OpenAPI | `http://localhost:8000/docs` |

## 验证命令

后端：

```bash
cd backend
python -m pytest -q
```

前端：

```bash
cd frontend
npm run lint
npx tsc --noEmit
```

## 维护约定

- 新 schema 变更以 Alembic 为主路径。
- 新前端功能优先走 read-model adapter，不继续扩大 legacy DTO 边界。
- 当前真实实现以 [docs/DEVELOPER_GUIDE.md](./docs/DEVELOPER_GUIDE.md) 为准。
- 当前下一步工作以 [docs/TODO.md](./docs/TODO.md) 为准。
