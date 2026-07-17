# VPS Dev Parallel Deployment Guide

更新时间：2026-06-11
目标分支：`dev`

本文档说明如何在已经部署 `main` 的同一台 VPS 上，再部署一个独立的 `dev` staging 环境。核心原则是：**目录、容器、数据库、volume、域名和环境变量全部隔离，只共用同一台 VPS 和一个公网反向代理入口**。

---

## 1. 推荐拓扑

假设当前线上 `main` 已经运行：

- 代码目录：`/opt/tradingnoobs`
- 域名：`app.example.com`
- Compose project：现有默认或 `tradingnoobs`
- Caddy 已占用 VPS 的 `80/443`

新增 `dev` staging：

- 代码目录：`/opt/tradingnoobs-dev`
- 域名：`dev.example.com`
- Compose project：`tradingnoobs-dev`
- 数据库：独立 Postgres 容器和独立 volume
- 前后端：独立容器
- 入口：复用现有 main Caddy，不启动第二个绑定 `80/443` 的 Caddy

为什么不直接复制后 `docker compose up -d`：

- 当前 `docker-compose.yml` 写死了 `container_name`，复制后会和 main 的 `tradingnoobs-backend`、`tradingnoobs-db` 等冲突。
- 当前 `caddy` 服务绑定 `80:80` 和 `443:443`，同一台 VPS 不能同时启动两个监听同一端口的 Caddy。
- main 与 dev 必须使用不同 Postgres volume，不能共享生产数据库。

---

## 2. DNS 和前置网络

1. 给 dev 域名添加 DNS A 记录，指向同一台 VPS：

```text
dev.example.com -> <VPS_PUBLIC_IP>
```

2. 在 VPS 上创建一个给 main Caddy 和 dev app 共享的 Docker 网络：

```bash
docker network create tradingnoobs-edge || true
```

3. 把现有 main Caddy 容器接入这个 edge 网络：

```bash
docker network connect tradingnoobs-edge tradingnoobs-caddy || true
```

注意：如果以后重建 main Caddy 容器，这个 network connect 可能需要重新执行。更稳的做法是在 main 的 compose 文件里把 `caddy` 长期加入 `tradingnoobs-edge` external network。

---

## 3. 拉取 dev 代码

```bash
cd /opt
git clone https://github.com/jovi20/tradingnoobs.git tradingnoobs-dev
cd /opt/tradingnoobs-dev
git checkout dev
git pull origin dev
```

如果目录已存在：

```bash
cd /opt/tradingnoobs-dev
git fetch origin
git checkout dev
git pull --ff-only origin dev
```

---

## 4. 创建 dev 专用 `.env`

在 `/opt/tradingnoobs-dev/.env` 写入独立配置：

```bash
DOMAIN=dev.example.com
DB_PASSWORD=<dev-only-strong-password>
SECRET_KEY=<dev-only-random-secret>
DEPLOYMENT_CAPABILITY_ALLOWLIST=
```

要求：

- `DB_PASSWORD` 不要复用 main。
- `SECRET_KEY` 不要复用 main，否则 token/cookie 边界会混乱。
- 交易日志 Beta 的 capability allowlist 必须保持为空，不配置或注入 Market、Broker、AI 等 provider secret。

---

## 5. 创建 dev override 文件

在 `/opt/tradingnoobs-dev/docker-compose.dev.override.yml` 创建以下文件。它会给 dev stack 改容器名、volume、数据库名，并让 dev 前后端加入 `tradingnoobs-edge` 网络供 main Caddy 反代。

```yaml
services:
  db:
    container_name: tradingnoobs-dev-db
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${DB_PASSWORD:-postgres}
      - POSTGRES_DB=tradingnoobs_dev
    volumes:
      - postgres_dev_data:/var/lib/postgresql/data

  backend:
    container_name: tradingnoobs-dev-backend
    environment:
      - DATABASE_URL=postgresql://postgres:${DB_PASSWORD:-postgres}@db:5432/tradingnoobs_dev
      - SECRET_KEY=${SECRET_KEY}
      - CORS_ORIGINS=https://${DOMAIN:-localhost},http://${DOMAIN:-localhost}
      - ENV_NAME=staging
      - AUTO_CREATE_SCHEMA=false
      - DEPLOYMENT_CAPABILITY_ALLOWLIST=
    networks:
      tradingnoobs: {}
      edge:
        aliases:
          - tradingnoobs-dev-backend

  frontend:
    container_name: tradingnoobs-dev-frontend
    build:
      args:
        - NEXT_PUBLIC_API_URL=https://${DOMAIN:-localhost}
    networks:
      tradingnoobs: {}
      edge:
        aliases:
          - tradingnoobs-dev-frontend

  db-backup:
    container_name: tradingnoobs-dev-db-backup
    environment:
      - POSTGRES_HOST=db
      - POSTGRES_DB=tradingnoobs_dev
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${DB_PASSWORD:-postgres}
      - SCHEDULE=@daily
      - BACKUP_KEEP_DAYS=7
      - BACKUP_KEEP_WEEKS=4
      - BACKUP_KEEP_MONTHS=6
      - HEALTHCHECK_PORT=8080
    volumes:
      - ./backups-dev:/backups

networks:
  tradingnoobs:
    name: tradingnoobs-dev-internal
    driver: bridge
  edge:
    external: true
    name: tradingnoobs-edge

volumes:
  postgres_dev_data:
    name: tradingnoobs-dev-postgres-data
```

重要：启动 dev 时不要启动 base compose 里的 `caddy` 服务。只启动 `db backend frontend db-backup`。

---

## 6. 更新 main Caddy，增加 dev 域名

在 main 部署目录的 Caddyfile 里新增一个站点块。示例：

