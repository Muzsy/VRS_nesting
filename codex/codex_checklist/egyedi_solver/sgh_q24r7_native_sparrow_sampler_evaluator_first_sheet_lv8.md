# SGH-Q24R7 checklist — Native Sparrow sampler/evaluator + LV8 first-sheet reference

## A. Mandatory reading

- [x] Read Q24R6 report: `codex/reports/egyedi_solver/sgh_q24r6_native_sparrow_tracker_search_parity_hardening.md`.
- [x] Read Q24R6 verify log.
- [x] Read Q24R6 smoke script: `scripts/smoke_sgh_q24r6_native_sparrow_tracker_search_parity_hardening.py`.
- [x] Read current native Sparrow core: `rust/vrs_solver/src/optimizer/sparrow/mod.rs` or split modules under `rust/vrs_solver/src/optimizer/sparrow/`.
- [x] Read adapter diagnostics: `rust/vrs_solver/src/adapter.rs`, `rust/vrs_solver/src/io.rs`.
- [x] Read CDE helpers: `rust/vrs_solver/src/optimizer/cde_adapter.rs`, `rust/vrs_solver/src/optimizer/collision_severity.rs`, `rust/vrs_solver/src/optimizer/loss_model.rs`.
- [x] Read LV8 fixture: `tests/fixtures/nesting_engine/ne2_input_lv8jav.json`.
- [x] Read/extract first-sheet composition from `samples/real_work_dxf/0014-01H/lv8jav/Nested/project_2447207_report.pdf`.
- [x] Read local Sparrow reference:
  - [x] `.cache/sparrow/src/sample/search.rs`
  - [x] `.cache/sparrow/src/eval/sep_evaluator.rs`
  - [x] `.cache/sparrow/src/optimizer/worker.rs`
  - [x] `.cache/sparrow/src/optimizer/separator.rs`
  - [x] `.cache/sparrow/src/optimizer/explore.rs`
  - [x] `.cache/sparrow/src/quantify/tracker.rs`
- [x] Skim `.cache/sparrow/src/optimizer/compress.rs` only to keep compression out of scope.

## B. Preserve native architecture

- [x] Production `sparrow_cde` still constructs `SparrowProblem`.
- [x] Production `sparrow_cde` still calls `SparrowOptimizer::solve`.
- [x] Production `sparrow_cde` still projects `SparrowSolution` only at output boundary.
- [x] No `WorkingLayout`, `VrsCollisionTracker`, old `SparrowSeparationKernel`, `PhaseOptimizer`, `MultiSheetManager`, or LBF fallback in production `optimizer/sparrow`.
- [x] `crate::io::Placement` is not used as native internal layout state.

## C. Sampler/evaluator parity

- [x] Introduce or harden a native sample/evaluator concept analogous to Sparrow `sample/search.rs` + `eval/sep_evaluator.rs`.
- [x] Candidate evaluation must be polygon/CDE-aware for infeasible magnitudes. AABB may be used only as broad-phase pruning, not as main infeasible ordering/evaluator.
- [x] Search must evaluate all eligible containers/sheets in the candidate pool, not only as a last-ditch fallback after current sheet success/failure.
- [x] Global/container-wide sampling must cover every eligible sheet.
- [x] Focused sampling must be driven by native collision neighborhoods/high-loss items, not only random jitter around current placement.
- [x] Coordinate descent/refinement must run on top candidates and use the same evaluator semantics.
- [x] Search must consider all allowed rotations per instance and must preserve Q24R6 rotation-aware seed behavior.
- [x] Diagnostics must separately report global/focused/refined/coord-descent samples, cross-sheet/container candidates, evaluator calls, and best-eval.

## D. Worker/search budget

- [x] Worker count and search budgets are configurable/deterministic, with production defaults strong enough for the dense LV8 probe.
- [x] Workers use native snapshots from the same master state and different target/candidate ordering.
- [x] Best-worker load-back is deterministic by weighted loss, raw loss, then worker id.
- [x] Rejected moves rollback cleanly.
- [x] GLS updates remain based on native quantified tracker losses.

## E. LV8 first-sheet reference input

- [x] Implement or update smoke helper that builds `q24r7_lv8_reference_sheet1` from `tests/fixtures/nesting_engine/ne2_input_lv8jav.json`.
- [x] Quantity vector must be exactly:
  - [x] `LV8_01170_10db = 10`
  - [x] `LV8_02048_20db = 7`
  - [x] `LV8_02049_50db = 50`
  - [x] `Lv8_07919_16db = 13`
  - [x] `Lv8_07920_50db = 12`
  - [x] `Lv8_07921_50db = 33`
  - [x] `Lv8_15435_10db = 10`
  - [x] `Lv8_11612_6db = 3`
  - [x] `Lv8_15348_6db = 4`
  - [x] `Lv8_10059_10db = 10`
  - [x] `LV8_00035_28db = 28`
  - [x] `LV8_00057_20db = 11`
- [x] Required total must be 191.
- [x] Use one stock sheet for the primary first-sheet probe.
- [x] Preserve fixture allowed rotations and geometry. If continuous/all-rotation parity is not supported, state this clearly.
- [x] Report whether first-sheet 191/191 is achieved. If not, report exact placed/unplaced count and top blockers.

## F. Runtime gates

- [x] Medium native CDE gate passes: 12/12, final pairs 0, boundary 0, no fallback, no compression.
- [x] LV8 12 types x1 regression still passes.
- [x] LV8 first-sheet reference probe is generated, run, and reported.
- [x] The first-sheet probe must not use bbox truth, LBF fallback, legacy fallback, or compression.
- [x] Final validation must be CDE-backed. Any placed subset must have 0 final pairs and 0 boundary violations.

## G. Required commands

- [x] `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`
- [x] `python3 scripts/smoke_sgh_q24r7_native_sparrow_sampler_evaluator_first_sheet_lv8.py`
- [x] `./scripts/check.sh`

## H. Report requirements

- [x] Write `codex/reports/egyedi_solver/sgh_q24r7_native_sparrow_sampler_evaluator_first_sheet_lv8.md`.
- [x] Include status lines:
  - [x] `SGH-Q24R7_STATUS: PASS|REVISE`
  - [x] `STATIC_ARCHITECTURE_GATE: PASS|FAIL`
  - [x] `STATIC_SAMPLER_EVALUATOR_GATE: PASS|FAIL`
  - [x] `RUNTIME_MEDIUM_CDE_GATE: PASS|FAIL`
  - [x] `RUNTIME_LV8_12TYPES_X1_GATE: PASS|FAIL`
  - [x] `RUNTIME_LV8_REFERENCE_SHEET1_GATE: PASS|FAIL|PARTIAL`
- [x] If first-sheet 191/191 fails, status may only be PASS if all hard architecture/evaluator gates pass and the report gives a concrete next algorithmic blocker. Do not fake 191/191.

## I. Q24R7 execution note

- Dense LV8 reference sheet-1 is reported as `PARTIAL`: the generated 191-instance input runs through the native `sparrow_cde` path and returns `partial` without bbox/LBF/legacy/compression, but it does not achieve a final CDE-valid 191/191 layout. The blocker is the remaining dense single-sheet search/runtime gap, not architecture fallback.
