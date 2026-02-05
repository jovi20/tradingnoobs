"""
AKShare Provider - A股/港股行情数据
"""
import os

# 禁用代理，防止网络问题
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'

from typing import Dict, Any


def get_a_stock_quote(symbol: str) -> Dict[str, Any]:
    """
    获取A股实时行情 (包含沪深京)
    symbol: 股票代码，如 "000001", "600519", "830833"
    """
    # 彻底禁用代理环境变量，防止干扰
    for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
        if key in os.environ:
            del os.environ[key]
    os.environ['NO_PROXY'] = '*'
    
    try:
        import akshare as ak
        
        # 针对不同市场使用最稳定的接口
        df = None
        try:
            if symbol.startswith(('43', '83', '87')):
                df = ak.stock_bj_a_spot_em()
            elif symbol.startswith(('60', '68')):
                df = ak.stock_sh_a_spot_em()
            elif symbol.startswith(('00', '30')):
                df = ak.stock_sz_a_spot_em()
            
            # 如果分市场接口没拿到，尝试通用的全量接口
            if df is None or df.empty or symbol not in df['代码'].values:
                df = ak.stock_zh_a_spot_em()
        except Exception:
            # 任何 segment 错误都回退到全量接口
            df = ak.stock_zh_a_spot_em()
        
        # 查找指定股票
        row = df[df['代码'] == symbol]
        
        if not row.empty:
            row = row.iloc[0]
            price = float(row['最新价']) if row['最新价'] else None
            return {
                'c': price,
                'pc': float(row['昨收']) if '昨收' in row and row['昨收'] else price,
                'h': float(row['最高']) if '最高' in row and row['最高'] else None,
                'l': float(row['最低']) if '最低' in row and row['最低'] else None,
                'o': float(row['今开']) if '今开' in row and row['今开'] else None,
                'name': row['名称'],
                'change_percent': float(row['涨跌幅']) if '涨跌幅' in row and row['涨跌幅'] else 0
            }
        else:
            raise ValueError(f"AKShare未找到股票: {symbol}")
            
    except Exception as ak_error:
        # Fallback: 尝试 Yahoo Finance
        try:
            import yfinance as yf
            if symbol.startswith('6'):
                suffix = '.SS'
            elif symbol.startswith(('0', '3')):
                suffix = '.SZ'
            else:
                suffix = '.BJ'
                
            ticker = yf.Ticker(symbol + suffix)
            info = ticker.fast_info
            
            if not info.last_price:
                raise ValueError("Yahoo Finance返回空数据")

            return {
                'c': info.last_price,
                'pc': info.previous_close,
                'h': info.day_high,
                'l': info.day_low,
                'o': info.open,
                'name': symbol,
                'change_percent': ((info.last_price - info.previous_close) / info.previous_close) * 100 if info.previous_close else 0
            }
        except Exception as yf_error:
            raise Exception(f"A股查询失败。AKShare: {str(ak_error)} | YFinance: {str(yf_error)}")


