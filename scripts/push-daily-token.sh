#!/usr/bin/env bash
# Push today's FYERS access token to GitHub Secrets and trigger a remote redeploy.
set -euo pipefail

REPO="${1:-mainakmb/fyers-api}"
TOKEN_FILE="${2:-auth}"
WORKFLOW="${3:-deploy-app.yml}"

if [[ ! -f "${TOKEN_FILE}" ]]; then
  echo "Token file not found: ${TOKEN_FILE}" >&2
  echo "Run 'python auth.py' locally first, or pass the path to your token file." >&2
  exit 1
fi

TOKEN="$(tr -d '[:space:]' < "${TOKEN_FILE}")"
if [[ -z "${TOKEN}" ]]; then
  echo "Token file is empty: ${TOKEN_FILE}" >&2
  exit 1
fi

echo "Updating FYERS_ACCESS_TOKEN secret on ${REPO} (production environment)..."
gh secret set FYERS_ACCESS_TOKEN --env production --repo "${REPO}" --body "${TOKEN}"

echo "Triggering workflow ${WORKFLOW}..."
gh workflow run "${WORKFLOW}" --repo "${REPO}"

echo "Done. Monitor the run with:"
echo "  gh run list --repo ${REPO} --workflow ${WORKFLOW} --limit 1"
