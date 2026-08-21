"""
Binance Provider - 加密货币行情数据
"""
from binance.spot import Spot
from typing import Dict, Any, List
from datetime import datetime


def get_crypto_quote(symbol: str) -> Dict[str, Any]:
    """
    获取加密货币实时行情
    symbol: 交易对，如 "BTCUSDT", "ETHUSDT"
    """
    try:
        client = Spot()  # 无需API key获取行情
        
        # 标准化symbol格式
        clean_symbol = symbol.upper().replace('-', '').replace('/', '')
        
        # 如果没有USDT后缀，尝试添加
        if not clean_symbol.endswith(('USDT', 'BUSD', 'BTC', 'ETH')):
            clean_symbol = clean_symbol + 'USDT'
        
        # 获取24小时ticker数据
        ticker = client.ticker_24hr(symbol=clean_symbol)
        
        return {
            'c': float(ticker['lastPrice']),           # current price
            'pc': float(ticker['prevClosePrice']),     # previous close
            'h': float(ticker['highPrice']),           # 24h high
            'l': float(ticker['lowPrice']),            # 24h low
            'o': float(ticker['openPrice']),           # open
            'volume': float(ticker['volume']),         # 24h volume
            'change_percent': float(ticker['priceChangePercent'])
        }
    except Exception as e:
        raise Exception(f"Binance 查询失败: {str(e)}")


def get_crypto_price_simple(symbol: str) -> float:
    """
    获取加密货币简单价格
    """
    try:
        quote = get_crypto_quote(symbol)
        return float(quote['c'])
    except Exception as e:
        raise Exception(f"Crypto 查询失败: {str(e)}")



def list_crypto_symbols() -> list:
    """
    获取Binance支持的交易对列表（可选功能）
    """
    try:
        client = Spot()
        info = client.exchange_info()
        symbols = [s['symbol'] for s in info['symbols'] if s['quoteAsset'] == 'USDT']
        return symbols
    except:
        return []

def get_klines(symbol: str, interval: str, start_time: int, end_time: int) -> List[Dict[str, Any]]:
    """
    获取K线数据
    symbol: 交易对
    interval: 时间间隔 ('1d', '1h', '15m')
    start_time: 开始时间戳 (ms)
    end_time: 结束时间戳 (ms)
    """
    try:
        client = Spot()
        
        # 标准化symbol
        clean_symbol = symbol.upper().replace('-', '').replace('/', '')
        if not clean_symbol.endswith(('USDT', 'BUSD', 'BTC', 'ETH')):
            clean_symbol = clean_symbol + 'USDT'
            
        # Binance klines response:
        # [
        #   [
        #     1499040000000,      // Open time
        #     "0.01634790",       // Open
        #     "0.80000000",       // High
        #     "0.01575800",       // Low
        #     "0.01577100",       // Close
        #     "148976.11500000",  // Volume
        #     1499644799999,      // Close time
        #     ...
        #   ]
        # ]
        klines = client.klines(symbol=clean_symbol, interval=interval, startTime=start_time, endTime=end_time)
        
        result = []
        for k in klines:
            result.append({
                'date': datetime.fromtimestamp(k[0] / 1000).strftime('%Y-%m-%d'),
                'open': float(k[1]),
                'high': float(k[2]),
                'low': float(k[3]),
                'close': float(k[4]),
                'volume': float(k[5])
            })
            
        return result
    except Exception as e:
        print(f"Binance klines error for {symbol}: {e}")
        return []
