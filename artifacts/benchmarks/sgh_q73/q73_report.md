# SGH-Q73 Report - Big-part pitch-minimizing interlock row-seed

## Verdict: FAIL

## Run

| run | status | placed | unplaced | used | util % | wall s |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| q73_A_interlock_rowseed_2sheet_sp5 | partial | 252 | 24 | 2 | 50.2812070220173 | 580.4 |

## Big-part (dominant repeated type) distribution

| metric | Q72 | Q73 |
| --- | --- | --- |
| dominant part | Lv8_11612_6db | Lv8_11612_6db |
| qty | 6 | 6 |
| placed | 3 | 3 |
| per-sheet rotations | `{"1": [89.92, 269.94], "0": [90.0]}` | `{"1": [89.88, 269.92], "0": [90.0]}` |
| min per used sheet | 1 | 1 |
| non-orthogonal placements | 0 | 0 |

## Q73 row-seed diagnostics

| check | value |
| --- | --- |
| row seed used | true |
| chosen rotation (deg) | 81.5 |
| min clear pitch (mm) | 521.0493873235815 |
| copies per sheet | 2 |
| seeded count | 4 |
| no-drop seed used | true |
| forced latest locked | true |
| final pairs / boundary | 0 / 0 |

## Per-sheet

| sheet | placed | physical util % |
| --- | ---: | ---: |
| 0 | 148 | 32.3313 |
| 1 | 104 | 61.242 |

## Comparison

| run | placed | used sheets | util % |
| --- | ---: | ---: | ---: |
| Q72 no-drop | 262 | 2 | 53.445129566910126 |
| **Q73 row-seed** | **252** | 2 | 50.2812070220173 |

## Visual Audit (manual, result-centric)

- This run is produced with the opt-in `VRS_BIG_ROW_SEED=1`. The seeder DID run (seeded 4 big copies,
  2 per sheet, @ 81.5deg, pitch 521 mm — non-orthogonal, CDE-valid at seed time).
- **But the final render regressed:** sheet 0 shows only ONE big part back at ~90deg with large empty
  space (148 parts, 32.3% util); the seeded 2-per-sheet / 81.5deg arrangement was destroyed.
- **Root cause:** the unpinned exploration SA resolves overlaps between the big row and the
  surrounding fillers by moving the high-loss BIG parts (rotating them back toward 90deg and ejecting
  one), because Sparrow has no item-pinning. Net: 252 placed < Q72 262 -> a regression.
- **Honest conclusion:** big-part row-seeding is valid at seed time but counterproductive without
  (a) item-pinning / obstacle-aware filling so the seed survives, and (b) the geometric reality that
  3 of this 2522 mm part do NOT fit per sheet (proven by a shapely BL-packing prototype). The seeder
  is gated OFF by default; the production latest-path stays at Q72 (262).

## Finding

Q73 row-seeds the dominant repeated big type at the tightest CDE-clear (often non-orthogonal) orientation, distributed to fill a sheet before opening the next. Judged on the big-part distribution (>= 2 per used sheet, non-orthogonal) and total placed_count not regressing vs Q72 (262); the 3-per-sheet limit for this long part is geometric and is reported honestly.

## Artifact evidence

- summary: `artifacts/benchmarks/sgh_q73/q73_summary.json`
- input: `artifacts/benchmarks/sgh_q73/inputs/q73_full276_2x1500x3000_margin5_spacing5_continuous_600.json`
- output: `artifacts/benchmarks/sgh_q73/outputs/q73_A_interlock_rowseed_2sheet_sp5_output.json`
- log: `artifacts/benchmarks/sgh_q73/logs/q73_A_interlock_rowseed_2sheet_sp5.log`
