import finnhub
from sqlalchemy.orm import Session
from models import SystemSetting

class MarketDataService:
    def __init__(self, db: Session):
        self.db = db
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        setting = self.db.query(SystemSetting).filter(SystemSetting.key == 'finnhub_api_key').first()
        if setting and setting.value:
            self.client = finnhub.Client(api_key=setting.value)

    def get_quote(self, symbol: str):
        if not self.client:
             self._initialize_client() # Retry init
             if not self.client:
                raise Exception("Finnhub API key not configured")
        
        try:
            return self.client.quote(symbol)
        except Exception as e:
            raise Exception(f"Finnhub API error: {str(e)}")

    def validate_api_key(self):
        """Test if the API key works by fetching a simple quote"""
        try:
            return self.get_quote('AAPL')
        except Exception as e:
            raise Exception(f"Validation failed: {str(e)}")
