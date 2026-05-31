# SGH-Q24R2 — Native Sparrow core port implementation

You are working in the VRS_nesting repository.

This is a **coding-first native Sparrow port task**. Do not drift into benchmark work, report work, or isolated CDE optimization. The only acceptable main outcome is a real implementation of the original jagua_rs/Sparrow solver lifecycle inside the VRS fixed-sheet `sparrow_cde` path.

## Controlling rule

Port the original Sparrow optimizer architecture into the VRS fixed-sheet solver. Do not merely tune the current partial approximation.

This task is not about proving full LV8 performance right now. It is about coding the missing native lifecycle.

## Why this task exists

Q24R1 was useful but wrong-focused relative to the main goal. It improved per-target CDE candidate-session reuse, but did not substantially rewrite:

- `rust/vrs_solver/src/optimizer/sparrow.rs`
- exploration pool
- biased restore
- large-item disruption
- compression phase
- worker move_items parity
- full search placement parity

Therefore Q24R1 remained `REVISE`. Q24R2 must implement the missing solver architecture, not another CDE-only optimization.

## Read first

Read the current VRS state:

```text
codex/reports/egyedi_solver/sgh_q24r1_native_sparrow_parity_lifecycle.md
codex/reports/egyedi_solver/sgh_q24r1_native_sparrow_parity_lifecycle_measurements.md
rust/vrs_solver/src/optimizer/sparrow.rs
rust/vrs_solver/src/optimizer/search_position.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/collision_severity.rs
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/io.rs
```

Then read the local original Sparrow clone:

```text
.cache/sparrow/src/optimizer/mod.rs
.cache/sparrow/src/optimizer/separator.rs
.cache/sparrow/src/optimizer/worker.rs
.cache/sparrow/src/optimizer/explore.rs
.cache/sparrow/src/optimizer/compress.rs
.cache/sparrow/src/sample/search.rs
.cache/sparrow/src/quantify/tracker.rs
```

`.cache/sparrow` is gitignored but present locally. Use it. If it is absent, mark that as a blocker and use any checked-in reference docs, but do not pretend parity without reading the reference.

## Scope discipline

Do not spend the main effort on:

- LV8 benchmark scripts;
- timeout tuning;
- new measurement tables;
- CDE session reuse only;
- diagnostics only;
- another report-only audit.

Benchmarks are allowed only after the code is implemented and only as minimal confirmation. Full LV8 convergence is not a required PASS gate in this task; native lifecycle implementation is.

## Required implementation

### 1. Native optimizer orchestration

Replace the current monolithic/partial `SparrowSeparationKernel::run` lifecycle with a VRS fixed-sheet equivalent of Sparrow Algorithm 11.

Implement an explicit orchestration like:

```rust
FixedSheetSparrowOptimizer::optimize(...)
    -> build_initial_solution(...)
    -> exploration_phase(...)
    -> compression_phase(...)
    -> final CDE validation
```

You may keep this in `optimizer/sparrow.rs` if necessary, but a split module tree is preferred if the file becomes too large:

```text
rust/vrs_solver/src/optimizer/sparrow/mod.rs
rust/vrs_solver/src/optimizer/sparrow/state.rs
rust/vrs_solver/src/optimizer/sparrow/separator.rs
rust/vrs_solver/src/optimizer/sparrow/worker.rs
rust/vrs_solver/src/optimizer/sparrow/explore.rs
rust/vrs_solver/src/optimizer/sparrow/compress.rs
rust/vrs_solver/src/optimizer/sparrow/search.rs
```

Do not create empty wrappers. New modules must contain real implementation.

### 2. Separator parity: strike/no-improvement loop

Implement a fixed-sheet adaptation of original Sparrow `Separator::separate`.

Required logic:

```text
min_loss_solution = current solution + tracker snapshot
min_loss = tracker total raw loss
strike_count = 0
while strike_count < strike_limit and not budget exhausted:
    no_improvement_count = 0
    initial_strike_loss = current raw loss
    while no_improvement_count < iter_no_improvement_limit:
        move_items_multi()
        if raw_loss == 0:
            save feasible incumbent
            return feasible
        else if raw_loss improved:
            save min_loss_solution
            maybe reset no_improvement_count on substantial improvement
        else:
            no_improvement_count += 1
        update GLS weights
    update strike_count based on substantial improvement
    rollback to min_loss_solution, preserving GLS weights
return best feasible or least-infeasible state
```

Hard requirements:

- rollback must restore layout and collision tracker consistently;
- GLS weights must preserve search memory across rollback;
- separation returns the least-infeasible solution if feasibility is not reached;
- the old one-shot grid restart must not be the main separation mechanism.

### 3. Worker-master `move_items_multi` parity

Implement the original worker-master model.

Required logic:

```text
master_solution = current solution snapshot
for each worker:
    worker.load(master_solution, master_tracker)
    worker.move_items()
choose worker with lowest weighted loss
master.restore(best_worker.solution, best_worker.tracker)
```

Parallelism is optional for now. Sequential deterministic workers are acceptable. The state model must still match Sparrow.

### 4. Worker `move_items` parity

Implement a worker method that processes all currently colliding items.

Required logic:

```text
candidates = all placed items with tracker.get_loss(item) > 0
shuffle/order candidates with worker-specific deterministic RNG
for item in candidates:
    if item is still colliding:
        evaluator = separation evaluator for this item
        best_sample = search_placement(layout, item, evaluator)
        move item to best_sample
        tracker.register_item_move(...)
```

Not acceptable:

- one worst item only;
- top-K only as the whole algorithm;
- at most one item moved per worker pass;
- worker loop that only collects diagnostics.

