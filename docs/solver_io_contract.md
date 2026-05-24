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
  - `jagua_optimizer_phase1_outer_only`: Phase 1 profile — rectangular or irregular (outer-only) multi-sheet, no item holes, no stock holes, no runtime margin shrink.
- `margin_mm` (number, `>= 0`): parsed and stored in `SolverInput` but **not applied at Rust runtime** (see margin policy section below). Non-zero `margin_mm` with Phase 1 profile returns `UNSUPPORTED_MARGIN_MM_RUNTIME`.

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
- Supported: rectangular or irregular (concave outer_points) `stocks`, multi-sheet, 0/90/180/270 rotation.
- Supported: `Stock.outer_points` L-shape/remnant stocks (hole-free). The `SheetShape` stores `has_irregular_outer=true` and uses `_outer_poly` for boundary containment checks in `rect_inside_sheet_shape()`.
- Unsupported: parts with `holes_points` or `prepared_holes_points` (non-empty) → `UNSUPPORTED_PART_HOLES_PHASE1`.
- Unsupported: stocks with non-empty `holes_points` (container holes) → `UNSUPPORTED_STOCK_HOLES_PHASE1`.
- Unsupported: `margin_mm > 0` → `UNSUPPORTED_MARGIN_MM_RUNTIME` (margin not applied at Rust runtime).
- Unsupported: part-in-hole cavity nesting.

Parts that cannot fit any stock dimension are pre-filtered before optimization; they appear in `unplaced` with reason `PART_NEVER_FITS_STOCK`.

Unsupported output format:
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

## Irregular sheet boundary policy (JG-16 / JG-17)

`SheetShape` fields added in JG-16:
- `has_irregular_outer: bool` — true when stock was defined via explicit `outer_points`.
- `area: f64` — outer polygon area in input units² (shoelace formula).

When `has_irregular_outer == true` (irregular stocks — JG-17 inset semantics):
- `rect_inside_sheet_shape()` uses an inset rect (INSET = 1e-6 per axis, inward) for all
  irregular boundary checks. This handles jagua-rs `SPolygon.collides_with` returning false
  for points exactly on the polygon boundary (vertex or collinear edge overlap). The inset
  test asks: "is the interior of the rect inside the polygon?" — the correct geometric predicate.
- All 4 inset corners are checked against `_outer_poly` using `SPolygon.collides_with(JagPoint)`.
- All 4 inset edges are checked against outer polygon edges using `Edge.collides_with(Edge)`.

When `has_irregular_outer == false` (rectangular stocks):
- Only bbox bounds check with EPS=1e-9 tolerance is applied; behaviour unchanged from pre-JG-16.
- A rect edge exactly touching the sheet boundary is accepted (within EPS).

## Boundary validation policy facade (JG-17)

`rust/vrs_solver/src/optimizer/boundary.rs` is the single auditable point for all placement
boundary decisions. All construction (initializer), repair, scoring, and adapter paths delegate
boundary checks through this module.

Public API:
- `rect_within_boundary(rect, sheet)` — canonical proxy check; delegates to `rect_inside_sheet_shape`.
- `sheet_index_valid(sheet_index, sheets)` — validates sheet index bounds.
- `is_placement_boundary_valid(rect, sheet_index, sheets)` — combined check for validation paths.

### Boundary-touch policy

**Rectangular stocks** (`has_irregular_outer = false`):
- Boundary check is bbox-only with EPS = 1e-9 tolerance.
- A rect edge exactly touching the sheet boundary is **accepted** (within EPS).

**Irregular stocks** (`has_irregular_outer = true`):
- An inset rect (1e-6 inward per axis) is used for all containment and edge-crossing checks.
- A rect placed exactly at the polygon boundary (corner on vertex, edge collinear with poly edge)
  is **accepted** if the interior of the rect is inside the polygon.
- A rect that straddles the boundary or has any corner in a concave notch is **rejected**.

### Proxy vs exact boundary

- **Proxy (Rust):** `rect_within_boundary()` — fast, used during construction, repair, scoring.
  For rectangular stocks this is exact (bbox). For irregular stocks it is a correct containment
  check via jagua SPolygon primitives with inset semantics.
- **Exact (Python):** `vrs_nesting.nesting.instances.validate_multi_sheet_output()` — uses
  Shapely `sheet_poly.covers(placement_poly)` for full polygon containment. This is the
  authoritative validation gate. The Python validator also applies `margin_mm` via
  `buffer(-margin_mm)` if specified, which the Rust runtime does not (JG-16).

### Container holes

Container holes (`Stock.holes_points`) remain unsupported in Phase 1 and are rejected at the
adapter level before construction begins (`UNSUPPORTED_STOCK_HOLES_PHASE1`).

## margin_mm / spacing_mm field status (JG-16 update)

**`margin_mm`** is now a parsed field in the Rust `SolverInput` struct (added in JG-16):
- `margin_mm: Option<f64>` with `#[serde(default)]`.
- It is **parsed** from JSON input but **not applied at Rust runtime** during placement.
- With Phase 1 profile: if `margin_mm > 0`, the solver returns `UNSUPPORTED_MARGIN_MM_RUNTIME` (explicit unsupported, not silent ignore).
- With legacy profile (no solver_profile): `margin_mm` is parsed and stored but has no effect on placement.
- `vrs_nesting/nesting/instances.py` `validate_multi_sheet_output()` continues to apply `margin_mm` via Shapely `buffer(-margin_mm)` during Python exact validation.

**`spacing_mm`** remains a validator-only field — not parsed by the Rust solver.

