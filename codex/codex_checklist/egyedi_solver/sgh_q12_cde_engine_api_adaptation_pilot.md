# Checklist — SGH-Q12 CDEngine API adaptation pilot

## Dependency gate

- [x] `codex/reports/egyedi_solver/sgh_q11r_backend_aware_score_consistency_candidate_fix.md`: first line `PASS`
- [x] `SGH-Q12_STATUS: READY` present in Q11R report

## API audit

- [x] `cargo tree` confirms jagua-rs 0.6.4 is a direct dependency
- [x] `rg` resolved all required symbols: `CDEngine`, `CDEConfig`, `Hazard`, `HazardEntity`, `NoFilter`, `SPSurrogateConfig`, `SPolygon`, `Rect`
- [x] API audit table present in report (symbol / path / visibility / usable / notes)
- [x] CDEngine lifecycle and ownership constraints documented
- [x] Semantic difference vs JaguaPolygonExact documented (touching edges = Collision in CDE)

## Implementation

- [x] `rust/vrs_solver/src/optimizer/cde_adapter.rs` created
- [x] `CdeAdapterConfig` struct (quadtree_depth, cd_threshold, default impl)
- [x] `CdePreparedShape` struct (SPolygon + f64 bbox, pub(crate))
- [x] `CdeQueryResult` enum (Collision | NoCollision | Unsupported { reason })
- [x] `CdeAdapter::query_pair` — genuine per-call CDEngine, B as Hole hazard
- [x] `CdeAdapter::query_boundary` — sheet as Exterior hazard
- [x] `prepare_shape_from_placement` — handles Absent (rect), Valid, Invalid
- [x] `prepare_shape_from_sheet` — handles rect and irregular sheet shapes
- [x] `pub mod cde_adapter;` added to `optimizer/mod.rs`
- [x] `transform_polygon` made `pub(crate)` in collision_backend.rs
- [x] `CdeCollisionBackend.name()` → `"cde_adapter"` (was `"cde_scaffold_blocked"`)
- [x] `CdeCollisionBackend.placement_overlaps` → uses CdeAdapter::query_pair
- [x] `CdeCollisionBackend.placement_within_sheet` → uses CdeAdapter::query_boundary
- [x] No bbox fallback — Unsupported returned for invalid geometry only
- [x] No JaguaPolygonExact fallback — CDE uses real CDEngine, semantics differ

## No-silent-fallback guarantees

- [x] Invalid polygon → prepare_shape_from_placement returns Err → Unsupported
- [x] Rect parts (no outer_points) → CDE uses rect polygon → Collision or NoCollision
- [x] Touching items: CDE returns Collision, JaguaPolygonExact returns NoCollision (documented semantic difference)
- [x] L-shape notch: CDE returns NoCollision (correct), Bbox returns Collision (false positive)

## Required tests (8 minimum)

- [x] `cde_api_audit_report_contains_resolved_symbols` (compile-time symbol resolution)
- [x] `cde_backend_does_not_fallback_to_bbox_when_unavailable` (L-notch: CDE ≠ Bbox)
- [x] `cde_backend_does_not_fallback_to_jagua_polygon_exact_when_unavailable` (touching: CDE ≠ JaguaPolygonExact)
- [x] `cde_adapter_returns_unsupported_with_clear_reason_if_api_unavailable` (malformed polygon)
- [x] `cde_backend_rect_overlap_query_works_or_is_blocked_explicitly` (overlapping rects → Collision)
- [x] `cde_backend_rotated_rect_query_works_or_is_blocked_explicitly` (rotated vs far → NoCollision)
- [x] `cde_backend_irregular_polygon_query_works_or_is_blocked_explicitly` (L-shape notch → NoCollision)
- [x] `cde_backend_invalid_geometry_is_unsupported_not_no_collision` (degenerate polygon → Unsupported)

## Additional tests

- [x] `cde_boundary_item_inside_rect_sheet_is_no_collision`
- [x] `cde_boundary_item_outside_rect_sheet_is_collision`
- [x] `backend_does_not_silently_fallback_to_bbox_when_exact_unavailable` (updated in collision_backend.rs)
- [x] `cde_backend_returns_unsupported_for_invalid_polygon` (updated in collision_backend.rs)
- [x] `backend_validation_reports_unsupported_count` (updated in repair.rs: now asserts 0 unsupported for valid rect parts)

## Updated existing tests

- [x] `backend_does_not_silently_fallback_to_bbox_when_exact_unavailable` — updated to test CDE ≠ Bbox via L-notch fixture
- [x] `cde_backend_still_returns_unsupported` → renamed to `cde_backend_returns_unsupported_for_invalid_polygon`
- [x] `backend_validation_reports_unsupported_count` — updated: CDE succeeds for rect parts (0 unsupported)

## Verification

- [x] `cargo test --lib`: 300 passed, 0 failed
- [x] `./scripts/verify.sh --report ...`: see verify.log
- [x] No bbox fallback CDE claim
- [x] No JaguaPolygonExact rename CDE claim
- [x] No production default switched to CDE

## Contract + report

- [x] `docs/egyedi_solver/sgh_q12_cde_engine_adapter_contract.md` created
- [x] `codex/reports/egyedi_solver/sgh_q12_cde_engine_api_adaptation_pilot.md` created
- [x] `codex/reports/egyedi_solver/sgh_q12_cde_engine_api_adaptation_pilot.verify.log` created
