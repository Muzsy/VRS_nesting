# SGH-Q10 — CollisionBackend policy production wiring

## Státusz

Implementációs task, SGH-Q09 után.

## Előfeltétel

Kötelező:

```text
codex/reports/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring.md
```

Első sor: `PASS`, és a report végén legyen:

```text
SGH-Q10_STATUS: READY
```

Ha ez nincs meg, állj meg `BLOCKED` reporttal, production kódmódosítás nélkül.

## Miért kell ez?

Az SGH-Q08/Q08R létrehozta és megtisztította a `CollisionBackend` réteget:

```text
BboxCollisionBackend                # default, backward-compatible
JaguaPolygonExactBackend            # supported exact polygon scope, no silent downgrade
CdeCollisionBackend                 # explicit Unsupported scaffold
find_violations_with_backend(...)
```

Az SGH-Q09 bekötötte a `PhaseOptimizer` production solve-pathot explicit opt-in módon.

Viszont a production acceptance/commit útvonalak még alapvetően a régi bbox-alapú `find_violations(...)` wrapperen mennek át. Ez azt jelenti, hogy a Q08-ban létrehozott exact backend még nem választható production validation policyként.

A Q10 célja: **a collision backend választás legyen explicit, moduláris production policy**, de a default viselkedés továbbra is bbox maradjon.

## Cél

Vezess be egy backward-compatible `collision_backend` input policyt, és vezesd végig a production acceptance gate-en.

Kötelező elv:

```text
default = bbox, régi viselkedés változatlan
jagua_polygon_exact csak explicit opt-in
cde explicit opt-in esetén Unsupported, nem bbox fallback
explicit exact backendnél invalid/unsupported exact geometry nem lehet silent bbox downgrade
accepted output a kiválasztott backend szerint violation-free
azonos input + azonos seed + azonos backend = determinisztikus output
```

## Kapcsolódó SGH-Q00/Q01 gap

```text
F04 — jagua-rs CDE / exact shape collision usage
F18 — irregular container / outer_points boundary kezelés
P06 — no silent downgrade / no proxy hidden as parity
```

A Q10 nem CDE implementáció, nem új optimizer. Ez production policy wiring és commit/validation gate.

## Scope

### Engedélyezett production fájlok

```text
rust/vrs_solver/src/io.rs                         # collision_backend input enum + optional diagnostics field if needed
rust/vrs_solver/src/adapter.rs                    # production routing / output validation by selected backend
rust/vrs_solver/src/optimizer/collision_backend.rs # checked validation helper / diagnostics, no backend-silent fallback
rust/vrs_solver/src/optimizer/repair.rs           # find_violations checked wrapper if this is the repo's canonical place
rust/vrs_solver/src/optimizer/working.rs          # validate_and_commit_with_backend helper
rust/vrs_solver/src/optimizer/phase.rs            # PhaseConfig backend policy field if needed for final commit diagnostics
```

Ha technikailag szükséges, minimális módosítás megengedett:

```text
rust/vrs_solver/src/optimizer/score.rs            # csak TODO/diagnostic vagy backend-aware helper, nem redesign
rust/vrs_solver/src/optimizer/separator.rs        # csak config mező átadás, nem új loss/search algoritmus
```

### Engedélyezett artefaktok

```text
canvases/egyedi_solver/sgh_q10_collision_backend_policy_production_wiring.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q10_collision_backend_policy_production_wiring.yaml
codex/prompts/egyedi_solver/sgh_q10_collision_backend_policy_production_wiring/run.md
codex/codex_checklist/egyedi_solver/sgh_q10_collision_backend_policy_production_wiring.md
codex/reports/egyedi_solver/sgh_q10_collision_backend_policy_production_wiring.md
codex/reports/egyedi_solver/sgh_q10_collision_backend_policy_production_wiring.verify.log
docs/egyedi_solver/sgh_q10_collision_backend_policy_contract.md
```

### Tiltott scope

```text
CDEngine teljes implementáció
CDE default bekapcsolása
exact backend default bekapcsolása
hole/cavity semantics
DXF/preflight refaktor
új stochastic coordinate descent kereső
új LossModel algoritmus
rotation policy újratervezés
legacy default output shape breaking change
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
docs/egyedi_solver/sgh_q08_collision_backend_contract.md
docs/egyedi_solver/sgh_q09_phase_optimizer_production_wiring_contract.md
codex/reports/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring.md
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/optimizer/collision_backend.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/optimizer/phase.rs
```

Futtasd és tedd a reportba a rövid eredményt:

```bash
rg -n "find_violations\(|find_violations_with_backend|validate_and_commit|CollisionBackend|BboxCollisionBackend|JaguaPolygonExactBackend|CdeCollisionBackend" rust/vrs_solver/src
```

A reportban külön válaszold meg:

```text
- hol használ production acceptance jelenleg bbox find_violations-t?
- hol létezik exact backend, de nincs production policyként kiválasztva?
- milyen pontokon kell explicit backend választást átadni?
```

## Kötelező implementáció

### 1. Input enum / backend policy

Adj backward-compatible input mezőt, például:

```rust
#[derive(Debug, Clone, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum CollisionBackendKind {
    Bbox,
    JaguaPolygonExact,
    Cde,
}
```

`SolverInput`:

```rust
#[serde(default)]
pub collision_backend: Option<CollisionBackendKind>,
```

Default: `Bbox`.

Elfogadható alternatíva: repo-stílushoz jobban illeszkedő név, de a JSON értékek legyenek egyértelműek:

```text
bbox
jagua_polygon_exact
cde
```

### 2. Checked validation helper

