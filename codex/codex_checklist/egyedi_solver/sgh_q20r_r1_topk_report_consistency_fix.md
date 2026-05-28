# Checklist — SGH-Q20R-R1 top-k coordinate descent + report consistency fix

## Pre-audit

- [x] Q20R report audited
- [x] Q20R checklist audited
- [x] `search_position.rs` audited
- [x] `separator.rs` integration audited
- [x] false top-k/report claims identified

## Top-k implementation

- [x] `SearchPositionConfig` has `refine_top_k` or `coord_descent_top_k`
- [x] candidate struct exists or report/checklist no longer claims one
- [x] global finite candidates collected
- [x] focused finite candidates collected
- [x] unsupported candidates counted and rejected
- [x] candidates sorted/tie-broken deterministically
- [x] coordinate descent runs over top-k finite candidates
- [x] `refined_samples` reflects refined candidate count
- [x] best refined candidate selected deterministically
- [x] Continuous rotation axis behavior unchanged
- [x] non-continuous policies still reject illegal rotations

## Backend invariants

- [x] CDE/Jagua boundary evaluation uses active backend
- [x] CDE/Jagua pair evaluation uses active backend
- [x] CDE/Jagua unsupported samples rejected
- [x] CDE/Jagua no silent bbox fallback
- [x] LBF fallback remains explicit and counted

## Tests

- [x] top-k refinement count test
- [x] top-k deterministic tie-break test
- [x] top-k disabled or zero behavior test
- [x] CDE no-bbox-fallback regression still passes
- [x] separator simple overlap regression still passes
- [x] Q20R smoke still passes

## Verify

- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::search_position`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::compress`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`
- [x] `python3 scripts/smoke_sgh_q20r_sparrow_search_position.py`
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q20r_r1_topk_report_consistency_fix.md`

## Report markers

- [x] first line PASS / REVISE / BLOCKED
- [x] PASS contains `SGH-Q20R_R1_STATUS: READY_FOR_AUDIT`
- [x] PASS contains `SGH-Q21_STATUS: READY`
- [x] PASS contains `Q19_STATUS: HOLD`
