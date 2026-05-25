# Runner prompt — SGH-Q00 `sgh_q00_sparrow_jagua_quality_feature_parity_audit`

## Feladat

A helyi `VRS_nesting` repo gyökerében dolgozz. Hajtsd végre az SGH-Q00 auditot:

```text
SGH-Q00 — Sparrow/jagua-rs quality-feature parity audit
```

Ez audit/report task. **Ne implementálj production kódot. Ne vendorolj külső forrást. Ne építs külső SparrowGH backendet.**

A cél: kódszintű bizonyíték alapján megállapítani, milyen nesting-minőségjavító funkciókat tartalmaz az eredeti `jagua-rs` / `Sparrow`, ezekből mit vett át a VRS, mit butított le, és mit kell teljesen vagy VRS-kompatibilisen portolni ahhoz, hogy legalább az eredeti minőségi szintet célozzuk.

## Dependency preflight

Ellenőrizd:

```text
codex/reports/egyedi_solver/sgh_05_transfer_swap_reinsert_move_operators.md
```

Elvárás:

```text
első sor: PASS vagy PASS_WITH_NOTES
tartalmazza: SGH-06_STATUS: READY
```

Ha nem teljesül, állj meg `BLOCKED` státusszal.

## Kötelező olvasmányok

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
docs/egyedi_solver/sparrow_sparrowgh_code_audit.md
docs/egyedi_solver/sparrowgh_vrs_migration_plan.md
docs/egyedi_solver/sgh_01_working_layout_state_contract.md
docs/egyedi_solver/sgh_02_vrs_separator_contract.md
docs/egyedi_solver/sgh_03_lbf_separator_construction_contract.md
docs/egyedi_solver/sgh_04_separator_backed_sheet_elimination_contract.md
docs/egyedi_solver/sgh_05_move_operators_contract.md
```

## Külső source audit

Clone-olj/olvass repo-n kívül, például:

```bash
mkdir -p /tmp/vrs_sparrow_quality_audit
cd /tmp/vrs_sparrow_quality_audit
git clone https://github.com/JeroenGar/jagua-rs.git JeroenGar_jagua_rs
git clone https://github.com/JeroenGar/sparrow.git JeroenGar_sparrow
git clone https://github.com/coroush/sparrow.git coroush_sparrow || true
git clone https://github.com/coroush/sparrow-grasshopper.git coroush_sparrow_grasshopper || true
```

Rögzítsd minden forráshoz:

```text
repo URL
commit hash / ref
license
relevant files
unavailable / NOT_FOUND / NETWORK_BLOCKED státusz
```

## Audit fókusz

Kódból, file-by-file bizonyítsd legalább ezeket:

```text
RotationRange / continuous/discrete rotation
continuous sampling + local rotation wiggle/refinement
transformation model
jagua-rs CDE / exact shape collision usage
collision severity / penetration / smooth loss
shape-based penalty
GLS dynamic weights
separator incumbent / restore / strike / best-state
move_items_multi / multi-worker / multi-order logic
BLF/LBF role
exploration/compression phases
infeasible solution pool
perturbation / disruption / large-item swap
time budget / phase split
seed determinism
BPP/bin reduction logic in forks if present
geometry caching / preprocessing / simplification
irregular container/remnant support
```

## VRS comparison

Auditáld a VRS oldalt:

```text
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/optimizer/sheet_elimination.rs
rust/vrs_solver/src/optimizer/moves.rs
rust/vrs_solver/src/optimizer/score.rs
rust/vrs_solver/src/optimizer/candidates.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/adapter.rs
```

Minden minőségfunkcióhoz tölts ki gap mátrixot:

```text
Feature
Sparrow/jagua-rs source evidence
VRS current equivalent
Parity status: FULL / PARTIAL / PROXY / MISSING / WRONG
Quality risk
Required migration strategy
Required tests
Required benchmark
Modularity requirement
```

## Tiltott következtetés

Ne írj olyat, hogy „később jó lesz”, bizonyíték nélkül. Ha a VRS proxy gyengébb, mondd ki.

## Kötelező kimenetek

Hozd létre/frissítsd:

```text
docs/egyedi_solver/sgh_q00_sparrow_jagua_quality_feature_parity_audit.md
docs/egyedi_solver/sgh_q00_quality_feature_gap_matrix.md
docs/egyedi_solver/sgh_q00_modular_architecture_principles.md
codex/codex_checklist/egyedi_solver/sgh_q00_sparrow_jagua_quality_feature_parity_audit.md
codex/reports/egyedi_solver/sgh_q00_sparrow_jagua_quality_feature_parity_audit.md
```

## Moduláris architektúra elvek

A `sgh_q00_modular_architecture_principles.md` mondja ki:

```text
- rotation policy provider külön modul
- geometry/collision backend külön modul
- collision severity / loss model külön modul
- search phase orchestration külön modul
- separator / move / sheet-elimination ne tartalmazzon hardcoded lebutított rotation/collision feltételezést
- minden proxy csak explicit, mérhető quality-risk flaggel létezhet
```

## Verify

Futtasd:

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q00_sparrow_jagua_quality_feature_parity_audit.md
```

PASS esetén a report végén:

```text
SGH-Q01_STATUS: READY
```
