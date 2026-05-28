# Checklist — SGH-Q18A-R1 phase timing and report consistency fix

## Pre-audit

- [x] Q18A report audited
- [x] Q18A checklist audited
- [x] Q18A docs audited
- [x] Actual timing implementation audited in `adapter.rs`, `phase.rs`, `io.rs`
- [x] False checklist claims identified

## Timing implementation

- [x] Legacy multisheet CDE final commit runtime measurable under `VRS_CDE_OBSERVABILITY_TIMING=1`
- [x] PhaseOptimizer exploration runtime measurable under `VRS_CDE_OBSERVABILITY_TIMING=1`
- [x] PhaseOptimizer compression runtime measurable under `VRS_CDE_OBSERVABILITY_TIMING=1`
- [x] PhaseOptimizer BPP runtime measurable under `VRS_CDE_OBSERVABILITY_TIMING=1`
- [x] PhaseOptimizer final commit runtime measurable under `VRS_CDE_OBSERVABILITY_TIMING=1`
- [x] Timing fields absent from default SolverOutput JSON
- [x] Timing fields are `Option`/backward-compatible if serialized
- [x] Default determinism smoke remains green

## Smoke/tests

- [x] Q18A smoke script checks default output has no wall-clock timing fields
- [x] Q18A smoke script checks timing-env legacy fields
- [x] Q18A smoke script checks timing-env phase_optimizer fields
- [x] Cargo tests cover timing fields absent by default
- [x] Cargo tests cover timing fields present under env flag
- [x] Cargo tests cover determinism not broken by default output

## Docs/report consistency

- [x] Q18A docs updated to reflect actual timing support
- [x] Q18A checklist corrected, no false checked items remain
- [x] Q18A report updated or addendum created
- [x] Q18A-R1 report created
- [x] Q18B recommendation re-evaluated using real timing evidence

## Verify

- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::phase`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`
- [x] `python3 scripts/smoke_sgh_q18a_cde_observability.py`
- [x] `VRS_CDE_OBSERVABILITY_TIMING=1 python3 scripts/smoke_sgh_q18a_cde_observability.py`
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q18a_r1_phase_timing_report_consistency_fix.md`

## Report markers

- [x] Report first line is `PASS`, `REVISE`, or `BLOCKED`
- [x] PASS report contains `SGH-Q18A_R1_STATUS: READY_FOR_AUDIT`
- [x] PASS report contains `SGH-Q20_STATUS: READY|HOLD`
- [x] PASS report contains `Q18B_RECOMMENDATION: REQUIRED|NOT_REQUIRED_NOW|INCONCLUSIVE_NEEDS_BIGGER_FIXTURE`
