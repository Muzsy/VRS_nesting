# SGH-Q24R6 — Native Sparrow tracker + search parity hardening package

This package is the next task after SGH-Q24R5 completed the architectural native-model cutover.

Q24R5 is a real milestone: production `sparrow_cde` now runs through `SparrowProblem -> SparrowOptimizer::solve -> SparrowSolution` instead of `WorkingLayout` / `VrsCollisionTracker`. Q24R6 must not undo that.

## Start here

```bash
codex/prompts/egyedi_solver/sgh_q24r6_native_sparrow_tracker_search_parity_hardening/run.md
```

## Controlling objective

Harden the new native Sparrow core toward jagua_rs/Sparrow behavior, **compression excluded**.

The task is not another model cutover. The model cut is done. Now make the native model work like a real Sparrow separation/search core:

```text
SparrowProblem
  -> native constructive/LBF-like seed
  -> SparrowCollisionTracker with CDE pair/container quantification
  -> native multi-worker move_items/search
  -> exploration pool/restore/disruption
  -> native final CDE validation
  -> SparrowSolution projection
```

## Non-negotiable exclusions

Do not spend the task on compression. Do not use compression to pass any gate. Default production `sparrow_cde` must keep compression disabled/zero-pass.

Do not reintroduce the old VRS solver core. If `WorkingLayout`, `VrsCollisionTracker`, old `SparrowSeparationKernel`, `PhaseOptimizer`, or `MultiSheetManager` becomes reachable from production `sparrow_cde`, the task is a failure.

## Main gaps to close

- `SparrowCollisionTracker` currently uses mostly count-like pair/boundary loss. Replace this with CDE-truth separation/resolution-distance style quantification suitable for GLS and search ranking.
- `native_search_placement` currently searches mainly on the current sheet. It must search across eligible sheets/containers and rotations.
- The worker loop is still sequential/skeleton. Implement proper worker snapshots, candidate comparison, best-worker load-back, and diagnostics.
- Exploration/disruption is shallow. Deepen pool/restore/disruption on native state, still without compression.
- Diagnostics currently under-report the real native tracker/search activity. Make them truthful.
- Add a small LV8 real-geometry smoke: `12 part types × 1 quantity`, not full 276 yet.

## Reject if

- The diff mainly changes docs/reports/scripts and does not materially improve native Rust core logic.
- Production `sparrow_cde` returns to old `WorkingLayout` / `VrsCollisionTracker` / legacy separation.
- The tracker remains binary count-only (`1.0` per collision) and search ranking still uses only `colliding_layout_idxs.len()`.
- Search only considers the current sheet/container.
- There is no real worker snapshot/best-worker restore path.
- Medium CDE is recovered by fallback, bbox truth, LBF fallback, or compression.
- LV8 12-type smoke is skipped without a real blocker documented in the report.
