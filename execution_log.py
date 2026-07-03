import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30))
PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
FYERS_LOG_PATH = str(LOG_DIR)

ORDER_STATUS_LABELS = {
    1: "cancelled",
    2: "filled",
    3: "rejected",
    4: "transit",
    5: "open",
    6: "pending",
}


def now_ist():
    return datetime.now(IST)


def now_ist_iso():
    return now_ist().isoformat()


def _status_label(status):
    if status is None:
        return None
    try:
        return ORDER_STATUS_LABELS.get(int(status), str(status))
    except (TypeError, ValueError):
        return str(status)


def _first_present(mapping, *keys):
    for key in keys:
        value = mapping.get(key)
        if value is not None and value != "":
            return value
    return None


def fetch_order_fill(fyers_client, order_id, symbol, attempts=5, delay_seconds=0.5):
    """Look up fill details from orderbook, then tradebook."""
    order_id = str(order_id)
    last_order = None

    for _ in range(attempts):
        try:
            response = fyers_client.orderbook()
            if response and response.get("s") == "ok":
                for order in response.get("orderBook", []):
                    if str(order.get("id")) != order_id:
                        continue
                    last_order = order
                    traded_price = _first_present(order, "tradedPrice", "traded_price")
                    filled_qty = _first_present(order, "filledQty", "qty_filled")
                    status = order.get("status")
                    if traded_price not in (None, 0, 0.0) or int(filled_qty or 0) > 0:
                        return {
                            "source": "orderbook",
                            "traded_price": traded_price,
                            "filled_qty": filled_qty,
                            "status": status,
                            "status_label": _status_label(status),
                            "order_datetime": _first_present(order, "orderDateTime", "order_date_time"),
                            "message": order.get("message"),
                        }
        except Exception:
            pass
        time.sleep(delay_seconds)

    try:
        response = fyers_client.tradebook()
        if response and response.get("s") == "ok":
            trades = [
                trade
                for trade in response.get("tradeBook", [])
                if str(trade.get("orderNumber")) == order_id
                or trade.get("symbol") == symbol
            ]
            if trades:
                total_qty = sum(int(_first_present(t, "tradedQty", "qty_traded") or 0) for t in trades)
                total_value = sum(
                    float(_first_present(t, "tradePrice", "price_traded") or 0)
                    * int(_first_present(t, "tradedQty", "qty_traded") or 0)
                    for t in trades
                )
                avg_price = round(total_value / total_qty, 4) if total_qty else None
                latest_trade = trades[-1]
                return {
                    "source": "tradebook",
                    "traded_price": avg_price,
                    "filled_qty": total_qty,
                    "status": last_order.get("status") if last_order else None,
                    "status_label": _status_label(last_order.get("status")) if last_order else None,
                    "order_datetime": _first_present(latest_trade, "orderDateTime", "tradeDateTime"),
                    "message": last_order.get("message") if last_order else None,
                }
    except Exception:
        pass

    if last_order:
        return {
            "source": "orderbook",
            "traded_price": _first_present(last_order, "tradedPrice", "traded_price"),
            "filled_qty": _first_present(last_order, "filledQty", "qty_filled"),
            "status": last_order.get("status"),
            "status_label": _status_label(last_order.get("status")),
            "order_datetime": _first_present(last_order, "orderDateTime", "order_date_time"),
            "message": last_order.get("message"),
        }

    return {
        "source": None,
        "traded_price": None,
        "filled_qty": None,
        "status": None,
        "status_label": None,
        "order_datetime": None,
        "message": None,
    }


def build_execution_record(script, action, order_request, place_response, context=None, fill_details=None):
    context = context or {}
    fill_details = fill_details or {}
    success = bool(place_response and place_response.get("s") == "ok")

    return {
        "timestamp_ist": now_ist_iso(),
        "script": script,
        "action": action,
        "success": success,
        "order_id": place_response.get("id") if place_response else None,
        "api_code": place_response.get("code") if place_response else None,
        "api_message": place_response.get("message") if place_response else None,
        "symbol": order_request.get("symbol"),
        "side": order_request.get("side"),
        "qty": order_request.get("qty"),
        "product_type": order_request.get("productType"),
        "order_type": order_request.get("type"),
        "traded_price": fill_details.get("traded_price"),
        "filled_qty": fill_details.get("filled_qty"),
        "order_status": fill_details.get("status"),
        "order_status_label": fill_details.get("status_label"),
        "exchange_order_time": fill_details.get("order_datetime"),
        "fill_source": fill_details.get("source"),
        "place_response": place_response,
        **context,
    }


def append_execution_log(script, record):
    with (LOG_DIR / f"{script}-executions.jsonl").open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(record, ensure_ascii=False) + "\n")
    log_path = LOG_DIR / f"{script}-executions.jsonl"
    return log_path


def print_execution_log(script, record, log_path):
    title = f"{script.upper()} EXECUTION LOG"
    border = "=" * (len(title) + 8)
    lines = [
        border,
        f"=== {title} ===",
        f"Time (IST):        {record.get('timestamp_ist')}",
        f"Action:            {record.get('action')}",
        f"Success:           {record.get('success')}",
        f"Symbol:            {record.get('symbol')}",
        f"Qty Requested:     {record.get('qty')}",
        f"Filled Qty:        {record.get('filled_qty')}",
        f"Traded Price:      {record.get('traded_price')}",
        f"Order ID:          {record.get('order_id')}",
        f"Order Status:      {record.get('order_status_label') or record.get('order_status')}",
        f"Exchange Time:     {record.get('exchange_order_time')}",
        f"Product Type:      {record.get('product_type')}",
    ]

    if record.get("index_symbol"):
        lines.append(f"Index Symbol:      {record.get('index_symbol')}")
    if record.get("index_price") is not None:
        lines.append(f"Index Price:       {record.get('index_price')}")
    if record.get("trigger_reason"):
        lines.append(f"Trigger Reason:    {record.get('trigger_reason')}")
    if record.get("index_entry") is not None:
        lines.append(f"Index Entry:       {record.get('index_entry')}")
    if record.get("index_stop_loss") is not None:
        lines.append(f"Index Stop Loss:   {record.get('index_stop_loss')}")
    if record.get("index_target") is not None:
        lines.append(f"Index Target:      {record.get('index_target')}")
    if record.get("option_type"):
        lines.append(f"Option Type:       {record.get('option_type')}")
    if record.get("order_lots") is not None:
        lines.append(f"Order Lots:        {record.get('order_lots')}")
    if record.get("lot_size") is not None:
        lines.append(f"Lot Size:          {record.get('lot_size')}")
    if record.get("api_message"):
        lines.append(f"API Message:       {record.get('api_message')}")
    if not record.get("success"):
        lines.append(f"Place Response:    {record.get('place_response')}")

    lines.extend([f"Log File:          {log_path}", border])
    print("\n".join(lines))


def log_execution(fyers_client, script, action, order_request, place_response, context=None):
    fill_details = {}
    if place_response and place_response.get("s") == "ok" and place_response.get("id"):
        fill_details = fetch_order_fill(
            fyers_client,
            place_response["id"],
            order_request.get("symbol"),
        )

    record = build_execution_record(
        script=script,
        action=action,
        order_request=order_request,
        place_response=place_response,
        context=context,
        fill_details=fill_details,
    )
    log_path = append_execution_log(script, record)
    print_execution_log(script, record, log_path)
    return record
