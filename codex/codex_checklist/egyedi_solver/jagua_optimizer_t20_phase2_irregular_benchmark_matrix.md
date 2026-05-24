# Checklist — JG-20 `jagua_optimizer_t20_phase2_irregular_benchmark_matrix`

## Dependency and preflight

- [x] JG-19 report létezik.
- [x] JG-19 report első sora `PASS` vagy `PASS_WITH_NOTES`.
- [x] JG-19 report tartalmazza: `JG-20_STATUS: READY`.
- [x] JG-19 remnant score smoke létezik és a report szerint PASS.
- [x] Repo szabályfájlok elolvasva (`AGENTS.md`, `docs/codex/*`, `docs/qa/testing_guidelines.md`).
- [x] JG tervdokumentumok elolvasva.

## Current code audit

- [x] `scripts/bench_jagua_optimizer_phase1_rectangular.py` benchmark mintaként auditálva.
- [x] `scripts/smoke_jagua_irregular_sheet_provider.py` regressziós smoke auditálva.
- [x] `scripts/smoke_jagua_irregular_boundary_validation.py` regressziós smoke auditálva.
- [x] `scripts/smoke_jagua_irregular_candidate_generation.py` regressziós smoke auditálva.
- [x] `scripts/smoke_jagua_remnant_score_model_v1.py` regressziós smoke auditálva.
- [x] `vrs_nesting/runner/vrs_solver_runner.py` runner/exact validation boundary auditálva.
- [x] `rust/vrs_solver/src/sheet.rs` irregular/remnant metadata auditálva.
- [x] `rust/vrs_solver/src/optimizer/boundary.rs` boundary policy auditálva.
- [x] `rust/vrs_solver/src/optimizer/candidates.rs` candidate stats auditálva.
- [x] `rust/vrs_solver/src/optimizer/score.rs` score_breakdown/remnant cost auditálva.

## Benchmark matrix implementation

- [x] `scripts/bench_jagua_optimizer_phase2_irregular.py` létrejött.
- [x] L-shape benchmark fut.
- [x] Konkáv remnant benchmark fut.
- [x] Vegyes rectangular + remnant benchmark fut.
- [x] Rectangular Phase 1 regressziós benchmark fut.
- [x] Minden benchmark fixture hole-free / outer-only.
- [x] Hole-os fixture nem kerül csendben átalakításra.
- [x] Invalid boundary layout automatikus FAIL.
- [x] Minden elfogadott irregular layout exact validator PASS.

## Metrics and reports

- [x] Metrikák rögzítve: placed, unplaced, used_sheets, utilization, runtime, boundary rejects vagy unavailable reason.
- [x] Seed/profile/backend meta rögzítve.
- [x] Stock/remnant/cost_per_use summary rögzítve.
- [x] Score breakdown rögzítve, ha elérhető.
- [x] Summary JSON létrejött: `codex/reports/egyedi_solver/jagua_optimizer_phase2_irregular_benchmark.json`.
- [x] Summary MD report létrejött: `codex/reports/egyedi_solver/jagua_optimizer_phase2_irregular_benchmark.md`.
- [x] Phase 2 gate döntés dokumentálva: `PHASE2_GATE_DECISION: PASS`.

## Regression and verification

- [x] `python3 scripts/bench_jagua_optimizer_phase2_irregular.py` PASS.
- [x] `python3 scripts/bench_jagua_optimizer_phase1_rectangular.py` PASS vagy explicit regression evidence készült.
- [x] `python3 scripts/smoke_jagua_irregular_sheet_provider.py` PASS.
- [x] `python3 scripts/smoke_jagua_irregular_boundary_validation.py` PASS.
- [x] `python3 scripts/smoke_jagua_irregular_candidate_generation.py` PASS.
- [x] `python3 scripts/smoke_jagua_remnant_score_model_v1.py` PASS.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [x] Repo verify PASS és log mentve.

## Documentation and progress checklist

- [x] JG-20 report tartalmaz dependency evidence-t.
- [x] JG-20 report tartalmaz code audit summary-t.
- [x] JG-20 report tartalmaz benchmark matrix és metrika táblát.
- [x] JG-20 report tartalmaz exact validation evidence-t.
- [x] JG-20 report tartalmaz invalid boundary fail evidence-t.
- [x] JG-20 report tartalmaz rectangular regression evidence-t.
- [x] Globális progress checklist JG-20 szakasza frissítve.
- [x] Gate 2 checklist frissítve.
- [x] Csak valódi PASS esetén szerepel: `JG-21_STATUS: READY`.

## Closing fields

- [x] Report első sora `PASS`, `PASS_WITH_NOTES`, `FAIL` vagy `BLOCKED`.
- [x] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [x] Következő task (JG-21) indíthatósága jelölve vagy explicit nem-ready.
