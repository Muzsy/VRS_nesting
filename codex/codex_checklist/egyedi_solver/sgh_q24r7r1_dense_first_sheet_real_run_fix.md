# SGH-Q24R7-R1 checklist — Dense first-sheet real-run fix

## A. Mandatory reading

- [x] Read Q24R7 report: `codex/reports/egyedi_solver/sgh_q24r7_native_sparrow_sampler_evaluator_first_sheet_lv8.md`.
- [x] Read Q24R7 verify log.
- [x] Read Q24R7 smoke script.
- [x] Read `rust/vrs_solver/src/optimizer/sparrow/mod.rs` and identify the large single-sheet guarded partial path.
- [x] Read `rust/vrs_solver/src/adapter.rs` native diagnostics projection.
- [x] Read `rust/vrs_solver/src/io.rs` diagnostics/output schema.
- [x] Read `tests/fixtures/nesting_engine/ne2_input_lv8jav.json`.
- [x] Re-check the fixed 191 sheet-1 quantity vector from Q24R7.

## B. Architecture preservation

- [x] Production `sparrow_cde` still constructs `SparrowProblem`.
- [x] Production `sparrow_cde` still calls `SparrowOptimizer::solve`.
- [x] Production `sparrow_cde` still projects `SparrowSolution` only at output boundary.
- [x] No `WorkingLayout`, `VrsCollisionTracker`, `SparrowSeparationKernel`, `PhaseOptimizer`, or `MultiSheetManager` in production `optimizer/sparrow`.
- [x] `crate::io::Placement` is not used as the internal native layout truth model.

## C. Guard removal / quarantine

- [x] Remove the production early return for `instances.len() >= 100 && sheets.len() == 1`.
- [x] Remove marker diagnostics created solely to indicate a skipped dense run.
- [x] If a timeout/perf safety guard remains, it is budget based inside the real solve path, not an instance-count return.
- [x] Any intentionally skipped dense mode is absent from production `sparrow_cde`.

## D. Real dense probe execution

- [x] Generate LV8 first-sheet input from `ne2_input_lv8jav.json` using the exact 191 vector.
- [x] Use one stock sheet.
- [x] Run native `sparrow_cde` with CDE backend.
- [x] Prove search actually ran: `sparrow_iterations=3`, `exploration_iterations=1`.
- [x] Prove `sparrow_search_position_calls > 0`: observed `6`.
- [x] Prove `sparrow_search_position_samples > 0`: observed `74`.
- [x] Prove `sparrow_worker_candidates_evaluated > 0`: observed `6`.
- [x] Prove CDE query counters > 0: smoke aggregate `718`.
- [x] Final validation uses real final pair/boundary numbers: pairs `178`, boundary `0`.
- [x] Runtime is real and bounded: observed `9.908s` for dense probe.

## E. Honest partial semantics

- [ ] First-sheet 191/191 is valid.
- [x] If not valid: report `PARTIAL`, not fake `PASS`.
- [x] Do not use `placed=191/191` as a solved metric when status is partial.
- [x] Add or surface diagnostics for unresolved/colliding/top-blocker instance ids.
- [x] Report exact final pairs, boundary violations, raw/weighted loss, runtime, search calls, worker candidates, CDE queries.

## F. Regression gates

- [x] Medium native CDE gate still passes.
- [x] LV8 12 types x1 regression still passes.
- [x] No bbox fallback.
- [x] No LBF fallback.
- [x] No legacy fallback.
- [x] Compression disabled/zero.

## G. Required commands

- [x] `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`
- [x] `python3 scripts/smoke_sgh_q24r7r1_dense_first_sheet_real_run_fix.py`
- [x] `./scripts/check.sh`
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q24r7r1_dense_first_sheet_real_run_fix.md`

## H. Required report

- [x] Write `codex/reports/egyedi_solver/sgh_q24r7r1_dense_first_sheet_real_run_fix.md`.
- [x] Include status lines.
- [x] Include exact dense probe metrics and blocker list.
