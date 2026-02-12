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
2.  **设置 Swap** (建议 1G 内存 VPS 设置 2G Swap):
    ```bash
    sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
    sudo mkswap /swapfile && sudo swapon /swapfile
    ```

### 2.2 应用部署
本项目提供 **All-in-One** 的 `docker-compose.yml`，包含前端、后端、数据库及 Caddy 网关。

1.  **配置生产环境变量**:
    ```bash
    cp .env.example .env
    nano .env
    
    # --- 核心配置 (必须修改) ---
    # DOMAIN: 部署的域名或 IP (不带协议头)，例如: 1.2.3.4 或 my-trading-app.com
    DOMAIN=localhost
    
    # SECRET_KEY: 后端加密密钥，生成命令: openssl rand -hex 32
    SECRET_KEY=change_this_to_a_secure_random_string
    
    # DB_PASSWORD: 数据库密码，请务必修改
    DB_PASSWORD=secure_db_password
    
    # --- LLM 配置 (可选) ---
    # 若配置了以下变量，后端将自动启用 AI 功能
    LLM_API_KEY=sk-proj-...
    LLM_API_URL=https://api.openai.com/v1  # 默认为官方 API，可改为中转地址
    LLM_MODEL=gpt-4                        # 默认为 gpt-4
    ```
2.  **启动服务**:
    ```bash
    sudo docker compose up -d --build
    ```

### 2.3 网关配置
`docker-compose.yml` 已集成 Caddy 服务，自动读取项目根目录下的 `Caddyfile`。
-   **SSL**: Caddy 会自动为配置的域名申请 HTTPS 证书。
-   **端口**: 仅暴露 80 和 443 端口，后端接口及前端服务均通过 Caddy 代理，不直接对外暴露。

### 2.4 数据库迁移
当代码更新涉及数据库变更时执行：
```bash
sudo docker exec -it tradingnoobs-backend python ops/migrate_db.py
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
使用内置脚本进行管理（需进入后端容器）：

1.  **列出用户**:
    ```bash
    sudo docker exec -it tradingnoobs-backend python ops/manage_users.py list-users
    ```

2.  **创建用户/管理员**:
    ```bash
    # 创建普通用户
    sudo docker exec -it tradingnoobs-backend python ops/manage_users.py create-user [EMAIL_ADDRESS] password123
    # 创建管理员
    sudo docker exec -it tradingnoobs-backend python ops/manage_users.py create-user [EMAIL_ADDRESS] admin123 admin
    ```

3.  **重置密码**:
    ```bash
    sudo docker exec -it tradingnoobs-backend python ops/manage_users.py reset-password [EMAIL_ADDRESS] new_password
    ```

4.  **封禁/解封用户**:
    ```bash
    sudo docker exec -it tradingnoobs-backend python ops/manage_users.py toggle-active [EMAIL_ADDRESS]
    ```

### 3.4 定时任务 (Scheduled Tasks)

#### 3.4.1 自动数据库备份
`docker-compose.yml` 已内置 `db-backup` 服务，无需额外配置：
-   **频率**: 默认每日备份 (`SCHEDULE=@daily`)。
-   **保留策略**: 保留最近 7 天、4 周、6 个月的备份。
-   **位置**: `./backups` 目录。
-   **自定义**: 修改 `docker-compose.yml` 中的环境变量调整策略。

#### 3.4.2 Python 库定时更新
若需定期更新依赖库（如 `akshare` 获取最新接口），请在宿主机设置 Crontab。

1.  **赋予脚本执行权限**:
    ```bash
    chmod +x update_libs.sh
    ```
2.  **设置 Crontab (例如每周一凌晨 3 点更新)**:
    ```bash
    crontab -e
    # 添加如下行:
    0 3 * * 1 /path/to/tradingnoobs/update_libs.sh >> /var/log/tradingnoobs_update.log 2>&1
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
-   **资产分类系统**: 利用 LLM 智能细分资产类型 (Equity, ETF, Bond, etc.)。

### 🚧 开发中 (In Progress)


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

