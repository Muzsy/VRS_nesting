PASS

# Report — SGH-Q12 `sgh_q12_cde_engine_api_adaptation_pilot`

## Status

PASS. Genuine jagua-rs CDE collision detection implemented and verified. 300 library tests pass. No bbox fallback, no JaguaPolygonExact fallback.

## Dependency gate

- `codex/reports/egyedi_solver/sgh_q11r_backend_aware_score_consistency_candidate_fix.md`: first line `PASS`
- `SGH-Q12_STATUS: READY`: present

## 1) Meta

- **Task slug:** `sgh_q12_cde_engine_api_adaptation_pilot`
- **Canvas:** `canvases/egyedi_solver/sgh_q12_cde_engine_api_adaptation_pilot.md`
- **Goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q12_cde_engine_api_adaptation_pilot.yaml`
- **Futás dátuma:** 2026-05-27
- **Branch / commit:** main / e2cb691
- **Fókusz terület:** Geometry | Collision Backend

## 2) Scope

### 2.1 Cél

1. Meghatározni, hogy a jagua-rs 0.6.4 CDE API használható-e a VRS-ből.
2. Pilotolni a valódi CDE adaptert: rect + outer polygon overlap/boundary querykkel.
3. Biztosítani, hogy CDE nem fallbackel bboxra vagy JaguaPolygonExactre.
4. Elkészíteni a `cde_adapter.rs` modult és a `CdeCollisionBackend` bekötést.
5. Dokumentálni a lifecycle/teljesítmény korlátokat és a port plan-t.

### 2.2 Nem-cél

- Hole/cavity semantics
- Session-owned CDEngine (production port plan dokumentálva, de nem implementálva)
- SPSurrogate caching
- Production default átkapcsolása CDE-re
- Sparrow teljes port

## 3) API Audit

### cargo tree

```
jagua-rs v0.6.4
```

Jagua-rs közvetlen dependency a `rust/vrs_solver/Cargo.toml`-ban.

### Resolved symbols

| Symbol/API | Path | Visibility | Usable from vrs_solver? | Notes |
|---|---|---|---|---|
| `CDEngine` | `jagua_rs::collision_detection::CDEngine` | `pub struct` | Yes (per-call) | Stateful; requires ≥1 Exterior hazard |
| `CDEngine::detect_poly_collision` | same | `pub fn` | Yes | Edge + containment detection |
| `CDEngine::detect_containment_collision` | same | `pub fn` | Yes | A⊂B and B⊂A via POI center |
| `CDEConfig` | `jagua_rs::collision_detection::CDEConfig` | `pub struct` | Yes | quadtree_depth, cd_threshold, item_surrogate_config |
| `Hazard` | `jagua_rs::collision_detection::hazards::Hazard` | `pub struct` | Yes | `new(entity, shape, dynamic)` |
| `HazardEntity::Exterior` | same | `pub enum variant` | Yes | Scope=Exterior; sheet boundary |
| `HazardEntity::Hole { idx }` | same | `pub enum variant` | Yes | Scope=Interior; placed item pair query |
| `HazardEntity::PlacedItem { pk: PItemKey }` | same | `pub enum variant` | Partial | Requires SlotMap PItemKey — not usable without layout state |
| `NoFilter` | `jagua_rs::collision_detection::hazards::filter::NoFilter` | `pub struct` | Yes | All hazards relevant |
| `SPSurrogateConfig::none()` | `jagua_rs::geometry::fail_fast::SPSurrogateConfig` | `pub fn` | Yes | Zero-surrogate config |
| `SPolygon` | `jagua_rs::geometry::primitives::SPolygon` | `pub struct` | Yes | f32; built via `to_jag_polygon` |
| `Rect` (jagua) | `jagua_rs::geometry::primitives::Rect` | `pub struct` | Yes | `try_new(x_min, y_min, x_max, y_max: f32)` |

### API decision questions

- **Van-e public CDEngine API?** Igen: `CDEngine::new` + `detect_poly_collision` public.
- **Kell-e hazard registration lifecycle?** Per-call workaround: minden querynél újraépítjük a CDEngine-t.
- **Tud-e placement-level synchronous queryt adni?** Igen: `detect_poly_collision`.
- **Tud-e outer polygon + rectangle transformot kezelni?** Igen: `to_jag_polygon` via existing geometry.rs.
- **Mi a minimum surrogate input contract?** `SPSurrogateConfig::none()` elegendő pilothoz.
- **Lifetimes/ownership akadályok?** `HazardEntity::PlacedItem` PItemKey-t igényel — session-owned CDEngine port plan kellene.

## 4) Implementáció

### Új fájl: `rust/vrs_solver/src/optimizer/cde_adapter.rs`

- `CdeAdapterConfig`: quadtree_depth (default 4), cd_threshold (default 0)
- `CdePreparedShape` (pub(crate)): SPolygon + f64 bbox
- `CdeQueryResult`: Collision | NoCollision | Unsupported { reason: &'static str }
- `CdeAdapter::query_pair(a, b)`: Hole hazard approach, per-call CDEngine
- `CdeAdapter::query_boundary(item, sheet)`: Exterior hazard approach
- `prepare_shape_from_placement`: Absent→rect, Valid→transform, Invalid→Err
- `prepare_shape_from_sheet`: rect és irregular sheet

### `rust/vrs_solver/src/optimizer/collision_backend.rs`

- `transform_polygon` → `pub(crate)` (cde_adapter.rs számára)
- `CdeCollisionBackend.name()` → `"cde_adapter"`
- `CdeCollisionBackend.placement_overlaps` → `CdeAdapter::query_pair`
- `CdeCollisionBackend.placement_within_sheet` → `CdeAdapter::query_boundary`
- `backend_does_not_silently_fallback_to_bbox_when_exact_unavailable` → updated: L-notch proof
- `cde_backend_still_returns_unsupported` → renamed: `cde_backend_returns_unsupported_for_invalid_polygon`

### `rust/vrs_solver/src/optimizer/mod.rs`

- `pub mod cde_adapter;` hozzáadva

### `rust/vrs_solver/src/optimizer/repair.rs`

- `backend_validation_reports_unsupported_count` updated: CDE adapter 0 unsupported queries for valid rect parts

## 5) Pair query mechanizmus

```
query_pair(A, B):
  1. union_bbox = union(A.f64_bbox, B.f64_bbox) + 1.0 margin
  2. exterior_spoly = to_jag_polygon(union_bbox corners)
  3. b_hole = Hazard::new(HazardEntity::Hole { idx: 0 }, B.spoly, false)
  4. ext_hz = Hazard::new(HazardEntity::Exterior, exterior_spoly, false)
  5. cde = CDEngine::new(jag_bbox, [ext_hz, b_hole], config)
  6. cde.detect_poly_collision(&A.spoly, &NoFilter)
     true  → Collision
     false → NoCollision
