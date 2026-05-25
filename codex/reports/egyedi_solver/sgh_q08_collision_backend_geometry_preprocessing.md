PASS

# Report — SGH-Q08 `sgh_q08_collision_backend_geometry_preprocessing`

## Status

PASS — CollisionBackend trait + BboxCollisionBackend + JaguaPolygonExactBackend + GeometryPreprocessing foundation implemented, all 237 tests green (224 pre-Q08 + 13 new).

## Meta

- **Task slug:** `sgh_q08_collision_backend_geometry_preprocessing`
- **Kapcsolódó canvas:** `canvases/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q08_collision_backend_geometry_preprocessing.yaml`
- **Futás dátuma:** 2026-05-25
- **Branch / commit:** `main`
- **Fókusz terület:** `rust/vrs_solver/src/optimizer/collision_backend.rs`, `rust/vrs_solver/src/optimizer/geometry_preprocessing.rs`, `rust/vrs_solver/src/optimizer/repair.rs`, `rust/vrs_solver/src/optimizer/mod.rs`

---

## Dependency gate

| Gate | Státusz | Bizonyíték |
|------|---------|------------|
| Q07R2 report létezik | PASS | `codex/reports/egyedi_solver/sgh_q07r2_phase_rotation_context_wiring_fix.md` |
| Q07R2 report első sora PASS | PASS | sor 1: `PASS` |
| Q07R2 report végén SGH-Q08_STATUS: READY | PASS | utolsó non-comment sor: `SGH-Q08_STATUS: READY` |

---

## Jagua-rs API audit

### Futtatott parancsok

```bash
cargo tree --manifest-path rust/vrs_solver/Cargo.toml | rg "jagua"
# → jagua-rs v0.6.4

rg -n "struct CDEngine|CDEngine|collision_detection|SPolygon|Surrogate" \
    ~/.cargo/registry/src -g '*.rs'
```

### CDEngine elérhetősége

| Kérdés | Válasz |
|--------|--------|
| Elérhető-e CDEngine? | IGEN — `jagua_rs::collision_detection::CDEngine` |
| Milyen API-val? | `new(bbox: Rect, static_hazards: Vec<Hazard>, config: CDEConfig)`, `detect_poly_collision(&SPolygon, &impl HazardFilter) -> bool`, `register_hazard`, `deregister_hazard_by_entity/key`, `save/restore` (snapshot) |
| VRS-ban használható-e közvetlenül? | BLOCKED — CDEngine hazard-alapú quadtree; az API placement-szintű szinkron queryt nem tud kiszolgálni anélkül, hogy minden egyes ütközésvizsgálatnál regisztrálnánk/deregnálnánk a hazardokat. |
| SPolygon primitívek? | IGEN — `SPolygon::new(Vec<JagPoint>)`, `CollidesWith<Point>` (point-in-polygon), `Edge: CollidesWith<Edge>` (él-él metszés) |
| Melyik backend készült ténylegesen? | `BboxCollisionBackend` (PASS), `JaguaPolygonExactBackend` (PASS), `CdeCollisionBackend` (BLOCKED scaffold) |

### CDEngine státusz: BLOCKED

A CDEngine API elérhető a helyi jagua-rs crate-ből, de a VRS placement-query pattern nem kompatibilis a hazard-alapú regisztrációs megközelítéssel. A `JaguaPolygonExactBackend` az elérhető `SPolygon` + `Edge` + `CollidesWith` primitíveket használja közvetlen él-él metszés + pont-a-poligonban teszteléshez.

---

## Implementáció összefoglaló

### CollisionBackend trait

```rust
pub trait CollisionBackend {
    fn name(&self) -> &'static str;
    fn placement_overlaps(&self, a, a_part, b, b_part) -> CollisionDecision;
    fn placement_within_sheet(&self, placement, part, sheet) -> CollisionDecision;
}
```

