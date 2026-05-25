# Runner prompt — SGH-Q04 `sgh_q04_exploration_compression_phase_orchestration`

## Feladat

A helyi `VRS_nesting` repo gyökerében dolgozz. Hajtsd végre az SGH-Q04 taskot:

```text
SGH-Q04 — Exploration/compression phase orchestration
```

Ez implementációs task, de **nem** geometry/rotation/backend task. A cél a meglévő SGH-Q02/Q03 separator + SGH-05 move scaffold fölé egy moduláris, Sparrow-irányú phase orchestration alapréteg bevezetése.

**Production scope:**

```text
rust/vrs_solver/src/optimizer/mod.rs
rust/vrs_solver/src/optimizer/phase.rs
rust/vrs_solver/src/optimizer/explore.rs
rust/vrs_solver/src/optimizer/compress.rs
rust/vrs_solver/src/optimizer/moves.rs          # csak ha disruption helperhez tényleg kell
```

**Dokumentáció/report/checklist scope:**

```text
docs/egyedi_solver/sgh_q04_phase_orchestration_contract.md
codex/codex_checklist/egyedi_solver/sgh_q04_exploration_compression_phase_orchestration.md
codex/reports/egyedi_solver/sgh_q04_exploration_compression_phase_orchestration.md
```

---

## Dependency preflight

Ellenőrizd:

```text
codex/reports/egyedi_solver/sgh_q03_multi_worker_move_items_multi.md
```

Feltételek:

```text
első sor: PASS vagy PASS_WITH_NOTES
tartalmazza: SGH-Q04_STATUS: READY
```

Ha nem teljesül, állj meg `BLOCKED` státusszal, és csak a report/checklist dependency részét frissítsd.

---

## Kötelező olvasmányok

Olvasd el:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
docs/egyedi_solver/sgh_q00_sparrow_jagua_quality_feature_parity_audit.md
docs/egyedi_solver/sgh_q00_quality_feature_gap_matrix.md
docs/egyedi_solver/sgh_q00_modular_architecture_principles.md
docs/egyedi_solver/sgh_q01_sparrow_quality_migration_correction_plan.md
docs/egyedi_solver/sgh_q01_corrected_task_roadmap.md
docs/egyedi_solver/sgh_q01_no_downgrade_acceptance_gates.md
docs/egyedi_solver/sgh_q03_multi_worker_move_items_multi_contract.md
codex/reports/egyedi_solver/sgh_q03_multi_worker_move_items_multi.md
```

Auditáld a valós kódot:

```text
rust/vrs_solver/src/optimizer/mod.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/moves.rs
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/score.rs
rust/vrs_solver/src/optimizer/stopping.rs
rust/vrs_solver/src/optimizer/sheet_elimination.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/io.rs
```

Auditáld a referencia Sparrow logikát, ha elérhető:

```text
sparrow/src/optimizer/explore.rs
sparrow/src/optimizer/compress.rs
sparrow/src/config.rs
sparrow/src/optimizer/separator.rs
sparrow/src/optimizer/worker.rs
```

---

## Implementációs követelmények

### 1. Phase API

Hozz létre `optimizer/phase.rs` modult.

Minimum elvárt modellek:

```text
PhaseConfig
PhaseBudget
PhaseDiagnostics
PhaseResult
PhaseStopReason
PhaseOptimizer vagy repo-konvenció szerinti ekvivalens orchestrator
```

Elvárás:

```text
exploration/compression külön budget
seed explicit
worker_count továbbadható VrsSeparatorConfig felé
deterministic default config
result tartalmaz initial_score, best_score, pool/disruption counters, stop reasons
```

### 2. ExplorationPhase + infeasible pool

Hozz létre `optimizer/explore.rs` modult.

Minimum elvárt modellek:

```text
ExplorationPhase
InfeasibleSolutionPool
InfeasibleCandidate
LargeItemSwapDisruption vagy ekvivalens helper
```

Elvárás:

```text
feasible incumbent megőrzése
VrsSeparator használata infeasible candidate javításra
sikertelen/de ígéretes infeasible candidate poolba tétele
bounded pool capacity
loss-ascending deterministic ordering
stable tie-break: loss, score, iteration, placement ordering
rollback-safe disruption
```

### 3. CompressionPhase

Hozz létre `optimizer/compress.rs` modult.

Elvárás:

```text
feasible incumbentból indul
csak score-nem-rontó candidate commitolható
accepted output find_violations-mentes
ha nincs javulás, eredeti incumbent marad
nem vezet be új geometry/collision proxyt
```

### 4. Orchestration flow

A `PhaseOptimizer` flow:

```text
1. input WorkingLayout score + validation
2. ExplorationPhase
3. best feasible incumbent kiválasztás
4. CompressionPhase
5. final PhaseResult
6. no-downgrade rollback: ha nincs javulás, baseline feasible incumbent marad
```

### 5. Tilos ebben a taskban

```text
BPP phase loop / sheet elimination iteratív loop
continuous rotation / RotationPolicy
smooth LossModel / pole penetration
CollisionBackend / CDE backend
DXF/preflight módosítás
IO contract módosítás
Python runner módosítás
külső Sparrow backendként futtatása
```

---

## Kötelező tesztek

Adj vagy frissíts unit teszteket legalább ezekre:

```text
1. PhaseConfig default/budget smoke.
2. InfeasibleSolutionPool capacity + loss ordering + deterministic tie-break.
3. Exploration preserves feasible incumbent and does not worsen score.
4. Exploration can store infeasible candidate without accepting infeasible output.
5. LargeItemSwapDisruption selects top-percentile large items deterministically.
6. Compression no-downgrade: best_score <= initial_score or unchanged baseline.
7. Compression accepted output find_violations == empty.
8. Full PhaseOptimizer same seed determinism.
9. Phase budget stop reason.
10. F11-F14 parity update documented in report.
```

---

## Contract dokumentáció

Hozd létre:

```text
docs/egyedi_solver/sgh_q04_phase_orchestration_contract.md
```

Kötelező szekciók:

```text
# SGH-Q04 phase orchestration contract
## Decision
## Source Sparrow feature mapping
## VRS adaptation boundary
## Public API
## PhaseConfig and budgets
## ExplorationPhase contract
## InfeasibleSolutionPool contract
## LargeItemSwapDisruption contract
## CompressionPhase contract
## Determinism and seed contract
## Score/no-downgrade contract
## Validation and commit gates
## Tests and acceptance gates
## Remaining quality gaps after SGH-Q04
## Next task: SGH-Q05
```

---

## Report és checklist

Hozd létre/frissítsd:

```text
codex/codex_checklist/egyedi_solver/sgh_q04_exploration_compression_phase_orchestration.md
codex/reports/egyedi_solver/sgh_q04_exploration_compression_phase_orchestration.md
```

A report tartalmazzon:

```text
Dependency evidence
Source evidence
Current-state audit
Change summary
Public API summary
Exploration/compression behavior summary
Infeasible pool summary
Disruption summary
Determinism contract
F11-F14 parity status update
No-downgrade gates G01-G08
Tests run + exact command output summary
Baseline vs phase fixture comparison
Scope safety
DoD -> Evidence Matrix
Advisory notes
```

Ha minden zöld, a report végén legyen:

```text
SGH-Q05_STATUS: READY
```

---

## Verify

Futtasd legalább:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml phase explore compress
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q04_exploration_compression_phase_orchestration.md
```

Ha bármelyik fail, a report első sora nem lehet PASS.
