# SGH-Q24R2 — Native Sparrow core port implementation

## Purpose

Implement the actual `jagua_rs`/`Sparrow` solver logic in our production `sparrow_cde` path.

This task exists because Q24/Q24R1 drifted into search tuning and CDE session reuse. Those changes are useful, but they did not port the original Sparrow lifecycle. The next step is not another timeout benchmark task. The next step is to code the missing solver architecture.

## Non-negotiable target

The goal is the complete and precise adoption of the original jagua_rs/Sparrow logic, adapted only where fixed-sheet nesting truly requires it.

Do not frame the task around bbox removal. Bbox is not the central issue. The central issue is that our solver lifecycle is still not the original Sparrow lifecycle.

Keep this sentence as the task's controlling rule:

> Port the original Sparrow optimizer architecture into the VRS fixed-sheet solver; do not merely tune the current partial approximation.

## Current failure mode

Current Q24R1 status:

- CDE session reuse was improved.
- Medium still passes.
- LV8 rows timeout.
- `sparrow.rs` lifecycle was not substantially rewritten.
- exploration pool is still missing.
- compression rewrite is still missing.
- worker move_items parity is partial.
- search placement parity is partial.
- tracker loss is partial.

This task must address the solver lifecycle itself.

## Mandatory reference reading

Before coding, inspect the local cloned Sparrow repository:

```text
.cache/sparrow
```

Read and map at minimum:

```text
.cache/sparrow/src/optimizer/mod.rs
.cache/sparrow/src/optimizer/separator.rs
.cache/sparrow/src/optimizer/worker.rs
.cache/sparrow/src/optimizer/explore.rs
.cache/sparrow/src/optimizer/compress.rs
.cache/sparrow/src/sample/search.rs
.cache/sparrow/src/quantify/tracker.rs
```

Then inspect current VRS files:

```text
codex/reports/egyedi_solver/sgh_q24r1_native_sparrow_parity_lifecycle.md
rust/vrs_solver/src/optimizer/sparrow.rs
rust/vrs_solver/src/optimizer/search_position.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/collision_severity.rs
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/io.rs
```

## Required implementation

### 1. Replace the current ad-hoc Sparrow loop with a native optimizer orchestration

Implement a VRS fixed-sheet equivalent of Sparrow's optimizer orchestration.

Current problem: `SparrowSeparationKernel::run` contains too much of the whole solver lifecycle in one loop and then does one grid restart plus primitive compression.

Required structure:

```rust
FixedSheetSparrowOptimizer::optimize(...)
    -> build_initial_solution(...)
    -> exploration_phase(...)
    -> compression_phase(...)
    -> final CDE validation
```

This may live in `sparrow.rs`, but preferably split into modules if the file becomes too large:

```text
rust/vrs_solver/src/optimizer/sparrow/mod.rs
rust/vrs_solver/src/optimizer/sparrow/state.rs
rust/vrs_solver/src/optimizer/sparrow/separator.rs
rust/vrs_solver/src/optimizer/sparrow/worker.rs
rust/vrs_solver/src/optimizer/sparrow/explore.rs
rust/vrs_solver/src/optimizer/sparrow/compress.rs
rust/vrs_solver/src/optimizer/sparrow/search.rs
```

Do not create empty wrapper modules. They must contain real logic.

### 2. Implement Sparrow separator parity

Port the structure of Sparrow Algorithm 9 into fixed-sheet form.

Required behaviour:

```text
min_loss_solution = current solution/tracker snapshot
while strike_count < strike_limit and not timeout:
    no_improvement_count = 0
    initial_strike_loss = current raw loss
    while no_improvement_count < iter_no_improvement_limit:
        move_items_multi()
        if raw_loss == 0: return feasible
        if raw_loss improved: save incumbent and maybe reset no_improvement_count
        else: no_improvement_count += 1
        update GLS weights
    update strike_count based on substantial improvement
    rollback to min_loss_solution, preserving GLS weights
return best feasible or best infeasible
```

Hard requirements:

- must preserve and restore tracker state correctly;
- GLS weights must survive rollbacks the same way Sparrow keeps search memory;
- weighted loss must not increase within accepted worker commits unless explicitly justified and diagnosed;
- the old one-shot grid restart cannot remain the main separation logic.

### 3. Implement real `move_items_multi` and worker `move_items`

Port the structure of Sparrow Algorithm 10 and Algorithm 5.

Required behaviour:

- workers are created from the master solution/tracker;
- each worker loads the master snapshot;
- each worker gathers **all currently colliding items**, not just a fixed top-K subset;
- each worker processes those items in a unique deterministic/randomized order;
- for each still-colliding item, worker calls search placement;
- worker moves the item only if the candidate improves weighted loss according to the evaluator;
- after all workers finish, master loads the best worker's solution/tracker.

Sequential workers are acceptable for now if parallelism is too much, but the state model must match the original worker-master model.

Not acceptable:

- one best item per iteration;
- top-K only as the whole algorithm;
- moving at most one item per worker pass;
- using the worker loop only for diagnostics.

### 4. Implement Sparrow search placement parity

Current `search_position_for_target` can remain the underlying function only if it is upgraded/used as Sparrow's `search_placement` equivalent.

Required behaviour:

- container-wide sampling;
- focused/local sampling around current placement;
- BestSamples retention of top candidates;
- pre-refinement coordinate descent;
- final finer coordinate descent;
- rotation refinement for continuous rotation policy;
- deterministic worker-specific RNG or deterministic pseudo-randomness;
- evaluator is CDE-backed and returns weighted separation loss.

