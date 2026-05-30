# SGH-Q22 — Real SparrowState + separation kernel with measurement

## Intent

This is not a small hygiene task and not another proxy patch. The target is a testable, explicit, **jagua_rs/Sparrow-style solver mode** inside the current Rust solver.

Sparrow's core idea is not “try more greedy candidates”. It decomposes nesting into feasibility problems where collisions are deliberately allowed in intermediate states and then gradually resolved. The kernel must therefore support an infeasible layout lifecycle, collision graph, GLS-weighted collision selection, sampled transform search, coordinate-descent refinement, rollback, and final exact/CDE validation.

Q20/Q20R/Q21R1 prepared the missing parts:

```text
Q20      continuous rotation refinement
Q20R/R1  search_position + top-k coordinate descent
Q21/R1   backend-oracle collision severity/evaluate_transform
```

Q22 must now wire these into an actual Sparrow-mode kernel.

## Hard principle

Do not implement a minimally working solver. Implement the first serious, measurable slice of the intended full jagua_rs/Sparrow architecture.

If a requirement cannot be implemented and tested honestly, mark the report `REVISE`, not `PASS`.

## Dependency gate

Required reports:

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

If missing, stop with `BLOCKED` report and no production code edits.

## Current repo reality to build on

The repo already has:

```text
rust/vrs_solver/src/optimizer/search_position.rs
rust/vrs_solver/src/optimizer/collision_severity.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/phase.rs
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/adapter.rs
```

Important existing capabilities:

- `search_position_for_target(...)` with deterministic global/focused sampling and top-k coordinate descent.
- `collision_severity::evaluate_transform_loss(...)` with backend-confirmed CDE/Jagua collision existence and improved multi-direction probe severity.
- `VrsCollisionTracker` with pair/boundary GLS weights and `restore_but_keep_weights`.
- `VrsSeparator` with multi-worker candidate attempts.
- CDE final commit gate and diagnostics.

Important current limitation:

The solver still does not have an explicit Sparrow-state pipeline. Existing separator logic can resolve collisions, but it is not exposed as a standalone `sparrow_experimental` solver lifecycle with intentional infeasible layout state, collision graph snapshots, separation-loop metrics, and final feasibility gate.

## Scope

### 1. Add an explicit `sparrow_experimental` optimizer pipeline

Extend `OptimizerPipelineKind`:

```rust
pub enum OptimizerPipelineKind {
    LegacyMultisheet,
    PhaseOptimizer,
    SparrowExperimental,
}
```

JSON value:

```json
"optimizer_pipeline": "sparrow_experimental"
```

Adapter routing must call the new Sparrow kernel only when this explicit value is selected. Existing `legacy_multisheet` and `phase_optimizer` behavior must not regress.

### 2. Add `optimizer/sparrow.rs`

Create a new module:

```text
rust/vrs_solver/src/optimizer/sparrow.rs
```

Export it in:

```text
rust/vrs_solver/src/optimizer/mod.rs
```

Minimum public structs:

```rust
pub struct SparrowConfig { ... }
pub struct SparrowDiagnostics { ... }
pub struct SparrowState { ... }
pub struct CollisionGraphSnapshot { ... }
pub struct SparrowSeparationKernel { ... }
pub struct SparrowResult { ... }
```

Names can differ if repo style demands it, but the concepts must be present and documented.

### 3. `SparrowState`: explicit infeasible lifecycle

`SparrowState` must wrap a `WorkingLayout`, but it is not just a type alias.

It must track at least:

```text
current layout
current raw loss
current weighted loss
best feasible layout, if any
best infeasible layout
best infeasible raw loss
best infeasible weighted loss
current collision graph snapshot
GLS weights / tracker state
iteration count
accepted/rejected/rollback counts
seed/run id
```

Intermediate state is allowed to be infeasible. Final returned placements are not.

### 4. Intentional infeasible seed layout

For `sparrow_experimental`, do not rely only on LBF building a mostly-valid layout.

Add a deterministic seed builder, e.g.:

```rust
build_sparrow_seed_layout(...)
```

