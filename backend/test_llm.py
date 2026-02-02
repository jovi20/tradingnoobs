import requests
from sqlalchemy.orm import Session
from database import SessionLocal
from models import SystemSetting

def test_llm_connection():
    db = SessionLocal()
    try:
        # 1. Fetch Settings
        url_setting = db.query(SystemSetting).filter(SystemSetting.key == 'llm_api_url').first()
        key_setting = db.query(SystemSetting).filter(SystemSetting.key == 'llm_api_key').first()
        model_setting = db.query(SystemSetting).filter(SystemSetting.key == 'llm_model').first()
        
        if not url_setting or not url_setting.value:
            print("❌ LLM API URL not configured.")
            return
        if not key_setting or not key_setting.value:
            print("❌ LLM API Key not configured.")
            return
            
        llm_api_url = url_setting.value
        llm_api_key = key_setting.value
        llm_model = model_setting.value if model_setting and model_setting.value else "gpt-4"

        # 2. Construct URL
        api_endpoint = llm_api_url.rstrip('/')
        if not api_endpoint.endswith('/chat/completions'):
            api_endpoint = f"{api_endpoint}/chat/completions"

        print(f"--- Configuration ---")
        print(f"Base URL: {llm_api_url}")
        print(f"Endpoint: {api_endpoint}")
        print(f"Model:    {llm_model}")
        print(f"Key:      {llm_api_key[:4]}...{llm_api_key[-4:] if len(llm_api_key) > 8 else '***'}")
        print("---------------------")

        # 3. Test Connection
        print("\nSending test request (requests)...")
        
        payload = {
            "model": llm_model,
            "messages": [
                {"role": "user", "content": "Hello"}
            ],
            "max_tokens": 10
        }

        try:
            response = requests.post(
                api_endpoint,
                headers={
                    "Authorization": f"Bearer {llm_api_key}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=30
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text[:500]}") # Print first 500 chars

            if response.status_code == 200:
                print("✅ Success!")
            else:
                print("❌ Failed.")
        except Exception as e:
             print(f"❌ Request Error: {e}")

    except Exception as e:
        print(f"❌ Script Error: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    test_llm_connection()