```caddyfile
dev.example.com {
    handle /api/* {
        reverse_proxy tradingnoobs-dev-backend:8000
    }

    handle {
        reverse_proxy tradingnoobs-dev-frontend:3000
    }

    encode gzip zstd

    header {
        Server "TradingNoobs-Dev/1.0"
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        Referrer-Policy strict-origin-when-cross-origin
    }

    log {
        output stdout
        format json
    }
}
```

然后 reload main Caddy：

```bash
cd /opt/tradingnoobs
docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
```

如果 Caddy 无法解析 `tradingnoobs-dev-backend`，先确认：

```bash
docker network inspect tradingnoobs-edge
docker network connect tradingnoobs-edge tradingnoobs-caddy || true
```

---

## 7. 启动 dev stack

在 dev 目录执行：

```bash
cd /opt/tradingnoobs-dev
docker compose \
  -p tradingnoobs-dev \
  -f docker-compose.yml \
  -f docker-compose.dev.override.yml \
  up -d --build db backend frontend db-backup
```

确认容器：

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep tradingnoobs-dev
```

预期至少看到：

```text
tradingnoobs-dev-db
tradingnoobs-dev-backend
tradingnoobs-dev-frontend
tradingnoobs-dev-db-backup
```

---

## 8. 数据库迁移

生产/staging 不应依赖 `AUTO_CREATE_SCHEMA=true`。dev staging 应跑 Alembic：

```bash
cd /opt/tradingnoobs-dev
docker compose \
  -p tradingnoobs-dev \
  -f docker-compose.yml \
  -f docker-compose.dev.override.yml \
  exec backend alembic upgrade head
```

如果当前镜像没有把 `alembic` 放到 PATH，可改用：

```bash
docker compose \
  -p tradingnoobs-dev \
  -f docker-compose.yml \
  -f docker-compose.dev.override.yml \
  exec backend python -m alembic upgrade head
```

---

## 9. 创建 dev 管理员

```bash
cd /opt/tradingnoobs-dev
docker compose \
  -p tradingnoobs-dev \
  -f docker-compose.yml \
  -f docker-compose.dev.override.yml \
  exec backend python ops/manage_users.py create-user dev-admin@example.com '<strong-password>' admin
```

如果用户已经存在：

```bash
docker compose \
  -p tradingnoobs-dev \
  -f docker-compose.yml \
  -f docker-compose.dev.override.yml \
  exec backend python ops/manage_users.py promote-admin dev-admin@example.com
```

---

## 10. 验证 dev 部署

浏览器打开：

```text
https://dev.example.com
```

API 健康检查：

```bash
curl -I https://dev.example.com/api/auth/me
```

`/api/auth/me` 未登录时返回认证错误是正常的；关键是请求到达 dev backend，而不是 main backend。

建议按 P19 checklist 验证：

- `/`
- `/timeline`
- `/dashboard`
- `/positions`
- `/positions/new`
- `/settings`
- `/admin/jobs`

日志检查：

```bash
cd /opt/tradingnoobs-dev
docker compose \
  -p tradingnoobs-dev \
  -f docker-compose.yml \
  -f docker-compose.dev.override.yml \
  logs -f backend frontend
```

---

## 11. 更新 dev

```bash
cd /opt/tradingnoobs-dev
git fetch origin
git checkout dev
git pull --ff-only origin dev

docker compose \
  -p tradingnoobs-dev \
  -f docker-compose.yml \
  -f docker-compose.dev.override.yml \
  up -d --build db backend frontend db-backup

docker compose \
  -p tradingnoobs-dev \
  -f docker-compose.yml \
  -f docker-compose.dev.override.yml \
  exec backend python -m alembic upgrade head
```

更新后重新跑浏览器 smoke。

---

## 12. 停止或删除 dev

只停止 dev：

```bash
cd /opt/tradingnoobs-dev
docker compose \
  -p tradingnoobs-dev \
  -f docker-compose.yml \
  -f docker-compose.dev.override.yml \
  down
```

停止并删除 dev 数据库 volume：

```bash
docker compose \
  -p tradingnoobs-dev \
  -f docker-compose.yml \
  -f docker-compose.dev.override.yml \
  down -v
```

只有确认 dev 数据可以丢弃时，才使用 `down -v`。

---

## 13. 常见问题

### `container name is already in use`

说明 dev 没有使用 override，或者启动了 base compose 的固定容器名。确认命令包含：

```bash
-p tradingnoobs-dev -f docker-compose.yml -f docker-compose.dev.override.yml
```

并且不要启动 `caddy` 服务。

### `bind: address already in use 0.0.0.0:80`

说明你启动了第二个 Caddy。dev staging 应复用 main Caddy，启动 dev 时只启动：

```bash
db backend frontend db-backup
```

### dev 域名打开的是 main

检查 main Caddyfile 是否有 `dev.example.com` 独立站点块，并 reload Caddy。也检查 dev frontend build arg：

```yaml
NEXT_PUBLIC_API_URL=https://${DOMAIN:-localhost}
```

`DOMAIN` 必须是 dev 域名。

### API CORS 报错

确认 dev backend 环境变量：

```bash
CORS_ORIGINS=https://dev.example.com,http://dev.example.com
```

然后重建后端：

```bash
docker compose \
  -p tradingnoobs-dev \
  -f docker-compose.yml \
  -f docker-compose.dev.override.yml \
  up -d --build backend
```

### Market、Broker 或 AI 能力

当前交易日志 Beta 不提供这些能力的 dev 启用捷径，也不要向该部署注入 provider key。重新启用属于 release change，必须先满足 active plan 的 provider、secret、runtime rollout、失败降级和人工批准门。
