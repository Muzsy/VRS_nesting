# Checklist — SGH-Q21R1 full Sparrow-aligned collision severity hardening

## Principle

- [x] The implementation targets full jagua_rs/Sparrow alignment, not a minimal green patch.
- [x] PASS is not used for partial work.

## Pre-audit

- [x] Q21 report audited
- [x] Q21 checklist audited
- [x] `collision_severity.rs` audited
- [x] `search_position.rs` integration audited
- [x] `separator.rs` tracker/GLS integration audited
- [x] hard-coded `f64::MAX` paths identified (collision_severity.rs:244,261,284,297 + separator.rs:970,989,1001,1020)
- [x] missing query accounting paths identified (separator.rs:173,184,224,236,559,571,599,614 — only confirmed_collisions counted, queries not)
- [x] cardinal-only probe paths identified (collision_severity.rs:120,170)
- [x] large-sheet initial-step problem documented (1500×3000 sheet → 167 mm initial step with 5% factor; capped to 10 mm in Q21R1)

## Config/defaults

- [x] `probe_max_initial_step_mm` added (default 10.0)
- [x] `probe_bracket_growth` added (default 2.0)
- [x] `probe_binary_refine_steps` added (default 8) and tolerance stop
- [x] `probe_tolerance_mm` added (default 0.05)
- [x] diagonal direction config added (`probe_use_diagonal_directions`, default true)
- [x] pair-center direction config added (`probe_use_pair_center_direction`, default true)
- [x] sheet-center direction config added (`probe_use_center_direction`, default true)
- [x] effective initial step is capped on large sheets (via `effective_initial_step()` helper, unit-tested)
- [x] defaults are justified in report (section 4.2)

## Multi-direction adaptive probe

- [x] Pair probe uses cardinal directions
- [x] Pair probe uses diagonal directions (4 diagonals, gated by config)
- [x] Pair probe uses pair-center-away direction when valid (`normalize(c_candidate - c_other)`)
- [x] Boundary probe uses cardinal directions
- [x] Boundary probe uses diagonal directions
- [x] Boundary probe uses sheet-center direction when valid (`normalize(c_sheet - c_candidate)`)
- [x] Directions are normalized and deduped deterministically (tolerance `1e-3`)
- [x] Probe brackets first clear distance (geometric growth `probe_bracket_growth`)
- [x] Probe binary-refines between last collision and first clear (`probe_binary_refine_steps` or `probe_tolerance_mm` halt)
- [x] Probe returns refined resolution severity (min across resolved directions)
- [x] Unresolved direction policy documented and tested — returns `cfg.hard_unsupported_loss`; `unresolved_probe=true` propagated through `EvaluationResult`

## Accounting

- [x] evaluate_transform boundary queries counted (`boundary_queries++`)
- [x] evaluate_transform pair queries counted (`pair_queries++`)
- [x] probe pair queries counted (`probe_pair_queries++` + `probe_queries++`)
- [x] probe boundary queries counted (`probe_boundary_queries++` + `probe_queries++`)
- [x] tracker compute_backend_decisions pair queries counted
- [x] tracker compute_backend_decisions boundary queries counted
- [x] tracker update_backend_decisions_for_item pair queries counted
- [x] tracker update_backend_decisions_for_item boundary queries counted
- [x] Unsupported counted in all query/probe paths (`unsupported_queries++` + `probe_unsupported++` outcome)
- [x] probe resolved/unresolved/unsupported counts exposed (`probe_resolved`, `probe_unresolved`, `probe_unsupported` in stats and output)

## Loss semantics

- [x] `cfg.hard_unsupported_loss` used for unsupported evaluation loss
- [x] `f64::MAX` not exposed as public unsupported loss in severity contract
- [x] Bbox backend legacy behavior preserved (eval_bbox_loss unchanged for legitimate path)
- [x] CDE/Jagua backend NoCollision overrides bbox overlap false positives (tested in `severity_bbox_false_positive_exact_backend_no_collision_zero_loss`)
- [x] CDE/Jagua backend Collision uses oracle-probe severity when enabled
- [x] bbox proxy severity only under Bbox backend or explicit disabled probe fallback
- [x] bbox proxy usage counted (`bbox_proxy_severity_uses++`)

## Integration

- [x] `search_position` uses improved central severity engine (delegates to `evaluate_transform_loss`)
- [x] `separator` tracker uses improved backend-confirmed severity (Q21R1 multi-direction probe via `compute_probe_pair_severity` / `compute_probe_boundary_severity`)
- [x] `separator` GLS weights use improved severity (tested in `separator_gls_uses_improved_backend_confirmed_severity`)
- [x] `phase` accumulates improved stats (8 new Q21R1 fields)
- [x] `adapter` exposes improved stats (8 new fields in `OptimizerDiagnosticsOutput`)
- [x] output diagnostics are backward-compatible (Q21 9 fields preserved, +8 new)

## Tests/smoke

- [x] large-sheet capped initial step test (`severity_initial_step_is_capped_on_large_sheet`)
- [x] pair multi-direction probe test (`severity_pair_probe_uses_diagonal_and_pair_center_directions`)
- [x] boundary multi-direction probe test (`severity_boundary_probe_uses_diagonal_and_sheet_center_directions`)
- [x] binary refinement test (`severity_probe_binary_refines_resolution_distance`)
- [x] unsupported accounting test (`severity_probe_unsupported_increments_unsupported_queries`)
- [x] tracker query accounting test (`severity_tracker_counts_pair_and_boundary_queries`)
- [x] update_backend_decisions query accounting test (`severity_tracker_update_counts_pair_and_boundary_queries`)
- [x] hard_unsupported_loss test (`severity_hard_unsupported_loss_used_instead_of_f64_max`)
- [x] bbox false-positive no-collision test (`severity_bbox_false_positive_exact_backend_no_collision_zero_loss`)
- [x] bbox proxy policy test (`severity_bbox_proxy_only_when_explicitly_enabled_or_bbox_backend`)
- [x] search_position improved stats test (`search_position_uses_improved_severity_stats`)
- [x] separator GLS improved severity test (`separator_gls_uses_improved_backend_confirmed_severity`)
- [x] Q21 smoke expanded (8 fixtures, replaces old 5-fixture set)

## Verify

- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::collision_severity` (13 passed)
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::search_position` (14 passed)
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator` (47 passed)
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter` (55 passed)
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` (400 passed)
- [x] `python3 scripts/smoke_sgh_q20r_sparrow_search_position.py` (37 passed previously; rerun in verify)
- [x] `python3 scripts/smoke_sgh_q21_collision_severity.py` (Q21R1 8-fixture set)
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q21r1_collision_severity_full_sparrow_alignment.md`

## Report markers

- [x] First line is `PASS`
- [x] PASS contains `SGH-Q21R1_STATUS: READY_FOR_AUDIT`
- [x] PASS contains `SGH-Q21_STATUS: READY_FOR_AUDIT`
- [x] PASS contains `SGH-Q22_STATUS: READY`
- [x] PASS contains `Q19_STATUS: HOLD`
- [x] PASS contains `Q18B_RECOMMENDATION: NOT_REQUIRED_NOW`
