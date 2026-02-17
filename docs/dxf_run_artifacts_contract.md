# DXF Run Artifacts Contract

## Purpose
This document defines the canonical DXF pipeline entrypoints and the run artifact contract for successful `dxf-run` executions.

## Canonical Entrypoints
- Primary:
  - `python3 -m vrs_nesting.cli dxf-run <project_dxf_v1.json> --run-root <runs_dir> [--sparrow-bin <path>]`
- Wrapper:
  - `python3 scripts/run_real_dxf_sparrow_pipeline.py --project <project_dxf_v1.json> --run-root <runs_dir> [--sparrow-bin <path>]`

Notes:
- The wrapper delegates to `vrs_nesting.cli` only.
- The wrapper must not emit extra stdout payload on success.

## Stdout/Stderr Contract
### Success (exit=0)
- stdout: exactly one non-empty line, absolute `run_dir` path.
- stderr: optional logs and warnings.

### Failure (exit!=0)
- stdout: should stay empty or non-parseable as run_dir.
- stderr: must contain actionable error context.

## run_id and run_dir Allocation Policy
Allocation uses `create_run_dir(run_root=...)`:
- `run_root` is resolved with `Path.resolve()`.
- `run_id` format: `YYYYMMDDTHHMMSSZ_<8hex>`.
- `run_dir` path: `<run_root>/<run_id>`.
- `run_dir/out` is created during allocation.
- `run_dir/run.log` is created during allocation.

## Required Run Artifacts (DXF, exit=0)
Top-level files in `run_dir`:
- `project.json`
- `run.log`
- `report.json`
- `sparrow_instance.json`
- `solver_input.json`
- `sparrow_input_meta.json`
- `sparrow_output.json`
- `solver_output.json`
- `source_geometry_map.json`
- `sparrow_stdout.log`
- `sparrow_stderr.log`

Output directory:
- `out/` exists
- `out/sheet_001.dxf` exists and is non-empty when at least one sheet is exported

Optional per-sheet subtree (expected when multisheet loop ran):
- `sheets/sheet_001/...`

## report.json Minimal Schema (`contract_version = dxf_v1`)
Required top-level keys:
- `contract_version` (`"dxf_v1"`)
- `project_name`
- `seed`
- `time_limit_s`
- `run_dir`
- `status`
- `paths`
- `metrics`
- `export_summary`

Required `paths` keys:
- `project_json`
- `sparrow_instance_json`
- `solver_input_json`
- `sparrow_input_meta_json`
- `sparrow_output_json`
- `solver_output_json`
- `out_dir`

Required `metrics` keys:
- `placements_count`
- `unplaced_count`

## Reference Implementation
- `vrs_nesting/cli.py`
- `scripts/run_real_dxf_sparrow_pipeline.py`
- `vrs_nesting/run_artifacts/run_dir.py`
- `vrs_nesting/sparrow/multi_sheet_wrapper.py`
- `scripts/smoke_real_dxf_sparrow_pipeline.py`

## Related Docs
- `docs/how_to_run.md` (current supported command examples)
- `docs/error_code_catalog.md` (runtime error code format)
