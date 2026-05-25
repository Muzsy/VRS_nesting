# Runner prompt — SGH-Q05 `sgh_q05_bpp_phase_loop_sheet_elimination`

## Feladat

A helyi `VRS_nesting` repo gyökerében dolgozz. Hajtsd végre az SGH-Q05 taskot:

```text
SGH-Q05 — BPP phase loop / iterative sheet elimination
```

Ez az SGH-Q04R utáni következő implementációs lépés. A cél: a meglévő egy-pass `SheetEliminationEngine` köré épített iteratív, rollback-safe BPP phase loop, majd ennek bekötése a `PhaseOptimizer::run()` folyamatba.

## Dependency gate

Csak akkor dolgozz tovább implementációval, ha igaz:

```text
codex/reports/egyedi_solver/sgh_q04r_phase_orchestration_wiring_and_pool_fix.md létezik
első sora PASS
report tartalmazza: SGH-Q05_STATUS: READY
```

Ha nem igaz, a Q05 report első sora `BLOCKED` legyen, és ne módosíts production kódot.

## Kötelező preflight

Olvasd el:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
docs/egyedi_solver/sgh_q01_corrected_task_roadmap.md
docs/egyedi_solver/sgh_q04_phase_orchestration_contract.md
docs/egyedi_solver/sgh_q04r_phase_orchestration_correction_notes.md
codex/reports/egyedi_solver/sgh_q04r_phase_orchestration_wiring_and_pool_fix.md
codex/codex_checklist/egyedi_solver/sgh_q04r_phase_orchestration_wiring_and_pool_fix.md
```

Auditáld a valós kódot:

```text
rust/vrs_solver/src/optimizer/phase.rs
rust/vrs_solver/src/optimizer/explore.rs
rust/vrs_solver/src/optimizer/compress.rs
rust/vrs_solver/src/optimizer/sheet_elimination.rs
rust/vrs_solver/src/optimizer/multisheet.rs
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/score.rs
rust/vrs_solver/src/optimizer/stopping.rs
```

## Production scope

Engedélyezett:

```text
rust/vrs_solver/src/optimizer/bpp_phase.rs      # új modul
rust/vrs_solver/src/optimizer/mod.rs            # új modul export
rust/vrs_solver/src/optimizer/phase.rs          # PhaseConfig + PhaseOptimizer integráció
rust/vrs_solver/src/optimizer/sheet_elimination.rs # csak minimális API/diag bővítés, ha tényleg szükséges
```

Dokumentáció/report:

```text
docs/egyedi_solver/sgh_q05_bpp_phase_loop_contract.md
codex/codex_checklist/egyedi_solver/sgh_q05_bpp_phase_loop_sheet_elimination.md
codex/reports/egyedi_solver/sgh_q05_bpp_phase_loop_sheet_elimination.md
codex/reports/egyedi_solver/sgh_q05_bpp_phase_loop_sheet_elimination.verify.log
```

Tilos:

```text
continuous rotation / RotationPolicy teljes bevezetése
smooth LossModel / pole penetration
CollisionBackend / CDE backend
DXF/preflight
IO contract
Python runner
frontend/API
új external benchmark backend
```

## Implementációs cél

A Q05 után legyen ilyen flow:

```text
PhaseOptimizer::run(layout, parts, sheets)
  -> ExplorationPhase::run(...)
  -> CompressionPhase::run(...)
  -> BppPhase::run(...)
  -> final PhaseResult
```

Elfogadható, ha indokolt és tesztelt:

```text
exploration -> compression -> bpp -> compression
```

De ne legyen recursion: `BppPhase` ne hívja újra a teljes `PhaseOptimizer`-t.

## BPP phase contract

Implementálj külön BPP phase modult:

```text
rust/vrs_solver/src/optimizer/bpp_phase.rs
```

A modul a meglévő `SheetEliminationEngine`-t használja többször egymás után.

Minden attempt menete:

```text
1. incumbent snapshot
2. SheetEliminationEngine::run(...)
3. commit gate:
   - placement count invariant
   - instance set invariant
   - find_violations == []
   - compute_sheet_count_used csökken
   - sheet_count_used soha nem nő
4. success -> commit és folytatás
5. fail -> rollback exact incumbent és stop/no improvement
```

A BPP phase elsődleges célja sheet-count reduction. Azonos sheet_count mellett csak score-javulás commitolható; sheet_count növekedés soha nem commitolható.

## PhaseConfig bővítés

Bővítsd:

```rust
pub bpp_budget: PhaseBudget,
pub bpp_max_eliminations: usize,
```

Default javaslat:

```text
bpp_budget = PhaseBudget::new(16, 30.0)
bpp_max_eliminations = 16
```

A budget használata determinisztikus legyen. Tesztekben ne wall-clock érzékeny elvárást használj; kis max iteration/max elimination limittel tesztelj.

## PhaseResult konzisztencia

Q05 után is igaz legyen:

```text
result.layout == final committed layout
result.score == score(result.layout)
result.unplaced == result.layout.unplaced
result.best_score ne legyen jobb, mint a final layout valós score-ja, ha nincs hozzá tényleges layout
find_violations(result.layout.placements) == []
```

Ha `best_score` semantics eddig túl optimista volt, javítsd úgy, hogy ne hazudjon.

## Kötelező tesztek

Adj célzott Rust teszteket. Minimum viselkedések:

```text
bpp_phase_iteratively_reduces_multiple_sheets
bpp_phase_failed_attempt_rolls_back_exact_incumbent
bpp_phase_never_increases_sheet_count
bpp_phase_output_is_violation_free
phase_optimizer_invokes_bpp_phase_loop
same_seed_bpp_phase_determinism
phase_result_score_layout_consistency_after_bpp
bpp_budget_limits_attempts
```

A név igazodhat a repo stílusához, de ezek a viselkedések legyenek bizonyítva.

## Dokumentáció

Hozd létre:

```text
docs/egyedi_solver/sgh_q05_bpp_phase_loop_contract.md
```

Tartalma:

```text
- BPP phase célja
- kapcsolat: SheetEliminationEngine -> BppPhase -> PhaseOptimizer
- commit/rollback invariánsok
- score vs sheet-count döntési szabály
- determinism contract
- remaining gaps: smooth loss, RotationPolicy, CDE backend
```

## Report

Hozd létre:

```text
codex/codex_checklist/egyedi_solver/sgh_q05_bpp_phase_loop_sheet_elimination.md
codex/reports/egyedi_solver/sgh_q05_bpp_phase_loop_sheet_elimination.md
codex/reports/egyedi_solver/sgh_q05_bpp_phase_loop_sheet_elimination.verify.log
```

A report tartalmazza:

```text
- dependency evidence
- changed files/functions matrix
- BPP phase loop contract evidence
- DoD -> Evidence matrix path + line hivatkozásokkal
- tests added/fixed
- no-downgrade evidence
- determinism evidence
- verify command outputs
- remaining quality gaps
```

Ne állíts teljes Sparrow parityt. Ez csak a BPP phase loop foundation.

## Verify parancsok

Futtasd:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::bpp_phase
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::phase
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q05_bpp_phase_loop_sheet_elimination.md
```

Ha bármelyik fail:

```text
report első sora: REVISE vagy BLOCKED
ne legyen SGH-Q06_STATUS marker
```

Ha minden zöld:

```text
report első sora: PASS
report vége: SGH-Q06_STATUS: READY
```