def get_fund_quote(symbol: str) -> Dict[str, Any]:
    """
    获取基金现价/净值 (场内与场外)
    """
    # 彻底禁用代理环境变量，防止干扰
    for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
        if key in os.environ:
            del os.environ[key]
    os.environ['NO_PROXY'] = '*'
    
    try:
        import akshare as ak
        
        # 1. 优先尝试作为场内基金（ETF/LOF）获取实时行情
        try:
            # 场内基金使用实时接口
            df_etf = ak.fund_etf_spot_em()
            result = df_etf[df_etf['代码'] == symbol]
            
            if not result.empty:
                row = result.iloc[0]
                return {
                    'c': float(row['最新价']),
                    'pc': float(row['最新价']),
                    'name': row['名称'],
                    'change_percent': float(row['涨跌幅']) if '涨跌幅' in row else 0
                }
        except Exception as e:
            print(f"ETF spot query failed for {symbol}: {e}")

        # 2. 如果场内基金未找到，尝试单只基金查询接口 (仅限场外)
        try:
            # 使用更针对单只基金的接口，减少全量拉取压力
            df_info = ak.fund_open_fund_info_em(symbol=symbol, indicator="单位净值走势")
            if not df_info.empty:
                # 最后一行为最新净值
                latest = df_info.iloc[-1]
                return {
                    'c': float(latest['单位净值']),
                    'pc': float(df_info.iloc[-2]['单位净值']) if len(df_info) > 1 else float(latest['单位净值']),
                    'name': symbol, # 该接口不直接回传名称，可依赖调用方标记
                    'change_percent': float(latest['日增长率']) if '日增长率' in latest else 0
                }
        except Exception as e:
             print(f"Single fund info query failed for {symbol}: {e}")

        # 3. 如果以上都失败，尝试全量场外接口 (兜底)
        try:
            df_open = ak.fund_open_fund_daily_em()
            code_col = '基金代码' if '基金代码' in df_open.columns else '代码'
            result = df_open[df_open[code_col] == symbol]
            
            if not result.empty:
                row = result.iloc[0]
                price_col = '单位净值' if '单位净值' in row else '最新净值'
                name_col = '基金简称' if '基金简称' in row else '名称'
                return {
                    'c': float(row[price_col]),
                    'pc': float(row[price_col]),
                    'name': row[name_col],
                    'change_percent': float(row['日增长率']) if '日增长率' in row and row['日增长率'] else 0
                }
        except Exception as e:
             print(f"Bulk open fund query failed: {e}")
             
    except Exception as e:
        print(f"AKShare internal error: {e}")

    # 4. 最终兜底方案: Yahoo Finance (例如 510300.SS)
    try:
        import yfinance as yf
        # 尝试沪市后缀，再尝试深市
        for suffix in ['.SS', '.SZ']:
            ticker = yf.Ticker(symbol + suffix)
            info = ticker.fast_info
            if info.last_price:
                return {
                    'c': info.last_price,
                    'pc': info.previous_close,
                    'name': symbol,
                    'change_percent': ((info.last_price - info.previous_close) / info.previous_close) * 100 if info.previous_close else 0
                }
    except Exception as yf_err:
        raise Exception(f"查询失败。AKShare 网络问题且 YFinance 无记录: {yf_err}")

    raise ValueError(f"未找到代码为 '{symbol}' 的有效基金数据")


def get_hk_stock_quote(symbol: str) -> Dict[str, Any]:
    """
    获取港股实时行情
    symbol: 股票代码，如 "00700", "09988"
    """
    # Remove possible .HK suffix and normalize to 5 digits
    clean_symbol = symbol.replace('.HK', '').replace('.hk', '').zfill(5)
    
    # Thoroughly disable proxy env vars
    import os
    for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
        os.environ.pop(key, None)
    os.environ['NO_PROXY'] = '*'
    
    try:
        import akshare as ak
        
        # Method 1: EM Real-time (Snapshot of all HK stocks)
        try:
            df = ak.stock_hk_spot_em()
            if df is not None and not df.empty:
                # Robust matching: ensure '代码' is treated as string and matched against padded clean_symbol
                row = df[df['代码'].astype(str).str.zfill(5) == clean_symbol]
                if not row.empty:
                    row = row.iloc[0]
                    return {
                        'c': float(row['最新价']) if row['最新价'] else None,
                        'pc': float(row['昨收']) if row['昨收'] else None,
                        'h': float(row['最高']) if row['最高'] else None,
                        'l': float(row['最低']) if row['最低'] else None,
                        'o': float(row['今开']) if row['今开'] else None,
                        'name': row['名称'],
                        'change_percent': float(row['涨跌幅']) if row['涨跌幅'] else 0
                    }
        except Exception as em_err:
            print(f"AKShare HK EM query failed: {em_err}")
            
        # Method 2: Sina Real-time (Fall back to more specific provider if EM is down)
        try:
            # Note: stock_hk_zh_spot uses a different data source
            df = ak.stock_hk_zh_spot(symbol=clean_symbol)
            if df is not None and not df.empty:
                # stock_hk_zh_spot returns a dataframe for a single stock usually or small set
                row = df.iloc[0]
                return {
                    'c': float(row['last']),
                    'pc': float(row['prevclose']),
                    'h': float(row['high']),
                    'l': float(row['low']),
                    'o': float(row['open']),
                    'name': row['name'],
                    'change_percent': ((float(row['last']) - float(row['prevclose'])) / float(row['prevclose'])) * 100 if float(row['prevclose']) else 0
                }
        except Exception as sina_err:
            print(f"AKShare HK Sina query failed: {sina_err}")

        raise ValueError(f"AKShare无法找到或获取港股代码: {symbol}")
        
    except Exception as e:
        raise Exception(f"AKShare 港股查询失败: {str(e)}")


