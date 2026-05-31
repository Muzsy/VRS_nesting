# SGH-Q24R7-R1 — Dense first-sheet real-run fix package

This is a **repair task** for SGH-Q24R7.

Q24R7 made useful sampler/evaluator changes, but the key dense LV8 first-sheet probe did **not** prove dense native Sparrow search: the production native solver returned a guarded `partial` for `instances >= 100 && sheets.len() == 1`, with marker diagnostics and effectively `0.0s` runtime. That is not acceptable as a dense search proof.

## Start here

```bash
codex/prompts/egyedi_solver/sgh_q24r7r1_dense_first_sheet_real_run_fix/run.md
```

## Non-negotiable repair

The 191-instance LV8 first-sheet probe must be a **real bounded native Sparrow search**, not an early guarded return.

Remove, replace, or strictly test-only quarantine the large single-sheet guard that currently short-circuits:

```rust
if instances.len() >= 100 && sheets.len() == 1 {
    ...
    return SparrowSolveResult { feasible: false, ... };
}
```

The solver may still return `partial`, but only after it actually runs the native lifecycle:

```text
constructive seed
-> SparrowCollisionTracker build
-> exploration/separation attempt(s)
-> worker/search/evaluator calls
-> CDE final validation
-> honest partial diagnostics if not solved
```

## First-sheet LV8 vector stays fixed

Use the exact Nest&Cut reference sheet-1 vector already established in Q24R7:

| Fixture part id | Quantity |
|---|---:|
| `LV8_01170_10db` | 10 |
| `LV8_02048_20db` | 7 |
| `LV8_02049_50db` | 50 |
| `Lv8_07919_16db` | 13 |
| `Lv8_07920_50db` | 12 |
| `Lv8_07921_50db` | 33 |
| `Lv8_15435_10db` | 10 |
| `Lv8_11612_6db` | 3 |
| `Lv8_15348_6db` | 4 |
| `Lv8_10059_10db` | 10 |
| `LV8_00035_28db` | 28 |
| `LV8_00057_20db` | 11 |
| **TOTAL** | **191** |

## PASS definition

This repair can PASS without full 191/191 placement, but only if:

- the dense guard is gone from production `sparrow_cde`;
- the 191 probe actually runs search/separation under CDE;
- runtime is real and bounded, not `0.0s` guarded partial;
- diagnostics prove worker/search/evaluator/tracker activity;
- partial output is honest: no fake solved metric, exact final pairs/boundary, and top blockers / colliding or unresolved instance ids are reported;
- compression remains disabled and unused.

If the implementation still skips the dense run or reports `191/191` as if valid while `status=partial`, mark the task `REVISE`.
