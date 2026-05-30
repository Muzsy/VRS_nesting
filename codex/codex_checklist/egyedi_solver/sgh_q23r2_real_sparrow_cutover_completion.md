# Checklist — SGH-Q23R2 Real Sparrow cutover completion

## Hard gates

- [ ] Report starts with `PASS` or `REVISE`.
- [ ] Missing `optimizer_pipeline` under `solver_profile=jagua_optimizer_phase1_outer_only` routes to `sparrow_cde`.
- [ ] Legacy/PhaseOptimizer routes are explicit opt-in only.
- [ ] `sparrow_cde` forces CDE regardless of requested collision backend.
- [ ] No production fallback to bbox, LBF, PhaseOptimizer, or legacy multisheet.
- [ ] Single-engine multi-hazard CDE candidate query implemented and wired to hot candidate evaluation.
- [ ] Pairwise CDE fallback queries are explicitly counted and bounded.
- [ ] Incremental collision graph update path is active after initialization.
- [ ] Multi-target/multi-worker Sparrow pass is active.
- [ ] Fixed-sheet exploration/compression lifecycle is active.
- [ ] Medium fixture status is `ok`.
- [ ] Medium fixture placed/required is `12/12`.
- [ ] Medium fixture final pairs and boundary violations are zero.
- [ ] Medium fixture `bbox_fallback_queries == 0`.
- [ ] Medium fixture `lbf_fallback_used == 0`.
- [ ] Medium fixture `backend_used == cde_adapter`.
- [ ] CDE engine-build reduction meets the Q23R1 hard target or a stronger batch metric proves equivalent progress.
- [ ] Full diagnostics are preserved on unsupported/error paths.
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` executed or limitation documented.
- [ ] Q23R2 smoke and benchmark scripts executed.
- [ ] Measurements JSON and MD written.

## Reject conditions

- [ ] Medium convergence is downgraded to soft gate.
- [ ] Default remains legacy.
- [ ] New code only adds report/docs without solving hot-path and convergence blockers.
- [ ] Positive collision truth comes from bbox.
- [ ] Invalid placements can be emitted as `ok`.
