# FYERS Options Trading Bot

Python scripts that watch a live index over the FYERS WebSocket and place market orders on options contracts. Run locally during development, or deploy hands-free to a **$4/month DigitalOcean droplet** via GitHub Actions.

| Script | Purpose |
|--------|---------|
| `buy.py` | Enter a position when the index hits an entry level |
| `sell.py` | Exit an open position on stop-loss or target levels |

## Quick start (local)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python auth.py
cp .env.buy.example .env.buy
cp .env.sell.example .env.sell
# Edit .env.buy and .env.sell for today's symbols and levels

python test-api.py   # verify token
python buy.py        # wait for entry (separate terminal)
python sell.py       # manage exit after position is open
```

## Cloud deployment

Infrastructure and app deploy use separate GitHub Actions workflows:

| Workflow | What it does |
|----------|----------------|
| [**Deploy Server**](.github/workflows/deploy-server.yml) | Provisions a DigitalOcean droplet (`blr1`, 512MB + 1GB swap) and syncs Terraform state to [`mainakmb/tfstate-storage`](https://github.com/mainakmb/tfstate-storage) |
| [**Deploy App**](.github/workflows/deploy-app.yml) | Syncs code to `/root/trading-bot/` and runs `test-api.py` (push, token refresh, manual sync) |
| [**Deploy Buy**](.github/workflows/deploy-app-buy.yml) | Deploys + starts `buy.py` in tmux (`buy_session`) with buy-only inputs |
| [**Deploy Sell**](.github/workflows/deploy-app-sell.yml) | Deploys + starts `sell.py` in tmux (`sell_session`) with sell-only inputs |

```text
GitHub Actions
  deploy-server.yml     →  DO droplet + tfstate sync
  deploy-app.yml        →  code sync + test-api.py
  deploy-app-buy.yml    →  buy.py  (tmux: buy_session)
  deploy-app-sell.yml   →  sell.py (tmux: sell_session)
```

**First-time setup**

1. Add **Environment secrets** under [Settings → Environments → production](https://github.com/mainakmb/fyers-api/settings/environments/production) (not repository secrets — both workflows use the `production` environment):

   | Secret | Used by |
   |--------|---------|
   | `DIGITALOCEAN_TOKEN` | Deploy Server |
   | `SSH_PRIVATE_KEY` | Both |
   | `STATE_REPO_PAT` | Both |
   | `FYERS_ACCESS_TOKEN` | Deploy App / Buy / Sell |
   | `FYERS_APP_ID` | Deploy App / Buy / Sell |
   | `FYERS_SECRET_KEY` | Deploy App / Buy / Sell |

2. Run [**Deploy Server**](https://github.com/mainakmb/fyers-api/actions/workflows/deploy-server.yml) — provisions the droplet and syncs state to `mainakmb/tfstate-storage`
3. Run [**Deploy App**](https://github.com/mainakmb/fyers-api/actions/workflows/deploy-app.yml) — syncs code and runs `test-api.py`
4. To trade, run [**Deploy Buy**](https://github.com/mainakmb/fyers-api/actions/workflows/deploy-app-buy.yml) and/or [**Deploy Sell**](https://github.com/mainakmb/fyers-api/actions/workflows/deploy-app-sell.yml) with today's strategy fields (blank inputs keep `.env.buy.example` / `.env.sell.example` values)

**Connect to the server**

After **Deploy Server** succeeds, note the IP from the workflow **Show Outputs** step (`server_static_ip`), the [DigitalOcean dashboard](https://cloud.digitalocean.com/droplets), or remote state at `mainakmb/tfstate-storage/fyers-api/terraform.tfstate`.

SSH as `root` with the **same private key** stored in `SSH_PRIVATE_KEY`:

```bash
ssh -i ~/.ssh/id_ed25519 root@YOUR_DROPLET_IP
```

```bash
# List running sessions
tmux list-sessions

# Attach to buy or sell loop (detach: Ctrl+B, then D)
tmux attach -t buy_session
tmux attach -t sell_session

tail -f /root/trading-bot/logs/runner-buy_session.log
tail -f /root/trading-bot/logs/runner-sell_session.log
tail -f /root/trading-bot/logs/fyersApi.log

