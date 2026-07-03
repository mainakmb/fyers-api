import importlib
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class BuyConfigTests(unittest.TestCase):
    def test_uses_environment_values_when_present(self):
        with patch.dict(
            os.environ,
            {
                "INDEX_SYMBOL": "NSE:NIFTY",
                "OPTIONS_SYMBOL": "NSE:NIFTY25000CE",
                "INDEX_ENTRY": "75000",
                "ORDER_LOTS": "2",
            },
            clear=False,
        ):
            import buy

            buy = importlib.reload(buy)
            self.assertEqual(buy.INDEX_SYMBOL, "NSE:NIFTY")
            self.assertEqual(buy.OPTIONS_SYMBOL, "NSE:NIFTY25000CE")
            self.assertEqual(buy.INDEX_ENTRY, 75000.0)
            self.assertEqual(buy.ORDER_LOTS, 2)

    def test_parse_option_type_from_suffix(self):
        import buy

        buy = importlib.reload(buy)
        self.assertEqual(buy.parse_option_type("NSE:NIFTY25000CE"), "CE")
        self.assertEqual(buy.parse_option_type("BSE:SENSEX2670277100PE"), "PE")

    def test_entry_triggered_uses_put_and_call_logic(self):
        import buy

        buy = importlib.reload(buy)
        buy.INDEX_ENTRY = 100.0

        self.assertTrue(buy.entry_triggered(99.0, "CE"))
        self.assertFalse(buy.entry_triggered(101.0, "CE"))
        self.assertTrue(buy.entry_triggered(101.0, "PE"))
        self.assertFalse(buy.entry_triggered(99.0, "PE"))


class SellConfigTests(unittest.TestCase):
    def test_uses_environment_values_when_present(self):
        with patch.dict(
            os.environ,
            {
                "INDEX_SYMBOL": "NSE:NIFTY",
                "OPTIONS_SYMBOL": "NSE:NIFTY25000CE",
                "INDEX_STOP_LOSS": "75000",
                "INDEX_TARGET": "76000",
                "EXIT_DELAY_SECONDS": "2",
            },
            clear=False,
        ):
            import sell

            sell = importlib.reload(sell)
            self.assertEqual(sell.INDEX_SYMBOL, "NSE:NIFTY")
            self.assertEqual(sell.OPTIONS_SYMBOL, "NSE:NIFTY25000CE")
            self.assertEqual(sell.INDEX_STOP_LOSS, 75000.0)
            self.assertEqual(sell.INDEX_TARGET, 76000.0)
            self.assertEqual(sell.EXIT_DELAY_SECONDS, 2.0)


if __name__ == "__main__":
    unittest.main()
