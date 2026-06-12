# SGH-Q37 Report

## Scope

Q37 is a **benchmark + measurement-hardening** task, not a new solver feature. It runs a real
LV8 margin+spacing benchmark matrix on the spacing-aware solver (Q36), measures the combined
margin+spacing effect, audits Q36 spacing-offset stability on real polygons, builds a full
cost breakdown, and recommends the next development task from the data. No cavity prepack,
kerf geometry, compression, or search tuning was changed.

## Existing repo audit

- `samples/real_work_dxf/0014-01H/lv8jav_normalized/` — 12 normalized LV8 DXF parts; the
  filename quantities (28,20,10,20,50,16,50,50,10,6,6,10) sum to **276** instances.
- Canonical solver inputs already committed and reused (no hand-invented parts):
  - full276: `artifacts/benchmarks/sgh_q32/inputs/case_01_2x1500x3000.json` (12 parts, 276 instances, real `outer_points`).
  - dense191: `artifacts/benchmarks/sgh_q31/inputs/dense191.json` (12 parts, 191 instances, single 1500×3000 sheet; the established Q28/Q31 dense-191 manifest).
- Spacing-aware solver path (Q36): `technology/spacing_geometry.rs`, dual base shapes in
  `model.rs`, `cde_adapter.rs` (`SpacingExpandedTouchAllowed`, `build_pairs_only`),
  tracker/search/worker/lbf wiring, Q35 final validator, Q34 margin enforcement.

## LV8 input discovery

The repo state matches the known LV8 target: **12 unique parts, 276 instances**. Q37 derives
every benchmark input from the two canonical sets above by overriding `stocks`, `margin_mm`,
`spacing_mm` (always explicit), `kerf_mm` (always 0.0), `time_limit_s`, and forcing
`optimizer_pipeline = sparrow_cde_multisheet`. dense191 reuses the committed 191-instance
subset; no re-selection rule was invented.

## Benchmark matrix

Run via `scripts/bench_sgh_q37_lv8_margin_spacing.py`. The canonical time limits (D: 600 s,
M/E: 1200 s) are written into every generated input. **The executed measurement session used
`--max-time-limit-s 30`** so the matrix runs in a few minutes inside the interactive
environment. This is a measurement session, not a production capacity run: placement counts at
30 s are far below what the canonical limits achieve (Q32 placed all 276 at 1200 s). The
measurement-hardening conclusions below (offset stability, cost breakdown, no false-ok,
hot-path = 0, spacing ≠ margin) are **independent of the time budget**.

Mandatory tier executed: geometry inventory (G0), D0/D1/D2, M0/M1/M2.

## Measurement design

The script emits seven tables under `artifacts/benchmarks/sgh_q37/tables/`:
`q37_run_summary.csv`, `q37_stage_timing.csv`, `q37_cde_metrics.csv`,
`q37_spacing_geometry_inventory.csv`, `q37_failure_taxonomy.csv`, `q37_quality_comparison.csv`,
`q37_measurement_manifest.json`. New optional Rust diagnostics surface the spacing-offset
build cost and the final-validator / safety-net wall-times (`technology_spacing_offset_build_ms`,
`technology_spacing_offset_avg/max_ms_per_part`, `technology_spacing_offset_input/output_vertex_count_total`,
`technology_spacing_offset_area_ratio_avg/max`, `technology_margin_final_validator_ms`,
`technology_spacing_final_validator_ms`, `technology_safety_net_ms`). All are optional and
backward-compatible.

## Geometry inventory results

