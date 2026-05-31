# SGH-Q24R9 checklist — Exact upstream-style tracker/evaluator/search semantics

## A. Mandatory upstream reading

- [ ] Read `.cache/sparrow/src/quantify/tracker.rs`.
- [ ] Read `.cache/sparrow/src/quantify/mod.rs` and any referenced quantification code.
- [ ] Read `.cache/sparrow/src/eval/sample_eval.rs`.
- [ ] Read `.cache/sparrow/src/eval/sep_evaluator.rs`.
- [ ] Read `.cache/sparrow/src/eval/lbf_evaluator.rs`.
- [ ] Read `.cache/sparrow/src/sample/search.rs`.
- [ ] Read `.cache/sparrow/src/sample/best_samples.rs`.
- [ ] Read `.cache/sparrow/src/sample/coord_descent.rs`.
- [ ] Read `.cache/sparrow/src/sample/uniform_sampler.rs`.
- [ ] Read `.cache/sparrow/src/optimizer/worker.rs`.
- [ ] Read `.cache/sparrow/src/optimizer/separator.rs`.
- [ ] Read `.cache/sparrow/src/optimizer/explore.rs`.
- [ ] Read current `rust/vrs_solver/src/optimizer/sparrow/mod.rs`.
- [ ] Read Q24R8 report and identify all proxy semantics.

## B. Architecture preservation

- [ ] Production `sparrow_cde` still uses `SparrowProblem`.
- [ ] Production `sparrow_cde` still calls `SparrowOptimizer::solve`.
- [ ] Production output still projects from `SparrowSolution` only at the API boundary.
- [ ] No production use of `WorkingLayout` inside optimizer/sparrow.
- [ ] No production use of `VrsCollisionTracker` inside optimizer/sparrow.
- [ ] No production use of `SparrowSeparationKernel` inside optimizer/sparrow.
- [ ] No legacy fallback in production `sparrow_cde`.

## C. Tracker quantification

- [ ] Remove bbox-overlap pair loss as primary quantification.
- [ ] Remove bbox-outside-area container loss as primary quantification.
- [ ] Implement CDE/hazard/resolution-style pair loss.
- [ ] Implement CDE/hazard/resolution-style container loss.
- [ ] Add/verify diagnostics for pair truth queries.
- [ ] Add/verify diagnostics for boundary truth queries.
- [ ] Add/verify diagnostics for pair quantification probes.
- [ ] Add/verify diagnostics for boundary quantification probes.
- [ ] Tracker stores pair/container loss and weight entries.
- [ ] Tracker exposes item raw and weighted losses.
- [ ] Tracker restore keeps weights.
- [ ] GLS update follows upstream-style loss-proportional semantics.

## D. Evaluators

- [ ] `SeparationEvaluator` uses tracker pair/container weights.
- [ ] `SeparationEvaluator` does CDE hazard collection for candidate placement.
- [ ] `SeparationEvaluator` uses quantified hazard loss, not AABB overlap.
- [ ] `SeparationEvaluator` supports upper-bound pruning.
- [ ] `LBFEvaluator` uses CDE truth and quantified least-infeasible fallback.
- [ ] Clear candidate ranking only applies after zero collision loss.

## E. Search and coordinate descent

- [ ] `BestSamples` uniqueness remains active.
- [ ] Focused and whole-container sampling remain active.
- [ ] Coordinate descent has two stages.
- [ ] Coordinate descent supports nonzero rotation wiggle when policy allows it.
- [ ] Add a synthetic/unit/smoke proof for rotation wiggle path.

## F. Worker/separator semantics

- [ ] Remove permissive `new_total < old_total || new_pairs < old_pairs` move acceptance.
- [ ] Worker acceptance is driven by moved-item/tracker weighted loss semantics.
- [ ] `move_items_multi` still starts all workers from the same master state.
- [ ] Best worker load-back remains active.
- [ ] Separator rollback preserves weights correctly.

## G. Compression exclusion

- [ ] Compression remains disabled by default.
- [ ] No compression phase is implemented/hardened in this task.
- [ ] Runtime diagnostics show zero compression passes.

## H. Runtime verification

- [ ] `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release` PASS.
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` PASS.
- [ ] `python3 scripts/smoke_sgh_q24r9_exact_upstream_style_tracker_evaluator_search_semantics.py` PASS or PASS_WITH_EXPLICIT_191_PARTIAL.
- [ ] `./scripts/check.sh` PASS.
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q24r9_exact_upstream_style_tracker_evaluator_search_semantics.md` PASS.

## I. Dense evidence

- [ ] 191 first-sheet run is real, not guarded.
- [ ] 191 run performs full final validation.
- [ ] final raw loss < initial raw loss.
- [ ] final pairs < initial pairs.
- [ ] validated placements > 39.
- [ ] target: final pairs <= 120 or exact blocker documented.
- [ ] target: validated placements >= 60 or exact blocker documented.
- [ ] unresolved IDs and reasons are reported if partial.

## J. Report

- [ ] Write `codex/reports/egyedi_solver/sgh_q24r9_exact_upstream_style_tracker_evaluator_search_semantics.md`.
- [ ] Include `SGH-Q24R9_STATUS: PASS|REVISE`.
- [ ] Include upstream-to-local tracker/evaluator/search parity map.
- [ ] Include proof that bbox proxy is not primary loss.
- [ ] Include runtime metrics and dense comparison to Q24R8.
- [ ] Include no-compression proof.
