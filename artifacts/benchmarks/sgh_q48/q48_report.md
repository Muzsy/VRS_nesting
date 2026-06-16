# SGH-Q48 Report - Interlocking density compaction benchmark

## Verdict: PASS

## Goal

- Full276 LV8 package, 6 x 1500x3000 mm sheets available.
- Technology: margin 5.0 mm, spacing 8.0 mm, kerf 0.0 mm.
- Rotation: global `rotation_policy = continuous`.
- A/B check: `VRS_BPP_DENSITY_COMPACT=1` versus `VRS_BPP_DENSITY_COMPACT=0`.
- Acceptance: valid output, no sheet-count regression, density pass ran.

## Runs

| run | status | placed | used sheets | util % | final pairs | boundary | density applied | interlock generated | interlock accepted | wall s | acceptance |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |
| q48_A_densityon_300 | ok | 276 | 3 | 54.4152 | 0 | 0 | true | 20 | 2 | 293.6 | PASS |
| q48_B_densityoff_300 | ok | 276 | 3 | 54.4152 | 0 | 0 | false | 0 | 0 | 292.4 | PASS |

## Density evidence

- Density pass applied in run A: `true`
- Density moves accepted in run A: `2`
- Interlock candidates generated in run A: `20`
- Interlock candidates accepted in run A: `2`
- Run B keeps the density pass disabled.

## Acceptance

| check | value |
| --- | --- |
| valid A | true |
| valid B | true |
| no sheet-count regression | true |
| density pass ran | true |

## Artifact evidence

- summary: `artifacts/benchmarks/sgh_q48/q48_summary.json`
- input: `artifacts/benchmarks/sgh_q48/inputs/q48_full276_6x1500x3000_margin5_spacing8_continuous_300.json`
- output A: `artifacts/benchmarks/sgh_q48/outputs/q48_A_densityon_300_output.json`
- output B: `artifacts/benchmarks/sgh_q48/outputs/q48_B_densityoff_300_output.json`
- log A: `artifacts/benchmarks/sgh_q48/logs/q48_A_densityon_300.log`
- log B: `artifacts/benchmarks/sgh_q48/logs/q48_B_densityoff_300.log`

## Render evidence

- A manifest: `artifacts/benchmarks/sgh_q48/renders/q48_A_densityon_300/render_manifest.json`
- A sheets: `sheet_00.svg/png`, `sheet_01.svg/png`, `sheet_02.svg/png`
- A overview: `artifacts/benchmarks/sgh_q48/renders/q48_A_densityon_300/overview.svg`,
  `artifacts/benchmarks/sgh_q48/renders/q48_A_densityon_300/overview.png`
- B manifest: `artifacts/benchmarks/sgh_q48/renders/q48_B_densityoff_300/render_manifest.json`
- B sheets: `sheet_00.svg/png`, `sheet_01.svg/png`, `sheet_02.svg/png`
- B overview: `artifacts/benchmarks/sgh_q48/renders/q48_B_densityoff_300/overview.svg`,
  `artifacts/benchmarks/sgh_q48/renders/q48_B_densityoff_300/overview.png`
