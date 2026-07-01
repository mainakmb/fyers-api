import webbrowser
from pathlib import Path

from fyers_apiv3 import fyersModel

AUTH_FILE = Path(__file__).with_name("auth")

# --- 1. ENTER YOUR DETAILS ---
CLIENT_ID = "P6WNRG76UH-100"       # e.g., "ABCD1234-100" (Must end in -100)
SECRET_KEY = "ZMLW2C50NV"
REDIRECT_URI = "https://trade.fyers.in/api-login/redirect-uri/index.html"

# --- 2. INITIALIZE SESSION MODEL ---
session = fyersModel.SessionModel(
    client_id=CLIENT_ID,
    secret_key=SECRET_KEY,
    redirect_uri=REDIRECT_URI,
    response_type="code",
    grant_type="authorization_code"
)

# =====================================================================
# STAGE 1: Generate Login URL
# =====================================================================
# Run this segment first. It will open your web browser.
login_url = session.generate_authcode()
print(f"Opening browser. If it doesn't open automatically, visit this URL:\n{login_url}\n")
webbrowser.open(login_url)

# =====================================================================
# STAGE 2: Extract Auth Code & Generate Access Token
# =====================================================================
"""
👉 WHAT TO DO NOW:
1. Complete the login, OTP, and 2FA PIN in the opened browser window.
2. Once logged in, the page will redirect to your REDIRECT_URI.
3. Look at the browser's address bar. It will have a parameter like: 
   '...&auth_code=eyJ0eX...'
4. Copy that long string completely (stop before '&state=' if present).
5. Paste it into the 'auth_code' input prompt in your terminal below.
"""

auth_code = input("Enter the 'auth_code' captured from the browser URL: ").strip()

if auth_code:
    # Set the received auth code into the session object
    session.set_token(auth_code)
    
    # Generate the daily access token
    response = session.generate_token()
    
    if "access_token" in response:
        access_token = response["access_token"]
        AUTH_FILE.write_text(access_token, encoding="utf-8")
        print("\n✅ Access Token Generated Successfully!")
        print(f"Saved to {AUTH_FILE}")
        print(f"YOUR ACCESS_TOKEN:\n{access_token}")
    else:
        print("\n❌ Failed to generate token. Error details:", response)
