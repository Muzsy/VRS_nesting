# Solver IO contract (v1)

## Purpose
This document defines the stable JSON boundary between VRS Python orchestration and an external table solver binary.

## Versioning
- `contract_version`: `v1`
- Backward compatibility policy:
  - `v1.x` keeps existing required fields stable.
  - New optional fields may be added in minor updates.
  - Breaking changes require `v2` and explicit migration notes.

## Input file: `solver_input.json`
The runner writes this file into `runs/<run_id>/solver_input.json`.

Required top-level fields:
- `contract_version` (string): must be `v1`
- `project_name` (string)
- `seed` (integer, `>= 0`)
- `time_limit_s` (integer, `> 0`)
- `stocks` (array, non-empty)
- `parts` (array, non-empty)

Stock item fields:
- `id` (string)
- `quantity` (integer, `> 0`)
- rectangle mode (required if `outer_points` not present):
  - `width` (number, `> 0`)
  - `height` (number, `> 0`)
- shaped mode (recommended):
  - `outer_points` (array of points, 3+)
  - `holes_points` (array of polygon point arrays, optional)

Point format:
- `[x, y]`
- or `{ "x": <number>, "y": <number> }`

Part item fields:
- `id` (string)
- `width` (number, `> 0`)
- `height` (number, `> 0`)
- `quantity` (integer, `> 0`)
- `allowed_rotations_deg` (array of integer degrees, non-empty)
  - allowed values: `0`, `90`, `180`, `270`

## Output file: `solver_output.json`
The solver must produce `runs/<run_id>/solver_output.json`.

Required top-level fields:
- `contract_version` (string): must be `v1`
- `status` (string): `ok` or `partial`
- `placements` (array)
- `unplaced` (array)

Placement item fields:
- `instance_id` (string)
- `part_id` (string)
- `sheet_index` (integer, `>= 0`)
- `x` (number)
- `y` (number)
- `rotation_deg` (number)

Unplaced item fields:
- `instance_id` (string)
- `part_id` (string)
- `reason` (string), e.g. `PART_NEVER_FITS_STOCK`

Optional top-level fields:
- `metrics` (object), e.g. utilization/runtime values

## Runner metadata: `runner_meta.json`
The Python runner records:
- `run_id`, `run_dir`
- `solver_bin`, `cmd`, `return_code`
- `seed`, `time_limit_s`
- `input_snapshot_path`, `output_path`
- `input_sha256`, `output_sha256`
- `started_at_utc`, `ended_at_utc`, `duration_sec`

## Binary resolution
`vrs_solver_runner.py` resolves solver executable in this order:
1. Explicit CLI flag `--solver-bin`
2. Environment variable `VRS_SOLVER_BIN`
3. `PATH` lookup for `vrs_solver`

## Failure modes
- Missing binary -> deterministic runner error
- Non-zero solver exit -> runner writes `runner_meta.json` and exits error
- Missing or invalid output JSON -> deterministic runner error with path context
- Invalid shape geometry (outer/holes) -> deterministic runner or validator error
