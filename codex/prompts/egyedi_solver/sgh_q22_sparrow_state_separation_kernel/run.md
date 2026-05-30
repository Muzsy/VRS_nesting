# Runner — SGH-Q22 real SparrowState + separation kernel with measurement

Implement SGH-Q22 from:

```text
canvases/egyedi_solver/sgh_q22_sparrow_state_separation_kernel.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q22_sparrow_state_separation_kernel.yaml
codex/codex_checklist/egyedi_solver/sgh_q22_sparrow_state_separation_kernel.md
```

## Non-negotiable goal

This task is not a small improvement and not a relabeling exercise. Implement the first testable **jagua_rs/Sparrow-style kernel**:

```text
intentional infeasible state
explicit collision graph
GLS-guided target selection
search_position relocation
backend-oracle evaluate_transform/collision_severity
commit/rollback preserving GLS weights
final backend validation
measurement fixtures
```

If the implementation only calls the existing phase optimizer or separator and labels it Sparrow, the task is REVISE.

## Dependency gate

Before edits, verify:

```text
codex/reports/egyedi_solver/sgh_q20r_r1_topk_report_consistency_fix.md
codex/reports/egyedi_solver/sgh_q21r1_collision_severity_full_sparrow_alignment.md
```

Required markers:

```text
SGH-Q20R_R1_STATUS: READY_FOR_AUDIT
SGH-Q21R1_STATUS: READY_FOR_AUDIT
SGH-Q22_STATUS: READY
```

If missing, produce BLOCKED report and stop.

## Required implementation

### 1. New pipeline

Add `OptimizerPipelineKind::SparrowExperimental` with JSON value:

```json
"sparrow_experimental"
```

Wire adapter routing. Existing pipelines must not regress.

### 2. New module

Create:

```text
rust/vrs_solver/src/optimizer/sparrow.rs
```

Export from `optimizer/mod.rs`.

Minimum concepts:

```text
SparrowConfig
SparrowDiagnostics
SparrowState
CollisionGraphSnapshot
SparrowSeparationKernel
SparrowResult
```

### 3. Infeasible seed

Create a deterministic seed builder for sparrow mode. It must include all instances that can fit under policy, even if placements overlap. Never-fit parts become unplaced.

Do not rely on LBF to decide which difficult items disappear.

### 4. Collision graph

Build deterministic graph snapshots from tracker/severity state. Include pair collisions, boundary violations, raw and weighted loss, worst item/pair/boundary, max weights, and stable top summaries where feasible.

### 5. Separation loop

Implement the real loop:

```text
build state and graph
if feasible -> validate final backend and return
select worst weighted target
search_position_for_target
backend-oracle evaluate/score
apply candidate tentatively
if improved -> commit
else rollback geometry, preserve/update GLS weights
update graph and best feasible/infeasible
repeat until budget
```

Use `search_position_for_target` as the primary relocation engine. LBF fallback must be disabled by default or explicitly counted as compatibility fallback.

### 6. Diagnostics

Expose diagnostics in `OptimizerDiagnosticsOutput` or equivalent optional fields:

```text
pipeline_used=sparrow_experimental
sparrow_invoked
sparrow_seed_placements
sparrow_seed_unplaced
sparrow_initial_raw_loss
sparrow_initial_weighted_loss
sparrow_final_raw_loss
sparrow_final_weighted_loss
sparrow_best_infeasible_raw_loss
sparrow_best_infeasible_weighted_loss
sparrow_iterations
sparrow_moves_attempted
sparrow_moves_accepted
sparrow_rollbacks
sparrow_gls_weight_updates
sparrow_converged
sparrow_collision_graph_initial_pairs
sparrow_collision_graph_final_pairs
sparrow_boundary_violations_initial
sparrow_boundary_violations_final
sparrow_search_position_calls
sparrow_search_position_samples
sparrow_severity_pair_queries
sparrow_severity_boundary_queries
sparrow_severity_probe_queries
sparrow_lbf_fallback_used
```

### 7. Measurement scripts

Add:

```text
scripts/smoke_sgh_q22_sparrow_kernel.py
scripts/bench_sgh_q22_sparrow_kernel.py
```

Smoke fixtures minimum:

```text
overlap_two_rects
boundary_recovery
three_item_collision_chain
continuous_rotation_rescue
medium_10_to_20_items
```

Smoke must print a measurement table with runtime, initial/final loss, iterations, moves, rollbacks, graph counts, query counts, fallback counts, and feasibility.

`bench_sgh_q22_sparrow_kernel.py --quick` must produce:

```text
codex/reports/egyedi_solver/sgh_q22_sparrow_state_separation_kernel_measurements.json
codex/reports/egyedi_solver/sgh_q22_sparrow_state_separation_kernel_measurements.md
```

## Tests

Add or map tests for:

```text
sparrow_seed_layout_includes_all_fit_instances
sparrow_state_allows_infeasible_intermediate_layout
collision_graph_snapshot_counts_pair_and_boundary_violations
sparrow_selects_worst_weighted_collider_deterministically
sparrow_move_commit_improves_loss_or_rolls_back
sparrow_rollback_preserves_gls_weights
sparrow_kernel_resolves_two_rect_overlap
sparrow_kernel_boundary_recovery
sparrow_pipeline_routes_from_adapter
sparrow_pipeline_final_commit_uses_selected_backend
sparrow_pipeline_cde_has_no_bbox_fallback
sparrow_pipeline_same_seed_is_deterministic
```

## Verify commands

Run:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::sparrow
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::search_position
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::collision_severity
cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q22_sparrow_kernel.py
python3 scripts/bench_sgh_q22_sparrow_kernel.py --quick
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q22_sparrow_state_separation_kernel.md
```

## Report

Create:

```text
codex/reports/egyedi_solver/sgh_q22_sparrow_state_separation_kernel.md
codex/reports/egyedi_solver/sgh_q22_sparrow_state_separation_kernel.verify.log
```

First line must be exactly:

```text
PASS
```

or:

```text
REVISE
```

or:

```text
BLOCKED
```

PASS markers:

```text
SGH-Q22_STATUS: READY_FOR_AUDIT
SPARROW_EXPERIMENTAL_STATUS: TESTABLE
SGH-Q23_STATUS: READY|HOLD
Q19_STATUS: HOLD
Q18B_RECOMMENDATION: REQUIRED|NOT_REQUIRED_NOW|INCONCLUSIVE_NEEDS_BIGGER_FIXTURE
```

Do not mark PASS unless the kernel is real, measured, and adapter-routed.
