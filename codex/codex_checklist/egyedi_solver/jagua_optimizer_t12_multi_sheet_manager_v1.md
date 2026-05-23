# Codex checklist — JG-12 `jagua_optimizer_t12_multi_sheet_manager_v1`

## Dependency preflight

- [x] `codex/reports/egyedi_solver/jagua_optimizer_t11_score_model_v1.md` létezik.
- [x] JG-11 report első sora `PASS`.
- [x] JG-11 report tartalmazza: `JG-12_STATUS: READY`.
- [x] `rust/vrs_solver/src/optimizer/score.rs` létezik és ScoreModel V1-et tartalmaz.
- [x] `scripts/smoke_jagua_score_model_v1.py` létezik.

## Required reads

- [x] `AGENTS.md` elolvasva.
- [x] `docs/codex/overview.md` elolvasva.
- [x] `docs/codex/yaml_schema.md` elolvasva.
- [x] `docs/codex/report_standard.md` elolvasva.
- [x] `docs/qa/testing_guidelines.md` elolvasva.
- [x] JG tervdokumentációk elolvasva.
- [x] JG-12 canvas/YAML/runner elolvasva.

## Real code audit

- [x] `adapter.rs` Phase 1 flow auditálva.
- [x] `initializer.rs` multi-sheet construction auditálva.
- [x] `repair.rs` multi-sheet repair auditálva.
- [x] `score.rs` sheet-count scoring auditálva.
- [x] `candidates.rs` sheet-aware candidate generation auditálva.
- [x] `io.rs` `Placement.sheet_index` és `Metrics.sheet_count_used` contract auditálva.
- [x] `sheet.rs` `expand_sheets()` stable ordering auditálva.
- [x] Régi JG-12 cavity extraction tervnév eltérés dokumentálva.

## Implementation

- [x] `rust/vrs_solver/src/optimizer/multisheet.rs` létrejött.
- [x] `MultiSheetManager` vagy repo-konform ekvivalens implementálva.
- [x] `MultiSheetDiagnostics` vagy repo-konform ekvivalens implementálva.
- [x] `used_sheets` / `sheet_count_used` helper implementálva.
- [x] Sheetenkénti summary/diagnostics elérhető.
- [x] `optimizer/mod.rs` exportálja a `multisheet` modult.
- [x] Phase 1 adapter flow MultiSheetManageren keresztül fut.
- [x] `SolverOutput` v1 meglévő mezői nem törtek.
- [x] `main.rs` változatlan maradt (nem kellett CLI módosítás).

## Correctness gates

- [x] Több rectangular sheet kezelése implementálva.
- [x] Sheet assignment determinisztikus.
- [x] Used sheets számítása pontos.
- [x] `sheet_index` contract nem törik.
- [x] Unplaced kezelés több sheet mellett is helyes.
- [x] Multi-sheet fixture valid.
- [x] Azonos seed azonos sheet assignmentet ad.
- [x] Sheetenkénti metrics/diagnostics reportolva.
- [x] Construction/repair sheetenkénti működése ellenőrizve.
- [x] Nincs regresszió single-sheet fixture-ön.
- [x] Report tartalmaz multi-sheet példát.
- [x] Exact validation gate nem gyengült.

## Smoke / tests

- [x] `cargo build --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml` PASS (64/64).
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::multisheet` PASS (10/10).
- [x] `python3 scripts/smoke_jagua_initial_construction.py` PASS.
- [x] `python3 scripts/smoke_jagua_repair_search_v1.py` PASS.
- [x] `python3 scripts/smoke_jagua_score_model_v1.py` PASS.
- [x] `python3 scripts/smoke_jagua_multisheet_manager_v1.py` PASS (21/21).
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t12_multi_sheet_manager_v1.md` PASS.
- [x] Verify log mentve: `codex/reports/egyedi_solver/jagua_optimizer_t12_multi_sheet_manager_v1.verify.log`.

## Report / progress

- [x] `codex/reports/egyedi_solver/jagua_optimizer_t12_multi_sheet_manager_v1.md` frissítve.
- [x] Globális progress checklist JG-12 szakasza frissítve.
- [x] Reportban szerepel a végső státusz: PASS.
- [x] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [x] Következő task indíthatósága egyértelműen jelölve van.
- [x] `JG-13_STATUS: READY` csak teljes PASS esetén szerepel.
