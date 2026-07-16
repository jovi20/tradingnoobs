# 项目文件与结构审查整理

审查日期：2026-07-06
当前分支：`dev`
当前 HEAD：`b9d564d docs: add vps dev parallel deployment guide`

本文记录对当前仓库文件、目录职责、文档入口和可清理项的审查结果。目标是帮助后续开发快速定位代码边界，并避免在迁移期误删仍被使用的 legacy 路径。

## 总览

仓库是前后端分离结构，主要由四类内容组成：

| 路径 | 当前职责 | 整理判断 |
|------|----------|----------|
| `backend/` | FastAPI API、SQLAlchemy 模型、Alembic 迁移、业务服务、运维脚本和后端测试。 | 核心后端目录，结构基本清晰；`models.py` 仍是后续计划拆分点。 |
| `frontend/` | Next.js App Router、工作台页面、领域组件、adapter、内部 SVG 图表 renderer 和前端测试。 | 核心前端目录，页面和组件已按领域拆分；仍有少量 legacy DTO 边界需要继续收敛。 |
| `docs/` | 当前指南、执行清单、路线图、规格、runbook、发布和回滚记录。 | 已按“当前事实 + 后续计划 + 历史归档”整理；完成计划移入 `docs/superpowers/plans/archive/`。 |
| `.github/` | GitHub Actions 配置目录。 | 旧 `website/` GitHub Pages workflow 已删除；当前主应用尚未建立 CI/CD。 |

## 后端结构

| 路径 | 说明 |
|------|------|
| `backend/main.py` | FastAPI 入口，注册 router、CORS、observability 和错误处理。 |
| `backend/config.py` | Pydantic settings，读取 `.env` 和环境变量。 |
| `backend/database.py` | SQLAlchemy engine/session/base。 |
| `backend/models.py` | 当前集中模型定义；`docs/TODO.md` 已记录后续模块化计划。 |
| `backend/schemas.py` | Pydantic 请求/响应 schema。 |
| `backend/routers/` | API 路由层，覆盖 auth、accounts、positions、trading positions、timeline、insights、admin、market、risk 等。 |
| `backend/services/` | 业务逻辑层，覆盖 truth accounting、market data、jobs、outbox、idempotency、reports、risk、platform config 等。 |
| `backend/services/providers/` | 市场数据 provider adapter，当前含 AKShare、Binance、Finnhub。 |
| `backend/alembic/` | Alembic 迁移链，是 schema 演进主路径。 |
| `backend/ops/` | 回填和管理员脚本。 |
| `backend/tests/` | 后端回归和契约测试。 |

审查结论：

- 后端边界整体健康，router/service/test 分布清楚。
- `backend/models.py` 体量和职责仍偏集中，但这是已知迁移计划，不建议在本次整理中强拆。
- `backend/README.md` 原内容被截断，本次已重写为可用的后端入口文档。
- Alembic 配置存在，`ops/migrate_db.py` 已删除；新增 schema 变更只走 Alembic revision。

## 前端结构

| 路径 | 说明 |
|------|------|
| `frontend/app/` | Next.js App Router 页面入口。 |
| `frontend/components/` | 页面和领域组件，当前按 admin、charts、dashboard、import、insights、navigation、positions、risk、settings、timeline、ui 等分组。 |
| `frontend/lib/adapters/` | API DTO 到 read model / UI model 的 adapter 层。 |
| `frontend/lib/generated/` | 生成契约输出边界。 |
| `frontend/lib/api.ts` | 现有 API client；不建议继续扩张为永久 DTO 层。 |
| `frontend/tests/` | 前端 adapter、契约、图表、页面边界测试。 |
| `frontend/public/` | logo 等静态资源。 |

审查结论：

- 前端领域拆分较清楚，workbench、domain、adapter 层已经形成可维护边界。
- `frontend/lib/api.ts` 和 legacy trading DTO 边界仍需按 `docs/TODO.md` 继续收敛。
- `frontend/tsconfig.tsbuildinfo` 是 TypeScript incremental build 缓存；本次已补 `.gitignore`，并从版本跟踪中移除但保留本地文件。

## 文档结构

