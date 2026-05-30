# Checklist — SGH-Q23 full Sparrow parity cutover

## Reference audit

- [ ] `.cache/sparrow` exists
- [ ] local Sparrow source tree inspected
- [ ] `docs/egyedi_solver/sgh_q23_sparrow_reference_map.md` created
- [ ] reference map includes actual local paths/types/functions
- [ ] main solve loop mapped
- [ ] feasibility lifecycle mapped
- [ ] separation procedure mapped
- [ ] search_position mapped
- [ ] coordinate descent/refinement mapped
- [ ] collision graph mapped
- [ ] GLS/pair weights mapped
- [ ] exploration/compression mapped
- [ ] CDE/jagua-rs session/engine usage mapped
- [ ] fixed-sheet adaptation deviations documented

## Production Sparrow path

- [ ] explicit production path exists, preferably `optimizer_pipeline = "sparrow_cde"`
- [ ] production path is not renamed PhaseOptimizer/legacy solver
- [ ] old solvers explicit opt-in only
- [ ] production failure cannot silently fallback to old solver
- [ ] unsupported/partial/failure outputs keep full diagnostics

## Sparrow parity behavior

- [ ] explicit SparrowState lifecycle
- [ ] state may be infeasible during search
- [ ] backend-confirmed collision graph
- [ ] weighted target selection from collision graph
- [ ] GLS/pair weights persist through restore/rollback as intended
- [ ] search_position is primary relocation path
- [ ] top-k coordinate descent/refinement used
- [ ] backend-oracle evaluate_transform scoring
- [ ] accepted moves follow Sparrow-style objective/acceptance
- [ ] rejected moves are rollback-safe
- [ ] stagnation handling via weights/disruption/restart, not legacy fallback
- [ ] best feasible incumbent tracked
- [ ] best infeasible incumbent tracked
- [ ] exploration/compression aligned to local reference or deviations documented

## CDE/Jagua geometry and scaling

- [ ] collision existence comes from active backend
- [ ] boundary validity comes from active backend
- [ ] final validation comes from active backend
- [ ] solve-scoped CDE/Jagua session/cache implemented or equivalent query reduction exists
- [ ] prepared geometry cache exists
- [ ] transformed placement cache exists
- [ ] pair decision cache exists
- [ ] boundary decision cache exists
- [ ] dirty invalidation implemented when item moves
- [ ] active-set pair filtering implemented
- [ ] incremental collision graph update implemented
- [ ] AABB/bbox only broadphase-prunes negative candidates
- [ ] AABB/bbox never creates positive collision truth

## Fixed-sheet adaptation

- [ ] hard constraints documented and implemented
- [ ] primary objective documented and implemented for fixed single-sheet contract
- [ ] secondary compactness/utilization objective documented
- [ ] multi-sheet status documented: implemented or explicit HOLD
- [ ] medium fixed single-sheet CDE fixture does not timeout

## Legacy/bbox guardrails

- [ ] BboxArea is not production Sparrow/CDE semantic loss identity
- [ ] bbox backend is explicit debug/legacy only
- [ ] LBF fallback disabled in production Sparrow/CDE
- [ ] phase_optimizer fallback disabled in production Sparrow/CDE
- [ ] legacy_multisheet fallback disabled in production Sparrow/CDE
- [ ] bbox_fallback_queries == 0 in production Sparrow/CDE
- [ ] lbf_fallback_used == 0 in production Sparrow/CDE

## Smoke / benchmark

- [ ] `scripts/smoke_sgh_q23_full_sparrow_parity_cutover.py` exists
- [ ] `scripts/bench_sgh_q23_full_sparrow_parity_cutover.py` exists
- [ ] tiny CDE convergence smoke passes
- [ ] overlap separation CDE smoke passes
- [ ] boundary recovery CDE smoke passes
- [ ] continuous rotation rescue CDE smoke passes or documented REVISE
- [ ] medium CDE no-timeout smoke passes
- [ ] production backend-oracle evaluation assertion passes
- [ ] no legacy fallback assertion passes
- [ ] diagnostics preserved on failure assertion passes
- [ ] benchmark counts ok/partial/unsupported/timeout/error in denominator
- [ ] measurement JSON written
- [ ] measurement Markdown written without hiding zero as dash

## Verify

- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::sparrow`
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::cde_session`
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::collision_severity`
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::search_position`
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter`
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`
- [ ] `python3 scripts/smoke_sgh_q23_full_sparrow_parity_cutover.py`
- [ ] `python3 scripts/bench_sgh_q23_full_sparrow_parity_cutover.py --quick`
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q23_full_sparrow_parity_cutover.md`

## Report

- [ ] first line is PASS, REVISE, or BLOCKED
- [ ] report includes reference map summary
- [ ] report includes intentional deviations from local Sparrow
- [ ] report includes production path status
- [ ] report includes CDE/session/cache metrics
- [ ] report includes active-set metrics
- [ ] report includes convergence metrics
- [ ] report includes fixed-sheet adaptation status
- [ ] PASS contains `SGH-Q23_STATUS: READY_FOR_AUDIT`
- [ ] PASS contains `SPARROW_PRODUCTION_STATUS: ...`
- [ ] PASS contains `LEGACY_SOLVER_STATUS: EXPLICIT_OPT_IN_ONLY`
- [ ] PASS contains `Q19_STATUS: HOLD`
