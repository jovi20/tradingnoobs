import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000/api"
EMAIL = "admin@tradingnoobs.com"
PASSWORD = "admin123456"

def get_token():
    response = requests.post(f"{BASE_URL}/auth/login", data={"username": EMAIL, "password": PASSWORD})
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
        return None
    return response.json()["access_token"]

def verify_price_and_sorting():
    token = get_token()
    if not token:
        return

    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Test Trades
    print("Creating test trades...")
    trade1_data = {
        "symbol": "AAPL",
        "exchange": "NASDAQ",
        "entry_price": 150.0,
        "quantity": 10,
        "entry_time": datetime.now().isoformat(),
        "status": "OPEN",
        "entry_reason": "Test Trade 1"
    }
    trade2_data = {
        "symbol": "TSLA",
        "exchange": "NASDAQ",
        "entry_price": 200.0,
        "quantity": 5,
        "entry_time": (datetime.now() - timedelta(days=1)).isoformat(),
        "status": "OPEN",
        "entry_reason": "Test Trade 2"
    }
    
    requests.post(f"{BASE_URL}/trades", json=trade1_data, headers=headers)
    requests.post(f"{BASE_URL}/trades", json=trade2_data, headers=headers)

    # 2. Verify Price Fetching (Default Sort: Entry Time Desc -> AAPL should be first)
    print("\nVerifying Price Fetching...")
    response = requests.get(f"{BASE_URL}/trades", headers=headers)
    trades = response.json()
    
    found_price = False
    for trade in trades:
        if trade['symbol'] == 'AAPL' and trade['status'] == 'OPEN':
            try:
                price = float(trade.get('current_price'))
                print(f"AAPL Trade Found. Current Price: {price}")
                if price > 0:
                    found_price = True
            except (ValueError, TypeError):
                print(f"Invalid price format: {trade.get('current_price')}")
    
    if found_price:
        print("✅ Real-time price fetching successful.")
    else:
        print("❌ Real-time price fetching failed or AAPL trade not found.")

    # 3. Verify Sorting (Symbol ASC -> AAPL, TSLA)
    print("\nVerifying Sorting (Symbol ASC)...")
    response = requests.get(f"{BASE_URL}/trades?sort_by=symbol&order=asc", headers=headers)
    trades_asc = response.json()
    symbols_asc = [t['symbol'] for t in trades_asc if t['symbol'] in ['AAPL', 'TSLA']]
    print(f"Symbols Order: {symbols_asc}")
    
    # 4. Verify Sorting (Symbol DESC -> TSLA, AAPL)
    print("\nVerifying Sorting (Symbol DESC)...")
    response = requests.get(f"{BASE_URL}/trades?sort_by=symbol&order=desc", headers=headers)
    trades_desc = response.json()
    symbols_desc = [t['symbol'] for t in trades_desc if t['symbol'] in ['AAPL', 'TSLA']]
    print(f"Symbols Order: {symbols_desc}")

    if symbols_asc == sorted(symbols_asc) and symbols_desc == sorted(symbols_desc, reverse=True):
        print("✅ Sorting verified successfully.")
    else:
        print("❌ Sorting verification failed.")

if __name__ == "__main__":
    verify_price_and_sorting()
