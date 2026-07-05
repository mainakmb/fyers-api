#!/usr/bin/env bash
set -euo pipefail

KEY_PATH="${1:-${HOME}/.ssh/id_rsa}"

if [ -z "${SSH_PRIVATE_KEY:-}" ]; then
  echo "::error::SSH_PRIVATE_KEY is empty. Add the full private key under Settings → Environments → production → Environment secrets."
  exit 1
fi

mkdir -p "$(dirname "${KEY_PATH}")"
chmod 700 "$(dirname "${KEY_PATH}")"

key="${SSH_PRIVATE_KEY//$'\r'/}"
if [[ "${key}" != *$'\n'* ]] && [[ "${key}" == *'\n'* ]]; then
  key="$(printf '%b' "${key}")"
fi

printf '%s' "${key}" > "${KEY_PATH}"
if [ -n "${key}" ] && [ "${key: -1}" != $'\n' ]; then
  printf '\n' >> "${KEY_PATH}"
fi
chmod 600 "${KEY_PATH}"

if ! ssh-keygen -y -f "${KEY_PATH}" > "${KEY_PATH}.pub" 2>/tmp/ssh-keygen.err; then
  echo "::error::Invalid SSH_PRIVATE_KEY. Paste the full unencrypted OpenSSH/PEM private key, including BEGIN/END lines."
  cat /tmp/ssh-keygen.err >&2
  exit 1
fi

echo "SSH key ready: $(ssh-keygen -lf "${KEY_PATH}.pub")"
