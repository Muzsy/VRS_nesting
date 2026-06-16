# SGH-Q47 Report - Shape profile priority layer benchmark

## Verdict: PASS

## Goal

- Full276 LV8 package, 6 x 1500x3000 mm sheets available.
- Technology: margin 5.0 mm, spacing 8.0 mm, kerf 0.0 mm.
- Rotation: global `rotation_policy = continuous`.
- A/B check: `VRS_SHAPE_PROFILE=1` versus `VRS_SHAPE_PROFILE=0`.
- Acceptance: both runs valid, no sheet-count regression, priority change visible.

## Runs

| run | status | placed | unplaced | used sheets | util % | final pairs | boundary | wall s | acceptance |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| q47_A_profileon_300 | ok | 276 | 0 | 3 | 54.4152 | 0 | 0 | 315.8 | PASS |
| q47_B_profileoff_300 | ok | 276 | 0 | 3 | 54.4152 | 0 | 0 | 290.1 | PASS |

## Shape profile evidence

- Profile diagnostics type count: `12`
- Anchors before fillers: `true`
- Highest priority type: `Lv8_11612_6db`
- Highest priority classes: `concave_like`, `large_anchor`, `repeated_family`,
  `high_interlock_potential`
- Highest priority budget multiplier: `2.25`

## Acceptance

| check | value |
| --- | --- |
| valid A | true |
| valid B | true |
| no sheet-count regression | true |
| priority change visible | true |

## Artifact evidence

- summary: `artifacts/benchmarks/sgh_q47/q47_summary.json`
- input: `artifacts/benchmarks/sgh_q47/inputs/q47_full276_6x1500x3000_margin5_spacing8_continuous_300.json`
- output A: `artifacts/benchmarks/sgh_q47/outputs/q47_A_profileon_300_output.json`
- output B: `artifacts/benchmarks/sgh_q47/outputs/q47_B_profileoff_300_output.json`
- log A: `artifacts/benchmarks/sgh_q47/logs/q47_A_profileon_300.log`
- log B: `artifacts/benchmarks/sgh_q47/logs/q47_B_profileoff_300.log`

## Render evidence

- A manifest: `artifacts/benchmarks/sgh_q47/renders/q47_A_profileon_300/render_manifest.json`
- A sheets: `sheet_00.svg/png`, `sheet_01.svg/png`, `sheet_02.svg/png`
- A overview: `artifacts/benchmarks/sgh_q47/renders/q47_A_profileon_300/overview.svg`,
  `artifacts/benchmarks/sgh_q47/renders/q47_A_profileon_300/overview.png`
- B manifest: `artifacts/benchmarks/sgh_q47/renders/q47_B_profileoff_300/render_manifest.json`
- B sheets: `sheet_00.svg/png`, `sheet_01.svg/png`, `sheet_02.svg/png`
- B overview: `artifacts/benchmarks/sgh_q47/renders/q47_B_profileoff_300/overview.svg`,
  `artifacts/benchmarks/sgh_q47/renders/q47_B_profileoff_300/overview.png`
