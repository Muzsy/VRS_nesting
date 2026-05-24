# Codex checklist — JG-13 `jagua_optimizer_t13_sheet_elimination_v1`

## Dependency preflight

- [x] `codex/reports/egyedi_solver/jagua_optimizer_t12_multi_sheet_manager_v1.md` létezik.
- [x] JG-12 report első sora `PASS`.
- [x] JG-12 report tartalmazza: `JG-13_STATUS: READY`.
- [x] `rust/vrs_solver/src/optimizer/multisheet.rs` létezik.
- [x] `scripts/smoke_jagua_multisheet_manager_v1.py` létezik.

## Required reads

- [x] `AGENTS.md` elolvasva.
- [x] `docs/codex/overview.md` elolvasva.
- [x] `docs/codex/yaml_schema.md` elolvasva.
- [x] `docs/codex/report_standard.md` elolvasva.
- [x] `docs/qa/testing_guidelines.md` elolvasva.
- [x] JG tervdokumentációk elolvasva.
- [x] JG-13 canvas/YAML/runner elolvasva.

## Real code audit

- [x] `multisheet.rs` MultiSheetManager flow auditálva.
- [x] `repair.rs` reinsert és violation logic auditálva.
- [x] `candidates.rs` candidate ordering auditálva.
- [x] `score.rs` sheet-count és objective breakdown auditálva.
- [x] `state.rs` snapshot/rollback modelhez auditálva.
- [x] `adapter.rs` Phase 1 wiring auditálva.
- [x] `io.rs` `Metrics.sheet_count_used` contract auditálva.
- [x] Régi JG-13 cavity-prepack tervnév eltérés dokumentálva.

## Implementation

- [x] `rust/vrs_solver/src/optimizer/sheet_elimination.rs` létrejött.
- [x] `SheetEliminationEngine` vagy repo-konform ekvivalens implementálva.
- [x] `SheetEliminationDiagnostics` vagy repo-konform ekvivalens implementálva.
- [x] Weakest sheet kiválasztási szabály implementálva.
- [x] Determinisztikus reinsert order implementálva.
- [x] Rollback snapshot implementálva.
- [x] Attempt/success/fail metrics implementálva.
- [x] `optimizer/mod.rs` exportálja a `sheet_elimination` modult.
- [x] Phase 1 flow JG-12 után sheet elimination pass-szal fut, vagy a report explicit indokolja az alternatív wiringot.
- [x] `SolverOutput` v1 meglévő mezői nem törtek.

## Correctness gates

- [x] Sikeres elimináció esetén `sheet_count_used` csökken.
- [x] Sikertelen elimináció rollbackel.
- [x] Rollback után a valid layout nem romlik.
- [x] Mesterséges fixture-ben legalább egy sheet eliminálható.
- [x] Invalid layout nem lehet eliminációs siker.
- [x] Time limit/stopping policy figyelembe véve.
- [x] Regression futott JG-12 fixture-ökre.
- [x] Exact validation gate nem gyengült.
- [x] Reportban attempt/success/fail metrikák szerepelnek.

## Smoke / tests

- [x] `cargo build --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::sheet_elimination` PASS.
- [x] `python3 scripts/smoke_jagua_multisheet_manager_v1.py` PASS.
- [x] `python3 scripts/smoke_jagua_sheet_elimination_v1.py` PASS.
- [x] `python3 scripts/smoke_jagua_exact_validation_bridge.py` PASS vagy környezeti okkal dokumentált.
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t13_sheet_elimination_v1.md` PASS.
- [x] Verify log mentve: `codex/reports/egyedi_solver/jagua_optimizer_t13_sheet_elimination_v1.verify.log`.

## Report / progress

- [x] `codex/reports/egyedi_solver/jagua_optimizer_t13_sheet_elimination_v1.md` frissítve.
- [x] Globális progress checklist JG-13 szakasza frissítve.
- [x] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [x] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [x] Következő task indíthatósága egyértelműen jelölve van.
- [x] `JG-14_STATUS: READY` csak teljes PASS esetén szerepel.
