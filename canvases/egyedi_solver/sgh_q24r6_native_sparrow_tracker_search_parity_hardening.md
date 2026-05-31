# SGH-Q24R6 — Native Sparrow tracker + search parity hardening

## One-line goal

Make the Q24R5 native Sparrow core behave much closer to jagua_rs/Sparrow in tracker/search/separation, while keeping compression out of scope.

## Current state after Q24R5

Q24R5 successfully cut production `sparrow_cde` away from the old VRS core. The production route is now native:

```text
SparrowProblem -> SparrowOptimizer::solve -> SparrowSolution
```

That is good. But the new native core is still young:

- tracker loss is mostly binary collision count;
- search is too shallow and mainly current-sheet based;
- worker logic is worker-shaped but not a real best-worker competition;
- exploration/disruption is shallow;
- diagnostics do not fully reflect search/tracker work;
- LV8 real geometry has not yet been proven on a native smoke.

## Main rule

Do not revert to the old solver. Do not wrap old VRS behavior. Do not fix this through compression.

This task must deepen the native Sparrow core itself.

## Expected result

After Q24R6, the solver should still be architecturally native, but with stronger algorithmic parity:

```text
Native model cutover: retained
Native CDE tracker: stronger, quantified loss
Native search: multi-sheet/container + rotation aware
Native worker loop: snapshot/compare/best-loadback
Native exploration: pool/restore/disruption improved
Compression: disabled / zero pass
LV8: 12 type × 1 smoke attempted and reported
```

## What this is not

This is not the full 276-piece LV8 target. That comes later.

This is not compression hardening. For fixed multisheet nesting, compression is a later last-sheet-only optimization layer.
