# SGH-Q01 — Sparrow quality migration correction plan

## Kontextus

SGH-Q00 PASS lett, és kimondta a lényeget: a VRS SGH-01..SGH-05 irány hasznos szerkezeti vázat adott, de több minőségkritikus jagua-rs/Sparrow funkciót **MISSING / PROXY / PARTIAL** szinten kezel.

A cél most nem újabb proxy implementáció. A cél egy konkrét, végrehajtható korrekciós migrációs terv, amely biztosítja:

```text
VRS végső optimizer minősége >= eredeti jagua-rs/Sparrow minőségi képességszintje
```

## Task cél

Készíts korrekciós migrációs tervet az SGH-Q00 audit alapján.

A terv:

```text
1. megtartandó SGH-01..SGH-05 szerkezeti elemeket azonosít;
2. proxy / missing elemek cseréjének sorrendjét adja;
3. moduláris target architektúrát ad;
4. konkrét SGH-Q02.. taskláncra bontja a munkát;
5. no-downgrade szabályokat ír elő;
6. benchmark / acceptance gate-eket rendel minden minőségkritikus funkcióhoz.
```

## Kötelező dependency gate

SGH-Q01 csak akkor indulhat, ha:

```text
codex/reports/egyedi_solver/sgh_q00_sparrow_jagua_quality_feature_parity_audit.md
```

létezik, első sora `PASS` vagy `PASS_WITH_NOTES`, és tartalmazza:

```text
SGH-Q01_STATUS: READY
```

Ha nem teljesül, állj meg `BLOCKED` státusszal, és csak a report/checklist dependency evidence részét frissítsd.

## Kötelező input doksik

Olvasd el:

```text
docs/egyedi_solver/sgh_q00_sparrow_jagua_quality_feature_parity_audit.md
docs/egyedi_solver/sgh_q00_quality_feature_gap_matrix.md
docs/egyedi_solver/sgh_q00_modular_architecture_principles.md
codex/reports/egyedi_solver/sgh_q00_sparrow_jagua_quality_feature_parity_audit.md
docs/egyedi_solver/sparrowgh_vrs_migration_plan.md
docs/egyedi_solver/sgh_01_working_layout_state_contract.md
docs/egyedi_solver/sgh_02_vrs_separator_contract.md
docs/egyedi_solver/sgh_03_lbf_separator_construction_contract.md
docs/egyedi_solver/sgh_04_separator_backed_sheet_elimination_contract.md
docs/egyedi_solver/sgh_05_move_operators_contract.md
```

Auditáld hozzá a valós kód anchorokat:

```text
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/optimizer/sheet_elimination.rs
rust/vrs_solver/src/optimizer/moves.rs
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/optimizer/candidates.rs
rust/vrs_solver/src/optimizer/boundary.rs
rust/vrs_solver/src/optimizer/score.rs
rust/vrs_solver/src/optimizer/stopping.rs
```

## Kötelező tervszakaszok

Hozd létre:

```text
docs/egyedi_solver/sgh_q01_sparrow_quality_migration_correction_plan.md
docs/egyedi_solver/sgh_q01_corrected_task_roadmap.md
docs/egyedi_solver/sgh_q01_no_downgrade_acceptance_gates.md
```

### `sgh_q01_sparrow_quality_migration_correction_plan.md`

Kötelező szekciók:

```text
# SGH-Q01 Sparrow quality migration correction plan

## Decision
## What SGH-01..SGH-05 gives us
## What must be stopped
## What must be replaced
## Target modular architecture
## RotationPolicy track
## CollisionBackend / CDE track
## LossModel / collision severity track
## GLS / separator parity track
## move_items_multi / multi-worker track
## exploration + compression orchestration track
## infeasible pool + disruption track
## geometry preprocessing/cache track
## BPP / fixed sheet adaptation
## Benchmark and acceptance strategy
## Migration order
## Risk register
```

### `sgh_q01_corrected_task_roadmap.md`

Kötelezően bontsa le SGH-Q02.. taskokra, minimum:

```text
SGH-Q02 — RotationPolicy + RotationRange parity plan / scaffold
SGH-Q03 — CollisionBackend abstraction + quality-risk proxy flags
SGH-Q04 — LossModel abstraction + smooth collision severity migration
SGH-Q05 — GLS parity + weight-preserving rollback
SGH-Q06 — multi-worker / move_items_multi separator migration
SGH-Q07 — exploration/compression PhaseOrchestrator
SGH-Q08 — infeasible solution pool + disruption strategy
SGH-Q09 — jagua-rs CDE backend feasibility / adapter plan
SGH-Q10 — benchmark suite: VRS vs Sparrow parity gates
```

A tasklánc módosítható, de csak SGH-Q00 bizonyíték alapján.

### `sgh_q01_no_downgrade_acceptance_gates.md`

Kötelezően tartalmazza:

```text
- no hardcoded rotation list without RotationPolicy
- no hardcoded AABB collision without CollisionBackend quality flag
- no binary boundary/loss proxy without LossModel quality flag
- no proxy accepted as final parity without benchmark
- every future SGH task must list: Sparrow feature, VRS equivalent, parity target, tests, benchmark gate
```

## Explicit döntések

A reportban mondd ki:

```text
SGH-06 solution pool / perturbation task is paused until SGH-Q02..Q06 foundations are planned.
SGH-01..SGH-05 are structural scaffolds, not final quality-parity implementation.
No further simplified proxy implementation may proceed without SGH-Q01 gates.
```

## Nem-cél

SGH-Q01 audit/terv task. Ne módosíts production Rust kódot.

Tilos:

```text
- production kód módosítása
- új solver funkció implementálása
- külső Sparrow backend bekötése
- vendor/submodule hozzáadás
- benchmark kampány futtatása
```

## Acceptance

PASS csak akkor adható, ha:

```text
- SGH-Q00 dependency gate zöld;
- mindhárom SGH-Q01 doksi elkészült;
- roadmap konkrét, sorrendezett és végrehajtható;
- no-downgrade gate-ek konkrétak;
- minden MISSING/PROXY/PARTIAL feature kap migration decisiont;
- report DoD -> Evidence Matrixot tartalmaz;
- verify zöld;
- report végén: SGH-Q02_STATUS: READY.
```
