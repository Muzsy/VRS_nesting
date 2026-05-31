# SGH-Q24R8 checklist — Full native Sparrow core parity, compression excluded

## A. Mandatory reading

- [x] Read `.cache/sparrow/src/optimizer/mod.rs` and understand `optimize`: LBFBuilder -> exploration_phase -> compression_phase.
- [x] Read `.cache/sparrow/src/optimizer/lbf.rs`.
- [x] Read `.cache/sparrow/src/optimizer/separator.rs`.
- [x] Read `.cache/sparrow/src/optimizer/worker.rs`.
- [x] Read `.cache/sparrow/src/optimizer/explore.rs`.
- [x] Read `.cache/sparrow/src/sample/search.rs`.
- [x] Read `.cache/sparrow/src/sample/best_samples.rs`.
- [x] Read `.cache/sparrow/src/sample/coord_descent.rs`.
- [x] Read `.cache/sparrow/src/sample/uniform_sampler.rs`.
- [x] Read `.cache/sparrow/src/eval/sep_evaluator.rs`.
- [x] Read `.cache/sparrow/src/eval/lbf_evaluator.rs`.
- [x] Read `.cache/sparrow/src/eval/sample_eval.rs`.
- [x] Read `.cache/sparrow/src/quantify/tracker.rs`.
- [x] Read `.cache/sparrow/src/quantify/mod.rs` / collision quantification implementation.
- [x] Read current `rust/vrs_solver/src/optimizer/sparrow/mod.rs` and identify all current local shortcuts.
- [x] Read Q24R7-R1 report and understand the weak dense result.

## B. Architecture preservation

- [x] `run_sparrow_pipeline` still calls native `SparrowProblem::from_solver_input`.
- [x] `run_sparrow_pipeline` still calls `SparrowOptimizer::solve`.
- [x] `SparrowSolution` is projected to `crate::io::Placement` only at the final output boundary.
- [x] No production use of `WorkingLayout`.
- [x] No production use of `VrsCollisionTracker`.
- [x] No production use of `SparrowSeparationKernel`.
- [x] No production use of `PhaseOptimizer` / `MultiSheetManager` / legacy VRS solver core.

## C. Native module parity

- [x] Implement/native-port `LBFBuilder` equivalent for fixed sheets.
- [x] Implement/native-port `CollisionTracker` equivalent with real CDE hazard collection and quantified loss.
- [x] Implement/native-port `SampleEval` and `SampleEvaluator` abstractions.
- [x] Implement/native-port `BestSamples` with uniqueness threshold.
- [x] Implement/native-port `UniformBBoxSampler` for focused and container-wide sampling.
- [x] Implement/native-port two-stage coordinate descent with rotation wiggle support.
- [x] Implement/native-port `search_placement` equivalent.
- [x] Implement/native-port `SeparationEvaluator` equivalent using tracker weights and quantified losses.
- [x] Implement/native-port `LBFEvaluator` equivalent for initial construction.
- [x] Implement/native-port `SeparatorWorker` equivalent.
- [x] Implement/native-port `Separator::separate` Algorithm 9 equivalent.
- [x] Implement/native-port `move_items_multi` Algorithm 10 equivalent.
- [x] Implement/native-port exploration pool/restore/disruption Algorithm 12 equivalent, omitting strip shrink and compression.

## D. Remove non-Sparrow shortcuts

- [x] Remove production `is_dense_reference_case` branching from the solve semantics.
- [x] Remove production dense throttling from `scaled_for_instance_count`.
- [x] Remove `max_targets=1` dense behavior.
- [x] Remove `others.truncate(24)` from production CDE/session/evaluator logic.
- [x] Remove `SparrowState::new_with_bounded_diag` from production solve path.
- [x] Remove `final_validation_tracker_bounded` from production final validation.
- [x] Remove `polygon_overlap_surrogate_loss` as primary pair loss.
- [x] Remove `polygon_boundary_surrogate_loss` as primary boundary/container loss.
- [x] Remove row/grid seed as the primary initial constructor.
- [x] Keep compression disabled and unused.

## E. Correctness gates

- [x] Tracker loss comes from CDE-confirmed hazards and real quantification functions.
- [x] Tracker stores pair and container entries with loss and weight.
- [x] Tracker restore keeps weights while restoring losses/layout mapping.
- [x] GLS weight update is proportional to loss relative to current maximum, with decay/floor behavior matching Sparrow.
- [x] Worker moves every still-colliding item in shuffled order, unless time budget expires.
- [x] `move_items_multi` loads the lowest weighted-loss worker state back into master.
- [x] Separator rollback uses min-loss solution + tracker snapshot and keeps GLS weights.
- [x] Search uses best-sample pool and coordinate descent, not a fixed 1x1 grid.
- [x] Full final validation is real CDE validation over all same-sheet pairs and boundaries.

## F. Runtime gates

- [x] `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release` PASS.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` PASS.
- [x] `python3 scripts/smoke_sgh_q24r8_full_native_sparrow_core_parity_no_compression.py` PASS or PASS_WITH_EXPLICIT_191_PARTIAL.
- [x] `./scripts/check.sh` PASS.
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q24r8_full_native_sparrow_core_parity_no_compression.md` PASS.

## G. Required measurements

- [x] Medium native CDE: valid 12/12, final pairs 0, boundary 0.
- [x] LV8 12 types x1: valid 12/12, final pairs 0, boundary 0.
- [x] LV8 reference sheet-1 191: real full search and full validation.
- [x] For 191: final raw loss < initial raw loss.
- [x] For 191: final pairs < initial pairs.
- [x] For 191: validated placements > 36.
- [x] For 191: search calls / samples / worker moves / CDE quantified queries are not Q24R7-R1-level tiny constants.
- [x] Report exact unresolved blockers if still partial.

## H. Report

- [x] Write `codex/reports/egyedi_solver/sgh_q24r8_full_native_sparrow_core_parity_no_compression.md`.
- [x] Include `SGH-Q24R8_STATUS: PASS|REVISE`.
- [x] Include upstream-to-local parity map.
- [x] Include changed files.
- [x] Include runtime metrics.
- [x] Include explicit no-compression proof.
- [x] Include explicit no-old-core proof.
