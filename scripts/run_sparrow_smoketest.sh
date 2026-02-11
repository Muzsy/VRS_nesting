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

# Sparrow output tipikusan ./output/final_<stem>.json
STEM="$(basename "$INPUT_JSON" .json)"
OUT_JSON_GUESS="output/final_${STEM}.json"
RUN_START_EPOCH="$(date +%s)"
PRE_GUESS_MTIME=""
if [[ -f "$OUT_JSON_GUESS" ]]; then
  PRE_GUESS_MTIME="$(stat -c %Y "$OUT_JSON_GUESS")"
fi

echo "[1/2] Sparrow run: $SPARROW_BIN -i $INPUT_JSON -t $TIME_LIMIT -s $SEED"
"$SPARROW_BIN" -i "$INPUT_JSON" -t "$TIME_LIMIT" -s "$SEED"

# Friss outputot várunk a mostani futásból, hogy ne validáljunk régi fájlt.
OUT_JSON=""
if [[ -f "$OUT_JSON_GUESS" ]]; then
  POST_GUESS_MTIME="$(stat -c %Y "$OUT_JSON_GUESS")"
  if [[ -z "$PRE_GUESS_MTIME" || "$POST_GUESS_MTIME" -gt "$PRE_GUESS_MTIME" || "$POST_GUESS_MTIME" -ge "$RUN_START_EPOCH" ]]; then
    OUT_JSON="$OUT_JSON_GUESS"
  fi
fi

if [[ -z "$OUT_JSON" ]]; then
  shopt -s nullglob
  BEST_MTIME=0
  for CANDIDATE in output/final_*.json; do
    MTIME="$(stat -c %Y "$CANDIDATE")"
    if [[ "$MTIME" -ge "$RUN_START_EPOCH" && "$MTIME" -gt "$BEST_MTIME" ]]; then
      OUT_JSON="$CANDIDATE"
      BEST_MTIME="$MTIME"
    fi
  done
  shopt -u nullglob
fi

if [[ -z "$OUT_JSON" ]]; then
  echo "ERROR: Nem található friss output/final_*.json a mostani Sparrow futásból." >&2
  exit 2
fi

VALIDATE_ARGS=(--input "$INPUT_JSON" --output "$OUT_JSON")

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
      exit 2
    fi
    echo "[WARN] shapely nincs telepítve → overlap-check kihagyva (OVERLAP_CHECK=1-el kikényszeríthető)." >&2
  fi
fi

echo "[2/2] Validate: $OUT_JSON"
./scripts/validate_sparrow_io.py "${VALIDATE_ARGS[@]}"
