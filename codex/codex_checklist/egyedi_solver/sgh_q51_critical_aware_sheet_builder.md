# SGH-Q51 Codex Checklist

Task: `sgh_q51_critical_aware_sheet_builder`
Canvas: `canvases/egyedi_solver/sgh_q51_critical_aware_sheet_builder.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q51_critical_aware_sheet_builder.yaml`
Branch: `sgh-q51-critical-aware-sheet-builder` (stacked on `sgh-q50-...` / main)

## T1 — Criticality tiers + queues

- [x] criticality tiers from `PartShapeProfile` (critical / structural / filler), deterministic
- [x] critical / structural / filler queues for the builder
- [x] unit tests (classification, determinism); `cargo build` + `cargo test` green

## T2 — Critical admission search (gating R&D core)

- [x] `try_admit_critical`: (1) direct density insertion (admitted fixed); (2) co-movable separation (`separate_sheet_local`) of `{admitted ∪ candidate}` from an overlapping seed (continuous rotation, CDE-valid, budgeted). NOTE: density-biased separation (for tight spacing) = SGH-Q52.
- [x] unit test on a constructed concave-pair fixture
- [x] **measure-gate:** 6×`Lv8_11612` — can admission place 3 big parts on one sheet? (decide before T3)

## T3 — build_critical_aware_seed phased builder

- [x] per sheet: critical admission → structural → filler → seal → next sheet; sheet count emerges
- [x] gated `VRS_SHEET_BUILDER` (off ⇒ current LBF seed)

## T4 — Soft-movable anchors

- [~] DEFERRED to SGH-Q52 (refinement; not needed for v1 safety — the feasibility-gated fallback already guarantees no regression)

## T5 — Decision diagnostics

- [x] `io.rs` per-sheet critical_admitted / deferred, admission attempts/failures, phase-close reasons, sheets_opened

## T6 — Tests

- [x] `tests/sparrow_sheet_builder.rs` (builder on/off; anchor-first; deterministic)
- [x] existing suites green (lib + multisheet + density + shape_profile)

## T7 — A/B benchmark (full276)

- [x] `scripts/bench_sgh_q51_sheet_builder.py`
- [x] `artifacts/benchmarks/sgh_q51/` (A/B + `q51_summary.json`)
- [x] used_sheets / critical-per-sheet / validity; no regression; anchor-first visible

## T8 — Verify + report

- [x] `codex/reports/egyedi_solver/sgh_q51_critical_aware_sheet_builder.md`
- [ ] `./scripts/verify.sh --report ...`