Requirements:

- Include every instance that can fit at least one sheet under its rotation policy.
- Items that cannot fit any sheet are marked `PART_NEVER_FITS_STOCK`.
- Seed placements may overlap.
- Seed must be deterministic for same input seed.
- Respect part rotation policy.
- Prefer first/cheapest sheet or deterministic sheet choice; document the rule.
- No holes in main solver input per Q15 contract.

The point is to create a full infeasible state that the separation kernel can repair, not to silently skip difficult parts as unplaced just because LBF had no clear candidate.

### 5. CollisionGraphSnapshot

Build explicit graph snapshots from `VrsCollisionTracker` / severity data.

Minimum fields:

```text
colliding_items_count
colliding_pairs_count
boundary_violations_count
total_raw_loss
total_weighted_loss
worst_item_index
worst_item_instance_id
worst_pair_instance_ids
worst_boundary_instance_id
max_pair_weight
max_boundary_weight
```

Optional but preferred:

```text
top_colliding_pairs: Vec<(instance_a, instance_b, severity, weight, weighted_loss)>
top_boundary_violations: Vec<(instance_id, severity, weight, weighted_loss)>
```

The snapshot must be deterministic and diagnosable.

### 6. SparrowSeparationKernel

Implement the actual loop instead of merely calling `PhaseOptimizer` and relabeling it.

Required lifecycle:

```text
initialize SparrowState from seed layout
build/update collision graph
while budget remains:
    if no collision and no boundary violation:
        validate final layout with active backend
        store best feasible
        optionally run compactness/compression attempt if configured
        return feasible result

    choose target item from collision graph / weighted loss
    call search_position_for_target(...)
    evaluate candidate with collision_severity / active backend
    apply candidate tentatively
    update tracker/collision graph
    if improved raw or weighted loss:
        commit
    else:
        rollback geometry but keep GLS weights policy-consistently
        update GLS weights / strike count

    periodically update GLS weights even on stagnation
    keep best infeasible incumbent
return best feasible if found else best infeasible diagnostics + unsupported/partial according to contract
```

You may reuse `VrsSeparator`, `VrsCollisionTracker`, `SearchPositionStats`, and `CollisionSeverityStats`, but do not hide the entire solver behind a black-box `VrsSeparator::run` call with no explicit Sparrow state/graph/metrics. The new kernel must expose its own state and diagnostics.

### 7. Search/evaluation integration

Inside Sparrow mode:

- Primary relocation must be `search_position_for_target(...)`.
- `generate_candidates_with_sheets(...)` must not be the primary path.
- If legacy LBF fallback remains available, it must be explicitly counted and disabled by default in `sparrow_experimental`.
- Under CDE/Jagua, no bbox fallback may be used as collision source-of-truth.
- `bbox_fallback_queries == 0` must remain true for CDE mode.

### 8. GLS lifecycle

The solver must have explicit GLS behavior:

- Pair and boundary weights survive rollback.
- Geometry snapshot restore must not reset weights.
- Weights update on repeated/stagnating collisions.
- Diagnostics must expose weight-update counts and max weights.

This is critical. Sparrow is not just random relocation; the search must be guided.

### 9. Final commit contract

For `sparrow_experimental`:

- Final successful output must pass `WorkingLayout::validate_and_commit_with_backend` with the selected backend.
- If CDE is selected, final diagnostics must report `backend_used = "cde_adapter"` and `bbox_fallback_queries = 0`.
- If no feasible layout is found, output must be honest:
  - either `status = "partial"` with explicit diagnostics and no invalid placements committed as valid, or
  - `status = "unsupported"` / `REVISE` if current output contract cannot represent best-infeasible safely.

Do not emit colliding placements as successful final placements.

### 10. Diagnostics output

Extend `OptimizerDiagnosticsOutput` or add a nested/flat compatible set of optional fields for Sparrow mode.

Minimum fields:

