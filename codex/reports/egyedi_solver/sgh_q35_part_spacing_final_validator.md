# SGH-Q35 Report

## Scope

Q35 applies `spacing_mm` (`TechnologyClearancePolicy::effective_part_spacing_mm()`) as a
FINAL VALIDATOR + SAFETY GATE in the `sparrow_cde_multisheet` pipeline. When
`spacing_mm > 0`, two placements on the same sheet must have at least `spacing_mm` Euclidean
distance between their transformed outer polygons; otherwise the output cannot be `ok`.

This is NOT spacing-aware solver geometry and NOT a polygon offset engine. The solver still
runs unchanged; Q35 only validates the result and removes spacing-violating placements as a
gate. Spacing-aware placement is deferred to Q36.

## Existing repo audit

- Q33 added `TechnologyClearancePolicy` (margin/spacing/kerf) + diagnostics.
- Q34/Q34-R1 added `margin_mm` sheet-boundary enforcement with a polygon final validator
  (`find_sheet_margin_violations`) and a status safety net.
- Canonical polygon helpers already exist:
  `crate::optimizer::collision_backend::extract_polygon_from_part` and `transform_polygon`.
  Q35 reuses these — no new extraction/transform convention.

## Cavity prepack note

The repository already contains cavity prepack / cavity prepack v2. Q35 does not modify or
connect it to the Sparrow multisheet solver. Cavity prepack remains a later integration
module. (The smoke verifies via `git status` that no cavity `.rs` file was modified by Q35.)

## Kerf independence note

`kerf_mm` is independent from `spacing_mm`. Q35 does not add `kerf_mm` to `spacing_mm`. Kerf
remains a separate technology value that follows the part and will later be resolved from
machine/material/thickness parameters. The spacing validator's distance threshold is
`effective_part_spacing_mm()` only.

## Part spacing validator implementation

New module `rust/vrs_solver/src/technology/spacing.rs` (exported via `pub mod spacing`):

```rust
pub struct PartSpacingViolation { sheet_index, a_instance_id, b_instance_id,
                                  a_part_id, b_part_id, distance_mm, required_spacing_mm }
pub fn find_part_spacing_violations(placements, parts, spacing_mm) -> Vec<PartSpacingViolation>
pub fn count_part_spacing_violations(placements, parts, spacing_mm) -> usize
pub fn polygon_distance_mm(a: &[Point], b: &[Point]) -> f64
```

Semantics:
- `spacing_mm <= 0` → no-op (no violations).
- Only placements with equal `sheet_index` are compared.
- Local polygon precedence (same as CDE/Sparrow): `prepared_outer_points` → `outer_points`;
  rectangle fallback `[(0,0),(w,0),(w,h),(0,h)]` ONLY when the part has no polygon; a
  malformed polygon is treated CONSERVATIVELY as a violation (distance 0).
- World polygon = `transform_polygon(local, x, y, rotation_deg)` — rotation-aware.
- A pair violates when `distance + SPACING_EPS < spacing_mm` (`SPACING_EPS = 1e-6`).

The decision is never bbox-based; `rotated_bbox_min_offset_f64`/`dims_for_rotation_f64` are
not used.

## Polygon distance semantics

`polygon_distance_mm`:
- Overlap / strict containment / coincident polygons → `0.0` (via `polygons_collide`).
- Otherwise the minimum segment-segment distance between the two boundaries, which yields
  `0.0` for touching edges/vertices and a positive value for separated polygons.
- Segment-segment distance returns 0 on (proper-or-touching) intersection, else the minimum
  of the four point-segment distances.

## Adapter safety gate

In `run_sparrow_finite_stock_multisheet_pipeline`, after the solver runs, the order is:

1. solver runs on margin-shrunk sheets (Q34) when `margin_mm > 0`;
2. Q34-R1 margin final validator → remove margin-violating placements → unplaced;
3. Q35 spacing final validator on the REMAINING placements;
4. spacing-violating placements removed → unplaced with reason `PART_SPACING_VIOLATION_Q35`;
5. a single shared recompute of all result aggregates;
6. diagnostics built from the fresh result.

