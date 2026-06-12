# SGH-Q36 Report

## Scope

Q36 makes the `sparrow_cde_multisheet` solver **spacing-aware**: when `spacing_mm > 0`,
part-part collision/search runs on a *spacing-expanded* contour (the original outer polygon
offset outward by `spacing_mm / 2`). When two expanded contours merely touch, the original
contours are exactly `spacing_mm` apart. Output/export and sheet boundary always use the
ORIGINAL geometry. The Q35 final validator + safety gate remains active as the production
safety net.

## Existing repo audit

- Q31: per-part `CdeBaseShape` cache (no `prepare_base_shape_native` in the hot path).
- Q33: `TechnologyClearancePolicy` (margin/spacing/kerf) + diagnostics.
- Q34/Q34-R1: `margin_mm` sheet-boundary enforcement (rectangular) + polygon final validator.
- Q35: `find_part_spacing_violations` / `count_part_spacing_violations` /
  `PART_SPACING_VIOLATION_Q35` final validator + safety gate.
- Canonical geometry helpers reused: `extract_polygon_from_part`, `transform_polygon`,
  `transform_base_to_candidate`, `CdeBaseShape`.

## Geometry roles: original vs spacing-expanded

| Role | Geometry | Used for |
|---|---|---|
| `Original` | part outer polygon | sheet boundary / margin validation, output/export, final polygon |
| `PartPartSpacingExpanded` | original offset outward by `spacing_mm / 2` | part-part collision / search ONLY |

`SPInstance` carries both `base_shape` (original) and `spacing_collision_base_shape`
(expanded). When `spacing_mm == 0`, the two are the SAME `Rc` — the pre-Q36 path is
byte-identical (preserved determinism + all prior gates).

## Why spacing is not sheet margin

Part-part spacing expansion must not be used as a sheet-boundary margin. Boundary/container
checks use original geometry plus margin policy; part-part checks use spacing-expanded
geometry. Concretely, the spacing-aware sessions are **pairs-only** (no real sheet Exterior
hazard — `build_pairs_only` registers only a large no-op container), so a spacing-expanded
candidate is never measured against the sheet edge. Boundary is enforced separately on the
original geometry by the broad-phase bbox-fit gate (and the tracker's original-shape boundary
quantification). The `spacing_not_sheet_margin` artifact confirms a single part with
`spacing_mm = 10, margin_mm = 0` is placed at the sheet edge with zero boundary violations.

## Offset implementation

`technology/spacing_geometry.rs`:
- `SpacingGeometryRole`, `SpacingOffsetConfig { spacing_mm, half_spacing_mm, tolerance_mm }`
  (`half_spacing_mm = spacing_mm / 2`; kerf is never folded in).
- `build_spacing_expanded_outer_polygon(local, half_spacing) -> Result<Vec<Point>, SpacingGeometryError>`:
  miter-join outward edge offset. Exact for axis-aligned rectangles; supports simple
  closed polygons (a triangle offset stays a triangle, NOT a bbox rectangle).
  `half_spacing <= 0` returns the original. Errors:
  `UNSUPPORTED_SPACING_OFFSET_Q36`, `INVALID_SPACING_OFFSET_POLYGON_Q36`,
  `SELF_INTERSECTING_SPACING_OFFSET_Q36` (area-shrink / edge-cross detection). Never a silent
  raw fallback — a part whose offset fails is unplaced with `UNSUPPORTED_SPACING_OFFSET_Q36`.

## Touching semantics for spacing-expanded geometry

New isolated `CdeTouchingPolicy::SpacingExpandedTouchAllowed`: expanded-contour touching is an
ALLOWED candidate (originals then exactly `spacing_mm` apart); positive overlap of expanded
contours is a collision. It shares `VrsTouchAllowed`'s pair post-policy but is a distinct
variant — raw/original `SparrowStrict` semantics are untouched and still used when spacing is
off.

## Sparrow integration

`SparrowConfig.spacing_mm` (default 0) is set from `FiniteStockRunConfig.spacing_mm`, which the
adapter fills from `technology_policy.effective_part_spacing_mm()`. `SparrowProblem::from_solver_input`
builds the per-part spacing-expanded base-shape cache (keyed by `part_id`) alongside the Q31
original cache. Diagnostics: `spacing_geometry_applied`, `spacing_offset_mm`,
`spacing_offset_part_count`, `spacing_offset_cache_hits/misses`, `spacing_offset_failure_count`.

## LBF/search/tracker changes

