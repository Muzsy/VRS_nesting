# Codex checklist — JG-14 `jagua_optimizer_t14_phase1_benchmark_matrix`

## Dependency preflight

- [x] `codex/reports/egyedi_solver/jagua_optimizer_t13_sheet_elimination_v1.md` létezik.
- [x] JG-13 report első sora `PASS`.
- [x] JG-13 report tartalmazza: `JG-14_STATUS: READY`.
- [x] `rust/vrs_solver/src/optimizer/sheet_elimination.rs` létezik.
- [x] `scripts/smoke_jagua_sheet_elimination_v1.py` létezik.

## Required reads

- [x] `AGENTS.md` elolvasva.
- [x] `docs/codex/overview.md` elolvasva.
- [x] `docs/codex/yaml_schema.md` elolvasva.
- [x] `docs/codex/report_standard.md` elolvasva.
- [x] `docs/qa/testing_guidelines.md` elolvasva.
- [x] JG tervdokumentációk elolvasva.
- [x] JG-14 canvas/YAML/runner elolvasva.

## Real code audit

- [x] `adapter.rs` Phase 1 profile dispatch auditálva.
- [x] `io.rs` SolverInput/SolverOutput/Metrics contract auditálva.
- [x] `vrs_solver_runner.py` runner_meta mezői auditálva.
- [x] `instances.py` exact validation bridge auditálva.
- [x] `multisheet.rs` sheet_count_used contract auditálva.
- [x] `sheet_elimination.rs` JG-13 pass auditálva.
- [x] Meglévő smoke/benchmark minták auditálva.

## Benchmark implementation

- [x] `scripts/bench_jagua_optimizer_phase1_rectangular.py` létrejött.
- [x] Smoke benchmark fixture implementálva.
- [x] Small benchmark fixture implementálva.
- [x] Medium benchmark fixture implementálva.
- [x] Realistic no-hole fixture implementálva vagy explicit blockerrel dokumentált.
- [x] Baseline compare bekötve, ahol van értelmes baseline.
- [x] Baseline unavailable eset dokumentált, ha nincs értelmes baseline.
- [x] Invalid layout nem lehet successful benchmark.
- [x] Minden accepted layout exact validator PASS státuszt igényel.
- [x] Summary JSON létrejön.
- [x] Summary MD benchmark report létrejön.

## Metrics / reporting

- [x] `placed_count` rögzítve.
- [x] `unplaced_count` rögzítve.
- [x] `sheet_count_used` rögzítve.
- [x] `utilization` rögzítve.
- [x] `duration_sec` / runtime rögzítve.
- [x] Seed/profile/rotations/backend meta rögzítve.
- [x] Case-level failure details rögzítve.
- [x] `PHASE1_GATE_DECISION` dokumentálva.
- [x] `JG-15_STATUS: READY` csak PASS gate esetén szerepel.

## Smoke / tests

- [x] `python3 scripts/bench_jagua_optimizer_phase1_rectangular.py` PASS.
- [x] `python3 scripts/smoke_jagua_sheet_elimination_v1.py` PASS.
- [x] `python3 scripts/smoke_jagua_exact_validation_bridge.py` PASS.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t14_phase1_benchmark_matrix.md` PASS.

## Global checklist / report

- [x] `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md` JG-14 szakasza frissítve.
- [x] Gate 1 checklist releváns pontjai frissítve.
- [x] `codex/reports/egyedi_solver/jagua_optimizer_t14_phase1_benchmark_matrix.md` elkészült/frissült.
- [x] `codex/reports/egyedi_solver/jagua_optimizer_t14_phase1_benchmark_matrix.verify.log` létrejött.
- [x] Ha volt eltérés vagy blocker, explicit dokumentálva van.
