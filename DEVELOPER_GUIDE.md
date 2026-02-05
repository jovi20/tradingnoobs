# Trading Noobs 开发者与运维指南

本文档集成了项目的开发配置、部署流程、运维维护、功能计划及性能优化指南，旨在为开发者和运维人员提供全方位的技术参考。

---

## 🏗️ 1. 开发环境搭建 (Development Setup)

### 1.1 获取代码
```bash
git clone <repo-url>
cd tradingnoobs
```

### 1.2 后端开发环境 (Backend)
基于 FastAPI 和 Python 3.10+。

```bash
cd backend
# 创建虚拟环境
python -m venv venv
# 激活环境
source venv/bin/activate      # Linux/macOS
# venv\Scripts\activate       # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 配置数据库和 API Key
```

**启动开发服务器**:
```bash
uvicorn main:app --reload
```
访问文档: `http://localhost:8000/docs`

### 1.3 前端开发环境 (Frontend)
基于 Next.js 14 和 TypeScript。

```bash
cd frontend
# 安装依赖
npm install

# 启动开发服务器
npm run dev
```
访问应用: `http://localhost:3000`

### 1.4 项目结构
```
tradingnoobs/
├── backend/                 # FastAPI 后端
│   ├── routers/             # API 路由 (业务入口)
│   ├── services/            # 核心业务逻辑 (LLM, 行情等)
│   ├── models.py            # SQLAlchemy 数据模型
│   └── schemas.py           # Pydantic 数据验证
├── frontend/                # Next.js 前端
│   ├── app/                 # App Router 页面
│   ├── components/          # React 组件
│   └── lib/                 # 工具库与 API 封装
├── docker-compose.yml       # 容器编排配置
└── Caddyfile                # 反向代理配置
```

---

## 🚀 2. 部署指南 (Deployment)

针对 VPS 环境（包括 ARM 架构），推荐使用 Docker + Caddy 分离部署方案。

### 2.1 环境准备
1.  **安装 Docker & Docker Compose**.
2.  **创建外部网络** (用于容器间通信):
    ```bash
    sudo docker network create web-proxy
    ```
3.  **设置 Swap** (建议 1G 内存 VPS 设置 2G Swap):
    ```bash
    sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
    sudo mkswap /swapfile && sudo swapon /swapfile
    ```

### 2.2 应用部署
在项目根目录下：
1.  **配置生产环境变量**:
    ```bash
    nano .env
    # 设置 DOMAIN, SECRET_KEY, DB_PASSWORD
    ```
2.  **启动服务**:
    ```bash
    sudo docker compose up -d --build
    ```

### 2.3 网关配置 (Caddy)
建议使用独立的 Caddy 容器作为反向代理网关。

**Caddyfile 示例**:
```caddy
{$DOMAIN} {
    handle {
        reverse_proxy tradingnoobs-frontend:3000
    }
    handle /api/* {
        reverse_proxy tradingnoobs-backend:8000
    }
    encode gzip
}
```

### 2.4 数据库迁移
当代码更新涉及数据库变更时执行：
```bash
sudo docker exec -it tradingnoobs-backend python migrate_db.py
```

---

## 🔧 3. 运维指南 (Operations)

### 3.1 常用命令
-   **查看状态**: `sudo docker compose ps`
-   **查看日志**: `sudo docker compose logs -f`
-   **资源监控**: `sudo docker stats`
-   **清理空间**: `sudo docker system prune -f`

### 3.2 数据库备份
使用内置脚本进行备份：
```bash
chmod +x backup_db.sh
./backup_db.sh
```
备份文件将保存在 `./backups` 目录。

### 3.3 用户管理
-   **提升管理员**:
    ```bash
    sudo docker exec -it tradingnoobs-backend python manage_users.py promote-admin user@example.com
    ```
-   **重置密码**:
    ```bash
    sudo docker exec -it tradingnoobs-backend python manage_users.py reset-password user@example.com new_password
    ```

---

## 🗺️ 4. 功能规划与状态 (Roadmap)

### ✅ 已完成功能 (Completed)
-   **用户认证**: 注册、登录、JWT 鉴权。
-   **交易记录**: 包含开平仓、心理记录、CSV 导出。
-   **看板**: 盈亏统计、胜率分析。
-   **行情集成**: 连接 Finnhub (美股)、Binance (Crypto)、AkShare (A/港股)。
-   **AI 洞察**: 基于 LLM 的自动周报生成。
-   **设置**: 账户管理、API Key 配置。

### 🚧 开发中 (In Progress)
-   **资产分类系统**: 利用 LLM 智能细分资产类型 (Equity, ETF, Bond, etc.)。

### 📋 待开发 (Todo)
-   **P2**: 截图上传功能 (用于复盘)。
-   **P2**: 资金管理模块 (出入金记录)。
-   **P2**: 风险控制提醒 (回撤/仓位告警)。
-   **P2**: 自动化同步 (IBKR / Binance 自动导入)。

---

## ⚡ 5. 性能优化与架构审查 (Critical Review)

### 🚨 已知风险 (High Priority)
1.  **阻塞式 I/O**: `MarketDataService` 中的部分同步请求可能阻塞 Event Loop。
    -   *解决方案*: 使用 `run_in_threadpool` 或迁移至 `httpx` 异步客户端。
2.  **内存占用 (OOM)**: 大量交易记录加载到内存可能导致低配 VPS 崩溃。
    -   *解决方案*: 尽可能使用 SQL 聚合查询 (`func.sum`, `func.count`) 代替应用层计算。

### ⚠️ 优化建议
1.  **数据库优化**: 为 `trades` 表的 `pnl` 添加持久化列（已部分实施），并添加 `(user_id, entry_time)` 复合索引。
2.  **构建优化**: 避免在低配 VPS 上进行 `npm run build`，建议本地构建 Docker 镜像后推送。

---

## 🛠️ 6. 开发辅助脚本 (Utility Scripts)
项目根目录下包含多个 Python 脚本，用于调试行情接口和数据结构：

### 6.1 行情验证
-   `test_assets.py`: 测试多品种行情获取（ETF、开放式基金、北交所股票）。
-   `test_robust.py`: 健壮性测试，验证针对易失败标的（如部分 ETF）的异常处理和降级机制。
-   `test_simple.py`: 快速冒烟测试，仅验证 A股龙头（如茅台）和主流 ETF 的连通性。

### 6.2 调试工具
-   `debug_akshare.py`: 绕过业务逻辑，直接调用 `akshare` 库函数，用于排查上游 API 变更或网络问题。
-   `debug_cols.py`: 打印 `akshare` 返回 DataFrame 的所有列名，用于修复因字段名变更（如 `基金代码` vs `代码`）导致的代码错误。

---

> 文档最后更新时间: 2026-02-05
