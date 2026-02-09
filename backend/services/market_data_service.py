"""
Trading Noobs - Unified Market Data Service
Routes requests to appropriate providers based on asset type:
- US Stocks → Finnhub
- A-Shares/HK Stocks → AKShare  
- Crypto → Binance
"""
import re
from datetime import datetime, timedelta
import finnhub
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import asyncio
from fastapi.concurrency import run_in_threadpool

from models import SystemSetting, AssetMetadata, AssetCoreType, AssetMarket, AssetCurrency, AssetRiskLevel
from services.providers import akshare_provider, binance_provider
from services.llm_service import classify_asset, classify_asset_rich

# Cache TTL in seconds (1 minute)
CACHE_TTL_SECONDS = 60


class MarketDataService:
    # Class-level cache shared across instances
    _quote_cache: Dict[str, Dict[str, Any]] = {}

    def _get_cached_quote(self, symbol: str, fetch_func):
        """
        Generic caching wrapper for any quote fetching function
        """
        symbol_upper = symbol.upper()
        cache_key = f"quote_{symbol_upper}"
        
        # Check cache
        cached = MarketDataService._quote_cache.get(cache_key)
        if cached:
            cache_age = datetime.now() - cached['timestamp']
            if cache_age.total_seconds() < CACHE_TTL_SECONDS:
                return cached['data']
        
        # Fetch fresh data
        try:
            data = fetch_func()
            
            # Update cache
            MarketDataService._quote_cache[cache_key] = {
                'data': data,
                'timestamp': datetime.now()
            }
            return data
        except Exception as e:
            print(f"Error fetching quote for {symbol}: {e}")
            raise e
    _asset_type_cache: Dict[str, str] = {}
    
    def __init__(self, db: Session):
        self.db = db
        self._finnhub_client = None

    async def _fetch_with_timeout(self, coro, timeout=5):
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            raise Exception(f"Market data request timed out ({timeout}s)")

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
            r'^[48][37]\d{4}$', # 北交所 43xxxx, 83xxxx, 87xxxx
        ]
        for pattern in a_share_patterns:
            if re.match(pattern, symbol_upper):
                return 'A_STOCK'
        
        # Fund detection (6-digit codes starting with specific prefixes)
        fund_patterns = [
            r'^5[016]\d{4}$',   # 场内基金 (50, 51, 56)
            r'^1[568]\d{4}$',   # 场内基金 (15, 16, 18)
            r'^0\d{5}$',        # 场外基金 (0xxxxx - note: 000xxx collision with SZ stock handled by order)
        ]
        for pattern in fund_patterns:
            if re.match(pattern, symbol_upper):
                return 'ETF_EQUITY' # Treating all funds as ETF_EQUITY for simplicity in types for now
        
        # HK Stock detection
        if symbol_upper.endswith('.HK') or exchange_upper in ['HKEX', 'HK', 'HONG KONG']:
            return 'HK_STOCK'
        if re.match(r'^\d{5}$', symbol_upper):  # 5-digit HK code
            return 'HK_STOCK'
        
        # Forex detection: 6-letter alphabetic pairs
        # Common pattern: USDCNY, EURUSD, GBPJPY
        if re.match(r'^[A-Z]{6}$', symbol_upper):
             # We can be more specific, but for now 6 alphabetic letters is a strong hint for FX
             return 'FOREX'

        # US Stock detection (Basic: 1-5 letters, 7-8 letters)
        if re.match(r'^[A-Z\.]{1,8}$', symbol_upper):
            return 'US_STOCK'

        # Default/Unknown
        return 'UNKNOWN'

    async def get_or_create_asset_metadata(self, symbol: str, name: Optional[str] = None, exchange: Optional[str] = None) -> AssetMetadata:
        """
        Get asset metadata from DB, or create/detect it using rules and LLM.
        """
        symbol_upper = symbol.upper()
        
        # 1. Check Database
        metadata = self.db.query(AssetMetadata).filter(AssetMetadata.symbol == symbol_upper).first()
        if metadata and metadata.core_type: # Ensure it's fully populated
            return metadata
            
        if not metadata:
            metadata = AssetMetadata(symbol=symbol_upper, name=name or symbol_upper)
            self.db.add(metadata)
        
        # 2. Rule-based Detection (Market and Currency)
        base_type = self.detect_asset_type(symbol, exchange)
        
        # Market Mapping
        if base_type == 'A_STOCK':
            metadata.market = AssetMarket.A_SHARE
            metadata.currency = AssetCurrency.CNY
            metadata.core_type = AssetCoreType.STOCK
        elif base_type == 'HK_STOCK':
            metadata.market = AssetMarket.HK
            metadata.currency = AssetCurrency.HKD
            metadata.core_type = AssetCoreType.STOCK
        elif base_type == 'CRYPTO':
            metadata.core_type = AssetCoreType.CRYPTO
            metadata.market = AssetMarket.CRYPTO
            metadata.currency = AssetCurrency.USD # Most pairs are USDT/USD
        elif base_type == 'ETF_EQUITY':
            # Could be A-share or HK or US. Let's check symbol.
            if re.match(r'^\d{6}$', symbol_upper):
                metadata.market = AssetMarket.A_SHARE
                metadata.currency = AssetCurrency.CNY
            metadata.core_type = AssetCoreType.FUND
        elif base_type == 'FOREX':
            metadata.market = AssetMarket.FOREX
            metadata.core_type = AssetCoreType.FX
            # Currency depends on the pair, LLM is better here
            
        # 3. LLM Classification for missing/nuanced fields
        try:
            rich_info = await classify_asset_rich(self.db, symbol_upper, name, exchange)
            if rich_info:
                # Only fill if not already set by rules, or override if needed
                if not metadata.core_type: metadata.core_type = AssetCoreType(rich_info['core_type'])
                if not metadata.market: metadata.market = AssetMarket(rich_info['market'])
                if not metadata.currency: metadata.currency = AssetCurrency(rich_info['currency'])
                if not metadata.risk_level: metadata.risk_level = AssetRiskLevel(rich_info['risk_level'])
                
                metadata.sector = rich_info.get('sector', 'General')
                metadata.instrument = rich_info.get('instrument', 'Spot')
                
        except Exception as e:
            print(f"Error in rich LLM detection for {symbol}: {e}")
            
        # 4. Final Fallbacks
        if not metadata.core_type:
             metadata.core_type = AssetCoreType.STOCK if base_type == 'US_STOCK' else AssetCoreType.STOCK
        if not metadata.market:
             metadata.market = AssetMarket.US if base_type == 'US_STOCK' else AssetMarket.US
        if not metadata.currency:
             metadata.currency = AssetCurrency.USD
        if not metadata.risk_level:
             metadata.risk_level = AssetRiskLevel.GROWTH # Default
             if metadata.core_type == AssetCoreType.CRYPTO:
                 metadata.risk_level = AssetRiskLevel.AGGRESSIVE
             elif metadata.core_type == AssetCoreType.FX:
                 metadata.risk_level = AssetRiskLevel.MODERATE
        
        self.db.commit()
        self.db.refresh(metadata)
        return metadata

    async def detect_asset_type_enhanced(self, symbol: str, exchange: Optional[str] = None) -> str:
        """
        Maintains backward compatibility but uses the new metadata system.
        """
        metadata = await self.get_or_create_asset_metadata(symbol, exchange=exchange)
        return metadata.core_type.value if metadata.core_type else "EQUITY"

    async def get_quote(
        self, 
        symbol: str, 
        exchange: Optional[str] = None,
        core_type: Optional[str] = None,
        market: Optional[str] = None,
        instrument: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get quote from appropriate provider based on asset type
        Hints (core_type, market, instrument) help in choosing the right provider
        """
        # If core_type is provided, we can use it directly or refine with market
        asset_type = core_type
        if not asset_type:
            asset_type = self.detect_asset_type(symbol, exchange)
        
        # Mapping hints to our internal provider routing logic
        async def fetch_wrapper():
            if asset_type == 'CRYPTO' or market == 'CRYPTO':
                return await self._fetch_with_timeout(run_in_threadpool(binance_provider.get_crypto_quote, symbol))
            
            # Prioritize US Market (Stocks, ETFs)
            elif market == 'US' or asset_type == 'US_STOCK' or (asset_type == 'STOCK' and market == 'US'):
                # Finnhub has its own internal caching, but let's wrap it for consistency or reuse its logic
                # Since _get_finnhub_quote already caches, we can just call it.
                # However, to be consistent with others, we could wrap it, but double caching is harmless.
                return await self._fetch_with_timeout(self._get_finnhub_quote(symbol))
            
            elif asset_type == 'A_STOCK' or market == 'A_SHARE':
                return await self._fetch_with_timeout(run_in_threadpool(akshare_provider.get_a_stock_quote, symbol))
            
            elif asset_type == 'HK_STOCK' or market == 'HK':
                return await self._fetch_with_timeout(run_in_threadpool(akshare_provider.get_hk_stock_quote, symbol))
            
            elif asset_type == 'FUND' or asset_type == 'ETF_EQUITY' or asset_type == 'ETF_BOND' or asset_type == 'ETF_COMMODITY':
                return await self._fetch_with_timeout(run_in_threadpool(akshare_provider.get_fund_quote, symbol))

            elif asset_type == 'FX' or asset_type == 'FOREX' or market == 'FOREX':
                return await self._fetch_with_timeout(run_in_threadpool(akshare_provider.get_forex_quote, symbol))
                
            else:
                # Final fallback
                final_type = self.detect_asset_type(symbol, exchange)
                if final_type == 'CRYPTO': return await self._fetch_with_timeout(run_in_threadpool(binance_provider.get_crypto_quote, symbol))
                if final_type == 'A_STOCK': return await self._fetch_with_timeout(run_in_threadpool(akshare_provider.get_a_stock_quote, symbol))
                if final_type == 'HK_STOCK': return await self._fetch_with_timeout(run_in_threadpool(akshare_provider.get_hk_stock_quote, symbol))
                if final_type == 'ETF_EQUITY': return await self._fetch_with_timeout(run_in_threadpool(akshare_provider.get_fund_quote, symbol))
                if final_type == 'US_STOCK': return await self._fetch_with_timeout(self._get_finnhub_quote(symbol))
                if final_type == 'FOREX': return await self._fetch_with_timeout(run_in_threadpool(akshare_provider.get_forex_quote, symbol))
                
                raise ValueError(f"Unknown asset type for symbol: {symbol}")

        # Use the generic cache wrapper
        # Note: _get_cached_quote is synchronous logic but fetch_wrapper is async
        # We need an async aware cache wrapper or handle it here
        
        symbol_upper = symbol.upper()
        cache_key = f"quote_{symbol_upper}"
        
        # Check cache
        cached = MarketDataService._quote_cache.get(cache_key)
        if cached:
            cache_age = datetime.now() - cached['timestamp']
            if cache_age.total_seconds() < CACHE_TTL_SECONDS:
                return cached['data']
        
        # Fetch fresh
        data = await fetch_wrapper()
        
        # Update cache
        MarketDataService._quote_cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now()
        }
        return data

    async def _get_finnhub_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get quote from Finnhub (US stocks) with caching and fallback to YFinance
        """
        symbol_upper = symbol.upper()
        cache_key = f"finnhub_{symbol_upper}"
        
        # Check cache first
        cached = MarketDataService._quote_cache.get(cache_key)
        if cached:
            cache_age = datetime.now() - cached['timestamp']
            if cache_age.total_seconds() < CACHE_TTL_SECONDS:
                print(f"[Cache HIT] Finnhub quote for {symbol_upper} from cache")
                return cached['data']
            else:
                print(f"[Cache EXPIRED] Finnhub quote for {symbol_upper}")
        
        # 1. Try Finnhub first
        try:
            client = self._get_finnhub_client()
            if client:
                data = await run_in_threadpool(client.quote, symbol_upper)
                # Check if data is valid (Finnhub sometimes returns 0s for invalid symbols, but usually c=0)
                # But for valid symbol c should be > 0 ideally, or at least pc
                if data.get('c') == 0 and data.get('pc') == 0:
                     raise ValueError("Finnhub returned empty data")
                     
                result = {
                    'c': data.get('c'),   # current price
                    'pc': data.get('pc'), # previous close
                    'h': data.get('h'),   # high
                    'l': data.get('l'),   # low
                    'o': data.get('o'),   # open
                    'd': data.get('d'),   # change
                    'dp': data.get('dp'), # change percent
                    'name': symbol_upper # Finnhub quote doesn't return name, use symbol
                }
                
                # Update cache
                MarketDataService._quote_cache[cache_key] = {
                    'data': result,
                    'timestamp': datetime.now()
                }
                print(f"[Cache UPDATE] Finnhub quote for {symbol_upper} cached")
                
                return result
        except Exception as e:
            print(f"Finnhub error for {symbol}: {e}")
            # Continue to fallback
            
        # 2. Fallback to Yahoo Finance
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol.upper())
            info = await run_in_threadpool(getattr, ticker, "fast_info")
            
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

    async def validate_symbol(self, symbol: str, exchange: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate if a symbol exists and return basic info
        """
        try:
            # Get rich metadata (handles DB cache internally)
            metadata = await self.get_or_create_asset_metadata(symbol, exchange=exchange)
            
            # Get current quote
            quote = await self.get_quote(symbol, exchange)
            
            return {
                'valid': True,
                'symbol': symbol.upper(),
                'asset_type': metadata.core_type.value if metadata.core_type else "EQUITY",
                'price': quote.get('c'),
                'name': quote.get('name') or metadata.name,
                'metadata': {
                    'name': metadata.name,
                    'core_type': metadata.core_type.value if metadata.core_type else None,
                    'market': metadata.market.value if metadata.market else None,
                    'currency': metadata.currency.value if metadata.currency else None,
                    'sector': metadata.sector,
                    'risk_level': metadata.risk_level.value if metadata.risk_level else None,
                    'instrument': metadata.instrument
                },
                'provider': self._get_provider_name(metadata.core_type.value if metadata.core_type else "EQUITY")
            }
        except Exception as e:
            # Generate candidates on failure
            candidates = []
            symbol_upper = symbol.upper()
            raw_error = str(e)
            
            # Crypto Smart Suggestions
            # If 3-5 letters, suggest adding USDT
            # But avoid double-suffixing if user is already typing the suffix (e.g. "ETHUS" -> "ETHUSUSDT" is bad)
            # So we skip if it ends with common suffix starts
            
            is_potential_len = re.match(r'^[A-Z0-9]{3,5}$', symbol_upper)
            is_pure_numeric = re.match(r'^\d+$', symbol_upper)
            has_partial_suffix = symbol_upper.endswith(('U', 'US', 'USD', 'BUS', 'BUSD'))
            
            if is_potential_len and not is_pure_numeric and not has_partial_suffix:
                 candidates.append({
                     'symbol': f"{symbol_upper}USDT",
                     'asset_type': 'CRYPTO',
                     'reason': '推荐: Binance 交易对'
                 })
            
            # Sanitize Error Message
            error_msg = "查询失败，请检查代码是否正确"
            
            if "Invalid symbol" in raw_error or "-1121" in raw_error:
                error_msg = "未找到该交易对 (Invalid Symbol)"
            elif "not found" in raw_error.lower() or "404" in raw_error:
                error_msg = "未找到该标的"
            elif "empty data" in raw_error:
                error_msg = "暂无该标的数据"
            elif "Unauthorized" in raw_error or "401" in raw_error:
                error_msg = "API 密钥无效或过期"
            elif "AKShare" in raw_error:
                error_msg = "数据源 (AKShare) 查询失败，请稍后再试"
            elif "Binance" in raw_error:
                error_msg = "数据源 (Binance) 查询失败，请检查交易对格式"
            
            return {
                'valid': False,
                'symbol': symbol.upper(),
                'error': error_msg,
                'candidates': candidates,
                'raw_error': raw_error # Optional: keep raw error for debug in console if needed, but UI shows 'error'
            }

    def _get_provider_name(self, asset_type: str) -> str:
        """Get provider name for display"""
        return {
            'A_STOCK': 'AKShare',
            'HK_STOCK': 'AKShare', 
            'CRYPTO': 'Binance',
            'US_STOCK': 'Finnhub',
            'FOREX': 'AKShare/YFinance',
            'ETF_EQUITY': 'AKShare'
        }.get(asset_type, 'Unknown')

    async def validate_api_key(self):
        """Test if the Finnhub API key works"""
        try:
            return await self._get_finnhub_quote('AAPL')
        except Exception as e:
            raise Exception(f"Validation failed: {str(e)}")