- **Tracker** (`quantify/tracker.rs`): `prepare_item` builds shapes from
  `spacing_collision_base_shape` (pairs + sessions); `recompute_boundary_for_item` builds the
  ORIGINAL shape on the fly when spacing is active; the internal pair sessions use
  `pair_touching_policy(spacing_applied)`. `spacing_applied` is derived from the instances
  (Rc identity), so off ⇒ identical to pre-Q36.
- **Separator search** (`sample/search.rs`): the candidate base is the spacing shape;
  `build_sheet_session` builds a pairs-only `SpacingExpandedTouchAllowed` session when spacing
  is active (boundary via the original-dims bbox-fit gate in `SeparationEvaluator`).
- **Worker** (`worker.rs`): the live session is pairs-only `SpacingExpandedTouchAllowed` when
  spacing is active.
- **LBF** (`lbf.rs`): candidate + placed-item shapes from the spacing base; pairs-only session
  when spacing active; the original-dims bbox-fit gate enforces boundary.

`pair collision / pair loss → spacing_collision_base_shape`; `boundary/container loss →
original base_shape`. No production path leaves part-part collision on original geometry when
`spacing_mm > 0`.

## Diagnostics

`OptimizerDiagnosticsOutput` gained: `technology_spacing_geometry_applied`,
`technology_spacing_offset_mm`, `technology_spacing_offset_part_count`,
`technology_spacing_offset_cache_hits`, `technology_spacing_offset_cache_misses`,
`technology_spacing_offset_failure_count`, `technology_spacing_boundary_uses_original_geometry`
(always true), `technology_spacing_output_uses_original_geometry` (always true). `technology_kerf_mm`
remains a separate value.

## Tests

`rust/vrs_solver/tests/technology_spacing_geometry.rs` (10 tests):

| Test | Proves |
|---|---|
| `rectangle_half_spacing_offset_exact` | 20×10 spacing 4 → extent −2..22 / −2..12 |
| `zero_spacing_uses_original_geometry` | spacing 0 → original polygon |
| `expanded_touching_means_original_spacing` | expanded touch ⇒ original exactly spacing apart, 0 violations |
| `expanded_overlap_means_spacing_violation` | original gap < spacing ⇒ violation |
| `spacing_must_not_become_sheet_margin` | spacing>0, margin 0 → part at edge, 0 boundary violations |
| `margin_and_spacing_are_independent` | margin 10 + spacing 6 → offset 3, margin stays 10 |
| `non_rect_polygon_offset_is_not_bbox` | triangle offset stays a triangle |
| `output_geometry_remains_original` | output respects original spacing; output-original flag true |
| `kerf_independence` | spacing 5 + kerf 2 → offset 2.5 (not 3.5) |
| `q35_final_validator_remains_active` | touching originals at positive spacing still flagged |

Plus 6 inline unit tests in `spacing_geometry.rs`. lib 466/466, Q33 9/9, Q34 15/15, Q35 10/10,
Q36 10/10.

## Synthetic artifacts

- `spacing_geometry_touch_ok` (2× 20×20, spacing 10, 200×100): status ok, offset 5, violation 0,
  parts placed ~30 mm apart (≥ spacing), output original.
- `spacing_not_sheet_margin` (1× 20×20, spacing 10, margin 0, 100×100): status ok, boundary
  violations 0, part at the sheet edge — spacing did not act as a margin.
- `spacing_violation_safety` (2× 25×25, spacing 30, 60×60): the spacing-aware solver cannot fit
  both 30 mm apart, so it returns a partial (1 placed, 1 unplaced) rather than a spacing-violating
  `ok`; the Q35 gate still guards the output.

## Q31/Q32/Q33/Q34/Q35 regression checks

- Q31 base-shape cache transfer intact; `prepare_base_shape_native` not reintroduced into the hot path.
- Q32 `smoke_sgh_q32_finite_stock_multisheet.py` → **PASS=89 FAIL=0** (spacing 0 path byte-identical).
- Q33 smoke → PASS; Q34 smoke → PASS; Q35 smoke → PASS.
- `./scripts/check.sh` → `[DONE] smoketest OK` (determinism gate intact — spacing 0).

## Cavity prepack note

The repository already contains cavity prepack / cavity prepack v2. Q36 does not modify,
replace, or connect it to the Sparrow multisheet solver. Cavity prepack remains a later
integration module.

## Kerf independence note

kerf_mm is independent from spacing_mm. Q36 does not add kerf_mm to spacing_mm and does not use
kerf_mm for spacing-expanded solver geometry.

## Non-goals

- No kerf geometry.
- No cavity prepack integration.
- No lead-in/out handling.
- No irregular sheet offset.
- No hole/cavity-aware spacing offset.
- No solver search tuning.
- No sample-budget tuning.
- No compression.
- No legacy multisheet fallback.

