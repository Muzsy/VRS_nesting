#!/bin/bash
# Build script for nfp_cgal_probe
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROBE_DIR="${SCRIPT_DIR}/../tools/nfp_cgal_probe"
BUILD_DIR="${PROBE_DIR}/build"

echo "=== Building nfp_cgal_probe ==="
echo "Probe dir: ${PROBE_DIR}"
echo "Build dir: ${BUILD_DIR}"

if [ ! -f "${PROBE_DIR}/CMakeLists.txt" ]; then
    echo "ERROR: CMakeLists.txt not found at ${PROBE_DIR}/CMakeLists.txt"
    exit 1
fi

if [ ! -f "${PROBE_DIR}/src/main.cpp" ]; then
    echo "ERROR: main.cpp not found at ${PROBE_DIR}/src/main.cpp"
    exit 1
fi

# Create build dir
mkdir -p "${BUILD_DIR}"

# CMake configure
echo "--- cmake configure ---"
cd "${BUILD_DIR}"
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=g++

# Build
echo "--- cmake build ---"
cmake --build . --parallel

# Verify binary
BINARY="${BUILD_DIR}/nfp_cgal_probe"
if [ ! -x "${BINARY}" ]; then
    echo "ERROR: binary not found or not executable: ${BINARY}"
    exit 1
fi

echo "--- binary info ---"
ls -lh "${BINARY}"
"${BINARY}" --version

echo "=== BUILD SUCCESS ==="