### 5. Search placement parity

Upgrade or wrap `search_position_for_target` so production search matches the original Sparrow search structure.

Required components:

- container-wide sampling;
- focused/current-region sampling;
- BestSamples/top sample retention;
- pre-refinement coordinate descent;
- final finer coordinate descent;
- continuous rotation refinement when policy allows it;
- worker-specific deterministic RNG/order;
- CDE-backed weighted separation evaluator.

Do not disable search depth to avoid timeouts. If deeper search is too expensive, add active-set/session support as a helper, not as a replacement for search parity.

### 6. Exploration phase parity

Implement original Sparrow exploration semantics adapted to fixed sheets.

Required components:

- bounded infeasible solution pool sorted by loss;
- insertion of least-infeasible local solutions;
- biased selection from the pool toward better solutions;
- restore selected infeasible solution;
- real disruption before retrying separation;
- repeated restore/disrupt/separate attempts under budget;
- best feasible incumbent tracking;
- best infeasible incumbent tracking.

Required disruption:

Implement at least one real large-item disruption based on geometry/area. Acceptable fixed-sheet adaptations:

- swap transforms of two large offending items;
- relocate one large offending item to a different sheet region;
- split a dense cluster by moving a large item away from the cluster;
- move a large offending item to another sheet if the current problem allows multiple sheets.

Not acceptable:

- one grid-spread restart as the entire exploration phase;
- fake disruption that does not change the layout;
- marking exploration pool as complete without pool insert/restore/disrupt counters and code.

### 7. Compression phase parity

Implement original Sparrow compression semantics adapted to fixed sheets.

Required lifecycle:

```text
incumbent = best feasible exploration solution
while compression budget remains:
    save incumbent
    apply compact/shrink pressure
    run separator to restore feasibility
    if feasible and fixed-sheet objective improved:
        accept as new incumbent
    else:
        rollback to incumbent
return incumbent
```

Fixed-sheet pressure options:

- shrink occupied envelope;
- reduce right/top extent;
- compact toward origin or sheet anchor;
- increase pressure to use fewer sheet regions;
- apply sheet-count pressure in multi-sheet cases.

Not acceptable:

- only `x - 1mm` / `y - 1mm` nudge loop;
- compression that never calls separator;
- accepting invalid compressed layouts;
- reporting compression complete without restore/pressure/separate/accept counters and code.

### 8. Tracker/loss support for the lifecycle

Ensure the tracker supports the new lifecycle:

- save/restore tracker snapshots;
- register item moves incrementally;
- preserve GLS weights across rollback where Sparrow does;
- separate pair collisions from boundary violations;
- provide raw and weighted loss;
- debug-assert layout/tracker consistency when feasible;
- integrate CDE-backed evaluator for production `sparrow_cde`.

Do not make this a bbox discussion. The positive requirement is Sparrow-style tracker behavior.

### 9. CDE active-set/session work only as support

If LV8-sized shapes make the new native lifecycle unusably slow during small checks, add supportive active-set/CDE work:

- target-search active hazard set;
- region-specific CDE session cache;
- spatial-grid hazard selection;
- full final CDE validation before success.

But do not let this become the main task. If the only meaningful code change is CDE optimization, this task is REVISE.

## Minimal verification

After coding, run only the checks needed to prove the new code compiles and the lifecycle can execute on small inputs:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q24r2_native_sparrow_core_port.py
```

The smoke script should be small and structural/functional. It should not become a full LV8 benchmark project.

Full LV8 gates are intentionally not the central PASS gate for Q24R2. They come after the native lifecycle is implemented.

## Required report

Write:

```text
codex/reports/egyedi_solver/sgh_q24r2_native_sparrow_core_port.md
codex/reports/egyedi_solver/sgh_q24r2_native_sparrow_core_port.verify.log
```

Top line must be `PASS` or `REVISE`.

The report must include:

- original Sparrow files inspected from `.cache/sparrow`;
- direct mapping table from original Sparrow modules/functions to VRS modules/functions;
- exact Rust files changed;
- whether the implementation changed real solver lifecycle code;
- whether exploration pool is actually implemented;
- whether compression restore/pressure/separate/accept is actually implemented;
- whether worker move_items processes all colliding items;
- whether search placement parity components are active;
- minimal tests run.

## PASS requirements

PASS is allowed only if all are true:

1. Real Rust lifecycle code changed in `optimizer/sparrow.rs` or new `optimizer/sparrow/*` modules.
2. Native optimizer orchestration exists: initial solution → exploration → compression → final validation.
3. Separator strike/no-improvement loop exists.
4. Worker-master `move_items_multi` exists.
5. Worker `move_items` processes all currently colliding items.
6. Search placement includes container sampling, focused sampling, BestSamples, and two-stage coordinate descent.
7. Exploration pool + biased restore + real large-item disruption exist.
8. Compression restore/pressure/separate/accept loop exists.
9. Tracker save/restore/update supports the lifecycle.
10. Minimal compile/smoke evidence is written.

## Automatic REVISE conditions

Mark REVISE if any of these is true:

- only reports/scripts/checklists changed;
- only `cde_adapter.rs` / `cde_observability.rs` changed meaningfully;
- `sparrow.rs` remains the current one-loop + one grid restart + primitive compression lifecycle;
- exploration pool is still missing or only diagnosed;
- compression rewrite is still missing or only diagnosed;
- worker `move_items` still moves only one/top-K item per pass;
- search depth is disabled to avoid timeouts;
- most work went into LV8 benchmark rows rather than code;
- `.cache/sparrow` was not inspected and no blocker was reported.
