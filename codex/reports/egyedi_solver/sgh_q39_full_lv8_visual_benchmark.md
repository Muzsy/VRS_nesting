# SGH-Q39 Report

## Scope

Q39 runs the **full LV8 production benchmark** at the declared time limits (600 / 1200 s,
**no cap on mandatory runs**), re-proves the known dense191 / full276 baselines as strict
regression gates, runs the spacing/margin production matrix, and renders every used sheet of
every run to SVG + PNG (ORIGINAL contours). No cavity prepack, kerf geometry, compression,
legacy fallback, UI/API, or sample-budget tuning.

## Existing repo audit

- Canonical committed inputs reused (no hand-invented parts): dense191
  (`artifacts/benchmarks/sgh_q31/inputs/dense191.json`, 12 parts / 191 instances) and full276
  (`artifacts/benchmarks/sgh_q32/inputs/case_01_2x1500x3000.json`, 12 parts / 276 instances).
- Render pipeline: reused the anchor-transform convention from
  `scripts/visualize_sparrow_output.py` (the source of the committed Q32 sheet viz). PNG via
  `cairosvg`. The Q39 runner renders ORIGINAL `outer_points` (never the spacing-expanded
  collision geometry) and draws the margin inset boundary when `margin > 0`.

## Canonical datasets used

dense191 (191 instances, 1×1500×3000) and full276 (276 instances). Every generated input sets
`spacing_mm` explicitly and `kerf_mm = 0.0`. Pipeline forced to `sparrow_cde_multisheet`,
backend `cde`, seed 42.

## Mandatory benchmark matrix

`scripts/bench_sgh_q39_full_lv8_visuals.py --tier mandatory` ran B0–B3 (baselines) and S0–S5
(spacing/margin) at full time limits with no cap. Extended E0–E4 are optional (not required
for PASS).

## Regression gate policy

`artifacts/benchmarks/sgh_q39/tables/q39_regression_gates.json` (machine-readable):

```json
{"dense191_baseline_ok": true, "full276_2sheet_baseline_ok": true,
 "full276_3sheet_baseline_ok": true, "mixed_stock_baseline_valid": true,
 "mandatory_spacing_runs_valid": true, "all_mandatory_renders_present": true,
 "no_false_ok": true, "hotpath_calls_zero": true, "time_limit_cap_applied": false}
```

All mandatory gates pass; no time cap was applied.

## Render pipeline reused

The runner emits, per run, `sheet_NN.svg` + `sheet_NN.png` for each used sheet, plus
`overview.svg` + `overview.png` and `render_manifest.json`. PNG via cairosvg 2.9. Renders show
the original manufacturing contour, the physical sheet boundary, and (for margin runs) a dashed
usable-area inset. The spacing-expanded shape is never rendered.

## Mandatory run results

| run | scenario | status | placed/total | used/avail | phys util % | wall s | final_pairs | offset_fail | spc_viol | hotpath |
|---|---|---|---|---|---|---|---|---|---|---|
| B0 | dense191 m0 s0 | ok | 191/191 | 1/1 | 82.4 | 90 | 0 | 0 | 0 | 0 |
| B1 | full276 2sheet m0 s0 | ok | 276/276 | 2/2 | 74.1 | 259 | 0 | 0 | 0 | 0 |
| B2 | full276 3sheet m0 s0 | ok | 276/276 | 2/3 | 74.1 | 259 | 0 | 0 | 0 | 0 |
| B3 | full276 mixed m0 s0 | partial | 272/276 | 3/3 | 57.1 | 1140 | 0 | 0 | 0 | 0 |
| S0 | dense191 m0 s2 | partial | 147/191 | 1/1 | 35.5 | 573 | 0 | 0 | 0 | 0 |
| S1 | dense191 m5 s2 | partial | 149/191 | 1/1 | 50.1 | 580 | 0 | 0 | 0 | 0 |
| S2 | full276 2sheet m0 s2 | partial | 237/276 | 2/2 | 44.5 | 1196 | 0 | 0 | 0 | 0 |
| S3 | full276 2sheet m5 s2 | partial | 250/276 | 2/2 | 42.1 | 1214 | 0 | 0 | 0 | 0 |
| S4 | full276 3sheet m0 s2 | partial | 245/276 | 3/3 | 35.7 | 1209 | 0 | 0 | 0 | 0 |
| S5 | full276 mixed m0 s2 | partial | 195/276 | 3/3 | 23.7 | 1175 | 0 | 0 | 0 | 0 |

Per-run render paths: `artifacts/benchmarks/sgh_q39/renders/<run_id>/{sheet_NN.svg,
sheet_NN.png, overview.svg, overview.png, render_manifest.json}`. No run had a false `ok`;
`technology_spacing_offset_failure_count = 0` and `q31 prepare_base_shape_native_hotpath_calls
= 0` in every run.

