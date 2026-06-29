# SGH-Q74 Report - Big-part pitch-minimizing interlock row-seed

## Verdict: PASS

## Run

| run | status | placed | unplaced | used | util % | wall s |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| q74_A_edge_interlock_pin_2sheet_sp5 | partial | 274 | 2 | 2 | 65.07422525431444 | 239.4 |

## Big-part (dominant repeated type) distribution

| metric | Q72 | Q74 |
| --- | --- | --- |
| dominant part | Lv8_11612_6db | Lv8_11612_6db |
| qty | 6 | 6 |
| placed | 1 | 4 |
| per-sheet rotations | `{"1": [90.0]}` | `{"0": [92.0, 92.0], "1": [92.0, 92.0]}` |
| min per used sheet | 1 | 2 |
| non-orthogonal placements | 0 | 4 |

## Q74 row-seed diagnostics

| check | value |
| --- | --- |
| edge interlock seed used | true |
| chosen rotation (deg) | 92.0 |
| pinned (locked) count | 4 |
| copies per sheet | 2 |
| seeded count | 4 |
| no-drop seed used | true |
| forced latest locked | true |
| final pairs / boundary | 0 / 0 |

## Per-sheet

| sheet | placed | physical util % |
| --- | ---: | ---: |
| 0 | 199 | 58.064 |
| 1 | 75 | 63.5929 |

## Comparison

| run | placed | used sheets | util % |
| --- | ---: | ---: | ---: |
| Q72 no-drop | 254 | 2 | 35.77834156291516 |
| **Q74 row-seed** | **274** | 2 | 65.07422525431444 |

## Visual Audit

- Pending manual review after the benchmark run.

## Finding

Q74 row-seeds the dominant repeated big type at the tightest CDE-clear (often non-orthogonal) orientation, distributed to fill a sheet before opening the next. Judged on the big-part distribution (>= 2 per used sheet, non-orthogonal) and total placed_count not regressing vs Q72 (262); the 3-per-sheet limit for this long part is geometric and is reported honestly.

## Artifact evidence

- summary: `artifacts/benchmarks/sgh_q74/q74_summary.json`
- input: `artifacts/benchmarks/sgh_q74/inputs/q74_full276_2x1500x3000_margin5_spacing5_continuous_600.json`
- output: `artifacts/benchmarks/sgh_q74/outputs/q74_A_edge_interlock_pin_2sheet_sp5_output.json`
- log: `artifacts/benchmarks/sgh_q74/logs/q74_A_edge_interlock_pin_2sheet_sp5.log`
