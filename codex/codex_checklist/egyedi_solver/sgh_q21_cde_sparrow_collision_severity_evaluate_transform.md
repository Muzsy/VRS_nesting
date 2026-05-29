# Checklist — SGH-Q21 CDE/Sparrow collision severity + evaluate_transform score

## Dependency gate

- [ ] Q20R-R1 report first line is `PASS`
- [ ] Q20R-R1 report contains `SGH-Q21_STATUS: READY`

## Pre-audit

- [ ] `search_position.rs` current local eval helpers audited
- [ ] `separator.rs` / `VrsCollisionTracker` current pair/boundary loss audited
- [ ] `loss_model.rs` bbox/smooth surrogate limitations audited
- [ ] `collision_backend.rs` backend API audited
- [ ] CDE/Jagua unsupported behavior audited
- [ ] Current diagnostics fields audited

## Severity API

- [ ] Central `collision_severity` or equivalent module exists
- [ ] Pair severity API exists
- [ ] Boundary severity API exists
- [ ] Candidate `evaluate_transform` API exists
- [ ] Severity stats/diagnostics struct exists
- [ ] Unsupported handling explicit
- [ ] Bbox backend legacy behavior preserved

## Backend-confirmed severity

- [ ] CDE/Jagua pair collision existence comes from active backend
- [ ] CDE/Jagua boundary existence comes from active backend
- [ ] CDE/Jagua NoCollision returns zero severity
- [ ] CDE/Jagua Collision returns positive severity
- [ ] CDE/Jagua Unsupported returns reject or hard unsupported loss
- [ ] Severity estimate uses backend oracle/probes if exact depth unavailable
- [ ] Bbox is not collision source-of-truth under CDE/Jagua
- [ ] Any bbox proxy severity use is explicit and counted

## SearchPosition integration

- [ ] `search_position` uses shared evaluate_transform/severity API
- [ ] Local duplicate bbox-eval path removed or delegated
- [ ] Q20R-R1 top-k coordinate descent behavior preserved
- [ ] Unsupported samples are rejected
- [ ] Deterministic ordering preserved
- [ ] CDE no bbox fallback invariant preserved

## Separator / GLS integration

- [ ] `VrsCollisionTracker::pair_loss` under CDE/Jagua uses backend-confirmed severity
- [ ] `VrsCollisionTracker::boundary_loss` under CDE/Jagua uses backend-confirmed severity
- [ ] `total_loss` uses backend severity
- [ ] `total_weighted_loss` uses backend severity
- [ ] `weighted_loss_for_item` uses backend severity
- [ ] `colliding_indices` uses backend severity
- [ ] `update_weights` uses backend severity
- [ ] `update_placement` recomputes backend severity correctly

## Diagnostics

- [ ] Severity backend exposed
- [ ] Severity enabled flag exposed
- [ ] Pair severity query count exposed
- [ ] Boundary severity query count exposed
- [ ] Probe query count exposed
- [ ] Backend-confirmed collision/no-collision counts exposed
- [ ] Unsupported severity query count exposed
- [ ] Bbox proxy severity use count exposed
- [ ] Report maps exact field names to requirements

## Tests

- [ ] Bbox backend preserves legacy pair loss
- [ ] Exact backend no-collision zeroes bbox false-positive
- [ ] Exact backend collision returns positive severity
- [ ] Shallow vs deep collision monotonicity tested
- [ ] Boundary valid zero tested
- [ ] Boundary violation positive tested
- [ ] Unsupported reject/hard-loss behavior tested
- [ ] SearchPosition uses severity engine tested
- [ ] Separator tracker uses backend-confirmed pair severity tested
- [ ] GLS weight update uses backend severity tested
- [ ] CDE no bbox source-of-truth regression tested
- [ ] Q20R smoke still passes

## Smoke/verify

- [ ] `scripts/smoke_sgh_q21_collision_severity.py` exists
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::collision_severity`
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::search_position`
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator`
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter`
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`
- [ ] `python3 scripts/smoke_sgh_q20r_sparrow_search_position.py`
- [ ] `python3 scripts/smoke_sgh_q21_collision_severity.py`
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q21_cde_sparrow_collision_severity_evaluate_transform.md`

## Report markers

- [ ] Report first line is `PASS`, `REVISE`, or `BLOCKED`
- [ ] PASS report contains `SGH-Q21_STATUS: READY_FOR_AUDIT`
- [ ] PASS report contains `SGH-Q22_STATUS: READY|HOLD`
- [ ] PASS report contains `Q19_STATUS: HOLD`
- [ ] PASS report contains `Q18B_RECOMMENDATION: REQUIRED|NOT_REQUIRED_NOW|INCONCLUSIVE_NEEDS_BIGGER_FIXTURE`
