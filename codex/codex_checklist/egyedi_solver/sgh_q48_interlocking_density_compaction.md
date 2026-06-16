# SGH-Q48 Codex Checklist

Task: `sgh_q48_interlocking_density_compaction`
Canvas: `canvases/egyedi_solver/sgh_q48_interlocking_density_compaction.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q48_interlocking_density_compaction.yaml`
Branch: `sgh-q48-interlocking-density-compaction` (stacked on `sgh-q47-...`)

## T1 — DensityEvaluator + density-score

- [x] `optimizer/sparrow/density.rs` (new): `density_candidate_score` + `DensityEvaluator`
- [x] `mod.rs` declares `pub mod density;`
- [x] unit tests: in-concavity placement scores better than separated; deterministic
- [x] continuous rotation untouched; CDE untouched
- [x] `cargo build` + `cargo test` green

## T2 — Interlock decision-diagnostics

- [x] `io.rs` `bpp_interlock_candidates_generated/accepted` (+ per-anchor)
- [x] `bpp_reduction.rs` instrumentation

## T3 — Density-aware sampling

- [x] contour-near sampling in `density.rs::contour_near_rect_mins` (kept out of the shared `uniform_sampler` to avoid perturbing the separator hot path; NFP-free, continuous preserved)

## T4 — Density-compaction pass (replaces y-only compact_sheet)

- [x] `bpp_reduction.rs` density-improving accept (translation + continuous rotation)
- [x] gate `VRS_BPP_DENSITY_COMPACT` (default off)

## T5 — Continuous-rotation seed correctness

- [x] `fixed_sheet.rs` `fitting_rotation` honours `continuous_rotation` (continuous seed, no snapping)

## T6 — Tests

- [x] `tests/sparrow_density_compaction.rs` (unit + integration)
- [x] existing `sparrow_finite_stock_multisheet.rs` (16) + `sparrow_shape_profile.rs` (3) green

## T7 — A/B regression + decision-diagnostic benchmark

- [x] `scripts/bench_sgh_q48_density_compaction.py`
- [x] `artifacts/benchmarks/sgh_q48/` (A/B + `q48_summary.json`)
- [x] no sheet/util regression; interlock candidates generated (diagnostics)

## T8 — Verify + report

- [x] `codex/reports/egyedi_solver/sgh_q48_interlocking_density_compaction.md`
- [ ] `./scripts/verify.sh --report ...`
