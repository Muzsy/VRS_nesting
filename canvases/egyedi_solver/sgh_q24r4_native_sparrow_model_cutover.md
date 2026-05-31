# SGH-Q24R4 — Native Sparrow model cutover

## One-line goal

Replace the old VRS solver-core model inside production `sparrow_cde` with a real Sparrow-native model: `Problem`, `SPInstance`, `Layout`, `Solution`, and `CollisionTracker`.

## Why this task exists

Q24R3 made the lifecycle look Sparrow-like and got the medium CDE gate passing without compression. That is a real milestone, but the implementation still runs through a VRS-shaped core: `WorkingLayout`, `Placement`, and `VrsCollisionTracker` are still the truth model under the production solver.

That is not a final Sparrow port. It is a hybrid. Hybrids invite future coding agents to keep building on the old system because it is cheaper than doing the hard cutover. This task closes that escape path.

## Non-negotiable rule

The production `sparrow_cde` path must run on native Sparrow concepts, not on the old VRS layout/tracker model.

Allowed boundary:

```text
VRS JSON/API structures -> native SparrowProblem -> native Sparrow optimizer -> VRS output projection
```

Forbidden production core:

```text
WorkingLayout -> VrsCollisionTracker -> adapter CDE calls -> WorkingLayout commit
```

## Compression status

Compression remains out of scope. Do not harden it. Do not use it to pass acceptance. The target is the complete Sparrow lifecycle model and separation/search/tracker behavior, excluding compression.

## Expected outcome

After this task, audit should be able to say:

```text
The solver is no longer a VRS solver with Sparrow-shaped functions.
It is now a Sparrow-native solver with a VRS input/output boundary.
```