```text
pipeline_used = "sparrow_experimental"
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

Names can follow repo style, but all these facts must be surfaced or documented as equivalent.

### 11. Measurement, not just unit tests

Create a dedicated measurement/smoke script:

```text
scripts/smoke_sgh_q22_sparrow_kernel.py
```

It must run deterministic fixtures and print a compact measurement table.

Minimum fixtures:

1. `overlap_two_rects`: two overlapping rectangles, one sheet, CDE or Jagua exact backend if available.
2. `boundary_recovery`: one item initially outside/near boundary and must be pulled inside.
3. `three_item_collision_chain`: multiple pair collisions requiring more than one move.
4. `continuous_rotation_rescue`: feasible only with non-orthogonal/continuous rotation or materially better with it.
5. `medium_10_to_20_items`: deterministic small stress fixture, not LV8, used for metrics.

Each fixture must report:

```text
status
seed
runtime_ms
initial_raw_loss
final_raw_loss
loss_reduction_ratio
iterations
moves_attempted
moves_accepted
rollbacks
gls_weight_updates
collision_pairs_initial
collision_pairs_final
boundary_violations_initial
boundary_violations_final
search_position_calls
cde_total_queries / backend query count if CDE
bbox_fallback_queries
feasible_final
```

Acceptance for smoke:

- At least the first 3 fixtures must converge to feasible final layout.
- CDE/Jagua fixture must have no bbox fallback.
- Same seed run twice must produce identical placements and identical deterministic counters.
- Runtime/timing values are not exact-compared.

### 12. Optional benchmark script for larger local run

Add:

```text
scripts/bench_sgh_q22_sparrow_kernel.py
```

This may run longer and should be suitable for Hermes/local machine.

Matrix suggestion:

```text
seeds: 1, 2, 3
backends: bbox, cde if available
fixtures: medium_10_to_20_items, synthetic_30_items
pipelines: phase_optimizer vs sparrow_experimental
```

Output:

```text
codex/reports/egyedi_solver/sgh_q22_sparrow_state_separation_kernel_measurements.json
codex/reports/egyedi_solver/sgh_q22_sparrow_state_separation_kernel_measurements.md
```

The benchmark does not need to beat all previous results in Q22, but it must give real evidence about feasibility rate, runtime, query counts, and loss reduction.

## Required tests

Add targeted tests for:

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

If names differ, map them in the report.

## Verification commands

Minimum:

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

Do not fake benchmark success. If the bench exposes poor performance, report it honestly and still mark PASS only if the kernel is correct, measured, and diagnosable.

## PASS criteria

PASS requires:

1. Explicit `sparrow_experimental` pipeline exists and routes from adapter.
2. `SparrowState` exists and permits infeasible intermediate states.
3. Explicit deterministic `CollisionGraphSnapshot` exists.
4. `SparrowSeparationKernel` implements a real loop with target selection, search_position, evaluation, commit/rollback, and GLS weight lifecycle.
5. Final feasible layout is backend-validated before successful output.
6. CDE/Jagua mode has no silent bbox fallback.
7. Smoke fixtures prove real convergence on at least overlap/boundary/chain cases.
8. Measurement table/report exists.
9. Same-seed determinism is tested.
10. Report is honest about remaining limitations.

## Expected known limitations after Q22

Allowed limitations if documented:

```text
not yet LV8 acceptance gate
not yet full multi-sheet minimization objective
not yet full Sparrow strip-shrink Algorithm 12/13 parity
not yet true overlap-area metric
CDE session/cache still optional unless measurements prove bottleneck
```

Not allowed limitations:

```text
sparrow_experimental is only phase_optimizer relabeled
no explicit infeasible state
no collision graph snapshot
no separation loop
no measurement script
CDE mode uses bbox fallback silently
invalid colliding layout emitted as successful final output
```

## Report markers

Create:

```text
codex/reports/egyedi_solver/sgh_q22_sparrow_state_separation_kernel.md
codex/reports/egyedi_solver/sgh_q22_sparrow_state_separation_kernel.verify.log
```

First line must be exactly one of:

```text
PASS
REVISE
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

Q19 remains HOLD unless a later task turns the measured kernel into a realistic LV8 acceptance gate.
