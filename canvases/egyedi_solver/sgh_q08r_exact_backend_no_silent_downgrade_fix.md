# SGH-Q08R — Exact backend no-silent-downgrade fix

## Státusz

Repair task az SGH-Q08 után.

## Előfeltétel

Az SGH-Q08 report létezzen és első sora legyen `PASS`:

```text
codex/reports/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing.md
```

A Q08 reportban szerepelhet `SGH-Q09_STATUS: READY`, de ezt a Q08R audit felülbírálja: Q09 csak Q08R PASS után indulhat.

## Miért kell javítani?

Az SGH-Q08 jó backend-vázat adott, de kódszinten az exact backend még több helyen minőségi kockázatot hordoz:

```text
rust/vrs_solver/src/optimizer/collision_backend.rs
- extract_polygon_from_part(...) Option<Vec<Point>> értéket ad, ezért nem különbözteti meg:
  Absent polygon vs Invalid polygon.
- malformed outer_points/prepared_outer_points esetén a JaguaPolygonExactBackend bbox/rect fallbackre eshet.
- polygons_collide(...) bool értéket ad; invalid/degenerate edge/SPolygon build esetén false lehet, ami hamis NoCollision.
- rect-vs-irregular és rect-vs-rect exact útvonal bbox_from_placement(...) + bbox_to_rect_pts(...) alapján épít polygont.
  Q07 után 45°/continuous rotation mellett ez AABB-proxy, nem valós rotált téglalap.
- touching semantics nincs tesztelve; bbox backend touching = NoCollision, exact edge.collides_with lehet, hogy touchingot Collisionnek vesz.
```

Ez sérti az SGH-Q00/Q01 no-downgrade szabályt: exact/CDE név alatt nem maradhat rejtett bbox vagy silent false/NoCollision fallback.

## Cél

A Q08R célja nem új backend, hanem a Q08 exact backend szerződésének szigorítása:

```text
1. outer polygon extraction legyen háromállapotú:
   - Absent: nincs irregular polygon adat, rect fallback jogos
   - Invalid(reason): van irregular polygon adat, de hibás/degenerált; exact backend -> Unsupported
   - Valid(Vec<Point>): exact polygon path

2. exact collision helper ne tudjon invalid geometriából hamis NoCollisiont adni.
   Invalid edge/SPolygon/degenerate geometry -> Unsupported.

3. rect polygon helper valós rotált rectangle sarkokat adjon vissza placement.rotation_deg alapján.
   Exact backendben tilos AABB-t használni rect geometriaként.

4. touching policy legyen explicit és tesztelt:
   bbox-kompatibilis alap: shared edge / shared point / just-touching boundary = NoCollision,
   positive-area overlap / true crossing / outside = Collision.

5. contract/report pontosítás:
   JaguaPolygonExactBackend csak a támogatott polygon/rect outer-boundary scope-ban exact.
   Holes/cavity/CDE továbbra is out-of-scope vagy BLOCKED.
```

## Scope

### Engedélyezett production fájlok

```text
rust/vrs_solver/src/optimizer/collision_backend.rs
rust/vrs_solver/src/optimizer/geometry_preprocessing.rs      # csak ha helper/enum reuse miatt szükséges
rust/vrs_solver/src/optimizer/repair.rs                      # csak Unsupported handling regression miatt, ha indokolt
rust/vrs_solver/src/optimizer/mod.rs                         # csak modul/export miatt, ha indokolt
rust/vrs_solver/src/geometry.rs                              # csak robust geometry helper miatt, ha indokolt
```

### Engedélyezett artefaktok

```text
canvases/egyedi_solver/sgh_q08r_exact_backend_no_silent_downgrade_fix.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q08r_exact_backend_no_silent_downgrade_fix.yaml
codex/prompts/egyedi_solver/sgh_q08r_exact_backend_no_silent_downgrade_fix/run.md
codex/codex_checklist/egyedi_solver/sgh_q08r_exact_backend_no_silent_downgrade_fix.md
codex/reports/egyedi_solver/sgh_q08r_exact_backend_no_silent_downgrade_fix.md
codex/reports/egyedi_solver/sgh_q08r_exact_backend_no_silent_downgrade_fix.verify.log
docs/egyedi_solver/sgh_q08_collision_backend_contract.md
```

