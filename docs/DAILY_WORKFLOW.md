# Daily Trading Bot Deploy Workflow

Hands-free pipeline split into two workflows:

- **`deploy-server.yml`** — provisions the DigitalOcean droplet and syncs Terraform state
- **`deploy-app.yml`** — deploys Python code over SSH, writes FYERS secrets, and restarts the tmux session

## Architecture

```text
deploy-server.yml
  ├─ Terraform apply  →  $4 DO droplet (512MB + 1GB swap via cloud-init)
  └─ State sync       →  mainakmb/tfstate-storage/fyers-api/terraform.tfstate

deploy-app.yml
  ├─ Read server IP   →  from remote tfstate (no re-provision)
  └─ SSH deploy       →  /root/trading-bot/
                           ├─ .env          (FYERS secrets, chmod 600)
                           ├─ .env.buy      (entry strategy)
                           ├─ .env.sell     (exit strategy)
                           └─ tmux session  trading_session → python3 main.py
```

## Required GitHub Secrets

Configure these under **Settings → Environments → production → Environment secrets** (both workflows use the `production` environment):

| Secret | Workflow |
|--------|----------|
| `DIGITALOCEAN_TOKEN` | Deploy Server |
| `SSH_PRIVATE_KEY` | Both |
| `STATE_REPO_PAT` | Both |
| `FYERS_ACCESS_TOKEN` | Deploy App |
| `FYERS_APP_ID` | Deploy App |
| `FYERS_SECRET_KEY` | Deploy App |

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

## Morning routine (refresh token + redeploy)

### Option A — helper script (recommended)

After generating a fresh token locally:

```bash
python auth.py
chmod +x scripts/push-daily-token.sh
./scripts/push-daily-token.sh
```

This updates `FYERS_ACCESS_TOKEN` and triggers `deploy-app.yml` via the GitHub CLI.

### Option B — GitHub CLI commands

```bash
# 1. Update the secret from your local auth file
gh secret set FYERS_ACCESS_TOKEN --repo mainakmb/fyers-api --body "$(tr -d '[:space:]' < auth)"

# 2. Trigger the app deploy workflow manually
gh workflow run deploy-app.yml --repo mainakmb/fyers-api

# 3. Watch progress
gh run watch --repo mainakmb/fyers-api
```

### Option C — API dispatch (for automation)

```bash
gh api repos/mainakmb/fyers-api/dispatches \
  -f event_type=refresh-trading-token
```

Ensure `FYERS_ACCESS_TOKEN` is already updated before dispatching.

## When each workflow runs

| Workflow | Trigger |
|----------|---------|
| **Deploy Server** | Push to `main` changing `terraform/**`; manual dispatch (optional **Destroy server** checkbox) |
| **Deploy App** | Push to `main` changing `*.py`, `requirements.txt`, env examples; manual dispatch; `refresh-trading-token` dispatch |

Run **Deploy Server** first on a fresh setup, then **Deploy App**. Daily token refreshes only need **Deploy App**.

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
ssh -i ~/.ssh/id_rsa root@"${SERVER_IP}" "tmux attach -t trading_session"   # detach: Ctrl+B then D
ssh -i ~/.ssh/id_rsa root@"${SERVER_IP}" "tail -f /root/trading-bot/logs/fyersApi.log"
```

## Strategy configuration

**Manual deploy (Run workflow):** [Deploy App](https://github.com/mainakmb/fyers-api/actions/workflows/deploy-app.yml) exposes inputs for every buy/sell field from `.env.buy.example` and `.env.sell.example` (index symbol, options symbol, entry/SL/target, lots, product type, delay seconds). Defaults match the example files — update them for today's contract before running.

**Automatic deploy (push to `main`):** Uses `.env.buy.example` and `.env.sell.example` from the repo. Edit those files and push to redeploy with updated strategy settings.

**Daily token refresh** (`push-daily-token.sh`) triggers Deploy App without inputs, so strategy comes from the example files in `main`.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| SSH timeout after apply | New droplet still booting; re-run workflow or wait for cloud-init |
| `tmux has-session` fails | `ssh root@IP 'cat /root/trading-bot/logs/fyersApi.log'` |
| Auth errors in logs | Re-run `push-daily-token.sh` with a fresh token from `auth.py` |
| State push failed | Confirm `STATE_REPO_PAT` can write to `mainakmb/tfstate-storage` |
