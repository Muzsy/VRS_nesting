# SGH-Q04 — Exploration/compression phase orchestration

## Kontextus

SGH-Q00/Q01 után kimondtuk: az SGH-01..SGH-05 vonal csak szerkezeti scaffold, nem teljes Sparrow-parity optimalizáló.

SGH-Q02 javította a GLS súlykezelést és a rollbacket.
SGH-Q03 bevezette a Sparrow `move_items_multi()` irányú deterministic multi-worker separator branch-et.

Ez a task a következő minőségkritikus réteg: **phase orchestration**.

Nem új geometriai backend, nem continuous rotation, nem BPP sheet-elimination loop. A cél az, hogy a már meglévő separator + move scaffold fölé bekerüljön egy moduláris exploration/compression keret, amely később a teljes Sparrow-minőségű keresés alapja lesz.

## Task cél

Implementáld a VRS solverben az első VRS-natív exploration/compression orchestration réteget:

```text
1. PhaseConfig / PhaseBudget / PhaseDiagnostics / PhaseResult moduláris modell;
2. ExplorationPhase: feasible incumbent megőrzés, infeasible solution pool, disruption attempt;
3. CompressionPhase: csak valid, score-nem-rontó tömörítési/javítási próbák;
4. InfeasibleSolutionPool: bounded, loss szerint rendezett, determinisztikus tie-break;
5. LargeItemSwapDisruption: determinisztikus, top-percentile nagy alkatrészekből dolgozó perturbáció;
6. minden accepted output find_violations-mentes;
7. azonos input + seed + config → determinisztikus output;
8. no-downgrade: phase orchestrator nem adhat rosszabb valid layoutot, mint a bemeneti/baseline feasible incumbent.
```

A célzott SGH-Q00 gap-ek:

```text
F11 exploration/compression orchestration: MISSING → PARTIAL(rectangular Phase 1)
F12 infeasible solution pool: MISSING → PARTIAL(rectangular Phase 1)
F13 disruption loop: PARTIAL → PARTIAL+(phase-integrated)
F14 per-phase time budget: MISSING → PARTIAL(rectangular Phase 1)
```

## Kötelező dependency gate

SGH-Q04 csak akkor indulhat, ha:

```text
codex/reports/egyedi_solver/sgh_q03_multi_worker_move_items_multi.md
```

létezik, első sora `PASS` vagy `PASS_WITH_NOTES`, és tartalmazza:

```text
SGH-Q04_STATUS: READY
```

Ha bármely feltétel hiányzik, állj meg `BLOCKED` státusszal, és csak ezeket frissítsd:

```text
codex/reports/egyedi_solver/sgh_q04_exploration_compression_phase_orchestration.md
codex/codex_checklist/egyedi_solver/sgh_q04_exploration_compression_phase_orchestration.md
```

## Kötelező repo anchorok

Olvasd el és auditáld, ne feltételezd:

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

## Sparrow/jagua-rs source evidence

Kötelező referencia:

```text
sparrow/src/optimizer/explore.rs      exploration_phase() / Algorithm 12
sparrow/src/optimizer/compress.rs     compression_phase() / Algorithm 13
sparrow/src/config.rs                 exploration/compression time-limit config
sparrow/src/optimizer/separator.rs    separator interaction
sparrow/src/optimizer/worker.rs       move_items worker behavior
```

A reportban rögzítsd, honnan olvastad a forrást:

```text
.cache/sparrow / vendor / scripts/ensure_sparrow.sh eredmény / SGH-Q00-Q01 audit doksi
```

Ha a külső source nem elérhető, az SGH-Q00/Q01/Q03 auditban rögzített leírást használd, de ezt jelöld.

## Allowed production files

```text
rust/vrs_solver/src/optimizer/mod.rs
rust/vrs_solver/src/optimizer/phase.rs
rust/vrs_solver/src/optimizer/explore.rs
rust/vrs_solver/src/optimizer/compress.rs
rust/vrs_solver/src/optimizer/moves.rs          # csak ha disruption helperhez tényleg kell
```

Ne módosíts IO contractot, Python runnert, DXF pipeline-t, CDE/geometry backendet vagy rotation modellt.

## Kötelező implementáció

### 1. Moduláris phase API

Hozz létre új, bővíthető API-t:

```rust
// optimizer/phase.rs
pub struct PhaseConfig { ... }
pub struct PhaseBudget { ... }
pub struct PhaseDiagnostics { ... }
pub struct PhaseResult { ... }
pub enum PhaseStopReason { ... }
pub struct PhaseOptimizer { ... } // vagy repo-konvenció szerinti név
```

Elvárás:

```text
- exploration/compression idő- vagy iterációbudget külön kezelhető;
- default config determinisztikus és kis unit teszteken gyors;
- seed mező explicit;
- worker_count továbbadható a VrsSeparatorConfig felé;
- minden result tartalmazza: initial_score, best_score, phase counters, pool stats, disruption stats, stop reasons;
- a PhaseOptimizer nem kényszeríti rá magát az IO runnerre; library-level API elég, ha nincs meglévő bekötési pont.
```

### 2. ExplorationPhase

Hozz létre:

