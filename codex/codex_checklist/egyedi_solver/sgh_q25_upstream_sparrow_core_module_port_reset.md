# SGH-Q25 checklist — Upstream Sparrow core module-by-module port reset

## A. Upstream reading and pinning

- [x] Confirm `.cache/sparrow` exists or run the repo's Sparrow setup script.
- [x] Record the upstream Sparrow commit hash in the report.
- [x] Read `.cache/sparrow/src/optimizer/mod.rs`.
- [x] Read `.cache/sparrow/src/optimizer/lbf.rs`.
- [x] Read `.cache/sparrow/src/optimizer/worker.rs`.
- [x] Read `.cache/sparrow/src/optimizer/separator.rs`.
- [x] Read `.cache/sparrow/src/optimizer/explore.rs`.
- [x] Read `.cache/sparrow/src/sample/search.rs`.
- [x] Read `.cache/sparrow/src/sample/coord_descent.rs`.
- [x] Read `.cache/sparrow/src/sample/best_samples.rs`.
- [x] Read `.cache/sparrow/src/sample/uniform_sampler.rs`.
- [x] Read `.cache/sparrow/src/eval/sample_eval.rs`.
- [x] Read `.cache/sparrow/src/eval/sep_evaluator.rs`.
- [x] Read `.cache/sparrow/src/eval/lbf_evaluator.rs`.
- [x] Read `.cache/sparrow/src/eval/specialized_jaguars_pipeline.rs`.
- [x] Read `.cache/sparrow/src/quantify/mod.rs`.
- [x] Read `.cache/sparrow/src/quantify/tracker.rs`.
- [x] Read `.cache/sparrow/src/quantify/pair_matrix.rs`.

## B. Module reset

- [x] Split `rust/vrs_solver/src/optimizer/sparrow/mod.rs` into a thin wiring file.
- [x] Add `model.rs`.
- [x] Add `optimizer.rs`.
- [x] Add `lbf.rs`.
- [x] Add `worker.rs`.
- [x] Add `separator.rs`.
- [x] Add `explore.rs`.
- [x] Add `fixed_sheet.rs`.
- [x] Add `diagnostics.rs`.
- [x] Add `sample/mod.rs`.
- [x] Add `sample/search.rs`.
- [x] Add `sample/coord_descent.rs`.
- [x] Add `sample/best_samples.rs`.
- [x] Add `sample/uniform_sampler.rs`.
- [x] Add `eval/mod.rs`.
- [x] Add `eval/sample_eval.rs`.
- [x] Add `eval/sep_evaluator.rs`.
- [x] Add `eval/lbf_evaluator.rs`.
- [x] Add `eval/specialized_cde_pipeline.rs`.
- [x] Add `quantify/mod.rs`.
- [x] Add `quantify/tracker.rs`.
- [x] Add `quantify/pair_matrix.rs`.
- [x] Add `quantify/overlap_proxy.rs` or equivalent upstream quantification module.

## C. Ban old/proxy production paths

- [x] No production `WorkingLayout` usage inside `optimizer/sparrow`.
- [x] No production `VrsCollisionTracker` usage inside `optimizer/sparrow`.
- [x] No production `SparrowSeparationKernel` usage inside `optimizer/sparrow`.
- [x] No production `PhaseOptimizer` / `MultiSheetManager` dependency inside `optimizer/sparrow`.
- [x] No `shelf_construct` production LBF shortcut.
- [x] No `fallback_anchor` production LBF shortcut.
- [x] No AABB penetration as separation evaluator ranking loss.
- [x] No `ix * iy` overlap proxy in production evaluator/quantifier except inside a directly ported upstream overlap proxy module with documented parity.
- [x] No worker choice by pair-count first.
- [x] No move acceptance by loose `new_total` / `new_pairs` improvement.

## D. Upstream parity by module

- [x] `quantify/tracker.rs` maps upstream tracker semantics.
- [x] `quantify/pair_matrix.rs` maps upstream pair matrix semantics.
- [x] `quantify/overlap_proxy.rs` maps upstream quantification semantics or documents exact local dependency constraint.
- [x] `eval/sample_eval.rs` maps upstream sample evaluator semantics.
- [x] `eval/sep_evaluator.rs` maps upstream separation evaluator semantics.
- [x] `eval/lbf_evaluator.rs` maps upstream LBF evaluator semantics.
- [x] `eval/specialized_cde_pipeline.rs` maps upstream specialized jagua pipeline to local CDE.
- [x] `sample/search.rs` maps upstream search placement semantics.
- [x] `sample/coord_descent.rs` maps upstream coordinate descent semantics.
- [x] `sample/best_samples.rs` maps upstream best sample uniqueness semantics.
- [x] `sample/uniform_sampler.rs` maps upstream uniform sampler semantics.
- [x] `lbf.rs` maps upstream LBFBuilder semantics with fixed-sheet adaptation only where necessary.
- [x] `worker.rs` maps upstream worker semantics.
- [x] `separator.rs` maps upstream separator semantics.
- [x] `explore.rs` maps upstream exploration/disruption semantics excluding compression.

## E. Fixed-sheet deviations

- [x] Strip expansion/shrink deviation documented.
- [x] Multisheet container-choice deviation documented.
- [x] Compression-only code explicitly deferred.
- [x] No fixed-sheet deviation used as excuse for shelf/proxy shortcuts.

## F. Verification

- [x] Run `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release`.
- [x] Run `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`.
- [x] Run `python3 scripts/smoke_sgh_q25_upstream_sparrow_core_module_port_reset.py`.
- [x] Run `./scripts/check.sh`.
- [x] Run `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q25_upstream_sparrow_core_module_port_reset.md`.

## G. Report

- [x] Write `codex/reports/egyedi_solver/sgh_q25_upstream_sparrow_core_module_port_reset.md`.
- [x] Include `SGH-Q25_STATUS: PASS|REVISE`.
- [x] Include upstream commit hash.
- [x] Include the required upstream-to-local mapping table.
- [x] Include list of fixed-sheet deviations.
- [x] Include list of removed proxy shortcuts.
- [x] Include runtime evidence.
- [x] Include no-compression evidence.
