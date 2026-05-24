# Checklist — JG-15 `jagua_optimizer_t15_irregular_sheet_capability_spike`

## Dependency preflight

- [x] `codex/reports/egyedi_solver/jagua_optimizer_t14_phase1_benchmark_matrix.md` létezik.
- [x] JG-14 report első sora `PASS`.
- [x] JG-14 report tartalmazza: `PHASE1_GATE_DECISION: PASS`.
- [x] JG-14 report tartalmazza: `JG-15_STATUS: READY`.
- [x] Phase 1 benchmark artifactok léteznek.

## Required reads

- [x] `AGENTS.md` elolvasva.
- [x] `docs/codex/overview.md` elolvasva.
- [x] `docs/codex/yaml_schema.md` elolvasva.
- [x] `docs/codex/report_standard.md` elolvasva.
- [x] `docs/qa/testing_guidelines.md` elolvasva.
- [x] JG tervdokumentációk elolvasva.
- [x] JG-15 canvas/YAML/runner elolvasva.

## Real code audit

- [x] `sheet.rs` Stock/SheetShape/rect_inside_sheet_shape auditálva.
- [x] `geometry.rs` jagua conversion helper auditálva.
- [x] `adapter.rs` JaguaAdapter boundary/collision methods auditálva.
- [x] `initializer.rs`, `repair.rs`, `multisheet.rs` irregular boundary érintettség auditálva.
- [x] `instances.py` exact validation outer_points support auditálva.
- [x] `vrs_solver_runner.py` validation_status/runner_meta path auditálva.
- [x] `Cargo.toml` jagua-rs dependency auditálva.
- [x] Tervverzió-eltérés dokumentálva.

## Spike artifacts

- [x] `tests/fixtures/egyedi_solver/jagua_irregular_l_shape.json` létrejött.
- [x] Fixture hole-free.
- [x] Fixture tartalmaz konkáv L-shape/remnant `stock.outer_points` mezőt.
- [x] Pozitív kontrollhelyzet dokumentálva.
- [x] Negatív notch/boundary violation kontrollhelyzet dokumentálva.
- [x] `rust/vrs_solver/src/bin/jagua_irregular_sheet_spike.rs` létrejött.
- [x] Rust spike bin grep-elhető döntési sorokat ír.
- [x] `scripts/smoke_jagua_irregular_sheet_spike.py` létrejött.
- [x] Smoke script fixture, bin, exact validation és decision report ellenőrzéseket futtat.
- [x] `docs/egyedi_solver/jagua_irregular_sheet_spike_decision.md` létrejött.

## Decision evidence

- [x] Megvizsgálva, hogy jagua natívan tud-e irregular boundaryt.
- [x] Boundary violation felismerése tesztelve.
- [x] Item-item collision regresszió ellenőrizve.
- [x] Nincs item hole vagy container hole bekeverve.
- [x] Döntési ág rögzítve: natív jagua boundary vagy saját boundary validator + jagua item-item collision.
- [x] Performance/kockázat röviden dokumentálva.
- [x] NO-GO esetén alternatív terv szerepel.
- [x] Report konkrét PASS/NO-GO döntéssel zár.

## Smoke / tests

- [x] `cargo build --manifest-path rust/vrs_solver/Cargo.toml --bin jagua_irregular_sheet_spike` PASS.
- [x] `cargo run --manifest-path rust/vrs_solver/Cargo.toml --bin jagua_irregular_sheet_spike` PASS.
- [x] `python3 scripts/smoke_jagua_irregular_sheet_spike.py` PASS.
- [x] `python3 scripts/bench_jagua_optimizer_phase1_rectangular.py` PASS/regression documented.
- [x] `python3 scripts/smoke_jagua_exact_validation_bridge.py` PASS.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.md` PASS.

## Global checklist / report

- [x] `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md` JG-15 szakasza frissítve.
- [x] `codex/reports/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.md` elkészült/frissült.
- [x] `codex/reports/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.verify.log` létrejött.
- [x] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [x] Ha volt eltérés vagy blocker, explicit dokumentálva van.
- [x] Következő task indíthatósága egyértelműen jelölve van.