A jelenlegi `find_violations_with_backend(...) -> Vec<(usize, ViolationType)>` önmagában nem elég explicit production policyhez, mert `Unsupported` esetben nem ad vissza diagnosztikát.

Kell egy checked helper, például:

```rust
pub struct BackendValidationDiagnostics {
    pub backend_name: String,
    pub unsupported_queries: usize,
    pub bbox_fallback_queries: usize,
}

pub struct BackendValidationResult {
    pub violations: Vec<(usize, ViolationType)>,
    pub diagnostics: BackendValidationDiagnostics,
}
```

vagy repo-stílushoz illeszkedő ekvivalens.

Kötelező invariáns:

```text
Bbox -> régi find_violations viselkedés pontosan megmarad
JaguaPolygonExact -> Unsupported számlálható és production acceptance-ben blokkolható
Cde -> Unsupported, nem bbox fallback production acceptance-ben
```

A régi `find_violations(...)` wrapper maradhat változatlanul bbox defaultként.

### 3. WorkingLayout commit helper

Adj backend-aware commit helper-t, például:

```rust
validate_and_commit_with_backend(..., backend_kind: CollisionBackendKind)
```

Kötelező:

```text
bbox backend -> jelenlegi validate_and_commit outputtal azonos
jagua_polygon_exact explicit -> ha unsupported_queries > 0, commit error / unsupported output
jagua_polygon_exact explicit -> ha violations > 0, commit error
cde explicit -> commit error / unsupported output
```

A régi `validate_and_commit(...)` maradjon bbox/default kompatibilis.

### 4. Adapter production routing

Az `adapter::solve()` mindkét production útvonalán használd a kiválasztott backend policyt az accepted output előtt:

```text
legacy_multisheet path:
  MultiSheetManager::run(...)
  final backend validation gate

phase_optimizer path:
  PhaseOptimizer::run(...)
  final backend validation gate
```

Explicit `jagua_polygon_exact` esetén tilos bbox fallbackkel elfogadni outputot.

Ha backend unsupported:

```text
status = unsupported
unsupported_reason = COLLISION_BACKEND_UNSUPPORTED vagy specifikusabb ok
placements = [] vagy repo-stílus szerinti safe output
```

Ha backend violationt talál:

```text
status = unsupported
unsupported_reason = COLLISION_BACKEND_COMMIT_VIOLATION vagy PHASE_OPTIMIZER_COMMIT_VIOLATION_BACKEND
```

A pontos reason string lehet repo-stílusú, de legyen explicit és tesztelt.

### 5. Optional diagnostics

Ha output contract szempontból elfogadható, adj optional diagnosztikát:

```rust
#[serde(skip_serializing_if = "Option::is_none")]
pub collision_backend_diagnostics: Option<CollisionBackendDiagnosticsOutput>
```

Minimum mezők:

```text
backend_used
unsupported_queries
bbox_fallback_queries
```

Ha nem akarsz outputot bővíteni, akkor legalább reportban és unit tesztekben legyen bizonyítva, de a későbbi audit miatt az optional output mező erősen ajánlott.

### 6. Dokumentáció

Hozd létre:

```text
docs/egyedi_solver/sgh_q10_collision_backend_policy_contract.md
```

Tartalmazza:

```text
accepted JSON values
default policy
exact backend no-silent-downgrade policy
CDE unsupported policy
which paths are wired in Q10
out-of-scope: separator/loss-model exact scoring if not implemented in this task
```

## Fontos határvonal

A Q10 minimum kötelező eredménye: **production acceptance gate backend-aware**.

Nem kötelező még, hogy a separator keresési loss, score model és candidate generation teljesen exact-backend alapú legyen. Ha ezt nem kötöd be, írd le explicit QUALITY_RISK-ként és legyen a következő marker:

```text
SGH-Q11_STATUS: READY
```

A Q11 várható scope-ja: backend-aware scoring/separator loss path.

## Kötelező tesztek

Minimum viselkedések:

```text
solver_input_collision_backend_defaults_to_bbox
explicit_bbox_matches_implicit_default_output
phase_optimizer_with_bbox_backend_preserves_q09_behavior
jagua_polygon_exact_backend_can_be_selected_in_solver_input
jagua_polygon_exact_invalid_outer_points_returns_unsupported_not_bbox_fallback
cde_backend_returns_unsupported_not_bbox_fallback
backend_validation_bbox_matches_find_violations
backend_validation_reports_unsupported_count
same_seed_same_backend_is_deterministic
```

Ha tudsz stabil fixture-t adni:

```text
jagua_polygon_exact_l_shape_notch_does_not_report_bbox_false_positive
```

Ez lehet helper szintű teszt is, ha a current construction még nem tudja kihasználni az exact backend által felszabadított notch területet.

## Verify

Futtasd legalább:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::collision_backend
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::working
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::phase
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q10_collision_backend_policy_production_wiring.md
```

Ha bármi fail: report első sora `REVISE` vagy `BLOCKED`, és nincs `SGH-Q11_STATUS: READY`.

## Report és checklist

Hozd létre:

```text
codex/codex_checklist/egyedi_solver/sgh_q10_collision_backend_policy_production_wiring.md
docs/egyedi_solver/sgh_q10_collision_backend_policy_contract.md
codex/reports/egyedi_solver/sgh_q10_collision_backend_policy_production_wiring.md
codex/reports/egyedi_solver/sgh_q10_collision_backend_policy_production_wiring.verify.log
```

PASS esetén report első sora:

```text
PASS
```

PASS esetén a report végén legyen:

```text
SGH-Q11_STATUS: READY
```