```rust
// optimizer/explore.rs
pub struct ExplorationPhase { ... }
pub struct InfeasibleSolutionPool { ... }
pub struct InfeasibleCandidate { ... }
pub struct LargeItemSwapDisruption { ... } // vagy külön privát/public helper
```

ExplorationPhase minimális, de valós működése:

```text
- bemenet: WorkingLayout + parts + sheets + PhaseConfig;
- feasible layout esetén incumbentként megőrzi;
- infeasible layout esetén VrsSeparatorral próbál javítani;
- sikertelen, de értelmes infeasible candidate-et poolba tesz;
- pool bounded capacity szerint működik;
- pool loss-ascending sorrendben tárol;
- tie-break determinisztikus: loss, score, iteration, stable placement ordering;
- stuck állapotban LargeItemSwapDisruption próbát végez;
- accepted feasible candidate csak akkor commitolható, ha validate_for_commit OK és score nem rosszabb az incumbentnál.
```

A disruption első verziója legyen egyszerű, de ne legyen véletlenszerű összevisszaság:

```text
- nagy alkatrészek kiválasztása area szerint;
- top-percentile / top-N config;
- két nagy item determinisztikus kiválasztása seed+iteration alapján;
- pozíció/sheet/rotáció swap vagy MoveExecutor meglévő try_swap használata;
- rollback-safe: hiba esetén eredeti layout marad.
```

### 3. CompressionPhase

Hozz létre:

```rust
// optimizer/compress.rs
pub struct CompressionPhase { ... }
pub struct CompressionDiagnostics { ... }
```

CompressionPhase elvárás:

```text
- mindig a legjobb feasible incumbentból indul;
- csak valid, find_violations-mentes layoutot adhat vissza;
- score-nem-rontó szabály: ha nincs javulás, az eredeti incumbentot adja vissza;
- deterministic orderben próbál tömörítési/javítási lépéseket;
- használhatja a meglévő MoveExecutor reinsert/transfer/swap primitíveket, de nem írhat saját lebutított geometriai collision backendet;
- reportban dokumentálja, hogy ez rectangular Phase 1 compression, nem teljes Sparrow compression parity.
```

A compression mérhető legyen legalább ezekkel:

```text
- best_score <= initial_score;
- bounding extent / compactness proxy nem nő, ha a compression commitol;
- minden commit után validate_for_commit OK.
```

### 4. PhaseOptimizer orchestration

A phase orchestrator sorrendje:

```text
1. input WorkingLayout score + validation;
2. ExplorationPhase futtatása;
3. legjobb feasible incumbent kiválasztása;
4. CompressionPhase futtatása az incumbentból;
5. végső PhaseResult visszaadása;
6. ha bármi nem javít, baseline feasible incumbent rollback-safe módon megmarad.
```

A `PhaseOptimizer` nem vállalhat olyan ígéretet, amit nem teljesít. Ha egy feature csak rectangular Phase 1 szintű, akkor a contract és report ezt írja.

### 5. Tilos megnyitni ebben a taskban

```text
BPP phase loop / sheet elimination iteratív loop  # SGH-Q05 lesz
continuous rotation / RotationPolicy             # SGH-Q07 lesz
smooth LossModel / pole penetration              # SGH-Q06 lesz
CollisionBackend / CDE backend                   # SGH-Q08 lesz
DXF/preflight módosítás
IO contract módosítás
Python runner módosítás
külső Sparrow backendként futtatása
runtime speedup ígérgetése bizonyíték nélkül
```

## Kötelező tesztek

Adj Rust unit teszteket legalább ezekre:

```text
1. dependency/config smoke: PhaseConfig default determinisztikus, budgets külön kezeltek.
2. InfeasibleSolutionPool capacity + loss-ascending order + deterministic tie-break.
3. Exploration preserves feasible incumbent: valid input esetén nem ad rosszabb score-t.
4. Exploration stores infeasible candidate when separator cannot fully repair, de accepted output nem lesz infeasible.
5. LargeItemSwapDisruption top-percentile nagy itemeket választ, same seed → same pair.
6. Compression no-downgrade: best_score <= initial_score, vagy unchanged baseline.
7. Compression accepted output find_violations-mentes.
8. Full PhaseOptimizer same seed determinism: azonos input + seed + config → bit-identical placements/diagnostics.
9. Phase budget gate: max_iterations/zero budget esetén dokumentált stop reason.
10. Parity non-regression table: F11-F14 nem romlik, F11/F12/F14 legalább PARTIAL.
```

## Benchmark / acceptance gate

Futtasd legalább:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml phase explore compress
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q04_exploration_compression_phase_orchestration.md
```

A reportban legyen külön összehasonlítás:

```text
Fixture: rectangular 30+ item congested fixture
Baseline/no-phase: score, valid, sheet_count, utilization/compactness proxy
Phase optimizer: score, valid, sheet_count, utilization/compactness proxy, pool_size, disruptions_attempted, disruptions_accepted
Acceptance: phase score <= baseline score; accepted output violations == 0; same seed deterministic
```

Ne hazudj Sparrow-parityt. Ez csak az orchestration foundation; a teljes smooth loss / rotation / CDE paritás későbbi task.

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
