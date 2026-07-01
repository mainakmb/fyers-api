import os
import time
from pathlib import Path

from fyers_apiv3 import fyersModel
from fyers_apiv3.FyersWebsocket import data_ws

# --- 1. CONFIGURATION ---
APP_ID = "P6WNRG76UH-100"          
AUTH_FILE = Path(__file__).with_name("auth")

if AUTH_FILE.exists():
    ACCESS_TOKEN = AUTH_FILE.read_text(encoding="utf-8").strip()
else:
    ACCESS_TOKEN = os.getenv("FYERS_ACCESS_TOKEN", "")

# COMBINED TOKEN FOR WEBSOCKET
WS_ACCESS_TOKEN = f"{APP_ID}:{ACCESS_TOKEN}"

# --- 2. DEFINE YOUR TRACKING TARGETS ---
INDEX_SYMBOL = os.getenv("INDEX_SYMBOL", "BSE:SENSEX-INDEX")
OPTIONS_SYMBOL = os.getenv("OPTIONS_SYMBOL", "BSE:SENSEX2670276900PE")

# Index Spot values for exit triggers
INDEX_STOP_LOSS = float(os.getenv("INDEX_STOP_LOSS", "77200.0"))
INDEX_TARGET = float(os.getenv("INDEX_TARGET", "76480.0"))

# Global tracking flags
is_exited = False
target_triggered_at = None  # ✅ FIXED: Initialized globally to prevent NameError
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


def market_exit_option():
    """Fires a market order to square off the options contract instantly."""
    global is_exited
    if is_exited:
        return

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
        "type": 2,                # 2 = Market Order
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
    global is_exited, target_triggered_at
    if is_exited:
        return

    if "ltp" in message:
        current_index_price = float(message["ltp"])
        print(f"Live Index Price ({INDEX_SYMBOL}): {current_index_price}")

        # --- DYNAMICALLY EXTRACT OPTION TYPE FROM SYMBOL ---
        option_type = OPTIONS_SYMBOL.upper()[-2:] 

        if option_type == "CE":
            sl_triggered = current_index_price <= INDEX_STOP_LOSS
            target_triggered = current_index_price >= INDEX_TARGET
        elif option_type == "PE":
            sl_triggered = current_index_price >= INDEX_STOP_LOSS
            target_triggered = current_index_price <= INDEX_TARGET
        else:
            print(f"⚠️ Unknown option type in symbol: {OPTIONS_SYMBOL}. Aborting evaluation.")
            return

        # 1. IMMEDIATE STOP-LOSS (No Delay)
        if sl_triggered:
            print(f"🛑 Stop-Loss triggered! Index at {current_index_price}")
            market_exit_option()
            return

        # 2. TARGET MECHANISM (With absolute 2-second premium float)
        if target_triggered or target_triggered_at is not None:
            
            # Step A: Lock in the initial trigger timestamp
            if target_triggered_at is None:
                target_triggered_at = time.time()
                print(f"🎯 Target initially breached at {current_index_price}. "
                      f"Premium float delay activated for {EXIT_DELAY_SECONDS} seconds...")
            
            # Step B: Check if the 2-second floating window has expired
            elif time.time() - target_triggered_at >= EXIT_DELAY_SECONDS:
                print(f"⏱️ {EXIT_DELAY_SECONDS}s float period over. Executing absolute market exit!")
                market_exit_option()

def on_error(message):
    print("WebSocket Error:", message)

def on_close(message):
    print("WebSocket Connection Closed.")

def on_open():
    """Subscribe to the index symbol once the socket opens."""
    data_type = "SymbolUpdate"
    fyers_ws.subscribe(symbols=[INDEX_SYMBOL], data_type=data_type)
    print(f"Subscribed to WebSocket stream for: {INDEX_SYMBOL}")

# --- 4. EXECUTION ---
if __name__ == "__main__":
    initial_qty = get_position_qty(OPTIONS_SYMBOL)
    if initial_qty == 0:
        print(f"Aborting: No open position found for {OPTIONS_SYMBOL}")
    else:
        print(f"Tracking open position of {initial_qty} Qty. Initiating WebSocket...")
        
        fyers_ws = data_ws.FyersDataSocket(
            access_token=WS_ACCESS_TOKEN,
            log_path="",
            litemode=True,  
            write_to_file=False,
            reconnect=True,
            on_connect=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        fyers_ws.connect()
        fyers_ws.keep_running()
        