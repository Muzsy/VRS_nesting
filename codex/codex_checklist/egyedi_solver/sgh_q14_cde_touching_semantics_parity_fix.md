# Checklist — SGH-Q14 CDE touching semantics parity fix

## Dependency gate

- [x] `codex/reports/egyedi_solver/sgh_q13_cde_session_backend_search_path_wiring.md` first line: `PASS`
- [x] Q13 report contains `SGH-Q14_STATUS: READY`

## Audit

- [x] `Edge::collides_with(proper_only=false)` confirmed — raw CDE counts touching as Collision
- [x] VRS/Q08R policy identified: touching = NoCollision, positive-area overlap = Collision
- [x] `polygons_collide` uses `segments_properly_intersect` (proper crossing only) confirmed
- [x] `polygon_within_sheet` uses strict-inside semantics (boundary touch OK) confirmed

## CDE post-policy (`cde_adapter.rs`)

- [x] `CdePreparedShape.world_pts` field added — f64 world-coord vertices for post-policy
- [x] `prepare_shape_from_placement` stores `world_pts`
- [x] `prepare_shape_from_sheet` stores `world_pts`
- [x] `query_pair` post-policy: CDE NoCollision → NoCollision fast path; CDE Collision → `polygons_collide` check
- [x] `query_boundary` post-policy: CDE NoCollision → NoCollision fast path; CDE Collision → `polygon_within_sheet_pts` check
- [x] Unsupported propagated correctly when geometry helper returns `Err`

## Geometry helpers (`collision_backend.rs`)

- [x] `polygons_collide` made `pub(crate)`
- [x] `polygon_within_sheet_pts` new function: all item pts inside-or-on sheet, no proper crossing
- [x] `segments_properly_intersect` used for proper crossing (not collinear/touching)
- [x] `point_inside_or_on_polygon` used for boundary-inclusive containment

## No-regression

- [x] Bbox arm untouched
- [x] JaguaPolygonExact arm untouched
- [x] `moves.rs` regression test updated (boundary touch now correctly NoCollision)
- [x] `sheet_elimination.rs` regression test updated (boundary touch now correctly NoCollision)

## Required tests (13/13 passing)

- [x] `cde_touching_rect_edges_are_no_collision`
- [x] `cde_touching_rect_corners_are_no_collision`
- [x] `cde_positive_rect_overlap_is_collision`
- [x] `cde_touching_irregular_polygon_edges_are_no_collision`
- [x] `cde_positive_irregular_overlap_is_collision`
- [x] `cde_item_touching_sheet_boundary_inside_is_no_collision`
- [x] `cde_item_corner_touching_sheet_boundary_inside_is_no_collision`
- [x] `cde_item_crossing_sheet_boundary_is_collision`
- [x] `cde_separator_candidate_loss_touching_layout_is_zero`
- [x] `cde_separator_candidate_loss_positive_overlap_is_positive`
- [x] `bbox_default_touching_semantics_unchanged`
- [x] `jagua_polygon_exact_touching_semantics_unchanged`
- [x] `no_silent_bbox_fallback_for_cde_touching_policy`

## Verify

- [x] `cargo test --lib` → 323 passed, 0 failed
- [x] `./scripts/verify.sh --report ...` → PASS
