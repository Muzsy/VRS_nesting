# SGH-Q08 — CollisionBackend + geometry preprocessing foundation

## Státusz

Implementációs task, SGH-Q07R2 után.

## Előfeltétel

Kötelező:

```text
codex/reports/egyedi_solver/sgh_q07r2_phase_rotation_context_wiring_fix.md
```

Első sor: `PASS`, és a report végén legyen:

```text
SGH-Q08_STATUS: READY
```

Ha ez nincs meg, állj meg `BLOCKED` reporttal, production kódmódosítás nélkül.

## Miért kell ez?

A Q02–Q07R2 után a solver már Sparrow-szerűbb search/orchestration vázat kapott, de a geometriája még mindig jelentős részben bbox/proxy alapú.

A Q08 célja a következő minőségi ugrás előkészítése:

```text
bbox-only collision / boundary proxy
  -> moduláris CollisionBackend / GeometryBackend
  -> jagua-rs/CDE vagy jagua-rs exact polygon backend
  -> preprocessing pipeline és shape cache foundation
```

Fontos: nem szabad azt állítani, hogy CDE parity kész, ha a repo/jagua-rs API alapján valójában csak bbox vagy kézzel összerakott polygon-collision wrapper készült el.

## Kapcsolódó SGH-Q00/Q01 gap

```text
F03 PROXY — transformation model
F04 PROXY — AABB / bbox-only item collision
F17 MISSING — geometry preprocessing pipeline
F18 PROXY — irregular boundary / outer_points csak részben feldolgozott
```

## Cél

Vezess be egy moduláris collision/geometry backend réteget, amelyben:

```text
CollisionBackend trait
  - BboxCollisionBackend: jelenlegi viselkedés, backward-compatible default
  - JaguaExactCollisionBackend vagy CdeCollisionBackend: jagua-rs alapú exact polygon collision útvonal, ha a helyi API alapján megvalósítható

GeometryBackend / GeometryPreprocessor foundation
  - rectangle fallback megmarad
  - outer_points alapú irregular item/sheet shape feldolgozás scaffold
  - shape preprocessing pipeline: validate, normalize orientation, simplify tolerance placeholder, bbox/cache metadata
  - surrogate/cache struktúra: későbbi CDE/pole/surrogate gyorsításhoz
```

A Q08 végén legyen egy használható, tesztelt backend API, de csak azt kösd production döntési útvonalra, ami bizonyítottan nem rontja a jelenlegi működést.

## Nagyon fontos minőségi szabály

```text
Ne cserélj bbox-proxyt másik proxyra úgy, hogy exact/CDE néven fut.
Ne írd be PASS-ként, hogy CDE kész, ha csak SPolygon corner/edge wrapper készült.
Ha a jagua-rs CDEngine API nem hozzáférhető a jelenlegi crate-ből, akkor:
  - explicit BLOCKED/PARTIAL report rész kell,
  - BboxCollisionBackend + JaguaPolygonExactBackend scaffold lehet PASS,
  - de CDECollisionBackend státusza MISSING/BLOCKED maradjon.
```

## Scope

### Engedélyezett production fájlok

```text
rust/vrs_solver/src/optimizer/collision_backend.rs        # új
rust/vrs_solver/src/optimizer/geometry_backend.rs         # új, ha indokolt
rust/vrs_solver/src/optimizer/geometry_preprocessing.rs   # új, ha indokolt
rust/vrs_solver/src/optimizer/mod.rs
rust/vrs_solver/src/geometry.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/boundary.rs
rust/vrs_solver/src/optimizer/candidates.rs              # csak backend-aware validation/helper miatt
rust/vrs_solver/src/optimizer/separator.rs               # csak backend config/hook miatt, ne refaktorold túl
rust/vrs_solver/src/optimizer/loss_model.rs              # csak ha backend adapterhez minimálisan kell
rust/vrs_solver/Cargo.toml                               # csak ha tényleg szükséges dependency/feature miatt
```

### Engedélyezett artefaktok

```text
canvases/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q08_collision_backend_geometry_preprocessing.yaml
codex/prompts/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing/run.md
codex/codex_checklist/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing.md
codex/reports/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing.md
codex/reports/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing.verify.log
docs/egyedi_solver/sgh_q08_collision_backend_contract.md
```

### Tiltott scope

```text
hole/cavity semantics teljes megoldása
DXF/preflight nagy refaktor
új optimizer stratégia
sheet elimination / BPP refaktor
rotation policy újratervezés
LossModel teljes átírása
külső benchmark backend kötelező futtatása
production default átkapcsolása exact backendre no-downgrade bizonyítás nélkül
```

## Kötelező pre-audit

