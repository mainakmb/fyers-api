import importlib
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class RuntimeConfigTests(unittest.TestCase):
    def test_uses_environment_values_when_present(self):
        with patch.dict(
            os.environ,
            {
                "INDEX_SYMBOL": "NSE:NIFTY",
                "OPTIONS_SYMBOL": "NSE:NIFTY25000CE",
                "INDEX_STOP_LOSS": "75000",
                "INDEX_TARGET": "76000",
            },
            clear=False,
        ):
            import main

            main = importlib.reload(main)
            self.assertEqual(main.INDEX_SYMBOL, "NSE:NIFTY")
            self.assertEqual(main.OPTIONS_SYMBOL, "NSE:NIFTY25000CE")
            self.assertEqual(main.INDEX_STOP_LOSS, 75000.0)
            self.assertEqual(main.INDEX_TARGET, 76000.0)

    def test_falls_back_to_defaults_when_values_are_missing(self):
        with patch.dict(os.environ, {}, clear=False):
            for key in ["INDEX_SYMBOL", "OPTIONS_SYMBOL", "INDEX_STOP_LOSS", "INDEX_TARGET"]:
                os.environ.pop(key, None)

            import main

            main = importlib.reload(main)
            self.assertEqual(main.INDEX_SYMBOL, "BSE:SENSEX-INDEX")
            self.assertEqual(main.OPTIONS_SYMBOL, "BSE:SENSEX2670276900PE")
            self.assertEqual(main.INDEX_STOP_LOSS, 77200.0)
            self.assertEqual(main.INDEX_TARGET, 76480.0)


if __name__ == "__main__":
    unittest.main()
