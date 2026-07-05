# Daily Trading Bot Deploy Workflow

Hands-free pipeline split across workflows:

- **`deploy-server.yml`** — provisions the DigitalOcean droplet and syncs Terraform state
- **`deploy-app.yml`** — syncs Python code over SSH, writes FYERS secrets, runs `test-api.py`
- **`deploy-app-buy.yml`** — deploys and starts `buy.py` in tmux (`buy_session`)
- **`deploy-app-sell.yml`** — deploys and starts `sell.py` in tmux (`sell_session`)

## Architecture

```text
deploy-server.yml
  ├─ Terraform apply  →  $4 DO droplet (512MB + 1GB swap via cloud-init)
  └─ State sync       →  mainakmb/tfstate-storage/fyers-api/terraform.tfstate

deploy-app.yml (sync only)
  ├─ Read server IP   →  from remote tfstate
  └─ SSH deploy       →  /root/trading-bot/ + test-api.py

deploy-app-buy.yml / deploy-app-sell.yml
  └─ Same deploy path →  starts buy.py or sell.py in its own tmux session
                           ├─ .env          (FYERS secrets, chmod 600)
                           ├─ .env.buy      (entry strategy)
                           └─ .env.sell     (exit strategy)
```

## Required GitHub Secrets

Configure these under **Settings → Environments → production → Environment secrets**:

| Secret | Workflow |
|--------|----------|
| `DIGITALOCEAN_TOKEN` | Deploy Server |
| `SSH_PRIVATE_KEY` | Deploy App / Buy / Sell |
| `STATE_REPO_PAT` | Deploy App / Buy / Sell |
| `FYERS_ACCESS_TOKEN` | Deploy App / Buy / Sell |
| `FYERS_APP_ID` | Deploy App / Buy / Sell |
| `FYERS_SECRET_KEY` | Deploy App / Buy / Sell |

### Fix `STATE_REPO_PAT` (403 on tfstate-storage)

