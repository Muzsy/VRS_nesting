#!/usr/bin/env bash
set -euo pipefail

GLOBAL_ENV="${HOME}/.codegraphcontext/.env"
REPO_ENV="$(pwd)/.codegraphcontext/.env"

if [[ ! -f "$REPO_ENV" ]]; then
  echo "Missing repo env: $REPO_ENV" >&2
  exit 1
fi

# Ensure core keys are explicit and consistent in both env files.
ensure_key() {
  local key="$1"
  local value="$2"
  local file="$3"
  if rg -q "^${key}=" "$file"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$file"
  else
    printf '%s=%s\n' "$key" "$value" >> "$file"
  fi
}

ensure_key "DEFAULT_DATABASE" "neo4j" "$REPO_ENV"
ensure_key "ENABLE_INHERIT_RESOLVE" "true" "$REPO_ENV"
ensure_key "SCIP_INDEXER" "true" "$REPO_ENV"
ensure_key "NEO4J_URI" "bolt://127.0.0.1:7687" "$REPO_ENV"
ensure_key "NEO4J_USERNAME" "neo4j" "$REPO_ENV"
ensure_key "NEO4J_PASSWORD" "codegraph123" "$REPO_ENV"

if [[ -f "$GLOBAL_ENV" ]]; then
  ensure_key "DEFAULT_DATABASE" "neo4j" "$GLOBAL_ENV"
  ensure_key "ENABLE_INHERIT_RESOLVE" "true" "$GLOBAL_ENV"
  ensure_key "SCIP_INDEXER" "true" "$GLOBAL_ENV"
  ensure_key "NEO4J_URI" "bolt://127.0.0.1:7687" "$GLOBAL_ENV"
  ensure_key "NEO4J_PASSWORD" "codegraph123" "$GLOBAL_ENV"
fi

echo "CGC config normalized."
