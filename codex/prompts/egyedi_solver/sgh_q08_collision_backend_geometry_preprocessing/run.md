# Runner — SGH-Q08 CollisionBackend + geometry preprocessing foundation

Feladat: hajtsd végre a `canvases/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing.md` canvas és a hozzá tartozó goal YAML alapján az SGH-Q08 taskot.

## Dependency gate

Kötelező:

```text
codex/reports/egyedi_solver/sgh_q07r2_phase_rotation_context_wiring_fix.md
```

Első sor: `PASS`.

A report végén legyen:

```text
SGH-Q08_STATUS: READY
```

Ha nincs, állj meg `BLOCKED` reporttal, production kódmódosítás nélkül.

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
docs/egyedi_solver/sgh_q07_rotation_policy_contract.md
canvases/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q08_collision_backend_geometry_preprocessing.yaml
rust/vrs_solver/src/geometry.rs
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/boundary.rs
rust/vrs_solver/src/optimizer/candidates.rs
rust/vrs_solver/src/adapter.rs
```

## Alapprobléma

A Q07R2 után a rotation policy végigmegy a phase pathon, de a geometriai validáció és collision döntés még bbox/proxy központú.

Q08 cél:

```text
CollisionBackend trait + BboxCollisionBackend default
Jagua exact vagy CDE backend foundation
Geometry preprocessing foundation
Backend-aware validation hook
```

## Jagua-rs API audit — kötelező

Futtasd és dokumentáld:

```bash
cargo tree --manifest-path rust/vrs_solver/Cargo.toml | rg "jagua"
rg -n "struct CDEngine|CDEngine|collision_detection|OriginalShape|SPolygon|Surrogate" ~/.cargo/registry/src rust -g '*.rs' || true
```

A reportban külön válaszold meg:

```text
- Elérhető-e CDEngine a helyi jagua-rs crate-ből?
- Ha igen: milyen API-val?
- Ha nem: milyen exact polygon primitive használható?
- Melyik backend készült ténylegesen?
```

Tilos nem létező API-t használni vagy CDE-ként eladni bbox fallbacket.

## Implementációs elv

### CollisionBackend

Hozz létre VRS-owned backend réteget, pl.:

```text
rust/vrs_solver/src/optimizer/collision_backend.rs
```

Legyen:

```text
CollisionBackend trait
CollisionDecision / CollisionError / diagnostics jellegű típus
BboxCollisionBackend
JaguaPolygonExactBackend vagy CdeCollisionBackend
```

A jagua-rs típusok ne jelenjenek meg a publikus optimizer API-ban.

### Bbox backend

A jelenlegi viselkedést őrizze meg. A meglévő `find_violations(...)` maradjon kompatibilis wrapper.

### Exact / CDE backend

Ha CDEEngine tényleg elérhető, használd. Ha nem, legyen JaguaPolygonExactBackend a meglévő SPolygon/Edge/CollidesWith primitive-ekből, és reportold a CDE státuszt BLOCKED/MISSING-ként.

### Geometry preprocessing

Hozz létre minimális preprocessing foundationt:

```text
PreparedShape metadata
preprocess_polygon
preprocess_rect
invalid polygon reject
consecutive duplicate cleanup
bbox + area + vertex count
simplification_tolerance metadata
backend readiness flags
```

A teljes offset/simplify/narrow-concavity-close pipeline ne legyen teljesként dokumentálva, ha csak scaffold.

### Backend-aware validation hook

Adj új API-t:

```text
find_violations_with_backend(..., backend: &dyn CollisionBackend)
```

vagy repo-stílushoz illeszkedő enumos változatot.

A régi `find_violations(...)` defaultként BboxCollisionBackend marad.

## Kötelező tesztek

Minimum:

```text
bbox_backend_matches_existing_rect_overlap_behavior
find_violations_default_matches_pre_q08_behavior
jagua_or_cde_backend_detects_polygon_overlap
jagua_or_cde_backend_rejects_l_shape_notch_or_irregular_outside
geometry_preprocessing_rejects_invalid_polygon
geometry_preprocessing_dedupes_consecutive_duplicate_points
backend_does_not_silently_fallback_to_bbox_when_exact_unavailable
```

Ha CDEEngine nem elérhető, a CDE-specifikus teszt lehet dokumentáltan BLOCKED/ignored, de a jagua polygon exact backend tesztjeinek zöldnek kell lenniük.

## Smoke / benchmark gate

Adj kis matrixot, scriptet vagy Rust tesztet:

```text
backend: bbox vs jagua_polygon/cde
fixture: irregular L-shape / concave polygon
checks: item-item collision, item-container boundary
result matrix: bbox_decision vs exact_decision
```

A cél nem külső benchmark, hanem bizonyíték, hogy az exact backend nem csak átnevezett bbox.

## Nem cél

Ne csináld most:

```text
hole/cavity semantics teljes megoldása
DXF/preflight nagy refaktor
új optimizer stratégia
BPP/sheet elimination refaktor
rotation policy újratervezés
LossModel teljes átírása
production default exact backendre váltása no-downgrade gate nélkül
```

## Verify

Futtasd legalább:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::collision_backend
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::geometry_preprocessing
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::repair
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::boundary
cargo test --manifest-path rust/vrs_solver/Cargo.toml item
cargo test --manifest-path rust/vrs_solver/Cargo.toml sheet
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing.md
```

Ha bármelyik fail, report első sora `REVISE` vagy `BLOCKED`, és nincs `SGH-Q09_STATUS: READY`.

## Report

Hozd létre/frissítsd:

```text
codex/codex_checklist/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing.md
docs/egyedi_solver/sgh_q08_collision_backend_contract.md
codex/reports/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing.md
codex/reports/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing.verify.log
```

PASS esetén a report első sora:

```text
PASS
```

és a végén:

```text
SGH-Q09_STATUS: READY
```
