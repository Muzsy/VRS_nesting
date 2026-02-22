#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT_DIR"

EXPECTED_OUTPUT_SHA256="e1741617758b37a03c219fd0e99ad927506c6a7eaf02be7ff329f73e02a31862"
SEED="${SEED:-7}"
TIME_LIMIT="${TIME_LIMIT:-30}"
RUN_ROOT="${RUN_ROOT:-runs}"
NESTING_ENGINE_BIN="${NESTING_ENGINE_BIN:-$ROOT_DIR/rust/nesting_engine/target/release/nesting_engine}"

TMP_INPUT="$(mktemp /tmp/nesting_engine_rotation_determinism_input_XXXXXX.json)"
trap 'rm -f "$TMP_INPUT"' EXIT

cat > "$TMP_INPUT" <<'JSON'
{
  "version": "nesting_engine_v2",
  "seed": 7,
  "time_limit_sec": 30,
  "sheet": {
    "width_mm": 220.0,
    "height_mm": 220.0,
    "kerf_mm": 0.2,
    "margin_mm": 2.0
  },
  "parts": [
    {
      "id": "rot17_rect",
      "quantity": 3,
      "allowed_rotations_deg": [17],
      "outer_points_mm": [[0.0, 0.0], [50.0, 0.0], [50.0, 24.0], [0.0, 24.0]],
      "holes_points_mm": []
    },
    {
      "id": "rot17_lshape",
      "quantity": 2,
      "allowed_rotations_deg": [17],
      "outer_points_mm": [[0.0, 0.0], [40.0, 0.0], [40.0, 12.0], [18.0, 12.0], [18.0, 36.0], [0.0, 36.0]],
      "holes_points_mm": []
    }
  ]
}
JSON

echo "[BUILD] nesting_engine release"
cargo build --release --manifest-path rust/nesting_engine/Cargo.toml

if [[ ! -x "$NESTING_ENGINE_BIN" ]]; then
  echo "ERROR: nesting_engine binary missing or not executable: $NESTING_ENGINE_BIN" >&2
  exit 2
fi

echo "[RUN] platform determinism rotation smoke"
RUN_DIR="$(python3 -m vrs_nesting.runner.nesting_engine_runner \
  --input "$TMP_INPUT" \
  --seed "$SEED" \
  --time-limit "$TIME_LIMIT" \
  --nesting-engine-bin "$NESTING_ENGINE_BIN" \
  --run-root "$RUN_ROOT")"

if [[ -z "$RUN_DIR" || ! -d "$RUN_DIR" ]]; then
  echo "ERROR: invalid run_dir from nesting_engine_runner: '$RUN_DIR'" >&2
  exit 2
fi

RUNNER_META="$RUN_DIR/runner_meta.json"
if [[ ! -f "$RUNNER_META" ]]; then
  echo "ERROR: missing runner_meta.json: $RUNNER_META" >&2
  exit 2
fi

RAW_OUTPUT_SHA256="$(python3 - "$RUNNER_META" <<'PY'
import json
import sys
from pathlib import Path

meta = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
print(str(meta.get('output_sha256', '')).strip())
PY
)"

OUTPUT_PATH="$RUN_DIR/nesting_output.json"

if [[ -z "$RAW_OUTPUT_SHA256" ]]; then
  echo "ERROR: output_sha256 missing in runner_meta: $RUNNER_META" >&2
  exit 2
fi

if [[ ! -f "$OUTPUT_PATH" ]]; then
  echo "ERROR: missing nesting output JSON: $OUTPUT_PATH" >&2
  exit 2
fi

OUTPUT_SHA256="$(python3 - "$OUTPUT_PATH" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

out = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
meta = out.get('meta')
if isinstance(meta, dict):
    # elapsed_sec is expected to vary by runtime; normalize before hashing.
    meta['elapsed_sec'] = 0.0
payload = json.dumps(out, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
print(hashlib.sha256(payload).hexdigest())
PY
)"

if [[ -z "$OUTPUT_SHA256" ]]; then
  echo "ERROR: failed to compute normalized output_sha256 from $OUTPUT_PATH" >&2
  exit 2
fi

echo "[INFO] arch=$(uname -m)"
echo "[INFO] run_dir=$RUN_DIR"
echo "[INFO] runner_output_sha256=$RAW_OUTPUT_SHA256"
echo "[INFO] normalized_output_sha256=$OUTPUT_SHA256"

if [[ "${PRINT_ONLY:-0}" == "1" ]]; then
  exit 0
fi

if [[ "$EXPECTED_OUTPUT_SHA256" == "REPLACE_WITH_GENERATED_SHA256" ]]; then
  echo "ERROR: EXPECTED_OUTPUT_SHA256 is not pinned yet." >&2
  echo "Observed output_sha256: $OUTPUT_SHA256" >&2
  echo "Re-run with PRINT_ONLY=1, then update EXPECTED_OUTPUT_SHA256 in this script." >&2
  exit 2
fi

if [[ "$OUTPUT_SHA256" != "$EXPECTED_OUTPUT_SHA256" ]]; then
  echo "ERROR: platform determinism hash mismatch" >&2
  echo " expected=$EXPECTED_OUTPUT_SHA256" >&2
  echo " actual=$OUTPUT_SHA256" >&2
  echo " run_dir=$RUN_DIR" >&2
  exit 1
fi

echo "[OK] platform determinism rotation smoke passed"
