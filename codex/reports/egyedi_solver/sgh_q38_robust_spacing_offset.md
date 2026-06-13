# SGH-Q38 Report

## Scope

Q38 replaces the naive per-edge miter offset (Q36) with a **robust straight-skeleton
polygon offset** so that real concave / high-vertex LV8 polygons produce a valid, single,
non-self-intersecting spacing-expanded outer contour. No solver search/sample tuning, no
kerf geometry, no cavity prepack, no compression, no legacy fallback.

## Existing Q36/Q37 problem

Q37 measured that the Q36 miter offset failed `SELF_INTERSECTING_SPACING_OFFSET_Q36` on the
high-vertex concave LV8 parts — at spacing 2, only 9/12 parts were offsettable and 116/276
instances (the 165/216/344-vertex parts `Lv8_07919/07920/07921`) were forced unplaced. That
was the production blocker the spacing-aware solver (Q36) could not get past.

## Offset algorithm chosen

`build_spacing_expanded_outer_polygon` now uses the already-vendored **`geo-buffer 0.2.0`**
crate (straight-skeleton buffer over `geo 0.24.1`), added as a direct dependency of
`vrs_solver` (versions pinned to the existing lockfile entries — no new resolution):

1. normalise the original local polygon (`clean_ring`);
2. build a `geo::Polygon`, oriented to the standard winding (`Orient::Default`);
3. `geo_buffer::buffer_polygon(&poly, +half_spacing_mm)` — outward inflate, wrapped in
   `catch_unwind` so any straight-skeleton panic maps to `OFFSET_BOOLEAN_UNION_FAILED_Q38`
   (never a silent raw fallback);
4. require **exactly one** exterior contour (`EMPTY_SPACING_OFFSET_Q38` /
   `MULTI_CONTOUR_SPACING_OFFSET_Q38` otherwise);
5. extract the exterior ring, drop the closing duplicate, and drop consecutive vertices that
   collapse to the **same f32 point** (`dedup_ring_f32`) — see below;
6. `validate_spacing_offset_outer_contour(original, offset)`.

The Q36 API and error variants are kept; new Q38-specific variants
(`MULTI_CONTOUR_SPACING_OFFSET_Q38`, `EMPTY_SPACING_OFFSET_Q38`,
`OFFSET_BOOLEAN_UNION_FAILED_Q38`) were added.

### f32 dedup (the key real-part fix)

The downstream CDE `SPolygon` stores vertices in f32 and rejects "duplicate points". The
straight skeleton on a 520-vertex part emitted consecutive vertices ~1e-4 mm apart that
collapse to identical f32 points (e.g. two `Point(1423.7, 283.40067)`), which `SPolygon::new`
rejected — so the offset *succeeded* in f64 but the part was still marked unsupported. Q38
drops consecutive/wraparound vertices that are equal in f32 space (`dedup_ring_f32`), which is
exactly what the collision engine sees: it removes no f32 boundary and is Q35-safe (no inward
move). This converted `Lv8_11612` at spacing 10 from unsupported to ok.

## Why this is robust for concave/high-vertex polygons

The straight skeleton computes the offset from the polygon's medial structure, so reflex
(concave) vertices and fine high-vertex detail are handled correctly instead of the miter's
per-edge line intersections blowing up into self-crossings. `validate_spacing_offset_outer_contour`
then enforces a single valid exterior ring (≥3 vertices, finite, no degenerate duplicate,
area > 0, offset area ≥ original, bbox not smaller than original, non-self-intersecting).

## LV8 failed-part regression

`rust/vrs_solver/tests/technology_spacing_offset_lv8.rs::lv8_failed_parts_offset_ok` loads
the real `Lv8_07919/07920/07921` polygons from the committed canonical input and asserts
`build_spacing_expanded_outer_polygon` + `validate_spacing_offset_outer_contour` are `Ok` at
spacing 2/5/10. All pass.

## Spacing 2/5/10/20/40 inventory

`scripts/bench_sgh_q38_spacing_offset_inventory.py` →
`artifacts/benchmarks/sgh_q38/tables/q38_spacing_offset_inventory.csv` + manifest. Offset
status is taken **authoritatively from the Rust solver** (single-instance-per-part probe on a
large sheet; unplaced `UNSUPPORTED_SPACING_OFFSET_Q36` ⇒ unsupported), geometry detail from a
reference shapely buffer.

| spacing_mm | offsettable | unsupported |
|---|---|---|
| 2 | **12/12** | 0 |
| 5 | **12/12** | 0 |
| 10 | **12/12** | 0 |
| 20 | **12/12** | 0 |
| 40 | **12/12** | 0 |

`UNSUPPORTED_SPACING_OFFSET_Q36` count at spacing 2 on LV8 is **0** (was 3 parts / 116
instances in Q37).

## Large spacing interpretation

20 and 40 mm spacing are included because the application may later be used for
flame-cutting / large-clearance workflows. These are robustness stress tests, not necessarily
the default laser-cutting configuration. On the LV8 set all 12 parts remain offsettable even
at 40 mm; the `lv8_large_spacing_stress` test additionally guarantees that any future large-
spacing failure is explicit and never a self-intersecting or raw/bbox output.