```

A `detect_containment_collision` helyesen kezeli A⊂B és B⊂A eseteket is.

## 6) Szemantikai különbség (CDE vs JaguaPolygonExact)

CDE `Edge::collides_with` `proper_only=false` → kolineáris/érintő élek is Collision.

| Fixture | Bbox | JaguaPolygonExact | CDE |
|---|---|---|---|
| L-shape notch (B in notch) | Collision (false positive) | NoCollision ✓ | NoCollision ✓ |
| Touching rects (shared edge) | NoCollision | NoCollision | Collision (stricter) |
| Overlapping rects | Collision | Collision | Collision |
| Degenerate/invalid polygon | Unsupported | Unsupported | Unsupported |

## 7) Teljesítmény megjegyzés

Per-call CDEngine construction: O(quadtree build) per query. Pilothoz elfogadható.

**Production port plan** (Q13 vagy external task):
1. Session-owned CDEngine per sheet layout
2. Register all items as `HazardEntity::Hole` at phase start
3. Query candidates without rebuilding
4. Reduces O(n × build) → O(n × query)

## 8) Tests

### cde_adapter tesztek (10 db)

```
test optimizer::cde_adapter::tests::cde_api_audit_report_contains_resolved_symbols ... ok
test optimizer::cde_adapter::tests::cde_backend_does_not_fallback_to_bbox_when_unavailable ... ok
test optimizer::cde_adapter::tests::cde_backend_does_not_fallback_to_jagua_polygon_exact_when_unavailable ... ok
test optimizer::cde_adapter::tests::cde_adapter_returns_unsupported_with_clear_reason_if_api_unavailable ... ok
test optimizer::cde_adapter::tests::cde_backend_rect_overlap_query_works_or_is_blocked_explicitly ... ok
test optimizer::cde_adapter::tests::cde_backend_rotated_rect_query_works_or_is_blocked_explicitly ... ok
test optimizer::cde_adapter::tests::cde_backend_irregular_polygon_query_works_or_is_blocked_explicitly ... ok
test optimizer::cde_adapter::tests::cde_backend_invalid_geometry_is_unsupported_not_no_collision ... ok
test optimizer::cde_adapter::tests::cde_boundary_item_inside_rect_sheet_is_no_collision ... ok
test optimizer::cde_adapter::tests::cde_boundary_item_outside_rect_sheet_is_collision ... ok
```

### Összes lib teszt

```
test result: ok. 300 passed; 0 failed; 0 ignored
```

## 9) Verify

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
# → 300 passed, 0 failed

./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q12_cde_engine_api_adaptation_pilot.md
# → see verify.log
```