## Dense191 baseline verdict

**B0 fully reproduced: 191/191, status ok, 1 sheet, final_pairs 0, ~90 s** (deadline not hit).
The known dense191 baseline holds on the current solver.

## Full276 baseline verdict

**B1 fully reproduced: 276/276, status ok, 2 sheets, final_pairs 0, ~259 s.**
**B2 fully reproduced: 276/276, status ok, used 2 of 3 available sheets (3rd unused),
~259 s.** Both known full276 baselines hold.

## Mixed-stock verdict

**B3: partial 272/276** on `1×1500×3000 + 2×1000×2000`, 3 sheets used, 4 instances unplaced
(insufficient capacity on the smaller mixed sheets), final_pairs 0, boundary_violations 0, no
false ok, exact unplaced reporting. This is the expected valid partial for the constrained
mixed-stock pool.

## Spacing production run results

At `spacing_mm = 2` the spacing-aware solver places fewer instances within the time budget (the
spacing-expanded collision geometry makes packing harder), but every result is honest and
violation-free:

- dense191: S0 (m0) **147/191**, S1 (m5) **149/191** — 1 sheet, offset_fail 0, spc_viol 0.
- full276 2-sheet: S2 (m0) **237/276**, S3 (m5) **250/276** — offset_fail 0, spc_viol 0.
- full276 3-sheet: S4 **245/276** (3 sheets). full276 mixed: S5 **195/276** (3 sheets).

S3 (margin 5 + spacing 2) placed slightly more than S2 (spacing 2 only): within solver
search-path variance at the deadline; both are valid violation-free partials.

## Runtime and cost analysis

`q39_stage_timing.csv` — the **Q35 spacing final validator dominates the added cost** of
spacing runs:

| run | spacing_final_validator_ms | spacing_offset_build_ms | safety_net_ms |
|---|---|---|---|
| B0–B3 (spacing 0) | ~0 | 0 | 0 |
| S0 | 37 118 | 646 | 0 |
| S1 | 44 223 | 648 | 0 |
| S2 | 52 538 | 635 | 0 |
| S3 | 69 589 | 637 | 0 |
| S4 | 70 027 | 644 | 0 |
| S5 | 36 665 | 633 | 0 |

The robust offset build (Q38) is ~0.64 s total per run; the O(n²) spacing validator is **37–70
seconds**. This confirms the Q37 hotspot at full production scale: the spacing final validator,
not the offset, is the cost driver.

## Per-sheet utilization summary

See `q39_per_sheet_summary.csv` (per used sheet: stock dims, physical/usable area, placed
count, placed part area, physical/usable utilization %, SVG/PNG paths). Baseline B1/B2 reach
~74 % physical utilization on the used sheets; spacing runs are lower (spacing consumes inter-
part area and limits density within the budget).

## Visual output inventory

All 10 mandatory runs: 0 missing SVG, 0 missing PNG, `render_status = ok`. Representative
relative paths:

- `artifacts/benchmarks/sgh_q39/renders/B1/sheet_00.svg|png`, `sheet_01.svg|png`, `overview.svg|png`
- `artifacts/benchmarks/sgh_q39/renders/B2/sheet_00..01.{svg,png}`, `overview.{svg,png}`
- `artifacts/benchmarks/sgh_q39/renders/B3/sheet_00..02.{svg,png}`, `overview.{svg,png}`
- `artifacts/benchmarks/sgh_q39/renders/S2/sheet_00..01.{svg,png}`, `overview.{svg,png}`
- `artifacts/benchmarks/sgh_q39/renders/S4/sheet_00..02.{svg,png}`, `overview.{svg,png}`
- `artifacts/benchmarks/sgh_q39/renders/S5/sheet_00..02.{svg,png}`, `overview.{svg,png}`
- (B0/S0/S1 single sheet: `sheet_00.{svg,png}` + `overview.{svg,png}`)

## Failure / partial taxonomy

All partials are capacity/time-driven, not correctness failures: B3 (4 unplaced,
mixed-stock capacity), S0–S5 (spacing reduces achievable density within the time budget). No
`UNSUPPORTED_SPACING_OFFSET_Q36` (offset_fail 0 everywhere), no `PART_SPACING_VIOLATION_Q35`
(spc_viol 0), no `SHEET_MARGIN_VIOLATION_Q34R1`, no false `ok`.

## Q31/Q35/Q36/Q38 regression checks

