# Trading Noobs 交易日志系统

一个全栈 Web 应用，用于记录、分析和复盘美股与加密货币交易。

![Dashboard Preview](https://img.shields.io/badge/Next.js-14-black?style=flat-square&logo=next.js) ![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?style=flat-square&logo=fastapi) ![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?style=flat-square&logo=typescript)

## ✨ 功能特性

- 🔐 **用户认证** - JWT Token 认证，邮箱注册登录
- 📈 **交易记录** - 开仓/平仓管理，含决策心理记录
- 📊 **数据看板** - P&L 曲线、胜率、盈亏比可视化
- 🎯 **策略管理** - 创建交易策略并关联到交易
- 📝 **复盘系统** - Markdown 复盘笔记 + 每日总结
- 🤖 **AI 周报** - LLM 生成周报，芒格理论评价
- 🌙 **主题切换** - 日间/夜间/跟随系统
- 📱 **响应式设计** - 支持手机浏览器

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Recharts |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Database | PostgreSQL (prod) / SQLite (dev) |
| Deployment | Docker, Caddy |

## 🚀 快速开始

### 本地开发

```bash
# 克隆项目
git clone <repo-url>
cd tradingnoobs

# 启动后端
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload

# 启动前端 (新终端)
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000

### Docker 部署

```bash
# 设置环境变量
export DOMAIN=your-domain.com
export SECRET_KEY=$(openssl rand -hex 32)

# 启动服务
docker compose up -d
```

## 📁 项目结构

```
tradingnoobs/
├── backend/                 # FastAPI 后端
│   ├── routers/             # API 路由
│   │   ├── auth.py          # 认证
│   │   ├── trades.py        # 交易
│   │   ├── strategies.py    # 策略
│   │   ├── dashboard.py     # 看板
│   │   ├── daily.py         # 每日总结
│   │   ├── settings.py      # 设置
│   │   └── weekly_report.py # 周报
│   ├── services/            # 业务逻辑
│   ├── models.py            # 数据模型
│   └── schemas.py           # 请求/响应模式
├── frontend/                # Next.js 前端
│   ├── app/                 # 页面路由
│   ├── components/          # React 组件
│   └── lib/                 # API 客户端
├── docker-compose.yml       # 容器编排
└── Caddyfile                # 反向代理
```

## 🔧 配置

### 环境变量

```bash
# backend/.env
DATABASE_URL=postgresql://user:pass@localhost/tradingnoobs
SECRET_KEY=your-secret-key
CORS_ORIGINS=http://localhost:3000
```

### API 密钥配置

在设置页面配置：
- **IBKR**: TWS/Gateway 地址、端口、Client ID
- **Binance**: API Key、Secret (建议只读权限)
- **Finnhub**: 美股行情 API Key
- **LLM**: OpenAI 格式 API (URL + Key + 模型)

## 📖 API 文档

启动后端后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🗺️ Roadmap

- [ ] IBKR 交易自动同步
- [ ] Binance 交易自动同步
- [ ] 实时行情数据
- [ ] 截图上传功能
- [ ] CSV/Excel 数据导出
- [ ] 资金管理 (入金/出金)
- [ ] 风控提醒

## 📄 License

MIT
