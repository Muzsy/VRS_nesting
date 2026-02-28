#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT_DIR"

INPUT_JSON="${INPUT_JSON:-poc/sparrow_io/swim.json}"
SEED="${SEED:-}"
TIME_LIMIT="${TIME_LIMIT:-}"

# SPARROW_BIN: explicit env esetén kötelezően azt használjuk, különben runtime configból indulunk.
SPARROW_BIN="${SPARROW_BIN:-}"
SPARROW_BIN_EXPLICIT=0
if [[ -n "${SPARROW_BIN}" ]]; then
  SPARROW_BIN_EXPLICIT=1
fi

need_cmd() {
  local c="$1"
  if ! command -v "$c" >/dev/null 2>&1; then
    echo "ERROR: Hiányzó parancs: $c" >&2
    exit 2
  fi
}

resolve_bin_from_value() {
  local value="$1"
  local resolved=""
  if resolved="$(command -v "$value" 2>/dev/null)"; then
    if [[ -x "$resolved" ]]; then
      echo "$resolved"
      return 0
    fi
  fi
  if [[ -x "$value" ]]; then
    echo "$value"
    return 0
  fi
  return 1
}

need_cmd python3

if [[ -z "$SEED" || -z "$TIME_LIMIT" || -z "$SPARROW_BIN" ]]; then
  readarray -t RUNTIME_DEFAULTS < <(python3 - <<'PY'
from vrs_nesting.config.runtime import runtime_defaults_from_env, resolve_sparrow_bin_name

defaults = runtime_defaults_from_env()
print(defaults.seed)
print(defaults.time_limit_s)
print(resolve_sparrow_bin_name())
PY
  )
  if [[ "${#RUNTIME_DEFAULTS[@]}" -ne 3 ]]; then
    echo "ERROR: Failed to resolve runtime defaults from vrs_nesting.config.runtime" >&2
    exit 2
  fi
  if [[ -z "$SEED" ]]; then
    SEED="${RUNTIME_DEFAULTS[0]}"
  fi
  if [[ -z "$TIME_LIMIT" ]]; then
    TIME_LIMIT="${RUNTIME_DEFAULTS[1]}"
  fi
  if [[ -z "$SPARROW_BIN" ]]; then
    SPARROW_BIN="${RUNTIME_DEFAULTS[2]}"
  fi
fi

echo "[PYTEST] Unit tests"
if ! python3 -m pytest -q; then
  echo "ERROR: pytest unit tests failed or pytest is not installed." >&2
  echo "Install tip: python3 -m pip install --break-system-packages -r requirements-dev.txt" >&2
  exit 2
fi

echo "[MYPY] Type check"
if ! python3 -m mypy --config-file mypy.ini vrs_nesting; then
  echo "ERROR: mypy type check failed or mypy is not installed." >&2
  echo "Install tip: python3 -m pip install --break-system-packages -r requirements-dev.txt" >&2
  exit 2
fi

chmod +x \
  scripts/ensure_sparrow.sh \
  scripts/run_sparrow_smoketest.sh \
  scripts/validate_sparrow_io.py \
  scripts/smoke_export_run_dir_out.py \
  scripts/smoke_export_original_geometry_block_insert.py \
  scripts/smoke_docs_commands.py \
  scripts/smoke_multisheet_wrapper_edge_cases.py \
  scripts/smoke_real_dxf_fixtures.py \
  scripts/smoke_real_dxf_nfp_pairs.py \
  scripts/run_real_dxf_sparrow_pipeline.py \
  scripts/smoke_real_dxf_sparrow_pipeline.py \
  scripts/smoke_nesting_engine_determinism.sh \
  scripts/smoke_svg_export.py || true

# --- Sparrow binary resolve/build ---
if [[ -n "$SPARROW_BIN" ]]; then
  if resolved_bin="$(resolve_bin_from_value "$SPARROW_BIN")"; then
    SPARROW_BIN="$resolved_bin"
  elif [[ "$SPARROW_BIN_EXPLICIT" == "1" ]]; then
    echo "ERROR: SPARROW_BIN nem futtatható: $SPARROW_BIN" >&2
    echo "Tipp: add meg full path-ként: SPARROW_BIN=/path/to/sparrow ./scripts/check.sh" >&2
    exit 2
  else
    SPARROW_BIN=""
  fi
fi

if [[ -z "$SPARROW_BIN" ]]; then
  echo "[SPARROW] Resolve/build via scripts/ensure_sparrow.sh"
  SPARROW_BIN="$(./scripts/ensure_sparrow.sh)"
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

echo "[DOCS] Command references smoke"
python3 scripts/smoke_docs_commands.py

echo "[DXF] Export --run-dir smoke"
python3 scripts/smoke_export_run_dir_out.py

echo "[DXF] Source geometry BLOCK/INSERT export smoke"
python3 scripts/smoke_export_original_geometry_block_insert.py

echo "[DXF] Multi-sheet wrapper edge-cases smoke"
python3 scripts/smoke_multisheet_wrapper_edge_cases.py

