# SGH-Q54 Report - Skeleton-aware admission benchmark

## Verdict: PASS

## Goal

- Measure the Q54 skeleton-aware admission path against the builder-only control.
- Prove the spacing-0 `6x Lv8_11612` run still reaches `2` sheets with `3` large parts per sheet.
- Record the honest spacing-5 outcome together with full276 no-regression evidence and renders.

## Runs

| run | status | placed | used sheets | util % | max big/sheet | accepted feature cand. | skeleton roles | wall s | acceptance |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |
| 6big_sp0_skeleton | ok | 6 | 2 | 39.8312 | 3 | 1 | 2 / 1 / 0 | 72.7 | PASS |
| 6big_sp5_builderonly | ok | 6 | 3 | 27.3879 | 2 | 0 | 0 / 0 / 0 | 77.4 | PASS |
| 6big_sp5_skeleton | ok | 6 | 3 | 27.3879 | 2 | 1 | 1 / 1 / 0 | 77.7 | PASS |
| full276_skeleton | ok | 276 | 3 | 54.4152 | 2 | 1 | 1 / 1 / 0 | 292.9 | PASS |
| full276_builderonly | ok | 276 | 3 | 54.4152 | 2 | 0 | 0 / 0 / 0 | 292.9 | PASS |

## Acceptance

| check | value |
| --- | --- |
| proof 2 sheets, 3 big at spacing 0 | true |
| full276 no regression | true |
| stretch 3 big per sheet at spacing 5 | false |

## Finding

Skeleton-aware admission reproduces the spacing-0 proof and now accepts feature-path candidates,
but spacing `5` still tops out at `2` large parts per sheet. The mechanism improvement is real;
the tight `3`-way packing remains open.

## Artifact evidence

- summary: `artifacts/benchmarks/sgh_q54/q54_summary.json`
- inputs: `artifacts/benchmarks/sgh_q54/inputs/`
- outputs: `artifacts/benchmarks/sgh_q54/outputs/`
- logs: `artifacts/benchmarks/sgh_q54/logs/`
- run log: `artifacts/benchmarks/sgh_q54/q54_run.log`

## Render evidence

- `artifacts/benchmarks/sgh_q54/renders/6big_sp0_skeleton/render_manifest.json`
- `artifacts/benchmarks/sgh_q54/renders/6big_sp5_builderonly/render_manifest.json`
- `artifacts/benchmarks/sgh_q54/renders/6big_sp5_skeleton/render_manifest.json`
- `artifacts/benchmarks/sgh_q54/renders/full276_skeleton/render_manifest.json`
- `artifacts/benchmarks/sgh_q54/renders/full276_builderonly/render_manifest.json`
