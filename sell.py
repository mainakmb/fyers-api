import os
import time
from pathlib import Path
from dotenv import load_dotenv
from fyers_apiv3 import fyersModel
from fyers_apiv3.FyersWebsocket import data_ws

from execution_log import FYERS_LOG_PATH, log_execution

# --- 1. CONFIGURATION ---
load_dotenv(Path(__file__).with_name(".env"))
load_dotenv(Path(__file__).with_name(".env.sell"))

APP_ID = os.getenv("FYERS_APP_ID", "E3J29EV658-200")
AUTH_FILE = Path(__file__).with_name("auth")

ACCESS_TOKEN = AUTH_FILE.read_text(encoding="utf-8").strip() if AUTH_FILE.exists() else os.getenv("FYERS_ACCESS_TOKEN", "")
WS_ACCESS_TOKEN = f"{APP_ID}:{ACCESS_TOKEN}"

# --- 2. DEFINE YOUR TRACKING TARGETS ---
INDEX_SYMBOL = os.getenv("INDEX_SYMBOL", "NSE:NIFTY50-INDEX")
OPTIONS_SYMBOL = os.getenv("OPTIONS_SYMBOL", "BSE:SENSEX2670277100PE").upper()
PRODUCT_TYPE = os.getenv("PRODUCT_TYPE", "INTRADAY").upper()

INDEX_STOP_LOSS = float(os.getenv("INDEX_STOP_LOSS", "24150.0"))
INDEX_TARGET = float(os.getenv("INDEX_TARGET", "24036.0"))

# Global tracking flags
is_exited = False
target_triggered_at = None  
EXIT_DELAY_SECONDS = float(os.getenv("EXIT_DELAY_SECONDS", "1"))
current_position_qty = 0  # ✅ Local tracking to eliminate REST API latency on exit

print(f"Using config -> symbol={INDEX_SYMBOL}, SL={INDEX_STOP_LOSS}, Target={INDEX_TARGET}, Product={PRODUCT_TYPE}")

fyers_rest = fyersModel.FyersModel(client_id=APP_ID, token=ACCESS_TOKEN, is_async=False, log_path=FYERS_LOG_PATH)

def get_position_qty(symbol):
    """Fetch current open quantity for the option contract at startup."""
    try:
        response = fyers_rest.positions()
        if response and response.get("s") == "ok":
            for pos in response.get("netPositions", []):
                if pos.get("symbol") == symbol:
                    return int(pos.get("netQty", 0))
    except Exception as e:
        print(f"Error fetching position size: {e}")
    return 0

def market_exit_option(trigger_context=None):
    """Fires a market order instantly using locally cached position size."""
    global is_exited, current_position_qty
    if is_exited or current_position_qty == 0:
        return

    trigger_context = trigger_context or {}
    # Determine exit side locally
    exit_side = -1 if current_position_qty > 0 else 1
    abs_qty = abs(current_position_qty)
    action = "SELL" if exit_side == -1 else "BUY"

    order_data = {
        "symbol": OPTIONS_SYMBOL,
        "qty": abs_qty,
        "type": 2,                # 2 = Market Order
        "side": exit_side,
        "productType": PRODUCT_TYPE,
        "limitPrice": 0,
        "stopPrice": 0,
        "validity": "DAY",
        "disclosedQty": 0,
        "offlineOrder": False
    }

    print(f"⚡ CRITICAL: Firing Market Order to close option position: {abs_qty} Qty...")
    response = fyers_rest.place_order(data=order_data)

    log_execution(
        fyers_rest,
        script="sell",
        action=action,
        order_request=order_data,
        place_response=response,
        context={
            "index_symbol": INDEX_SYMBOL,
            "index_stop_loss": INDEX_STOP_LOSS,
            "index_target": INDEX_TARGET,
            "index_price": trigger_context.get("index_price"),
            "trigger_reason": trigger_context.get("trigger_reason"),
            "position_qty_before_exit": current_position_qty,
        },
    )

    is_exited = True

# --- 3. WEBSOCKET CALLBACKS ---
def on_message(message):
    global is_exited, target_triggered_at

    if is_exited:
        return

    # Handle Fyers packing ticks into lists
    if isinstance(message, list):
        if len(message) > 0:
            message = message[0]
        else:
            return

    if "ltp" in message:
        current_index_price = float(message["ltp"])
        
        # Safer string matching for contract type
        if "CE" in OPTIONS_SYMBOL:
            sl_triggered = current_index_price <= INDEX_STOP_LOSS
            target_triggered = current_index_price >= INDEX_TARGET
        elif "PE" in OPTIONS_SYMBOL:
            sl_triggered = current_index_price >= INDEX_STOP_LOSS
            target_triggered = current_index_price <= INDEX_TARGET
        else:
            print(f"⚠️ Unable to parse CE/PE from {OPTIONS_SYMBOL}. Aborting.")
            return

        # 1. IMMEDIATE STOP-LOSS (Zero Latency Execution)
        if sl_triggered:
            print(f"🛑 STOP LOSS HIT! Index: {current_index_price}. Exiting instantly.")
            market_exit_option(
                {
                    "index_price": current_index_price,
                    "trigger_reason": "stop_loss",
                }
            )
            return

        # 2. ROBUST TARGET MECHANISM
        if target_triggered:
            if target_triggered_at is None:
                target_triggered_at = time.time()
                print(f"🎯 Target hit at {current_index_price}. Holding premium float for {EXIT_DELAY_SECONDS}s...")
            elif time.time() - target_triggered_at >= EXIT_DELAY_SECONDS:
                print(f"⏱️ Float time complete. Executing Target Exit at {current_index_price}!")
                market_exit_option(
                    {
                        "index_price": current_index_price,
                        "trigger_reason": "target",
                    }
                )
        else:
            # ✅ RECOVERY: If price falls back out of target zone before the 2 seconds expire, reset!
            if target_triggered_at is not None:
                print(f"🔄 Price retraced to {current_index_price}. Resetting target window.")
                target_triggered_at = None

def on_error(message):
    print("WebSocket Error:", message)

def on_close(message):
    print("WebSocket Connection Closed.")

def on_open():
    data_type = "SymbolUpdate"
    fyers_ws.subscribe(symbols=[INDEX_SYMBOL], data_type=data_type)
    print(f"Subscribed to: {INDEX_SYMBOL}")

# --- 4. EXECUTION ---
if __name__ == "__main__":
    current_position_qty = get_position_qty(OPTIONS_SYMBOL)
    
    if current_position_qty == 0:
        print(f"Aborting: No open position found for {OPTIONS_SYMBOL}")
    else:
        print(f"Tracking open position of {current_position_qty} Qty. Initiating Engine...")
        
        fyers_ws = data_ws.FyersDataSocket(
            access_token=WS_ACCESS_TOKEN,
            log_path=FYERS_LOG_PATH,
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