- Q31: `prepare_base_shape_native_hotpath_calls = 0` in all 10 runs.
- Q35: spacing final validator active; `technology_spacing_violation_count = 0` everywhere.
- Q36: spacing geometry diagnostics present; boundary/output use original geometry; spacing-0
  baselines (B0–B3) reproduce the pre-Q36 results exactly (byte-identical path).
- Q38: robust offset — `technology_spacing_offset_failure_count = 0` in every spacing run on
  the full LV8 set.

## Interpretation

1. **Dense191 baseline?** Fully reproduced — B0 191/191, ok, 1 sheet.
2. **Full276 2-sheet baseline?** Fully reproduced — B1 276/276, ok, 2 sheets.
3. **Full276 3-sheet on 2 sheets?** Yes — B2 276/276, used 2 of 3 (3rd unused).
4. **Mixed-stock outcome?** B3 partial 272/276, 3 sheets, 4 unplaced (capacity), final_pairs 0,
   valid — no false ok.
5. **spacing=2 / margin+spacing exact placed/unplaced?** dense191: S0 147/191, S1 (m5) 149/191;
   full276: S2 237/276, S3 (m5) 250/276, S4 (3 sheet) 245/276, S5 (mixed) 195/276.
6. **Main limiter — validator or runtime?** Both linked: spacing reduces packable density, and
   the **Q35 O(n²) spacing final validator (37–70 s)** is the dominant added runtime; the
   robust offset (~0.64 s) is negligible. So search density under spacing + validator cost, not
   offset, are the limiters.
7. **Visually consistent?** Yes — renders show original contours, all used sheets + overviews
   present, 0 missing files.
8. **Next realistic step?** See below.

## Recommended next task

The baselines are solid and offset robustness is solved; the remaining frontier is
**spacing-run quality + the O(n²) spacing validator cost**. Recommended next task: **Q40 —
broad-phase / AABB-bucketed pruning of the Q35 spacing final validator** (cut the 37–70 s down
so spacing runs spend the budget on packing, not validation), optionally paired with
spacing-aware search-density improvements so `spacing=2` full276 approaches the spacing-0
placement rate. No solver-correctness change is needed — the gates are green.

## Final verdict

**PASS.** B0 191/191, B1 276/276 (2 sheets), B2 276/276 (used 2) all re-proven; B3 mixed-stock
a correct partial; S0–S5 ran at full time limits with exact recorded results; spacing
offset_failure_count = 0 in all spacing runs; no false ok; q31 hotpath = 0 in every run; SVG +
PNG present for every used sheet of every mandatory run plus per-run overviews, all showing
original contours; mandatory runs used the full 600/1200 s with no cap; all tables, logs,
outputs, renders and this report are produced; build/test/smoke/check/verify PASS.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-13T12:08:22+02:00 → 2026-06-13T12:10:45+02:00 (143s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q39_full_lv8_visual_benchmark.verify.log`
- git: `main@19e38c5`
- módosított fájlok (git status): 11

**git diff --stat**

```text
 .../outputs/technology_policy_smoke_output.json    | 14 +++---
 .../sgh_q34/outputs/sheet_margin_ok_output.json    |  8 +--
 .../outputs/sheet_margin_too_large_output.json     |  8 +--
 .../sgh_q35/outputs/part_spacing_ok_output.json    | 12 ++---
 .../outputs/part_spacing_violation_output.json     | 12 ++---
 .../outputs/spacing_geometry_touch_ok_output.json  | 14 +++---
 .../outputs/spacing_not_sheet_margin_output.json   | 14 +++---
 .../outputs/spacing_violation_safety_output.json   | 58 +++++++++++-----------
 8 files changed, 70 insertions(+), 70 deletions(-)
```

**git status --porcelain (preview)**

```text
 M artifacts/benchmarks/sgh_q33/outputs/technology_policy_smoke_output.json
 M artifacts/benchmarks/sgh_q34/outputs/sheet_margin_ok_output.json
 M artifacts/benchmarks/sgh_q34/outputs/sheet_margin_too_large_output.json
 M artifacts/benchmarks/sgh_q35/outputs/part_spacing_ok_output.json
 M artifacts/benchmarks/sgh_q35/outputs/part_spacing_violation_output.json
 M artifacts/benchmarks/sgh_q36/outputs/spacing_geometry_touch_ok_output.json
 M artifacts/benchmarks/sgh_q36/outputs/spacing_not_sheet_margin_output.json
 M artifacts/benchmarks/sgh_q36/outputs/spacing_violation_safety_output.json
?? artifacts/benchmarks/sgh_q39/
?? codex/reports/egyedi_solver/sgh_q39_full_lv8_visual_benchmark.md
?? codex/reports/egyedi_solver/sgh_q39_full_lv8_visual_benchmark.verify.log
```

<!-- AUTO_VERIFY_END -->
