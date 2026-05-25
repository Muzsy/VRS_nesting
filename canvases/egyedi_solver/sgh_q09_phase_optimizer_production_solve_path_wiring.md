# SGH-Q09 — PhaseOptimizer production solve-path wiring

## Státusz

Implementációs task, SGH-Q08R után.

## Előfeltétel

Kötelező:

```text
codex/reports/egyedi_solver/sgh_q08r_exact_backend_no_silent_downgrade_fix.md
```

Első sor: `PASS`, és a report végén legyen:

```text
SGH-Q09_STATUS: READY
```

Ha ez nincs meg, állj meg `BLOCKED` reporttal, production kódmódosítás nélkül.

## Miért kell ez?

Az SGH-Q02–Q08R sorozat több minőségkritikus komponenst hozott létre:

```text
GLS rollback + súlymegőrzés
multi-worker separator
exploration/compression phase orchestration
infeasible solution pool / disruption
iteratív BPP sheet elimination
LossModel foundation
RotationPolicy foundation
CollisionBackend foundation
```

Kódszintű audit alapján viszont a tényleges `adapter::solve()` Phase1 production útvonala továbbra is főleg a régi `MultiSheetManager` folyamaton fut:

```text
build_initial_layout_with_rotation_context
run_repair_with_rotation_context
SheetEliminationEngine
```

Ez azt jelenti, hogy a `PhaseOptimizer` és a Q04/Q05 orchestration réteg jelenleg részben library/test útvonal, nem teljes production solve-path. A Q09 célja ezt kijavítani, de rollback-safe módon.

## Cél

Vezess be egy explicit, opt-in production pipeline kapcsolót, amelyen keresztül a Phase1 solver a `PhaseOptimizer` útvonalat tudja futtatni.

Kötelező elv:

```text
alapértelmezett viselkedés változatlan marad
új phase optimizer path csak explicit opt-in
nincs silent fallback quality pipeline hibánál
minden accepted output violation-free
azonos input + azonos seed = azonos output
```

## Kapcsolódó SGH-Q00/Q01 gap

```text
F09 — move_items_multi / multi-worker
F11 — exploration/compression phases
F12 — infeasible solution pool
F13 — perturbation/disruption
F14 — phase time budget
F16 — BPP/bin reduction loop
```

A Q09 nem új algoritmust ír. A meglévő komponenseket köti be a valós solve-pathba.

## Scope

### Engedélyezett production fájlok

```text
rust/vrs_solver/src/io.rs                         # input/output opt-in pipeline mező, optional diagnostics ha kell
rust/vrs_solver/src/adapter.rs                    # production routing legacy vs phase_optimizer
rust/vrs_solver/src/optimizer/phase.rs            # csak config/helper/diagnostics, ha szükséges
rust/vrs_solver/src/optimizer/working.rs          # csak commit helper, ha szükséges
rust/vrs_solver/src/optimizer/initializer.rs      # csak helper export/refactor, ha szükséges
rust/vrs_solver/src/optimizer/multisheet.rs       # csak teszt/helper refactor, ha szükséges
rust/vrs_solver/src/optimizer/repair.rs           # csak validation helper, ha szükséges
```

### Engedélyezett artefaktok

```text
canvases/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q09_phase_optimizer_production_solve_path_wiring.yaml
codex/prompts/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring/run.md
codex/codex_checklist/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring.md
codex/reports/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring.md
codex/reports/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring.verify.log
docs/egyedi_solver/sgh_q09_phase_optimizer_production_wiring_contract.md
```

### Tiltott scope

```text
CDE teljes implementáció
exact backend production default bekapcsolása
hole/cavity semantics
DXF/preflight refaktor
új stochastic coordinate descent kereső
új LossModel algoritmus
rotation policy újratervezés
output contract breaking change
legacy default viselkedés megváltoztatása
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
codex/reports/egyedi_solver/sgh_q08r_exact_backend_no_silent_downgrade_fix.md
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/optimizer/multisheet.rs
rust/vrs_solver/src/optimizer/phase.rs
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/optimizer/repair.rs
```

Futtasd és tedd a reportba a rövid eredményt:

```bash
rg -n "PhaseOptimizer|PhaseConfig|MultiSheetManager::new|find_violations\(|run_repair|SheetEliminationEngine" rust/vrs_solver/src
```

A reportban külön válaszold meg:

```text
- hol fut jelenleg production solve path?
- hol létezik PhaseOptimizer csak library/test útként?
- pontosan milyen opt-in kapcsolóval kerül be a PhaseOptimizer?
```