## Final verdict

**PASS.** All acceptance criteria met:

- `spacing_mm > 0` ⇒ solver part-part collision/search uses spacing-expanded geometry; offset
  is `spacing_mm / 2`; kerf is never added.
- Output/export and sheet boundary/margin use original geometry; spacing creates no artificial
  sheet margin.
- Spacing-expanded touching is an allowed candidate; positive overlap is a collision.
- The Q35 final validator stays active; a spacing violation can never yield an `ok` output.
- Q31 base-shape cache intact (no `prepare_base_shape_native` hot-path regression); cavity
  prepack / v2 unmodified; no compression / legacy fallback.
- build / lib (466) / Q33 (9) / Q34 (15) / Q35 (10) / Q36 (10) / smokes (Q36 50, Q35, Q34, Q33,
  Q32 89) / check.sh / verify.sh all PASS.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-12T01:19:20+02:00 → 2026-06-12T01:21:43+02:00 (143s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q36_spacing_aware_solver_geometry.verify.log`
- git: `main@836e131`
- módosított fájlok (git status): 25

**git diff --stat**

```text
 .../outputs/technology_policy_smoke_output.json    |  16 +-
 .../sgh_q34/outputs/sheet_margin_ok_output.json    |  14 +-
 .../outputs/sheet_margin_too_large_output.json     |  14 +-
 .../sgh_q35/outputs/part_spacing_ok_output.json    |  16 +-
 .../outputs/part_spacing_violation_output.json     |  78 ++++++----
 rust/vrs_solver/src/adapter.rs                     |  33 ++++
 rust/vrs_solver/src/io.rs                          |  23 +++
 rust/vrs_solver/src/optimizer/cde_adapter.rs       | 168 +++++++++++++++++----
 .../src/optimizer/sparrow/diagnostics.rs           |  24 +++
 rust/vrs_solver/src/optimizer/sparrow/lbf.rs       |  38 +++--
 rust/vrs_solver/src/optimizer/sparrow/mod.rs       |   6 +-
 rust/vrs_solver/src/optimizer/sparrow/model.rs     |  78 ++++++++++
 .../vrs_solver/src/optimizer/sparrow/multisheet.rs |   9 +-
 rust/vrs_solver/src/optimizer/sparrow/optimizer.rs |   7 +
 .../src/optimizer/sparrow/quantify/tracker.rs      |  61 ++++++--
 .../src/optimizer/sparrow/sample/search.rs         |  26 +++-
 rust/vrs_solver/src/optimizer/sparrow/tests.rs     |   2 +
 rust/vrs_solver/src/optimizer/sparrow/worker.rs    |  23 ++-
 rust/vrs_solver/src/technology/mod.rs              |   1 +
 19 files changed, 528 insertions(+), 109 deletions(-)
```

**git status --porcelain (preview)**

```text
 M artifacts/benchmarks/sgh_q33/outputs/technology_policy_smoke_output.json
 M artifacts/benchmarks/sgh_q34/outputs/sheet_margin_ok_output.json
 M artifacts/benchmarks/sgh_q34/outputs/sheet_margin_too_large_output.json
 M artifacts/benchmarks/sgh_q35/outputs/part_spacing_ok_output.json
 M artifacts/benchmarks/sgh_q35/outputs/part_spacing_violation_output.json
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/cde_adapter.rs
 M rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs
 M rust/vrs_solver/src/optimizer/sparrow/lbf.rs
 M rust/vrs_solver/src/optimizer/sparrow/mod.rs
 M rust/vrs_solver/src/optimizer/sparrow/model.rs
 M rust/vrs_solver/src/optimizer/sparrow/multisheet.rs
 M rust/vrs_solver/src/optimizer/sparrow/optimizer.rs
 M rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs
 M rust/vrs_solver/src/optimizer/sparrow/sample/search.rs
 M rust/vrs_solver/src/optimizer/sparrow/tests.rs
 M rust/vrs_solver/src/optimizer/sparrow/worker.rs
 M rust/vrs_solver/src/technology/mod.rs
?? artifacts/benchmarks/sgh_q36/
?? codex/reports/egyedi_solver/sgh_q36_spacing_aware_solver_geometry.md
?? codex/reports/egyedi_solver/sgh_q36_spacing_aware_solver_geometry.verify.log
?? rust/vrs_solver/src/technology/spacing_geometry.rs
?? rust/vrs_solver/tests/technology_spacing_geometry.rs
?? scripts/smoke_sgh_q36_spacing_aware_solver_geometry.py
```

<!-- AUTO_VERIFY_END -->
