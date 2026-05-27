# Checklist — SGH-Q16 CDE final commit gate consistency fix

## Dependency gate

- [x] `codex/reports/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract.md` first line: `PASS`
- [x] Q15 report contains `SGH-Q16_STATUS: READY`

## Audit

- [x] `WorkingLayout::validate_and_commit_with_backend` audited
- [x] `CollisionBackendKind::Cde` branch found — blanket stub identified
- [x] Old blanket `CDE_BACKEND_UNSUPPORTED` behavior documented before fix
- [x] `CdeCollisionBackend` implementation audited
- [x] `validate_placements_with_backend_checked` audited
- [x] `validate_placements_for_backend` audited
- [x] Adapter CDE solve path audited
- [x] Existing stale CDE scaffold comments identified

## Implementation

- [x] `CollisionBackendKind::Cde` final commit uses `CdeCollisionBackend`
- [x] Valid CDE layout commits successfully
- [x] `backend_diagnostics.backend_name == "cde_adapter"`
- [x] `unsupported_queries == 0` for valid CDE layout
- [x] `bbox_fallback_queries == 0` for CDE final commit
- [x] Unsupported CDE query returns `WorkingCommitError::UnsupportedBackend`
- [x] CDE collision returns `WorkingCommitError::Violations`
- [x] CDE boundary violation returns `WorkingCommitError::Violations`
- [x] No bbox fallback in CDE final commit
- [x] No JaguaPolygonExact fallback in CDE final commit
- [x] Legacy bbox behavior unchanged
- [x] JaguaPolygonExact behavior unchanged

## Stale comments / docs

- [x] `rust/vrs_solver/src/io.rs` CDE comment updated
- [x] `rust/vrs_solver/src/optimizer/working.rs` CDE comment updated
- [x] `rust/vrs_solver/src/optimizer/collision_backend.rs` CDE scaffold/BLOCKED wording corrected
- [x] Docs state CDE final commit supported
- [x] Docs state CDE session/cache performance is Q18 follow-up, not Q16
- [x] Docs state CDE remains opt-in
- [x] Docs state main solver remains outer-only after Q15

## Required tests

- [x] `working_cde_valid_layout_commits_successfully`
- [x] `working_cde_valid_layout_reports_cde_adapter_backend`
- [x] `working_cde_positive_overlap_rejects_with_violation`
- [x] `working_cde_boundary_violation_rejects_with_violation`
- [x] `working_cde_unsupported_geometry_rejects_without_bbox_fallback`
- [x] `adapter_cde_backend_valid_simple_case_is_not_unsupported`
- [x] `adapter_cde_backend_valid_simple_case_reports_cde_diagnostics`
- [x] `adapter_cde_backend_invalid_geometry_returns_unsupported_not_bbox_fallback`
- [x] `adapter_cde_backend_does_not_return_legacy_cde_backend_unsupported_for_valid_case`
- [x] `bbox_default_commit_behavior_unchanged`
- [x] `jagua_polygon_exact_commit_behavior_unchanged`
- [x] `cde_backend_returns_unsupported_not_bbox_fallback` updated (malformed geometry + CDE_BACKEND_UNSUPPORTED_QUERY)

## Verify

- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::working` → 16 passed
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::collision_backend` → 21 passed
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::cde_adapter` → 21 passed
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter` → 48 passed
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` → 334 passed
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q16_cde_final_commit_gate_consistency_fix.md` → PASS

## Report

- [x] Report first line is `PASS`
- [x] Report includes dependency gate result
- [x] Report includes pre-audit command output summary
- [x] Report includes changed files
- [x] Report includes CDE branch before/after summary
- [x] Report proves valid CDE final commit
- [x] Report proves unsupported geometry remains unsupported
- [x] Report proves `bbox_fallback_queries == 0`
- [x] Report proves bbox and JaguaPolygonExact non-regression
- [x] Report lists exact test commands and results
- [x] PASS report ends with `SGH-Q18_STATUS: READY`