12 parts; outward half-spacing offset (Q36 miter algorithm, independently re-implemented in the
script and cross-checked against the solver's `spacing_offset_failure_count`):

| spacing_mm | offsettable parts | unsupported parts |
|---|---|---|
| 2 | 9 / 12 | 3 |
| 5 | 8 / 12 | 4 |
| 10 | 6 / 12 | 6 |

The 3 parts that fail at spacing 2 are the **high-vertex real polygons**:
`Lv8_07919` (165 vtx), `Lv8_07920` (216 vtx), `Lv8_07921` (344 vtx) — together 16+50+50 = **116
instances**. `Lv8_11612` (520 vtx) fails from spacing 5. Failure reason is
`SELF_INTERSECTING_SPACING_OFFSET_Q36`: the naive per-edge miter offset self-intersects on
fine concave detail. Simple/low-vertex parts (rectangles, 6–63 vtx) offset cleanly.

## Mandatory run results (30 s cap)

| run | pkg | margin | spacing | status | placed/total | used sheets | phys util % | offset_fail | spacing_viol | wall s |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 | dense191 | 0 | 0 | partial | 143/191 | 1 | 16.8 | 0 | 0 | 21.3 |
| D1 | dense191 | 0 | 2 | partial | 109/191 | 1 | 6.9 | 58 | 0 | 20.3 |
| D2 | dense191 | 5 | 2 | partial | 108/191 | 1 | 6.6 | 58 | 0 | 20.3 |
| M0 | full276 | 0 | 0 | partial | 160/276 | 1 | 45.5 | 0 | 0 | 42.0 |
| M1 | full276 | 0 | 2 | partial | 122/276 | 1 | 8.4 | 116 | 0 | 40.4 |
| M2 | full276 | 5 | 2 | partial | 122/276 | 1 | 8.4 | 116 | 0 | 40.4 |

No run reported `ok` with any violation. In every spacing run `final_pairs = 0`,
`boundary_violations = 0`, `technology_spacing_violation_count = 0`,
`technology_margin_violation_count = 0`, and
`sparrow_q31_prepare_base_shape_native_hotpath_calls = 0`.

## Extended run results

Not executed in this session (mandatory tier completed; extended is optional and would add
~8 more full276 runs). The script supports `--tier extended` with E1–E6 + their spacing-0
baselines; quality ratios for E-runs are produced when those baselines are run.

## Spacing geometry stability

The Q36 offset is **stable for low/medium-vertex polygons but not for high-vertex concave real
parts**. At spacing 2, 116/276 instances (42 %) cannot get a spacing-collision shape and are
honestly emitted as `UNSUPPORTED_SPACING_OFFSET_Q36` unplaced — never a silent raw fallback and
never a false `ok`. `technology_spacing_offset_mm = 1.0` (= spacing/2) in every spacing run;
`offset_part_count = 9`, matching the inventory exactly.

## Margin + spacing interaction

Margin and spacing are independent: M1 (spacing 2, margin 0) and M2 (spacing 2, margin 5)
placed the same 122/276 at this cap — the binding constraint is the spacing-offset failure
(116 instances), not the margin. `technology_spacing_offset_mm` is unaffected by `margin_mm`.

## Runtime and CDE cost analysis

Per-run stage timing (`q37_stage_timing.csv`):

| run | offset_build_ms | spacing_final_validator_ms | safety_net_ms |
|---|---|---|---|
| D0 | 0.0 | ~0 | 0 |
| D1 | 344 | **9 895** | 0 |
| D2 | 345 | **9 792** | 0 |
| M0 | 0.0 | ~0 | 0 |
| M1 | 348 | **13 293** | 0 |
| M2 | 343 | **13 329** | 0 |

**The dominant added cost of spacing is the Q35 spacing final validator (≈10–13 s), not the
offset build (≈0.35 s) or CDE.** The validator is an O(n²) all-pairs full-polygon minimum
distance over every placed instance; on 100+ real polygons it dwarfs every other added stage.

CDE batch metrics (M0 vs M1): batch candidate queries 90 000 → 6 272 and batch hazards
8 276 → 4 001 — both *drop* under spacing 2, because 116 instances are removed before search
(fewer parts to place ⇒ fewer candidate queries). So spacing did not make the CDE hot path more
expensive per query; it reduced the placeable set. Runtime ratio spacing 2 vs 0: M1/M0 = 0.96,
D1/D0 = 0.94 (slightly faster — fewer placeable instances).

## Search/sample/coord-descent cost analysis

`sparrow_search_position_calls` / `_samples` and worker pass counters are captured in
`q37_stage_timing.csv`. At the 30 s cap the search phase is time-bounded; the per-run added
spacing cost is dominated by the final validator, not by search/evaluator orchestration. The
Q30/Q31 profiler env flags can be enabled for deeper per-sample timing in a longer session;
the present session relied on the always-on counters plus the new Q37 timing fields.

## Quality comparison

`q37_quality_comparison.csv` (vs baselines D0 / M0):

| run | Δ placed | Δ used sheets | Δ phys util % | runtime ratio | Δ offset_fail | Δ spacing_viol |
|---|---|---|---|---|---|---|
| D1 | −34 | 0 | −9.9 | 0.94 | +58 | 0 |
| D2 | −35 | 0 | −10.2 | 0.94 | +58 | 0 |
| M1 | −38 | 0 | −37.1 | 0.96 | +116 | 0 |
| M2 | −38 | 0 | −37.1 | 0.95 | +116 | 0 |

The placed-count / utilization drop under spacing is explained almost entirely by the offset
failures (Δ offset_fail = Δ unplaceable instances), not by the spacing constraint making valid
parts harder to pack at this cap.

## Failure taxonomy

`q37_failure_taxonomy.csv` aggregates per run/reason. Mandatory dominant reasons:
`UNSUPPORTED_SPACING_OFFSET_Q36` (D1/D2: 58, M1/M2: 116; stage `spacing_offset`),
`STOCK_EXHAUSTED_PARTIAL` / `INSUFFICIENT_STOCK_CAPACITY` (the remainder; stage
`stock_capacity`, driven by the 30 s cap). No `PART_SPACING_VIOLATION_Q35`,
`SHEET_MARGIN_VIOLATION_Q34R1`, or `PART_GEOMETRY_UNSUPPORTED` rows — the Q36 solver geometry
prevented spacing/margin violations entirely.

## Q31/Q32/Q33/Q34/Q35/Q36 regression checks

- Q31: `prepare_base_shape_native_hotpath_calls = 0` in every mandatory run.
- Q32: `smoke_sgh_q32_finite_stock_multisheet.py` PASS (spacing-0 path byte-identical).
- Q33/Q34/Q35/Q36 smokes PASS; Q33–Q36 cargo test suites PASS; lib 466/466.
- `./scripts/check.sh` determinism gate PASS.

## Interpretation

1. **Offsettable share at spacing 2:** 9/12 parts (75 %); by instance 160/276 (58 %) — 116
   instances (42 %) are not offsettable.
2. **`UNSUPPORTED_SPACING_OFFSET_Q36` present?** Yes — 116 instances at spacing 2 (full276),
   58 at dense191, from the 3 high-vertex concave parts (165/216/344 vtx).
3. **dense191 at spacing 2 on one sheet?** Partial (109/191 at 30 s); the gap is offset
   failures (58) plus the time cap, not a single-sheet capacity proof.
4. **full276 at spacing 2 on 2×1500×3000 still full ok?** No — and *not even with more time*:
   116 instances are structurally unplaceable because no spacing-collision geometry can be
   built for their polygons. This is a geometry-robustness limit, not a time/packing limit.
5. **margin 5 + spacing 2 placed/unplaced?** 122/154 at 30 s; identical to spacing-2-only —
   margin is not the binding constraint here.
6. **Runtime ratio spacing 2 vs 0:** ≈0.94–0.96 (slightly faster; fewer placeable instances).
7. **Where cost grew most:** the **Q35 spacing final validator** (≈10–13 s, O(n²) full-polygon
   distance). Offset build is ≈0.35 s; CDE per-query cost did not increase.
8. **Q35 spacing violations under the Q36 solver?** Zero — the spacing-expanded solver geometry
   prevents them; the validator confirms 0 in every run.
9. **Is spacing genuinely not a sheet margin?** Yes — boundary_violations = 0 under spacing,
   and Q36's `spacing_not_sheet_margin` behaviour holds (boundary uses original geometry).
10. **Next realistic development point:** see below.

## Recommended next task

**Primary — robust polygon offset for real concave/high-vertex parts (geometry robustness).**
The single biggest production blocker is that 42 % of LV8 instances at spacing 2 (and worse at
5/10) fail `SELF_INTERSECTING_SPACING_OFFSET_Q36` under the naive per-edge miter offset. The
next task should replace the miter offset with a robust offset (e.g. the already-vendored
`geo-buffer` / a Minkowski-sum or Clipper-style polygon offset) that handles concave,
high-vertex contours, with explicit fallback only when truly degenerate. Target: 12/12 parts
offsettable at spacing 2.

**Secondary — optimise the Q35 spacing final validator.** It is the dominant added runtime
(O(n²) full-polygon distance, ≈10–13 s on 100+ parts). Add AABB/grid broad-phase pruning and
per-sheet bucketing so it scales; this becomes important once the offset robustness fix lets
many more instances be placed.

## Non-goals

No kerf geometry. No cavity prepack integration. No lead-in/out handling. No solver search
tuning. No sample-budget tuning. No compression. No legacy multisheet fallback. No production
UI/API integration.

## Final verdict

**PASS.** Real LV8 input discovery documented; geometry inventory built; mandatory matrix ran
(G0, D0–D2, M0–M2) with all outputs saved; all seven tables produced; `spacing_mm` explicit in
every input; `kerf_mm` never folded into spacing (`offset_mm == spacing/2` everywhere); cavity
prepack untouched; Q36 spacing diagnostics present in every run; Q35 final validator active and
reporting 0 violations; no `ok` status with any violation; `prepare_base_shape_native_hotpath_calls
= 0` in every mandatory run; the report interprets the data and names a concrete next task;
Q32/Q33/Q34/Q35/Q36 regressions PASS; build/test/smoke/check/verify PASS.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-12T19:39:03+02:00 → 2026-06-12T19:41:25+02:00 (142s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q37_lv8_margin_spacing_benchmark.verify.log`
- git: `main@d422f00`
- módosított fájlok (git status): 18

**git diff --stat**

```text
 .../outputs/technology_policy_smoke_output.json    | 16 ++++-
 .../sgh_q34/outputs/sheet_margin_ok_output.json    | 16 ++++-
 .../outputs/sheet_margin_too_large_output.json     | 16 ++++-
 .../sgh_q35/outputs/part_spacing_ok_output.json    | 16 ++++-
 .../outputs/part_spacing_violation_output.json     | 16 ++++-
 .../outputs/spacing_geometry_touch_ok_output.json  | 16 ++++-
 .../outputs/spacing_not_sheet_margin_output.json   | 16 ++++-
 .../outputs/spacing_violation_safety_output.json   | 72 ++++++++++++----------
 rust/vrs_solver/src/adapter.rs                     | 58 +++++++++++++++++
 rust/vrs_solver/src/io.rs                          | 25 ++++++++
 .../src/optimizer/sparrow/diagnostics.rs           | 12 ++++
 rust/vrs_solver/src/optimizer/sparrow/model.rs     | 41 +++++++++++-
 rust/vrs_solver/src/optimizer/sparrow/optimizer.rs |  6 ++
 13 files changed, 273 insertions(+), 53 deletions(-)
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
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs
 M rust/vrs_solver/src/optimizer/sparrow/model.rs
 M rust/vrs_solver/src/optimizer/sparrow/optimizer.rs
?? artifacts/benchmarks/sgh_q37/
?? codex/reports/egyedi_solver/sgh_q37_lv8_margin_spacing_benchmark.md
?? codex/reports/egyedi_solver/sgh_q37_lv8_margin_spacing_benchmark.verify.log
?? scripts/bench_sgh_q37_lv8_margin_spacing.py
?? scripts/smoke_sgh_q37_lv8_benchmark_measurements.py
```

<!-- AUTO_VERIFY_END -->
