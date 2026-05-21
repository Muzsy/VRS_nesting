#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <regex-query>" >&2
  exit 2
fi

QUERY="$1"
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

RG_BIN="$(command -v rg || true)"
if [[ -z "$RG_BIN" ]] && [[ -x "/home/muszy/.npm-global/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/codex-path/rg" ]]; then
  RG_BIN="/home/muszy/.npm-global/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/codex-path/rg"
fi
if [[ -z "$RG_BIN" ]]; then
  echo "artifact_rag_v0_rg: missing dependency 'rg' (ripgrep)" >&2
  echo "suggested fix: sudo apt update && sudo apt install -y ripgrep" >&2
  exit 3
fi

# Artifact-only sources (kept separate from code graph ranking)
ARTIFACT_DIRS=(
  "/home/muszy/codex-hermes-loop/runs"
  "/home/muszy/codex-hermes-loop/artifacts"
  "$REPO_ROOT/codex-hermes-loop/evals"
  "$REPO_ROOT/codex/reports"
  "$REPO_ROOT/runs"
  "$REPO_ROOT/tmp/runs"
  "$REPO_ROOT/poc"
  "$REPO_ROOT/docs"
)

SEARCH_FILES=()
for d in "${ARTIFACT_DIRS[@]}"; do
  if [[ -d "$d" ]]; then
    while IFS= read -r f; do
      SEARCH_FILES+=("$f")
    done < <(find "$d" -type f \( -name "*.md" -o -name "*.log" -o -name "*.json" \) 2>/dev/null)
  fi
done

if [[ ${#SEARCH_FILES[@]} -eq 0 ]]; then
  echo "artifact_rag_v0_rg: no artifact files found in configured dirs" >&2
  exit 1
fi

echo "artifact_rag_v0_rg query: $QUERY"
echo "artifact_rag_v0_rg dirs:"
for d in "${ARTIFACT_DIRS[@]}"; do
  [[ -d "$d" ]] && echo "  - $d"
done

echo
"$RG_BIN" -n -i --max-count 200 -e "$QUERY" "${SEARCH_FILES[@]}" || true
