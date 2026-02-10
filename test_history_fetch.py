
import sys
import os
import asyncio
from datetime import datetime, timedelta

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.database import SessionLocal
from backend.services.market_data_service import MarketDataService

async def test_history():
    db = SessionLocal()
    service = MarketDataService(db)
    
    start = datetime.now() - timedelta(days=30)
    end = datetime.now()
    
    print("Testing A-Share (600519)...")
    res = await service.get_price_history("600519", start, end)
    print(f"Rows: {len(res)}")
    if res: print(f"Sample: {res[0]}")
    
    print("\nTesting US Stock (AAPL)...")
    res = await service.get_price_history("AAPL", start, end)
    print(f"Rows: {len(res)}")
    if res: print(f"Sample: {res[0]}")
    
    print("\nTesting Crypto (BTCUSDT)...")
    res = await service.get_price_history("BTCUSDT", start, end)
    print(f"Rows: {len(res)}")
    if res: print(f"Sample: {res[0]}")

    db.close()

if __name__ == "__main__":
    asyncio.run(test_history())