Do not leave production search budgets in a toy state. Do not solve timeouts by disabling search depth. If search cost is too high, implement active-set/CDE query reduction as support.

### 5. Implement exploration phase parity

Port Sparrow Algorithm 12 conceptually, adapted to fixed-sheet nesting.

Required behaviour:

- maintain a bounded infeasible solution pool sorted by loss;
- insert local-best infeasible solutions into the pool;
- restore from the pool with bias toward better infeasible solutions;
- disrupt restored solutions using a large-item disruption strategy;
- run repeated restore/disrupt/separate attempts under a budget;
- preserve best feasible and best infeasible incumbents;
- do not use one grid-spread restart as the whole exploration phase.

Fixed-sheet disruption options:

- swap two large items' transforms;
- relocate one or two large items to different sheet regions;
- split a dense cluster;
- redistribute a large offending item to another sheet if allowed.

The implementation must include at least one real large-item disruption strategy based on geometry/area, not a random no-op.

### 6. Implement compression phase parity

Port Sparrow Algorithm 13 conceptually, adapted to fixed-sheet nesting.

Required behaviour:

```text
start from best feasible incumbent
repeat under compression budget:
    save incumbent
    apply compact/shrink pressure
    call separator to restore feasibility
    if feasible and objective improved: accept as incumbent
    else: rollback to incumbent
return best compressed feasible layout
```

Fixed-sheet pressure may be:

- reduce occupied extent toward lower-left / sheet origin;
- shrink allowed region envelope;
- reduce right/top spread;
- reduce sheet usage pressure for multi-sheet layouts;
- compact clusters while keeping CDE validity via separator.

Not acceptable:

- only trying `x - 1mm` and `y - 1mm` per item;
- compression without calling separator;
- accepting invalid compressed layouts;
- reporting compression as done when it is only a local nudge loop.

### 7. Implement tracker/loss parity as part of the lifecycle

The tracker must support the new lifecycle.

Required behaviour:

- collision graph/tracker state can be saved/restored;
- item move updates tracker incrementally;
- GLS weights survive rollback appropriately;
- CDE/separation-based loss is used by the production evaluator;
- tracker and layout consistency can be debug-asserted;
- boundary violations and pair collisions are represented distinctly.

Do not turn this into a bbox discussion. The requirement is positive: the tracker must behave like Sparrow's collision tracker, adapted to VRS geometry and CDE.

### 8. Active-set/CDE reduction is support, not the main task

The LV8 timeout shows that query cost matters. However, this task is not allowed to become only a CDE optimization task.

Implement active-set/session improvements only where needed to make the native Sparrow lifecycle usable:

- target-search active hazard set;
- region-specific CDE sessions;
- spatial-grid/prereject for hazard selection;
- full final CDE validation over all hazards before emitting success.

Active-set must never replace the solver lifecycle work.

### 9. Minimal verification only after coding

This task is code-first. Do not spend the run mainly on benchmark scripts.

Required minimum checks after implementation:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q24r2_native_sparrow_core_port.py
```

Create the smoke script only after the implementation. It should verify structure and a small functional run; it must not become the task's main work.

Do not make full LV8 convergence a PASS gate in this task. LV8 can remain measured honestly, but the purpose here is to port the algorithmic structure. Full LV8 quality gates come after the native lifecycle exists.

## PASS / REVISE rules

### PASS requires all of the following

- real Rust implementation changes in `optimizer/sparrow.rs` or new `optimizer/sparrow/*` modules;
- separator strike/no-improvement loop implemented;
- worker-master `move_items_multi` implemented;
- worker `move_items` processes all currently colliding items;
- search placement has container sampling, focused sampling, BestSamples, and two-stage coordinate descent active;
- exploration pool + biased restore + real large-item disruption implemented;
- compression restore/pressure/separate/accept loop implemented;
- tracker save/restore/update supports the lifecycle;
- CDE session/active-set work, if done, supports the lifecycle rather than replacing it;
- minimal tests/smoke pass or exact compile blockers are documented with code evidence.

### Automatic REVISE if any of these happens

- only reports/scripts/checklists are changed;
- only `cde_adapter.rs` / `cde_observability.rs` are meaningfully changed;
- `sparrow.rs` lifecycle remains the current one-loop + grid restart + primitive compression shape;
- exploration pool is still reported as `NOT_DONE`, `PARTIAL`, or equivalent;
- compression rewrite is still reported as `NOT_DONE`, `PARTIAL`, or equivalent;
- worker move_items still moves only one/top-K item instead of all currently colliding items per worker pass;
- search depth is disabled to make tests pass;
- the implementation spends the run mainly creating benchmark rows instead of coding the native lifecycle.

## Required report

Write:

```text
codex/reports/egyedi_solver/sgh_q24r2_native_sparrow_core_port.md
codex/reports/egyedi_solver/sgh_q24r2_native_sparrow_core_port.verify.log
```

Report must include:

- top line: `PASS` or `REVISE`;
- list of original Sparrow files inspected in `.cache/sparrow`;
- mapping from original Sparrow function/module to implemented VRS function/module;
- exact Rust files changed;
- what lifecycle structures were implemented;
- what remains for later LV8 quality/performance work;
- tests actually run.

Do not claim PASS unless the lifecycle is actually ported.
