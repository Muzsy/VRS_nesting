#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT_DIR"

INPUT_JSON="${INPUT_JSON:-$ROOT_DIR/poc/nesting_engine/float_policy_near_touching_fixture_v2.json}"
RUNS="${RUNS:-10}"

echo "[NEST][FLOAT] Determinism smoke on float-boundary fixture"
RUNS="$RUNS" INPUT_JSON="$INPUT_JSON" ./scripts/smoke_nesting_engine_determinism.sh
