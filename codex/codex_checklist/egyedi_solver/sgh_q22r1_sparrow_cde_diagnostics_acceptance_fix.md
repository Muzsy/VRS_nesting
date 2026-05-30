# Checklist — SGH-Q22R1 Sparrow CDE diagnostics and acceptance hardening

## Pre-audit

- [x] Q22 report audited (`codex/reports/egyedi_solver/sgh_q22_sparrow_state_separation_kernel.md`)
- [x] Q22 measurement JSON/MD audited (sparrow_cde 0/3 convergent; existing Q22 hides unsupported)
- [x] `optimizer/sparrow.rs` audited (kernel signature unchanged)
- [x] `adapter.rs` unsupported output path audited (Q22 drops `optimizer_diagnostics` on `SPARROW_NO_FEASIBLE_LAYOUT`)
- [x] Q22 smoke script audited (skips CDE unsupported as pass; `boundary_recovery` misnamed; `continuous_rotation_rescue` not required)
- [x] Q22 bench script audited (denominator excludes unsupported; zeros render as `-`; no per-backend summary)
- [x] CDE unsupported/timeout behavior documented in report

## Unsupported diagnostics

- [x] `SPARROW_NO_FEASIBLE_LAYOUT` output preserves `optimizer_diagnostics` (new helper `_unsupported_output_with_full_diag`)
- [x] `SPARROW_COMMIT_VIOLATION_BACKEND` output preserves `optimizer_diagnostics`
- [x] Unsupported CDE output also preserves `collision_backend_diagnostics`
- [x] Unsupported output includes final/best infeasible Sparrow loss metrics (`sparrow_final_raw_loss`, `sparrow_best_infeasible_raw_loss`)
- [x] Unsupported output includes iterations/moves/rollbacks/search_position counts

## Smoke hardening

- [x] Tiny CDE Sparrow fixture must converge (`fixture_tiny_cde_must_converge` — no skip on unsupported)
- [x] Tiny CDE Sparrow fixture asserts `bbox_fallback_queries == 0`
- [x] Smoke no longer skips CDE unsupported as pass evidence (`fixture_cde_no_bbox_fallback` replaced by 2 explicit fixtures)
- [x] Boundary smoke renamed to `already_feasible_single_item` (true boundary recovery already proven in unit test `sparrow_kernel_boundary_recovery`)
- [x] Continuous rotation smoke now requires convergence (2×80×30 on 100×100 with continuous rotation MUST converge)
- [x] Same-seed determinism still tested

## Benchmark hardening

- [x] Unsupported Sparrow runs counted in denominator (`if pipeline == "sparrow_experimental": sparrow_total += 1`)
- [x] Timeout Sparrow runs counted in denominator
- [x] Zero values render as `0` / `0.0`, not `-` (`render_value(v)` helper: only `None` → `-`)
- [x] Per-backend summary exists for bbox vs cde (new table: total / converged / unsupported / timeout)
- [x] CDE failure reason retained in `notes`
- [x] Measurement JSON and MD regenerated

## Q18B recommendation

- [x] Q18B marker decision deferred until measurements: `REQUIRED_FOR_CDE_SCALE` if CDE medium remains unsupported, `NOT_REQUIRED_NOW` only if CDE quick is viable beyond micro
- [x] Decision documented in report based on measured per-backend bench results

## Verify

- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::sparrow` (9 passed — unchanged Q22 unit tests)
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter -- sparrow_pipeline` (4 Q22 + 2 Q22R1 = 6 sparrow tests passed)
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` (419 passed: 417 prior + 2 new Q22R1)
- [x] `python3 scripts/smoke_sgh_q22_sparrow_kernel.py` (26 passed including tiny CDE convergence and medium CDE diagnostics preservation)
- [x] `python3 scripts/bench_sgh_q22_sparrow_kernel.py --quick` (honest accounting; per-backend summary)
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q22r1_sparrow_cde_diagnostics_acceptance_fix.md`

## Report markers

- [x] First line is `PASS`
- [x] PASS contains `SGH-Q22R1_STATUS: READY_FOR_AUDIT`
- [x] PASS contains `SGH-Q22_STATUS: READY_FOR_AUDIT`
- [x] PASS contains `SPARROW_EXPERIMENTAL_STATUS: TESTABLE_WITH_CDE_MICRO`
- [x] PASS contains `Q18B_RECOMMENDATION: REQUIRED|REQUIRED_FOR_CDE_SCALE|NOT_REQUIRED_NOW` (decided by measurements)
