# SGH-Q49 Report - Density budget allocation benchmark

## Verdict: PASS

## Goal

- Full276 LV8 package, 6 x 1500x3000 mm sheets available.
- Technology: margin 5.0 mm, spacing 8.0 mm, kerf 0.0 mm.
- Rotation: global `rotation_policy = continuous`.
- A/B check: density compaction ON with reserved budget versus density compaction OFF.
- Acceptance: valid output, no sheet-count regression, density pass runs across all 276 parts.

## Runs

| run | status | placed | used sheets | util % | final pairs | density applied | sweeps | parts processed | interlock generated | interlock accepted | wall s | acceptance |
| --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| q49_A_densityon_300 | ok | 276 | 3 | 54.4152 | 0 | true | 18 | 1656 | 109991 | 480 | 272.8 | PASS |
| q49_B_densityoff_300 | ok | 276 | 3 | 54.4152 | 0 | false | 0 | 0 | 0 | 0 | 291.6 | PASS |

## Density budget evidence

- Density sweeps in run A: `18`
- Density parts processed in run A: `1656`
- Density moves accepted in run A: `497`
- Interlock accepted in run A: `480`
- Q48 starved reference: `20` generated / `2` accepted.

## Acceptance

| check | value |
| --- | --- |
| valid A | true |
| valid B | true |
| no sheet-count regression | true |
| density pass ran | true |
| density processed all 276 | true |

## Artifact evidence

- summary: `artifacts/benchmarks/sgh_q49/q49_summary.json`
- input: `artifacts/benchmarks/sgh_q49/inputs/q49_full276_6x1500x3000_margin5_spacing8_continuous_300.json`
- output A: `artifacts/benchmarks/sgh_q49/outputs/q49_A_densityon_300_output.json`
- output B: `artifacts/benchmarks/sgh_q49/outputs/q49_B_densityoff_300_output.json`
- log A: `artifacts/benchmarks/sgh_q49/logs/q49_A_densityon_300.log`
- log B: `artifacts/benchmarks/sgh_q49/logs/q49_B_densityoff_300.log`

## Render evidence

- A manifest: `artifacts/benchmarks/sgh_q49/renders/q49_A_densityon_300/render_manifest.json`
- A sheets: `sheet_00.svg/png`, `sheet_01.svg/png`, `sheet_02.svg/png`
- A overview: `artifacts/benchmarks/sgh_q49/renders/q49_A_densityon_300/overview.svg`,
  `artifacts/benchmarks/sgh_q49/renders/q49_A_densityon_300/overview.png`
- B manifest: `artifacts/benchmarks/sgh_q49/renders/q49_B_densityoff_300/render_manifest.json`
- B sheets: `sheet_00.svg/png`, `sheet_01.svg/png`, `sheet_02.svg/png`
- B overview: `artifacts/benchmarks/sgh_q49/renders/q49_B_densityoff_300/overview.svg`,
  `artifacts/benchmarks/sgh_q49/renders/q49_B_densityoff_300/overview.png`
