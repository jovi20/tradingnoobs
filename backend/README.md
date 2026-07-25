# Trading Noobs Backend

FastAPI 后端，负责认证、账户、交易 truth model、Timeline read model、交易日志异步任务和管理员运维 API。

更新时间：2026-07-25

## JOURNAL Beta 边界

当前 Beta 默认关闭 `BROKER_SYNC`、`MARKET`、`AI_INSIGHTS`、`PDF_EXPORT`、`RISK_CARDS` 和 `OPEN_REGISTRATION`。仓库中可能保留相应 router、service、schema 和测试，但代码存在不表示路由已注册或功能可用；这些能力不得出现在 Beta OpenAPI、导航、设置或 job/outbox producer 中。

`OPEN_REGISTRATION` 仍为 hard-off，但 invite-only onboarding 是独立的基线能力：管理员通过 `/api/admin/invitations` 创建一次性、限时、随机且仅哈希存储的邀请码，用户通过 `/api/auth/register` 兑换并提交有效 IANA 时区。共享邀请码和无邀请码注册均不可用。

- 普通用户不能保存 Broker、行情或 LLM 凭据。可选能力未来需要平台 secret 时，只能读取受管环境或加密 `IntegrationCredential`。
- 缺失 `DEPLOYMENT_CAPABILITY_ALLOWLIST` 时 deployment ceiling 为空，数据库 FeatureFlag 不能越过该 ceiling。
- `IBKR_FLEX_XML_V1` 是 `JRN-013` 至 `JRN-015` 的本地文件 adapter。JRN-013 已有 schema/parser/preview 与 evidence-first API；provider evidence 尚未验证时 `/api/positions/import/ibkr-flex/upload` 在 staging 前返回 `404 FEATURE_DISABLED`。它不访问网络，也不使用 Flex Token 或 Query ID。

## 目录结构

| 路径 | 说明 |
|------|------|
| `main.py` | FastAPI 应用入口，注册中间件和路由。 |
| `config.py` | 环境变量和运行配置。 |
| `database.py` | SQLAlchemy engine、session 和 declarative base。 |
| `models.py` | 当前 SQLAlchemy 模型集中定义处；后续计划拆分。 |
| `schemas.py` | Pydantic 请求和响应模型。 |
| `routers/` | API 路由层。 |
| `services/` | 业务逻辑、read model 和任务；provider、AI、risk、PDF 等 optional service 代码当前为 `DISABLED / DEFERRED`。 |
| `services/providers/` | 保留的市场数据 provider adapter；不属于 JOURNAL Beta 运行依赖。 |
| `alembic/` | Alembic 迁移脚本和版本链。 |
| `ops/` | 迁移、回填和管理员脚本。 |
| `tests/` | 后端测试。 |

## 本地开发

```bash
cd backend
python -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip==26.1.2
python -m pip install --require-hashes -r requirements-ci.lock.txt
cp .env.example .env
alembic -c alembic.ini upgrade head
uvicorn main:app --reload --no-access-log
```

默认地址：

| 服务 | 地址 |
|------|------|
| API | `http://localhost:8000` |
| OpenAPI | `http://localhost:8000/docs` |
| Health check | `http://localhost:8000/api/health` |

## 环境变量

复制 `.env.example` 到 `.env` 后按需修改。

| 变量 | 默认/示例 | 说明 |
|------|-----------|------|
| `DATABASE_URL` | `sqlite:///./tradingnoobs.db` | 本地默认 SQLite；部署建议 PostgreSQL。 |
| `SECRET_KEY` | `your-super-secret-key-change-in-production` | JWT 签名密钥，生产环境必须替换。 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | access token 有效期。 |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | 允许访问 API 的前端来源。 |
| `UPLOAD_DIR` | `./uploads` | 上传目录。 |
| `MAX_UPLOAD_SIZE` | `10485760` | 上传大小限制，单位 byte。 |
| `ENV_NAME` | `development` | `development` 或 `production`。 |
| `AUTO_CREATE_SCHEMA` | 空 | 控制受保护 schema bootstrap；生产默认关闭。 |
| `DEPLOYMENT_CAPABILITY_ALLOWLIST` | 空 | 部署拥有的 optional capability ceiling；JOURNAL Beta 保持为空，不能用数据库配置扩大。 |

历史 Broker、Market 和 LLM 环境变量可能仍被 deferred 代码识别，但它们不属于 JOURNAL Beta 配置合同。不要在当前 profile 的 `.env`、部署清单或普通设置中配置、保存或分发相关凭据。

## 数据库迁移

Alembic 是 schema 演进主路径。

```bash
cd ..
alembic -c backend/alembic.ini upgrade head
```

开发环境启动时仍有受保护 schema bootstrap，具体边界见 [../docs/DEVELOPER_GUIDE.md](../docs/DEVELOPER_GUIDE.md)。

## 测试

从仓库根目录运行与 CI 相同的完整门禁：

```bash
backend/venv/bin/python scripts/run_journal_baseline_gate.py
```

只运行后端测试：

```bash
PYTHONPATH=backend backend/venv/bin/python -m pytest backend/tests -q
```

常用聚焦测试示例：

```bash
PYTHONPATH=backend backend/venv/bin/python -m pytest backend/tests/test_alembic_chain.py -q
PYTHONPATH=backend backend/venv/bin/python -m pytest backend/tests/test_openapi_contracts.py -q
PYTHONPATH=backend backend/venv/bin/python -m pytest backend/tests/test_trading_position_lifecycle_router.py -q
```

## 维护注意

- 新 schema 变更优先新增 Alembic revision，不再维护手写迁移聚合脚本。
- 普通交易写入优先走 `TradingPosition` / `PositionEvent` / `AccountLedgerEntry` truth 路径。
- legacy `Position` / `TradeBatch` / `Transaction` 仍处于迁移期，新增功能不要继续扩大 legacy 写入面。
- 对外错误响应应保持统一 error envelope 和 request id。
