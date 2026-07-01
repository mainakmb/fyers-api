# FYERS Options Exit Monitor

A Python script that monitors a live index price over the FYERS WebSocket and automatically squares off an open options position when index-based stop-loss or target levels are hit.

The script does **not** place entry orders. Open your position manually (or via another tool), then run this monitor to manage exits.

## How it works

1. Verifies an open position exists for the configured option symbol.
2. Subscribes to real-time ticks for the index symbol (e.g. `BSE:SENSEX-INDEX`).
3. Evaluates exit rules on each tick:
   - **Stop-loss** — exits immediately when the index crosses the SL level.
   - **Target** — when the index first crosses the target, waits 2 seconds (premium float), then exits with a market order even if price bounces back.

Exit direction is inferred from the option symbol suffix (`CE` or `PE`):

| Option | Stop-loss triggers when | Target triggers when |
|--------|-------------------------|----------------------|
| CE (call) | Index ≤ SL | Index ≥ target |
| PE (put)  | Index ≥ SL | Index ≤ target |

## Prerequisites

- Python 3.11+
- A [FYERS](https://fyers.in/) trading account with API access
- An active options position to monitor

## Setup

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install fyers-apiv3
```

### 2. Authenticate

Generate a daily access token using `auth.py`:

```bash
python auth.py
```

Complete the browser login flow, paste the `auth_code` when prompted, and copy the access token from the output.

Store the token in one of these ways:

- **Local file (recommended for development):** save the token to an `auth` file in the project root (this file is gitignored).
- **Environment variable:** set `FYERS_ACCESS_TOKEN`.

```bash
export FYERS_ACCESS_TOKEN="your_access_token_here"
```

### 3. Verify API connectivity

```bash
python test-api.py
```

This checks your profile and available margin without placing any orders.

## Configuration

All runtime settings are controlled via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `FYERS_ACCESS_TOKEN` | FYERS access token (if not using `auth` file) | — |
| `INDEX_SYMBOL` | Index to monitor for exit triggers | `BSE:SENSEX-INDEX` |
| `OPTIONS_SYMBOL` | Option contract to square off | `BSE:SENSEX2670276900PE` |
| `INDEX_STOP_LOSS` | Index level for immediate stop-loss exit | `77200.0` |
| `INDEX_TARGET` | Index level for delayed target exit | `76480.0` |

Example:

```bash
export INDEX_SYMBOL="BSE:SENSEX-INDEX"
export OPTIONS_SYMBOL="BSE:SENSEX2670276900PE"
export INDEX_STOP_LOSS="77200.0"
export INDEX_TARGET="76480.0"
python main.py
```

Update `OPTIONS_SYMBOL` to match your current expiry and strike before each session.

> **Note:** Exit orders use `productType: "MARGIN"`. If your position is intraday, change this in `main.py` to `"INTRADAY"`.

## Running the monitor

```bash
python main.py
```

The script aborts safely if no open position is found for `OPTIONS_SYMBOL`. Once running, it stays connected via WebSocket until an exit is triggered or the process is stopped.

## GitHub Actions

The workflow in `.github/workflows/fyers-trading.yml` can be triggered manually from the Actions tab. It accepts the same configuration inputs as environment variables and runs tests, connectivity checks, and the trading script.

Required secret:

- `FYERS_ACCESS_TOKEN` — add under **Settings → Secrets and variables → Actions**

Use with care: the workflow will attempt a real market exit if an open position exists.

## Tests

```bash
python -m unittest discover -s tests -v
```

Tests cover configuration loading and defaults. They do not hit the live API.

## Project layout

```
├── main.py          # WebSocket monitor and exit logic
├── auth.py          # OAuth token generation helper
├── test-api.py      # API connectivity smoke test
├── tests/           # Unit tests
└── .github/workflows/fyers-trading.yml
```

## Safety

- This script places **real market orders** against your FYERS account.
- Always confirm `OPTIONS_SYMBOL`, SL, and target levels before starting.
- Run `test-api.py` first to verify your token is valid.
- Never commit `auth`, `.env`, or API secrets to version control.