`apply_spacing_violation_safety_net` removes BOTH endpoints of every violation pair (this is
a safety gate, not optimization). Because removed instances land in `unplaced`, the top-level
`status = if unplaced.is_empty() { "ok" } else { "partial" }` can no longer be `ok` when a
spacing violation exists. Guarantee: `technology_spacing_violation_count > 0 ⇒ status != ok`.

## Diagnostics

Added to `OptimizerDiagnosticsOutput` (optional, skip-if-none):
- `technology_part_spacing_applied` — `effective_part_spacing_mm() > 0`.
- `technology_part_spacing_mm` — `effective_part_spacing_mm()` (kerf NOT included).
- `technology_spacing_violation_count` — violation pair count (0 for valid `ok`).
- `technology_spacing_safety_net_removed_count` — unique placements removed by the gate.

`technology_kerf_mm` remains a separate field and is never folded into spacing.

## Result stat recomputation

New `multisheet.rs::recompute_multisheet_result_after_safety_net(result, parts,
original_sheets)` recomputes `used_sheet_indices`, `used_sheet_area`, `placed_part_area`,
`utilization_pct`, `placed_instances`, `unplaced_instances`, `status`, and
`best_full_solution_found` from the (possibly reduced) placements/unplaced. It is called once
after BOTH safety nets, fixing the Q34-R1 stale-stat caveat for margin and spacing alike.
Diagnostics and the top-level output are therefore never contradictory.

## Tests

`rust/vrs_solver/tests/technology_part_spacing.rs` (10 tests):

| Test | Proves |
|---|---|
| `rectangles_spacing_ok` | gap = 5, spacing 5 → no violation |
| `rectangles_spacing_violation` | gap = 4.9 < 5 → violation, distance recorded |
| `touching_parts_violate_positive_spacing` | touching (d=0), spacing 1 → violation |
| `touching_with_zero_spacing_ok` | spacing 0 → no-op |
| `different_sheets_ignored` | different sheet_index → never compared |
| `non_rect_polygon_proves_non_bbox` | triangles inside large bboxes, far apart → no violation (fails with bbox validator) |
| `non_rect_polygon_close_violates` | triangles actually close → violation |
| `rotated_polygon_spacing` | 45°-rotated triangle: far → none, adjacent → violation |
| `rectangle_fallback_spacing` | no `outer_points` → rect fallback; gap 5 ok, gap 3 violation |
| `invalid_polygon_conservative_violation` | malformed polygon → conservative violation |

`rust/vrs_solver/src/adapter.rs` inline unit tests (4):
- `spacing_safety_net_removes_both_endpoints` — Test 9: A–B violation removes A and B, keeps
  C, reason `PART_SPACING_VIOLATION_Q35`.
- `spacing_safety_net_forces_non_ok_status` — Test 10: removal leaves a non-empty `unplaced`,
  so top-level status cannot be `ok`.
- `spacing_safety_net_noop_when_no_violations`, plus the existing margin safety-net tests.

Results: lib 460/460, Q33 9/9, Q34 15/15, Q35 10/10.

## Smoke results

`scripts/smoke_sgh_q35_part_spacing_final_validator.py` — **35/35 PASS** (static + cavity-git
guard + synthetic ok/violation + dynamic `cargo test`).

- `part_spacing_ok.json` (1 part): status ok, spacing applied, mm 5.0, violation 0, kerf 0.0
  separate.
- `part_spacing_violation.json` (2 parts; solver not yet spacing-aware): status partial,
  spacing violation 1, 2 placements removed with `PART_SPACING_VIOLATION_Q35`, kerf separate.

## Q32/Q33/Q34 regression checks

- Q32 `smoke_sgh_q32_finite_stock_multisheet.py` → **PASS=89 FAIL=0**.
- Q33 `smoke_sgh_q33_technology_clearance_policy.py` → **43/43 PASS**.
- Q34 `smoke_sgh_q34_sheet_margin_enforcement.py` → **41/41 PASS**.

