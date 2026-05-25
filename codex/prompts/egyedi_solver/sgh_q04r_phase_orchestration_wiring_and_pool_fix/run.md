# Runner prompt — SGH-Q04R `sgh_q04r_phase_orchestration_wiring_and_pool_fix`

## Feladat

A helyi `VRS_nesting` repo gyökerében dolgozz. Hajtsd végre az SGH-Q04R corrective taskot:

```text
SGH-Q04R — Phase orchestration wiring + infeasible pool correction
```

Ez **nem új feature task**, hanem SGH-Q04 kódszintű javítás. A cél: az SGH-Q04-ben létrehozott phase/explore/compress modulok tényleg teljesítsék a Q04 contractot, és csak utána legyen érvényes az SGH-Q05 readiness.

## Production scope

Engedélyezett:

```text
rust/vrs_solver/src/optimizer/phase.rs
rust/vrs_solver/src/optimizer/explore.rs
rust/vrs_solver/src/optimizer/compress.rs
rust/vrs_solver/src/optimizer/mod.rs      # csak ha szükséges
rust/vrs_solver/src/optimizer/moves.rs    # csak ha disruption helperhez tényleg kell
```

Dokumentáció/report:

```text
docs/egyedi_solver/sgh_q04r_phase_orchestration_correction_notes.md
codex/codex_checklist/egyedi_solver/sgh_q04r_phase_orchestration_wiring_and_pool_fix.md
codex/reports/egyedi_solver/sgh_q04r_phase_orchestration_wiring_and_pool_fix.md
codex/reports/egyedi_solver/sgh_q04r_phase_orchestration_wiring_and_pool_fix.verify.log
```

Tilos:

```text
BPP phase loop / sheet elimination iteratív loop
continuous rotation / RotationPolicy teljes bevezetése
smooth LossModel / pole penetration
CollisionBackend / CDE backend
DXF/preflight
IO contract
Python runner
frontend/API
```

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
codex/reports/egyedi_solver/sgh_q04_exploration_compression_phase_orchestration.md
codex/codex_checklist/egyedi_solver/sgh_q04_exploration_compression_phase_orchestration.md
```

Auditáld a valós kódot:

```text
rust/vrs_solver/src/optimizer/phase.rs
rust/vrs_solver/src/optimizer/explore.rs
rust/vrs_solver/src/optimizer/compress.rs
rust/vrs_solver/src/optimizer/moves.rs
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/score.rs
```

## Ismert blokkolók, amelyeket ellenőrizni és javítani kell

### B1 — PhaseOptimizer stub wiring

Jelenlegi hibagyanú:

```text
PhaseOptimizer::run()
  -> self.run_exploration(...)
  -> self.run_compression(...)
```

A privát `run_exploration()` / `run_compression()` csak score-stub, nem hívja az `ExplorationPhase` és `CompressionPhase` modulokat.

Elvárt:

```text
PhaseOptimizer::run()
  -> ExplorationPhase::new(config.clone()).run(layout, parts, sheets)
  -> CompressionPhase::new(config.clone()).run(explored_layout, parts, sheets)
```

### B2 — InfeasibleSolutionPool best() ordering

Jelenlegi hibagyanú:

```text
BinaryHeap max-heap miatt best() = highest raw_loss
```

Elvárt:

```text
best() = lowest raw_loss
capacity = lowest N retained
stable tie-break = raw_loss, score, iteration, placement_order
```

A jelenlegi olyan teszt, amely `5.0, 1.0, 3.0` esetén `5.0`-t vár best-ként, hibás és javítandó.

### B3 — Fake time budget

Jelenlegi hibagyanú:

```rust
let elapsed = (iteration as f64) * 0.01;
```

Elvárt:

```text
std::time::Instant alapú elapsed mérés
```

### B4 — Disruption max_attempts + no-violation contract

Elvárt:

```text
try_disrupt() használja max_attempts értékét
determinisztikusan több párt próbál
Some(output) esetén find_violations(output).is_empty()
```

### B5 — Compression commit score mismatch

Elvárt commit sorrend:

```text
try_result -> find_violations -> score(try_result) -> commit, ha jobb
```

Nem elfogadható:

```text
new_placements score alapján döntünk, majd másik try_result-et commitolunk
```

### B6 — Hardcoded rotation list Q04-ben

Ez nem teljes RotationPolicy task, de Q04R-ben legalább ezt javítsd:

```text
rotations_to_try = part.allowed_rotations_deg
```

Ne maradjon új hardcoded `[0,90,180,270]` lista a compression logicban.

## Implementációs elvárások

1. Tartsd meg az SGH-Q04 moduláris API-ját, de javítsd a valódi működést.
2. Ne vezess be új geometriai proxyt.
3. Ne nyisd meg SGH-Q05 BPP loop scope-ot.
4. Ne nyisd meg SGH-Q06/Q07/Q08 smooth loss / rotation policy / CDE scope-ot.
5. A final layout mindig validált/no-downgrade legyen.
6. A report ne állítson többet, mint amit a kód tényleg csinál.

## Kötelező regression tesztek

Adj vagy javíts célzott Rust teszteket:

```text
phase_optimizer_invokes_real_phases_or_non_stub_diagnostics
infeasible_pool_best_returns_lowest_loss
infeasible_pool_capacity_retains_lowest_losses
phase_result_unplaced_matches_layout_unplaced
phase_result_score_matches_layout_score
large_item_swap_disruption_some_is_violation_free
compression_scores_actual_try_result_before_commit
compression_uses_part_allowed_rotations_not_hardcoded_list
same_seed_phase_optimizer_determinism
```

A tesztnevek lehetnek repo-konvenció szerintiek, de a fenti viselkedéseket bizonyítani kell.

## Verify parancsok

Futtasd:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::phase
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::explore
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::compress
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q04r_phase_orchestration_wiring_and_pool_fix.md
```

Ha bármelyik fail:

```text
report első sora: REVISE vagy BLOCKED
ne legyen SGH-Q05_STATUS marker
```

Ha minden zöld:

```text
report első sora: PASS
report vége: SGH-Q05_STATUS: READY
```

## Report elvárás

A Q04R report tartalmazza:

```text
- dependency evidence
- blocker evidence matrix B1-B6
- fixed files/functions matrix
- tests added/fixed
- before/after behavior summary
- no-downgrade and determinism evidence
- verify command outputs
- remaining quality gaps after Q04R
- explicit note: original SGH-Q04 readiness only valid after Q04R PASS
```
