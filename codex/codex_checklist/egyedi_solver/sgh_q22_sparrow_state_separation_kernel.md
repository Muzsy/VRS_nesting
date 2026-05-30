# Checklist — SGH-Q22 real SparrowState + separation kernel

## Dependency gate

- [x] Q20R-R1 report exists and is PASS/READY (`codex/reports/egyedi_solver/sgh_q20r_r1_topk_report_consistency_fix.md` → `SGH-Q20R_R1_STATUS: READY_FOR_AUDIT`)
- [x] Q21R1 report exists and is PASS/READY (`SGH-Q21R1_STATUS: READY_FOR_AUDIT`)
- [x] `SGH-Q22_STATUS: READY` present in Q21R1 report

## Pipeline routing

- [x] `OptimizerPipelineKind::SparrowExperimental` added (`rust/vrs_solver/src/io.rs`)
- [x] JSON value is `sparrow_experimental` (serde rename_all = "snake_case")
- [x] Adapter routes explicit sparrow_experimental to new kernel (`rust/vrs_solver/src/adapter.rs`)
- [x] LegacyMultisheet behavior unchanged (no other diagnostics output emitted)
- [x] PhaseOptimizer behavior unchanged (separate match arm; new Sparrow fields added as `Option = None`)
- [x] Optimizer diagnostics identify `pipeline_used = sparrow_experimental` (test: `sparrow_pipeline_routes_from_adapter`)

## Sparrow module

- [x] `rust/vrs_solver/src/optimizer/sparrow.rs` exists
- [x] Module exported from `optimizer/mod.rs`
- [x] `SparrowConfig` exists
- [x] `SparrowDiagnostics` exists
- [x] `SparrowState` exists
- [x] `CollisionGraphSnapshot` exists
- [x] `SparrowSeparationKernel` exists
- [x] `SparrowResult` exists

## Infeasible state lifecycle

- [x] SparrowState stores current layout
- [x] SparrowState permits infeasible intermediate layouts (test: `sparrow_state_allows_infeasible_intermediate_layout`)
- [x] Best feasible layout tracked (`best_feasible_layout: Option<WorkingLayout>`)
- [x] Best infeasible layout tracked (`best_infeasible_layout: Option<WorkingLayout>`)
- [x] Current raw/weighted loss tracked (`current_raw_loss`, `current_weighted_loss`)
- [x] Best infeasible raw/weighted loss tracked
- [x] Iterations tracked
- [x] Moves attempted/accepted tracked
- [x] Rollbacks tracked
- [x] GLS updates tracked
- [x] Seed/run metadata tracked (`SparrowState.seed`)

## Seed layout

- [x] Deterministic seed builder exists (`build_sparrow_seed_layout`)
- [x] All fit instances are included in seed placements (test: `sparrow_seed_layout_includes_all_fit_instances`)
- [x] Never-fit parts marked unplaced (`PART_NEVER_FITS_STOCK`)
- [x] Seed placements may intentionally overlap (place at (0,0) of first-fit sheet)
- [x] Rotation policy respected (uses `expand_instances_with_policy` and `can_fit_any_stock_with_policy`)
- [x] Same seed gives same seed layout (deterministic for-each iteration)
- [x] Q15 hole-free contract respected (no holes in inputs; outer-only)

## Collision graph

- [x] Pair collision count tracked (`colliding_pairs_count`)
- [x] Boundary violation count tracked (`boundary_violations_count`)
- [x] Total raw loss tracked
- [x] Total weighted loss tracked
- [x] Worst item identified deterministically (`worst_item_index`, ties broken by `instance_id`)
- [x] Worst pair identified deterministically (sorted by weighted_loss DESC, instance_id ASC)
- [x] Worst boundary violation identified deterministically (same)
- [x] Max pair/boundary weights tracked
- [x] Optional top summaries stable (`top_colliding_pairs`, `top_boundary_violations`, top-K)

## Separation loop

- [x] Loop is implemented in Sparrow kernel, not just PhaseOptimizer relabeling (`SparrowSeparationKernel::run`)
- [x] Target item selected from collision graph / weighted loss (`state.current_graph.worst_item_index`)
- [x] Primary relocation uses `search_position_for_target`
- [x] Candidate evaluated with active backend/severity (tracker rebuilt via `update_placement`)
- [x] Improvement committed (kept geometry + tracker state)
- [x] Non-improvement rolled back (`restore_but_keep_weights` + geometry restore)
- [x] GLS weights preserved through rollback (test: `sparrow_rollback_preserves_gls_weights`)
- [x] GLS weights updated on stagnation/collision (period `gls_update_period = 5`, plus on `search_position` None)
- [x] Best feasible state retained (`best_feasible_layout`)
- [x] Best infeasible state retained (`best_infeasible_layout` + `best_infeasible_raw_loss`)
- [x] Budget / max iteration / time limit obeyed (`max_iterations`, `time_limit_s`)

## Backend and final commit

