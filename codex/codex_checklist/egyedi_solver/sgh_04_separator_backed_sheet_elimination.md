# Checklist — SGH-04 `sgh_04_separator_backed_sheet_elimination`

## Dependency gate

- [x] SGH-03 report létezik: `codex/reports/egyedi_solver/sgh_03_lbf_separator_construction_integration.md`.
- [x] SGH-03 report első sora `PASS` vagy `PASS_WITH_NOTES`.
- [x] SGH-03 report tartalmazza: `SGH-04_STATUS: READY`.
- [x] Dependency evidence dokumentálva a SGH-04 reportban.

## Repo rules and local code audit

- [x] `AGENTS.md` elolvasva.
- [x] `docs/codex/overview.md` elolvasva.
- [x] `docs/codex/yaml_schema.md` elolvasva.
- [x] `docs/codex/report_standard.md` elolvasva.
- [x] `docs/qa/testing_guidelines.md` elolvasva.
- [x] `docs/egyedi_solver/sparrow_sparrowgh_code_audit.md` elolvasva.
- [x] `docs/egyedi_solver/sparrowgh_vrs_migration_plan.md` elolvasva.
- [x] `docs/egyedi_solver/sgh_01_working_layout_state_contract.md` elolvasva.
- [x] `docs/egyedi_solver/sgh_02_vrs_separator_contract.md` elolvasva.
- [x] `docs/egyedi_solver/sgh_03_lbf_separator_construction_contract.md` elolvasva.
- [x] `rust/vrs_solver/src/optimizer/sheet_elimination.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/separator.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/working.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/initializer.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/candidates.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/repair.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/boundary.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/multisheet.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/stopping.rs` auditálva.
- [x] `rust/vrs_solver/src/io.rs`, `item.rs`, `sheet.rs` auditálva.

## Implementation

- [x] `SheetEliminationDiagnostics` bővült SGH-04 LBF/separator/reject mezőkkel.
- [x] `SheetEliminationDiagnostics::summary()` tartalmazza az új mezőket.
- [x] Target selection sheet-count reducing módon highest-used sheetet választ.
- [x] A report dokumentálja a VRS `max(sheet_index)+1` constraintet.
- [x] Displaced queue largest-first: area desc → max_dim desc → instance_id asc.
- [x] LBF clear redistribution csak `sheet_index < target_sheet` sheeteket használ.
- [x] LBF scoring determinisztikus és used receiving sheetet preferál.
- [x] Separator fallback be van kötve LBF failure után.
- [x] Separator fallback `WorkingLayout`-ot és `VrsSeparator::run()`-t használ.
- [x] Optional separator allowed-sheet filter bevezetve, vagy target/higher sheet reuse szigorúan rejectálva és dokumentálva.
- [x] Fallback csak commit gate success után fogad el eredményt.
- [x] Commit gate ellenőrzi: no violations, no target/higher sheet, sheet_count_used reduced.
- [x] Sikertelen attempt teljes rollbacket ad az eredeti snapshotra.
- [x] Public `SheetEliminationEngine::run()` signature kompatibilis maradt, vagy eltérés reportban indokolva.

## Tests

- [x] Meglévő sheet_elimination tesztek zöldek.
- [x] Target selection highest used sheetet választ.
- [x] Redistribution nem használ target sheetet.
- [x] Redistribution nem használ target feletti unused sheetet.
- [x] Egyszerű 2 sheet → 1 sheet elimináció PASS.
- [x] Impossible elimination rollback-safe és byte-identical placement snapshot.
- [x] Separator-backed fallback célzott tesztben aktiválható és valid layoutot ad.
- [x] Separator fallback rejectálódik target/higher sheet reuse esetén.
- [x] Diagnostics summary tartalmazza az új SGH-04 mezőket.
- [x] Final committed output `find_violations()` szerint valid.
- [x] Separator allowed-sheet filter default None mellett nem töri a korábbi separator teszteket.

## Documentation

- [x] Elkészült `docs/egyedi_solver/sgh_04_separator_backed_sheet_elimination_contract.md`.
- [x] A doksi leírja a current SheetElimination V1 gapet.
- [x] A doksi leírja a SparrowGH bin-reduction mappinget.
- [x] A doksi leírja a VRS sheet_count_used constraintet.
- [x] A doksi leírja a target sheet selection V2 szabályt.
- [x] A doksi leírja a receiving sheet restrictiont.
- [x] A doksi leírja az LBF reinsertion V2 szabályt.
- [x] A doksi leírja a separator-backed fallback V1 szabályt.
- [x] A doksi leírja a commit/rollback gate-eket.
- [x] A doksi leírja, hogyan készíti elő SGH-05-öt.

## Scope safety

- [x] Nem történt Sparrow/SparrowGH vendorolás.
- [x] Nem készült külső backend adapter.
- [x] Nem lett módosítva `rust/vrs_solver/src/io.rs`.
- [x] Nem lett módosítva `rust/vrs_solver/src/adapter.rs`.
- [x] Nem lett átírva `rust/vrs_solver/src/optimizer/score.rs` objective modellje.
- [x] Nem lett implementálva `moves.rs` transfer/swap execution.
- [x] Nem változott a Python runner / exact validator.
- [x] Nem lett continuous rotation bevezetve.
- [x] Nem lett solution pool / perturbáció / multi-restart bevezetve.
- [x] Nem lett cavity-prepack bevezetve.

## Verification and report

- [x] Focused Rust teszt lefutott: `cargo test -p vrs_solver sheet_elimination separator` vagy ekvivalens.
- [x] Teljes `cargo test -p vrs_solver` lefutott, ha indokolt.
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_04_separator_backed_sheet_elimination.md` lefutott.
- [x] Verify log létrejött: `codex/reports/egyedi_solver/sgh_04_separator_backed_sheet_elimination.verify.log`.
- [x] Report tartalmaz DoD → Evidence Matrixot.
- [x] Report első sora `PASS`, `PASS_WITH_NOTES`, `FAIL` vagy `BLOCKED`.
- [x] Ha zöld, report végén szerepel: `SGH-05_STATUS: READY`.