## Kötelező implementáció

### 1. Pipeline enum / input kapcsoló

Adj backward-compatible input mezőt, például:

```rust
#[derive(Debug, Clone, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum OptimizerPipelineKind {
    LegacyMultisheet,
    PhaseOptimizer,
}
```

`SolverInput`:

```rust
#[serde(default)]
pub optimizer_pipeline: Option<OptimizerPipelineKind>,
```

Default: `LegacyMultisheet`.

Elfogadható alternatíva: repo-stílushoz jobban illeszkedő név, de a JSON érték legyen egyértelmű és snake_case.

### 2. Legacy path változatlanul marad

Ha nincs `optimizer_pipeline`, vagy `legacy_multisheet`, akkor a jelenlegi `adapter::solve()` viselkedés ne változzon.

Kötelező teszt:

```text
same Phase1 input legacy implicit vs legacy explicit -> azonos placements/unplaced/metrics/score_breakdown
```

### 3. Phase optimizer opt-in path

Ha:

```json
"solver_profile": "jagua_optimizer_phase1_outer_only",
"optimizer_pipeline": "phase_optimizer"
```

akkor:

```text
1. input gate-ek ugyanazok: holes/margin/can_fit prefilter
2. build_initial_layout_with_rotation_context(...) adja a seed layoutot
3. WorkingLayout::new(...)
4. PhaseConfig a valós inputból:
   - seed = input.seed
   - rotation_context = már létrehozott global/part-level context
   - budgets time_limit_s alapján determinisztikusan osztva
   - worker_count default legalább 1, ne törje a determinismet
5. PhaseOptimizer::new(config).run(...)
6. final WorkingLayout validate_and_commit vagy equivalent validation gate
7. accepted output csak violation-free lehet
```

Fontos: ha a phase optimizer output invalid, ne fallbackelj csendben legacy-re. Report/teszt szinten legyen explicit hiba vagy unsupported/partial kezelés.

### 4. Optional diagnostics

Ha szükséges a bizonyításhoz, adj optional output diagnosztikát, például:

```rust
#[serde(skip_serializing_if = "Option::is_none")]
pub optimizer_diagnostics: Option<OptimizerDiagnosticsOutput>
```

Minimum mezők:

```text
pipeline_used
phase_optimizer_invoked
exploration_iterations
compression_iterations
bpp_attempts vagy bpp_iterations
```

Ez opcionális mezőként nem breaking change. Ha nem adsz output mezőt, akkor unit teszttel bizonyítsd, hogy a phase path tényleg meghívódik.

### 5. No silent downgrade

Quality pipeline esetén tilos:

```text
phase_optimizer kérés -> legacy futtatás marker nélkül
phase optimizer invalid output -> legacy fallback
PhaseConfig.rotation_context elvesztése
seed elvesztése
```

## Kötelező tesztek

Minimum Rust tesztek:

```text
solver_input_optimizer_pipeline_defaults_to_legacy
legacy_explicit_matches_implicit_output
phase_optimizer_pipeline_invokes_phase_optimizer
phase_optimizer_pipeline_preserves_rotation_context
phase_optimizer_pipeline_is_deterministic_for_same_seed
phase_optimizer_pipeline_output_has_no_violations
phase_optimizer_invalid_commit_does_not_silently_fallback_to_legacy
```

A tesztnevek igazodhatnak a repo-stílushoz, de ezek a viselkedések legyenek lefedve.

## Acceptance gate

PASS csak akkor lehet, ha:

```text
- dependency gate PASS
- default legacy output backward-compatible
- explicit phase_optimizer path tényleg PhaseOptimizert futtat
- no silent fallback bizonyított
- no violation gate zöld
- determinism gate zöld
- cargo test --lib PASS
- teljes verify PASS
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

Ha bármelyik fail, report első sora `REVISE` vagy `BLOCKED`, és nincs következő marker.

## Report

Hozd létre:

```text
codex/codex_checklist/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring.md
docs/egyedi_solver/sgh_q09_phase_optimizer_production_wiring_contract.md
codex/reports/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring.md
codex/reports/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring.verify.log
```

PASS esetén a report első sora:

```text
PASS
```

és a végén:

```text
SGH-Q10_STATUS: READY
```

## Q10 előkészítő megjegyzés

Q09 után a következő logikus task: `CollisionBackendKind` / backend policy végigvezetése a phase/search/commit validation pathon. Q09 ezt még ne oldja meg teljesen, csak ne nehezítse meg.
