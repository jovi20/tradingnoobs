# Trading Noobs Backend

FastAPI 后端，负责认证、账户、交易 truth model、Timeline read model、Insights、市场数据、异步任务和管理员运维 API。

更新时间：2026-07-06

## 目录结构

| 路径 | 说明 |
|------|------|
| `main.py` | FastAPI 应用入口，注册中间件和路由。 |
| `config.py` | 环境变量和运行配置。 |
| `database.py` | SQLAlchemy engine、session 和 declarative base。 |
| `models.py` | 当前 SQLAlchemy 模型集中定义处；后续计划拆分。 |
| `schemas.py` | Pydantic 请求和响应模型。 |
| `routers/` | API 路由层。 |
| `services/` | 业务逻辑、read model、任务、市场数据和导出服务。 |
| `services/providers/` | 市场数据 provider adapter。 |
| `alembic/` | Alembic 迁移脚本和版本链。 |
| `ops/` | 迁移、回填和管理员脚本。 |
| `tests/` | 后端测试。 |

## 本地开发

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
alembic -c alembic.ini upgrade head
uvicorn main:app --reload
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
| `LLM_API_URL` | `https://api.openai.com/v1` | OpenAI 兼容 LLM 接口地址。 |
| `LLM_API_KEY` | 空 | LLM API key。 |
| `LLM_MODEL` | `gpt-4-turbo` | LLM 模型名。 |
| `FINNHUB_API_KEY` | 空 | Finnhub 行情 key。 |
| `BINANCE_API_KEY` | 空 | Binance key。 |
| `BINANCE_API_SECRET` | 空 | Binance secret。 |
| `ENV_NAME` | `development` | `development` 或 `production`。 |
| `AUTO_CREATE_SCHEMA` | 空 | 控制受保护 schema bootstrap；生产默认关闭。 |

## 数据库迁移

Alembic 是 schema 演进主路径。

```bash
cd ..
alembic -c backend/alembic.ini upgrade head
```

开发环境启动时仍有受保护 schema bootstrap，具体边界见 [../docs/DEVELOPER_GUIDE.md](../docs/DEVELOPER_GUIDE.md)。

## 测试

```bash
cd backend
python -m pytest -q
```

常用聚焦测试示例：

```bash
python -m pytest tests/test_alembic_chain.py -q
python -m pytest tests/test_openapi_contracts.py -q
python -m pytest tests/test_trading_position_lifecycle_router.py -q
```

## 维护注意

- 新 schema 变更优先新增 Alembic revision，不再维护手写迁移聚合脚本。
- 普通交易写入优先走 `TradingPosition` / `PositionEvent` / `AccountLedgerEntry` truth 路径。
- legacy `Position` / `TradeBatch` / `Transaction` 仍处于迁移期，新增功能不要继续扩大 legacy 写入面。
- 对外错误响应应保持统一 error envelope 和 request id。