## No raw/bbox fallback proof

On any offset failure the function returns an explicit `SpacingGeometryError`; it returns the
original contour **only** for the `half_spacing_mm <= 0` no-op case (not a failure path).
There is no width/height bbox-expand anywhere. The smoke statically asserts no
`bbox-expand` logic, presence of the explicit multi-contour / buffer-failure errors, and the
`triangle_offset_is_not_bbox` test proves a true offset (area between the original and the
bbox-rectangle), not a bbox expansion.

## Kerf independence

`SpacingOffsetConfig::from_spacing_mm` keeps `half_spacing_mm = spacing_mm / 2`; kerf is never
added. The solver-path test `solver_spacing10_kerf3_offset_is_half_spacing` asserts
`technology_spacing_offset_mm == 5.0` (not 6.5/13) and `technology_kerf_mm == 3.0` with
`technology_spacing_offset_failure_count == 0`.

## Cavity prepack untouched

The repository already contains cavity prepack / cavity prepack v2. Q38 does not modify,
connect, rewrite, or benchmark it. The smoke verifies via `git status` that no cavity `.rs`
file was modified.

## Solver diagnostics after Q37 short rerun

`bench_sgh_q37_lv8_margin_spacing.py --tier mandatory --max-time-limit-s 30` after Q38:

| run | spacing | offset_fail (Q37→Q38) | placed (Q37→Q38) | spacing_viol |
|---|---|---|---|---|
| D1 | 2 | 58 → **0** | 109 → 125 | 0 |
| D2 | 2 (margin 5) | 58 → **0** | 108 → 125 | 0 |
| M1 | 2 | 116 → **0** | 122 → 143 | 0 |
| M2 | 2 (margin 5) | 116 → **0** | 122 → 143 | 0 |

`technology_spacing_offset_failure_count == 0` for all spacing runs; the previously
offset-blocked instances are now placeable, raising placed counts even at the 30 s cap. No
spacing/margin/boundary violations, no false `ok`.

## Tests

`rust/vrs_solver/tests/technology_spacing_offset_lv8.rs` (8 tests): rectangle sanity, concave
L-shape at 2/5/10, LV8 failed parts at 2/5/10, large-spacing stress (20/40), no-bbox triangle,
kerf independence, solver-path (spacing 10 + kerf 3), and Q36 no-sheet-margin regression.
`technology_spacing_geometry.rs` (10) updated for the robust offset. lib 466/466.

## Smoke results

`scripts/smoke_sgh_q38_robust_spacing_offset.py` — 32/32 PASS (static API/robustness/kerf/
cavity checks + inventory 12/12 at 2/5/10 + LV8 failed-part status + Q37 short rerun
offset_failure_count == 0).

## Remaining risks

- The straight-skeleton buffer cost grows with vertex count; offset build is still ~0.3–0.4 s
  total for the LV8 set (one-time, cached per part) — not a hot-path concern.
- The Q35 spacing final validator (O(n²)) remains the dominant added runtime (Q37 finding),
  now exercised on MORE placed instances since offsets no longer fail.
- f32 dedup relies on f32-equality; extremely fine sub-f32 features could still trip
  `SPolygon` in theory, in which case the part is explicitly unsupported (no silent fallback).

## Recommended next task

Q38 achieves spacing 2/5/10 → 12/12 offsettable on LV8 (and 20/40 too). Recommended next task:
**Q39 / Q37-R1-full — the full 600/1200 s LV8 margin+spacing production benchmark**, now that
offset robustness no longer caps placement. A strong secondary is broad-phase pruning of the
Q35 spacing final validator (the O(n²) runtime hotspot identified in Q37), which becomes more
important as more instances are placed.

## Final verdict

