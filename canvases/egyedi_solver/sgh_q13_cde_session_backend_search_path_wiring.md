# SGH-Q13 — CDE session backend + search-path wiring

## Státusz

Implementation task SGH-Q12 után.

## Előfeltétel

Kötelező:

```text
codex/reports/egyedi_solver/sgh_q12_cde_engine_api_adaptation_pilot.md
```

Első sor: `PASS`, és a report végén legyen:

```text
SGH-Q13_STATUS: READY
```

Ha nincs meg, állj meg `BLOCKED` reporttal, production kódmódosítás nélkül.

## Miért kell?

SGH-Q12 bizonyította, hogy a jagua-rs `CDEngine` API ténylegesen használható VRS-ből, de a megoldás még **per-call CDEngine**:

```text
pair query -> CDEngine::new(...) minden egyes queryre
boundary query -> CDEngine::new(...) minden egyes queryre
```

Ez pilotnak jó volt, de production keresésre nem elég. Ráadásul Q11R/Q12 után még maradt CDE-specifikus keresési hiány:

```text
VrsCollisionTracker::compute_backend_decisions(Cde) -> minden pair Unsupported
VrsSeparator::candidate_backend_loss(Cde) -> f64::MAX
```

Ez azt jelenti: explicit `collision_backend: "cde"` esetén a final validation már CDE-képes, de a separator/search útvonal még nem használja ténylegesen a CDE döntéseket.

## Cél

A Q13 célja kettős, de szűk scope-pal:

```text
1. CDE session/lifecycle foundation:
   - ne kelljen minden queryhez nulláról CDEEngine-t építeni, ha az API engedi;
   - legyen egy VRS-owned CdeLayoutSession / CdeSheetSession contract;
   - ha a jagua-rs filter/lifecycle API ezt nem engedi tisztán, legyen explicit BLOCKED/PARTIAL evidence, nem fake session.

2. CDE search-path wiring:
   - VrsCollisionTracker ne jelöljön minden CDE pairt/boundaryt Unsupportedként;
   - VrsSeparator candidate_backend_loss(Cde) ne legyen automatikusan f64::MAX;
   - backend-aware scoring/validation CDE-vel valóban használható legyen opt-in phase/search útvonalon.
```

A default továbbra is `bbox`. CDE továbbra is explicit opt-in.

## Nem cél

```text
production default CDE-re váltása
hole/cavity semantics teljes megoldása
DXF/preflight refaktor
Sparrow teljes port
optimizer stratégia újraírása
spacing/kerf/margin model teljes átírása
```

## Scope

### Engedélyezett production fájlok

```text
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/optimizer/cde_session.rs          # új, ajánlott
rust/vrs_solver/src/optimizer/collision_backend.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/score.rs
rust/vrs_solver/src/optimizer/moves.rs
rust/vrs_solver/src/optimizer/phase.rs
rust/vrs_solver/src/optimizer/sheet_elimination.rs
rust/vrs_solver/src/optimizer/bpp_phase.rs
rust/vrs_solver/src/optimizer/mod.rs
```

### Engedélyezett artefaktok

```text
canvases/egyedi_solver/sgh_q13_cde_session_backend_search_path_wiring.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q13_cde_session_backend_search_path_wiring.yaml
codex/prompts/egyedi_solver/sgh_q13_cde_session_backend_search_path_wiring/run.md
codex/codex_checklist/egyedi_solver/sgh_q13_cde_session_backend_search_path_wiring.md
codex/reports/egyedi_solver/sgh_q13_cde_session_backend_search_path_wiring.md
codex/reports/egyedi_solver/sgh_q13_cde_session_backend_search_path_wiring.verify.log
docs/egyedi_solver/sgh_q13_cde_session_backend_contract.md
```

## Kötelező pre-audit