## 10) DoD Evidence

| DoD | Evidence |
|---|---|
| jagua-rs CDE API audit elvégezve | API audit table (szekció 3), `cde_api_audit_report_contains_resolved_symbols` teszt |
| CDE adapter elkészült (nem bbox, nem JaguaPolygonExact) | `cde_adapter.rs` + L-notch test + touching test |
| No-silent-fallback garantált | `cde_backend_does_not_fallback_*` tesztek, invalid → Unsupported |
| cargo test --lib zöld | 300 passed, 0 failed |
| verify.sh zöld | verify.log |
| Hamis CDE állítás nincs | Per-call CDEngine: valódi CDE query minden esetben |
| Silent fallback nincs | Egyetlen path sem delegál bboxra vagy JaguaPolygonExactre |

## 11) Nem-blokkoló megjegyzések

1. **Per-call CDEngine**: production-ban session-owned CDEngine ajánlott (port plan dokumentálva).
2. **Touching semantics**: CDE szigorúbb (touching=Collision). Meglévő tesztek módosítva a helyes viselkedés tükrözésére.
3. **Hole/cavity**: nem scope, külön task.

SGH-Q13_STATUS: READY

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-27T01:38:28+02:00 → 2026-05-27T01:41:57+02:00 (209s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q12_cde_engine_api_adaptation_pilot.verify.log`
- git: `main@e2cb691`
- módosított fájlok (git status): 11

**git diff --stat**

```text
 rust/vrs_solver/src/optimizer/collision_backend.rs | 125 +++++++++++++--------
 rust/vrs_solver/src/optimizer/mod.rs               |   1 +
 rust/vrs_solver/src/optimizer/repair.rs            |  19 ++--
 3 files changed, 94 insertions(+), 51 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/optimizer/collision_backend.rs
 M rust/vrs_solver/src/optimizer/mod.rs
 M rust/vrs_solver/src/optimizer/repair.rs
?? canvases/egyedi_solver/sgh_q12_cde_engine_api_adaptation_pilot.md
?? codex/codex_checklist/egyedi_solver/sgh_q12_cde_engine_api_adaptation_pilot.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q12_cde_engine_api_adaptation_pilot.yaml
?? codex/prompts/egyedi_solver/sgh_q12_cde_engine_api_adaptation_pilot/
?? codex/reports/egyedi_solver/sgh_q12_cde_engine_api_adaptation_pilot.md
?? codex/reports/egyedi_solver/sgh_q12_cde_engine_api_adaptation_pilot.verify.log
?? docs/egyedi_solver/sgh_q12_cde_engine_adapter_contract.md
?? rust/vrs_solver/src/optimizer/cde_adapter.rs
```

<!-- AUTO_VERIFY_END -->
