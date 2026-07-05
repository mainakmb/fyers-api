import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fyers_apiv3 import fyersModel

from execution_log import FYERS_LOG_PATH

load_dotenv(Path(__file__).with_name(".env"))

APP_ID = os.getenv("FYERS_APP_ID", "E3J29EV658-200")
AUTH_FILE = Path(__file__).with_name("auth")

if AUTH_FILE.exists():
    ACCESS_TOKEN = AUTH_FILE.read_text(encoding="utf-8").strip()
else:
    ACCESS_TOKEN = os.getenv("FYERS_ACCESS_TOKEN", "")

fyers = fyersModel.FyersModel(
    client_id=APP_ID,
    token=ACCESS_TOKEN,
    is_async=False,
    log_path=FYERS_LOG_PATH,
)


def test_api_connection():
    if not ACCESS_TOKEN:
        print("❌ FYERS_ACCESS_TOKEN is missing. Run auth.py or set it in .env.")
        return False

    print("Connecting to FYERS API...")
    try:
        profile_response = fyers.get_profile()

        if not profile_response or profile_response.get("s") != "ok":
            print("❌ Authentication failed or token expired.")
            print("Response:", profile_response)
            return False

        print("\n✅ Connection Successful!")
        print(f"User Name : {profile_response['data'].get('name')}")
        print(f"Client ID : {profile_response['data'].get('fy_id')}")
        print(f"Email ID  : {profile_response['data'].get('email_id')}")

        funds_response = fyers.funds()
        if funds_response and funds_response.get("s") == "ok":
            balance = funds_response["fund_limit"][0].get("equityAmount", 0.0)
            print(f"Available Margin: ₹{balance}")

        return True
    except Exception as exc:
        print(f"❌ An error occurred during connection: {exc}")
        return False


if __name__ == "__main__":
    raise SystemExit(0 if test_api_connection() else 1)