If [Deploy Server](https://github.com/mainakmb/fyers-api/actions/workflows/deploy-server.yml) fails with `unable to access tfstate-storage: 403`:

1. Create a **classic PAT** with the **`repo`** scope, **or** a **fine-grained PAT** limited to `mainakmb/tfstate-storage` with **Contents: Read and write**.
2. In `mainakmb/fyers-api`, go to **Settings → Environments → production → Add secret**.
3. Name: `STATE_REPO_PAT`, value: the PAT string.
4. Re-run **Deploy Server** from the Actions tab.

Do **not** store this PAT only under repository secrets if the environment secret is missing — the workflow reads from the `production` environment.

### Fix `SSH_PRIVATE_KEY` (exit 255 on Prepare SSH Key)

If Deploy Server fails at **Prepare SSH Key** with exit code `255`, the secret value is missing or not a valid private key.

1. Generate or reuse an **unencrypted** key pair locally:
   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/fyers-trading-bot -N ""
   ```
2. Copy the **private** key file contents exactly (including `BEGIN` / `END` lines):
   ```bash
   cat ~/.ssh/fyers-trading-bot
   ```
3. Add to **Settings → Environments → production → Environment secrets** as `SSH_PRIVATE_KEY`.
4. Re-run **Deploy Server**.

The workflow writes the key to `~/.ssh/id_rsa` on the runner and derives the `.pub` file for Terraform. Use the same key pair you intend to SSH with after deploy.

## Morning routine (refresh token + go live)

### Option A — helper script (recommended)

After generating a fresh token locally:

```bash
python auth.py
chmod +x scripts/push-daily-token.sh
./scripts/push-daily-token.sh
```

This updates `FYERS_ACCESS_TOKEN` and triggers **Deploy App** (sync + `test-api.py`). Then run **Deploy Buy** and/or **Deploy Sell** from the Actions tab.

### Option B — GitHub CLI commands

```bash
# 1. Update the secret from your local auth file
gh secret set FYERS_ACCESS_TOKEN --env production --repo mainakmb/fyers-api --body "$(tr -d '[:space:]' < auth)"

# 2. Sync code and verify API
gh workflow run deploy-app.yml --repo mainakmb/fyers-api

# 3. Start buy and/or sell loops
gh workflow run deploy-app-buy.yml --repo mainakmb/fyers-api
gh workflow run deploy-app-sell.yml --repo mainakmb/fyers-api

# 4. Watch progress
gh run watch --repo mainakmb/fyers-api
```

### Option C — API dispatch (for automation)

```bash
gh api repos/mainakmb/fyers-api/dispatches \
  -f event_type=refresh-trading-token
```

Ensure `FYERS_ACCESS_TOKEN` is already updated before dispatching. Follow with **Deploy Buy** / **Deploy Sell** to start trading.

## When each workflow runs

| Workflow | Trigger | Starts tmux |
|----------|---------|-------------|
| **Deploy Server** | Push to `main` changing `terraform/**`; manual destroy | — |
| **Deploy App** | Push to `main` (app paths); manual dispatch; token refresh | No |
| **Deploy Buy** | Manual dispatch only | `buy_session` → `buy.py` |
| **Deploy Sell** | Manual dispatch only | `sell_session` → `sell.py` |

Run **Deploy Server** first on a fresh setup, then **Deploy App**. Start **Deploy Buy** for entry monitoring and **Deploy Sell** for exit monitoring — independently, as needed.

### Destroy the droplet

1. Open [Deploy Server](https://github.com/mainakmb/fyers-api/actions/workflows/deploy-server.yml)
2. Click **Run workflow**
3. Check **Destroy the DigitalOcean droplet (terraform destroy)**
4. Run — this tears down the droplet and syncs empty state back to `tfstate-storage`

Push-to-`main` runs always **apply**; destroy is manual-dispatch only.

Updating a secret alone does **not** trigger a run — always follow with `gh workflow run` or the helper script.

## Verify the live server

```bash
SERVER_IP="$(cd terraform && terraform output -raw server_static_ip)"
ssh -i ~/.ssh/id_rsa root@"${SERVER_IP}" "tmux list-sessions"
ssh -i ~/.ssh/id_rsa root@"${SERVER_IP}" "tmux attach -t buy_session"    # detach: Ctrl+B then D
ssh -i ~/.ssh/id_rsa root@"${SERVER_IP}" "tmux attach -t sell_session"
ssh -i ~/.ssh/id_rsa root@"${SERVER_IP}" "tail -f /root/trading-bot/logs/fyersApi.log"
```

## Strategy configuration

**Deploy Buy** — inputs map to `.env.buy` (from `.env.buy.example`; blank keeps example value):

| Input | Variable |
|-------|----------|
| `index_symbol` | `INDEX_SYMBOL` |
| `options_symbol` | `OPTIONS_SYMBOL` |
| `index_entry` | `INDEX_ENTRY` |
| `order_lots` | `ORDER_LOTS` |
| `product_type` | `PRODUCT_TYPE` |
| `entry_delay_seconds` | `ENTRY_DELAY_SECONDS` |

**Deploy Sell** — inputs map to `.env.sell` (from `.env.sell.example`; blank keeps example value):

| Input | Variable |
|-------|----------|
| `index_symbol` | `INDEX_SYMBOL` |
| `options_symbol` | `OPTIONS_SYMBOL` |
| `index_stop_loss` | `INDEX_STOP_LOSS` |
| `index_target` | `INDEX_TARGET` |
| `product_type` | `PRODUCT_TYPE` |
| `exit_delay_seconds` | `EXIT_DELAY_SECONDS` |

**Push to `main`** updates example files on the server via **Deploy App** but does not start tmux. Run **Deploy Buy** / **Deploy Sell** to go live.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| SSH timeout after apply | New droplet still booting; re-run workflow or wait for cloud-init |
| `tmux has-session` fails | `ssh root@IP 'tail -n 80 /root/trading-bot/logs/runner-buy_session.log'` |
| Auth errors in logs | Re-run `push-daily-token.sh` with a fresh token from `auth.py` |
| State push failed | Confirm `STATE_REPO_PAT` can write to `mainakmb/tfstate-storage` |
| WebSocket 504 off-hours | Normal outside market session; `test-api.py` only checks REST |
