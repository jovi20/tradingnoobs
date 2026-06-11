# 市场数据接入附录

本文档只描述当前仓库中的真实实现，对应 `backend/services/market_data_service.py`、`backend/services/market_data_orchestrator.py`、`backend/services/provider_router.py` 与 `backend/services/providers/*`。

如果文档与代码不一致，以代码为准，再回头修正文档。

---

## 1. 路由入口与职责

统一入口：
- `backend/services/market_data_service.py`：对旧调用方保留 facade，`get_quote()` 仍返回包含 `c / pc / h / l / o` 的 legacy quote dict。
- `backend/services/provider_router.py`：负责 provider routing，按 symbol / exchange / market / core_type 生成确定性 provider 顺序。
- `backend/services/market_data_orchestrator.py`：负责 provider fallback、60 秒 quote cache、freshness/degradation metadata 与 structured logs。

主要职责：
- 根据代码模式或资产元数据选择 provider
- 做 60 秒级行情缓存，并在 cache hit 时标记 `freshness=CACHED`
- 提供 symbol 校验、报价查询、历史价格查询
- 辅助写入或补全 `AssetMetadata`

对外相关 API：
- `GET /api/market/validate/{symbol}`
- `GET /api/market/quote/{symbol}`
- `GET /api/market/detect/{symbol}`
- `GET /api/market/calendar`

---

## 2. 当前 provider 路由规则

### 2.1 行情路由概览

| 资产类别 | 当前主 provider | 触发规则 | 主要回退 |
|----------|-----------------|----------|----------|
| A 股 | AKShare | 6 位股票代码、北交所代码、`market=A_SHARE` | provider 内部部分场景回退 YFinance |
| 港股 | AKShare / `akshare-one` | 5 位数字港股代码、`.HK`、`exchange=HK*` | 无统一二级 provider，失败时报错 |
| 美股 | Finnhub | 字母代码、`market=US`、`asset_type=US_STOCK` | orchestrator fallback 到 YFinance |
| 加密货币 | Binance | 后缀 `USDT/BUSD/BTC/ETH`、`exchange=BINANCE/CRYPTO` | 无 |
| 基金 | AKShare | 基金代码模式、`asset_type=FUND/ETF_*` | 部分场景回退 YFinance |
| 外汇 | AKShare | 6 位字母货币对、`market=FOREX` | YFinance |

### 2.2 Public quote metadata

`GET /api/market/quote/{symbol}` 保留旧结构：

```json
{
  "symbol": "MSFT",
  "asset_type": "US_STOCK",
  "quote": {"c": 421.13, "pc": 418.9},
  "provider": "finnhub",
  "freshness": "FRESH",
  "degraded": false,
  "source_refs": ["provider:finnhub", "symbol:MSFT"],
  "trust": {
    "freshness": "FRESH",
    "degraded": false,
    "source_refs": ["provider:finnhub", "symbol:MSFT"]
  }
}
```

metadata 规则：
- `freshness=FRESH`：provider 直接成功返回。
- `freshness=CACHED`：命中 orchestrator 60 秒 quote cache。
- `freshness=UNAVAILABLE`：所有 provider 均失败，`quote=null`，`error` 为稳定错误摘要。
- `degraded=true`：主 provider 失败但 fallback 成功，或所有 provider 失败。
- `degraded_reason`：记录失败 provider 与原因，供 UI 解释“为什么用了 fallback”。
- `source_refs`：至少包含 `symbol:*` 和参与路由的 `provider:*` refs，方便和其他 read model / artifact 统一展示来源。

### 2.3 detect_asset_type 现有识别逻辑

当前识别主要基于代码模式：
- `CRYPTO`
  - 代码以 `USDT/BUSD/BTC/ETH/BNB` 等结尾
  - 或交易所显式为 `BINANCE / CRYPTO`
- `A_STOCK`
  - `000/001/002/003/300/600/601/603/688`
  - 北交所相关 `43/83/87`
- `ETF_EQUITY`
  - 常见基金前缀 `15/16/18/50/51/56`
- `HK_STOCK`
  - 5 位数字
  - 或 `.HK`
  - 或交易所为 `HKEX / HK / HONG KONG`
- `FOREX`
  - 6 位纯字母货币对，如 `EURUSD`
- `US_STOCK`
  - 1 到 8 位字母或带点代码

说明：
- 这个识别逻辑是当前路由规则，不是金融分类标准。
- 资产元数据补全会在规则识别后，再尝试通过 LLM 丰富 `core_type / market / currency / risk_level`。

---

## 3. 当前 provider 说明

### 3.1 AKShare

覆盖：
- A 股报价
- 港股报价
- 基金报价
- 外汇报价
- A 股 / 港股历史 K 线

当前实现特点：
- provider 文件：`backend/services/providers/akshare_provider.py`
- 启动时会强制禁用代理环境变量，避免访问国内数据源异常
- 对 ETF / LOF / 场外基金做了按代码前缀的分支处理
- 部分批量接口使用内存缓存，降低封禁或频率问题

当前回退：
- A 股报价失败时回退 YFinance
- 外汇报价失败时回退 YFinance
- 部分基金场景有 YFinance 兜底

