# Checklist — SGH-Q08 `sgh_q08_collision_backend_geometry_preprocessing`

## Dependency gate

- [x] SGH-Q07R2 report létezik: `codex/reports/egyedi_solver/sgh_q07r2_phase_rotation_context_wiring_fix.md`
- [x] SGH-Q07R2 report első sora: PASS
- [x] SGH-Q07R2 report végén: `SGH-Q08_STATUS: READY`

## Preflight reads

- [x] AGENTS.md átolvasva
- [x] docs/codex/overview.md átolvasva
- [x] docs/codex/yaml_schema.md átolvasva
- [x] docs/codex/report_standard.md átolvasva
- [x] docs/qa/testing_guidelines.md átolvasva
- [x] docs/egyedi_solver/sgh_q00_quality_feature_gap_matrix.md átolvasva
- [x] docs/egyedi_solver/sgh_q01_corrected_task_roadmap.md átolvasva
- [x] docs/egyedi_solver/sgh_q07_rotation_policy_contract.md átolvasva
- [x] canvases/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing.md átolvasva
- [x] codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q08_collision_backend_geometry_preprocessing.yaml átolvasva

## Kódaudit (pre-Q08)

- [x] `rust/vrs_solver/src/geometry.rs` — to_jag_point, to_jag_polygon, jag_edge_from_points bridge fv-ek jelen vannak
- [x] `rust/vrs_solver/src/optimizer/repair.rs` — `find_violations` bbox/PlacedBbox alapú
- [x] `rust/vrs_solver/src/optimizer/boundary.rs` — `rect_within_boundary` → `rect_inside_sheet_shape`
- [x] `rust/vrs_solver/src/optimizer/candidates.rs` — `PlacedBbox::overlaps` EPS-alapú
- [x] `rust/vrs_solver/src/optimizer/mod.rs` — modulok listája
- [x] `rust/vrs_solver/src/sheet.rs` — `SheetShape._outer_poly: SPolygon`, `has_irregular_outer`
- [x] `rust/vrs_solver/src/item.rs` — `Part.outer_points: Option<JsonValue>`
- [x] `rust/vrs_solver/src/adapter.rs` átolvasva

## Jagua-rs API audit

- [x] `cargo tree | rg jagua` → jagua-rs v0.6.4
- [x] CDEngine elérhető: `jagua_rs::collision_detection::CDEngine`
- [x] CDEngine API: `new`, `detect_poly_collision`, `register_hazard`, `save/restore`
- [x] CDEngine VRS-ban BLOCKED: hazard-regisztrációs API nem kompatibilis szinkron placement-query patternnel
- [x] SPolygon primitívek: `SPolygon::new`, `CollidesWith<Point>`, `Edge: CollidesWith<Edge>`
- [x] Report tartalmazza az audit eredményét

## Implementáció

### collision_backend.rs (ÚJ)

- [x] `CollisionDecision` enum: Collision, NoCollision, Unsupported { reason }
- [x] `CollisionBackend` trait: name(), placement_overlaps(), placement_within_sheet()
- [x] Jagua-rs típusok NEM szivárognak a publikus optimizer API-ba
- [x] `BboxCollisionBackend`: pre-Q08 viselkedés megőrizve (PlacedBbox::overlaps + rect_within_boundary)
- [x] `JaguaPolygonExactBackend`: exact polygon-polygon él-él + pont-a-poligonban (SPolygon+Edge)
  - [x] Part outer_points parsing JSON-ból (array-of-[x,y])
  - [x] transform_polygon: anchor + rotation alkalmazás
  - [x] polygons_collide: edge-edge + point-in-polygon
  - [x] Rect-rect fallback: bbox (exact rect esetén)
- [x] `CdeCollisionBackend`: scaffold, minden metódus Unsupported (BLOCKED dokumentálva)

### geometry_preprocessing.rs (ÚJ)

- [x] `BackendReadiness`: bbox, jagua_polygon, cde flagek
- [x] `PreparedShape`: vertex_count, bbox, area, has_irregular_shape, simplification_tolerance, backend_readiness
- [x] `preprocess_polygon`: invalid reject, dedup consecutive, closing dedup, area/bbox metadata
- [x] `preprocess_rect`: rect shortcut, valid dims check
- [x] `simplification_tolerance: None` — QUALITY_RISK TODO dokumentálva

### repair.rs (MÓDOSÍTOTT)

- [x] `find_violations_with_backend(placements, parts, sheets, backend: &dyn CollisionBackend)` hozzáadva
- [x] Unsupported esetén explicit bbox fallback (nem silently)
- [x] `find_violations` változatlan (backward-compatible)
- [x] Import: `use super::collision_backend::{CollisionBackend, CollisionDecision};`

### mod.rs (MÓDOSÍTOTT)

- [x] `pub mod collision_backend;` hozzáadva
- [x] `pub mod geometry_preprocessing;` hozzáadva

## Kötelező tesztek

| Teszt | Hol | Státusz |
|-------|-----|---------|
| `bbox_backend_matches_existing_rect_overlap_behavior` | collision_backend | PASS |
| `find_violations_default_matches_pre_q08_behavior` | collision_backend | PASS |
| `jagua_or_cde_backend_detects_polygon_overlap` | collision_backend | PASS |
| `jagua_or_cde_backend_rejects_l_shape_notch_or_irregular_outside` | collision_backend | PASS |
| `geometry_preprocessing_rejects_invalid_polygon` | geometry_preprocessing | PASS |
| `geometry_preprocessing_dedupes_consecutive_duplicate_points` | geometry_preprocessing | PASS |
| `backend_does_not_silently_fallback_to_bbox_when_exact_unavailable` | collision_backend | PASS |

## Smoke / benchmark gate

- [x] L-shape item A vs rect item B in notch fixture
- [x] BboxCollisionBackend → Collision (false positive, expected)
- [x] JaguaPolygonExactBackend → NoCollision (exact, B in notch)
- [x] Eredmény: exact backend ≠ bbox backend → bizonyított különbség

## Verification

- [x] `cargo test optimizer::collision_backend` → 7/7 PASS
- [x] `cargo test optimizer::geometry_preprocessing` → 6/6 PASS
- [x] `cargo test optimizer::repair` → PASS
- [x] `cargo test optimizer::boundary` → PASS
- [x] `cargo test item` → PASS
- [x] `cargo test sheet` → PASS
- [x] `cargo test --lib` → 237/237 PASS (224 pre-Q08 + 13 új)
- [x] `./scripts/verify.sh --report ...` → PASS (AUTO_VERIFY szekció)

## No-scope-violation gate

- [x] Hole/cavity semantics: NEM módosítva
- [x] DXF/preflight: NEM módosítva
- [x] Új optimizer stratégia: NEM bevezetve
- [x] BPP/sheet elimination refaktor: NEM módosítva
- [x] Rotation policy újratervezés: NEM módosítva
- [x] LossModel átírás: NEM módosítva
- [x] Production default exact backendre váltás: DEFERRED (no-downgrade gate nélkül)
- [x] CDEngine-ként adott el bbox fallbacket: NEM (CdeCollisionBackend → Unsupported)

## Documentation

- [x] `codex/codex_checklist/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing.md` elkészült
- [x] `docs/egyedi_solver/sgh_q08_collision_backend_contract.md` elkészült
- [x] `codex/reports/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing.md` elkészült (első sor: PASS)
- [x] `codex/reports/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing.verify.log` elkészült
