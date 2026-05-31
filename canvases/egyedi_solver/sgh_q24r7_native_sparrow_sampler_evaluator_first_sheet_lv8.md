# SGH-Q24R7 — Native Sparrow sampler/evaluator + LV8 first-sheet reference

## One-line goal

Make the native Sparrow core search like Sparrow, not like a shallow fallback sampler, and test it on the real LV8 first-sheet composition from the Nest&Cut report.

## Current state after Q24R6

Q24R6 is a real PASS:

```text
SparrowProblem -> SparrowOptimizer::solve -> SparrowSolution
native CDE tracker quantification
multi-sheet/rotation search
worker snapshots / best-worker load-back
LV8 12 types x1 smoke passed
compression disabled
```

But the remaining search gap is still material:

- infeasible sample ordering still uses an AABB-style proxy;
- cross-sheet/container search is still partly fallback-like;
- sampling/evaluator logic is not close enough to Sparrow's `sample/search.rs` + `eval/sep_evaluator.rs`;
- the LV8 proof is still sparse.

## Correct dense LV8 probe

Do not use the artificial `12 x max 4` subset. The Q24R7 probe input must be generated from:

```text
tests/fixtures/nesting_engine/ne2_input_lv8jav.json
```

with quantities equal to **Nesting layout 1 / 2** from:

```text
samples/real_work_dxf/0014-01H/lv8jav/Nested/project_2447207_report.pdf
```

Reference sheet 1 quantity vector:

```text
LV8_01170_10db      10
LV8_02048_20db       7
LV8_02049_50db      50
Lv8_07919_16db      13
Lv8_07920_50db      12
Lv8_07921_50db      33
Lv8_15435_10db      10
Lv8_11612_6db        3
Lv8_15348_6db        4
Lv8_10059_10db      10
LV8_00035_28db      28
LV8_00057_20db      11
TOTAL              191
```

## Main rule

The goal is not compression and not another architecture cut. The goal is native sample/evaluator parity and dense LV8 scaling.

## Expected result

After Q24R7:

```text
Architecture: still native, no old VRS core
Sampler: stronger global/focused/container-aware candidates
Evaluator: polygon/CDE-aware infeasible magnitude, not AABB truth/proxy as main ordering
Search: not current-sheet-only and not fallback-only multi-container
Worker loop: larger/configurable search budget and candidate competition
LV8: first-sheet reference input generated and run honestly
Compression: zero-pass / disabled
```

If full 191/191 is not achieved, do not hide it. Report why and what remains.
