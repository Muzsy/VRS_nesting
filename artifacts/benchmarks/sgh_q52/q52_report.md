# SGH-Q52 Report - Density-biased admission benchmark

## Verdict: PASS

## Goal

- Measure density-biased admission separation against Q51 builder-only baselines.
- Prove spacing-0 still reaches 3 big curved parts per sheet.
- Confirm tight spacing and full276 no-regression while documenting the negative finding.

## Runs

| run | status | placed | used sheets | util % | max big/sheet | builder applied | critical admitted | wall s | acceptance |
| --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |
| 6big_sp0_builderon | ok | 6 | 2 | 39.8312 | 3 | true | 3 | 73.0 | PASS |
| 6big_sp5_builderonly | ok | 6 | 3 | 27.3879 | 2 | true | 2 | 78.3 | PASS |
| 6big_sp5_bias | ok | 6 | 3 | 27.3879 | 2 | true | 6 | 77.0 | PASS |
| 6big_sp8_builderonly | ok | 6 | 3 | 27.8872 | 2 | true | 4 | 77.1 | PASS |
| 6big_sp8_bias | ok | 6 | 3 | 27.8872 | 2 | true | 6 | 76.1 | PASS |
| full276_bias | ok | 276 | 3 | 54.4152 | 2 | true | 2 | 292.9 | PASS |
| full276_builderonly | ok | 276 | 3 | 54.4152 | 2 | true | 2 | 292.9 | PASS |
| full276_off | ok | 276 | 3 | 54.4152 | 2 | false | 0 | 317.7 | PASS |

## Acceptance

| check | value |
| --- | --- |
| proof 2 sheets, 3 big at spacing 0 | true |
| tight spacing no regression vs builder only | true |
| full276 no regression | true |
| tight spacing improved big per sheet | false |

## Finding

NEGATIVE as expected: density-bias matches overlap-minimising separation at tight spacing, both
remaining at 2 big parts per sheet. It is retained as a gated building block for a later simultaneous
multi-part admission search.

## Artifact evidence

- summary: `artifacts/benchmarks/sgh_q52/q52_summary.json`
- inputs: `artifacts/benchmarks/sgh_q52/inputs/`
- outputs: `artifacts/benchmarks/sgh_q52/outputs/`
- logs: `artifacts/benchmarks/sgh_q52/logs/`
- run log: `artifacts/benchmarks/sgh_q52/q52_run.log`

## Render evidence

- `artifacts/benchmarks/sgh_q52/renders/6big_sp0_builderon/render_manifest.json`
- `artifacts/benchmarks/sgh_q52/renders/6big_sp5_bias/render_manifest.json`
- `artifacts/benchmarks/sgh_q52/renders/6big_sp5_builderonly/render_manifest.json`
- `artifacts/benchmarks/sgh_q52/renders/6big_sp8_bias/render_manifest.json`
- `artifacts/benchmarks/sgh_q52/renders/6big_sp8_builderonly/render_manifest.json`
- `artifacts/benchmarks/sgh_q52/renders/full276_bias/render_manifest.json`
- `artifacts/benchmarks/sgh_q52/renders/full276_builderonly/render_manifest.json`
- `artifacts/benchmarks/sgh_q52/renders/full276_off/render_manifest.json`
