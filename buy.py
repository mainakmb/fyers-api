import json
import os
import time
from pathlib import Path
from urllib.request import urlopen

from dotenv import load_dotenv
from fyers_apiv3 import fyersModel
from fyers_apiv3.FyersWebsocket import data_ws

SYMBOL_MASTER_BASE_URL = "https://public.fyers.in/sym_details"
SYMBOL_MASTER_FILES = {
    ("NSE", "FO"): "NSE_FO",
    ("NSE", "CM"): "NSE_CM",
    ("NSE", "CD"): "NSE_CD",
    ("NSE", "COM"): "NSE_COM",
    ("BSE", "FO"): "BSE_FO",
    ("BSE", "CM"): "BSE_CM",
    ("MCX", "COM"): "MCX_COM",
}

# --- 1. CONFIGURATION ---
load_dotenv(Path(__file__).with_name(".env.buy"))

APP_ID = "E3J29EV658-200"
AUTH_FILE = Path(__file__).with_name("auth")

ACCESS_TOKEN = AUTH_FILE.read_text(encoding="utf-8").strip() if AUTH_FILE.exists() else os.getenv("FYERS_ACCESS_TOKEN", "")
WS_ACCESS_TOKEN = f"{APP_ID}:{ACCESS_TOKEN}"

INDEX_SYMBOL = os.getenv("INDEX_SYMBOL", "NSE:NIFTY50-INDEX")
OPTIONS_SYMBOL = os.getenv("OPTIONS_SYMBOL", "BSE:SENSEX2670277100PE").upper()
PRODUCT_TYPE = os.getenv("PRODUCT_TYPE", "INTRADAY").upper()
ORDER_LOTS = int(os.getenv("ORDER_LOTS", "1"))

# Index level that triggers a market buy on the option contract
INDEX_ENTRY = float(os.getenv("INDEX_ENTRY", "24100.0"))

is_entered = False
entry_triggered_at = None
ENTRY_DELAY_SECONDS = float(os.getenv("ENTRY_DELAY_SECONDS", "0"))
order_qty = 0
lot_size = 0

print(
    f"Using config -> index={INDEX_SYMBOL}, option={OPTIONS_SYMBOL}, "
    f"entry={INDEX_ENTRY}, lots={ORDER_LOTS}, product={PRODUCT_TYPE}"
)

fyers_rest = fyersModel.FyersModel(client_id=APP_ID, token=ACCESS_TOKEN, is_async=False, log_path="")


def _symbol_master_key(symbol):
    """Map a FYERS symbol to the public symbol master file name."""
    exchange = symbol.split(":", 1)[0]
    if exchange == "MCX":
        return "MCX_COM"
    if "CE" in symbol or "PE" in symbol or "FUT" in symbol:
        return SYMBOL_MASTER_FILES[(exchange, "FO")]
    return SYMBOL_MASTER_FILES[(exchange, "CM")]


def get_lot_size(symbol):
    """Fetch the exchange lot size for a symbol from FYERS symbol master."""
    master_key = _symbol_master_key(symbol)
    url = f"{SYMBOL_MASTER_BASE_URL}/{master_key}_sym_master.json"
    with urlopen(url, timeout=30) as response:
        master_data = json.loads(response.read().decode("utf-8"))

    symbol_data = master_data.get(symbol)
    if not symbol_data:
        raise ValueError(f"Symbol {symbol} not found in {master_key} symbol master")

    lot_size = int(symbol_data.get("minLotSize", 0))
    if lot_size <= 0:
        raise ValueError(f"Invalid lot size returned for {symbol}")

    return lot_size


def resolve_order_qty(symbol, lots):
    """Return order quantity for the requested number of lots."""
    if lots <= 0:
        raise ValueError("ORDER_LOTS must be greater than 0")

    per_lot_qty = get_lot_size(symbol)
    return per_lot_qty, per_lot_qty * lots


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
        "qty": order_qty,
        "type": 2,  # Market order
        "side": 1,  # Buy
        "productType": PRODUCT_TYPE,
        "limitPrice": 0,
        "stopPrice": 0,
        "validity": "DAY",
        "disclosedQty": 0,
        "offlineOrder": False,
    }

    print(f"Placing market buy for {order_qty} x {OPTIONS_SYMBOL} ({ORDER_LOTS} lot(s))...")
    response = fyers_rest.place_order(data=order_data)
    print("Execution Response:", response)

    if response and response.get("s") == "ok":
        is_entered = True
        print("Entry order placed successfully.")
    else:
        print("Entry order failed. Will keep monitoring index for retry.")


def parse_option_type(symbol):
    """Return CE or PE based on the option contract suffix."""
    symbol = symbol.upper()
    if symbol.endswith("PE"):
        return "PE"
    if symbol.endswith("CE"):
        return "CE"
    raise ValueError(f"Unable to parse CE/PE from {symbol}")


def entry_triggered(current_index_price, option_type):
    """Return True when index price crosses the configured entry level.

    Uses the same index direction as sell.py stop-loss logic:
    - Call (CE): buy on dip when index <= INDEX_ENTRY
    - Put (PE): buy on rally when index >= INDEX_ENTRY
    """
    if option_type == "CE":
        return current_index_price <= INDEX_ENTRY
    if option_type == "PE":
        return current_index_price >= INDEX_ENTRY
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

    try:
        option_type = parse_option_type(OPTIONS_SYMBOL)
    except ValueError as exc:
        print(f"{exc}. Aborting.")
        return

    if not entry_triggered(current_index_price, option_type):
        if entry_triggered_at is not None:
            print(f"Price retraced to {current_index_price}. Resetting entry window.")
            entry_triggered_at = None
        return

    if ENTRY_DELAY_SECONDS <= 0:
        print(
            f"{option_type} entry hit at index {current_index_price} "
            f"(rule: {'<=' if option_type == 'CE' else '>='} {INDEX_ENTRY}). Buying at market."
        )
        market_buy_option()
        return

    if entry_triggered_at is None:
        entry_triggered_at = time.time()
        print(
            f"{option_type} entry hit at {current_index_price} "
            f"(rule: {'<=' if option_type == 'CE' else '>='} {INDEX_ENTRY}). "
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
    try:
        lot_size, order_qty = resolve_order_qty(OPTIONS_SYMBOL, ORDER_LOTS)
    except (OSError, ValueError, KeyError) as exc:
        raise SystemExit(f"Aborting: unable to resolve lot size for {OPTIONS_SYMBOL}: {exc}") from exc

    print(f"Resolved lot size={lot_size}, order_qty={order_qty}")

    try:
        option_type = parse_option_type(OPTIONS_SYMBOL)
    except ValueError as exc:
        raise SystemExit(f"Aborting: {exc}") from exc

    entry_rule = "<=" if option_type == "CE" else ">="
    print(
        f"Waiting for {option_type} entry: index {entry_rule} {INDEX_ENTRY}. "
        f"Starting WebSocket..."
    )

    existing_qty = get_position_qty(OPTIONS_SYMBOL)
    if existing_qty != 0:
        raise SystemExit(f"Aborting: Position already open for {OPTIONS_SYMBOL} ({existing_qty} qty).")

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
