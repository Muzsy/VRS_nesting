# Runner prompt — SGH-Q01 `sgh_q01_sparrow_quality_migration_correction_plan`

## Feladat

A helyi `VRS_nesting` repo gyökerében dolgozz. Hajtsd végre az SGH-Q01 taskot:

```text
SGH-Q01 — Sparrow quality migration correction plan
```

Ez **audit + tervezési** task. Nem implementáció.

Cél: az SGH-Q00 parity audit alapján készíts konkrét korrekciós migrációs tervet, hogy a VRS végső nesting minősége legalább az eredeti jagua-rs/Sparrow minőségi képességszintjét elérje, és a további fejlesztés ne építsen lebutított proxykra.

---

## Dependency preflight

Ellenőrizd:

```text
codex/reports/egyedi_solver/sgh_q00_sparrow_jagua_quality_feature_parity_audit.md
```

Feltételek:

```text
első sor: PASS vagy PASS_WITH_NOTES
tartalmazza: SGH-Q01_STATUS: READY
```

Ha nem teljesül, állj meg `BLOCKED` státusszal, és csak a SGH-Q01 report/checklist dependency részét frissítsd.

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
codex/reports/egyedi_solver/sgh_q00_sparrow_jagua_quality_feature_parity_audit.md
docs/egyedi_solver/sparrowgh_vrs_migration_plan.md
docs/egyedi_solver/sgh_01_working_layout_state_contract.md
docs/egyedi_solver/sgh_02_vrs_separator_contract.md
docs/egyedi_solver/sgh_03_lbf_separator_construction_contract.md
docs/egyedi_solver/sgh_04_separator_backed_sheet_elimination_contract.md
docs/egyedi_solver/sgh_05_move_operators_contract.md
```

Auditáld hozzá a valós VRS kódot, de ne módosítsd:

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

---

## Kötelező outputok

Hozd létre:

```text
docs/egyedi_solver/sgh_q01_sparrow_quality_migration_correction_plan.md
docs/egyedi_solver/sgh_q01_corrected_task_roadmap.md
docs/egyedi_solver/sgh_q01_no_downgrade_acceptance_gates.md
codex/reports/egyedi_solver/sgh_q01_sparrow_quality_migration_correction_plan.md
codex/codex_checklist/egyedi_solver/sgh_q01_sparrow_quality_migration_correction_plan.md
```

---

## Kötelező döntések

A terv mondja ki egyértelműen:

```text
SGH-06 is paused.
SGH-01..SGH-05 are structural scaffolds, not quality parity.
No future simplified proxy is acceptable without explicit quality-risk flag and benchmark gate.
Every MISSING / PROXY / PARTIAL feature from SGH-Q00 gets a migration path.
```

---

## Kötelező roadmap tartalom

A corrected roadmap minimum fedje le:

```text
RotationPolicy / continuous rotation
CollisionBackend / CDE
LossModel / collision severity
GLS parity
weight-preserving rollback
multi-worker move_items_multi
exploration/compression orchestration
infeasible solution pool
disruption / large-item swap
geometry preprocessing/cache
BPP fixed-sheet adaptation
benchmark/acceptance parity gates
```

Minden tasknál legyen:

```text
objective
source Sparrow/jagua-rs feature
current VRS gap
dependency
allowed production files
required tests
required benchmark/acceptance gate
PASS marker
```

---

## Scope tiltás

Ne módosíts production kódot.

Tilos:

```text
Rust optimizer implementáció
Python runner módosítás
IO contract módosítás
külső source vendor/submodule
benchmark kampány futtatása
```

---

## Report

A report tartalmazzon:

```text
Dependency evidence
SGH-Q00 gap summary
Keep / stop / replace decision table for SGH-01..SGH-05
Corrected migration order
DoD -> Evidence Matrix
Risk register
Verification results
```

Ha minden zöld, a report végére:

```text
SGH-Q02_STATUS: READY
```

---

## Verify

Futtasd:

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q01_sparrow_quality_migration_correction_plan.md
```

Ha fail, a report első sora nem lehet PASS.
