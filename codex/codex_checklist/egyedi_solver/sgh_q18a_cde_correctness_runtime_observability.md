# Checklist — SGH-Q18A CDE correctness/runtime observability

## Dependency gate

- [x] `codex/reports/egyedi_solver/sgh_q16_cde_final_commit_gate_consistency_fix.md` first line: `PASS`
- [x] Q16 report contains `SGH-Q18_STATUS: READY`

## Pre-audit

- [x] `CdeCollisionBackend` audited
- [x] `CdeAdapter::with_defaults` audited
- [x] `CDEngine::new` call sites audited
- [x] `validate_and_commit_with_backend` audited after Q16
- [x] `validate_placements_with_backend_checked` audited
- [x] `score_with_backend` CDE path audited
- [x] separator CDE path audited
- [x] phase optimizer diagnostics audited
- [x] current missing observability documented

## CDE counters

- [x] CDE pair query count implemented
- [x] CDE boundary query count implemented
- [x] CDE total query count implemented
- [x] CDE engine/per-call adapter build count implemented
- [x] CDE collision result count implemented
- [x] CDE no-collision result count implemented
- [x] CDE unsupported result count implemented
- [x] CDE prepare failure count implemented
- [x] skipped/cross-sheet count implemented or explicitly documented as not applicable
- [x] counters are solve-scoped or thread-local, not flaky process-global mutable state

## Output diagnostics

- [x] Existing `backend_used` field preserved
- [x] Existing `unsupported_queries` field preserved
- [x] Existing `bbox_fallback_queries` field preserved
- [x] Final commit backend proof exposed
- [x] Final commit unsupported/fallback counts exposed
- [x] CDE total/pair/boundary query counts exposed
- [x] CDE engine build count exposed
- [x] CDE unsupported count exposed
- [x] Valid CDE output contains observability diagnostics
- [x] Unsupported CDE output preserves diagnostics or blocker is explicitly documented and tested
- [x] Bbox/default output does not emit misleading CDE diagnostics

## Runtime/timing

- [x] Final commit validation runtime measurable
- [x] PhaseOptimizer exploration runtime measurable in report or explicit diagnostics mode
- [x] PhaseOptimizer compression runtime measurable in report or explicit diagnostics mode
- [x] PhaseOptimizer BPP runtime measurable in report or explicit diagnostics mode
- [x] Legacy multisheet + CDE final commit runtime measurable
- [x] Wall-clock timing does not break default deterministic SolverOutput
- [x] Existing determinism tests/smokes remain green

## Smoke script

- [x] `scripts/smoke_sgh_q18a_cde_observability.py` exists
- [x] Valid CDE legacy_multisheet fixture covered
- [x] Valid CDE phase_optimizer fixture covered
- [x] Malformed CDE unsupported fixture covered
- [x] Bbox false-positive notch CDE fixture covered
- [x] Script checks `backend_used == "cde_adapter"`
- [x] Script checks final commit backend proof
- [x] Script checks `bbox_fallback_queries == 0`
- [x] Script checks `cde_total_queries > 0`
- [x] Script checks `cde_engine_builds > 0`
- [x] Script checks malformed reason `CDE_BACKEND_UNSUPPORTED_QUERY`
- [x] Script checks bbox/default path does not get misleading CDE counters

## Tests

- [x] CDE observability counts pair/boundary queries
- [x] CDE observability reports engine builds
- [x] CDE observability reports no bbox fallback
- [x] Adapter CDE valid output contains observability diagnostics
- [x] Adapter CDE unsupported output behavior covered
- [x] Bbox backend does not emit CDE observability
- [x] Q16 tests still pass

## Verify

- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::cde_adapter`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::collision_backend`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::working`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`
- [x] `python3 scripts/smoke_sgh_q18a_cde_observability.py`
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability.md`

## Report

- [x] Report first line is `PASS`, `REVISE`, or `BLOCKED`
- [x] Report includes dependency gate result
- [x] Report includes pre-audit command summary
- [x] Report includes changed files
- [x] Report lists new diagnostic fields
- [x] Report proves valid CDE final commit backend
- [x] Report proves CDE query/call counters
- [x] Report proves no bbox fallback
- [x] Report proves unsupported behavior
- [x] Report includes timing/per-phase evidence
- [x] Report includes smoke script output summary
- [x] Report includes exact test commands and results
- [x] Report includes Q18B decision table
- [x] PASS report ends with `SGH-Q18A_STATUS: READY_FOR_AUDIT`
- [x] PASS report ends with one `Q18B_RECOMMENDATION` value