def search_stock(keyword: str, market: str = 'A') -> list:
    """
    搜索股票（可选功能）
    """
    try:
        import akshare as ak
        
        if market == 'A':
            df = ak.stock_zh_a_spot_em()
            results = df[df['名称'].str.contains(keyword) | df['代码'].str.contains(keyword)]
        else:
            df = ak.stock_hk_spot_em()
            results = df[df['名称'].str.contains(keyword) | df['代码'].str.contains(keyword)]
        
        return results[['代码', '名称', '最新价']].head(10).to_dict('records')
    except:
        return []
def get_forex_quote(symbol: str) -> Dict[str, Any]:
    """
    获取外汇/汇率实时行情
    symbol: 6位字母代码，如 "USDCNY", "EURUSD"
    """
    symbol_upper = symbol.upper()
    
    # 1. 尝试使用 AKShare
    try:
        import akshare as ak
        
        # 判断是否涉及人民币 (CNY)
        if 'CNY' in symbol_upper:
            df = ak.fx_spot_quote()
            # 标准化搜索格式: USD/CNY
            # 该接口返回的列名通常包含：'货币对', '买报价', '卖报价'
            # '货币对' 可能是 '美元/人民币' 或 'USD/CNY'
            search_regex = f"{symbol_upper[:3]}.*{symbol_upper[3:]}"
            # 兼容中文名匹配
            cn_map = {'USD': '美元', 'CNY': '人民币', 'EUR': '欧元', 'JPY': '日元', 'GBP': '英镑', 'AUD': '澳元', 'HKD': '港币'}
            cn_name = f"{cn_map.get(symbol_upper[:3], symbol_upper[:3])}/{cn_map.get(symbol_upper[3:], symbol_upper[3:])}"
            
            row = df[df['货币对'].str.contains(symbol_upper[:3], case=False) & df['货币对'].str.contains(symbol_upper[3:], case=False)]
            if not row.empty:
                row = row.iloc[0]
                price = float(row['买报价']) if row['买报价'] else None
                return {
                    'c': price,
                    'pc': price, # AKShare 实时接口通常不提供昨收，使用当前价占位
                    'name': row['货币对'],
                    'change_percent': 0
                }
        else:
            # 国际货币对
            df = ak.fx_pair_quote()
            row = df[df['货币对'].str.contains(symbol_upper[:3], case=False) & df['货币对'].str.contains(symbol_upper[3:], case=False)]
            if not row.empty:
                row = row.iloc[0]
                price = float(row['买报价']) if row['买报价'] else None
                return {
                    'c': price,
                    'pc': price,
                    'name': row['货币对'],
                    'change_percent': 0
                }
    except Exception as ak_err:
        print(f"AKShare Forex error: {ak_err}")

    # 2. 兜底方案: Yahoo Finance (格式: USDCNY=X)
    try:
        import yfinance as yf
        ticker = yf.Ticker(f"{symbol_upper}=X")
        info = ticker.fast_info
        
        if info.last_price:
            return {
                'c': info.last_price,
                'pc': info.previous_close,
                'name': f"{symbol_upper} (Forex)",
                'change_percent': ((info.last_price - info.previous_close) / info.previous_close) * 100 if info.previous_close else 0
            }
    except Exception as yf_err:
        raise Exception(f"外汇查询失败。AKShare & YFinance 均无法获取数据: {yf_err}")

    raise ValueError(f"未找到外汇标的数据: {symbol}")
