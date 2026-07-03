import unittest

from execution_log import build_execution_record


class ExecutionLogTests(unittest.TestCase):
    def test_build_execution_record_includes_fill_and_context(self):
        record = build_execution_record(
            script="buy",
            action="BUY",
            order_request={
                "symbol": "NSE:NIFTY25000CE",
                "qty": 50,
                "side": 1,
                "productType": "INTRADAY",
                "type": 2,
            },
            place_response={"s": "ok", "id": "order-1", "code": 1101, "message": "Success"},
            context={"index_price": 24120.5, "trigger_reason": "CE entry"},
            fill_details={
                "traded_price": 132.4,
                "filled_qty": 50,
                "status": 2,
                "status_label": "filled",
                "order_datetime": "2026-07-03 14:30:00",
                "source": "orderbook",
            },
        )

        self.assertTrue(record["success"])
        self.assertEqual(record["traded_price"], 132.4)
        self.assertEqual(record["filled_qty"], 50)
        self.assertEqual(record["index_price"], 24120.5)
        self.assertEqual(record["order_status_label"], "filled")


if __name__ == "__main__":
    unittest.main()
