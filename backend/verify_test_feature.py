import requests
from database import SessionLocal
from database import SessionLocal
from models import SystemSetting

BASE_URL = "http://localhost:8000/api"
EMAIL = "admin@tradingnoobs.com"
PASSWORD = "admin123456"

def get_token():
    response = requests.post(f"{BASE_URL}/auth/login", data={"username": EMAIL, "password": PASSWORD})
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
        return None
    return response.json()["access_token"]

def verify_test_endpoint():
    print("Verifying Test Endpoint...")
    token = get_token()
    if not token:
        return

    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.post(f"{BASE_URL}/admin/test-llm", headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Endpoint verified successfully.")
        elif response.status_code == 400:
            print("⚠️ Endpoint reachable but external API failed (Expected if config is invalid).")
        else:
            print("❌ Endpoint failed unexpectedly.")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    verify_test_endpoint()
