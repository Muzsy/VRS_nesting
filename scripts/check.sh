#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT_DIR"

INPUT_JSON="${INPUT_JSON:-poc/sparrow_io/swim.json}"
SEED="${SEED:-0}"
TIME_LIMIT="${TIME_LIMIT:-60}"

# SPARROW_BIN: ha a felhasználó megadja, használjuk. Egyébként buildeljük cache-be.
SPARROW_BIN="${SPARROW_BIN:-}"

need_cmd() {
  local c="$1"
  if ! command -v "$c" >/dev/null 2>&1; then
    echo "ERROR: Hiányzó parancs: $c" >&2
    exit 2
  fi
}

need_cmd python3
need_cmd git

if [[ -z "$SPARROW_BIN" ]]; then
  need_cmd cargo
fi

chmod +x scripts/run_sparrow_smoketest.sh scripts/validate_sparrow_io.py || true

# --- Sparrow build (ha nincs előre megadott bináris) ---
if [[ -z "$SPARROW_BIN" ]]; then
  CACHE_DIR=".cache/sparrow"
  mkdir -p .cache

  if [[ ! -d "$CACHE_DIR/.git" ]]; then
    rm -rf "$CACHE_DIR"
    echo "[1/3] Prepare Sparrow source (clone)"
    git clone https://github.com/JeroenGar/sparrow.git "$CACHE_DIR"
  fi

  # Optional pin
  if [[ -f "poc/sparrow_io/sparrow_commit.txt" ]]; then
    COMMIT="$(tr -d '\n\r' < poc/sparrow_io/sparrow_commit.txt)"
    if [[ -n "$COMMIT" ]]; then
      echo "[1/3] Sparrow pin: $COMMIT"
      ( cd "$CACHE_DIR" && git fetch --all --tags --prune && git checkout "$COMMIT" )
    fi
  fi

  echo "[2/3] Build Sparrow (release)"
  ( cd "$CACHE_DIR" && cargo build --release )
  SPARROW_BIN="$ROOT_DIR/.cache/sparrow/target/release/sparrow"
fi

if [[ ! -x "$SPARROW_BIN" ]]; then
  echo "ERROR: SPARROW_BIN nem futtatható: $SPARROW_BIN" >&2
  echo "Tipp: add meg full path-ként: SPARROW_BIN=/path/to/sparrow ./scripts/check.sh" >&2
  exit 2
fi

export SPARROW_BIN
export SEED
export TIME_LIMIT

# --- Run smoketest (Sparrow + validator) ---
echo "[3/3] Sparrow IO smoketest"
./scripts/run_sparrow_smoketest.sh "$INPUT_JSON"

echo "[DONE] smoketest OK"
