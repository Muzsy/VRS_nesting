#!/usr/bin/env bash
set -euo pipefail

INPUT_JSON="${1:-poc/sparrow_io/swim.json}"
SEED="${SEED:-0}"
TIME_LIMIT="${TIME_LIMIT:-60}"

# SPARROW_BIN: legyen elérhető a PATH-ban, vagy add meg full path-ként
SPARROW_BIN="${SPARROW_BIN:-sparrow}"

# Sparrow output tipikusan ./output/final_<stem>.json
STEM="$(basename "$INPUT_JSON" .json)"
OUT_JSON_GUESS="output/final_${STEM}.json"

echo "[1/2] Sparrow run: $SPARROW_BIN -i $INPUT_JSON -t $TIME_LIMIT -s $SEED"
"$SPARROW_BIN" -i "$INPUT_JSON" -t "$TIME_LIMIT" -s "$SEED"

# Ha nem ott van, keressük a legfrissebb final_*.json-t
if [[ -f "$OUT_JSON_GUESS" ]]; then
  OUT_JSON="$OUT_JSON_GUESS"
else
  OUT_JSON="$(ls -t output/final_*.json | head -n 1)"
fi

echo "[2/2] Validate: $OUT_JSON"
./scripts/validate_sparrow_io.py --input "$INPUT_JSON" --output "$OUT_JSON" --overlap-check
