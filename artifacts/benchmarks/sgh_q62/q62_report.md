# SGH-Q62 Report - Full276 LV8 spacing-5 / 2-sheet rerun

## Verdict: FAIL

## Goal

- Re-run the same Full276 LV8 package used in Q49 with the current Q61-wired solver behavior.
- Target: place all 276 parts onto 2 x 1500x3000 mm sheets with margin 5 mm and spacing 5 mm.
- Save Q49-shaped benchmark artifacts: input, raw outputs, logs, summary, report, and renders.

## Runs

| run | status | placed | unplaced | used sheets | util % | final pairs | max critical/sheet | feature accepted | pair generated | wall s | acceptance |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| q62_A_current_q61_2sheet_sp5 | partial | 259 | 17 | 2 | 49.96641349141249 | 0 | 2 | 2 | 0 | 181.3 | FAIL |
| q62_B_builderonly_2sheet_sp5 | partial | 252 | 24 | 2 | 40.48378391770911 | 0 | 2 | 0 | 0 | 179.9 | FAIL |

## Acceptance

| check | value |
| --- | --- |
| current solver full valid 276 | false |
| current solver reached <= 2 sheets | false |
| baseline valid | false |
| current solver no worse placed-count than baseline | true |

## Finding

The current Q61-wired solver did not reach the requested 2-sheet full-valid target on the Q49 full276 LV8 package at spacing 5 / margin 5. The saved diagnostics capture the actual placed-count, used-sheet count, and Q61 critical-admission counters.

## Artifact evidence

- summary: `artifacts/benchmarks/sgh_q62/q62_summary.json`
- input: `artifacts/benchmarks/sgh_q62/inputs/q62_full276_2x1500x3000_margin5_spacing5_continuous_600.json`
- output A: `artifacts/benchmarks/sgh_q62/outputs/q62_A_current_q61_2sheet_sp5_output.json`
- output B: `artifacts/benchmarks/sgh_q62/outputs/q62_B_builderonly_2sheet_sp5_output.json`
- log A: `artifacts/benchmarks/sgh_q62/logs/q62_A_current_q61_2sheet_sp5.log`
- log B: `artifacts/benchmarks/sgh_q62/logs/q62_B_builderonly_2sheet_sp5.log`

## Render evidence

- A manifest: `artifacts/benchmarks/sgh_q62/renders/q62_A_current_q61_2sheet_sp5/render_manifest.json`
- B manifest: `artifacts/benchmarks/sgh_q62/renders/q62_B_builderonly_2sheet_sp5/render_manifest.json`
