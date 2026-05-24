# Runner prompt — SGH-00 `sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan`

## Feladat

A helyi `VRS_nesting` repo gyökerében dolgozz. Hajtsd végre az SGH-00 taskot:

```text
SGH-00 — sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan
```

Ez audit és migrációs terv task. **Ne implementálj production kódot. Ne köss be külső SparrowGH benchmark backendet. Ne vendorolj külső forrást.** A cél: a Sparrow és SparrowGH/coroush forráskód valós auditja, majd annak kidolgozása, hogyan vesszük át vagy implementáljuk újra a szükséges algoritmikus részeket a saját VRS `jagua_optimizer` rétegbe.

---

## Kötelező dependency preflight

Mielőtt bármilyen külső auditot vagy migrációs tervet készítesz, ellenőrizd:

```text
codex/reports/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md
```

Feltételek:

- report létezik;
- első sora `PASS` vagy `PASS_WITH_NOTES`;
- tartalmazza: `PHASE2_GATE_DECISION: PASS`;
- nincs `STOP`, `NO-GO`, unresolved exact validation vagy boundary blocker.

Ha bármelyik feltétel nem teljesül, állj meg:

```text
STATUS: BLOCKED
REASON: Missing or non-PASS dependency: JG-20 Phase 2 gate
```

Ilyenkor csak a SGH-00 reportot és checklistet frissítsd dependency evidence-szel. Ne írj kész migrációs döntést.

---

## Kötelező olvasmányok

Olvasd el:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_master_plan.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_rs_sajat_optimizer_fejlesztesi_terv.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_canvas_yaml_runner_task_bontas.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
canvases/egyedi_solver/jagua_optimizer_task_index.md
canvases/egyedi_solver/sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan.yaml
codex/codex_checklist/egyedi_solver/sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan.md
```

A `run.md`, a canvas és a YAML az irányadó. Az `AGENTS.md` outputs szabálya kötelező.

---

## Külső forrás audit — nem vendor, nem benchmark backend

Ideiglenes, repo-n kívüli könyvtárba clone-olhatsz vagy olvashatsz külső forrást, például:

```bash
mkdir -p /tmp/vrs_sparrow_audit
cd /tmp/vrs_sparrow_audit
git clone https://github.com/JeroenGar/sparrow.git JeroenGar_sparrow
git clone https://github.com/coroush/sparrow.git coroush_sparrow
git clone https://github.com/coroush/sparrow-grasshopper.git coroush_sparrow_grasshopper || true
```

Ha nincs internet vagy valamelyik repo nem létezik, ezt dokumentáld `NOT_FOUND` vagy `NETWORK_BLOCKED` státusszal. Ne találj ki fájlokat.

Kötelező rögzíteni:

```text
repo URL
commit hash / ref
license file path
license summary
releváns source file pathok
```

---

## Audit fókusz

### SparrowGH / coroush BPP fókusz

Ha elérhető, auditáld:

```text
src/bp_optimizer/mod.rs
src/bp_optimizer/bp_lbf.rs
src/bp_optimizer/bp_separator.rs
src/bp_optimizer/bp_explore.rs
src/bp_optimizer/bp_moves.rs
src/config.rs
src/sample/search.rs
src/eval/lbf_evaluator.rs
src/eval/sep_evaluator.rs
src/quantify/tracker.rs
```

Külön keresd és dokumentáld:

```text
bp_optimize entrypoint
initial FFD/LBF construction
separator fallback
BinSeparator / separation loop
collision tracker / weighted loss
move_items_multi vagy hasonló multi-worker selection
bin_reduction_phase / least-loaded bin removal
transfer / swap / reinsert move operators
solution pool / perturbation / stagnation handling
compaction
terminator / time budget
```

### Eredeti Sparrow fókusz

Ha elérhető, auditáld:

```text
src/optimizer/separator.rs
src/optimizer/explore.rs
src/optimizer/compress.rs
src/optimizer/worker.rs
src/sample/search.rs
src/eval/lbf_evaluator.rs
src/eval/sep_evaluator.rs
src/quantify/tracker.rs
src/config.rs
```

Külön keresd és dokumentáld:

```text
exploration/compression loop
separator/collision repair
temporary infeasible states
incumbent snapshot / rollback
collision loss / weighted loss update
sample placement
multi-worker search
stopping policy
```

---

## VRS oldali audit

Auditáld a jelenlegi valós VRS kódot:

```text
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/geometry.rs
rust/vrs_solver/src/optimizer/mod.rs
rust/vrs_solver/src/optimizer/boundary.rs
rust/vrs_solver/src/optimizer/candidates.rs
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/score.rs
rust/vrs_solver/src/optimizer/multisheet.rs
rust/vrs_solver/src/optimizer/sheet_elimination.rs
rust/vrs_solver/src/optimizer/moves.rs
rust/vrs_solver/src/optimizer/state.rs
rust/vrs_solver/src/optimizer/stopping.rs
vrs_nesting/runner/vrs_solver_runner.py
vrs_nesting/nesting/instances.py
scripts/bench_jagua_optimizer_phase1_rectangular.py
scripts/bench_jagua_optimizer_phase2_irregular.py
scripts/smoke_jagua_irregular_boundary_validation.py
scripts/smoke_jagua_remnant_score_model_v1.py
```

Külön válaszold meg:

1. A VRS jelenlegi `LayoutState` képes-e ideiglenes colliding/infeasible állapotot tárolni?
2. A jelenlegi `repair.rs` valódi separator-e, vagy csak valid placement repair?
3. A jelenlegi `sheet_elimination.rs` mennyiben felel meg a SparrowGH bin reduction mintának?
4. A jelenlegi `moves.rs` elég-e transfer/swap/reinsert műveletekhez?
5. A `score.rs` döntési mechanizmus vagy főleg utólagos metrika?
6. Hol kapcsolódik az exact validator a pipeline-ba?
7. Milyen módosítás kell úgy, hogy a final accepted output továbbra is exact validator PASS legyen?

---

## Kimeneti dokumentumok

Hozd létre:

```text
docs/egyedi_solver/sparrow_sparrowgh_code_audit.md
docs/egyedi_solver/sparrowgh_vrs_migration_plan.md
```

### `sparrow_sparrowgh_code_audit.md` kötelező struktúra

```text
# Sparrow / SparrowGH code audit

