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

Optional top-level fields:
- `solver_profile` (string): capability profile selector. If omitted, defaults to legacy rectangular behavior.
  - `jagua_optimizer_phase1_outer_only`: Phase 1 profile — rectangular multi-sheet, no item holes, no irregular stock.

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
- optional geometry fields (for geometry-based export and advanced flows):
  - `outer_points` (array of points, 3+)
  - `holes_points` (array of polygon point arrays, optional)

## Output file: `solver_output.json`
The solver must produce `runs/<run_id>/solver_output.json`.

Required top-level fields:
- `contract_version` (string): must be `v1`
- `status` (string): `ok`, `partial`, or `unsupported`
- `placements` (array)
- `unplaced` (array)

Optional top-level fields:
- `unsupported_reason` (string): present only when `status == "unsupported"`, e.g. `UNSUPPORTED_PART_HOLES_PHASE1`

Placement item fields:
- `instance_id` (string)
- `part_id` (string)
- `sheet_index` (integer, `>= 0`)
- `x` (number)
- `y` (number)
- `rotation_deg` (number)

`sheet_index` semantics (explicit contract):
- The solver must treat `stocks` as an ordered sequence and expand each stock item by its `quantity`.
- Expansion order is stable: for each `stocks[i]`, emit `quantity` virtual sheets before moving to `stocks[i+1]`.
- `sheet_index` points to this expanded sequence with 0-based indexing.
- Example: `stocks=[{id:A,quantity:2},{id:B,quantity:1}]` => valid sheet slots are
  `0:A#0`, `1:A#1`, `2:B#0`.

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

## Phase 1 outer-only capability policy (`jagua_optimizer_phase1_outer_only`)

When `solver_profile == "jagua_optimizer_phase1_outer_only"`:
- Supported: rectangular or shaped `stocks`, multi-sheet, 0/90/180/270 rotation.
- Unsupported: parts with `holes_points` or `prepared_holes_points` (non-empty).
- Unsupported: part-in-hole cavity, irregular/remnant nesting.

Unsupported part output:
```json
{
  "contract_version": "v1",
  "status": "unsupported",
  "unsupported_reason": "UNSUPPORTED_PART_HOLES_PHASE1",
  "placements": [],
  "unplaced": []
}
```

Runner behavior on `status == "unsupported"`:
- Does NOT call `validate_multi_sheet_output()` (not a layout response).
- Writes `runner_meta.json` with `solver_status: "unsupported"` and `unsupported_reason`.
- Returns `run_dir` normally; caller must check `solver_status` in meta.

Backward compatibility:
- If `solver_profile` is absent, the solver runs legacy rectangular mode regardless of part geometry fields.
- `validate_multi_sheet_output()` only validates `ok`/`partial` layouts; `unsupported` is not a valid layout status.

## Failure modes
- Missing binary -> deterministic runner error
- Non-zero solver exit -> runner writes `runner_meta.json` and exits error
- Missing or invalid output JSON -> deterministic runner error with path context
- Invalid shape geometry (outer/holes) -> deterministic runner or validator error
- Part holes with Phase 1 profile -> deterministic `unsupported` output, no layout placement
