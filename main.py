import os
import time

from pathlib import Path

from fyers_apiv3 import fyersModel
from fyers_apiv3.FyersWebsocket import data_ws

# --- 1. CONFIGURATION ---
APP_ID = "P6WNRG76UH-100"          # e.g., "XCXXXXXXxx-100"
AUTH_FILE = Path(__file__).with_name("auth")

if AUTH_FILE.exists():
    ACCESS_TOKEN = AUTH_FILE.read_text(encoding="utf-8").strip()
else:
    ACCESS_TOKEN = os.getenv("FYERS_ACCESS_TOKEN", "")

# COMBINED TOKEN FOR WEBSOCKET: Fyers requires "APP_ID:ACCESS_TOKEN" format
WS_ACCESS_TOKEN = f"{APP_ID}:{ACCESS_TOKEN}"

# --- 2. DEFINE YOUR TRACKING TARGETS ---
INDEX_SYMBOL = os.getenv("INDEX_SYMBOL", "BSE:SENSEX-INDEX")
OPTIONS_SYMBOL = os.getenv("OPTIONS_SYMBOL", "BSE:SENSEX2670276900PE")

# Index Spot values for exit triggers
INDEX_STOP_LOSS = float(os.getenv("INDEX_STOP_LOSS", "77200.0"))
INDEX_TARGET = float(os.getenv("INDEX_TARGET", "76480.0"))

# Global flag to prevent multiple orders triggering simultaneously 
is_exited = False
EXIT_DELAY_SECONDS = 2

# Initialize the REST API client for execution
fyers_rest = fyersModel.FyersModel(
    client_id=APP_ID, 
    token=ACCESS_TOKEN, 
    is_async=False, 
    log_path=""
)

def get_position_qty(symbol):
    """Fetch current open quantity for the option contract."""
    try:
        response = fyers_rest.positions()
        if response and response.get("s") == "ok":
            for pos in response.get("netPositions", []):
                if pos.get("symbol") == symbol:
                    return int(pos.get("netQty", 0))
    except Exception as e:
        print(f"Error fetching position size: {e}")
    return 0

def delay_before_exit():
    """Pause briefly before sending the exit order after a trigger."""
    time.sleep(EXIT_DELAY_SECONDS)


def market_exit_option():
    """Fires a market order to instantly square off the options contract."""
    global is_exited
    if is_exited:
        return

    delay_before_exit()

    net_qty = get_position_qty(OPTIONS_SYMBOL)
    if net_qty == 0:
        print(f"No active position found for {OPTIONS_SYMBOL}. Marking as exited.")
        is_exited = True
        return

    # Determine exit side: Sell to exit Long (+), Buy to exit Short (-)
    exit_side = -1 if net_qty > 0 else 1
    abs_qty = abs(net_qty)

    order_data = {
        "symbol": OPTIONS_SYMBOL,
        "qty": abs_qty,
        "type": 2,                # 2 = Market Order (Ensures instant execution)
        "side": exit_side,
        "productType": "MARGIN",  # Change to "INTRADAY" if your position is intraday
        "limitPrice": 0,
        "stopPrice": 0,
        "validity": "DAY",
        "disclosedQty": 0,
        "offlineOrder": False
    }

    print(f"Sending Market Order to close option position: {abs_qty} Qty...")
    response = fyers_rest.place_order(data=order_data)
    print("Execution Response:", response)
    
    is_exited = True

# --- 3. WEBSOCKET CALLBACKS ---
def on_message(message):
    """Callback triggered whenever a new tick arrives from the index chart."""
    global is_exited
    if is_exited:
        return

    # Extract the Last Traded Price (ltp) from the tick payload
    if "ltp" in message:
        current_index_price = float(message["ltp"])
        print(f"Live Index Price ({INDEX_SYMBOL}): {current_index_price}")

        # Check your conditional chart strategies
        # Assuming you are LONG on the option (Exiting if index drops below SL or breaks Target)
        if current_index_price <= INDEX_STOP_LOSS:
            print(f"Stop-Loss triggered! Index {current_index_price} <= {INDEX_STOP_LOSS}")
            market_exit_option()

        elif current_index_price >= INDEX_TARGET:
            print(f"Target profit hit! Index {current_index_price} >= {INDEX_TARGET}")
            market_exit_option()

def on_error(message):
    print("WebSocket Error:", message)

def on_close(message):
    print("WebSocket Connection Closed.")

def on_open():
    """Subscribe to the index symbol once the socket opens."""
    # Using 'lite' mode (litemode=True below) grants optimized bandwidth for raw LTP ticks
    data_type = "SymbolUpdate"
    fyers_ws.subscribe(symbols=[INDEX_SYMBOL], data_type=data_type)
    print(f"Subscribed to WebSocket stream for: {INDEX_SYMBOL}")

# --- 4. EXECUTION ---
if __name__ == "__main__":
    # Validate there's an actual option position before spinning up the socket loop
    initial_qty = get_position_qty(OPTIONS_SYMBOL)
    if initial_qty == 0:
        print(f"Aborting: No open position found for {OPTIONS_SYMBOL}")
    else:
        print(f"Tracking open position of {initial_qty} Qty. Initiating WebSocket...")
        
        # Initialize Fyers Data Socket
        fyers_ws = data_ws.FyersDataSocket(
            access_token=WS_ACCESS_TOKEN,
            log_path="",
            litemode=True,  # Set to True if you only need the 'ltp' payload (highly efficient)
            write_to_file=False,
            reconnect=True,
            on_connect=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        fyers_ws.connect()
        fyers_ws.keep_running()
        