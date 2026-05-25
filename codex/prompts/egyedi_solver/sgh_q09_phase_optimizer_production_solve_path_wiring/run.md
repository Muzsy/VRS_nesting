# Runner — SGH-Q09 PhaseOptimizer production solve-path wiring

Feladat: hajtsd végre a `canvases/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring.md` canvas és a hozzá tartozó goal YAML alapján az SGH-Q09 taskot.

## Dependency gate

Kötelező:

```text
codex/reports/egyedi_solver/sgh_q08r_exact_backend_no_silent_downgrade_fix.md
```

Első sor: `PASS`.

A report végén legyen:

```text
SGH-Q09_STATUS: READY
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
canvases/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q09_phase_optimizer_production_solve_path_wiring.yaml
codex/reports/egyedi_solver/sgh_q08r_exact_backend_no_silent_downgrade_fix.md
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/optimizer/multisheet.rs
rust/vrs_solver/src/optimizer/phase.rs
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/optimizer/repair.rs
```

## Alapprobléma

Q02–Q08R létrehozott több minőségjavító komponenst, de a valós Phase1 `adapter::solve()` útvonal még nem futtatja teljes production pipeline-ként a `PhaseOptimizer` réteget.

A Q09 célja:

```text
explicit opt-in phase_optimizer production path
legacy_multisheet default változatlan
seed + rotation_context + time budget megőrzés
WorkingLayout commit gate
no silent fallback
```

## Előzetes audit — kötelező

Futtasd:

```bash
rg -n "PhaseOptimizer|PhaseConfig|MultiSheetManager::new|find_violations\(|run_repair|SheetEliminationEngine" rust/vrs_solver/src
```

A reportban írd le:

```text
- jelenlegi production path
- jelenlegi PhaseOptimizer útvonal
- milyen konkrét routing kerül be Q09-ben
```

## Implementációs irány

### 1. SolverInput kapcsoló

Adj optional input mezőt:

```rust
#[serde(default)]
pub optimizer_pipeline: Option<OptimizerPipelineKind>,
```

Javasolt enum:

```rust
#[derive(Debug, Clone, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum OptimizerPipelineKind {
    LegacyMultisheet,
    PhaseOptimizer,
}
```

Default: `LegacyMultisheet`.

### 2. Legacy path

Ha nincs `optimizer_pipeline`, vagy `legacy_multisheet`, a jelenlegi `MultiSheetManager` útvonal maradjon.

Kötelező: implicit legacy és explicit legacy ugyanarra az inputra bit-szinten vagy strukturálisan azonos outputot adjon.

### 3. Phase optimizer path

Ha `optimizer_pipeline = phase_optimizer`:

```text
same input gates: holes/margin/can_fit
expand_instances_with_policy
build_initial_layout_with_rotation_context
WorkingLayout::new
PhaseConfig { seed, rotation_context, budgets, worker_count, ... }
PhaseOptimizer::new(config).run(...)
commit validation
output build
```

A time budgetet egyszerű, determinisztikus osztással add át, például:

```text
exploration: 60%
compression: 25%
bpp: 15%
```

Elfogadható más split, de dokumentáld és teszteld. Ne legyen negatív vagy 0 alatti budget.

### 4. No silent fallback

Explicit `phase_optimizer` kérés esetén tilos legacy-re visszaesni marker nélkül.

Ha a phase output invalid:

```text
status = unsupported vagy error result a repo-stílus szerint
reason = PHASE_OPTIMIZER_COMMIT_VIOLATION vagy hasonló
```

Ne adj vissza legacy layoutot úgy, mintha phase optimizer futott volna.

### 5. Diagnostics

Adj optional output diagnosztikát vagy célzott unit tesztet, amely bizonyítja:

```text
pipeline_used = phase_optimizer
phase_optimizer_invoked = true
exploration/compression/bpp diagnostics elérhető vagy legalább tesztben ellenőrzött
```

Opcionális JSON mező megengedett, ha `skip_serializing_if = Option::is_none`.

## Kötelező tesztek

Minimum viselkedések:

```text
solver_input_optimizer_pipeline_defaults_to_legacy
legacy_explicit_matches_implicit_output
phase_optimizer_pipeline_invokes_phase_optimizer
phase_optimizer_pipeline_preserves_rotation_context
phase_optimizer_pipeline_is_deterministic_for_same_seed
phase_optimizer_pipeline_output_has_no_violations
phase_optimizer_invalid_commit_does_not_silently_fallback_to_legacy
```

A konkrét tesztnevek igazodhatnak a repo stílusához.

## Nem cél

Ne csináld most:

```text
CDE teljes implementáció
exact backend production default bekapcsolása
CollisionBackend policy teljes végigvezetése
hole/cavity semantics
DXF/preflight refaktor
új stochastic coordinate descent kereső
új LossModel algoritmus
rotation policy újratervezés
legacy default output megváltoztatása
```

## Verify

Futtasd legalább:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::phase
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::multisheet
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::working
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring.md
```

Ha bármi fail: report első sora `REVISE` vagy `BLOCKED`, és nincs `SGH-Q10_STATUS: READY`.

## Report és checklist

Hozd létre:

```text
codex/codex_checklist/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring.md
docs/egyedi_solver/sgh_q09_phase_optimizer_production_wiring_contract.md
codex/reports/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring.md
codex/reports/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring.verify.log
```

PASS esetén report első sora:

```text
PASS
```

és a végén:

```text
SGH-Q10_STATUS: READY
```
