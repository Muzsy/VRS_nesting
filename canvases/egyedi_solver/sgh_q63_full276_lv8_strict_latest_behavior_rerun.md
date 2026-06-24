# SGH-Q63 - Full276 LV8 strict latest-behavior rerun

## Goal

The user wants the same Full276 LV8 package rerun again, but this time the solver must expose the
latest sheet-builder / critical-admission behavior honestly, without silently falling back to older
seed/bootstrap paths that mask the role-aware logic in the final renders.

## Scope

- Add an explicit strict latest-behavior mode to the Sparrow BPP sheet-builder path.
- Ensure the strict mode does not silently fall back to the older native constructive seed when the
  critical-aware builder is partial.
- Ensure the strict mode does not random-bootstrap still-unplaced parts at the end of the builder.
- Ensure skeleton-role critical admission cannot be short-circuited by the older generic direct path
  before the role-specific latest logic is attempted.
- Re-run the Full276 LV8 2-sheet / margin 5 / spacing 5 package with the strict mode enabled.
- Save the benchmark artifacts under a new benchmark directory with Q49-shaped outputs.

## Non-goals

- No claim that the strict latest-behavior run will hit 276/276 on 2 sheets.
- No broad solver redesign outside the strict latest-behavior observation path.
- No modification of the Q62 benchmark artifacts.

## Acceptance

- There is an explicit solver runtime switch for strict latest behavior.
- In strict latest mode, the builder seed is not silently replaced by the older native seed.
- In strict latest mode, unresolved parts are not random-bootstrapped inside the builder.
- In strict latest mode, skeleton-role critical admission does not take the older generic direct
  insert shortcut before the role-routed path.
- A new benchmark run is saved under `artifacts/benchmarks/sgh_q63/`.
- The report clearly states whether the strict latest-behavior run still uses 2 sheets, how many
  parts it places, and how it compares to the Q62 masked/current run.