### 3.2 Finnhub

覆盖：
- 美股实时报价
- 部分美股历史数据
- 市场日历相关数据

当前实现特点：
- Finnhub Client 由 `SystemSetting.key = finnhub_api_key` 懒加载
- 实时报价先走 Finnhub，失败后回退 YFinance
- 历史数据优先尝试 Finnhub `stock_candles`，失败再回退 YFinance

当前限制：
- 免费额度有限
- 如果返回 `c=0` 且 `pc=0`，当前实现会视为无效数据并进入回退逻辑

### 3.3 Binance

覆盖：
- 加密货币实时报价
- 加密货币 K 线

当前实现特点：
- provider 文件：`backend/services/providers/binance_provider.py`
- 使用 `binance-connector` 的 `Spot` client
- 公共行情不需要 API Key
- 会自动把 `BTC` 这类基础代码标准化为 `BTCUSDT`
- 会去掉 `/`、`-` 等分隔符

当前限制：
- 默认强依赖 Binance 交易对格式
- 如果用户输入非 Binance 现货交易对，当前没有第二 provider 兜底

### 3.4 YFinance 的实际角色

YFinance 在当前项目中是回退 provider，不是统一主数据源。

当前使用位置：
- 美股报价回退
- A 股报价回退
- 外汇报价回退
- 通用历史价格回退

因此文档中不要把 YFinance 写成“主集成方案”。

---

## 4. 配置项与依赖

### 4.1 Python 依赖

当前相关依赖来自 `backend/requirements.txt`：
- `finnhub-python`
- `akshare`
- `yfinance`
- `binance-connector`

### 4.2 配置项

| 配置项 | 来源 | 作用 |
|--------|------|------|
| `finnhub_api_key` | `SystemSetting` | 美股报价与部分市场日历 |
| `llm_api_url` | `SystemSetting` / 环境变量 | 资产元数据富分类 |
| `llm_api_key` | `SystemSetting` / 环境变量 | 资产元数据富分类 |
| `llm_model` | `SystemSetting` / 环境变量 | 资产元数据富分类 |

说明：
- 用户设置中的 `finnhub_api_key` 存在，但当前行情主服务读取的是系统设置。
- LLM 配置不参与行情报价本身，只参与资产元数据补全。

---

## 5. 历史数据与缓存行为

### 5.1 缓存

- `market_data_orchestrator` 报价缓存：60 秒，返回 `freshness=CACHED`
- `MarketDataService._quote_cache` 仍保留给旧 helper 使用，新增 quote facade 已转向 orchestrator
- AKShare 批量基金数据缓存：当前实现为小时级内存缓存

### 5.2 历史价格

| 资产类别 | 当前历史数据来源 |
|----------|------------------|
| A 股 / 港股 | AKShare |
| Crypto | Binance Klines |
| 美股 | Finnhub 或 YFinance |
| 其他兜底 | YFinance |

---

## 6. 限制与已知行为

- 当前 symbol 检测是规则优先，不保证所有边缘代码都能被正确分类。
- 当前 provider 选择有“启发式”特征，尤其是基金和外汇。
- `AssetMetadata` 是补全层，不是严格的权威静态主数据表。
- 行情缓存目前是进程内缓存，重启后丢失。
- 失败时 UI 可看到简化错误信息，底层原始错误主要用于调试。

---

## 7. 排障建议

### 7.1 AKShare 查询失败

常见表现：
- `Connection aborted`
- `RemoteDisconnected`
- AKShare 源站返回空数据

排查方向：
- 检查服务器网络是否能访问国内站点
- 检查代理环境变量是否污染运行环境
- 重试同一标的，确认是否为源站临时问题

### 7.2 Finnhub 查询失败

常见表现：
- 401 或 unauthorized
- 免费额度超限
- 返回空报价

排查方向：
- 检查 `SystemSetting.finnhub_api_key`
- 用后台提供的测试接口或直接请求 `AAPL` 验证
- 确认当前请求是否已经自动回退到 YFinance

### 7.3 Binance 查询失败

常见表现：
- `Invalid symbol`
- 非标准交易对格式

排查方向：
- 确认输入是否应为 Binance 现货交易对
- 优先使用 `BTCUSDT`、`ETHUSDT` 这类标准格式
- 如果是 `BTC` 这种简写，当前服务会自动补后缀，但非标准币对仍会失败

### 7.4 自动识别错误

如果资产识别和实际市场不一致：
- 先检查 symbol 与 exchange 是否录入准确
- 再检查 `AssetMetadata` 是否被旧数据缓存过
- 必要时通过持仓元数据更新逻辑手动修正

---

## 8. P16 验证命令

后端 market 目标测试：

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_market_router.py
../.venv313/bin/python -m unittest discover -s tests -p test_market_data_orchestrator.py
../.venv313/bin/python -m unittest discover -s tests -p test_market_provider_contracts.py
```

前端 freshness label 测试：

```bash
cd frontend
node --experimental-strip-types --test tests/market-data.test.mts
./node_modules/.bin/tsc --noEmit --pretty false
```
