# SGH-Q50 Report - Density-guided LNS sheet-drop benchmark

## Verdict: PASS

## Goal

- Full276 LV8 package, 6 x 1500x3000 mm sheets available.
- Technology: margin 5.0 mm, spacing 8.0 mm, kerf 0.0 mm.
- Rotation: global `rotation_policy = continuous`.
- A/B check: density + LNS sheet-drop ON versus density-only baseline.
- Acceptance: valid output, no sheet-count regression, LNS pass ran and attempted elimination.
- Stretch goal: drop from 3 sheets to 2 sheets.

## Runs

| run | status | placed | used sheets | util % | final pairs | LNS applied | attempts | sheets dropped | restarts | wall s | acceptance |
| --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- |
| q50_A_lnson_300 | ok | 276 | 3 | 54.4152 | 0 | true | 1 | 0 | 3 | 243.0 | PASS |
| q50_B_lnsoff_300 | ok | 276 | 3 | 54.4152 | 0 | false | 0 | 0 | 0 | 273.1 | PASS |

## LNS evidence

- LNS pass applied in run A: `true`
- LNS attempts in run A: `1`
- LNS restarts in run A: `3`
- LNS sheets dropped in run A: `0`
- Stretch result, dropped a sheet: `false`

## Acceptance

| check | value |
| --- | --- |
| valid A | true |
| valid B | true |
| no sheet-count regression | true |
| LNS pass ran | true |
| LNS attempted elimination | true |
| STRETCH LNS dropped a sheet | false |

## Artifact evidence

- summary: `artifacts/benchmarks/sgh_q50/q50_summary.json`
- input: `artifacts/benchmarks/sgh_q50/inputs/q50_full276_6x1500x3000_margin5_spacing8_continuous_300.json`
- output A: `artifacts/benchmarks/sgh_q50/outputs/q50_A_lnson_300_output.json`
- output B: `artifacts/benchmarks/sgh_q50/outputs/q50_B_lnsoff_300_output.json`
- log A: `artifacts/benchmarks/sgh_q50/logs/q50_A_lnson_300.log`
- log B: `artifacts/benchmarks/sgh_q50/logs/q50_B_lnsoff_300.log`

## Render evidence

- A manifest: `artifacts/benchmarks/sgh_q50/renders/q50_A_lnson_300/render_manifest.json`
- A sheets: `sheet_00.svg/png`, `sheet_01.svg/png`, `sheet_02.svg/png`
- A overview: `artifacts/benchmarks/sgh_q50/renders/q50_A_lnson_300/overview.svg`,
  `artifacts/benchmarks/sgh_q50/renders/q50_A_lnson_300/overview.png`
- B manifest: `artifacts/benchmarks/sgh_q50/renders/q50_B_lnsoff_300/render_manifest.json`
- B sheets: `sheet_00.svg/png`, `sheet_01.svg/png`, `sheet_02.svg/png`
- B overview: `artifacts/benchmarks/sgh_q50/renders/q50_B_lnsoff_300/overview.svg`,
  `artifacts/benchmarks/sgh_q50/renders/q50_B_lnsoff_300/overview.png`
