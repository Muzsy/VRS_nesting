# SGH-Q53 Report - Feature-first critical admission proof

## Verdict: FAIL

## Goal

- Compare Q51/Q52 builder-only control against the Q53 feature-first critical admission arm.
- Prove or disprove that spacing 5 can reach at least 3 `Lv8_11612` parts on one sheet while staying CDE-valid.
- Export diagnostics, raw outputs, and sheet-plan renders in the same artifact shape as Q51/Q52.

## Runs

| run | status | placed | used sheets | util % | max big/sheet | feature cand. | accepted feature pair | critical feature succ. | wall s | acceptance |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |
| feature_off | ok | 6 | 3 | 27.387929881017428 | 2 | 0 | None | 0 | 555.1 | PASS |
| feature_on | ok | 6 | 3 | 27.387929881017428 | 2 | 306 | None | 0 | 555.8 | FAIL_TARGET |

## Acceptance

| check | value |
| --- | --- |
| feature_on_valid | true |
| feature_on_has_3_big_on_a_sheet | false |
| feature_candidates_exercised | true |
| feature_path_evidenced_or_reason_recorded | true |
| feature_off_control_valid | true |

## Diagnostics highlights

- `feature_off` big/sheet: `{'0': 2, '1': 2, '2': 2}` rotations: `{'0': [270.0, 90.0], '1': [281.625, 90.956], '2': [91.162, 90.0]}`
- `feature_on` big/sheet: `{'0': 2, '1': 2, '2': 2}` rotations: `{'0': [270.0, 90.0], '1': [281.625, 90.956], '2': [91.162, 90.0]}`
- `feature_on` refine: seed=`None`, refined=`None`, iterations=`0`
- `feature_on` rejection summary: `seed_not_clear=38`
- `feature_on` phase close reason: `deadline`

## Artifact evidence

- summary: `artifacts/benchmarks/sgh_q53/q53_summary.json`
- outputs: `artifacts/benchmarks/sgh_q53/outputs/`
- logs: `artifacts/benchmarks/sgh_q53/logs/`
- renders: `artifacts/benchmarks/sgh_q53/renders/`

## Render evidence

- `feature_off`: `artifacts/benchmarks/sgh_q53/renders/feature_off/render_manifest.json`
- `feature_on`: `artifacts/benchmarks/sgh_q53/renders/feature_on/render_manifest.json`

## Notes

- PNG generated for all SVG renders: `True`
- Finding: Feature-first critical admission stayed CDE-valid and exercised the feature path (`306` candidates, `14` critical feature attempts), but the 600 s spacing-5 gate still ended at `2` big parts per sheet across `3` sheets, matching the builder-only control.
