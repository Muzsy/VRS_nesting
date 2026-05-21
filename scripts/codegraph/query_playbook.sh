#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

echo "[Q1] call chain around can_place"
~/.local/bin/cgc analyze callers can_place --file "$REPO_ROOT/rust/nesting_engine/src/feasibility/narrow.rs"
~/.local/bin/cgc analyze chain can_place_dispatch can_place \
  --from-file "$REPO_ROOT/rust/nesting_engine/src/placement/nfp_placer.rs" \
  --to-file "$REPO_ROOT/rust/nesting_engine/src/feasibility/narrow.rs" --depth 6

echo "[Q2] cavity_prepack expansion back into final placements"
~/.local/bin/cgc find content "cavity_prepack"
~/.local/bin/cgc find content "cavity_prepack_summary"

echo "[Q3] files defining NFP placement strategy"
~/.local/bin/cgc find pattern nfp_placer
~/.local/bin/cgc find content "parse_placer_value"
~/.local/bin/cgc find content "generate_hybrid_candidates"

echo "[Q4] BLF fallback code paths"
~/.local/bin/cgc find content "BLF fallback"
~/.local/bin/cgc find content "fallback"
~/.local/bin/cgc analyze callers blf_place --file "$REPO_ROOT/rust/nesting_engine/src/placement/blf.rs"
