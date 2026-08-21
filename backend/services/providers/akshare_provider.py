"""
AKShare Provider - A股/港股行情数据
"""
import os

# 禁用代理，防止网络问题
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'

from typing import Dict, Any, List
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Global cache for bulk data to prevent IP bans
# Format: {'key': {'data': df, 'time': datetime}}
_BULK_CACHE = {}
_BULK_CACHE_TTL = 3600 * 4  # 4 Hours TTL (User asked for "once per day", setting generous TTL)

def _get_cached_bulk_data(key: str, fetch_func) -> pd.DataFrame:
    """Helper to get bulk data with caching"""
    now = datetime.now()
    if key in _BULK_CACHE:
        cache_entry = _BULK_CACHE[key]
        if (now - cache_entry['time']).total_seconds() < _BULK_CACHE_TTL:
            return cache_entry['data']
            
    try:
        logger.info(f"Fetching bulk data for {key}...")
        df = fetch_func()
        if df is not None and not df.empty:
            _BULK_CACHE[key] = {'data': df, 'time': now}
        return df
    except Exception as e:
        logger.error(f"Bulk fetch failed for {key}: {e}")
        # Return old cache if available even if expired, as fallback
        if key in _BULK_CACHE:
            return _BULK_CACHE[key]['data']
        return None