Two cross-task adjustments were required because Q35 now enforces spacing (which defaults to
`margin` when absent, per Q33):
- Q34 test helper `ms_input` pins `spacing_mm: 0.0` to isolate margin enforcement (otherwise
  the Q33 default `spacing = margin` would also fire the Q35 gate).
- The Q33 smoke input `technology_policy_smoke.json` uses quantity 1 so the policy-bridge
  smoke stays `ok` (its `spacing_mm = 2.0` diagnostic is unchanged; with a single part there
  are no spacing pairs). Two stale Q34 smoke checks were updated to the post-Q35 mechanism
  (recompute helper) and to exclude the new `technology_part_spacing_mm` diagnostic name.

## Non-goals

- No spacing-aware solver geometry.
- No polygon offset engine.
- No kerf-expanded geometry.
- No cavity prepack integration.
- No lead-in/out handling.
- No solver search tuning.
- No compression.
- No legacy multisheet fallback.

## Final verdict

**PASS.** All acceptance criteria met:

- `spacing_mm > 0` runs a part-part final spacing validator over full transformed polygons.
- `outer_points`/`prepared_outer_points` parts are not decided by bbox; rectangle fallback
  only for parts without a polygon.
- Touching/overlap at positive spacing → violation; different sheets are ignored.
- Spacing violation forces top-level status away from `ok`; the gate uses the explicit
  `PART_SPACING_VIOLATION_Q35` reason; result stats and diagnostics are recomputed (no stale).
- `kerf_mm` is never added to `spacing_mm`.
- Cavity prepack / v2 was not modified or connected.
- Q34 margin, Q33 policy, and Q32 finite-stock multisheet all still PASS.
- No compression/legacy regression.
- build / lib (460) / Q33 (9) / Q34 (15) / Q35 (10) / smokes (Q35 35, Q34 41, Q33 43, Q32 89)
  / check.sh / verify.sh all PASS.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-11T20:25:57+02:00 → 2026-06-11T20:28:20+02:00 (143s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q35_part_spacing_final_validator.verify.log`
- git: `main@846c48f`
- módosított fájlok (git status): 16

**git diff --stat**

```text
 .../sgh_q33/inputs/technology_policy_smoke.json    |   2 +-
 .../outputs/technology_policy_smoke_output.json    |  54 ++++---
 .../sgh_q34/outputs/sheet_margin_ok_output.json    |  10 +-
 .../outputs/sheet_margin_too_large_output.json     |  10 +-
 rust/vrs_solver/src/adapter.rs                     | 162 ++++++++++++++++++++-
 rust/vrs_solver/src/io.rs                          |  14 ++
 .../vrs_solver/src/optimizer/sparrow/multisheet.rs |  35 +++++
 rust/vrs_solver/src/technology/mod.rs              |   1 +
 rust/vrs_solver/tests/technology_sheet_margin.rs   |   3 +
 scripts/smoke_sgh_q34_sheet_margin_enforcement.py  |  18 ++-
 10 files changed, 260 insertions(+), 49 deletions(-)
```

**git status --porcelain (preview)**

```text
 M artifacts/benchmarks/sgh_q33/inputs/technology_policy_smoke.json
 M artifacts/benchmarks/sgh_q33/outputs/technology_policy_smoke_output.json
 M artifacts/benchmarks/sgh_q34/outputs/sheet_margin_ok_output.json
 M artifacts/benchmarks/sgh_q34/outputs/sheet_margin_too_large_output.json
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/sparrow/multisheet.rs
 M rust/vrs_solver/src/technology/mod.rs
 M rust/vrs_solver/tests/technology_sheet_margin.rs
 M scripts/smoke_sgh_q34_sheet_margin_enforcement.py
?? artifacts/benchmarks/sgh_q35/
?? codex/reports/egyedi_solver/sgh_q35_part_spacing_final_validator.md
?? codex/reports/egyedi_solver/sgh_q35_part_spacing_final_validator.verify.log
?? rust/vrs_solver/src/technology/spacing.rs
?? rust/vrs_solver/tests/technology_part_spacing.rs
?? scripts/smoke_sgh_q35_part_spacing_final_validator.py
```

<!-- AUTO_VERIFY_END -->
