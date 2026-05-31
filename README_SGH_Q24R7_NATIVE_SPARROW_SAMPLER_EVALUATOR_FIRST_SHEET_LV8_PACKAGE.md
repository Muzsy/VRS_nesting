# SGH-Q24R7 — Native Sparrow sampler/evaluator + LV8 first-sheet reference package

This package follows SGH-Q24R6.

Q24R5 cut production `sparrow_cde` to the native `SparrowProblem -> SparrowOptimizer::solve -> SparrowSolution` route. Q24R6 hardened native tracker/search/worker behavior. Q24R7 must now strengthen the native sampler/evaluator and prove the dense LV8 step on a **real reference subset**, not an artificial `12 types x max 4` subset.

## Start here

```bash
codex/prompts/egyedi_solver/sgh_q24r7_native_sparrow_sampler_evaluator_first_sheet_lv8/run.md
```

## Correct LV8 probe set

Use the Nest&Cut reference **layout 1 / sheet 1** composition from:

```text
samples/real_work_dxf/0014-01H/lv8jav/Nested/project_2447207_report.pdf
```

The first sheet contains **191 parts**:

| Fixture part id | Quantity on reference sheet 1 |
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

Source mapping notes:

- Report part `LV8_00057-2_20db REV8` maps to fixture id `LV8_00057_20db`.
- Report part `Lv8 _10059_10db REV2` maps to fixture id `Lv8_10059_10db`.
- Report sheet dimensions are shown as `3000 mm x 1500 mm`; the fixture stores the equivalent rectangle as `1500 x 3000`.
- The report used 5 mm gap and all rotations. The current fixture has its own solver-ready geometry and rotation lists. Do not silently change fixture semantics; document any gap/rotation mismatch honestly.

## Controlling objective

Bring native `sparrow_cde` closer to jagua_rs/Sparrow sample/evaluator behavior **without compression**:

```text
native candidate generation
  -> multi-container/global/focused sampling
  -> polygon/CDE-aware sample evaluator
  -> coordinate descent/refinement
  -> worker competition/load-back
  -> dense LV8 sheet-1 reference probe
```

## Non-negotiables

- Do not reintroduce `WorkingLayout`, `VrsCollisionTracker`, old `SparrowSeparationKernel`, `PhaseOptimizer`, `MultiSheetManager`, legacy solver, LBF fallback, or bbox truth into production `sparrow_cde`.
- Do not use compression to pass any gate. Compression remains out of scope.
- Do not replace the dense LV8 reference subset with an artificial subset.
- Do not fake the first-sheet result. If it cannot place all 191, report exact placed/unplaced counts and algorithmic blockers.

## Required output

Write a report to:

```text
codex/reports/egyedi_solver/sgh_q24r7_native_sparrow_sampler_evaluator_first_sheet_lv8.md
```

Include:

- current Sparrow reference files read from `.cache/sparrow`;
- code changes with file paths;
- static architecture status;
- sampler/evaluator changes;
- medium CDE runtime result;
- LV8 12 types x1 regression;
- LV8 first-sheet reference probe: 191 required, placed count, unplaced ids, runtime, final CDE status, diagnostics;
- explicit status: `PASS` only if hard gates pass; `REVISE` otherwise.