**PASS.** The Q37-blocking parts `Lv8_07919/07920/07921` offset cleanly at spacing 2/5/10; LV8
inventory is 12/12 offsettable at 2/5/10 (and 20/40); spacing 20/40 measured; every accepted
offset is a single valid non-self-intersecting exterior contour; no raw/original or bbox
fallback; kerf never folded into spacing; cavity prepack untouched; Q36 no-sheet-margin and
Q35 final validator intact; Q37 short rerun spacing runs report
`technology_spacing_offset_failure_count == 0`; build/test/smoke/check/verify PASS.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-13T08:44:01+02:00 → 2026-06-13T08:46:24+02:00 (143s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q38_robust_spacing_offset.verify.log`
- git: `main@b3ad574`
- módosított fájlok (git status): 35

**git diff --stat**

```text
 .../outputs/technology_policy_smoke_output.json    |   14 +-
 .../sgh_q34/outputs/sheet_margin_ok_output.json    |    8 +-
 .../outputs/sheet_margin_too_large_output.json     |    8 +-
 .../sgh_q35/outputs/part_spacing_ok_output.json    |   14 +-
 .../outputs/part_spacing_violation_output.json     |   14 +-
 .../outputs/spacing_geometry_touch_ok_output.json  |   14 +-
 .../outputs/spacing_not_sheet_margin_output.json   |   14 +-
 .../outputs/spacing_violation_safety_output.json   |   28 +-
 artifacts/benchmarks/sgh_q37/logs/D0.log           |    2 +-
 artifacts/benchmarks/sgh_q37/logs/D1.log           |    2 +-
 artifacts/benchmarks/sgh_q37/logs/D2.log           |    2 +-
 artifacts/benchmarks/sgh_q37/logs/M0.log           |    2 +-
 artifacts/benchmarks/sgh_q37/logs/M1.log           |    2 +-
 artifacts/benchmarks/sgh_q37/logs/M2.log           |    2 +-
 .../benchmarks/sgh_q37/outputs/D0_output.json      |  955 ++++++------
 .../benchmarks/sgh_q37/outputs/D1_output.json      | 1084 +++++++-------
 .../benchmarks/sgh_q37/outputs/D2_output.json      | 1087 +++++++-------
 .../benchmarks/sgh_q37/outputs/M0_output.json      |   64 +-
 .../benchmarks/sgh_q37/outputs/M1_output.json      | 1563 +++++++++----------
 .../benchmarks/sgh_q37/outputs/M2_output.json      | 1567 ++++++++++----------
 .../benchmarks/sgh_q37/tables/q37_cde_metrics.csv  |   12 +-
 .../sgh_q37/tables/q37_failure_taxonomy.csv        |  870 +++++------
 .../sgh_q37/tables/q37_measurement_manifest.json   |    2 +-
 .../sgh_q37/tables/q37_quality_comparison.csv      |    8 +-
 .../benchmarks/sgh_q37/tables/q37_run_summary.csv  |   12 +-
 .../benchmarks/sgh_q37/tables/q37_stage_timing.csv |   12 +-
 rust/vrs_solver/Cargo.lock                         |    2 +
 rust/vrs_solver/Cargo.toml                         |    5 +
 rust/vrs_solver/src/technology/spacing_geometry.rs |  265 ++--
 29 files changed, 3927 insertions(+), 3707 deletions(-)
```

**git status --porcelain (preview)**

```text
 M artifacts/benchmarks/sgh_q33/outputs/technology_policy_smoke_output.json
 M artifacts/benchmarks/sgh_q34/outputs/sheet_margin_ok_output.json
 M artifacts/benchmarks/sgh_q34/outputs/sheet_margin_too_large_output.json
 M artifacts/benchmarks/sgh_q35/outputs/part_spacing_ok_output.json
 M artifacts/benchmarks/sgh_q35/outputs/part_spacing_violation_output.json
 M artifacts/benchmarks/sgh_q36/outputs/spacing_geometry_touch_ok_output.json
 M artifacts/benchmarks/sgh_q36/outputs/spacing_not_sheet_margin_output.json
 M artifacts/benchmarks/sgh_q36/outputs/spacing_violation_safety_output.json
 M artifacts/benchmarks/sgh_q37/logs/D0.log
 M artifacts/benchmarks/sgh_q37/logs/D1.log
 M artifacts/benchmarks/sgh_q37/logs/D2.log
 M artifacts/benchmarks/sgh_q37/logs/M0.log
 M artifacts/benchmarks/sgh_q37/logs/M1.log
 M artifacts/benchmarks/sgh_q37/logs/M2.log
 M artifacts/benchmarks/sgh_q37/outputs/D0_output.json
 M artifacts/benchmarks/sgh_q37/outputs/D1_output.json
 M artifacts/benchmarks/sgh_q37/outputs/D2_output.json
 M artifacts/benchmarks/sgh_q37/outputs/M0_output.json
 M artifacts/benchmarks/sgh_q37/outputs/M1_output.json
 M artifacts/benchmarks/sgh_q37/outputs/M2_output.json
 M artifacts/benchmarks/sgh_q37/tables/q37_cde_metrics.csv
 M artifacts/benchmarks/sgh_q37/tables/q37_failure_taxonomy.csv
 M artifacts/benchmarks/sgh_q37/tables/q37_measurement_manifest.json
 M artifacts/benchmarks/sgh_q37/tables/q37_quality_comparison.csv
 M artifacts/benchmarks/sgh_q37/tables/q37_run_summary.csv
 M artifacts/benchmarks/sgh_q37/tables/q37_stage_timing.csv
 M rust/vrs_solver/Cargo.lock
 M rust/vrs_solver/Cargo.toml
 M rust/vrs_solver/src/technology/spacing_geometry.rs
?? artifacts/benchmarks/sgh_q38/
?? codex/reports/egyedi_solver/sgh_q38_robust_spacing_offset.md
?? codex/reports/egyedi_solver/sgh_q38_robust_spacing_offset.verify.log
?? rust/vrs_solver/tests/technology_spacing_offset_lv8.rs
?? scripts/bench_sgh_q38_spacing_offset_inventory.py
?? scripts/smoke_sgh_q38_robust_spacing_offset.py
```

<!-- AUTO_VERIFY_END -->
