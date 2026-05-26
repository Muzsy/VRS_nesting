# Runner — SGH-Q10 CollisionBackend policy production wiring

Feladat: hajtsd végre a `canvases/egyedi_solver/sgh_q10_collision_backend_policy_production_wiring.md` canvas és a hozzá tartozó goal YAML alapján az SGH-Q10 taskot.

## Dependency gate

Kötelező:

```text
codex/reports/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring.md
```

Első sor: `PASS`.

A report végén legyen:

```text
SGH-Q10_STATUS: READY
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
docs/egyedi_solver/sgh_q08_collision_backend_contract.md
docs/egyedi_solver/sgh_q09_phase_optimizer_production_wiring_contract.md
canvases/egyedi_solver/sgh_q10_collision_backend_policy_production_wiring.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q10_collision_backend_policy_production_wiring.yaml
codex/reports/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring.md
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/optimizer/collision_backend.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/optimizer/phase.rs
```

## Alapprobléma

Q08/Q08R létrehozta a moduláris collision backend réteget, Q09 pedig bekötötte a PhaseOptimizer production útvonalat. A production acceptance gate viszont még főleg bbox `find_violations(...)` alapon működik.

A Q10 célja:

```text
collision_backend input policy
bbox default változatlan
jagua_polygon_exact explicit opt-in
cde explicit unsupported
backend-aware production acceptance gate
no silent bbox fallback explicit exact/cde esetben
```

## Előzetes audit — kötelező

Futtasd:

```bash
rg -n "find_violations\(|find_violations_with_backend|validate_and_commit|CollisionBackend|BboxCollisionBackend|JaguaPolygonExactBackend|CdeCollisionBackend" rust/vrs_solver/src
```

A reportban írd le:

```text
- jelenlegi production bbox validation pontok
- Q08 exact backend helper pontok
- Q10-ben pontosan milyen policy wiring kerül be
```

## Implementációs irány

### 1. SolverInput kapcsoló

Adj optional input mezőt:

```rust
#[serde(default)]
pub collision_backend: Option<CollisionBackendKind>,
```

Javasolt enum:

```rust
#[derive(Debug, Clone, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum CollisionBackendKind {
    Bbox,
    JaguaPolygonExact,
    Cde,
}
```

Default: `Bbox`.

### 2. Checked validation

A production acceptance gate nem használhat olyan helper-t, amely elveszíti az `Unsupported` tényt.

Vezess be diagnosztikus eredményt, például:

```text
BackendValidationResult {
  violations,
  diagnostics: { backend_name, unsupported_queries, bbox_fallback_queries }
}
```

vagy repo-stílusú ekvivalenst.

Kötelező:

```text
bbox: régi find_violations-szal azonos
jagua_polygon_exact: unsupported_queries > 0 blokkolja az accepted outputot
cde: unsupported, nem fallback
```

### 3. WorkingLayout commit

Adj backend-aware commit helpert, de a régi `validate_and_commit(...)` maradjon kompatibilis bbox defaultként.

### 4. Adapter routing

Az `adapter::solve()` output építés előtt validáljon a kiválasztott backenddel:

```text
legacy_multisheet path: final backend gate
phase_optimizer path: final backend gate
```

Explicit exact/cde esetén no silent fallback.

### 5. Diagnostics

Opcionális, de ajánlott output mező:

```text
collision_backend_diagnostics.backend_used
collision_backend_diagnostics.unsupported_queries
collision_backend_diagnostics.bbox_fallback_queries
```

Ha output mezőt nem adsz, a report + tesztek legyenek elég erősek.

## Kötelező tesztek

Minimum:

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

Stabil helper fixture esetén:

```text
jagua_polygon_exact_l_shape_notch_does_not_report_bbox_false_positive
```

## Nem cél

Ne csináld most:

```text
CDE teljes implementáció
exact backend default bekapcsolása
separator/loss-model exact scoring teljes átírása
hole/cavity semantics
DXF/preflight refaktor
új stochastic coordinate descent kereső
új LossModel algoritmus
rotation policy újratervezés
legacy default output breaking change
```

Ha a separator/score model még bbox alapú marad, dokumentáld QUALITY_RISK-ként, és a report végén Q11 marker legyen.

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

PASS esetén report végén:

```text
SGH-Q11_STATUS: READY
```