# Re-run API connectivity test manually
cd /root/trading-bot && source .venv/bin/activate && python3 test-api.py
```

**Daily token refresh**

```bash
python auth.py
./scripts/push-daily-token.sh
```

This updates `FYERS_ACCESS_TOKEN` in the `production` environment and triggers **Deploy App** (code sync + `test-api.py` only). Then run **Deploy Buy** and/or **Deploy Sell** to start the loops you need.

**Destroy the droplet** — run **Deploy Server** manually with the **Destroy server** checkbox checked.

Full ops guide: [docs/DAILY_WORKFLOW.md](docs/DAILY_WORKFLOW.md)

## How it works

### Buy (`buy.py`)

1. Loads secrets from `.env`, strategy from `.env.buy`.
2. Aborts if a position already exists for `OPTIONS_SYMBOL`.
3. Subscribes to `INDEX_SYMBOL` over WebSocket.
4. Fetches lot size from the FYERS symbol master API and places a **market buy** when the index crosses `INDEX_ENTRY`.

| Option | Buy triggers when |
|--------|-------------------|
| CE (call) | Index ≤ `INDEX_ENTRY` (buy on dip) |
| PE (put)  | Index ≥ `INDEX_ENTRY` (buy on rally) |

Optional `ENTRY_DELAY_SECONDS` holds the order briefly after the trigger. If price retraces out of the entry zone before the delay expires, the timer resets.

### Sell (`sell.py`)

1. Loads secrets from `.env`, strategy from `.env.sell`.
2. Subscribes to `INDEX_SYMBOL` over WebSocket (runs even before a position exists so the server stays up after a fresh deploy).
3. When a position is open, exits with a **market order** on stop-loss or target.

| Option | Stop-loss triggers when | Target triggers when |
|--------|-------------------------|----------------------|
| CE | Index ≤ SL | Index ≥ target |
| PE | Index ≥ SL | Index ≤ target |

- **Stop-loss** — fires immediately.
- **Target** — waits `EXIT_DELAY_SECONDS` after the target is hit, then exits.

## Prerequisites

- Python 3.11+
- A [FYERS](https://fyers.in/) trading account with API access
- For cloud deploy: DigitalOcean account, GitHub `production` environment secrets

## Local setup

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Authenticate

Generate a daily access token:

```bash
python auth.py
```

Complete the browser login flow and paste the `auth_code` when prompted. On success, the token is saved to `auth` in the project root (gitignored).

Scripts read the token from `auth` first, then fall back to `FYERS_ACCESS_TOKEN` from `.env`.

### 3. Configure strategy files

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
| `ORDER_LOTS` | Number of lots to buy | `1` |
| `PRODUCT_TYPE` | FYERS product type (`INTRADAY` or `MARGIN`) | `INTRADAY` |
| `ENTRY_DELAY_SECONDS` | Hold time after entry trigger (0 = immediate) | `0` |

**`.env.sell`** — exit settings:

| Variable | Description | Default |
|----------|-------------|---------|
| `INDEX_SYMBOL` | Index to monitor | `NSE:NIFTY50-INDEX` |
| `OPTIONS_SYMBOL` | Option contract to square off | `BSE:SENSEX2670277100PE` |
| `INDEX_STOP_LOSS` | Index level for immediate stop-loss exit | `24150.0` |
| `INDEX_TARGET` | Index level for delayed target exit | `24036.0` |
| `PRODUCT_TYPE` | FYERS product type (`INTRADAY` or `MARGIN`) | `INTRADAY` |
| `EXIT_DELAY_SECONDS` | Premium float delay before target exit | `1` |

Update `OPTIONS_SYMBOL` to match your current expiry and strike before each session. Edit `.env.buy.example` / `.env.sell.example` and push to `main` to sync strategy files, or override fields in **Deploy Buy** / **Deploy Sell**. Push and token refresh sync code only — run the buy/sell workflows to go live.

### 4. Verify API connectivity

```bash
python test-api.py
```

Checks REST auth (`get_profile`, funds). It does not verify the live WebSocket feed — WebSocket errors (e.g. 504) outside market hours are normal.

## Tests

```bash
python -m unittest discover -s tests -v
```

Tests cover config loading only. They do not call the live API.

## Logs

Runtime logs are written under `logs/` (gitignored):

- `logs/buy-executions.jsonl` / `logs/sell-executions.jsonl` — trade execution records
- `logs/fyersApi.log` / `logs/fyersRequests.log` — FYERS SDK logs

On the server (`/root/trading-bot/logs/`):

- `runner-buy_session.log` / `runner-sell_session.log` — stdout/stderr from each tmux loop
- `fyersApi.log` — FYERS SDK logs

## Project layout

```
├── buy.py / sell.py             # Trading loops (separate tmux sessions on server)
├── execution_log.py             # Shared execution logging
├── auth.py                      # OAuth token helper (local)
├── test-api.py                  # API connectivity smoke test
├── requirements.txt
├── .env.buy.example             # Entry strategy template
├── .env.sell.example            # Exit strategy template
├── scripts/
│   └── push-daily-token.sh      # Refresh FYERS token + trigger Deploy App
├── terraform/                   # DigitalOcean droplet (Terraform)
├── .github/workflows/
│   ├── deploy-server.yml        # Provision / destroy droplet
│   ├── deploy-app.yml           # Sync code + test-api
│   ├── deploy-app-buy.yml       # Start buy.py in tmux
│   ├── deploy-app-sell.yml      # Start sell.py in tmux
│   └── deploy-app-reusable.yml  # Shared deploy logic
├── docs/
│   └── DAILY_WORKFLOW.md        # Full CI/CD ops guide
└── tests/
```

## Safety

- These scripts place **real market orders** against your FYERS account.
- Always confirm `OPTIONS_SYMBOL`, entry, SL, and target levels before starting.
- Run `test-api.py` first to verify your token is valid (REST only).
- WebSocket 504 errors in `fyersApi.log` outside market hours (evenings/weekends) usually mean the FYERS feed is down — retry during live session.
- Never commit `auth`, `.env`, `.env.buy`, `.env.sell`, Terraform state, or API secrets.
- Remote state lives in the private repo `mainakmb/tfstate-storage` — not in this repo.
