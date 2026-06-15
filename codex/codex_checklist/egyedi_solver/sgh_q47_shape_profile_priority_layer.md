# SGH-Q47 Codex Checklist

Task: `sgh_q47_shape_profile_priority_layer`
Canvas: `canvases/egyedi_solver/sgh_q47_shape_profile_priority_layer.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q47_shape_profile_priority_layer.yaml`

## T1 — PartShapeProfile module + per-type compute

- [x] `rust/vrs_solver/src/optimizer/sparrow/shape_profile.rs` (struct + `compute`)
- [x] `mod.rs` declares `pub mod shape_profile;`
- [x] `model.rs` per-unique-part profile cache + `SPInstance.shape_profile: Rc<PartShapeProfile>`
- [x] `cargo build` green; `cargo test` green (467 lib + 16 multisheet)
- [x] deterministic compute (same input → same profile) — unit test
- [x] continuous rotation untouched (no rotation/sampler code in diff)

## T2 — Decision diagnostics

- [x] `io.rs` `ShapeProfileDiagnostics` + `OptimizerDiagnosticsOutput.shape_profiles`
- [x] `multisheet.rs` `FiniteStockRunResult.shape_profile_diagnostics` + `adapter.rs` wiring
- [x] `shape_profile::build_shape_profile_diagnostics` (per-type, priority_rank order)

## T3 — Profile-aware ordering

- [x] `lbf.rs` `order()` primary = `priority_score`, tie-break hull×diameter + instance_id
- [x] `bpp_reduction.rs` displaced/compact/pick_large sorts use `profile_order_key`
- [x] `VRS_SHAPE_PROFILE=0` reproduces pre-Q47 ordering (priority 0.0 ⇒ legacy keys)

## T4 — Profile-aware placement budget (implemented + measured)

- [x] `bpp_reduction.rs` `search_placement_on_sheet` deadline × `search_budget_multiplier` (base 2.0 s, clamp [0.8 s, 6.0 s]); `VRS_SHAPE_PROFILE=0` ⇒ flat 2.0 s
- [x] re-measured A/B: outcome-neutral on full276 (A==B), kept as Q48 substrate (report §7)

## T5 — Tests

- [x] `shape_profile.rs` unit tests (7): determinism, rectangle/slender/tiny/large-concave classification, anchor>tiny priority, gate
- [x] `tests/sparrow_shape_profile.rs` (3): shape_profiles emitted, anchor outranks tiny end-to-end, collision feasibility preserved
- [x] `tests/sparrow_finite_stock_multisheet.rs` still green (16)

## T6 — A/B regression benchmark

- [x] `scripts/bench_sgh_q47_shape_profile_full276.py`
- [x] `artifacts/benchmarks/sgh_q47/` (A/B outputs + `q47_summary.json`) — verdict PASS
- [x] no sheet-count regression vs `VRS_SHAPE_PROFILE=0` (both 3 sheets); priority change visible (anchors before fillers)
- [x] honest finding: ordering+budget outcome-neutral on full276 (A==B) ⇒ density lever = SGH-Q48

## T7 — Verify + report

- [x] `codex/reports/egyedi_solver/sgh_q47_shape_profile_priority_layer.md` (verdict PASS)
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q47_shape_profile_priority_layer.md`
