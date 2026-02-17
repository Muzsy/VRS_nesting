# How To Run VRS Nesting

This guide describes the current, supported commands for local execution.

## Prerequisites
- Python 3.10+
- Rust toolchain (`cargo`, `rustc`)
- Python dependencies:
  - `python3 -m pip install --break-system-packages -r requirements-dev.txt`

## Required quality gate
- Local full gate:
  - `./scripts/check.sh`
- Codex/report wrapper:
  - `./scripts/verify.sh --report codex/reports/<path>/<task>.md`

## CLI entrypoints

### 1) Table-solver flow (`v1`)
- Command:
```bash
python3 -m vrs_nesting.cli run <project_v1.json> --run-root runs
```
- Output contract on success:
  - stdout contains exactly one non-empty line: absolute `run_dir`.

### 2) DXF + Sparrow flow (`dxf_v1`)
- Command:
```bash
python3 -m vrs_nesting.cli dxf-run <project_dxf_v1.json> --run-root runs [--sparrow-bin /path/to/sparrow]
```
- Wrapper equivalent:
```bash
python3 scripts/run_real_dxf_sparrow_pipeline.py --project <project_dxf_v1.json> --run-root runs [--sparrow-bin /path/to/sparrow]
```
- Output contract on success:
  - stdout contains exactly one non-empty line: absolute `run_dir`.

## Sparrow resolution policy
Resolution order in `scripts/ensure_sparrow.sh`:
1. `SPARROW_BIN`
2. `SPARROW_SRC_DIR`
3. `vendor/sparrow`
4. fallback `.cache/sparrow` clone/build (disabled by default in CI)

CI default:
- `SPARROW_ALLOW_NETWORK_FALLBACK=0`

Local override (if needed):
- `SPARROW_ALLOW_NETWORK_FALLBACK=1 ./scripts/check.sh`

## Typical local run
1. Run gate:
```bash
./scripts/check.sh
```
2. Run DXF pipeline:
```bash
python3 -m vrs_nesting.cli dxf-run samples/project_rect_1000x2000.json --run-root runs
```