- [x] Final successful output uses `WorkingLayout::validate_and_commit_with_backend`
- [x] Selected backend is respected (test: `sparrow_pipeline_final_commit_uses_selected_backend`)
- [x] CDE output reports correct backend (`backend_used` includes "cde_adapter" or similar)
- [x] CDE mode has `bbox_fallback_queries == 0` (test: `sparrow_pipeline_cde_has_no_bbox_fallback`)
- [x] Invalid colliding layout is not emitted as successful final output (no-feasible path returns `unsupported` with reason `SPARROW_NO_FEASIBLE_LAYOUT`)
- [x] Unsupported/partial behavior is explicit if no feasible layout found

## Diagnostics

- [x] `sparrow_invoked` exposed
- [x] seed placement/unplaced counts exposed (`sparrow_seed_placements`, `sparrow_seed_unplaced`)
- [x] initial/final raw loss exposed
- [x] initial/final weighted loss exposed
- [x] best infeasible losses exposed
- [x] iteration/move/rollback counts exposed
- [x] GLS weight update count exposed
- [x] convergence flag exposed (`sparrow_converged`)
- [x] initial/final graph counts exposed (`sparrow_collision_graph_initial_pairs`, `..._final_pairs`)
- [x] search_position stats exposed (`sparrow_search_position_calls`, `..._samples`)
- [x] severity stats exposed (`sparrow_severity_pair/boundary/probe_queries`)
- [x] LBF fallback count exposed and disabled by default (`sparrow_lbf_fallback_used`, `SparrowConfig.allow_lbf_fallback = false`)

## Measurement

- [x] `scripts/smoke_sgh_q22_sparrow_kernel.py` exists
- [x] overlap_two_rects fixture covered (converged 100%)
- [x] boundary_recovery fixture covered (single item, already feasible after seed)
- [x] three_item_collision_chain fixture covered (3 pairs → 0, 2 moves)
- [x] continuous_rotation_rescue fixture covered (converged 100%)
- [x] medium_10_to_20_items fixture covered (12 parts, 66 pairs → 0, 11 moves)
- [x] Smoke prints measurement table
- [x] Same-seed determinism checked (smoke + adapter test)
- [x] CDE/Jagua no bbox fallback checked (smoke + adapter test)
- [x] `scripts/bench_sgh_q22_sparrow_kernel.py --quick` exists and runs
- [x] Measurement JSON written (`sgh_q22_sparrow_state_separation_kernel_measurements.json`)
- [x] Measurement Markdown written (`sgh_q22_sparrow_state_separation_kernel_measurements.md`)

## Tests

- [x] seed includes all fit instances (`sparrow_seed_layout_includes_all_fit_instances`)
- [x] infeasible intermediate state allowed (`sparrow_state_allows_infeasible_intermediate_layout`)
- [x] collision graph counts pair/boundary violations (`collision_graph_snapshot_counts_pair_and_boundary_violations`)
- [x] worst weighted collider selection deterministic (`sparrow_selects_worst_weighted_collider_deterministically`)
- [x] move commit improves or rolls back (`sparrow_move_commit_improves_loss_or_rolls_back`)
- [x] rollback preserves GLS weights (`sparrow_rollback_preserves_gls_weights`)
- [x] two-rect overlap resolved (`sparrow_kernel_resolves_two_rect_overlap`)
- [x] boundary recovery resolved (`sparrow_kernel_boundary_recovery`)
- [x] adapter routing tested (`sparrow_pipeline_routes_from_adapter`)
- [x] final commit backend tested (`sparrow_pipeline_final_commit_uses_selected_backend`)
- [x] CDE no bbox fallback tested (`sparrow_pipeline_cde_has_no_bbox_fallback`)
- [x] same-seed determinism tested (`sparrow_kernel_same_seed_is_deterministic` + `sparrow_pipeline_same_seed_is_deterministic`)

## Verify

- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::sparrow` (9 passed)
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator` (47 passed)
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::search_position` (14 passed)
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::collision_severity` (13 passed)
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter` (4 new sparrow tests pass)
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` (417 passed total)
- [x] `python3 scripts/smoke_sgh_q22_sparrow_kernel.py` (14 passed, 0 failed)
- [x] `python3 scripts/bench_sgh_q22_sparrow_kernel.py --quick` (JSON + MD outputs written)
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q22_sparrow_state_separation_kernel.md`

## Report markers

- [x] First line is `PASS`, `REVISE`, or `BLOCKED`
- [x] PASS contains `SGH-Q22_STATUS: READY_FOR_AUDIT`
- [x] PASS contains `SPARROW_EXPERIMENTAL_STATUS: TESTABLE`
- [x] PASS contains `SGH-Q23_STATUS: HOLD` (Q23 strip-shrink / Algorithm 12/13 parity not yet)
- [x] PASS contains `Q19_STATUS: HOLD`
- [x] PASS contains `Q18B_RECOMMENDATION: NOT_REQUIRED_NOW`