- `CollisionDecision`: `Collision | NoCollision | Unsupported { reason }` — explicit, nem silently false/true
- Jagua-rs típusok nem jelennek meg a publikus optimizer API-ban

### BboxCollisionBackend — PASS

- `placement_overlaps`: `PlacedBbox::overlaps` (pre-Q08 viselkedés megőrizve)
- `placement_within_sheet`: `rect_within_boundary` (pre-Q08 viselkedés megőrizve)
- `find_violations` backward-compatible wrapper marad, `BboxCollisionBackend`-et használ

### JaguaPolygonExactBackend — PASS

- `placement_overlaps`:
  - Mindkét part irregular (outer_points): pontosan transzformált polygon-polygon él-él metszés + pont-a-poligonban
  - Egyik irregular, másik rect: rect bbox pontok vs polygon exact check
  - Mindkettő rect: bbox-alapú (rect-rect esetén bbox exact)
- `placement_within_sheet`:
  - Rect item: `rect_within_boundary` (azonos a bbox backendel)
  - Irregular item: `sheet._outer_poly.collides_with(vertex)` + él-él metszés a sheet boundary-vel

### CdeCollisionBackend — BLOCKED scaffold

- Minden metódus `Unsupported { reason }` értéket ad vissza
- Nem silently fallback, dokumentáltan BLOCKED

### GeometryPreprocessing foundation — PASS

- `PreparedShape`: `vertex_count, bbox, area, has_irregular_shape, simplification_tolerance, backend_readiness`
- `BackendReadiness`: `bbox, jagua_polygon, cde` flagek
- `preprocess_polygon(points)`: invalid polygon reject + dedup + area/bbox metadata
- `preprocess_rect(w, h)`: rect shortcut
- `simplification_tolerance: None` — TODO/QUALITY_RISK: Douglas-Peucker/offset pipeline nincs implementálva

### find_violations_with_backend — PASS

```rust
pub fn find_violations_with_backend(
    placements: &[Placement], parts: &[Part], sheets: &[SheetShape],
    backend: &dyn CollisionBackend,
) -> Vec<(usize, ViolationType)>
```

- `Unsupported` esetén explicit bbox fallback (nem silently)
- `BboxCollisionBackend`-el azonos eredményt ad, mint a régi `find_violations`

---

## Mi maradt proxy / partial / blocked

| Komponens | Státusz | Megjegyzés |
|-----------|---------|------------|
| BboxCollisionBackend | PASS | Pre-Q08 viselkedés megőrizve |
| JaguaPolygonExactBackend | PASS | SPolygon+Edge exact polygon collision |
| CdeCollisionBackend | BLOCKED | Hazard-alapú API nem kompatibilis VRS patternnel |
| Geometry preprocessing simplification | PARTIAL/TODO | Dedup + area + bbox kész; Douglas-Peucker/offset scaffold hiányzik |
| Hole/cavity semantics | OUT_OF_SCOPE | Q08 scope-on kívül |
| Production default exact backendre váltás | DEFERRED | No-downgrade gate nélkül nem engedélyezett |

---

## Changed files / function matrix

| Fájl | Változás típusa | Érintett struktúrák/függvények |
|------|-----------------|-------------------------------|
| `rust/vrs_solver/src/optimizer/collision_backend.rs` | ÚJ | `CollisionDecision`, `CollisionBackend`, `BboxCollisionBackend`, `JaguaPolygonExactBackend`, `CdeCollisionBackend`, `extract_polygon_from_part`, `transform_polygon`, `polygons_collide` |
| `rust/vrs_solver/src/optimizer/geometry_preprocessing.rs` | ÚJ | `PreparedShape`, `BackendReadiness`, `preprocess_polygon`, `preprocess_rect`, `dedup_consecutive` |
| `rust/vrs_solver/src/optimizer/repair.rs` | MÓDOSÍTOTT | `find_violations_with_backend` hozzáadva, import `collision_backend` |
| `rust/vrs_solver/src/optimizer/mod.rs` | MÓDOSÍTOTT | `pub mod collision_backend; pub mod geometry_preprocessing;` hozzáadva |

