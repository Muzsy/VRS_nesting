# SGH-Q34-R1 Report

## Scope

Q34-R1 fixes two correctness defects in the Q34 sheet-margin enforcement, without
changing the feature surface. No solver search, spacing, kerf, cavity, or compression
changes. Two fixes only:

1. The final margin validator now checks the **full transformed part polygon**, not a
   rotated bounding box derived from `part.width × part.height`.
2. A margin violation now guarantees the **top-level `SolverOutput.status` cannot be `ok`**
   (violating placements are removed and moved to `unplaced`).

## Existing Q34 audit finding

Q34 used rotated bbox for final margin validation. Q34-R1 replaces that with actual
transformed part polygon containment.

Concretely, two defects were found in the Q34 implementation:

- **Bbox validator:** `count_sheet_margin_violations` used
  `rotated_bbox_min_offset_f64` / `dims_for_rotation_f64` on `part.width`/`part.height`.
  For a part with a small `outer_points` polygon but a large declared bbox (e.g. a
  triangle inside a 100×100 declared box), the bbox check would wrongly flag a placement
  that is actually inside the margin-inset region.
- **Lost status downgrade:** the adapter set `result.status = "partial"` on violation, but
  the top-level `SolverOutput.status` is recomputed later as
  `if unplaced.is_empty() { "ok" } else { "partial" }`. With a violation but no unplaced
  entry, the output could still become `ok`.

## Polygon validator implementation

New `sheet.rs::find_sheet_margin_violations(placements, parts, original_sheets, margin_mm)
-> Vec<String>` returns the violating `instance_id`s. `count_sheet_margin_violations`
is kept as a thin `.len()` wrapper for backward compatibility.

For each placement it:
1. Finds the `Part` by `part_id`.
2. Extracts the **local part polygon** using the *same* canonical helper the CDE/Sparrow
   placement path uses — `crate::optimizer::collision_backend::extract_polygon_from_part`
   (precedence: `prepared_outer_points` → `outer_points`). Rectangle fallback
   `[(0,0),(w,0),(w,h),(0,h)]` is used **only** when the part has no polygon (`Absent`).
   A malformed polygon (`Invalid`) is treated conservatively as a violation.
3. Transforms the local polygon with the canonical `transform_polygon(local, x, y,
   rotation_deg)` — rotation about the local origin, then translation by the placement
   anchor. No new coordinate convention is introduced.
4. Checks that **every transformed vertex** lies inside the margin-inset rectangle
   `[min_x+m, min_y+m, max_x−m, max_y−m]` (within `EPS`). Because the container is a convex
   rectangle, vertex containment implies full-polygon containment.

The validator no longer references `rotated_bbox_min_offset_f64` / `dims_for_rotation_f64`.

## Status safety-net fix

New `adapter.rs::apply_margin_violation_safety_net(placements, unplaced,
violating_instance_ids) -> (placements, unplaced)`: removes every violating placement and
appends it to `unplaced` with reason `SHEET_MARGIN_VIOLATION_Q34R1`.

In `run_sparrow_finite_stock_multisheet_pipeline`, when `find_sheet_margin_violations`
returns a non-empty list the adapter:
- removes the violating placements and moves them to `unplaced` via the helper;
- sets `result.status = "partial"`, `result.best_full_solution_found = false`;
- updates `placed_instances` / `unplaced_instances`.

Because the violating instances are now in `unplaced`, the later top-level
`status = if unplaced.is_empty() { "ok" } else { "partial" }` computation can no longer
yield `ok`. The guarantee `technology_margin_violation_count > 0 ⇒ top-level status != ok`
holds structurally, not just in a diagnostics field.

## Tests

`rust/vrs_solver/tests/technology_sheet_margin.rs` (15 tests total; 6 new for R1):

| Test | Proves |
|---|---|
| `polygon_inside_declared_bbox_outside_no_violation` | **Key regression**: triangle polygon inside inset, declared 100×100 bbox outside → 0 violations (fails with a bbox validator) |
| `polygon_actually_violates_margin` | Triangle at (75,75) → world max 95 > 90 → 1 violation |
| `rotated_polygon_containment` | 45°-rotated triangle: inside → none; vertex crossing inset → violation |
| `rectangle_fallback_still_works` | No `outer_points` → rect fallback; inside none, outside one |
| `zero_margin_no_violations` | margin 0 → validator no-op |
| (existing Q34 tests) | shrink math, too-large/irregular errors, full-run placement, backwards compat |

