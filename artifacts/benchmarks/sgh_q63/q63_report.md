# SGH-Q63 Report - Full276 LV8 strict latest-behavior rerun

## Verdict: PASS_WITH_NOTES

## Goal

- Re-run the same Full276 LV8 package used in Q49 with strict latest sheet-builder behavior.
- Strict mode means: no silent native-seed fallback, no builder bootstrap masking, no generic direct shortcut before skeleton-role latest routing.
- Target package: 2 x 1500x3000 mm sheets, margin 5 mm, spacing 5 mm, continuous rotation.

## Runs

| run | status | placed | unplaced | used sheets | util % | critical admitted | pair consulted | slot-edge accepted | wall s | note |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |
| q63_A_strict_latest_q61_2sheet_sp5 | partial | 39 | 237 | 1 | 47.42769561160895 | 2 | True | 0 | 155.2 | strict latest |
| q63_B_masked_q62style_2sheet_sp5 | partial | 258 | 18 | 2 | 49.7442340176186 | 2 | False | 0 | 180.9 | masked q62-style |

## Acceptance

| check | value |
| --- | --- |
| strict mode avoids masked builder fallback path | true |
| strict run no worse placed-count than masked q62-style run | false |
| strict run remains on <= 2 sheets | true |

## Finding

The strict latest-behavior run really exposes the newer role-aware builder path instead of the masked Q62 fallback pattern, but on this Full276 package that honest path currently performs much worse than the masked current run. This benchmark should therefore be read as a visibility/diagnostics rerun, not as a packing-quality win.

## Artifact evidence

- summary: `artifacts/benchmarks/sgh_q63/q63_summary.json`
- input: `artifacts/benchmarks/sgh_q63/inputs/q63_full276_2x1500x3000_margin5_spacing5_continuous_600.json`
- output A: `artifacts/benchmarks/sgh_q63/outputs/q63_A_strict_latest_q61_2sheet_sp5_output.json`
- output B: `artifacts/benchmarks/sgh_q63/outputs/q63_B_masked_q62style_2sheet_sp5_output.json`
- log A: `artifacts/benchmarks/sgh_q63/logs/q63_A_strict_latest_q61_2sheet_sp5.log`
- log B: `artifacts/benchmarks/sgh_q63/logs/q63_B_masked_q62style_2sheet_sp5.log`

## Render evidence

- A manifest: `artifacts/benchmarks/sgh_q63/renders/q63_A_strict_latest_q61_2sheet_sp5/render_manifest.json`
- B manifest: `artifacts/benchmarks/sgh_q63/renders/q63_B_masked_q62style_2sheet_sp5/render_manifest.json`