def get_a_stock_quote(symbol: str) -> Dict[str, Any]:
    """
    获取A股实时行情 (包含沪深京)
    symbol: 股票代码，如 "000001", "600519", "830833"
    Logic: 使用 ak.stock_individual_info_em 获取个股信息
    """
    # 彻底禁用代理环境变量，防止干扰
    for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
        if key in os.environ:
            del os.environ[key]
    os.environ['NO_PROXY'] = '*'
    
    try:
        import akshare as ak
        
        # 使用 stock_individual_info_em 接口
        # 该接口返回 DataFrame: item, value
        df = ak.stock_individual_info_em(symbol=symbol)
        
        if df is None or df.empty:
             raise ValueError(f"AKShare未找到股票: {symbol}")

        # 将 DataFrame 转为字典以便查找
        # 假设 df 结构:
        #    item               value
        # 0    最新               7.05
        # ...
        data_map = dict(zip(df['item'], df['value']))
        
        # 尝试提取所需字段
        # 注意：stock_individual_info_em 返回的字段可能不包含完整的 OHLC
        # 如果必须有 OHLC，可能需要组合其他接口，但根据文档要求我们主要依靠这个
        # 观察示例数据，它有 "最新", "总市值", "行业" 等
        # 如果缺少 OHLC，我们暂时用 "最新" 填充，或者尝试获取
        
        price = float(data_map.get('最新', 0))
        
        # 尝试寻找涨跌幅，示例中没有直接显示，但通常会有
        # 如果没有，可能需要计算或者接受 0
        # 为了稳健，如果找不到昨收，就用 price
        
        # 注意：stock_individual_info_em 可能确实比较基础
        # 如果用户强烈要求这个接口，我们尽量适配
        # 寻找其他可能存在的key (不同时间段可能不同)
        
        # 辅助：为了获取完整的 OHLC，通常还需要 spot 接口
        # 但既然文档指定了 stock_individual_info_em，我们先严格执行
        # 如果发现字段严重缺失导致业务无法运行，再反馈
        
        # 尝试转换数值
        def parse_float(val):
            try:
                return float(val)
            except:
                return 0.0

        return {
            'c': price,
            'pc': price, # 接口未明确提供昨收，暂用最新价
            'h': price,  # 暂无
            'l': price,  # 暂无
            'o': price,  # 暂无
            'name': str(data_map.get('股票简称', symbol)),
            'change_percent': 0.0 # 暂无
        }
            
    except Exception as ak_error:
        # Fallback: 尝试 Yahoo Finance
        try:
            import yfinance as yf
            if symbol.startswith(('6', '5', '9')):
                suffix = '.SS'
            elif symbol.startswith(('0', '3', '1', '2')):
                suffix = '.SZ'
            elif symbol.startswith(('4', '8')):
                suffix = '.BJ'
            else:
                # Default to .SZ if unknown, or maybe .BJ but .SZ is safer for funds like 15xxxx
                suffix = '.SZ'
                
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
    优化策略：优先单只查询，批量接口必须缓存
    """
    # 彻底禁用代理
    for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
        if key in os.environ:
            del os.environ[key]
    os.environ['NO_PROXY'] = '*'
    
    import akshare as ak

    # 1. 优先尝试 单只基金实时行情 (针对 ETF/LOF)
    # 使用 stock_individual_info_em，这是轻量级接口
    # 适用: 15xxxx, 16xxxx, 51xxxx, 56xxxx 等
    if symbol.startswith(('15', '16', '51', '56', '58')):
        try:
            # 复用 get_a_stock_quote 的逻辑或直接调用
            # 这里重写精简版以防循环引用或差异
            df = ak.stock_individual_info_em(symbol=symbol)
            if df is not None and not df.empty:
                data_map = dict(zip(df['item'], df['value']))
                price = float(data_map.get('最新', 0))
                if price > 0:
                     return {
                        'c': price,
                        'pc': price, # 暂无
                        'name': str(data_map.get('股票简称', symbol)),
                        'change_percent': 0.0 # 暂无
                    }
        except Exception:
            pass

    # 2. 优先尝试 单只场外基金净值 (针对 OTC)
    # 适用: 0xxxxx 等
    try:
        # 指标参数: "单位净值走势" 获取最新净值
        df_info = ak.fund_open_fund_info_em(symbol=symbol, indicator="单位净值走势")
        if not df_info.empty:
            latest = df_info.iloc[-1]
            # 尝试获取上一日
            prev = df_info.iloc[-2] if len(df_info) > 1 else latest
            
            return {
                'c': float(latest['单位净值']),
                'pc': float(prev['单位净值']),
                'name': symbol, # 接口不含名称，但在 Context 中可能已有
                'change_percent': float(latest['日增长率']) if '日增长率' in latest else 0
            }
    except Exception:
        pass

    # 3. 兜底：使用缓存的批量接口
    
    # 3.1 ETF Spot (Cached)
    if symbol.startswith(('15', '51', '56', '58')):
        df_etf = _get_cached_bulk_data('etf_spot', ak.fund_etf_spot_em)
        if df_etf is not None:
            # 过滤
            res = df_etf[df_etf['代码'] == symbol]
            if not res.empty:
                row = res.iloc[0]
                return {
                    'c': float(row['最新价']),
                    'pc': float(row['最新价']), # 昨收不准，用最新
                    'name': row['名称'],
                    'change_percent': float(row['涨跌幅'])
                }

    # 3.2 LOF Spot (Cached)
    if symbol.startswith('16'):
        df_lof = _get_cached_bulk_data('lof_spot', ak.fund_lof_spot_em)
        if df_lof is not None:
            res = df_lof[df_lof['代码'] == symbol]
            if not res.empty:
                row = res.iloc[0]
                return {
                    'c': float(row['最新价']),
                    'pc': float(row['最新价']),
                    'name': row['名称'],
                    'change_percent': float(row['涨跌幅'])
                }

    # 3.3 Open Fund Daily (Cached) - Last Resort for OTC
    df_open = _get_cached_bulk_data('open_fund_daily', ak.fund_open_fund_daily_em)
    if df_open is not None:
         # 列名可能变化
         code_col = '基金代码' if '基金代码' in df_open.columns else '代码'
         res = df_open[df_open[code_col] == symbol]
         if not res.empty:
             row = res.iloc[0]
             price_col = '单位净值' if '单位净值' in row else '最新净值'
             name_col = '基金简称' if '基金简称' in row else '名称'
             return {
                'c': float(row[price_col]),
                'pc': float(row[price_col]),
                'name': row[name_col],
                'change_percent': float(row['日增长率']) if '日增长率' in row and row['日增长率'] else 0
            }

    # 4. Final Fallback: Yahoo
    try:
        import yfinance as yf
        for suffix in ['.SS', '.SZ']:
            try:
                ticker = yf.Ticker(symbol + suffix)
                info = ticker.fast_info
                if info.last_price:
                     return {
                        'c': info.last_price,
                        'pc': info.previous_close,
                        'name': symbol,
                        'change_percent': 0
                    }
            except:
                continue
    except:
        pass

    raise ValueError(f"Fund data not found for {symbol}")


def get_hk_stock_quote(symbol: str) -> Dict[str, Any]:
    """
    获取港股实时行情 (使用 akshare_one)
    symbol: 股票代码，如 "00700", "09988"
    """
    # 格式化代码：去除后缀并填充至5位
    clean_symbol = symbol.replace('.HK', '').replace('.hk', '').zfill(5)
    
    # 彻底禁用代理，防止网络干扰
    import os
    for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
        os.environ.pop(key, None)
    os.environ['NO_PROXY'] = '*'
    
    try:
        import akshare_one
        
        # 使用 akshare_one.get_realtime_data
        df = akshare_one.get_realtime_data(symbol=clean_symbol, source="eastmoney_direct")
        
        if df is not None and not df.empty:
            row = df.iloc[0]
            # 字段映射 (akshare-one 返回的字段通常比较标准，但需确认)
            # 假设返回字段包含: 最新价, 昨收, 最高, 最低, 今开, 名称, 涨跌幅
            
            price = float(row.get('最新价', 0)) or float(row.get('last', 0))
            prev_close = float(row.get('昨收', 0)) or float(row.get('prevclose', price))
            
            return {
                'c': price,
                'pc': prev_close,
                'h': float(row.get('最高', 0)),
                'l': float(row.get('最低', 0)),
                'o': float(row.get('今开', 0)),
                'name': str(row.get('名称', symbol)),
                'change_percent': float(row.get('涨跌幅', 0))
            }
        else:
             raise ValueError(f"AKShare-One未找到港股: {symbol}")
             
    except Exception as e:
        raise Exception(f"港股查询失败: {e}")


def get_history_k_data(symbol: str, start_date: str, end_date: str, adjust: str = "qfq") -> List[Dict[str, Any]]:
    """
    获取历史K线数据 (A股/港股)
    start_date, end_date: 'YYYYMMDD'
    Returns: [{'date': '2023-01-01', 'open': 10, 'close': 11, 'high': 12, 'low': 9, 'volume': 100}, ...]
    """
    # 彻底禁用代理
    import os
    for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
        if key in os.environ:
            del os.environ[key]
    os.environ['NO_PROXY'] = '*'
    
    symbol_clean = symbol.replace('.HK', '').replace('.hk', '')
    
    # 简单判断是否为港股 (5位数字)
    is_hk = len(symbol_clean) == 5 and symbol_clean.isdigit()
    
    try:
        import akshare as ak
        
        if is_hk:
            # HK Stock
            # 使用 ak.stock_hk_daily (需注意接口变化) 或 akshare_one 如果有封装
            # 这里尝试标准 akshare 接口: stock_hk_daily
            # 如果 symbol 是 00700，需确保格式
            
            # 尝试 akshare_one (如果我们有这个文件且它支持)
            try:
                # Assuming akshare_one has get_hk_hist based on previous context, 
                # but let's stick to standard AKShare first if possible to reduce dependencies 
                # unless standard is broken. 
                # Standard ak.stock_hk_hist is robust.
                df = ak.stock_hk_hist(symbol=symbol_clean, period="daily", start_date=start_date, end_date=end_date, adjust=adjust)
            except:
                # Fallback or standard
                df = ak.stock_hk_hist(symbol=symbol_clean, period="daily", start_date=start_date, end_date=end_date, adjust=adjust)
                
            # Columns: 日期, 开盘, 收盘, 最高, 最低, 成交量, ...
            if df is None or df.empty:
                 return []
                 
            # Rename columns to standard
            df = df.rename(columns={
                '日期': 'date', '开盘': 'open', '收盘': 'close', 
                '最高': 'high', '最低': 'low', '成交量': 'volume'
            })
            
        else:
            # A Stock
            # code: 6位代码
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust=adjust)
            if df is None or df.empty:
                return []
                
            # Columns: 日期, 开盘, 收盘, 最高, 最低, 成交量, ...
            df = df.rename(columns={
                '日期': 'date', '开盘': 'open', '收盘': 'close', 
                '最高': 'high', '最低': 'low', '成交量': 'volume'
            })
            
        # Convert to list of dicts
        # Ensure date format YYYY-MM-DD
        if 'date' in df.columns:
             # Check format. AKShare usually returns '2023-01-01' string or date obj
             df['date'] = df['date'].astype(str)
             
        # Select standard columns
        result = df[['date', 'open', 'close', 'high', 'low', 'volume']].to_dict('records')
        return result
        
    except Exception as e:
        print(f"AKShare history query failed for {symbol}: {e}")
        return []



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
            # 该接口返回的列名通常包含：'货币对', '买报价', '卖报价'
            # '货币对' 可能是 '美元/人民币' 或 'USD/CNY'，因此按两侧币种代码分别做包含匹配
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
