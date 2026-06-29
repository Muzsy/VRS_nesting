# SGH-Q72 Report - Full-instance seed + fixed-bin global repack

## Verdict: FAIL

## Goal

- Keep the solver on the forced latest-path with NO part dropped before the optimizer.
- The seed must retain all instances; the real exploration SA + redistribute pipeline packs
  them on the fixed 2 sheets.
- Success is judged ONLY on placed_count vs the Q62 baseline (259).

## Run

| run | status | placed | unplaced | used sheets | util % | non-orth rot | wall s |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| q72_A_no_drop_repack_2sheet_sp5 | partial | 254 | 22 | 2 | 35.77834156291516 | 192 | 579.4 |

## Q72 No-drop / global-repack diagnostics

| check | value |
| --- | --- |
| forced latest lock active | true |
| no-drop seed used | true |
| seed instance count before pipeline | 276 |
| builder placed before completion | 219 |
| global repack re-inserted count | 57 |
| native seed fallback used | false |
| seed source | builder_forced_latest |

## Per-sheet

| sheet | placed | physical util % |
| --- | ---: | ---: |
| 0 | 153 | 25.7821 |
| 1 | 101 | 39.4753 |

## Comparison (placed_count is the only acceptance metric)

| run | placed | unplaced | used sheets | util % |
| --- | ---: | ---: | ---: | ---: |
| Q62 current (baseline) | 259 | 17 | 2 | 49.96641349141249 |
| Q70 corner-first | 237 | 39 | 2 | 58.695127362605085 |
| Q71 edge-lock | 215 | 61 | 2 | 53.81611027571408 |
| **Q72 no-drop repack** | **254** | 22 | 2 | 35.77834156291516 |

- Target: 276 / 2 sheets. Baseline to beat: 259 (Q62).

## Visual Proxy

- Render manifest: `artifacts/benchmarks/sgh_q72/renders/q72_A_no_drop_repack_2sheet_sp5/render_manifest.json`
- Top rotations: `[{"rotation_deg": 90.0, "count": 18}, {"rotation_deg": 270.0, "count": 17}, {"rotation_deg": 180.0, "count": 14}, {"rotation_deg": 0.0, "count": 13}, {"rotation_deg": 292.5, "count": 11}, {"rotation_deg": 112.5, "count": 9}, {"rotation_deg": 157.5, "count": 9}, {"rotation_deg": 315.0, "count": 9}, {"rotation_deg": 202.5, "count": 8}, {"rotation_deg": 67.5, "count": 7}, {"rotation_deg": 225.0, "count": 6}, {"rotation_deg": 247.5, "count": 6}]`
- Sheet 0 physical utilization: `25.7821`

## Visual Audit

- Pending manual review after the benchmark run.

## Finding

Q72 completes the forced-latest seed to a no-drop full-instance seed (builder critical/anchor placements kept, remainder re-inserted) and hands it to the real exploration SA + redistribute pipeline on the fixed 2 sheets. The only acceptance metric is placed_count vs the Q62 baseline (259); edge-lock/corner/residual are diagnostics only.

## Artifact evidence

- summary: `artifacts/benchmarks/sgh_q72/q72_summary.json`
- input: `artifacts/benchmarks/sgh_q72/inputs/q72_full276_2x1500x3000_margin5_spacing5_continuous_600.json`
- output: `artifacts/benchmarks/sgh_q72/outputs/q72_A_no_drop_repack_2sheet_sp5_output.json`
- log: `artifacts/benchmarks/sgh_q72/logs/q72_A_no_drop_repack_2sheet_sp5.log`
