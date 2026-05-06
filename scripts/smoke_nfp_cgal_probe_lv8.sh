#!/bin/bash
# Smoke test for nfp_cgal_probe — runs all 3 LV8 pairs
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROBE_BINARY="${SCRIPT_DIR}/../tools/nfp_cgal_probe/build/nfp_cgal_probe"
OUTPUT_DIR="${SCRIPT_DIR}/../tmp/reports/nfp_cgal_probe"

echo "=== nfp_cgal_probe smoke test ==="
echo "Binary: ${PROBE_BINARY}"
echo "Output: ${OUTPUT_DIR}"

if [ ! -x "${PROBE_BINARY}" ]; then
    echo "ERROR: binary not found or not executable: ${PROBE_BINARY}"
    echo "Run scripts/build_nfp_cgal_probe.sh first"
    exit 1
fi

mkdir -p "${OUTPUT_DIR}"

PAIRS=(
    "lv8_pair_01"
    "lv8_pair_02"
    "lv8_pair_03"
)

ALL_PASSED=true

for pair in "${PAIRS[@]}"; do
    FIXTURE="${SCRIPT_DIR}/../tests/fixtures/nesting_engine/nfp_pairs/${pair}.json"
    OUTPUT="${OUTPUT_DIR}/${pair}.json"

    if [ ! -f "${FIXTURE}" ]; then
        echo "ERROR: fixture not found: ${FIXTURE}"
        ALL_PASSED=false
        continue
    fi

    echo "--- ${pair} ---"
    set +e
    "${PROBE_BINARY}" --fixture "${FIXTURE}" --output-json "${OUTPUT}" 2>&1
    RV=$?
    set -e

    if [ -f "${OUTPUT}" ]; then
        STATUS=$(python3 -c "import json; d=json.load(open('${OUTPUT}')); print(d.get('status','UNKNOWN'))" 2>/dev/null || echo "PARSE_ERROR")
        TIMING=$(python3 -c "import json; d=json.load(open('${OUTPUT}')); print(d.get('timing_ms','?'))" 2>/dev/null || echo "?")
        OUTER_V=$(python3 -c "import json; d=json.load(open('${OUTPUT}')); print(len(d.get('outer_i64',[])))" 2>/dev/null || echo "?")
        echo "  status=${STATUS} timing_ms=${TIMING} outer_vertices=${OUTER_V}"
        if [ "${STATUS}" != "success" ]; then
            echo "  WARNING: status != success"
            ALL_PASSED=false
        fi
    else
        echo "  ERROR: no output file created (exit code: ${RV})"
        ALL_PASSED=false
    fi
done

echo ""
if [ "${ALL_PASSED}" = true ]; then
    echo "=== ALL SMOKE TESTS PASSED ==="
else
    echo "=== SOME SMOKE TESTS FAILED ==="
fi