### Tiltott scope

```text
CDEngine teljes integráció
hole/cavity semantics
DXF/preflight nagy refaktor
production default exact backendre váltása
új optimizer stratégia
rotation policy újratervezés
LossModel / separator / phase orchestration refaktor
```

## Kötelező pre-audit

Olvasd el:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
docs/egyedi_solver/sgh_q00_quality_feature_gap_matrix.md
docs/egyedi_solver/sgh_q01_corrected_task_roadmap.md
docs/egyedi_solver/sgh_q08_collision_backend_contract.md
canvases/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing.md
codex/reports/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing.md
rust/vrs_solver/src/optimizer/collision_backend.rs
rust/vrs_solver/src/optimizer/geometry_preprocessing.rs
rust/vrs_solver/src/optimizer/repair.rs
```

Futtasd és dokumentáld a reportban:

```bash
rg -n "extract_polygon_from_part|parse_points_json|polygons_collide|bbox_to_rect_pts|bbox_from_placement|collides_with" rust/vrs_solver/src/optimizer/collision_backend.rs
rg -n "JaguaPolygonExactBackend|CdeCollisionBackend|find_violations_with_backend" docs/egyedi_solver/sgh_q08_collision_backend_contract.md codex/reports/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing.md
```

## Kötelező javítások

### 1. Polygon extraction háromállapotú legyen

Cseréld le az `Option<Vec<Point>>` contractot valami ilyen repo-stílusú típusra:

```rust
pub(crate) enum PolygonExtraction {
    Absent,
    Invalid { reason: &'static str },
    Valid(Vec<Point>),
}
```

Elvárt viselkedés:

```text
outer_points/prepared_outer_points mindkettő None -> Absent
van outer_points vagy prepared_outer_points, de parse/shape invalid -> Invalid
valid >= 3, nem degenerált polygon -> Valid
```

Fontos:

```text
Absent esetben rect fallback jogos.
Invalid esetben JaguaPolygonExactBackend minden érintett queryre Unsupported-ot adjon.
Invalid soha ne essen bbox fallbackre vagy NoCollisionra.
```

A `preprocess_polygon(...)` meglévő logikáját érdemes újrahasználni, hogy a validáció egységes legyen.

### 2. Exact collision helper ne bool legyen, ha hibázhat

A `polygons_collide(a,b) -> bool` contract nem elég.

Alakítsd át úgy, hogy hibát is tudjon jelezni, például:

```rust
fn polygons_collide(...) -> Result<bool, &'static str>
```

vagy közvetlenül:

```rust
fn polygons_collide(...) -> CollisionDecision
```

Elvárt viselkedés:

```text
valid geometry + positive overlap/crossing -> Collision
valid geometry + no positive overlap -> NoCollision
invalid/degenerate geometry vagy SPolygon/Edge build failure -> Unsupported
```

Tilos invalid geometriából `false` / `NoCollision`.

### 3. Rotated rectangle polygon helper

Exact backendben ne használd a `bbox_from_placement(...)` + `bbox_to_rect_pts(...)` párost rect alakgeometriaként.

Legyen helper:

```rust
fn rect_polygon_from_placement(placement: &Placement, width: f64, height: f64) -> Result<[Point; 4], &'static str>
```

vagy `Vec<Point>` visszatéréssel.

Elvárt geometria:

```text
local rect: (0,0), (w,0), (w,h), (0,h)
rotation: placement.rotation_deg körül a local origin / placement anchor szerint, azonosan a transform_polygon(...) logikával
translation: placement.x, placement.y
```

Exact backendben rect-vs-irregular, irregular-vs-rect és rect-vs-rect is ezt használja.

A BboxCollisionBackend maradhat AABB/bbox, mert az a backward-compatible proxy backend.

### 4. Boundary check exact rect esetben is rotation-aware legyen

`JaguaPolygonExactBackend::placement_within_sheet(...)` rect item esetén ne `rect_within_boundary(...)`-t használjon, ha a placement rotation nem tengelyigazított.

Elvárt:

```text
Absent polygon -> rect_polygon_from_placement(...) világpontok
Valid irregular polygon -> transform_polygon(...)
Invalid polygon -> Unsupported
```

Ezután ugyanaz a polygon-within-sheet helper fusson:

```text
- minden item vertex bent vagy boundary-n legyen
- item edge ne lépjen ki / ne metssze pozitív crossinggal a sheet boundaryt
- touching boundary engedett, ha a bbox policy is ezt tekinti NoCollisionnek
```

### 5. Touching policy explicit és tesztelt legyen

Ne hagyd implicit jagua edge-collision szemantikára.

Minimum követelmény:

```text
- rect A x=[0,10], rect B x=[10,20], közös él -> NoCollision
- közös sarok -> NoCollision
- nagyon kicsi pozitív overlap -> Collision
- irregular polygon boundary érintése sheet szélén -> NoCollision, ha teljesen bent van
- item edge valódi crossinggal kilóg -> Collision
```

Használhatsz saját toleráns segment helper(eke)t, ha a jagua `Edge.collides_with` touchingot is collisionnek veszi. A döntési szemantika fontosabb, mint az, hogy minden edge check közvetlenül jagua primitive legyen.

### 6. Contract/report pontosítás

Frissítsd:

```text
docs/egyedi_solver/sgh_q08_collision_backend_contract.md
```

Tisztázd:

```text
JaguaPolygonExactBackend status: PARTIAL/PASS for supported outer-boundary polygon/rectangle collision.
Nem teljes CDE parity.
Nem hole-aware.
No silent fallback: Invalid exact geometry -> Unsupported.
Rect exact path rotation-aware.
Touching policy: no positive-area overlap = NoCollision.
```

A Q08R reportban külön táblázd:

```text
Finding from audit
Fix implemented
Tests proving it
Remaining limitation
```

## Kötelező tesztek

Adj célzott Rust teszteket, minimum ezekkel a nevekkel vagy nagyon közeli megfelelőkkel:

```text
exact_backend_malformed_outer_points_returns_unsupported_not_bbox_fallback
exact_backend_degenerate_polygon_returns_unsupported_not_no_collision
exact_backend_rotated_rect_vs_rect_uses_true_rotated_geometry_not_aabb
exact_backend_rotated_rect_vs_irregular_uses_true_rotated_geometry_not_aabb
exact_backend_rect_boundary_check_is_rotation_aware
touching_rect_edges_are_not_collision
touching_rect_corners_are_not_collision
positive_area_overlap_is_collision
invalid_polygon_does_not_become_no_collision
```

Backward compatibility:

```text
bbox backend tesztek maradjanak zöldek
find_violations default továbbra is BboxCollisionBackend wrapper
CdeCollisionBackend továbbra is Unsupported scaffold
```

## Verify

Futtasd legalább:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::collision_backend
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::geometry_preprocessing
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::repair
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q08r_exact_backend_no_silent_downgrade_fix.md
```

Ha bármelyik fail, report első sora `REVISE` vagy `BLOCKED`, és nincs `SGH-Q09_STATUS: READY`.

## PASS feltételek

PASS csak akkor lehet, ha:

```text
- Invalid exact geometry soha nem fallbackel bboxra.
- Invalid exact geometry soha nem lesz NoCollision.
- Exact backend rect geometriája rotation-aware.
- Touching policy explicit és tesztelt.
- Bbox default backward compatibility megmarad.
- Q08 contract doksi javítva.
- cargo test --lib és verify zöld.
```

PASS esetén a report vége:

```text
SGH-Q09_STATUS: READY
```