| 路径 | 说明 |
|------|------|
| `docs/README.md` | 文档索引和推荐阅读顺序。 |
| `docs/DEVELOPER_GUIDE.md` | 当前真实实现和开发入口。 |
| `docs/TODO.md` | 当前最小执行清单。 |
| `docs/project-summary-and-roadmap.md` | 当前项目描述、风险约束和后续路线图。 |
| `docs/superpowers/plans/` | 当前仍有效的后续参考计划。 |
| `docs/superpowers/plans/archive/` | 已完成或已收口的 P0-P19 阶段计划、checkpoint 和执行记录。 |
| `docs/superpowers/specs/` | 架构、契约和设计基线。 |
| `docs/*runbook*.md` / `docs/*playbook*.md` | 运维、发布、回滚和导出操作说明。 |

审查结论：

- 文档体系完整，但入口偏深；本次新增根目录 [../README.md](../README.md) 作为第一入口。
- `docs/README.md` 曾引用未跟踪的 `顶层设计.md`，本次改为明确标记“当前仓库未跟踪”。
- 2026-07-06 已新增 [project-summary-and-roadmap.md](./project-summary-and-roadmap.md)，并将已完成 P0-P19 阶段计划归档，避免旧计划继续显示为当前 active lane。

## 部署与脚本

| 文件 | 说明 | 审查结论 |
|------|------|----------|
| `start.sh` | macOS/Linux 本地启动脚本。 | 已重写，支持 backend-only、frontend-only、skip/force install、端口配置和端口占用检查。 |
| `docker-compose.yml` | PostgreSQL、backend、frontend、Caddy、backup 组合部署。 | 结构清晰；生产依赖 `SECRET_KEY`、`DOMAIN`、`DB_PASSWORD` 等环境变量。 |
| `Caddyfile` | 反向代理配置。 | 与 compose 配套。 |
| `.github/workflows/` | GitHub Actions workflow 目录。 | 旧 `website/` GitHub Pages workflow 已删除；后续如需 CI/CD，应新增真实 backend/frontend 检查或部署流程。 |

## 本次已整理

- 新增根目录 [../README.md](../README.md)，作为项目第一入口。
- 重写 [../backend/README.md](../backend/README.md)，补齐后端目录、运行、环境变量、迁移和测试说明。
- 新增 [../frontend/README.md](../frontend/README.md)，补齐前端目录、运行、命令和维护边界说明。
- 新增本文档，记录项目结构审查结果和后续整理建议。
- 更新 [README.md](./README.md)，加入结构审查文档入口，并修正 `顶层设计.md` 的失效链接描述。
- 更新 [../.gitignore](../.gitignore)，忽略 TypeScript build info 缓存。
- 将 `frontend/tsconfig.tsbuildinfo` 从版本跟踪中移除，但不删除本地文件。
- 重写并保留根目录本地启动脚本：`start.sh`。
- 按当前维护需求删除根目录冗余脚本：`start.ps1`、`backup_db.sh`、`update_libs.sh`。
- 删除过期脚本入口：`.github/workflows/deploy.yml`、`backend/ops/migrate_db.py`。
- 新增 [script-inventory.md](./script-inventory.md)，记录项目脚本必要性评估和后续维护规则。
- 整理 `docs/` 计划文件：当前入口保留 roadmap、TODO、legacy cutover inventory、model modularization plan；已完成 P0-P19 计划移入 `docs/superpowers/plans/archive/`。

## 建议后续清理项

| 优先级 | 项目 | 建议 |
|--------|------|------|
| P2 | `backend/models.py` | 等 truth/legacy 边界进一步稳定后，按既有 P10E 计划拆分模型并保留 re-export 兼容层。 |
| P2 | `frontend/lib/api.ts` | 继续收敛 legacy DTO 使用，把新页面绑定到 generated contracts 或 read-model adapters。 |
| P3 | 文档日期 | 只在实际变更时更新对应文档日期，避免全量机械刷新。 |

## 不建议本次移动的内容

- 不移动 `backend/models.py`：当前测试和导入路径依赖广，强拆风险高。
- 不删除 legacy positions 相关前端页面：仍是迁移期工具和 fallback 边界。
- 不删除本地 `frontend/tsconfig.tsbuildinfo` 文件：它是生成缓存，本次只移出版本跟踪。
