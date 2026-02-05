import requests
import sys

# Constants
API_URL = "http://localhost:8000"
EMAIL = "test@example.com" # Replace with valid user
PASSWORD = "password123"   # Replace with valid password

def login():
    try:
        response = requests.post(f"{API_URL}/api/auth/login", data={"username": EMAIL, "password": PASSWORD})
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        print(f"Login failed: {e}")
        return None

def check_positions(token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{API_URL}/api/positions", headers=headers)
        response.raise_for_status()
        positions = response.json()
        
        print(f"Found {len(positions)} positions.")
        
        for pos in positions:
            status = pos.get('status', 'UNKNOWN')
            batches = pos.get('batches')
            
            print(f"Position {pos['id']} ({pos.get('symbol')}) - Status: {status}")
            
            if batches is None:
                print("  ERROR: 'batches' field is MISSING entirely")
                print("  KEYS PRESENT:", list(pos.keys()))
                if 'debug_trace' in pos:
                    print("  DEBUG TRACE FOUND:", pos['debug_trace'])
                else:
                    print("  DEBUG TRACE MISSING - OLD CODE RUNNING")

            elif len(batches) == 0:
                print("  WARNING: 'batches' field is present but EMPTY")
            else:
                print(f"  SUCCESS: Batches found: {len(batches)}")
                # for b in batches:
                #    print(f"    Batch {b['id']} - Type: {b['type']}")
                    
            if status == 'CLOSED' and (batches is None or len(batches) == 0):
                print("  ALARM: Closed position with no batches!")
                
    except Exception as e:
        print(f"Failed to fetch positions: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print("Response Text:", e.response.text)

if __name__ == "__main__":
    token = login()
    if token:
        check_positions(token)
