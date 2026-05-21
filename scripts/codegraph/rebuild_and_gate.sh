#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PROFILE="${1:-prod}"
SKIP_INDEX="${SKIP_INDEX:-false}"

if [[ "$PROFILE" != "prod" && "$PROFILE" != "full" ]]; then
  echo "Usage: $0 [prod|full]" >&2
  echo "Optional env: SKIP_INDEX=true" >&2
  exit 2
fi

cd "$REPO_ROOT"

echo "[1/5] Normalize CodeGraphContext config"
scripts/codegraph/fix_cgc_config.sh

echo "[2/5] Apply index profile: $PROFILE"
scripts/codegraph/set_index_profile.sh "$PROFILE"

if [[ "$SKIP_INDEX" == "true" ]]; then
  echo "[3/5] Skip index rebuild (SKIP_INDEX=true)"
else
  echo "[3/5] Rebuild CodeGraph index (neo4j)"
  ~/.local/bin/cgc --database neo4j index . --force
fi

echo "[4/5] Run health check"
scripts/codegraph/health_check.sh

echo "[5/5] Run RAG smoke eval"
scripts/codegraph/eval_rag_smoke.sh

LATEST_HEALTH="$(ls -1t /home/muszy/codex-hermes-loop/evals/*health_check.log 2>/dev/null | head -n 1 || true)"
LATEST_EVAL="$(ls -1t /home/muszy/codex-hermes-loop/evals/*rag_smoke.log 2>/dev/null | head -n 1 || true)"

echo
echo "Done. Latest logs:"
[[ -n "$LATEST_HEALTH" ]] && echo "- health: $LATEST_HEALTH"
[[ -n "$LATEST_EVAL" ]] && echo "- eval:   $LATEST_EVAL"
