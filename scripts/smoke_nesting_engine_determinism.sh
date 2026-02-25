#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT_DIR"

INPUT_JSON="${INPUT_JSON:-$ROOT_DIR/poc/nesting_engine/sample_input_v2.json}"
RUNS="${RUNS:-50}"
CANONICALIZER="${CANONICALIZER:-$ROOT_DIR/scripts/canonicalize_json.py}"
BIN_PATH="${BIN_PATH:-$ROOT_DIR/rust/nesting_engine/target/release/nesting_engine}"

export LC_ALL=C
export RAYON_NUM_THREADS=1
export RUST_BACKTRACE=1

need_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: missing command: $cmd" >&2
    exit 2
  fi
}

need_cmd cargo
need_cmd python3
need_cmd cmp

if [[ ! -f "$INPUT_JSON" ]]; then
  echo "ERROR: input JSON not found: $INPUT_JSON" >&2
  exit 2
fi

if [[ ! -f "$CANONICALIZER" ]]; then
  echo "ERROR: canonicalizer script not found: $CANONICALIZER" >&2
  exit 2
fi

echo "[BUILD] nesting_engine release"
cargo build --release --manifest-path rust/nesting_engine/Cargo.toml

if [[ ! -x "$BIN_PATH" ]]; then
  echo "ERROR: nesting_engine binary missing or not executable: $BIN_PATH" >&2
  exit 2
fi

TMP_DIR="$(mktemp -d /tmp/nesting_engine_determinism_XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

BASELINE="$TMP_DIR/run_01.canonical.json"
echo "[RUN] deterministic smoke ($RUNS runs)"

for i in $(seq 1 "$RUNS"); do
  OUT_FILE="$TMP_DIR/run_$(printf '%02d' "$i").canonical.json"
  cat "$INPUT_JSON" | "$BIN_PATH" nest | python3 "$CANONICALIZER" > "$OUT_FILE"

  if [[ "$i" -eq 1 ]]; then
    continue
  fi

  if ! cmp -s "$BASELINE" "$OUT_FILE"; then
    cp "$BASELINE" /tmp/out_a.json
    cp "$OUT_FILE" /tmp/out_b.json
    echo "ERROR: determinism mismatch between run 1 and run $i" >&2
    echo "  canonical_a: /tmp/out_a.json" >&2
    echo "  canonical_b: /tmp/out_b.json" >&2
    exit 1
  fi
done

echo "[OK] determinism smoke passed ($RUNS/$RUNS canonical outputs are byte-identical)"
