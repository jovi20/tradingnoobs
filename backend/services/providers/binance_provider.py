"""
Binance Provider - 加密货币行情数据
"""
from binance.spot import Spot
from typing import Dict, Any


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
        client = Spot()
        clean_symbol = symbol.upper().replace('-', '').replace('/', '')
        if not clean_symbol.endswith(('USDT', 'BUSD', 'BTC', 'ETH')):
            clean_symbol = clean_symbol + 'USDT'
        
        ticker = client.ticker_price(symbol=clean_symbol)
        return float(ticker['price'])
    except Exception as e:
        raise Exception(f"Binance 查询失败: {str(e)}")


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
