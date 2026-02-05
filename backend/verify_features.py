
import requests
import sys

BASE_URL = "http://localhost:8000/api"

def register(email, password):
    print("Registering new user...")
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "email": email, 
        "password": password,
        "invite_code": "bigme"
    })
    if resp.status_code == 201:
        print("Registration successful.")
        return True
    elif resp.status_code == 400 and "already registered" in resp.text:
        print("User already exists.")
        return True
    else:
        print(f"Registration failed: {resp.text}")
        return False

def login(email, password):
    # Try login first
    resp = requests.post(f"{BASE_URL}/auth/login", data={"username": email, "password": password})
    
    if resp.status_code == 401:
        # Register if unauthorized (maybe user doesn't exist)
        if register(email, password):
             resp = requests.post(f"{BASE_URL}/auth/login", data={"username": email, "password": password})
    
    if resp.status_code != 200:
        print(f"Login failed: {resp.text}")
        sys.exit(1)
    return resp.json()["access_token"]

def ensure_account(token):
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{BASE_URL}/accounts", headers=headers)
    accounts = resp.json()
    if accounts:
        return accounts[0]['id']
    
    print("Creating test account...")
    resp = requests.post(f"{BASE_URL}/accounts", json={
        "name": "Test Account",
        "broker": "IBKR",
        "initial_balance": 100000
    }, headers=headers)
    return resp.json()['id']

def ensure_position(token, account_id):
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{BASE_URL}/positions", headers=headers)
    positions = resp.json()
    if positions:
        return positions[0]
    
    print("Creating test position...")
    resp = requests.post(f"{BASE_URL}/positions", json={
        "account_id": account_id,
        "symbol": "TEST",
        "direction": "LONG",
        "entry_price": 100,
        "quantity": 10,
        "entry_time": "2023-01-01T10:00:00",
        "asset_type": "STOCK"
    }, headers=headers)
    return resp.json()

def verify_metadata_update(token):
    print("\n--- Verifying Metadata Update ---")
    headers = {"Authorization": f"Bearer {token}"}
    
    account_id = ensure_account(token)
    pos = ensure_position(token, account_id)
    
    pos_id = pos['id']
    symbol = pos['symbol']
    print(f"Testing on Position ID: {pos_id}, Symbol: {symbol}")
    
    # 2. Update Metadata
    new_sector = "Test Sector Updated"
    update_payload = {
        "asset_metadata": {
            "sector": new_sector,
            "risk_level": "AGGRESSIVE" 
        }
    }
    
    resp = requests.patch(f"{BASE_URL}/positions/{pos_id}", json=update_payload, headers=headers)
    if resp.status_code != 200:
        print(f"Update failed: {resp.text}")
        return
        
    updated_pos = resp.json()
    meta = updated_pos.get('asset_metadata', {})
    print(f"Updated Sector: {meta.get('sector')}")
    print(f"Updated Risk: {meta.get('risk_level')}")
    
    if meta.get('sector') == new_sector and meta.get('risk_level') == "AGGRESSIVE":
        print("SUCCESS: Metadata updated.")
    else:
        print("FAILURE: Metadata mismatch.")

def verify_pnl_history(token):
    print("\n--- Verifying PnL History ---")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Trigger Snapshot via Dashboard
    print("Triggering Dashboard Stats (Snapshot Record)...")
    requests.get(f"{BASE_URL}/dashboard", headers=headers)
    
    # 2. Get History
    resp = requests.get(f"{BASE_URL}/dashboard/pnl-history?days=30", headers=headers)
    if resp.status_code != 200:
        print(f"PnL History failed: {resp.text}")
        return
        
    history = resp.json()
    print(f"History Points: {len(history)}")
    if history:
        print(f"Latest Point: {history[-1]}")
        print("SUCCESS: PnL History returned data.")
    else:
        print("WARNING: PnL History empty (might need more data/time).")

if __name__ == "__main__":
    # Ensure server is running separately
    try:
        token = login("test@example.com", "password123") # Adjust credentials if needed
        verify_metadata_update(token)
        verify_pnl_history(token)
    except Exception as e:
        print(f"Error: {e}")