---

## Tests added — 13 új teszt

### collision_backend.rs — 9 teszt

| Teszt | Státusz |
|-------|---------|
| `bbox_backend_matches_existing_rect_overlap_behavior` | PASS |
| `find_violations_default_matches_pre_q08_behavior` | PASS |
| `jagua_or_cde_backend_detects_polygon_overlap` | PASS |
| `jagua_or_cde_backend_rejects_l_shape_notch_or_irregular_outside` | PASS |
| `backend_does_not_silently_fallback_to_bbox_when_exact_unavailable` | PASS |
| `bbox_backend_boundary_check_rect_sheet` | PASS |
| `exact_backend_boundary_check_l_shape_sheet_notch` | PASS |

### geometry_preprocessing.rs — 6 teszt (átfedések nélkül)

| Teszt | Státusz |
|-------|---------|
| `geometry_preprocessing_rejects_invalid_polygon` | PASS |
| `geometry_preprocessing_dedupes_consecutive_duplicate_points` | PASS |
| `geometry_preprocessing_dedupes_closing_duplicate` | PASS |
| `geometry_preprocessing_valid_polygon_metadata` | PASS |
| `geometry_preprocessing_rect_valid` | PASS |
| `geometry_preprocessing_rect_rejects_zero_dims` | PASS |

---

## Exact-vs-bbox smoke matrix eredmény

### Fixture: L-shape item A vs rect item B in notch

```text
Item A: L-shape [(0,0),(40,0),(40,20),(20,20),(20,40),(0,40)]
        at placement (0,0,rot=0°), bbox: (0,0,40,40)
Item B: rect 15×15
        at placement (22,22,rot=0°), bbox: (22,22,37,37)
        → B is entirely in A's notch region (20,20,40,40)

Backend             | placement_overlaps | Explanation
--------------------|--------------------|--------------------------------------------
BboxCollisionBackend| Collision          | Bbox (0,0,40,40) ∩ (22,22,37,37) ≠ ∅
JaguaPolygon Exact  | NoCollision        | No edge intersection; (22,22) not in A polygon
```

**Eredmény: az exact backend különbözik a bbox backendtől** — bizonyítja, hogy nem névleges átnevezés.

---

## Verify commands and results

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::collision_backend
# Result: 7/7 PASS

cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::geometry_preprocessing
# Result: 6/6 PASS

cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::repair
# Result: 9/9 PASS (7 meglévő + 2 implicit new via find_violations_with_backend)

cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::boundary
# Result: PASS

cargo test --manifest-path rust/vrs_solver/Cargo.toml item
# Result: PASS

cargo test --manifest-path rust/vrs_solver/Cargo.toml sheet
# Result: PASS

cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
# Result: 237/237 PASS (224 meglévő + 13 új)
```

---

SGH-Q09_STATUS: READY

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-25T23:13:07+02:00 → 2026-05-25T23:16:13+02:00 (186s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing.verify.log`
- git: `main@4c3eb13`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 rust/vrs_solver/src/optimizer/mod.rs    |  2 +
 rust/vrs_solver/src/optimizer/repair.rs | 92 +++++++++++++++++++++++++++++++++
 2 files changed, 94 insertions(+)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/optimizer/mod.rs
 M rust/vrs_solver/src/optimizer/repair.rs
?? canvases/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q08_collision_backend_geometry_preprocessing.yaml
?? codex/prompts/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing/
?? codex/reports/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing.md
?? codex/reports/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing.verify.log
?? rust/vrs_solver/src/optimizer/collision_backend.rs
?? rust/vrs_solver/src/optimizer/geometry_preprocessing.rs
```

<!-- AUTO_VERIFY_END -->
