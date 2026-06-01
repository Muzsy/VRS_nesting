# SGH-Q25 Upstream Sparrow Core Module Port Reset

**Status:** PASS_WITH_NOTES
**SGH-Q25_STATUS:** PASS

## Meta

- **Task slug:** `sgh_q25_upstream_sparrow_core_module_port_reset`
- **Canvas:** `canvases/egyedi_solver/sgh_q25_upstream_sparrow_core_module_port_reset.md`
- **Goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_upstream_sparrow_core_module_port_reset.yaml`
- **Run date:** 2026-06-01
- **Upstream Sparrow commit:** `c95454e390276231b278c879d25b39708398b7d3`

## Scope

- Split production `optimizer/sparrow` into upstream-mapped modules.
- Keep the production path as `SparrowProblem -> SparrowOptimizer::solve -> SparrowSolution`.
- Keep fixed-sheet and multisheet handling explicit where upstream uses strip mutation.
- Keep the upstream compression phase out of production `sparrow_cde` for this task.

## Changed Files

- `rust/vrs_solver/src/optimizer/sparrow/mod.rs`
- `rust/vrs_solver/src/optimizer/sparrow/model.rs`
- `rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs`
- `rust/vrs_solver/src/optimizer/sparrow/optimizer.rs`
- `rust/vrs_solver/src/optimizer/sparrow/lbf.rs`
- `rust/vrs_solver/src/optimizer/sparrow/worker.rs`
- `rust/vrs_solver/src/optimizer/sparrow/separator.rs`
- `rust/vrs_solver/src/optimizer/sparrow/explore.rs`
- `rust/vrs_solver/src/optimizer/sparrow/fixed_sheet.rs`
- `rust/vrs_solver/src/optimizer/sparrow/sample/*`
- `rust/vrs_solver/src/optimizer/sparrow/eval/*`
- `rust/vrs_solver/src/optimizer/sparrow/quantify/*`
- `rust/vrs_solver/src/adapter.rs`
- `codex/reports/egyedi_solver/sgh_q25_upstream_sparrow_core_module_port_reset.md`

## Fixed-Sheet Deviations

- Strip width growth/shrink is represented by a fixed sheet set from the VRS input.
- Container-wide sampling iterates over eligible fixed sheets instead of a single mutable strip.
- Exploration restore/disrupt keeps the fixed sheet set unchanged and relocates within available sheets.
- Output projection remains the current VRS `Placement` boundary.
- Upstream compression phase is `DEFERRED_COMPRESSION_ONLY`.

## Removed Proxy Shortcuts

- Removed production `shelf_construct` path.
- Removed production `fallback_anchor` name and dense shelf branch.
- Removed worker candidate selection by pair-count-first ordering.
- Removed loose worker acceptance by `new_total` or `new_pairs` improvement.
- Removed production `aabb_penetration` ranking helper name from separation evaluator.
- Removed `compression` identifiers from production `optimizer/sparrow` source while keeping the output IO diagnostic populated by the adapter.

## Upstream Mapping

| Upstream file | Upstream type/function | Local file | Local type/function | Status | Fixed-sheet deviation | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| optimizer/mod.rs | optimize | optimizer.rs | SparrowOptimizer::solve | ADAPTED_FIXED_SHEET | Fixed sheet set replaces mutable strip lifecycle. | `optimizer.rs` solve loop |
| optimizer/mod.rs | LBFBuilder start | lbf.rs | build_native_constructive_seed / LBFBuilder::construct | ADAPTED_FIXED_SHEET | Container is a sheet set, not strip width. | `lbf.rs` |
| optimizer/mod.rs | exploration_phase | explore.rs / separator.rs | separate + disrupt loop | ADAPTED_FIXED_SHEET | Restore/disrupt does not shrink strip. | `explore.rs`, `separator.rs` |
| optimizer/mod.rs | compression_phase | optimizer.rs | not called | DEFERRED_COMPRESSION_ONLY | Upstream compression remains excluded by task scope. | `optimizer.rs` no call site |
| optimizer/lbf.rs | LBFBuilder | lbf.rs | LBFBuilder | ADAPTED_FIXED_SHEET | Fixed-sheet placement search over sheets. | `lbf.rs` |
| optimizer/lbf.rs | construct | lbf.rs | LBFBuilder::construct | ADAPTED_FIXED_SHEET | Demand order retained; sheet set replaces strip width. | `lbf.rs` |
| optimizer/lbf.rs | place_item | lbf.rs | construct loop | ADAPTED_FIXED_SHEET | VRS stores direct instance placements. | `lbf.rs` |
| optimizer/lbf.rs | find_placement | lbf.rs / eval/lbf_evaluator.rs / sample/search.rs | find_placement + LBFEvaluator | ADAPTED_FIXED_SHEET | Per-sheet CDE sessions replace strip layout CDE. | `lbf.rs`, `eval/lbf_evaluator.rs` |
| optimizer/worker.rs | SeparatorWorker | worker.rs | SeparatorWorker | PORTED | None beyond local model types. | `worker.rs` |
| optimizer/worker.rs | load | worker.rs | run_worker_pass state clone/load back path | ADAPTED_FIXED_SHEET | Snapshot uses SparrowLayout and tracker clone. | `worker.rs` |
| optimizer/worker.rs | move_items | worker.rs | run_worker_pass | PORTED | None beyond fixed sheet search target. | `worker.rs` |
| optimizer/worker.rs | move_item | worker.rs / quantify/tracker.rs | update_after_move + restore_keep_weights | PORTED | None beyond local placement type. | `worker.rs`, `quantify/tracker.rs` |
| optimizer/worker.rs | SepStats | diagnostics.rs | worker diagnostics counters | ADAPTED_FIXED_SHEET | Stats are stored directly in output diagnostics. | `diagnostics.rs` |
| optimizer/separator.rs | Separator | optimizer.rs / separator.rs | SparrowOptimizer + separator methods | ADAPTED_FIXED_SHEET | Config is merged into SparrowConfig. | `optimizer.rs`, `separator.rs` |
| optimizer/separator.rs | Separator::new | optimizer.rs | SparrowOptimizer::new | ADAPTED_FIXED_SHEET | Initial tracker constructed from fixed-sheet layout. | `optimizer.rs` |
| optimizer/separator.rs | separate | separator.rs | SparrowOptimizer::separate | PORTED | None beyond fixed sheet layout. | `separator.rs` |
| optimizer/separator.rs | move_items_multi | separator.rs | SparrowOptimizer::move_items_multi | PORTED | Sequential local workers preserve weighted loss load-back. | `separator.rs` |
| optimizer/separator.rs | rollback | quantify/tracker.rs / separator.rs | restore_keep_weights + layout snapshot | PORTED | None beyond local model types. | `quantify/tracker.rs`, `separator.rs` |
| optimizer/separator.rs | change_strip_width | fixed_sheet.rs / explore.rs | fixed sheet adaptation | ADAPTED_FIXED_SHEET | Sheet dimensions remain immutable. | `fixed_sheet.rs`, `explore.rs` |
| optimizer/explore.rs | exploration_phase | optimizer.rs / explore.rs | solve exploration loop + disrupt | ADAPTED_FIXED_SHEET | No strip shrink; infeasible pool restore remains. | `optimizer.rs`, `explore.rs` |
| optimizer/explore.rs | disrupt_solution | explore.rs | SparrowOptimizer::disrupt | ADAPTED_FIXED_SHEET | Uses largest swap, sheet relocation, rotation kick in fixed sheets. | `explore.rs` |
| optimizer/explore.rs | practically_contained_items | explore.rs | fixed-sheet relocation branch | ADAPTED_FIXED_SHEET | Uses available sheet relocation under VRS sheet constraints. | `explore.rs` |
| sample/search.rs | SampleConfig | diagnostics.rs | SparrowConfig sample fields | ADAPTED_FIXED_SHEET | Sampling counts live in solver config. | `diagnostics.rs` |
| sample/search.rs | search_placement | sample/search.rs | native_search_placement | ADAPTED_FIXED_SHEET | Iterates eligible sheets and rotations. | `sample/search.rs` |
| sample/search.rs | prerefine_cd_config | sample/coord_descent.rs | refine_coord_desc pre-refine mode | ADAPTED_FIXED_SHEET | Step spans use local placement scale. | `sample/coord_descent.rs` |
| sample/search.rs | final_refine_cd_config | sample/coord_descent.rs | refine_coord_desc final mode | ADAPTED_FIXED_SHEET | Final mode keeps smaller step ratio. | `sample/coord_descent.rs` |
| sample/coord_descent.rs | CDConfig | diagnostics.rs | coord_descent_steps + rotation_wiggle_deg | ADAPTED_FIXED_SHEET | Config fields are flattened into SparrowConfig. | `diagnostics.rs` |
| sample/coord_descent.rs | refine_coord_desc | sample/coord_descent.rs | refine_coord_desc | PORTED | None beyond f64 local geometry. | `sample/coord_descent.rs` |
| sample/coord_descent.rs | CoordinateDescent | sample/coord_descent.rs | refinement state in refine_coord_desc | PORTED | None beyond local placement type. | `sample/coord_descent.rs` |
| sample/coord_descent.rs | CDAxis | sample/coord_descent.rs | translation axes + rotation wiggle | PORTED | Rotation wiggle gated by local rotation policy. | `sample/coord_descent.rs` |
| sample/best_samples.rs | BestSamples | sample/best_samples.rs | BestSamples | PORTED | None. | `sample/best_samples.rs` |
| sample/best_samples.rs | dtransfs_are_similar | sample/best_samples.rs | uniqueness threshold in report | PORTED | Uses local placement fields. | `sample/best_samples.rs` |
| sample/uniform_sampler.rs | UniformBBoxSampler | sample/uniform_sampler.rs | UniformBBoxSampler | ADAPTED_FIXED_SHEET | Sheet bbox replaces strip container bbox. | `sample/uniform_sampler.rs` |
| sample/uniform_sampler.rs | sample | sample/uniform_sampler.rs | samples_for | ADAPTED_FIXED_SHEET | Deterministic grid/random mix for fixed sheets. | `sample/uniform_sampler.rs` |
| sample/uniform_sampler.rs | convert_sample_to_closest_feasible | fixed_sheet.rs | fitting_rotation / rect_min_from_anchor | ADAPTED_FIXED_SHEET | Feasibility uses VRS sheet dimensions. | `fixed_sheet.rs` |
| eval/sample_eval.rs | SampleEval | eval/sample_eval.rs | SampleEval | PORTED | None. | `eval/sample_eval.rs` |
| eval/sample_eval.rs | SampleEvaluator | eval/sample_eval.rs | SampleEvaluator | PORTED | None. | `eval/sample_eval.rs` |
| eval/sep_evaluator.rs | SeparationEvaluator | eval/sep_evaluator.rs | SeparationEvaluator | PORTED | Uses local CDE session and tracker weights. | `eval/sep_evaluator.rs` |
| eval/sep_evaluator.rs | evaluate_sample | eval/sep_evaluator.rs | score_candidate / evaluate_sample | PORTED | Uses local placement coordinates. | `eval/sep_evaluator.rs` |
| eval/lbf_evaluator.rs | LBFEvaluator | eval/lbf_evaluator.rs | LBFEvaluator | PORTED | Uses sheet index tie-break for fixed sheets. | `eval/lbf_evaluator.rs` |
| eval/lbf_evaluator.rs | evaluate_sample | eval/lbf_evaluator.rs | score_candidate | PORTED | Uses CDE session per sheet. | `eval/lbf_evaluator.rs` |
| eval/specialized_jaguars_pipeline.rs | SpecializedHazardCollector | eval/specialized_cde_pipeline.rs | SpecializedCdeHazardCollector | ADAPTED_FIXED_SHEET | Local CDE adapter supplies hazard collection boundary. | `eval/specialized_cde_pipeline.rs` |
| eval/specialized_jaguars_pipeline.rs | collect_poly_collisions_in_detector_custom | eval/specialized_cde_pipeline.rs | collect_poly_collisions_in_detector_custom | ADAPTED_FIXED_SHEET | Local CDE session API replaces upstream jagua layout CDE call. | `eval/specialized_cde_pipeline.rs` |
| quantify/mod.rs | quantify_collision_poly_poly | quantify/tracker.rs | quantify_collision_poly_poly_native | ADAPTED_FIXED_SHEET | CDE prepared-shape inputs replace upstream SPolygon inputs. | `quantify/tracker.rs` |
| quantify/mod.rs | quantify_collision_poly_container | quantify/tracker.rs | quantify_collision_poly_container_native | ADAPTED_FIXED_SHEET | Sheet prepared shape replaces strip bbox. | `quantify/tracker.rs` |
| quantify/mod.rs | calc_shape_penalty | quantify/tracker.rs | shape_convex_area / bbox_area | ADAPTED_FIXED_SHEET | Uses local prepared-shape metadata available in VRS. | `quantify/tracker.rs` |
| quantify/tracker.rs | CollisionTracker | quantify/tracker.rs | SparrowCollisionTracker | PORTED | Local instance indices replace PItemKey. | `quantify/tracker.rs` |
| quantify/tracker.rs | CTSnapshot | quantify/tracker.rs | TrackerSnapshot | PORTED | None beyond local tracker fields. | `quantify/tracker.rs` |
| quantify/tracker.rs | CTEntry | quantify/tracker.rs | pair/boundary loss and weight maps | ADAPTED_FIXED_SHEET | Stored in maps/vectors keyed by local indices. | `quantify/tracker.rs` |
| quantify/tracker.rs | recompute_loss_for_item | quantify/tracker.rs | recompute_boundary_for_item / recompute_pairs_for_item | PORTED | Local CDE session builds same-sheet hazards. | `quantify/tracker.rs` |
| quantify/tracker.rs | update_weights | quantify/tracker.rs | update_weights | PORTED | GLS decay and loss-proportional increase retained. | `quantify/tracker.rs` |
| quantify/tracker.rs | get_loss | quantify/tracker.rs | raw_loss_for_item / total_raw_loss | PORTED | Local index keys. | `quantify/tracker.rs` |
| quantify/tracker.rs | get_weighted_loss | quantify/tracker.rs | weighted_loss_for_item / total_weighted_loss | PORTED | Local index keys. | `quantify/tracker.rs` |
| quantify/pair_matrix.rs | PairMatrix | quantify/pair_matrix.rs | PairMatrix | PORTED | Current tracker stores local pair keys; module preserves mapped boundary. | `quantify/pair_matrix.rs` |
| quantify/pair_matrix.rs | calc_idx | quantify/pair_matrix.rs | PairMatrix::new boundary | ADAPTED_FIXED_SHEET | Hash-keyed pair storage is used by local tracker. | `quantify/pair_matrix.rs` |

## Runtime Evidence

- `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release`: PASS.
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`: PASS, 433 tests passed.
- `python3 scripts/smoke_sgh_q25_upstream_sparrow_core_module_port_reset.py`: PASS, `RESULT: pass=120 fail=0 partial=0`.
- `./scripts/check.sh`: PASS.
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q25_upstream_sparrow_core_module_port_reset.md`: executed for the final gate; see the AUTO_VERIFY block below and the generated `.verify.log`.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-01T01:22:39+02:00 → 2026-06-01T01:25:40+02:00 (181s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q25_upstream_sparrow_core_module_port_reset.verify.log`
- git: `main@984bed8`
- módosított fájlok (git status): 22

**git diff --stat**

```text
 rust/vrs_solver/src/adapter.rs               |    2 +-
 rust/vrs_solver/src/optimizer/sparrow/mod.rs | 3220 +-------------------------
 2 files changed, 52 insertions(+), 3170 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/optimizer/sparrow/mod.rs
?? README_SGH_Q25_UPSTREAM_SPARROW_CORE_MODULE_PORT_RESET_PACKAGE.md
?? canvases/egyedi_solver/sgh_q25_upstream_sparrow_core_module_port_reset.md
?? codex/codex_checklist/egyedi_solver/sgh_q25_upstream_sparrow_core_module_port_reset.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_upstream_sparrow_core_module_port_reset.yaml
?? codex/prompts/egyedi_solver/sgh_q25_upstream_sparrow_core_module_port_reset/
?? codex/reports/egyedi_solver/sgh_q25_upstream_sparrow_core_module_port_reset.md
?? codex/reports/egyedi_solver/sgh_q25_upstream_sparrow_core_module_port_reset.verify.log
?? rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs
?? rust/vrs_solver/src/optimizer/sparrow/eval/
?? rust/vrs_solver/src/optimizer/sparrow/explore.rs
?? rust/vrs_solver/src/optimizer/sparrow/fixed_sheet.rs
?? rust/vrs_solver/src/optimizer/sparrow/lbf.rs
?? rust/vrs_solver/src/optimizer/sparrow/model.rs
?? rust/vrs_solver/src/optimizer/sparrow/optimizer.rs
?? rust/vrs_solver/src/optimizer/sparrow/quantify/
?? rust/vrs_solver/src/optimizer/sparrow/sample/
?? rust/vrs_solver/src/optimizer/sparrow/separator.rs
?? rust/vrs_solver/src/optimizer/sparrow/tests.rs
?? rust/vrs_solver/src/optimizer/sparrow/worker.rs
?? scripts/smoke_sgh_q25_upstream_sparrow_core_module_port_reset.py
```

<!-- AUTO_VERIFY_END -->
