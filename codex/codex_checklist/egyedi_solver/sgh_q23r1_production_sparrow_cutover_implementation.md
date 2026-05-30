# Checklist — SGH-Q23R1 production Sparrow cutover implementation

## Reference and baseline

- [ ] `.cache/sparrow` exists
- [ ] Q23 `REVISE` report read
- [ ] Q23 measurements read
- [ ] `docs/egyedi_solver/sgh_q23_sparrow_reference_map.md` read
- [ ] `docs/egyedi_solver/sgh_q23r1_sparrow_reference_delta.md` created
- [ ] Reference delta focuses on missing implementation, not broad re-audit

## CDE/Jagua session/cache

- [ ] Per-call CDE hot path replaced or hidden behind solve-scoped session/cache
- [ ] Prepared geometry cache implemented
- [ ] Transformed placement cache implemented
- [ ] Pair decision cache implemented
- [ ] Boundary decision cache implemented
- [ ] Version/dirty invalidation implemented on item move
- [ ] Active-set pair filtering implemented
- [ ] Unsupported CDE never maps to NoCollision
- [ ] Session/cache diagnostics exposed
- [ ] Engine builds no longer scale with pair/boundary query count

## Incremental collision graph

- [ ] Initial graph build implemented
- [ ] `register_item_move`-style update implemented
- [ ] Stale edges touching moved item removed
- [ ] Only dirty/active-set pairs re-queried
- [ ] Boundary violation for moved item updated
- [ ] GLS weights separated from transient collision edges
- [ ] Deterministic top-k diagnostics preserved

## Sparrow move lifecycle

- [ ] Multi-target pass over colliding items implemented
- [ ] Target set derived from weighted collision graph
- [ ] Deterministic ordering / seed tie-breaks implemented
- [ ] `search_position` remains primary relocation mechanism
- [ ] Coordinate/local refinement used
- [ ] Backend-oracle `evaluate_transform` used
- [ ] Accepted move commits and updates graph incrementally
- [ ] Rejected move rollback-safe
- [ ] GLS weights persist as intended through rollback

## GLS / stagnation / incumbents

- [ ] Weighted collision utility implemented
- [ ] Repeated problematic pairs/items penalized
- [ ] Stagnation detected
- [ ] Disruption/restart implemented
- [ ] Best feasible incumbent tracked
- [ ] Best infeasible incumbent tracked

## Exploration/compression fixed-sheet lifecycle

- [ ] Exploration pass loop implemented
- [ ] Separation pass loop implemented
- [ ] Compression pass on best feasible incumbent implemented
- [ ] Fixed-sheet objective implemented
- [ ] Final CDE/Jagua validation implemented
- [ ] PhaseOptimizer not called as black-box production postpass

## Production cutover

- [ ] Normal production route uses `sparrow_cde`
- [ ] Missing/implicit production config does not silently use old solver, or normal run configs explicitly route to `sparrow_cde`
- [ ] `phase_optimizer` explicit opt-in only
- [ ] `legacy_multisheet` explicit opt-in only
- [ ] `sparrow_experimental` debug/development only
- [ ] `sparrow_cde` overrides bbox backend request to CDE/Jagua

## Forbidden fallback checks

- [ ] No bbox positive collision truth in production `sparrow_cde`
- [ ] No bbox semantic loss truth in production `sparrow_cde`
- [ ] No bbox final validation in production `sparrow_cde`
- [ ] No LBF fallback in production `sparrow_cde`
- [ ] No PhaseOptimizer fallback in production `sparrow_cde`
- [ ] No legacy_multisheet fallback in production `sparrow_cde`
- [ ] Failure returns diagnostics, not legacy result

## Smoke / benchmark

- [ ] `scripts/smoke_sgh_q23r1_production_sparrow_cutover.py` created
- [ ] `scripts/bench_sgh_q23r1_production_sparrow_cutover.py` created
- [ ] Tiny CDE convergence passes
- [ ] Two-rectangle overlap separation passes
- [ ] Boundary recovery passes
- [ ] Continuous rotation rescue passes
- [ ] Medium 10–20 item CDE fixture converges without timeout
- [ ] Production default/routing assertion passes
- [ ] Backend-oracle evaluation assertion passes
- [ ] No legacy fallback assertion passes
- [ ] Incremental graph/cache metrics assertion passes
- [ ] Failure diagnostics assertion passes
- [ ] Benchmark denominator accounting includes ok/partial/unsupported/timeout/error

## Required commands

- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::sparrow`
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::cde_session`
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::collision_severity`
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::search_position`
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator`
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter`
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`
- [ ] `python3 scripts/smoke_sgh_q23r1_production_sparrow_cutover.py`
- [ ] `python3 scripts/bench_sgh_q23r1_production_sparrow_cutover.py --quick`
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q23r1_production_sparrow_cutover_implementation.md`

## Report

- [ ] First line is PASS, REVISE, or BLOCKED
- [ ] `SGH-Q23R1_STATUS` marker present
- [ ] `SPARROW_PRODUCTION_STATUS` marker present
- [ ] `PRODUCTION_DEFAULT_STATUS` marker present
- [ ] `CDE_SESSION_STATUS` marker present
- [ ] `INCREMENTAL_GRAPH_STATUS` marker present
- [ ] `LEGACY_SOLVER_STATUS` marker present
- [ ] `MEDIUM_CDE_STATUS` marker present
- [ ] Measurements JSON created
- [ ] Measurements Markdown created
- [ ] PASS not claimed unless medium CDE converges and production route is Sparrow/CDE
