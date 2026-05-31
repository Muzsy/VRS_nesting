# SGH-Q24R5 — Architectural native Sparrow cutover

## One-line goal

Cut production `sparrow_cde` away from the old VRS core and make a native Sparrow `Problem → Optimizer → Solution → CollisionTracker` model the only production truth, with compression still excluded.

## Why this task exists

Q24R3 made the lifecycle look Sparrow-like. Q24R4 attempted the model cutover but honestly reported `REVISE`: the solver still runs through `WorkingLayout`, `crate::io::Placement` as internal placement state, and `VrsCollisionTracker`.

That is the wrong foundation. As long as the old core remains inside production `sparrow_cde`, future coding agents can keep building on it. This task removes that escape path.

## Non-negotiable rule

Production `sparrow_cde` must not be a VRS solver with Sparrow-shaped function names. It must be a Sparrow-native solver with only an input/output compatibility boundary.

Allowed:

```text
SolverInput -> SparrowProblem -> SparrowOptimizer -> SparrowSolution -> SolverOutput projection
```

Forbidden:

```text
SolverInput -> WorkingLayout -> VrsCollisionTracker -> Sparrow-shaped wrapper -> WorkingLayout commit
```

## Scope boundary

Compression is not the target. Do not optimize compression, do not use compression to pass acceptance, and do not turn the task into a benchmark campaign.

## Expected audit result after this task

```text
Q24R5 PASS means the production solver core has been architecturally cut over.
The remaining work after Q24R5 should be tracker/search quality hardening on the native model, not removing old VRS core dependencies.
```