Olvasd el:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
canvases/egyedi_solver/sgh_q12_cde_engine_api_adaptation_pilot.md
docs/egyedi_solver/sgh_q12_cde_engine_adapter_contract.md
codex/reports/egyedi_solver/sgh_q12_cde_engine_api_adaptation_pilot.md
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/optimizer/collision_backend.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/sheet_elimination.rs
```

Auditáld a jagua-rs filter/lifecycle API-t:

```bash
rg -n "trait.*Filter|struct.*Filter|impl.*Filter|NoFilter|HazardEntity|PlacedItem|PItemKey|SlotMap|CDEngine" ~/.cargo/registry/src rust -g '*.rs' || true
```

A reportban külön válaszold meg:

```text
- Lehet-e egy CDEEngine-ben sok placed item hazardot regisztrálni és querynél self-hazardot filterrel kizárni?
- Használható-e HazardEntity::PlacedItem PItemKey VRS layout state nélkül?
- Ha nem, használható-e Hole { idx } + custom filter?
- Ha egyik sem tiszta: session cache melyik részét lehet biztonságosan implementálni most?
```

## Kötelező implementációs részletek

### 1. CDE session contract

Hozz létre session/lifecycle contractot, például:

```rust
pub struct CdeSheetSession { ... }
pub struct CdeLayoutSession { ... }
pub enum CdeSessionCapability { FullSession, QueryBatch, PerCallOnly { reason: &'static str } }
```

Elvárás:

```text
- VRS-owned API, nem szivárogtat jagua-rs típust public optimizer API-ba.
- Képes dokumentáltan megmondani, mire alkalmas a jelenlegi jagua-rs API-val.
- Ha session engine megvalósítható: építsen egy CDEEngine-t sheetenként/layoutonként.
- Ha self-filter nem tiszta: ne fake-eld; legyen PARTIAL/BLOCKED capability, és fallback csak explicit per-call CDE, nem bbox.
```

Elfogadható PASS:

```text
A) Full/Batch CDE session validálás megvalósul és a per-call adapterrel egyező döntéseket ad.
B) Ha a filter/lifecycle API miatt full session nem biztonságos, akkor CdeSessionCapability::PerCallOnly dokumentáltan marad, de a search-path CDE wiring ténylegesen használja a per-call CdeCollisionBackendet, nem Unsupported sentinel.
```

Nem elfogadható:

```text
CDE session néven bbox/JaguaPolygonExact fallback
CDE separator loss automatikus f64::MAX minden candidate-re
silent fallback bboxra exact/cde query hiba esetén
```

### 2. VrsCollisionTracker CDE döntések

`compute_backend_decisions(Cde)` jelenleg minden pairt Unsupportednek és minden boundaryt Unsupportednek jelöl. Ezt javítsd.

Elvárt:

```text
CollisionBackendKind::Cde -> CdeCollisionBackend alapján pair/boundary döntések
NoCollision -> exact_no_collision / boundary_exact_valid
Collision -> bbox/loss proxy vagy positive collision loss
Unsupported -> unsupported sentinel loss
```

A JaguaPolygonExact és Bbox viselkedés ne romoljon.

### 3. Separator candidate_backend_loss(Cde)

`candidate_backend_loss(Cde) -> f64::MAX` tilos maradjon.

Elvárt:

```text
CollisionBackendKind::Cde esetén:
- placement_within_sheet(candidate, part, sheet) CdeCollisionBackend alapján;
- pair collision queryk CdeCollisionBackend alapján;
- Collision -> valamilyen positive loss, pl. bbox overlap loss max(1.0) vagy smooth loss proxy;
- NoCollision -> 0 contribution;
- Unsupported -> f64::MAX;
```

Ez nem teljes smooth CDE loss parity; de CDE search útvonal ne legyen automatikusan használhatatlan.

### 4. Backend-aware phase/search smoke

Legyen olyan opt-in test, amely ténylegesen futtatja:

```text
optimizer_pipeline: phase_optimizer
collision_backend: cde
```

és bizonyítja:

```text
- valid rect fixture-en nincs unsupported output;
- separator/BPP/phase nem full f64::MAX miatt áll meg;
- final validation CDE szerint violation-free vagy explicit unsupported;
- bbox default output változatlan.
```

### 5. Diagnostics

Bővítsd vagy pontosítsd a diagnosztikát:

```text
backend_used: bbox | jagua_polygon_exact | cde_adapter
cde_session_capability: full_session | query_batch | per_call_only
cde_queries: pair_count, boundary_count, unsupported_count
cde_engine_builds: count
```

Ha a diagnostics JSON/output mezők publikus szerződést érintenek, dokumentáld.

## Kötelező tesztek

Minimum:

```text
cde_tracker_build_uses_cde_backend_not_all_unsupported
cde_separator_candidate_backend_loss_is_not_always_max
cde_separator_repairs_simple_overlap_or_reports_real_unsupported
cde_phase_optimizer_valid_rect_fixture_has_no_backend_unsupported
cde_score_with_backend_matches_validation_for_valid_rects
cde_session_capability_reports_truthful_lifecycle_status
cde_session_or_batch_matches_per_call_adapter_for_pair_matrix
bbox_default_still_matches_pre_q13_behavior
jagua_polygon_exact_path_unchanged
no_silent_bbox_fallback_for_cde_search_path
```

Ha full session nem implementálható a jagua-rs API-val, akkor a session teszt bizonyítsa a `PerCallOnly { reason }` státuszt és azt, hogy a search-path mégis CDE per-call backendet használ, nem unsupported sentinel állapotot.

## Verify

Futtasd legalább:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::cde_adapter
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::cde_session
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::collision_backend
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::phase
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::score
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q13_cde_session_backend_search_path_wiring.md
```

Ha bármelyik fail: report első sora `REVISE` vagy `BLOCKED`, és nincs `SGH-Q14_STATUS: READY`.

## PASS feltételek

PASS csak akkor:

```text
- CDE lifecycle/session státusz őszintén dokumentált.
- CDE search path nem full Unsupported/f64::MAX sentinel.
- CDE queryk ténylegesen CdeCollisionBackendet/CdeAdaptert használnak.
- Bbox default változatlan.
- JaguaPolygonExact nem regresszál.
- cargo test --lib és verify zöld.
```

PASS esetén report vége:

```text
SGH-Q14_STATUS: READY
```