Olvasd el és dokumentáld a reportban:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
docs/egyedi_solver/sgh_q00_quality_feature_gap_matrix.md
docs/egyedi_solver/sgh_q01_corrected_task_roadmap.md
docs/egyedi_solver/sgh_q07_rotation_policy_contract.md
rust/vrs_solver/src/geometry.rs
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/boundary.rs
rust/vrs_solver/src/optimizer/candidates.rs
rust/vrs_solver/src/adapter.rs
```

Auditáld a jagua-rs helyi API-t is:

```bash
cargo tree --manifest-path rust/vrs_solver/Cargo.toml | rg "jagua"
rg -n "struct CDEngine|CDEngine|collision_detection|OriginalShape|SPolygon|Surrogate" ~/.cargo/registry/src rust -g '*.rs' || true
```

A reportban külön írd le:

```text
- elérhető-e CDEngine a jelenlegi jagua-rs crate-ből?
- ha igen: milyen minimális API-n keresztül lehet használni?
- ha nem: milyen jagua-rs polygon primitive áll rendelkezésre, és mi marad BLOCKED?
```

## Kötelező implementációs minimum

### 1. CollisionBackend trait

Legyen egy VRS-owned trait, amely nem szivárogtat jagua-rs típust a publikus optimizer API-ba.

Elvárt jelleg:

```rust
pub trait CollisionBackend {
    fn name(&self) -> &'static str;
    fn placement_overlaps(
        &self,
        a: &Placement,
        a_part: &Part,
        b: &Placement,
        b_part: &Part,
    ) -> CollisionDecision;
    fn placement_within_sheet(
        &self,
        placement: &Placement,
        part: &Part,
        sheet: &SheetShape,
    ) -> CollisionDecision;
}
```

A pontos signature igazodhat a repo stílusához, de:

```text
- külön item-item collision
- külön item-container boundary
- hibák/unsupported állapotok ne silently true/false értékre essenek vissza
- legyen backend name és diagnostics
```

### 2. BboxCollisionBackend

A jelenlegi viselkedést emeld ki explicit backendbe.

Követelmény:

```text
- defaultként ugyanazt adja, mint a jelenlegi find_violations / rect_within_boundary / PlacedBbox.overlaps
- minden meglévő teszt zöld marad
- backward compatibility bizonyított legyen
```

### 3. Jagua exact / CDE backend foundation

Próbáld meg a tényleges jagua-rs CDEngine használatát, de ne találj ki nem létező API-t.

Elfogadható PASS opciók:

```text
A) Valódi CdeCollisionBackend:
   - jagua-rs CDEngine vagy megfelelő collision_detection API használata
   - rectangle és irregular polygon placement collision tesztek
   - shape cache/preprocessing scaffold

B) Ha CDEEngine nem elérhető:
   - JaguaPolygonExactBackend meglévő SPolygon/Edge/CollidesWith primitívekkel
   - CdeCollisionBackend státusz dokumentáltan BLOCKED/MISSING
   - backend trait és exact polygon adapter működik, nem bbox proxyként
```

Nem elfogadható:

```text
- CDECollisionBackend név alatt bbox overlap
- jagua-rs API-ról reportban bizonyíték nélküli állítás
- exact backend production defaultként bekötve regressziós no-downgrade gate nélkül
```

### 4. Geometry preprocessing foundation

Hozz létre egy minimális, moduláris preprocessing réteget.

Kötelező elemek:

```text
PreparedShape / PreparedGeometry metadata
  - original vertex count
  - bbox
  - area
  - has_irregular_shape
  - simplification_tolerance used
  - backend readiness flags

preprocess_polygon / preprocess_rect helper
  - invalid polygon reject
  - duplicate consecutive point cleanup
  - orientation/area normalizáció dokumentálva
  - simplification placeholder explicit TODO/QUALITY_RISK, ha még nincs teljes Douglas-Peucker/Vatti/offset cleanup
```

Fontos: a teljes offset/simplify/narrow-concavity-close pipeline lehet scaffold, de a reportban ne szerepeljen teljesként, ha nem az.

### 5. Backend-aware validation hook

Adj új API-t, amely a collision backendet használja, például:

```rust
find_violations_with_backend(..., backend: &dyn CollisionBackend)
```

A meglévő `find_violations(...)` maradhat backward-compatible wrapper a `BboxCollisionBackend` felé.

Legalább validációs szinten legyen bizonyított, hogy az exact/jagua backend képes eltérő választ adni bbox-tól olyan irregular fixture-n, ahol a bbox false positive/false negative kimutatható.

## Kötelező tesztek

Minimum Rust tesztek:

```text
bbox_backend_matches_existing_rect_overlap_behavior
find_violations_default_matches_pre_q08_behavior
jagua_or_cde_backend_detects_polygon_overlap
jagua_or_cde_backend_rejects_l_shape_notch_or_irregular_outside
geometry_preprocessing_rejects_invalid_polygon
geometry_preprocessing_dedupes_consecutive_duplicate_points
backend_does_not_silently_fallback_to_bbox_when_exact_unavailable
```

Ha a CDEEngine nem érhető el, akkor a CDE-specifikus teszt `#[ignore]` vagy dokumentált BLOCKED lehet, de a jagua polygon backend teszteknek zöldnek kell lenniük.

## Kötelező smoke / benchmark jellegű gate

Adj legalább egy kis smoke scriptet vagy Rust benchmark-smoke-ot, amely riportolja:

```text
backend: bbox vs jagua_polygon/cde
fixture: irregular L-shape vagy concave polygon
checks: item-item collision, item-container boundary
result matrix: bbox_decision vs exact_decision
```

Elfogadási szabály:

```text
- default bbox backend nem regresszál
- exact backend legalább egy irregular esetben többet tud bizonyítani, mint a bbox útvonal
- minden accepted layout find_violations_with_backend szerint violation-free
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

PASS esetén a report első sora:

```text
PASS
```

A végén:

```text
SGH-Q09_STATUS: READY
```

A reportnak külön tartalmaznia kell:

```text
- dependency gate eredmény
- jagua-rs API audit bizonyíték
- milyen backend készült: Bbox / JaguaPolygon / CDE
- mi maradt proxy / partial / blocked
- changed files / function matrix
- tests added
- exact-vs-bbox smoke eredmény
- verify log összefoglaló
```
