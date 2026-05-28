# Checklist — SGH-Q20 continuous rotation refinement v1

## Dependency gate

- [x] Q16 report first line is PASS
- [x] Q18A report first line is PASS
- [x] Q18A-R1 report first line is PASS
- [x] Q18A-R1 contains `SGH-Q20_STATUS: READY`

## Pre-audit

- [x] `rotation_policy.rs` current Continuous behavior audited
- [x] `item.rs` rotation precedence audited
- [x] `CompressionPhase` rotation loop audited
- [x] `MoveExecutor::try_reinsert` rotation validation audited
- [x] backend-aware commit/validation path audited
- [x] Q18A/R1 diagnostics compatibility audited

## Candidate generation

- [x] Continuous policy has deterministic coarse angle coverage
- [x] Canonical angles remain included
- [x] Useful diagonal/coarse angles are included under the selected sample count
- [x] Candidate list is normalized and deduped
- [x] Legacy `allowed_rotations_deg` precedence preserved
- [x] Same seed/config gives stable candidate order

## Local refinement

- [x] Local refinement helper added or equivalent implementation exists
- [x] Refinement candidates generated only for Continuous policy
- [x] Symmetric offset/wiggle candidates around current rotation implemented
- [x] Candidate count capped
- [x] Locked/HalfTurn/Orthogonal/FortyFive/Discrete receive no unsupported extra angles
- [x] Normalization/deduping covered by tests

## Compression phase wiring

- [x] Compression phase tries refinement candidates
- [x] Refinement attempts are rollback-safe
- [x] Candidate accepted only if score improves
- [x] Candidate accepted only after backend-aware validation
- [x] CDE/Jagua exact path does not fallback to bbox
- [x] Incumbent layout preserved on rejection

## Diagnostics

- [x] Refinement attempts exposed in diagnostics
- [x] Refinement accepts exposed in diagnostics
- [x] Refinement rejections or rejected count exposed in diagnostics
- [x] Best score delta or equivalent improvement evidence exposed/documented
- [x] Report maps exact field names to requirements
- [x] Timing fields remain governed by Q18A-R1 env policy

## Tests

- [x] Unit test: Continuous candidate generation includes deterministic coarse diagonal coverage
- [x] Unit test: local refinement symmetry/normalization/deduping
- [x] Unit test: non-continuous policies do not get extra rotation candidates
- [x] Unit/integration test: compression attempts refinement under Continuous
- [x] Unit/integration test: accepted refinement is score-improving and backend-valid
- [x] Regression test: default determinism stable
- [x] Regression test: CDE bbox fallback count remains zero
- [x] Smoke script added or explicit equivalent test evidence documented

## Verify

- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml rotation_policy`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::compress`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`
- [x] `python3 scripts/smoke_sgh_q18a_cde_observability.py`
- [x] `python3 scripts/smoke_sgh_q20_continuous_rotation_refinement.py`
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q20_continuous_rotation_refinement.md`

## Report markers

- [x] Report first line is `PASS`, `REVISE`, or `BLOCKED`
- [x] PASS report contains `SGH-Q20_STATUS: READY_FOR_AUDIT`
- [x] PASS report contains `SGH-Q21_STATUS: READY|HOLD`
- [x] PASS report contains `Q19_STATUS: HOLD`
- [x] PASS report contains `Q18B_RECOMMENDATION: REQUIRED|NOT_REQUIRED_NOW|INCONCLUSIVE_NEEDS_BIGGER_FIXTURE`
