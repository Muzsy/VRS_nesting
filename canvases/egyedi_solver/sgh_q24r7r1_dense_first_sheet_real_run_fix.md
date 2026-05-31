# SGH-Q24R7-R1 — Dense first-sheet real-run fix

## One-line goal

Fix Q24R7 so the LV8 first-sheet 191-instance probe is a real native Sparrow CDE search, not a guarded partial shortcut.

## Why this exists

Q24R7 reported `PASS`, but the most important new test did not actually exercise dense search. The code has a large single-sheet guard:

```rust
if instances.len() >= 100 && sheets.len() == 1 {
    return SparrowSolveResult { feasible: false, ... };
}
```

That means the first-sheet reference probe did not validate sampler/evaluator scaling. It only proved that a seed projection can be emitted as `partial`.

## Correct repair direction

Do **not** move on to Q24R8. Repair Q24R7 first.

The 191-instance single-sheet LV8 input must go through:

```text
SparrowProblem
-> SparrowOptimizer::solve
-> native constructive seed
-> SparrowCollisionTracker
-> exploration/separation
-> worker competition
-> native_search_placement / CandidateEvaluator
-> CDE final validation
-> honest output projection
```

## What is allowed

A `partial` dense result is allowed if the solver cannot solve the reference sheet yet. But it must be a real partial after bounded search, not a shortcut.

Allowed result examples:

```text
status=partial
required=191
valid_placed=K
unresolved/colliding=N
final_pairs > 0 OR boundary > 0
runtime real
search calls > 0
worker candidates > 0
CDE queries > 0
```

## What is forbidden

- Early return for `instances >= 100 && sheets.len() == 1` in production `sparrow_cde`.
- Marker values like `sparrow_collision_graph_final_pairs = 1` used to fake a blocked dense result.
- `0.0s` dense runtime.
- Reporting `191/191 placed` as success when the layout is not CDE-valid.
- Compression.
- Legacy / LBF / bbox truth fallback.
- Reintroducing `WorkingLayout`, `VrsCollisionTracker`, `SparrowSeparationKernel`, `PhaseOptimizer`, or `MultiSheetManager` into production `optimizer/sparrow`.

## Expected outcome

After this repair:

```text
Architecture: native Sparrow preserved
Dense guard: removed/quarantined outside production
191 probe: real run
Result: PASS if solved, PARTIAL if not solved but honestly diagnosed
Next step: only then continue sampler/evaluator or dense LV8 scaling work
```
