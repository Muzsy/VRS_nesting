# Runner prompt — SGH-Q03 `sgh_q03_multi_worker_move_items_multi`

## Feladat

A helyi `VRS_nesting` repo gyökerében dolgozz. Hajtsd végre az SGH-Q03 taskot:

```text
SGH-Q03 — Multi-worker move_items_multi
```

Ez implementációs task, de szűk scope-pal. A cél a meglévő `VrsSeparator` belső move keresésének bővítése Sparrow `move_items_multi()` irányba.

**Production scope:**

```text
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/Cargo.toml        # csak ha rayon/RNG dependency tényleg kell
```

**Dokumentáció/report/checklist scope:**

```text
docs/egyedi_solver/sgh_q03_multi_worker_move_items_multi_contract.md
codex/codex_checklist/egyedi_solver/sgh_q03_multi_worker_move_items_multi.md
codex/reports/egyedi_solver/sgh_q03_multi_worker_move_items_multi.md
```

---

## Dependency preflight

Ellenőrizd:

```text
codex/reports/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback.md
```

Feltételek:

```text
első sor: PASS vagy PASS_WITH_NOTES
tartalmazza: SGH-Q03_STATUS: READY
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
docs/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback_contract.md
codex/reports/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback.md
```

Auditáld a valós kódot:

```text
rust/vrs_solver/Cargo.toml
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/candidates.rs
rust/vrs_solver/src/optimizer/boundary.rs
rust/vrs_solver/src/optimizer/moves.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/io.rs
```

Auditáld a referencia Sparrow logikát, ha elérhető:

```text
sparrow/optimizer/separator.rs move_items_multi()
sparrow/optimizer/worker.rs move_items()
```

---

## Implementációs követelmény

### 1. Config

Bővítsd a `VrsSeparatorConfig`-ot default mezőkkel:

```text
worker_count: usize   # default 1
seed: u64             # default 0 vagy dokumentált determinisztikus default
```

Kötelező:

```text
worker_count=1 → SGH-Q02 single-worker kompatibilis ág
worker_count=0 → nem pánikol; normalizált 1 vagy dokumentált guard
azonos seed + azonos input + azonos worker_count → bit-identikus output
meglévő public mezők és ..Default struct update nem törhetnek
```

### 2. Worker modell

Implementálj explicit worker/candidate modellt `separator.rs` alatt:

```text
SeparatorWorker / WorkerCandidate vagy ekvivalens privát típusok
```

A worker:

```text
master WorkingLayout snapshotból indul
master VrsCollisionTracker állapotból indul, GLS súlyekkel együtt
saját seedelt shuffled colliding item sorrendet kap
legalább egy javító vagy legjobb elérhető move candidate-et próbál
candidate layoutot, tracker állapotot, raw loss-t, weighted loss-t és diagnostics adatokat ad vissza
nem használ közös mutable állapotot
```

### 3. `move_items_multi`

A `VrsSeparator::run()` logikáját úgy alakítsd, hogy:

```text
worker_count <= 1: single-worker SGH-Q02 behavior
worker_count > 1: multi-worker behavior
```

A multi-worker ág:

```text
N workert indít ugyanarról a master állapotról
minden worker más seedelt item-sorrendet próbál
ha rayon elérhető és stabilan buildel, használd rayon par_iter alapú futtatásra
ha dependency miatt nem indokolt a rand, használj kis privát determinisztikus Fisher-Yates shuffle helper-t
az eredmények összegyűjtése után stabil, thread-scheduling-független tie-break választ
csak javító candidate-et commitol
nem rontja el a restore_but_keep_weights és GLS update logikát
```

Ajánlott tie-break:

```text
1. kisebb raw loss
2. kisebb weighted loss
3. több accepted move
4. kisebb worker_id
5. stabil placement ordering hash/tuple
```

### 4. Tilos megnyitni

Ebben a taskban tilos:

```text
exploration/compression phase orchestration
infeasible solution pool
large-item disruption loop
BPP phase loop
continuous rotation
RotationPolicy trait
smooth LossModel / pole penetration
CollisionBackend / CDE backend
DXF/preflight módosítás
Python runner módosítás
IO contract módosítás
külső Sparrow backendként futtatása
```

---

## Kötelező tesztek

Adj vagy frissíts unit teszteket legalább ezekre:

```text
1. worker_count=1 backward compatibility: egyszerű overlap fixture továbbra is best_loss == 0.0 és valid.
2. worker_count=0 guard/normalizálás: nem pánikol.
3. worker_count=3 same seed determinism: azonos input + seed + worker_count → bit-identical output/diagnostics.
4. shuffled order helper smoke: eltérő worker_id/seed eltérő, de determinisztikus sorrendet tud adni.
5. 3-worker dense 20+ item fixture best_loss <= 1-worker best_loss.
6. 3-worker accepted output find_violations-mentes, ha best_loss == 0.0.
7. tie-break deterministic fixture: azonos score esetén stabil worker választás.
```

---

## Contract dokumentáció

Hozd létre:

```text
docs/egyedi_solver/sgh_q03_multi_worker_move_items_multi_contract.md
```

Kötelező szekciók:

```text
# SGH-Q03 multi-worker move_items_multi contract
## Decision
## Source Sparrow feature mapping
## VRS implementation summary
## Config semantics
## Worker model
## Determinism and seed contract
## Candidate selection and tie-break contract
## Rollback and GLS weight handling
## Tests and acceptance gates
## Remaining quality gaps after SGH-Q03
## Next task: SGH-Q04
```

---

## Report és checklist

Hozd létre/frissítsd:

```text
codex/codex_checklist/egyedi_solver/sgh_q03_multi_worker_move_items_multi.md
codex/reports/egyedi_solver/sgh_q03_multi_worker_move_items_multi.md
```

A report tartalmazzon:

```text
Dependency evidence
Source evidence
Current-state audit
Change summary
Config semantics
Worker model summary
Determinism contract
F09 parity status update
No-downgrade gates G01-G08
Tests run + exact command output summary
1-worker vs 3-worker dense fixture comparison
Scope safety
DoD -> Evidence Matrix
```

Ha minden zöld, a report végén legyen:

```text
SGH-Q04_STATUS: READY
```

---

## Verify

Futtasd legalább:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml separator
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q03_multi_worker_move_items_multi.md
```

Ha bármelyik fail, a report első sora nem lehet PASS.
