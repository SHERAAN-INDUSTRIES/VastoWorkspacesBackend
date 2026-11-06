#!/usr/bin/env bash
set -Eeuo pipefail
echo 'Configuring Vasto sign-in'
# Check if OAuth credentials are already configured
if grep -q '^VASTO_CLIENT_ID=.' .env && grep -q '^VASTO_CLIENT_SECRET=.' .env; then
  printf 'OAuth credentials already configured in .env, skipping credential import.\n'
else
  if [[ -n "$CREDENTIALS_FILE" ]]; then
    "$PY" scripts/import-oidc-credentials.py "$CREDENTIALS_FILE" || exit $?
  elif ((INTERACTIVE)); then
    "$PY" scripts/import-oidc-credentials.py --interactive || exit $?
  else
    shopt -s nullglob
    local_credentials=("$HOME"/.config/vasto-workspaces/*-local.env)
    shopt -u nullglob
    if ((${#local_credentials[@]} == 1)); then
      "$PY" scripts/import-oidc-credentials.py "${local_credentials[0]}" || exit $?
    elif [[ -t 0 ]]; then
      if ((${#local_credentials[@]} > 1)); then
        printf 'Found multiple local Vasto credential files.\n'
        read -r -p 'Enter the file path to use (blank to enter credentials): ' CREDENTIALS_FILE
      fi
      if [[ -n "$CREDENTIALS_FILE" ]]; then
        "$PY" scripts/import-oidc-credentials.py "$CREDENTIALS_FILE" || exit $?
      else
        "$PY" scripts/import-oidc-credentials.py --interactive || exit $?
      fi
    else
      printf 'No Vasto credentials file was selected. Pass --credentials-file PATH or run this script in a terminal for hidden interactive setup.\n' >&2
      exit 1
    fi
  fi
fi
