# 项目脚本清单与必要性评估

更新时间：2026-07-06
当前分支：`dev`

本文记录仓库内仍保留的启动、部署、运维、构建和后台任务入口，以及本轮已经删除的过期脚本。后续新增脚本前，应先确认它是否比现有 Docker Compose、npm scripts、Alembic 或后端 CLI 更合适。

## 结论摘要

| 类别 | 文件或入口 | 结论 |
|------|------------|------|
| 本地启动 | `start.sh` | 保留。面向 macOS/Linux 本地开发，统一启动前后端。 |
| 容器部署 | `docker-compose.yml`、`Caddyfile`、`backend/Dockerfile`、`frontend/Dockerfile` | 保留。当前 VPS / staging 部署主路径。 |
| 前端命令 | `frontend/package.json` scripts | 保留。Next.js 标准开发、构建、运行、检查入口。 |
| 后台任务 | `backend/job_worker_cli.py`、`backend/outbox_relay_cli.py` | 保留。和 job / outbox 服务、测试绑定。 |
| 运维 CLI | `backend/ops/manage_users.py` | 保留。VPS 与管理员 runbook 仍需要用户创建、晋升、重置密码等能力。 |
| 数据回填 | `backend/ops/backfill_trading_truth.py` | 保留。legacy/truth 迁移期仍需要一次性或定向回填。 |
| 数据迁移 | `backend/alembic/` | 保留。schema 演进唯一主路径。 |
| 手写迁移 | `backend/ops/migrate_db.py` | 已删除。和 Alembic 职责冲突，且包含历史 ALTER TABLE 片段。 |
| 旧前端发布 | `.github/workflows/deploy.yml` | 已删除。指向不存在的 `website/` 目录。 |
| 根目录旧脚本 | `start.ps1`、`backup_db.sh`、`update_libs.sh` | 已删除。当前维护路径不再依赖它们。 |

## 保留脚本

### `start.sh`

保留原因：

- 是本地开发最短路径，适合快速拉起 backend 和 frontend。
- 已支持只启动后端、只启动前端、跳过依赖安装、强制安装依赖、端口调整和端口占用检查。
- 只面向本地开发，不承担生产部署职责。

维护规则：

- 新增本地启动能力优先扩展 `start.sh`，不要再散落新的根目录启动脚本。
- Windows 启动脚本暂不维护；需要时优先用 Docker Compose 或手动进入 `backend/`、`frontend/` 执行命令。

### Docker / Compose / Caddy

保留文件：

- `docker-compose.yml`
- `Caddyfile`
- `backend/Dockerfile`
- `frontend/Dockerfile`

保留原因：

- 这是当前部署和 dev/staging 验证主路径。
- Compose 已包含 PostgreSQL、backend、frontend、Caddy 和数据库备份容器。
- Caddy 和两个 Dockerfile 与 Compose 配套，不能单独删除。

维护规则：

- 生产或 VPS 相关变更优先收敛到 Compose、Caddy 和环境变量文档。
- 如后续引入 CI/CD，应新增真实 backend/frontend 检查或部署 workflow，不恢复旧 `website/` workflow。

### `frontend/package.json` scripts

保留命令：

- `npm run dev`
- `npm run build`
- `npm run start`
- `npm run lint`

保留原因：

- 都是 Next.js 项目的标准入口。
- `start.sh`、Dockerfile 和验证流程都会间接依赖这些命令。

维护规则：

- 新增前端检查命令时，优先放在 `package.json`，再由文档引用。
- 不把长串一次性命令写成新的根目录 shell 脚本。

### 后端后台任务 CLI

保留文件：

- `backend/job_worker_cli.py`
- `backend/outbox_relay_cli.py`

保留原因：

- 分别服务于 job queue 和 transactional outbox。
- 已有测试覆盖，是后台任务本地调试、手动补偿和未来部署 worker 的基础入口。

维护规则：

- 后续如果部署常驻 worker，应复用这两个 CLI，而不是复制业务逻辑到新的 shell 脚本。

### 后端运维与回填 CLI

保留文件：

- `backend/ops/manage_users.py`
- `backend/ops/backfill_trading_truth.py`

保留原因：

- `manage_users.py` 仍用于管理员用户创建、晋升、密码重置和账号启停。
- `backfill_trading_truth.py` 仍用于 legacy positions 到 truth tables 的迁移回填。

维护规则：

- 这类脚本必须保持幂等或可重复执行边界清楚。
- 执行前应确认目标数据库环境，避免误操作生产数据。

### Alembic 迁移链

保留路径：

- `backend/alembic/`

保留原因：

- 当前 schema 演进主路径。
- 已有迁移链测试覆盖。

维护规则：

- 新 schema 变更必须新增 Alembic revision。
- 不再维护手写 `ALTER TABLE` 聚合迁移脚本。

## 已删除脚本与入口

| 文件 | 删除原因 | 替代方式 |
|------|----------|----------|
| `.github/workflows/deploy.yml` | 发布不存在的 `website/` 目录，和当前 Next.js frontend/backend 结构不匹配。 | 后续需要 CI/CD 时新增真实 workflow。 |
| `backend/ops/migrate_db.py` | 手写历史迁移和 Alembic 冲突，容易绕过 revision chain。 | 使用 `backend/alembic/`。 |
| `start.ps1` | Windows 本地启动入口无人维护，容易和 `start.sh` 行为分叉。 | Docker Compose 或手动执行前后端命令。 |
| `backup_db.sh` | 备份职责已由 Compose 中 `db-backup` 服务和管理员备份能力覆盖。 | Compose backup service / admin runbook。 |
| `update_libs.sh` | VPS 手动 rebuild 辅助脚本，不是当前稳定运维路径。 | 显式执行部署步骤或后续建立 CI/CD。 |

## 后续脚本整理规则

- 根目录只保留真正跨项目的一线入口。
- schema 变更只走 Alembic，不再新增手写迁移聚合脚本。
- 生产部署优先使用 Docker Compose / Caddy；临时 VPS 命令写进 runbook，而不是默认放入根目录。
- 若脚本只服务一次性迁移，完成后应移动到归档文档或删除，并在本清单更新状态。
- 新增 GitHub Actions 前，应确认它服务当前 `backend/`、`frontend/` 或 Compose 流程。
