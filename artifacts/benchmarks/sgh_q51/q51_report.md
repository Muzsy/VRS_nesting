# SGH-Q51 Report - Critical-aware sheet builder benchmark

## Verdict: PASS

## Goal

- Prove the critical-aware constructive sheet builder can place 3 large curved parts per sheet
  when spacing is 0.
- Confirm tight spacing 8 and full276 runs remain valid with no full276 regression.
- Keep the benchmark evidence in `artifacts/benchmarks/sgh_q51/`.

## Runs

| run | status | placed | used sheets | util % | max big/sheet | builder applied | wall s | acceptance |
| --- | --- | ---: | ---: | ---: | ---: | --- | ---: | --- |
| 6big_sp0_builderon | ok | 6 | 2 | 39.8312 | 3 | true | 61.3 | PASS |
| 6big_sp8_builderon | ok | 6 | 3 | 27.8872 | 2 | true | 60.9 | PASS |
| full276_builderon | ok | 276 | 3 | 54.4152 | 2 | true | 244.0 | PASS |
| full276_builderoff | ok | 276 | 3 | 54.4152 | 2 | false | 243.1 | PASS |

## Acceptance

| check | value |
| --- | --- |
| proof 2 sheets, 3 big per sheet at spacing 0 | true |
| no full276 regression vs off | true |

## Artifact evidence

- summary: `artifacts/benchmarks/sgh_q51/q51_summary.json`
- inputs: `artifacts/benchmarks/sgh_q51/inputs/`
- outputs: `artifacts/benchmarks/sgh_q51/outputs/`
- logs: `artifacts/benchmarks/sgh_q51/logs/`

## Render evidence

- `artifacts/benchmarks/sgh_q51/renders/6big_sp0_builderon/render_manifest.json`
- `artifacts/benchmarks/sgh_q51/renders/6big_sp8_builderon/render_manifest.json`
- `artifacts/benchmarks/sgh_q51/renders/full276_builderon/render_manifest.json`
- `artifacts/benchmarks/sgh_q51/renders/full276_builderoff/render_manifest.json`
