# SGH-Q23R3 — Real Sparrow search lifecycle completion

## Purpose

Finish the missing production search lifecycle pieces after Q23R2.

Q23R2 solved the biggest CDE-throughput issue: the single-engine multi-hazard CDE candidate session is active and engine builds dropped sharply. But Q23R2 is still **REVISE** because the actual search lifecycle is not Sparrow-complete and the medium fixture still does not converge.

This task is not an audit. It must implement the missing pieces.

## Current hard blockers

- `medium_10_to_20_items / sparrow_cde / cde` is still `unsupported`.
- medium placed/required is still `0/12`.
- final collision pairs remain nonzero.
- final raw loss remains nonzero.
- default Phase1 routing is still legacy.
- `sparrow_cde` still behaves too much like a single-target loop.
- collision graph refresh is still full snapshot based in the hot path.
- exploration/restart/disruption lifecycle is missing.
- compression/compaction after feasibility is missing.
- LV8 readiness smoke is missing.

## Non-negotiable target

The goal is a functional fixed-sheet adaptation of jagua_rs/Sparrow:

- infeasible internal layouts;
- CDE/exact geometry as truth source;
- collision graph + GLS-driven search;
- multi-target / worker-based movement;
- exploration and compression phases;
- fixed-sheet objective integrated into search;
- final backend-valid output;
- legacy only explicit opt-in.

BBox is not the topic. BBox may remain only as broad-phase/prereject. It must not be positive collision truth, search loss, final validity, or fallback.

## Required implementation

### 1. Production multi-target pass

Replace the single worst-target loop in `sparrow_cde` with a real multi-target / worker pass:

- top-K colliding items and boundary offenders;
- deterministic worker orders;
- worker-local move sequences from a shared snapshot;
- CDE-confirmed accepted moves;
- best worker committed by weighted loss/raw loss/tie-breaker;
- GLS weights preserved correctly;
- no LBF fallback.

### 2. Incremental collision graph

The hot loop must not call full graph snapshot rebuild after every move.

Implement maintained graph updates for moved items:

- moved item boundary edge;
- moved item pair edges;
- total raw/weighted loss;
- per-item incident loss;
- top-K pairs/items/boundary offenders;
- deterministic tie-breaking.

Full rebuild is allowed for initialization and debug consistency only.

### 3. Exploration/restart/disruption

Add fixed-sheet exploration:

- deterministic restarts;
- multiple seed strategies;
- stagnation detection;
- disruption;
- best feasible and best infeasible incumbents;
- complete accounting of all attempts.

### 4. Compression/compaction

After a feasible layout is found, run a fixed-sheet compression pass:

- reduce spread/compactness objective;
- preserve CDE validity;
- reject invalid moves;
- emit diagnostics even if no improvement is possible.

### 5. Medium hard gate

`medium_10_to_20_items` under production `sparrow_cde` must be:

- `status = ok`;
- `placed/required = 12/12`;
- `sparrow_converged = true`;
- final pairs = 0;
- final boundary violations = 0;
- final raw loss = 0;
- no bbox fallback;
- no LBF fallback;
- backend = CDE;
- no timeout.

This cannot be softened.

### 6. Production default flip

Only after the medium gate passes:

- missing `optimizer_pipeline` under `solver_profile=jagua_optimizer_phase1_outer_only` routes to `sparrow_cde`;
- legacy and phase optimizer remain explicit opt-in only.

### 7. LV8 readiness smoke

If `tests/fixtures/nesting_engine/ne2_input_lv8jav.json` exists, add a deterministic LV8 subset smoke. Full 276/276 LV8 acceptance is later, but the subset must run honestly with complete diagnostics and no hidden fallback.

## PASS rule

PASS is allowed only if the medium fixture converges 12/12, default routing is flipped, incremental graph is active, multi-target pass is active, exploration/compression are active, and production `sparrow_cde` has no hidden legacy/bbox/LBF fallback.

Any missing hard gate means `REVISE`.
