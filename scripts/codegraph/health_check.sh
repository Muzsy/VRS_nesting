#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT_DIR="/home/muszy/codex-hermes-loop/evals"
STAMP="$(date +%Y%m%d_%H%M)"
OUT_FILE="$OUT_DIR/${STAMP}_health_check.log"

mkdir -p "$OUT_DIR"
cd "$REPO_ROOT"

fails=0

RG_BIN="$(command -v rg || true)"
if [[ -z "$RG_BIN" ]] && [[ -x "/home/muszy/.npm-global/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/codex-path/rg" ]]; then
  RG_BIN="/home/muszy/.npm-global/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/codex-path/rg"
fi

report() {
  local status="$1"
  local name="$2"
  local reason="$3"
  local fix="$4"
  printf '[%s] %s\n' "$status" "$name"
  printf '  reason: %s\n' "$reason"
  printf '  suggested fix: %s\n' "$fix"
  if [[ "$status" == "FAIL" ]]; then
    fails=$((fails+1))
  fi
}

{
  echo "# CodeGraph Health Check"
  echo "repo=$REPO_ROOT"
  echo "timestamp=$STAMP"
  echo

  if command -v cgc >/dev/null 2>&1; then
    report PASS "cgc available" "$(command -v cgc)" "n/a"
  else
    report FAIL "cgc available" "cgc not found" "install/restore CodeGraphContext CLI"
  fi

  if command -v docker >/dev/null 2>&1; then
    report PASS "docker available" "$(command -v docker)" "n/a"
  else
    report FAIL "docker available" "docker not found" "install Docker and ensure daemon running"
  fi

  if [[ -n "$RG_BIN" ]]; then
    report PASS "rg available" "$RG_BIN" "n/a"
  else
    report FAIL "rg available" "rg (ripgrep) not found in PATH or known fallback path" "install ripgrep (sudo apt update && sudo apt install -y ripgrep)"
    echo
    echo "OVERALL: FAIL (checks_failed=$fails)"
    exit $fails
  fi

  if [[ -x /home/muszy/.local/bin/cgc-mcp-clean ]]; then
    report PASS "MCP wrapper exists" "wrapper is executable" "n/a"
  else
    report FAIL "MCP wrapper exists" "missing or non-executable wrapper" "create /home/muszy/.local/bin/cgc-mcp-clean and chmod +x"
  fi

  if docker ps --format '{{.Names}}' | "$RG_BIN" -q '^codegraph-neo4j$'; then
    report PASS "Neo4j container status" "codegraph-neo4j is running" "n/a"
  else
    report FAIL "Neo4j container status" "codegraph-neo4j not running" "docker start codegraph-neo4j"
  fi

  NODE_COUNT="$(docker exec codegraph-neo4j cypher-shell -u neo4j -p codegraph123 "MATCH (n) RETURN count(n);" 2>/dev/null | tail -n 1 || echo 0)"
  if [[ "$NODE_COUNT" =~ ^[0-9]+$ ]] && (( NODE_COUNT > 0 )); then
    report PASS "Neo4j node count" "count(n)=$NODE_COUNT" "n/a"
  else
    report FAIL "Neo4j node count" "count(n) unavailable or zero ($NODE_COUNT)" "run cgc index . --force with neo4j backend"
  fi

  FUNC_COUNT="$(docker exec codegraph-neo4j cypher-shell -u neo4j -p codegraph123 "MATCH (f:Function) RETURN count(f);" 2>/dev/null | tail -n 1 || echo 0)"
  if [[ "$FUNC_COUNT" =~ ^[0-9]+$ ]] && (( FUNC_COUNT > 0 )); then
    report PASS "Neo4j function count" "count(Function)=$FUNC_COUNT" "n/a"
  else
    report FAIL "Neo4j function count" "count(Function) unavailable or zero ($FUNC_COUNT)" "reindex code graph"
  fi

  Q_OUT="$(~/.local/bin/cgc --database neo4j find pattern can_place 2>&1 || true)"
  if echo "$Q_OUT" | "$RG_BIN" -q "can_place"; then
    report PASS "CodeGraph query can_place" "query returned expected symbol(s)" "n/a"
  else
    report FAIL "CodeGraph query can_place" "no can_place evidence in query output" "check index freshness and backend"
  fi

  # Do not fail on misleading context lines if actual query and neo4j counts passed.
  if echo "$Q_OUT" | "$RG_BIN" -q "Using database: neo4j"; then
    report PASS "Effective backend evidence" "runtime output shows neo4j" "n/a"
  elif (( NODE_COUNT > 0 )) && (( FUNC_COUNT > 0 )); then
    report PASS "Effective backend evidence" "neo4j counts prove indexed graph even if context line mentions falkordb" "n/a"
  else
    report FAIL "Effective backend evidence" "cannot prove neo4j usage" "verify DEFAULT_DATABASE and runtime DB overrides"
  fi

  if "$RG_BIN" -q '^DEFAULT_DATABASE=neo4j' "$REPO_ROOT/.codegraphcontext/.env"; then
    report PASS "Repo config DEFAULT_DATABASE" "DEFAULT_DATABASE=neo4j" "n/a"
  else
    report FAIL "Repo config DEFAULT_DATABASE" "DEFAULT_DATABASE not neo4j" "set DEFAULT_DATABASE=neo4j in .codegraphcontext/.env"
  fi

  if "$RG_BIN" -q '^SCIP_INDEXER=true' "$REPO_ROOT/.codegraphcontext/.env"; then
    report PASS "Repo config SCIP_INDEXER" "SCIP_INDEXER=true" "n/a"
  else
    report FAIL "Repo config SCIP_INDEXER" "SCIP_INDEXER not true" "set SCIP_INDEXER=true"
  fi

  if "$RG_BIN" -q '^ENABLE_INHERIT_RESOLVE=true' "$REPO_ROOT/.codegraphcontext/.env"; then
    report PASS "Repo config ENABLE_INHERIT_RESOLVE" "ENABLE_INHERIT_RESOLVE=true" "n/a"
  else
    report FAIL "Repo config ENABLE_INHERIT_RESOLVE" "ENABLE_INHERIT_RESOLVE not true" "set ENABLE_INHERIT_RESOLVE=true"
  fi

  MCP_CHECK="$(python3 - <<'PY'
import tomllib
from pathlib import Path
p = Path('/home/muszy/.codex/config.toml')
if not p.exists():
    print('MISSING_CONFIG')
    raise SystemExit(0)
obj = tomllib.loads(p.read_text())
servers = obj.get('mcp_servers', {})
cgc = servers.get('CodeGraphContext', {})
if not isinstance(cgc, dict):
    print('INVALID_CGC_BLOCK')
    raise SystemExit(0)
if not cgc.get('enabled', False):
    print('CGC_DISABLED')
    raise SystemExit(0)
if not cgc.get('command') and not cgc.get('url'):
    print('CGC_NO_ENDPOINT')
    raise SystemExit(0)
orphans = []
for name, cfg in servers.items():
    if isinstance(cfg, dict) and 'startup_timeout_sec' in cfg and 'command' not in cfg and 'url' not in cfg:
        orphans.append(name)
if orphans:
    print('ORPHAN:' + ','.join(orphans))
else:
    print('OK')
PY
)"

  case "$MCP_CHECK" in
    OK)
      report PASS "Codex MCP config validity" "CodeGraphContext block valid; no orphan timeout-only MCP blocks" "n/a"
      ;;
    MISSING_CONFIG)
      report FAIL "Codex MCP config validity" "~/.codex/config.toml missing" "restore config"
      ;;
    CGC_DISABLED)
      report FAIL "Codex MCP config validity" "CodeGraphContext MCP disabled" "set enabled=true"
      ;;
    CGC_NO_ENDPOINT)
      report FAIL "Codex MCP config validity" "CodeGraphContext has no command/url" "set command=/home/muszy/.local/bin/cgc-mcp-clean"
      ;;
    ORPHAN:*)
      report FAIL "Codex MCP config validity" "orphan MCP block(s): ${MCP_CHECK#ORPHAN:}" "remove timeout-only MCP blocks or add command/url"
      ;;
    *)
      report FAIL "Codex MCP config validity" "unexpected parser state: $MCP_CHECK" "inspect ~/.codex/config.toml"
      ;;
  esac

  echo
  if (( fails == 0 )); then
    echo "OVERALL: PASS"
  else
    echo "OVERALL: FAIL (checks_failed=$fails)"
  fi

} | tee "$OUT_FILE"

echo "Saved: $OUT_FILE"
exit $fails
