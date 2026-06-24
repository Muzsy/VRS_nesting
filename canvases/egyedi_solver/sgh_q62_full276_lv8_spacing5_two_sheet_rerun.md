# SGH-Q62 — Full276 LV8 spacing-5 / 2-sheet rerun with current Q61 solver behavior

## Goal

Re-run the same Full276 LV8 package used by SGH-Q49 with the current Q61-wired solver behavior on a
hard target configuration:

- `276` parts
- `2 x 1500x3000 mm` sheets only
- `margin = 5 mm`
- `spacing = 5 mm`
- `rotation_policy = continuous`

Save the outputs into a new benchmark directory under `artifacts/benchmarks/`, in the same artifact
shape as Q49: input, raw outputs, per-run logs, summary, top-level benchmark report, and SVG/PNG
sheet-plan renders with manifests.

## Non-goals

- Do not modify solver logic in this task.
- Do not change any Q61 gate behavior.
- Do not claim success if the solver does not actually reach 2 sheets / 276 placed.

## Inputs / references

- Q49 benchmark package and report:
  - `artifacts/benchmarks/sgh_q49/inputs/q49_full276_6x1500x3000_margin5_spacing8_continuous_300.json`
  - `artifacts/benchmarks/sgh_q49/q49_report.md`
- Current solver behavior:
  - `artifacts/benchmarks/sgh_q61/SOLVER_CURRENT_BEHAVIOR.md`
- User-provided external reference PDF:
  - `samples/real_work_dxf/0014-01H/lv8jav/Nested/project_2447207_report.pdf`

## Deliverables

- New task artifacts:
  - `canvases/egyedi_solver/sgh_q62_full276_lv8_spacing5_two_sheet_rerun.md`
  - `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q62_full276_lv8_spacing5_two_sheet_rerun.yaml`
  - `codex/codex_checklist/egyedi_solver/sgh_q62_full276_lv8_spacing5_two_sheet_rerun.md`
  - `codex/reports/egyedi_solver/sgh_q62_full276_lv8_spacing5_two_sheet_rerun.md`
- Benchmark runner:
  - `scripts/bench_sgh_q62_full276_spacing5_two_sheet.py`
- Benchmark artifacts:
  - `artifacts/benchmarks/sgh_q62/inputs/`
  - `artifacts/benchmarks/sgh_q62/outputs/`
  - `artifacts/benchmarks/sgh_q62/logs/`
  - `artifacts/benchmarks/sgh_q62/renders/`
  - `artifacts/benchmarks/sgh_q62/q62_summary.json`
  - `artifacts/benchmarks/sgh_q62/q62_report.md`

## Execution shape

- Run A: current Q61 solver behavior with the documented production-wiring gates enabled.
- Run B: builder-only baseline on the same 2-sheet / spacing-5 input.
- Render both runs with the existing benchmark render helper style.

## Acceptance

- The benchmark rerun completes and artifacts are saved in a new benchmark directory.
- The report clearly states whether the target was achieved:
  - `status == ok`
  - `placed_count == 276`
  - `used_sheets <= 2`
  - `0` final pairs / `0` boundary violations
- If the target is not reached, the report still captures the real outcome and relevant Q61 diagnostics.

## Risks / rollback

- Risk: long runtime due to the hard 2-sheet target.
- Risk: solver may legitimately fail to achieve the target with the current algorithmic gap.
- Rollback: none needed for solver code; this task only adds benchmark/docs artifacts.
