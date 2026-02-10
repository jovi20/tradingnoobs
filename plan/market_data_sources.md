# 市场数据源文档 (Market Data Sources)

本文档详细介绍了 `Trading Noobs` 用于获取各类资产实时市场数据的外部 API。系统通过 `backend/services/market_data_service.py` 中的路由机制选择合适的提供商。

## 提供商摘要 (Summary of Providers)

| 资产类别 | 主要提供商 | 备选 / 说明 |
| :--- | :--- | :--- |
| **A股 (CN)** | **AKShare** | 使用东方财富 (EastMoney) 接口。 |
| **港股 (HK)** | **AKShare-One** | 使用 `akshare-one` 库。**不使用 Yahoo Finance**。 |
| **美股 (US)** | **Finnhub** | 需要 API Key。可靠性高。 |
| **加密货币** | **Binance** | 使用官方 `binance-connector-python`。公开数据无需 API Key。 |
| **基金 (CN)** | **AKShare** | 支持 ETF (场内) 和 OTC 基金 (场外)。 |
| **外汇** | **AKShare** | 使用东方财富接口，Yahoo Finance 作为备选。 |

---

## 1. AKShare (A股, 港股, 基金, 外汇)

**库**: `akshare`, `akshare-one` (Python)
**认证**: 无需认证。
**代理**: 系统在调用 AKShare 前会自动禁用代理 (`NO_PROXY=*`)，以防止连接国内数据源时出现问题。

### A股 (A-Shares)
- **文件**: `akshare_provider.py`
- **接口**: `ak.stock_individual_info_em(symbol="...")`
- **描述**: 获取东方财富个股信息。
- **示例**:
  ```python
  import akshare as ak
  # symbol="600519" (贵州茅台)
  df = ak.stock_individual_info_em(symbol="600519")
  print(df)
  ```

### 港股 (HK Stocks)
- **文件**: `akshare_provider.py`
- **库**: `akshare-one`
- **接口**: `akshare_one.get_realtime_data(symbol="...", source="eastmoney_direct")`
- **描述**: 获取港股实时数据。
- **示例**:
  ```python
  import akshare_one
  # symbol="00700" (腾讯控股)
  df_hk = akshare_one.get_realtime_data(symbol="00700", source="eastmoney_direct")
  print(df_hk)
  ```

### 基金 (Funds)
- **ETF基金实时行情**: `fund_etf_spot_em()` 单次返回所有数据，可每日缓存减少查询次数
- **LOF基金实时行情** 接口: fund_lof_spot_em 单次返回所有数据，可每日缓存减少查询次数
- **场外基金 (OTC)**:
    1. `fund_open_fund_info_em(symbol, indicator="单位净值走势")`: 指定单只基金。
    2. `fund_open_fund_daily_em()`: 批量获取每日净值（兜底）。

### 外汇 (Forex)
- **人民币汇率**: `fx_spot_quote()` (如 USD/CNY)。
- **国际汇率**: `fx_pair_quote()` (如 EUR/USD)。

---

## 2. Finnhub (美股)

**库**: `finnhub-python`
**认证**: **必需**。必须在 `SystemSettings` 中设置 API Key (键: `finnhub_api_key`)。

### 美股 (US Stocks)
- **客户端**: `finnhub.Client(api_key=...)`
- **使用接口**:
    - `quote(symbol)`: 获取实时价格、涨跌额、最高、最低、开盘、昨收。
- **限制**: 免费版有速率限制 (约 60 次/分钟)。
- **逻辑**: 用于任何不匹配 加密货币/A股/港股 模式的代码 (如果代码超过 5 位或纯字母，默认为美股逻辑)。

---

## 3. Binance (加密货币)

**库**: `binance-connector-python`
**认证**: 获取公共市场数据 (Ticker, 深度) 不需要。

### 加密货币 (Crypto)
- **客户端**: `binance.spot.Spot()`
- **使用接口**:
    - `ticker_24hr(symbol)`: 滚动 24 小时统计数据。
    - `exchange_info()`: 验证交易对是否存在。
- **代码处理**:
    - 自动添加 `USDT` 后缀 (如果缺失) (如 `BTC` -> `BTCUSDT`)。
    - 标准化为大写并移除分隔符 (如 `BTC/USDT` -> `BTCUSDT`)。

---

## 故障排除指南 (Troubleshooting)

### 常见问题

1. **"Connection aborted" / "RemoteDisconnected" (AKShare)**
    - **原因**: 连接东方财富 (EM) 服务器网络不稳定。
    - **解决**: 系统会自动重试。
    - **操作**: 通常无需手动干预。如果持续发生，请检查服务器 DNS 或网络连接。

2. **"Finnhub API limit reached"**
    - **原因**: 短时间内刷新美股次数过多。
    - **解决**: 等待一分钟或升级 Finnhub 套餐。可以在设置中更改 API Key。

3. **资产类别检测错误 (Wrong Asset Class Detection)**
    - 系统会自动检测资产类型。
    - **强制更正**: 如果自动检测错误 (例如美股代码看起来像加密货币)，您可以在“持仓详情”页面手动设置“资产类型” (Core Type)。
