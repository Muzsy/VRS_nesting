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

chmod +x \
  scripts/run_sparrow_smoketest.sh \
  scripts/validate_sparrow_io.py \
  scripts/smoke_export_run_dir_out.py \
  scripts/run_real_dxf_sparrow_pipeline.py \
  scripts/smoke_real_dxf_sparrow_pipeline.py || true

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

echo "[DXF] Import convention smoke"
python3 scripts/smoke_dxf_import_convention.py

echo "[GEO] Polygonize + offset robustness smoke"
python3 scripts/smoke_geometry_pipeline.py

echo "[DXF] Export --run-dir smoke"
python3 scripts/smoke_export_run_dir_out.py

echo "[DXF] Real Sparrow pipeline smoke"
python3 scripts/smoke_real_dxf_sparrow_pipeline.py

if [[ -f "rust/vrs_solver/Cargo.toml" ]]; then
  echo "[4/5] Nesting solution validator smoke"
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
    {"id": "PART_A", "width": 70, "height": 60, "quantity": 2, "allowed_rotations_deg": [0]},
    {"id": "PART_B", "width": 120, "height": 20, "quantity": 1, "allowed_rotations_deg": [0]}
  ]
}
JSON

  VRS_RUN_DIR="$(python3 -m vrs_nesting.runner.vrs_solver_runner \
    --input "$TMP_NEST_INPUT" \
    --solver-bin "$VRS_SOLVER_BIN_PATH" \
    --seed "$SEED" \
    --time-limit "$TIME_LIMIT" \
    --run-root runs)"

  echo "[INFO] vrs_run_dir: $VRS_RUN_DIR"
  python3 scripts/validate_nesting_solution.py --run-dir "$VRS_RUN_DIR"

  echo "[5/5] Determinism hash stability smoke"
  VRS_RUN_DIR_A="$(python3 -m vrs_nesting.runner.vrs_solver_runner \
    --input "$TMP_NEST_INPUT" \
    --solver-bin "$VRS_SOLVER_BIN_PATH" \
    --seed "$SEED" \
    --time-limit "$TIME_LIMIT" \
    --run-root runs)"
  VRS_RUN_DIR_B="$(python3 -m vrs_nesting.runner.vrs_solver_runner \
    --input "$TMP_NEST_INPUT" \
    --solver-bin "$VRS_SOLVER_BIN_PATH" \
    --seed "$SEED" \
    --time-limit "$TIME_LIMIT" \
    --run-root runs)"

  HASH_A="$(python3 - "$VRS_RUN_DIR_A/runner_meta.json" <<'PY'
import json
import sys
from pathlib import Path

meta = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(str(meta.get("output_sha256", "")).strip())
PY
)"
  HASH_B="$(python3 - "$VRS_RUN_DIR_B/runner_meta.json" <<'PY'
import json
import sys
from pathlib import Path

meta = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(str(meta.get("output_sha256", "")).strip())
PY
)"

  if [[ -z "$HASH_A" || -z "$HASH_B" ]]; then
    echo "ERROR: Missing output_sha256 in determinism smoke meta" >&2
    echo " run_a=$VRS_RUN_DIR_A" >&2
    echo " run_b=$VRS_RUN_DIR_B" >&2
    exit 2
  fi
  if [[ "$HASH_A" != "$HASH_B" ]]; then
    echo "ERROR: Determinism hash mismatch" >&2
    echo " run_a=$VRS_RUN_DIR_A hash=$HASH_A" >&2
    echo " run_b=$VRS_RUN_DIR_B hash=$HASH_B" >&2
    exit 2
  fi
  echo "[INFO] Determinism hash stable: $HASH_A"

  echo "[6/6] Timeout/perf guard smoke"
  python3 scripts/smoke_time_budget_guard.py --require-real-solver
fi

echo "[DONE] smoketest OK"
