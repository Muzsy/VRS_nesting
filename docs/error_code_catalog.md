# VRS Error Code Catalog

## Purpose
This document defines stable user-facing error code prefixes and key runtime error codes for CLI/runner flows.

## Error format
- Standard runtime error line:
  - `ERROR: <CODE>: <message>`
- `<CODE>` is stable and machine-searchable.

## Prefixes
- `E_SCHEMA_*`: project/schema validation errors
- `DXF_*`: DXF import geometry/layer contract errors
- `E_RUN_*`: table-solver pipeline orchestration errors
- `E_DXF_*`: DXF+Sparrow pipeline orchestration errors
- `E_SPARROW_*`: Sparrow runner resolution/execution/output errors
- `E_VRS_SOLVER_*`: table solver runner resolution/execution/output errors

## Core codes (current)
- `E_RUN_SOLVER`: table pipeline failed in solver runner stage (`vrs_nesting/pipeline/run_pipeline.py`)
- `E_RUN_PIPELINE`: table pipeline unexpected failure (`vrs_nesting/pipeline/run_pipeline.py`)
- `E_DXF_RUN`: DXF pipeline expected execution/validation failure (`vrs_nesting/pipeline/dxf_pipeline.py`)
- `E_DXF_PIPELINE`: DXF pipeline unexpected failure (`vrs_nesting/pipeline/dxf_pipeline.py`)
- `E_SPARROW_BIN_NOT_FOUND`: Sparrow binary resolution failed (`vrs_nesting/runner/sparrow_runner.py`)
- `E_SPARROW_NON_ZERO_EXIT`: Sparrow process returned non-zero (`vrs_nesting/runner/sparrow_runner.py`)
- `E_SPARROW_OUTPUT_NOT_FOUND`: expected Sparrow output artifact missing (`vrs_nesting/runner/sparrow_runner.py`)
- `E_SPARROW_OUTPUT_PARSE`: Sparrow output JSON parse/shape failed (`vrs_nesting/runner/sparrow_runner.py`)
- `E_SPARROW_INPUT_NOT_FOUND`: Sparrow runner input file missing (`vrs_nesting/runner/sparrow_runner.py`)
- `E_SPARROW_RUN_DIR_NOT_FOUND`: Sparrow runner target run_dir missing (`vrs_nesting/runner/sparrow_runner.py`)
- `E_SPARROW_RUN_ID_ALLOC`: run_id allocation failed after retries (`vrs_nesting/runner/sparrow_runner.py`)
- `E_SPARROW_UNEXPECTED`: unexpected Sparrow runner exception (`vrs_nesting/runner/sparrow_runner.py`)

## Notes
- Project model and DXF importer already expose deterministic structured codes:
  - `ProjectValidationError.code` in `vrs_nesting/project/model.py`
  - `DxfImportError.code` in `vrs_nesting/dxf/importer.py`
- New runtime errors should follow the same format and be added here.

