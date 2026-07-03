# FYERS Options Trading Scripts

Local Python scripts that watch a live index over the FYERS WebSocket and place market orders on options contracts.

| Script | Purpose |
|--------|---------|
| `buy.py` | Enter a position when the index hits an entry level |
| `sell.py` | Exit an open position on stop-loss or target levels |

These scripts are intended for **local execution only** — run them from your machine during market hours.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install fyers-apiv3 python-dotenv

python auth.py
cp .env.buy.example .env.buy
cp .env.sell.example .env.sell
# Edit .env.buy and .env.sell for today's symbols and levels

python test-api.py   # verify token
python buy.py        # wait for entry
python sell.py       # manage exit after position is open
```

## How it works

### Buy (`buy.py`)

1. Loads config from `.env.buy`.
2. Aborts if a position already exists for `OPTIONS_SYMBOL`.
3. Subscribes to `INDEX_SYMBOL` over WebSocket.
4. Fetches lot size from the FYERS symbol master API and places a **market buy** for `ORDER_LOTS` lot(s) when the index crosses `INDEX_ENTRY`.

| Option | Buy triggers when |
|--------|-------------------|
| CE (call) | Index ≤ `INDEX_ENTRY` (buy on dip) |
| PE (put)  | Index ≥ `INDEX_ENTRY` (buy on rally) |

Entry direction matches `sell.py` stop-loss logic so buy and sell levels stay consistent.

Optional `ENTRY_DELAY_SECONDS` holds the order briefly after the trigger. If price retraces out of the entry zone before the delay expires, the timer resets.

### Sell (`sell.py`)

1. Loads config from `.env.sell`.
2. Aborts if no open position exists for `OPTIONS_SYMBOL`.
3. Subscribes to `INDEX_SYMBOL` over WebSocket.
4. Exits with a **market order** on stop-loss or target.

| Option | Stop-loss triggers when | Target triggers when |
|--------|-------------------------|----------------------|
| CE | Index ≤ SL | Index ≥ target |
| PE | Index ≥ SL | Index ≤ target |

- **Stop-loss** — fires immediately.
- **Target** — waits `EXIT_DELAY_SECONDS` (premium float) after the target is hit, then exits. If price retraces out of the target zone before the delay expires, the timer resets.

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

Generate a daily access token:

```bash
python auth.py
```

Complete the browser login flow and paste the `auth_code` when prompted. On success, the token is saved to `auth` in the project root (gitignored).

Scripts read the token from `auth` first, then fall back to `FYERS_ACCESS_TOKEN` if the file is missing.

### 3. Configure environment files

Each script loads its own env file:

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
| `ORDER_LOTS` | Number of lots to buy (qty = API lot size × lots) | `1` |
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

**Exit:**

```bash
python sell.py
```

Typical flow: run `buy.py` for entry, then `sell.py` in a separate terminal to manage the exit.

## Operational notes

### Daily token refresh

FYERS access tokens expire daily. Re-run `python auth.py` each morning after 8:00 AM to generate a fresh token before trading.

## Tests

```bash
python -m unittest discover -s tests -v
```

Tests cover config loading only. They do not call the live API.

## Project layout

```
├── buy.py              # Index-triggered market buy entry
├── sell.py             # WebSocket monitor and exit logic
├── auth.py             # OAuth token generation helper
├── test-api.py         # API connectivity smoke test
├── .env.buy.example    # Example config for buy.py
├── .env.sell.example   # Example config for sell.py
├── .gitignore
└── tests/
```

## Safety

- These scripts place **real market orders** against your FYERS account.
- Always confirm `OPTIONS_SYMBOL`, entry, SL, and target levels before starting.
- Run `test-api.py` first to verify your token is valid.
- Never commit `auth`, `.env.buy`, `.env.sell`, or API secrets to version control.
