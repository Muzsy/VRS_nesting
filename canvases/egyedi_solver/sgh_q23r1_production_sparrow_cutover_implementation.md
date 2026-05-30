# SGH-Q23R1 — Production Sparrow cutover implementation

## Mission

This is the execution step after Q23 returned `REVISE`.

The goal is not another audit. The goal is to finish the production cutover from the old solver path to a real jagua_rs/Sparrow-style fixed-sheet solver.

The production path must become `sparrow_cde` or an equivalently explicit production route. Old solver paths may remain only as legacy/debug comparisons.

## Why R1 exists

Q23 established a partial `sparrow_cde` path, but it did not complete full parity or scale:

```text
medium_10_to_20_items / sparrow_cde:
  status: unsupported
  placed_count: 0/12
  runtime_ms: ~25017.8
  cde_total_queries: 11236
  cde_engine_builds: 7650
```

That is not a production Sparrow solver. R1 must implement the missing structural pieces.

## Implementation target

The implementation must align the VRS production solver with the local `.cache/sparrow` reference:

```text
infeasible-state feasibility solving
collision graph with incremental updates
GLS/pair-weight memory
search_position relocation/refinement
coordinate descent
separation lifecycle
multi-target pass over colliding items
exploration/compression lifecycle adapted to fixed sheet
solve-scoped CDE/Jagua session/cache
fixed-sheet objective and final validation
legacy quarantine
```

## Critical blocker to solve

The per-call CDE path must be replaced or hidden behind a solve-scoped cache/session. Rebuilding `CDEngine` thousands of times on a medium fixture is incompatible with Sparrow-style local search.

R1 must implement:

```text
prepared geometry cache
transformed placement cache
pair decision cache
boundary decision cache
dirty invalidation on move
active-set pair filtering
incremental graph update
session/cache metrics
```

## Production cutover

Normal production solving must route to `sparrow_cde`. Missing/implicit production config cannot keep silently using the old solver. If global default compatibility must be preserved for external contracts, all normal production run configs must be explicitly wired to `sparrow_cde`, and the compatibility default must be documented as temporary/non-production.

## PASS definition

PASS means:

```text
medium CDE fixture converges
production route is Sparrow/CDE
legacy is explicit opt-in only
CDE/Jagua is geometry truth
stateful session/cache or equivalent active
incremental graph active
no bbox/LBF/PhaseOptimizer fallback in production Sparrow
smoke + benchmark + cargo gates pass
```

Anything less is `REVISE`, but R1 must still implement as much of the cutover as possible before reporting REVISE.
