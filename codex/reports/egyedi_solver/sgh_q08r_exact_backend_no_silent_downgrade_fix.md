PASS

# Report - SGH-Q08R `sgh_q08r_exact_backend_no_silent_downgrade_fix`

## Status

PASS. The exact backend no-silent-downgrade fixes are implemented and the full repo gate completed successfully.

## Dependency gate

- `codex/reports/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing.md`: first line `PASS`

## Pre-fix audit

| Finding from audit | Fix implemented | Tests proving it | Remaining limitation |
|---|---|---|---|
| `extract_polygon_from_part` returned `Option<Vec<Point>>`, merging absent and invalid polygon data. | Added `PolygonExtraction::{Absent, Invalid, Valid}`. Invalid parse/shape now returns `Unsupported`. | `exact_backend_malformed_outer_points_returns_unsupported_not_bbox_fallback`, `exact_backend_degenerate_polygon_returns_unsupported_not_no_collision`, `invalid_polygon_does_not_become_no_collision` | Exact backend still covers outer polygons only, not holes. |
| `polygons_collide` returned `bool`, so invalid helper state could become false/NoCollision. | Changed `polygons_collide` to `Result<bool, &'static str>` and validate polygons before collision tests. | `exact_backend_degenerate_polygon_returns_unsupported_not_no_collision`, `positive_area_overlap_is_collision` | This is a direct polygon helper, not CDE parity. |
| Exact rect paths used `bbox_from_placement` + AABB rectangle points. | Exact backend now builds world rectangle polygons from `(0,0),(w,0),(w,h),(0,h)` using placement anchor and `rotation_deg`. | `exact_backend_rotated_rect_vs_rect_uses_true_rotated_geometry_not_aabb`, `exact_backend_rotated_rect_vs_irregular_uses_true_rotated_geometry_not_aabb` | Bbox backend intentionally remains AABB/proxy. |
| Exact rect boundary path delegated to bbox boundary behavior. | `JaguaPolygonExactBackend::placement_within_sheet` now uses the same polygon-within-sheet helper for rect and irregular items. | `exact_backend_rect_boundary_check_is_rotation_aware` | Sheet holes remain out of scope. |
| Touching policy was implicit through jagua edge collision semantics. | Added tolerant segment/polygon helpers: shared edge/corner is NoCollision, true crossing/positive-area overlap is Collision. | `touching_rect_edges_are_not_collision`, `touching_rect_corners_are_not_collision`, `positive_area_overlap_is_collision` | Uses VRS-owned tolerant geometry policy for this exact backend scope. |
| CDE scaffold could be mistaken for exact parity. | Contract remains explicit: CDE backend returns `Unsupported`. | `cde_backend_still_returns_unsupported` | Full CDE integration remains blocked/deferred. |

## Post-fix audit

- `bbox_from_placement` remains in `BboxCollisionBackend`, which is intentional and backward-compatible.
- `bbox_to_rect_pts` is removed from exact backend code.
- `collides_with` is no longer used for exact item edge-touch collision decisions.

## Tests run

- `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::collision_backend`: PASS
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::geometry_preprocessing`: PASS
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::repair`: PASS
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`: PASS
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q08r_exact_backend_no_silent_downgrade_fix.md`: PASS

SGH-Q09_STATUS: READY

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-25T23:36:36+02:00 → 2026-05-25T23:39:39+02:00 (183s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q08r_exact_backend_no_silent_downgrade_fix.verify.log`
- git: `main@303264f`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 .../sgh_q08_collision_backend_contract.md          |  37 +-
 rust/vrs_solver/src/optimizer/collision_backend.rs | 546 ++++++++++++++-------
 2 files changed, 404 insertions(+), 179 deletions(-)
```

**git status --porcelain (preview)**

```text
 M docs/egyedi_solver/sgh_q08_collision_backend_contract.md
 M rust/vrs_solver/src/optimizer/collision_backend.rs
?? README_SGH_Q08R_PACKAGE.md
?? canvases/egyedi_solver/sgh_q08r_exact_backend_no_silent_downgrade_fix.md
?? codex/codex_checklist/egyedi_solver/sgh_q08r_exact_backend_no_silent_downgrade_fix.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q08r_exact_backend_no_silent_downgrade_fix.yaml
?? codex/prompts/egyedi_solver/sgh_q08r_exact_backend_no_silent_downgrade_fix/
?? codex/reports/egyedi_solver/sgh_q08r_exact_backend_no_silent_downgrade_fix.md
?? codex/reports/egyedi_solver/sgh_q08r_exact_backend_no_silent_downgrade_fix.verify.log
```

<!-- AUTO_VERIFY_END -->
