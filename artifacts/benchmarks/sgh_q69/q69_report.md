# SGH-Q69 Report - Full276 LV8 forced-latest result audit

## Verdict: FAIL

## Goal

- Force the solver onto the current role-aware / hint-aware / simultaneous-aware path.
- Disallow native constructive seed fallback and random bootstrap rescue.
- Re-run the same Full276 LV8 package on 2 x 1500x3000 mm sheets with margin 5 mm and spacing 5 mm.
- Produce a hard post-check with render evidence and explicit diagnostics.

## Run

| run | status | placed | unplaced | used sheets | util % | non-orth rotations | sheets opened | pair accepted | sim authority | wall s |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| q69_A_forced_latest_2sheet_sp5 | partial | 62 | 214 | 2 | 48.79324783882088 | 42 | 2 | 0 | False | 156.1 |

## Hard Post-Check

| check | value |
| --- | --- |
| forced latest lock active | true |
| seed source = builder_forced_latest | true |
| native seed fallback used | false |
| random bootstrap used | false |
| builder reached multiple sheets | true |
| role-aware activity visible in diagnostics | true |
| non-orth rotation count > 0 | true |

## Comparison

| baseline | status | placed | unplaced | used sheets | pair accepted | pair consulted | wall s |
| --- | --- | ---: | ---: | ---: | ---: | --- | ---: |
| Q62 current | partial | 259 | 17 | 2 | 0 | False | 0.0 |
| Q63 strict latest | partial | 39 | 237 | 1 | 1 | True | 0.0 |
| Q69 forced latest | partial | 62 | 214 | 2 | 0 | True | 156.1 |

## Visual Proxy

- Render manifest: `artifacts/benchmarks/sgh_q69/renders/q69_A_forced_latest_2sheet_sp5/render_manifest.json`
- Non-orth rotation count: `42`
- Top rotations: `[{"rotation_deg": 270.0, "count": 8}, {"rotation_deg": 74.0, "count": 7}, {"rotation_deg": 180.0, "count": 7}, {"rotation_deg": 330.0, "count": 5}, {"rotation_deg": 300.0, "count": 4}, {"rotation_deg": 90.0, "count": 3}, {"rotation_deg": 98.0, "count": 3}, {"rotation_deg": 210.0, "count": 3}, {"rotation_deg": 240.0, "count": 3}, {"rotation_deg": 0.0, "count": 2}, {"rotation_deg": 60.0, "count": 2}, {"rotation_deg": 82.0, "count": 2}]`
- Interpretation: The forced-latest run exposes non-orthogonal placement activity, so the current path is not visually collapsing to a 90-degree-only layout.

## Visual Audit

- `sheet_00.png`: only `5` placements, but they are clearly not legacy grid-fill placements. The large orange parts are edge-driven and the yellow inserts show cavity/slot-style usage.
- `sheet_01.png`: `57` placements with many diagonal green parts and rotated yellow fillers. The current role-aware path is visibly active here; this is not a 90-degree-only fallback layout.
- Manual conclusion: the visibility goal passes, but the production-quality goal fails. The solver is now honestly showing the newer logic, yet it still leaves `214` parts unplaced and remains dramatically below the masked Q62 current result.

## Finding

The solver stayed on the forced latest-path lock without native seed fallback or random bootstrap, and both diagnostics and renders now make that visible. That part of the task succeeded. The benchmark result itself is still a hard fail: `62/276` placed on `2` sheets is far below the Q62 current run's `259/276`, so the latest path is now observable but not yet competitive.

## Artifact evidence

- summary: `artifacts/benchmarks/sgh_q69/q69_summary.json`
- input: `artifacts/benchmarks/sgh_q69/inputs/q69_full276_2x1500x3000_margin5_spacing5_continuous_600.json`
- output: `artifacts/benchmarks/sgh_q69/outputs/q69_A_forced_latest_2sheet_sp5_output.json`
- log: `artifacts/benchmarks/sgh_q69/logs/q69_A_forced_latest_2sheet_sp5.log`