Status: **PARTIAL PROMOTION — `margin_mm` is now a v1 SolverInput field but runtime shrink is deferred (JG-17 or later). Non-zero margin with Phase 1 → explicit unsupported.**

Fixtures must not claim runtime margin/spacing enforcement the Rust solver does not implement.

## Candidate generation policy (JG-18)

`rust/vrs_solver/src/optimizer/candidates.rs` provides two APIs:

### Legacy API (rectangular stocks)

```rust
generate_candidates(sheet_count: usize, placed: &[PlacedBbox]) -> Vec<CandidatePoint>
```

Generates one origin `(0.0, 0.0)` per sheet plus three points per placed bbox
(right-side, top-side, top-right corner). Sorted by `(sheet_index ASC, y ASC, x ASC)`,
deduplicated by EPS proximity.

### Irregular-aware API (JG-18, all stocks)

```rust
generate_candidates_with_sheets(
    sheets: &[SheetShape],
    placed: &[PlacedBbox],
) -> (Vec<CandidatePoint>, CandidateGenerationStats)
```

For rectangular stocks (`has_irregular_outer = false`): identical output to legacy API.

For irregular stocks (`has_irregular_outer = true`), adds:
- **VertexNear**: each outer polygon vertex as a bbox-min candidate point.
- **EdgeNear**: midpoint of each outer polygon edge.
- **InteriorSample**: deterministic grid across the sheet bbox with step = `bbox / INTERIOR_GRID_STEPS` (default 5), minimum step 1.0. Generates up to `(INTERIOR_GRID_STEPS-1)²` = 16 interior points per sheet.

All candidate points are bbox-min positions. Boundary validity is enforced in construction
and repair loops via `boundary::rect_within_boundary`. Candidates failing the boundary
check or collision check are discarded silently (counted in `ConstructionDiagnostics`).

### CandidateSource enum

| Variant | Source |
|---|---|
| `Origin` | Sheet origin `(0, 0)` |
| `PlacedNeighbor` | Right/top/top-right of placed bbox |
| `VertexNear` | Outer polygon vertex |
| `EdgeNear` | Midpoint of outer polygon edge |
| `InteriorSample` | Grid interior point |

### Candidate ordering and dedup

Result sorted by `(sheet_index ASC, y ASC, x ASC)`. Adjacent candidates within EPS
proximity on the same sheet are deduplicated (last-wins after sort). Deterministic for
identical `(sheets, placed)` input — no random sampling.

### Integration call sites (JG-18)

All three construction paths use `generate_candidates_with_sheets`:
- `optimizer/initializer.rs` — `build_initial_layout()`
- `optimizer/repair.rs` — repair reinsertion loop
- `optimizer/sheet_elimination.rs` — sheet elimination reinsertion

`ConstructionDiagnostics` (in `initializer.rs`) accumulates per-run candidate counts:
`total_candidates_generated`, `candidates_from_vertex`, `candidates_from_edge`,
`candidates_from_interior`.

## Sheet-cost score model (JG-19)

### Stock.cost_per_use field

Optional field on `Stock` (backward-compatible via `#[serde(default)]`):

```json
{ "id": "remnant_A3", "width": 297, "height": 420, "quantity": 1, "cost_per_use": 0.2 }
```

- Absent or `null` → defaults to `1.0` (identical behavior to pre-JG-19).
- Clamped to `>= 0.0` in `stock_to_shape`.
- Propagated to `SheetShape.cost_per_use: f64`.

### score_breakdown output (Phase1 only)

`SolverOutput` now includes an optional `score_breakdown` for `jagua_optimizer_phase1_outer_only`:

```json
{
  "score_breakdown": {
    "total_cost": -3000.0,
    "placed_area_contribution": -7500.0,
    "unplaced_contribution": 0.0,
    "sheet_cost_contribution": 2000.0,
    "sheet_cost_total": 0.2,
    "usable_area_utilization": 0.1875,
    "overlap_contribution": 0.0,
    "boundary_contribution": 0.0,
    "compactness_contribution": 4500.0
  }
}
```

Absent for legacy profiles (`skip_serializing_if = "Option::is_none"`) — no breaking change.

### sheet_count_contribution semantics (JG-19 update)

`sheet_count_contribution = sheet_cost_total * sheet_count_penalty_per_sheet`

where `sheet_cost_total = sum(cost_per_use for each used sheet slot)`.

For all-default-cost fixtures (`cost_per_use` absent) this equals the pre-JG-19
formula `sheet_count_used * sheet_count_penalty_per_sheet` — backward-compatible.

### usable_area_utilization

`placed_area / total usable area of used sheets`. Range [0, 1]. For irregular sheets,
`sheet.area` is the polygon area (shoelace), not the bbox area.

### Penalty hierarchy (unchanged)

`overlap/boundary (1e9) >> unplaced (1e6) >> sheet_cost (1e4 * cost) >> placed_area (1.0) >> compactness (0.001)`

An invalid layout always scores worse than any valid layout, regardless of cost savings.

### V1 limitations

- `cost_per_use` is a V1 nesting optimization proxy; not a final inventory/costing field.
- Phase 1 construction places items on the lowest-index fitting sheet (BLF/greedy).
  Sheet cost preference is expressed in the score model for evaluation and SA search guidance.
- See `docs/egyedi_solver/jagua_remnant_score_model_v1.md` for decision examples and design rationale.

## Failure modes
- Missing binary -> deterministic runner error
- Non-zero solver exit -> runner writes `runner_meta.json` and exits error
- Missing or invalid output JSON -> deterministic runner error with path context
- Invalid shape geometry (outer/holes) -> deterministic runner or validator error
- Part holes with Phase 1 profile -> deterministic `unsupported` output, no layout placement
