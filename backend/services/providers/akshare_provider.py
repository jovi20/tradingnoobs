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
    获取A股实时行情
    symbol: 股票代码，如 "000001", "600519"
    """
    # 首先尝试 AKShare 实时行情接口
    try:
        import akshare as ak
        
        # 使用东方财富实时行情（更稳定）
        df = ak.stock_zh_a_spot_em()
        
        # 查找指定股票
        row = df[df['代码'] == symbol]
        
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
        else:
            raise ValueError(f"AKShare未找到股票: {symbol}")
            
    except Exception as ak_error:
        # Fallback: 尝试 Yahoo Finance
        try:
            import yfinance as yf
            suffix = '.SS' if symbol.startswith('6') else '.SZ'
            ticker = yf.Ticker(symbol + suffix)
            info = ticker.fast_info
            
            # YF数据可能为空
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


def get_hk_stock_quote(symbol: str) -> Dict[str, Any]:
    """
    获取港股实时行情
    symbol: 股票代码，如 "00700", "09988"
    """
    try:
        import akshare as ak
        
        # 去除可能的.HK后缀
        clean_symbol = symbol.replace('.HK', '').replace('.hk', '').zfill(5)
        
        # 获取港股实时行情 (东方财富)
        df = ak.stock_hk_spot_em()
        
        # 查找指定股票
        row = df[df['代码'] == clean_symbol]
        
        if row.empty:
            raise ValueError(f"找不到港股代码: {symbol}")
        
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
