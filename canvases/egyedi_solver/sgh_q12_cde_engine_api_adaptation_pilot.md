# SGH-Q12 — jagua-rs CDEngine API adaptation pilot

## Státusz

Implementation/audit pilot task SGH-Q11R után.

## Előfeltétel

Kötelező:

```text
codex/reports/egyedi_solver/sgh_q11r_backend_aware_score_consistency_candidate_fix.md
```

Első sor: `PASS`.

A reportban legyen:

```text
SGH-Q12_STATUS: READY
```

Megjegyzés: ha a Q11R report törzsében még maradt régi `REVISE` packaging szöveg, de a report első sora `PASS`, az auto-verify blokk PASS, és a follow-up duplicate-overlap tesztek zöldek, akkor ezt ne blokkolóként kezeld. A Q11R follow-up ezt felülírta.

## Miért kell?

Q08–Q11R után van:

```text
BboxCollisionBackend                # default proxy
JaguaPolygonExactBackend            # opt-in exact-ish outer-boundary polygon backend
CdeCollisionBackend                 # scaffold, jelenleg Unsupported
backend-aware scoring/separator/BPP # Q11R után
```

De a jagua-rs/Sparrow minőségi alapja nem a saját polygon wrapper, hanem a jagua-rs geometriakezelés és CDE jellegű collision detection réteg. Q12 célja az, hogy ezt ne csak dokumentáljuk, hanem kódszinten is eldöntsük és pilotoljuk:

```text
1. Tényleg elérhető-e a jagua-rs 0.6.4 CDEngine / collision detection API a VRS-ből?
2. Ha igen: készíts minimális, opt-in CDE adaptert, no-silent-fallback szabályokkal.
3. Ha nem: dokumentált BLOCKED/PARTIAL státusz, konkrét API gap és következő port stratégia.
```

## Alapszabály

Tilos CDE-nek nevezni bármit, ami valójában bbox vagy a Q08-as JaguaPolygonExactBackend újracsomagolása.

Elfogadható kimenetek:

```text
A) PASS: valódi CdeCollisionBackend opt-in módon működik legalább rect + outer polygon placement overlap/boundary fixture-ökön.
B) PARTIAL/PASS_WITH_NOTES: CDE API közvetlenül nem illeszthető, de elkészült egy tiszta CdeAdapter contract + compile-gated/feature-gated skeleton és részletes port plan; ebben az esetben NEM állítható, hogy CDE kész.
C) BLOCKED/REVISE: az API nem auditált vagy a kód bbox fallbacket ad CDE néven.
```

Ha nincs működő CDE path, a report végén ne szerepeljen automatikusan `SGH-Q13_STATUS: READY`, hacsak a következő task explicit nem a dokumentált CDE blocker feloldása.

## Scope

### Engedélyezett production fájlok

```text
rust/vrs_solver/src/optimizer/collision_backend.rs
rust/vrs_solver/src/optimizer/cde_adapter.rs          # új, ajánlott
rust/vrs_solver/src/optimizer/geometry_preprocessing.rs
rust/vrs_solver/src/optimizer/mod.rs
rust/vrs_solver/src/geometry.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/Cargo.toml                            # csak feature/dependency miatt, ha indokolt
```

### Engedélyezett artefaktok

```text
canvases/egyedi_solver/sgh_q12_cde_engine_api_adaptation_pilot.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q12_cde_engine_api_adaptation_pilot.yaml
codex/prompts/egyedi_solver/sgh_q12_cde_engine_api_adaptation_pilot/run.md
codex/codex_checklist/egyedi_solver/sgh_q12_cde_engine_api_adaptation_pilot.md
codex/reports/egyedi_solver/sgh_q12_cde_engine_api_adaptation_pilot.md
codex/reports/egyedi_solver/sgh_q12_cde_engine_api_adaptation_pilot.verify.log
docs/egyedi_solver/sgh_q12_cde_engine_adapter_contract.md
```

### Tiltott scope

```text
bbox fallback CDE néven
JaguaPolygonExactBackend átnevezése CDE-re
production default átkapcsolása CDE-re
hole/cavity semantics teljes megoldása
DXF/preflight nagy refaktor
optimizer stratégia újraírása
Sparrow teljes port egy taskban
```

## Kötelező source/API audit

Futtasd és dokumentáld:

```bash
cargo tree --manifest-path rust/vrs_solver/Cargo.toml | rg "jagua|cde|collision|spolygon"
rg -n "CDEngine|CDE|CollisionDetection|collision_detection|OriginalShape|SPolygon|Surrogate|Hazard|hazard|collides_with|CollidesWith" \
  ~/.cargo/registry/src rust -g '*.rs' || true
```

A reportban legyen külön táblázat:

```text
Symbol / API | Path | Visibility | Usable from vrs_solver? | Notes
```

Kötelező döntési kérdések:

```text
- Van-e public CDEEngine vagy ekvivalens API?
- Kell-e hazard registration / layout state lifecycle?
- Tud-e placement-level synchronous queryt adni?
- Tud-e outer polygon + rectangle transformot kezelni?
- Mi a minimum cache/surrogate input contract?
- Milyen lifetimes/ownership akadályok vannak?
```

## Kötelező implementációs minimum

### 1. `cde_adapter.rs` vagy ekvivalens modul

Hozz létre VRS-owned adaptert, amely elrejti a jagua-rs típusokat:

```rust
pub struct CdeAdapterConfig { ... }
pub struct CdePreparedShape { ... }
pub struct CdePlacementQuery { ... }
pub enum CdeQueryResult { Collision, NoCollision, Unsupported { reason: String } }
```

A pontos forma igazodhat a jagua-rs API-hoz, de a cél:

```text
- ne szivárogjon jagua-rs típus a public optimizer API-ba;
- legyen előkészített shape/cache contract;
- Unsupported legyen explicit, ne bool false;
- CDE unavailable esetén compile-time vagy runtime clear error legyen.
```

### 2. `CdeCollisionBackend` valódi bekötés vagy tiszta blocker

Ha a CDE API használható:

```text
- CdeCollisionBackend placement_overlaps() menjen CdeAdapteren keresztül;
- placement_within_sheet() is CDE/adapter vagy explicit polygon-boundary helper legyen;
- invalid geometry -> Unsupported;
- bbox fallback tilos;
- tests: rect overlap, rotated rect, irregular polygon, outside sheet.
```

Ha a CDE API nem használható:

```text
- CdeCollisionBackend maradhat Unsupported,
- de docs/report pontosan írja le, mely API gap miatt;
- legyen `cde_adapter.rs` skeleton, amely explicit `CDE_API_UNAVAILABLE` reasonnel tér vissza;
- legyen teszt, hogy CDE kérés továbbra sem fallbackel bboxra vagy JaguaPolygonExactre.
```

### 3. Geometry preprocessing kapcsolat

A CDE adapternek ne nyers serde_json `outer_points`-ből dolgozzon szétszórtan.

Használja vagy bővítse:

```text
PreparedShape / PreparedGeometry
preprocess_polygon / preprocess_rect
bbox / area / vertex count / readiness flags
```

A reportban írd le:

```text
- milyen shape metadata kell a CDE-hez;
- mi van már meg;
- mi hiányzik még teljes Sparrow/jagua parityhez.
```

### 4. No-silent-fallback gate

Explicit teszteld:

```text
collision_backend: "cde"
```

esetén:

```text
- ha CDE működik: tényleges CDE query fut;
- ha nem működik: Unsupported / unsupported output;
- soha nem BboxCollisionBackend;
- soha nem JaguaPolygonExactBackend fallback.
```

## Kötelező tesztek

Minimum:

```text
cde_api_audit_report_contains_resolved_symbols
cde_backend_does_not_fallback_to_bbox_when_unavailable
cde_backend_does_not_fallback_to_jagua_polygon_exact_when_unavailable
cde_adapter_returns_unsupported_with_clear_reason_if_api_unavailable
cde_backend_rect_overlap_query_works_or_is_blocked_explicitly
cde_backend_rotated_rect_query_works_or_is_blocked_explicitly
cde_backend_irregular_polygon_query_works_or_is_blocked_explicitly
cde_backend_invalid_geometry_is_unsupported_not_no_collision
```

Ha valódi CDE implementáció sikerül, ezeknek működő queryt kell bizonyítaniuk. Ha nem, akkor a `*_works_or_is_blocked_explicitly` tesztek bizonyítsák, hogy nem fallbackelünk, hanem explicit blocker van.

## Verify

Futtasd legalább:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::cde_adapter
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::collision_backend
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::geometry_preprocessing
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q12_cde_engine_api_adaptation_pilot.md
```

Ha bármi fail: report első sora `REVISE` vagy `BLOCKED`.

## Report követelmény

A report első sora csak akkor legyen `PASS`, ha:

```text
- jagua-rs CDE API audit ténylegesen megtörtént;
- CDE adapter vagy explicit CDE blocker contract elkészült;
- no-silent-fallback tesztek zöldek;
- cargo test --lib és verify zöld;
- a report nem állít kész CDE parityt, ha nincs valódi CDE query.
```

A report végén csak akkor szerepeljen:

```text
SGH-Q13_STATUS: READY
```

ha a következő lépés egyértelműen meghatározott és a Q12 saját acceptance gate-je teljesült.
