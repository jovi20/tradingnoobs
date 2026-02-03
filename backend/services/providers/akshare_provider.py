"""
AKShare Provider - A股/港股行情数据
"""
import os

# 禁用代理，防止网络问题
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'

import akshare as ak
from typing import Optional, Dict, Any


def get_a_stock_quote(symbol: str) -> Dict[str, Any]:
    """
    获取A股实时行情
    symbol: 股票代码，如 "000001", "600519"
    """
    try:
        # 优先尝试 AKShare 分时接口
        df = ak.stock_zh_a_minute(symbol=symbol, period='1')
        if df.empty:
            raise ValueError(f"AKShare返回空数据: {symbol}")
            
        latest = df.iloc[-1]
        
        # 尝试获取股票名称
        name = symbol
        try:
            info_df = ak.stock_individual_info_em(symbol=symbol)
            # value of "股票简称" row
            name_row = info_df[info_df['item'] == '股票简称']
            if not name_row.empty:
                name = name_row.iloc[0]['value']
        except:
            pass # Ignore name fetch error, use symbol
        
        return {
            'c': float(latest['close']),
            'pc': float(latest['open']), 
            'h': float(latest['high']),
            'l': float(latest['low']),
            'o': float(latest['open']),
            'name': name, 
            'change_percent': 0 
        }
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
                'change_percent': ((info.last_price - info.previous_close) / info.previous_close) * 100
            }
        except Exception as yf_error:
            raise Exception(f"A股查询失败。AKShare: {str(ak_error)} | YFinance: {str(yf_error)}")


def get_hk_stock_quote(symbol: str) -> Dict[str, Any]:
    """
    获取港股实时行情
    symbol: 股票代码，如 "00700", "09988"
    """
    try:
        # 去除可能的.HK后缀
        clean_symbol = symbol.replace('.HK', '').replace('.hk', '').zfill(5)
        
        # 获取港股实时行情 (Sina源: stock_hk_spot)
        df = ak.stock_hk_spot()
        
        # 查找指定股票
        row = df[df['symbol'] == clean_symbol]
        
        if row.empty:
            raise ValueError(f"找不到港股代码: {symbol}")
        
        row = row.iloc[0]
        return {
            'c': float(row['lasttrade']) if row['lasttrade'] else None,
            'pc': float(row['prevclose']) if row['prevclose'] else None,
            'h': float(row['high']) if row['high'] else None,
            'l': float(row['low']) if row['low'] else None,
            'o': float(row['open']) if row['open'] else None,
            'name': row['name_cn'],   # Sina has name_cn and name_en
            'change_percent': float(row['percent']) if row['percent'] else None
        }
    except Exception as e:
        raise Exception(f"AKShare 港股查询失败: {str(e)}")


def search_stock(keyword: str, market: str = 'A') -> list:
    """
    搜索股票（可选功能）
    """
    try:
        if market == 'A':
            df = ak.stock_zh_a_spot_em()
            results = df[df['名称'].str.contains(keyword) | df['代码'].str.contains(keyword)]
        else:
            df = ak.stock_hk_spot_em()
            results = df[df['名称'].str.contains(keyword) | df['代码'].str.contains(keyword)]
        
        return results[['代码', '名称', '最新价']].head(10).to_dict('records')
    except:
        return []
