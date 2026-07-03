# FYERS Options Trading Scripts

Python scripts that monitor a live index price over the FYERS WebSocket and place market orders on options contracts.

- **`buy.py`** — enters a position when the index hits an entry level
- **`sell.py`** — exits an open position on stop-loss or target levels

## How it works

### Sell (`sell.py`)

1. Verifies an open position exists for the configured option symbol.
2. Subscribes to real-time ticks for the index symbol.
3. Evaluates exit rules on each tick:
   - **Stop-loss** — exits immediately when the index crosses the SL level.
   - **Target** — when the index first crosses the target, waits briefly (premium float), then exits with a market order.

| Option | Stop-loss triggers when | Target triggers when |
|--------|-------------------------|----------------------|
| CE (call) | Index ≤ SL | Index ≥ target |
| PE (put)  | Index ≥ SL | Index ≤ target |

### Buy (`buy.py`)

1. Confirms no open position exists for the option symbol.
2. Subscribes to real-time index ticks.
3. Places a **market buy** when the index crosses `INDEX_ENTRY`.

| Option | Buy triggers when |
|--------|-------------------|
| CE | Index ≥ `INDEX_ENTRY` |
| PE | Index ≤ `INDEX_ENTRY` |

## Prerequisites

- Python 3.11+
- A [FYERS](https://fyers.in/) trading account with API access

## Setup

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install fyers-apiv3 python-dotenv
```

### 2. Authenticate

Generate a daily access token using `auth.py`:

```bash
python auth.py
```

Complete the browser login flow and paste the `auth_code` when prompted. On success, the access token is written automatically to `auth` in the project root (gitignored).

### 3. Configure environment files

Each script uses its own env file. Copy the examples and edit for your session:

```bash
cp .env.buy.example .env.buy
cp .env.sell.example .env.sell
```

**`.env.buy`** — entry settings:

| Variable | Description | Default |
|----------|-------------|---------|
| `INDEX_SYMBOL` | Index to monitor | `NSE:NIFTY50-INDEX` |
| `OPTIONS_SYMBOL` | Option contract to buy | `BSE:SENSEX2670277100PE` |
| `INDEX_ENTRY` | Index level that triggers the buy | `24100.0` |
| `ORDER_QTY` | Option quantity to buy | `1` |
| `PRODUCT_TYPE` | FYERS product type | `INTRADAY` |
| `ENTRY_DELAY_SECONDS` | Hold time after entry trigger (0 = immediate) | `0` |

**`.env.sell`** — exit settings:

| Variable | Description | Default |
|----------|-------------|---------|
| `INDEX_SYMBOL` | Index to monitor | `NSE:NIFTY50-INDEX` |
| `OPTIONS_SYMBOL` | Option contract to square off | `BSE:SENSEX2670277100PE` |
| `INDEX_STOP_LOSS` | Index level for immediate stop-loss exit | `24150.0` |
| `INDEX_TARGET` | Index level for delayed target exit | `24036.0` |
| `PRODUCT_TYPE` | FYERS product type | `INTRADAY` |
| `EXIT_DELAY_SECONDS` | Premium float delay before target exit | `1` |

Update `OPTIONS_SYMBOL` to match your current expiry and strike before each session.

### 4. Verify API connectivity

```bash
python test-api.py
```

## Running

**Entry:**

```bash
python buy.py
```

Aborts if a position already exists. After a successful buy, stops placing new orders.

**Exit:**

```bash
python sell.py
```

Aborts if no open position is found. Runs until an exit is triggered or the process is stopped.

Typical flow: run `buy.py` for entry, then `sell.py` to manage exits.

## Operational notes

### The access token lifecycle

FYERS access tokens expire daily. If you generated your `auth` file token today, it will not work tomorrow morning. Re-run `python auth.py` each morning after 8:00 AM to generate a fresh token.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Project layout

```
├── buy.py              # Index-triggered market buy entry
├── sell.py             # WebSocket monitor and exit logic
├── auth.py             # OAuth token generation helper
├── test-api.py         # API connectivity smoke test
├── .env.buy.example    # Example config for buy.py
├── .env.sell.example   # Example config for sell.py
└── tests/
```

## Safety

- These scripts place **real market orders** against your FYERS account.
- Always confirm `OPTIONS_SYMBOL`, entry, SL, and target levels before starting.
- Run `test-api.py` first to verify your token is valid.
- Never commit `auth`, `.env.buy`, `.env.sell`, or API secrets to version control.
