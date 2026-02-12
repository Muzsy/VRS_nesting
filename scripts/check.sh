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
      (
        cd "$CACHE_DIR"
        if git rev-parse --verify "${COMMIT}^{commit}" >/dev/null 2>&1; then
          git checkout "$COMMIT"
        else
          echo "[1/3] Pinned commit nincs lokálisan, fetch szükséges."
          if git fetch --all --tags --prune; then
            git checkout "$COMMIT"
          else
            echo "ERROR: Nem sikerült fetch-elni és a pinned commit nem elérhető lokálisan: $COMMIT" >&2
            exit 2
          fi
        fi
      )
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

if [[ -f "rust/vrs_solver/Cargo.toml" ]]; then
  echo "[4/4] Nesting solution validator smoke"
  cargo build --release --manifest-path rust/vrs_solver/Cargo.toml
  VRS_SOLVER_BIN_PATH="$ROOT_DIR/rust/vrs_solver/target/release/vrs_solver"

  if [[ ! -x "$VRS_SOLVER_BIN_PATH" ]]; then
    echo "ERROR: VRS solver binary missing or not executable: $VRS_SOLVER_BIN_PATH" >&2
    exit 2
  fi

  TMP_NEST_INPUT="$(mktemp /tmp/vrs_nest_input_XXXXXX.json)"
  cat > "$TMP_NEST_INPUT" <<'JSON'
{
  "contract_version": "v1",
  "project_name": "check_gate_smoke",
  "seed": 0,
  "time_limit_s": 60,
  "stocks": [
    {
      "id": "SHEET_A",
      "quantity": 2,
      "outer_points": [[0, 0], [100, 0], [100, 100], [0, 100]],
      "holes_points": [
        [[70, 70], [80, 70], [80, 80], [70, 80]]
      ]
    }
  ],
  "parts": [
    {"id": "PART_A", "width": 70, "height": 60, "quantity": 2, "allow_rotation": false},
    {"id": "PART_B", "width": 120, "height": 20, "quantity": 1, "allow_rotation": false}
  ]
}
JSON

  VRS_RUN_DIR="$(python3 -m vrs_nesting.runner.vrs_solver_runner \
    --input "$TMP_NEST_INPUT" \
    --solver-bin "$VRS_SOLVER_BIN_PATH" \
    --run-root runs)"

  echo "[INFO] vrs_run_dir: $VRS_RUN_DIR"
  python3 scripts/validate_nesting_solution.py --run-dir "$VRS_RUN_DIR"
fi

echo "[DONE] smoketest OK"