## Source repositories and pinned refs
## License and attribution
## Original Sparrow architecture summary
## SparrowGH/coroush BPP architecture summary
## File-by-file audit
## Algorithmic components
## What is directly reusable
## What must be reimplemented VRS-style
## What must not be copied/adopted
## Gaps and uncertainties
## Evidence appendix
```

### `sparrowgh_vrs_migration_plan.md` kötelező struktúra

```text
# SparrowGH → VRS jagua_optimizer migration plan

## Decision
## Target architecture
## VRS module mapping
## State model changes
## Separator migration plan
## Initial construction migration plan
## Sheet elimination migration plan
## Move operators migration plan
## Solution pool / perturbation plan
## Scoring and exact validation integration
## Irregular/remnant handling
## Rotation policy handling
## Test and benchmark strategy
## Rollback strategy
## Proposed SGH task chain
## Acceptance gates
```

---

## Kötelező migrációs döntés

A tervben egyértelműen mondd ki:

```text
Do not use SparrowGH as external benchmark backend.
Use Sparrow/SparrowGH as audited algorithmic source.
Port or reimplement selected algorithms inside VRS jagua_optimizer.
```

A migrációs terv minimum javasolt tasklánca:

```text
SGH-01 — working layout / infeasible search state audit + scaffold
SGH-02 — per-sheet separator V1
SGH-03 — LBF + separator fallback construction
SGH-04 — sheet elimination / bin reduction V1
SGH-05 — transfer/swap/reinsert move operators
SGH-06 — solution pool / perturbation / stagnation handling
SGH-07 — VRS quality benchmark suite + exact validator gate
SGH-08 — irregular/remnant hardening on migrated search loop
```

Ha az audit alapján módosítod, indokold.

---

## Hard rules

```text
REAL_CODE_ONLY:
- Work only from actual repository files and actually retrieved external source files.
- Do not invent source paths, APIs, functions, schemas, commands or benchmark results.
```

```text
NO_EXTERNAL_BENCHMARK_BACKEND:
- Do not build a SparrowGH CLI adapter.
- Do not run SparrowGH as a VRS benchmark backend.
- Do not compare benchmark quality against SparrowGH in this task.
```

```text
NO_PRODUCTION_CODE_CHANGE:
- This is audit + migration plan only.
- Do not modify Rust optimizer production code, Python runner code, solver IO contract, DXF pipeline or quality profiles.
```

```text
LICENSE_REQUIRED:
- License and attribution evidence is mandatory.
- If license is missing or ambiguous, direct-copy is BLOCKED.
```

```text
EXACT_VALIDATION_REQUIRED:
- Every future implementation task must end with VRS exact validator gate.
- Temporary infeasible search state may be proposed only as internal working state, never as accepted output.
```

---

## Report és checklist

Frissítsd:

```text
codex/codex_checklist/egyedi_solver/sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan.md
codex/reports/egyedi_solver/sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan.md
```

A report tartalmazzon:

```text
Dependency evidence
Source/ref/license table
VRS current-state audit summary
Sparrow/SparrowGH component audit summary
DoD → Evidence Matrix
Migration decision
Proposed SGH task chain
Risks and blockers
Verification results
```

Siker esetén a report végére:

```text
SGH-01_STATUS: READY
```

---

## Kötelező verify

Futtasd:

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan.md
```

Ha ez audit-only task ellenére környezeti okból fail, dokumentáld pontosan. A verify FAIL-t nem szabad elhallgatni.
