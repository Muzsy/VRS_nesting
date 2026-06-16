# SGH-Q49 Codex Checklist

Task: `sgh_q49_density_budget_allocation`
Canvas: `canvases/egyedi_solver/sgh_q49_density_budget_allocation.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q49_density_budget_allocation.yaml`
Branch: `sgh-q49-density-budget-allocation` (stacked on `sgh-q48-...`)

## T1 — Budget reservation

- [x] `VRS_BPP_DENSITY_BUDGET_FRAC` (default 0.35, active only when density on; off ⇒ 0.0)
- [x] reduction loop deadline capped to `total_budget·(1−frac) − guard`
- [x] `density_deadline` stays `total_budget − guard`
- [x] `io.rs` `bpp_reduction_time_ms` + `bpp_density_time_ms`
- [x] `cargo build` + `cargo test` green; off-path unchanged

## T2 — Per-part efficiency

- [x] incremental tracker in `density_compact_sheet` (build once/sweep, update `tracker.shapes[li]`)
- [x] tunable candidate budget `VRS_BPP_DENSITY_SAMPLES` + contour priority + early-exit-no-improve

## T3 — Multi-sweep

- [x] sweep loop until convergence or `density_deadline`
- [x] `io.rs` `bpp_density_sweeps` + `bpp_density_parts_processed`

## T4 — Tests

- [x] budget split honoured; density processes all parts on a small fixture within budget
- [x] `VRS_BPP_DENSITY_COMPACT=0` unchanged; deterministic
- [x] existing suites green (478 lib + 16 + 3 + 2 density)

## T5 — A/B re-benchmark (full276)

- [x] `scripts/bench_sgh_q49_density_budget.py`
- [x] `artifacts/benchmarks/sgh_q49/` (A/B + `q49_summary.json`)
- [x] parts_processed / sweeps / interlock accepted / utilization / used_sheets vs Q48-starved & off

## T6 — Verify + report

- [x] `codex/reports/egyedi_solver/sgh_q49_density_budget_allocation.md`
- [ ] `./scripts/verify.sh --report ...`
