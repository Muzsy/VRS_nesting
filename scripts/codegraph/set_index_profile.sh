#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <prod|full>" >&2
  exit 1
fi

PROFILE="$1"
REPO_ENV="$(pwd)/.codegraphcontext/.env"
if [[ ! -f "$REPO_ENV" ]]; then
  echo "Missing repo env: $REPO_ENV" >&2
  exit 1
fi

set_key() {
  local key="$1"
  local value="$2"
  if rg -q "^${key}=" "$REPO_ENV"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$REPO_ENV"
  else
    printf '%s=%s\n' "$key" "$value" >> "$REPO_ENV"
  fi
}

case "$PROFILE" in
  prod)
    set_key IGNORE_TEST_FILES true
    set_key IGNORE_DIRS "node_modules,venv,.venv,env,.env,dist,build,target,out,.git,.idea,.vscode,__pycache__,scripts/experiments,scripts/smoke_*"
    ;;
  full)
    set_key IGNORE_TEST_FILES false
    set_key IGNORE_DIRS "node_modules,venv,.venv,env,.env,dist,build,target,out,.git,.idea,.vscode,__pycache__"
    ;;
  *)
    echo "Unknown profile: $PROFILE (expected prod|full)" >&2
    exit 1
    ;;
esac

echo "Applied index profile: $PROFILE"
