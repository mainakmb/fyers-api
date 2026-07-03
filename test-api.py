import os

from pathlib import Path
from fyers_apiv3 import fyersModel

# --- 1. CONFIGURATION ---
APP_ID = "E3J29EV658-200"          # e.g., "XCXXXXXXxx-100"
AUTH_FILE = Path(__file__).with_name("auth")

if AUTH_FILE.exists():
    ACCESS_TOKEN = AUTH_FILE.read_text(encoding="utf-8").strip()
else:
    ACCESS_TOKEN = os.getenv("FYERS_ACCESS_TOKEN", "")

# --- 2. INITIALIZE CLIENT ---
fyers = fyersModel.FyersModel(
    client_id=APP_ID, 
    token=ACCESS_TOKEN, 
    is_async=False, 
    log_path=""
)

# --- 3. TEST CONNECTIVITY ---
def test_api_connection():
    print("Connecting to FYERS API...")
    try:
        # Fetching profile details works even when the market is closed
        profile_response = fyers.get_profile()
        
        if profile_response and profile_response.get("s") == "ok":
            print("\n✅ Connection Successful!")
            print(f"User Name : {profile_response['data'].get('name')}")
            print(f"Client ID : {profile_response['data'].get('fy_id')}")
            print(f"Email ID  : {profile_response['data'].get('email_id')}")
            
            # Fetch funds as an extra validation check
            funds_response = fyers.funds()
            if funds_response and funds_response.get("s") == "ok":
                # Extract available balance safely
                balance = funds_response['fund_limit'][0].get('equityAmount', 0.0)
                print(f"Available Margin: ₹{balance}")
                
        else:
            print("\n❌ Authentication Failed or Token Expired!")
            print("Response Received:", profile_response)
            
    except Exception as e:
        print(f"\n❌ An error occurred during connection: {e}")

if __name__ == "__main__":
    test_api_connection()
    