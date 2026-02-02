from database import SessionLocal
from services.market_data_service import MarketDataService

def test():
    db = SessionLocal()
    try:
        service = MarketDataService(db)
        print("Validating Finnhub API Key...")
        quote = service.validate_api_key()
        print(f"Success! AAPL Quote: {quote}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test()
