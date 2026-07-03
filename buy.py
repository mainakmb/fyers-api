import os
import time
from pathlib import Path

from dotenv import load_dotenv
from fyers_apiv3 import fyersModel
from fyers_apiv3.FyersWebsocket import data_ws

# --- 1. CONFIGURATION ---
load_dotenv(Path(__file__).with_name(".env.buy"))

APP_ID = "E3J29EV658-200"
AUTH_FILE = Path(__file__).with_name("auth")

ACCESS_TOKEN = AUTH_FILE.read_text(encoding="utf-8").strip() if AUTH_FILE.exists() else os.getenv("FYERS_ACCESS_TOKEN", "")
WS_ACCESS_TOKEN = f"{APP_ID}:{ACCESS_TOKEN}"

INDEX_SYMBOL = os.getenv("INDEX_SYMBOL", "NSE:NIFTY50-INDEX")
OPTIONS_SYMBOL = os.getenv("OPTIONS_SYMBOL", "BSE:SENSEX2670277100PE").upper()
PRODUCT_TYPE = os.getenv("PRODUCT_TYPE", "INTRADAY").upper()
ORDER_QTY = int(os.getenv("ORDER_QTY", "1"))

# Index level that triggers a market buy on the option contract
INDEX_ENTRY = float(os.getenv("INDEX_ENTRY", "24100.0"))

is_entered = False
entry_triggered_at = None
ENTRY_DELAY_SECONDS = float(os.getenv("ENTRY_DELAY_SECONDS", "0"))

print(
    f"Using config -> index={INDEX_SYMBOL}, option={OPTIONS_SYMBOL}, "
    f"entry={INDEX_ENTRY}, qty={ORDER_QTY}, product={PRODUCT_TYPE}"
)

fyers_rest = fyersModel.FyersModel(client_id=APP_ID, token=ACCESS_TOKEN, is_async=False, log_path="")


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


def market_buy_option():
    """Place a market buy order for the configured option contract."""
    global is_entered
    if is_entered:
        return

    order_data = {
        "symbol": OPTIONS_SYMBOL,
        "qty": ORDER_QTY,
        "type": 2,  # Market order
        "side": 1,  # Buy
        "productType": PRODUCT_TYPE,
        "limitPrice": 0,
        "stopPrice": 0,
        "validity": "DAY",
        "disclosedQty": 0,
        "offlineOrder": False,
    }

    print(f"Placing market buy for {ORDER_QTY} x {OPTIONS_SYMBOL}...")
    response = fyers_rest.place_order(data=order_data)
    print("Execution Response:", response)

    if response and response.get("s") == "ok":
        is_entered = True
        print("Entry order placed successfully.")
    else:
        print("Entry order failed. Will keep monitoring index for retry.")


def entry_triggered(current_index_price):
    """Return True when index price crosses the configured entry level."""
    if "CE" in OPTIONS_SYMBOL:
        return current_index_price >= INDEX_ENTRY
    if "PE" in OPTIONS_SYMBOL:
        return current_index_price <= INDEX_ENTRY
    return False


def on_message(message):
    global is_entered, entry_triggered_at

    if is_entered:
        return

    if isinstance(message, list):
        if not message:
            return
        message = message[0]

    if "ltp" not in message:
        return

    current_index_price = float(message["ltp"])

    if "CE" not in OPTIONS_SYMBOL and "PE" not in OPTIONS_SYMBOL:
        print(f"Unable to parse CE/PE from {OPTIONS_SYMBOL}. Aborting.")
        return

    if not entry_triggered(current_index_price):
        if entry_triggered_at is not None:
            print(f"Price retraced to {current_index_price}. Resetting entry window.")
            entry_triggered_at = None
        return

    if ENTRY_DELAY_SECONDS <= 0:
        print(f"Entry level hit at index {current_index_price}. Buying at market.")
        market_buy_option()
        return

    if entry_triggered_at is None:
        entry_triggered_at = time.time()
        print(
            f"Entry level hit at {current_index_price}. "
            f"Waiting {ENTRY_DELAY_SECONDS}s before market buy..."
        )
    elif time.time() - entry_triggered_at >= ENTRY_DELAY_SECONDS:
        print(f"Entry delay complete at index {current_index_price}. Buying at market.")
        market_buy_option()


def on_error(message):
    print("WebSocket Error:", message)


def on_close(message):
    print("WebSocket Connection Closed.")


def on_open():
    data_type = "SymbolUpdate"
    fyers_ws.subscribe(symbols=[INDEX_SYMBOL], data_type=data_type)
    print(f"Subscribed to: {INDEX_SYMBOL}")


if __name__ == "__main__":
    if ORDER_QTY <= 0:
        raise SystemExit("Aborting: ORDER_QTY must be greater than 0.")

    existing_qty = get_position_qty(OPTIONS_SYMBOL)
    if existing_qty != 0:
        raise SystemExit(f"Aborting: Position already open for {OPTIONS_SYMBOL} ({existing_qty} qty).")

    print(f"Waiting for index entry at {INDEX_ENTRY}. Starting WebSocket...")

    fyers_ws = data_ws.FyersDataSocket(
        access_token=WS_ACCESS_TOKEN,
        log_path="",
        litemode=True,
        write_to_file=False,
        reconnect=True,
        on_connect=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )
    fyers_ws.connect()
    fyers_ws.keep_running()
