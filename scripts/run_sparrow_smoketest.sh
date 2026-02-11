#!/usr/bin/env bash
set -euo pipefail

INPUT_JSON="${1:-poc/sparrow_io/swim.json}"
SEED="${SEED:-0}"
TIME_LIMIT="${TIME_LIMIT:-60}"

# SPARROW_BIN: legyen elérhető a PATH-ban, vagy add meg full path-ként
SPARROW_BIN="${SPARROW_BIN:-sparrow}"

# Overlap check kezelése:
# - OVERLAP_CHECK=1  -> kötelező overlap-check
# - OVERLAP_CHECK=0  -> tiltva
# - OVERLAP_CHECK unset/auto -> ha van shapely, fut; ha nincs és CI=true, FAIL; ha nincs és nem CI, skip + warning
OVERLAP_CHECK="${OVERLAP_CHECK:-auto}"
OVERLAP_AREA_EPS="${OVERLAP_AREA_EPS:-1e-6}"

latest_run_dir() {
  local run_root="runs"
  local latest=""
  local latest_mtime=0

  [[ -d "$run_root" ]] || return 0

  shopt -s nullglob
  for d in "$run_root"/*; do
    [[ -d "$d" ]] || continue
    local mtime
    mtime="$(stat -c %Y "$d")"
    if [[ "$mtime" -gt "$latest_mtime" ]]; then
      latest_mtime="$mtime"
      latest="$d"
    fi
  done
  shopt -u nullglob

  [[ -n "$latest" ]] && printf '%s\n' "$latest"
}

RUN_DIR=""
PRE_LAST_RUN="$(latest_run_dir || true)"

RUNNER_ARGS=(
  --input "$INPUT_JSON"
  --seed "$SEED"
  --time-limit "$TIME_LIMIT"
  --run-root runs
  --sparrow-bin "$SPARROW_BIN"
)

echo "[1/2] Sparrow run via runner module"
if ! RUN_DIR="$(python3 -m vrs_nesting.runner.sparrow_runner "${RUNNER_ARGS[@]}")"; then
  POST_LAST_RUN="$(latest_run_dir || true)"
  if [[ -n "$POST_LAST_RUN" && "$POST_LAST_RUN" != "$PRE_LAST_RUN" ]]; then
    echo "ERROR: runner futás sikertelen. Debug run_dir: $POST_LAST_RUN" >&2
  else
    echo "ERROR: runner futás sikertelen, run_dir nem azonosítható." >&2
  fi
  exit 2
fi

echo "[INFO] run_dir: $RUN_DIR"

RUNNER_META="$RUN_DIR/runner_meta.json"
if [[ ! -f "$RUNNER_META" ]]; then
  echo "ERROR: hiányzó runner meta: $RUNNER_META" >&2
  echo "[DEBUG] run_dir: $RUN_DIR" >&2
  exit 2
fi

readarray -t META_FIELDS < <(python3 - "$RUNNER_META" <<'PY'
import json
import sys

meta_path = sys.argv[1]
with open(meta_path, "r", encoding="utf-8") as f:
    meta = json.load(f)

input_snapshot = meta.get("input_snapshot_path", "")
final_json = meta.get("final_json_path", "")

if not input_snapshot or not final_json:
    raise SystemExit(2)

print(input_snapshot)
print(final_json)
PY
)

if [[ "${#META_FIELDS[@]}" -ne 2 ]]; then
  echo "ERROR: runner_meta parse hiba: $RUNNER_META" >&2
  echo "[DEBUG] run_dir: $RUN_DIR" >&2
  exit 2
fi

INPUT_SNAPSHOT="${META_FIELDS[0]}"
OUT_JSON="${META_FIELDS[1]}"

VALIDATE_ARGS=(--input "$INPUT_SNAPSHOT" --output "$OUT_JSON")

if [[ "$OVERLAP_CHECK" == "1" ]]; then
  VALIDATE_ARGS+=(--overlap-check --overlap-area-eps "$OVERLAP_AREA_EPS")
elif [[ "$OVERLAP_CHECK" == "0" ]]; then
  : # no overlap-check
else
  # auto
  if python3 - <<'PY' >/dev/null 2>&1
import shapely  # noqa: F401
PY
  then
    VALIDATE_ARGS+=(--overlap-check --overlap-area-eps "$OVERLAP_AREA_EPS")
  else
    if [[ "${CI:-}" == "true" || "${CI:-}" == "1" ]]; then
      echo "ERROR: overlap-check-hez kell a shapely (CI-ben kötelező)." >&2
      echo "Tipp (Ubuntu): sudo apt-get install -y python3-shapely" >&2
      echo "Tipp (pip): pip install shapely" >&2
      echo "[DEBUG] run_dir: $RUN_DIR" >&2
      exit 2
    fi
    echo "[WARN] shapely nincs telepítve -> overlap-check kihagyva (OVERLAP_CHECK=1-el kikényszeríthető)." >&2
  fi
fi

echo "[2/2] Validate: $OUT_JSON"
if ! ./scripts/validate_sparrow_io.py "${VALIDATE_ARGS[@]}"; then
  echo "[DEBUG] run_dir: $RUN_DIR" >&2
  exit 2
fi