echo "[DXF] Real fixture import smoke"
python3 scripts/smoke_real_dxf_fixtures.py

echo "[DXF] Real NFP pairs smoke"
python3 scripts/smoke_real_dxf_nfp_pairs.py

echo "[DXF] Real Sparrow pipeline smoke"
python3 scripts/smoke_real_dxf_sparrow_pipeline.py

echo "[DXF] SVG export artifact smoke"
if python3 - <<'PY' >/dev/null 2>&1
from ezdxf import bbox as _bbox  # noqa: F401
from ezdxf.addons.drawing import Frontend, RenderContext, layout  # noqa: F401
from ezdxf.addons.drawing.svg import SVGBackend  # noqa: F401
PY
then
  python3 scripts/smoke_svg_export.py
else
  echo "[SKIP] SVG export smoke skipped: ezdxf drawing svg backend is not available"
fi

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

if [[ -f "rust/nesting_engine/Cargo.toml" ]]; then
  echo "[BUILD] nesting_engine (release)"
  cargo build --release --manifest-path rust/nesting_engine/Cargo.toml

  echo "[NEST] Baseline nesting_engine smoke"
  NESTING_ENGINE_BIN_PATH="$ROOT_DIR/rust/nesting_engine/target/release/nesting_engine"
  if [[ ! -x "$NESTING_ENGINE_BIN_PATH" ]]; then
    echo "ERROR: nesting_engine binary missing or not executable: $NESTING_ENGINE_BIN_PATH" >&2
    exit 2
  fi

  TMP_BASELINE_OUT="$(mktemp /tmp/nesting_engine_baseline_out_XXXXXX.json)"
  TMP_BASELINE_OUT_2="$(mktemp /tmp/nesting_engine_baseline_out2_XXXXXX.json)"
  TMP_NFP_FALLBACK_OUT="$(mktemp /tmp/nesting_engine_nfp_fallback_out_XXXXXX.json)"
  TMP_NOHOLES_NFP_OUT_A="$(mktemp /tmp/nesting_engine_noholes_nfp_out_a_XXXXXX.json)"
  TMP_NOHOLES_NFP_OUT_B="$(mktemp /tmp/nesting_engine_noholes_nfp_out_b_XXXXXX.json)"

  "$NESTING_ENGINE_BIN_PATH" nest < "poc/nesting_engine/sample_input_v2.json" > "$TMP_BASELINE_OUT"
  python3 -m json.tool "$TMP_BASELINE_OUT" > /dev/null

  python3 - "$TMP_BASELINE_OUT" <<'PY'
import json
import sys
from pathlib import Path

out = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
h = str(out.get("meta", {}).get("determinism_hash", ""))
if not h.startswith("sha256:") or h == "sha256:placeholder":
    raise SystemExit(f"bad determinism_hash: {h}")
print(f"[NEST] hash OK: {h[:30]}...")
PY
  BASELINE_HASH="$(python3 - "$TMP_BASELINE_OUT" <<'PY'
import json
import sys
from pathlib import Path

out = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(str(out.get("meta", {}).get("determinism_hash", "")).strip())
PY
)"
  if [[ -z "$BASELINE_HASH" ]]; then
    echo "ERROR: missing baseline determinism hash in nesting_engine smoke output" >&2
    exit 2
  fi

  "$NESTING_ENGINE_BIN_PATH" nest < "poc/nesting_engine/sample_input_v2.json" > "$TMP_BASELINE_OUT_2"
  python3 - "$TMP_BASELINE_OUT" "$TMP_BASELINE_OUT_2" <<'PY'
import json
import sys
from pathlib import Path

a = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
b = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
ha = a.get("meta", {}).get("determinism_hash")
hb = b.get("meta", {}).get("determinism_hash")
if ha != hb:
    raise SystemExit(f"determinism hash mismatch: {ha} != {hb}")
print("[NEST] determinism OK")
PY

  echo "[NEST] placer=nfp fallback smoke (holes/hole_collapsed -> blf)"
  "$NESTING_ENGINE_BIN_PATH" nest --placer nfp < "poc/nesting_engine/sample_input_v2.json" > "$TMP_NFP_FALLBACK_OUT"
  python3 -m json.tool "$TMP_NFP_FALLBACK_OUT" > /dev/null
  NFP_FALLBACK_HASH="$(python3 - "$TMP_NFP_FALLBACK_OUT" <<'PY'
import json
import sys
from pathlib import Path

out = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(str(out.get("meta", {}).get("determinism_hash", "")).strip())
PY
)"
  if [[ -z "$NFP_FALLBACK_HASH" ]]; then
    echo "ERROR: missing determinism hash in --placer nfp fallback output" >&2
    exit 2
  fi
  if [[ "$NFP_FALLBACK_HASH" != "$BASELINE_HASH" ]]; then
    echo "ERROR: --placer nfp fallback hash mismatch vs baseline BLF" >&2
    echo " baseline=$BASELINE_HASH" >&2
    echo " nfp_fallback=$NFP_FALLBACK_HASH" >&2
    exit 2
  fi
  echo "[NEST] placer=nfp fallback hash OK"

  echo "[NEST] placer=nfp noholes determinism smoke"
  "$NESTING_ENGINE_BIN_PATH" nest --placer nfp < "poc/nesting_engine/f2_3_noholes_input_v2.json" > "$TMP_NOHOLES_NFP_OUT_A"
  "$NESTING_ENGINE_BIN_PATH" nest --placer=nfp < "poc/nesting_engine/f2_3_noholes_input_v2.json" > "$TMP_NOHOLES_NFP_OUT_B"
  python3 -m json.tool "$TMP_NOHOLES_NFP_OUT_A" > /dev/null
  python3 -m json.tool "$TMP_NOHOLES_NFP_OUT_B" > /dev/null
  python3 - "$TMP_NOHOLES_NFP_OUT_A" "$TMP_NOHOLES_NFP_OUT_B" <<'PY'
import json
import sys
from pathlib import Path

a = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
b = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
ha = a.get("meta", {}).get("determinism_hash")
hb = b.get("meta", {}).get("determinism_hash")
if not ha or not hb:
    raise SystemExit("missing determinism_hash in noholes nfp smoke output")
if ha != hb:
    raise SystemExit(f"noholes nfp determinism mismatch: {ha} != {hb}")
print("[NEST] placer=nfp noholes determinism OK")
PY

  python3 - "poc/nesting_engine/sample_input_v2.json" "$TMP_BASELINE_OUT" <<'PY'
import json
import sys
from pathlib import Path

inp = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
out = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
margin = float(inp["sheet"]["margin_mm"])
for p in out.get("placements", []):
    x = float(p["x_mm"])
    y = float(p["y_mm"])
    if x < margin - 1e-3 or y < margin - 1e-3:
        raise SystemExit(f"placement below margin: {p}")
print(f"[NEST] 0 out-of-bounds OK, placed={len(out.get('placements', []))}")
PY

  echo "[NEST] Validator FAIL smoke (expected non-zero on overlap fixture)"
  if python3 scripts/validate_nesting_solution.py \
    --input-v2 "poc/nesting_engine/sample_input_v2.json" \
    --output-v2 "poc/nesting_engine/invalid_overlap_fixture.json"; then
    echo "ERROR: validator unexpectedly accepted invalid_overlap_fixture.json" >&2
    exit 1
  fi

  echo "[NEST] Validator PASS smoke (baseline output)"
  python3 scripts/validate_nesting_solution.py \
    --input-v2 "poc/nesting_engine/sample_input_v2.json" \
    --output-v2 "$TMP_BASELINE_OUT"

  echo "[NEST] CLI smoke (nest-v2)"
  CLI_RUN_DIR="$(python3 -m vrs_nesting.cli nest-v2 \
    --input "poc/nesting_engine/sample_input_v2.json" \
    --seed "$SEED" \
    --time-limit "$TIME_LIMIT" \
    --nesting-engine-bin "$NESTING_ENGINE_BIN_PATH" \
    --run-root runs)"

  if [[ -z "$CLI_RUN_DIR" || ! -d "$CLI_RUN_DIR" ]]; then
    echo "ERROR: invalid run_dir returned by nest-v2 CLI smoke: '$CLI_RUN_DIR'" >&2
    exit 2
  fi

  CLI_HASH="$(python3 - "$CLI_RUN_DIR/runner_meta.json" <<'PY'
import json
import sys
from pathlib import Path

meta = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(str(meta.get("determinism_hash", "")).strip())
PY
)"
  if [[ -z "$CLI_HASH" ]]; then
    echo "ERROR: missing determinism_hash in nest-v2 runner meta: $CLI_RUN_DIR/runner_meta.json" >&2
    exit 2
  fi
  if [[ "$CLI_HASH" != "$BASELINE_HASH" ]]; then
    echo "ERROR: nest-v2 CLI hash mismatch vs baseline bin smoke" >&2
    echo " baseline=$BASELINE_HASH" >&2
    echo " cli=$CLI_HASH" >&2
    exit 2
  fi
  echo "[NEST] CLI determinism OK"

  echo "[NEST] Canonical JSON determinism smoke"
  NEST_DET_INPUT="$(mktemp /tmp/nesting_engine_det_input_XXXXXX.json)"
  python3 - "poc/nesting_engine/sample_input_v2.json" "$NEST_DET_INPUT" <<'PY'
import json
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
payload = json.loads(src.read_text(encoding="utf-8"))
if isinstance(payload, dict):
    payload["time_limit_sec"] = 1
dst.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
PY
  # CI-ben emelhető: NESTING_ENGINE_DETERMINISM_RUNS=50
  RUNS="${NESTING_ENGINE_DETERMINISM_RUNS:-10}" \
    INPUT_JSON="$NEST_DET_INPUT" \
    ./scripts/smoke_nesting_engine_determinism.sh
fi

echo "[DONE] smoketest OK"