###
你是一名对 ARM 架构、低配 VPS、生存级性能极度敏感的资深全栈工程师 / SRE / 架构审查官，需要审查一个 ToC 交易日志记录系统 的代码。

部署环境（必须作为前提）：

架构：ARM（非 x86）

CPU：2 核

内存：1GB

磁盘：普通 SSD（非高 IOPS）

单机部署、单实例

阶段：

MVP（可以不优雅，但不能浪费资源）

最高原则（必须反复对照）：

在 ARM + 1G 内存环境下，
任何“额外抽象 / 通用方案 / 可扩展设计”都是性能负债
能删就删，能同步就别异步，能直写就别绕层

一、ARM 架构一票否决项（发现即判不合格）

请重点检查是否存在以下情况：

❌ 架构级问题

微服务 / Sidecar / 多进程模型

Node + Java / 多运行时混用

依赖 x86 优化明显但 ARM 表现一般 的组件

高 GC 压力语言 + 大对象模型（未做限制）

❌ 资源浪费行为

JVM / Node 默认配置直接使用

使用高内存 Web 框架却只做 CRUD

引入但几乎不用的重型依赖

👉 一旦发现，请直接标记：
「❌ 不适合 ARM 2C / 1G VPS，上线即高风险」

二、进程模型与并发策略（ARM 特别关注）

请分析：

实际运行时会启动多少线程 / Worker

是否存在：

线程数 > CPU 核数数倍

无上限线程池 / goroutine / promise

是否存在 CPU 竞争导致：

上下文切换过多

tail latency 激增

请判断：

在 CPU 满载 时，系统是否还能正常写日志

三、交易日志写入路径（绝对核心）

请从 CPU + 内存 + IO 三个角度审查交易日志写入：

1️⃣ CPU

是否有：

复杂金额计算

高频时间格式化

JSON 深度序列化

是否在写入前做过度校验

2️⃣ 内存

是否构建完整日志对象后再写库

是否存在中间 DTO / VO / Mapper

是否有写入队列但未限制长度

3️⃣ IO

是否同步写数据库

是否多次 flush / commit

是否写库同时打日志

请明确指出：

最慢的一步在哪里

是否能在 ARM 2C 下稳定支撑 ToC 峰值写入

四、数据库设计（假设 IO 是最大瓶颈）

以「磁盘慢、缓存小」为前提审查：

必须检查

每个接口的 SQL 数量

是否存在：

order by + limit 但索引不命中

count(*) 扫描大表

是否为日志表：

明确按时间查询

严格控制字段数量

请回答

删掉哪些字段 / 索引反而更快

是否存在“为了未来需求而预留”的设计（应删）

五、内存生存能力（1GB 极限）

请以 长时间运行（7×24） 为前提判断：

常驻内存大小估算

峰值内存是否接近 OOM

是否存在：

无上限缓存

内存中聚合交易数据

前端分页过大导致响应体膨胀

请给出：

OOM 最可能出现的场景

六、前端对 ARM VPS 的“间接杀伤”

请从服务器视角审查前端行为：

是否存在：

自动刷新 / 轮询

大列表无限滚动

同一页面多接口并发请求

是否允许前端指定过大的 pageSize

请指出：

哪些前端行为在 ARM VPS 上是致命的

七、日志、监控与系统噪音

在普通 SSD + ARM CPU 下：

是否在热路径打印日志

是否日志级别过高

是否引入 Prometheus / APM 等高消耗组件

请评估：

日志与监控是否会 比业务本身更耗资源

八、最终生存结论（必须给出）

请明确回答：

该系统是否能在 ARM 2C / 1G VPS 上稳定运行

最先压垮系统的 3 个点（按概率排序）

如果只允许修改 20% 代码，最优先动哪里

是否建议：

立即上线

降级功能后上线

暂缓上线

结论必须直接、冷酷、基于现实，不允许“理论上可行”。

🔧 可选增强指令（按需加）

👉 更真实压力

“假设高峰期写入 QPS = 平均的 5 倍”

👉 极限生存

“假设 VPS 内存只剩 700MB 可用”

👉 砍功能模式

“必须删除一个功能以换性能，请给出建议”
###
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

> 文档最后更新时间: 2026-02-12
