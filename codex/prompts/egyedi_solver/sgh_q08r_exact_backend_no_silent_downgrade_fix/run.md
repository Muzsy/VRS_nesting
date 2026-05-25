# Runner — SGH-Q08R Exact backend no-silent-downgrade fix

Feladat: hajtsd végre a `canvases/egyedi_solver/sgh_q08r_exact_backend_no_silent_downgrade_fix.md` canvas és a hozzá tartozó goal YAML alapján az SGH-Q08R javító taskot.

## Dependency gate

Kötelező:

```text
codex/reports/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing.md
```

Első sor: `PASS`.

A Q08 reportban szerepelhet `SGH-Q09_STATUS: READY`, de ezt Q08R felülbírálja: Q09 csak Q08R PASS után indulhat.

Ha a Q08 report nincs meg vagy nem PASS, állj meg `BLOCKED` reporttal, production kódmódosítás nélkül.

## Kötelező bemenetek

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
canvases/egyedi_solver/sgh_q08r_exact_backend_no_silent_downgrade_fix.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q08r_exact_backend_no_silent_downgrade_fix.yaml
rust/vrs_solver/src/optimizer/collision_backend.rs
rust/vrs_solver/src/optimizer/geometry_preprocessing.rs
rust/vrs_solver/src/optimizer/repair.rs
```

## Javítandó hiba

Q08 után a backend-váz megvan, de az exact backend még nem elég szigorú.

Ellenőrizd:

```bash
rg -n "extract_polygon_from_part|parse_points_json|polygons_collide|bbox_to_rect_pts|bbox_from_placement|collides_with" rust/vrs_solver/src/optimizer/collision_backend.rs
rg -n "JaguaPolygonExactBackend|CdeCollisionBackend|find_violations_with_backend" docs/egyedi_solver/sgh_q08_collision_backend_contract.md codex/reports/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing.md
```

A reportban rögzítsd a pre-fix találatokat fájl/sor szinten.

## Kötelező javítás

### 1. Polygon extraction: Absent / Invalid / Valid

Ne maradjon `Option<Vec<Point>>` contract.

Elvárt:

```text
Absent: nincs outer_points és nincs prepared_outer_points -> rect fallback jogos
Invalid: van outer_points/prepared_outer_points, de parse/shape invalid -> Unsupported
Valid: valid polygon -> exact polygon path
```

Invalid exact geometry soha nem mehet bbox fallbackre és soha nem lehet NoCollision.

### 2. polygons_collide ne bool legyen, ha hibázhat

A helper tudjon Unsupported állapotot visszaadni.

Elfogadható:

```rust
fn polygons_collide(...) -> Result<bool, &'static str>
```

vagy:

```rust
fn polygons_collide(...) -> CollisionDecision
```

Invalid/degenerate geometry, edge build failure, SPolygon build failure: `Unsupported`.

### 3. Rotation-aware rect geometry

Exact backendben rect geometriához tilos `bbox_from_placement(...) + bbox_to_rect_pts(...)` használata.

Adj helper-t:

```rust
fn rect_polygon_from_placement(placement: &Placement, width: f64, height: f64) -> Result<Vec<Point>, &'static str>
```

vagy `[Point; 4]` visszatéréssel.

A local rect legyen:

```text
(0,0), (w,0), (w,h), (0,h)
```

majd ugyanazzal a rotation/translation anchorral menjen át, mint `transform_polygon(...)`.

Exact backendben rect-vs-rect, rect-vs-irregular, irregular-vs-rect ezt használja.

### 4. Boundary exact path rotation-aware

`JaguaPolygonExactBackend::placement_within_sheet(...)` exact rect esetben se `rect_within_boundary(...)` útvonalon döntsön.

Használj közös polygon-within-sheet helper-t:

```text
Absent polygon -> rotated rect world polygon
Valid polygon -> transformed outer polygon
Invalid polygon -> Unsupported
```

### 5. Touching policy

A bbox-kompatibilis policy legyen explicit:

```text
shared edge -> NoCollision
shared point -> NoCollision
positive-area overlap -> Collision
boundary touch while inside -> NoCollision
true crossing/outside -> Collision
```

Ha a jagua `Edge.collides_with` touchingot collisionnek veszi, vezess be saját tolerant segment helper-t, amely megkülönbözteti a touchingot a true crossingtól.

## Kötelező tesztek

Adj célzott teszteket, minimum ezekkel vagy ekvivalens nevekkel:

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
bbox_backend_still_matches_existing_behavior
cde_backend_still_returns_unsupported
```

Fontos: ezek ne csak helper unit tesztek legyenek, hanem a `JaguaPolygonExactBackend` publikus trait metódusain keresztül is bizonyítsák a viselkedést.

## Dokumentáció

Frissítsd:

```text
docs/egyedi_solver/sgh_q08_collision_backend_contract.md
```

Kötelező pontosítások:

```text
JaguaPolygonExactBackend status: supported outer-boundary rect/polygon collision scope-ban exact, globálisan még PARTIAL.
CDE parity nincs kész.
Hole/cavity semantics nincs kész.
Invalid exact geometry -> Unsupported.
Rect exact path rotation-aware.
Touching policy: no positive-area overlap = NoCollision.
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

## Report output

Hozd létre:

```text
codex/codex_checklist/egyedi_solver/sgh_q08r_exact_backend_no_silent_downgrade_fix.md
codex/reports/egyedi_solver/sgh_q08r_exact_backend_no_silent_downgrade_fix.md
codex/reports/egyedi_solver/sgh_q08r_exact_backend_no_silent_downgrade_fix.verify.log
```

A report tartalmazzon táblázatot:

```text
Finding from audit | Fix implemented | Tests proving it | Remaining limitation
```

PASS esetén első sor:

```text
PASS
```

és a végén:

```text
SGH-Q09_STATUS: READY
```
