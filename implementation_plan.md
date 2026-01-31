# Trading Noobs 功能实施计划

## 项目概述

Trading Noobs 是一个全栈交易日志系统，用于记录、分析和复盘美股与加密货币交易。

---

## 实施进度 ✅

### 阶段 1：认证与状态管理 ✅

| 文件 | 操作 | 状态 |
|------|------|------|
| `contexts/AuthContext.tsx` | 新增 | ✅ 完成 |
| `components/Providers.tsx` | 新增 | ✅ 完成 |
| `app/layout.tsx` | 修改 | ✅ 完成 |
| `app/login/page.tsx` | 修改 - 连接 API | ✅ 完成 |
| `app/register/page.tsx` | 修改 - 连接 API | ✅ 完成 |
| `components/Navbar.tsx` | 修改 - 登出按钮 | ✅ 完成 |

---

### 阶段 2：交易模块联调 ✅

| 文件 | 操作 | 状态 |
|------|------|------|
| `app/trades/page.tsx` | 修改 - 连接 API | ✅ 完成 |
| `app/trades/new/page.tsx` | 修改 - 连接 API | ✅ 完成 |
| `app/trades/[id]/page.tsx` | 修改 - 连接 API | ✅ 完成 |

---

### 阶段 3：看板与策略 ✅

| 文件 | 操作 | 状态 |
|------|------|------|
| `app/page.tsx` | 修改 - Dashboard API | ✅ 完成 |
| `app/strategies/page.tsx` | 重写 - 完整 CRUD | ✅ 完成 |

---

### 阶段 4：日历与周报 ✅

| 文件 | 操作 | 状态 |
|------|------|------|
| `app/daily/page.tsx` | 重写 - 日历视图 | ✅ 完成 |
| `app/reports/page.tsx` | 重写 - 周报列表 | ✅ 完成 |
| `lib/api.ts` | 新增 Daily API | ✅ 完成 |

---

### 阶段 5：设置 ✅

| 文件 | 操作 | 状态 |
|------|------|------|
| `app/settings/page.tsx` | 修改 - 连接 API | ✅ 完成 |

---

## 待实现功能 (P2)

| 功能 | 说明 | 优先级 |
|------|------|------|
| 截图上传 | 交易支持上传 K 线截图 | P2 |
| CSV 导出 | 交易记录批量导出 | P2 |
| 资金管理 | 入金/出金记录 | P2 |
| 风控提醒 | 连续亏损/仓位过大提醒 | P2 |
| 实时行情 | Finnhub WebSocket 接入 | P2 |
| IBKR 同步 | 自动同步盈透交易 | P2 |
| Binance 同步 | 自动同步币安交易 | P2 |

---

## 文件变更清单

### 新增文件
- `frontend/contexts/AuthContext.tsx` - 认证状态管理
- `frontend/components/Providers.tsx` - Provider 组件

### 修改文件
- `frontend/app/layout.tsx` - 包裹 Providers
- `frontend/app/login/page.tsx` - 真实登录 API
- `frontend/app/register/page.tsx` - 真实注册 API
- `frontend/components/Navbar.tsx` - 添加登出按钮
- `frontend/app/page.tsx` - Dashboard 真实数据
- `frontend/app/trades/page.tsx` - 交易列表真实数据
- `frontend/app/trades/new/page.tsx` - 创建交易真实 API
- `frontend/app/trades/[id]/page.tsx` - 交易详情真实 API
- `frontend/app/strategies/page.tsx` - 策略管理完整 CRUD
- `frontend/app/daily/page.tsx` - 日历视图真实数据
- `frontend/app/reports/page.tsx` - 周报列表真实 API
- `frontend/app/settings/page.tsx` - 设置保存真实 API
- `frontend/lib/api.ts` - 添加 Daily API

---

## 启动方式

```powershell
# 方式一：使用启动脚本
.\start.bat

# 方式二：手动启动
# 后端
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload

# 前端（新终端）
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000