`rust/vrs_solver/src/adapter.rs` inline unit tests (2 new):

| Test | Proves |
|---|---|
| `margin_safety_net_moves_violating_to_unplaced` | violating placement removed; appears in `unplaced` with `SHEET_MARGIN_VIOLATION_Q34R1`; `unplaced` non-empty ⇒ status cannot be ok |
| `margin_safety_net_noop_when_no_violations` | empty violation list is a no-op |

Results: lib 457/457 (incl. 2 new), Q33 9/9, Q34 15/15.

## Smoke results

`scripts/smoke_sgh_q34_sheet_margin_enforcement.py` — **41/41 PASS**.

New R1 static checks: `find_sheet_margin_violations` exists; no "rotated bounding box"
final-validator language; validator does not use bbox helpers; validator uses
`extract_polygon_from_part` + `transform_polygon`; `SHEET_MARGIN_VIOLATION_Q34R1` reason
present; adapter uses the violation list (not just count); adapter applies the safety net;
status forced to partial; polygon regression test names present. New R1 dynamic check:
`cargo test --test technology_sheet_margin` runs and passes (soft-skips if cargo absent).

Synthetic `sheet_margin_ok`: ok, 2 placed, 0 violations, usable 6400 / physical 10000, all
placements inside [10,90]. `sheet_margin_too_large`: partial, 0 placed, 1 unplaced.

## Q32/Q33 regression checks

- `scripts/smoke_sgh_q33_technology_clearance_policy.py` → **43/43 PASS**.
- `scripts/smoke_sgh_q32_finite_stock_multisheet.py` → **PASS=89 FAIL=0**.

Q33 policy diagnostics, Q32 finite-stock pipeline, Q31 base-shape cache, and the
no-compression / no-legacy guards are all intact.

## Non-goals

- No part-part spacing enforcement.
- No kerf-expanded geometry.
- No polygon offset engine.
- No cavity prepack.
- No lead-in/out handling.
- No solver search tuning.

`spacing_mm` and `kerf_mm` remain diagnostic-only.

## Final verdict

**PASS.** All acceptance criteria met:

- Final margin validation runs on the full transformed part polygon.
- For `outer_points` / `prepared_outer_points` parts it does **not** decide on the
  width×height bbox; rectangle fallback is used only for parts without a polygon.
- Margin violations remove placements and force top-level status away from `ok`; violating
  placements never survive in a valid `ok` output.
- `SHEET_MARGIN_VIOLATION_Q34R1` appears on the safety-net path.
- Q34 synthetic ok and too-large cases still behave correctly.
- Q33 and Q32 smokes still PASS.
- No spacing/kerf/cavity/compression/legacy regression.
- build / lib (457) / Q33 (9) / Q34 (15) / smokes (Q34 41, Q33 43, Q32 89) / check.sh / verify.sh all PASS.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-11T12:54:43+02:00 → 2026-06-11T12:57:06+02:00 (143s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q34_r1_sheet_margin_polygon_validator_fix.verify.log`
- git: `main@e8f1549`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 .../outputs/technology_policy_smoke_output.json    |   4 +-
 .../sgh_q34/outputs/sheet_margin_ok_output.json    |   4 +-
 .../outputs/sheet_margin_too_large_output.json     |   4 +-
 rust/vrs_solver/src/adapter.rs                     | 104 ++++++++++++++--
 rust/vrs_solver/src/sheet.rs                       |  99 ++++++++++-----
 rust/vrs_solver/tests/technology_sheet_margin.rs   | 134 ++++++++++++++++++++-
 scripts/smoke_sgh_q34_sheet_margin_enforcement.py  |  65 +++++++++-
 7 files changed, 361 insertions(+), 53 deletions(-)
```

**git status --porcelain (preview)**

```text
 M artifacts/benchmarks/sgh_q33/outputs/technology_policy_smoke_output.json
 M artifacts/benchmarks/sgh_q34/outputs/sheet_margin_ok_output.json
 M artifacts/benchmarks/sgh_q34/outputs/sheet_margin_too_large_output.json
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/sheet.rs
 M rust/vrs_solver/tests/technology_sheet_margin.rs
 M scripts/smoke_sgh_q34_sheet_margin_enforcement.py
?? codex/reports/egyedi_solver/sgh_q34_r1_sheet_margin_polygon_validator_fix.md
?? codex/reports/egyedi_solver/sgh_q34_r1_sheet_margin_polygon_validator_fix.verify.log
```

<!-- AUTO_VERIFY_END -->
