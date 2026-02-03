"""
Trading Noobs - Unified Market Data Service
Routes requests to appropriate providers based on asset type:
- US Stocks → Finnhub
- A-Shares/HK Stocks → AKShare  
- Crypto → Binance
"""
import re
import finnhub
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from models import SystemSetting
from services.providers import akshare_provider, binance_provider


class MarketDataService:
    def __init__(self, db: Session):
        self.db = db
        self._finnhub_client = None

    def _get_finnhub_client(self):
        """Lazy load Finnhub client"""
        if self._finnhub_client is None:
            setting = self.db.query(SystemSetting).filter(
                SystemSetting.key == 'finnhub_api_key'
            ).first()
            if setting and setting.value:
                self._finnhub_client = finnhub.Client(api_key=setting.value)
        return self._finnhub_client

    def detect_asset_type(self, symbol: str, exchange: Optional[str] = None) -> str:
        """
        Detect asset type based on symbol and exchange
        Returns: 'A_STOCK', 'HK_STOCK', 'CRYPTO', 'US_STOCK'
        """
        symbol_upper = symbol.upper()
        exchange_upper = (exchange or '').upper()
        
        # Crypto detection
        crypto_patterns = ['USDT', 'BUSD', 'BTC', 'ETH', 'BNB']
        if any(symbol_upper.endswith(p) for p in crypto_patterns):
            return 'CRYPTO'
        if 'BINANCE' in exchange_upper or exchange_upper in ['CRYPTO', 'BINANCE']:
            return 'CRYPTO'
        
        # A-Share detection (6-digit codes)
        a_share_patterns = [
            r'^0[0-3]\d{4}$',   # 深圳主板/中小板 000xxx, 001xxx, 002xxx, 003xxx
            r'^300\d{3}$',      # 创业板 300xxx
            r'^6[0-9]\d{4}$',   # 上海主板 600xxx, 601xxx, 603xxx, 688xxx
        ]
        for pattern in a_share_patterns:
            if re.match(pattern, symbol_upper):
                return 'A_STOCK'
        
        # HK Stock detection
        if symbol_upper.endswith('.HK') or exchange_upper in ['HKEX', 'HK', 'HONG KONG']:
            return 'HK_STOCK'
        if re.match(r'^\d{5}$', symbol_upper):  # 5-digit HK code
            return 'HK_STOCK'
        
        # US Stock detection (Basic: 1-5 letters, maybe dots for BRK.B)
        if re.match(r'^[A-Z\.]{1,8}$', symbol_upper):
            return 'US_STOCK'

        # Default/Unknown
        return 'UNKNOWN'

    def get_quote(self, symbol: str, exchange: Optional[str] = None) -> Dict[str, Any]:
        """
        Get quote from appropriate provider based on asset type
        """
        asset_type = self.detect_asset_type(symbol, exchange)
        
        if asset_type == 'CRYPTO':
            return binance_provider.get_crypto_quote(symbol)
        
        elif asset_type == 'A_STOCK':
            return akshare_provider.get_a_stock_quote(symbol)
        
        elif asset_type == 'HK_STOCK':
            return akshare_provider.get_hk_stock_quote(symbol)
        
        elif asset_type == 'US_STOCK':
            return self._get_finnhub_quote(symbol)
            
        else:
            raise ValueError(f"Unknown asset type for symbol: {symbol}")

    def _get_finnhub_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get quote from Finnhub (US stocks) with fallback to YFinance
        """
        # 1. Try Finnhub first
        try:
            client = self._get_finnhub_client()
            if client:
                data = client.quote(symbol.upper())
                # Check if data is valid (Finnhub sometimes returns 0s for invalid symbols, but usually c=0)
                # But for valid symbol c should be > 0 ideally, or at least pc
                if data.get('c') == 0 and data.get('pc') == 0:
                     raise ValueError("Finnhub returned empty data")
                     
                return {
                    'c': data.get('c'),   # current price
                    'pc': data.get('pc'), # previous close
                    'h': data.get('h'),   # high
                    'l': data.get('l'),   # low
                    'o': data.get('o'),   # open
                    'd': data.get('d'),   # change
                    'dp': data.get('dp'), # change percent
                    'name': symbol.upper() # Finnhub quote doesn't return name, use symbol
                }
        except Exception as e:
            print(f"Finnhub error for {symbol}: {e}")
            # Continue to fallback
            
        # 2. Fallback to Yahoo Finance
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol.upper())
            info = ticker.fast_info
            
            if not info.last_price:
                 raise ValueError("Yahoo Finance returned empty data")

            previous_close = info.previous_close
            current_price = info.last_price
            change_percent = 0
            if previous_close:
                change_percent = ((current_price - previous_close) / previous_close) * 100

            return {
                'c': current_price,
                'pc': previous_close,
                'h': info.day_high,
                'l': info.day_low,
                'o': info.open,
                'd': current_price - previous_close,
                'dp': change_percent,
                'name': symbol.upper()
            }
        except Exception as yf_error:
            raise Exception(f"Market data failed. Finnhub & YFinance both failed for {symbol}: {str(yf_error)}")

    def validate_symbol(self, symbol: str, exchange: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate if a symbol exists and return basic info
        """
        try:
            quote = self.get_quote(symbol, exchange)
            asset_type = self.detect_asset_type(symbol, exchange)
            return {
                'valid': True,
                'symbol': symbol.upper(),
                'asset_type': asset_type,
                'price': quote.get('c'),
                'name': quote.get('name'),
                'provider': self._get_provider_name(asset_type)
            }
        except Exception as e:
            # Generate candidates on failure
            candidates = []
            symbol_upper = symbol.upper()
            
            # Crypto Smart Suggestions
            # If 3-5 letters and not purely numeric, suggest adding USDT
            # (e.g. BTC -> BTCUSDT)
            if re.match(r'^[A-Z]{3,5}$', symbol_upper):
                 candidates.append({
                     'symbol': f"{symbol_upper}USDT",
                     'asset_type': 'CRYPTO',
                     'reason': '推荐: Binance 交易对'
                 })
            
            return {
                'valid': False,
                'symbol': symbol.upper(),
                'error': str(e),
                'candidates': candidates
            }

    def _get_provider_name(self, asset_type: str) -> str:
        """Get provider name for display"""
        return {
            'A_STOCK': 'AKShare',
            'HK_STOCK': 'AKShare', 
            'CRYPTO': 'Binance',
            'US_STOCK': 'Finnhub'
        }.get(asset_type, 'Unknown')

    def validate_api_key(self):
        """Test if the Finnhub API key works"""
        try:
            return self._get_finnhub_quote('AAPL')
        except Exception as e:
            raise Exception(f"Validation failed: {str(e)}")
