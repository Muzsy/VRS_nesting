# Checklist — SGH-Q04R `sgh_q04r_phase_orchestration_wiring_and_pool_fix`

## Dependency

- [x] SGH-Q04 report létezik.
- [x] SGH-Q04 report első sora PASS.
- [x] SGH-Q04 report tartalmazza: `SGH-Q05_STATUS: READY`.

## Preflight reads

- [x] AGENTS.md átolvasva.
- [x] docs/codex/overview.md átolvasva.
- [x] docs/codex/yaml_schema.md átolvasva.
- [x] docs/codex/report_standard.md átolvasva.
- [x] docs/qa/testing_guidelines.md átolvasva.
- [x] docs/egyedi_solver/sgh_q01_corrected_task_roadmap.md átolvasva.
- [x] docs/egyedi_solver/sgh_q04_phase_orchestration_contract.md átolvasva.
- [x] codex/reports/egyedi_solver/sgh_q04_exploration_compression_phase_orchestration.md átolvasva.
- [x] codex/codex_checklist/egyedi_solver/sgh_q04_exploration_compression_phase_orchestration.md átolvasva.

## Code audit

- [x] rust/vrs_solver/src/optimizer/phase.rs auditálva — B1 stub confirmed.
- [x] rust/vrs_solver/src/optimizer/explore.rs auditálva — B2, B3, B4 confirmed.
- [x] rust/vrs_solver/src/optimizer/compress.rs auditálva — B3, B5, B6 confirmed.
- [x] rust/vrs_solver/src/optimizer/moves.rs auditálva — try_swap, try_reinsert API verified.
- [x] rust/vrs_solver/src/optimizer/repair.rs ref — find_violations API verified.
- [x] rust/vrs_solver/src/optimizer/score.rs ref — ScoreModel API verified.

## Blocker fixes

- [x] B1 — PhaseOptimizer::run() wires real ExplorationPhase and CompressionPhase.
- [x] B2 — InfeasibleSolutionPool::best() returns lowest raw_loss (iterate min, not peek).
- [x] B3 — Fake elapsed replaced with std::time::Instant in explore.rs and compress.rs.
- [x] B4 — try_disrupt() loops 0..max_attempts, each attempt find_violations-checked.
- [x] B5 — Compression scores try_result (not new_placements clone) before commit.
- [x] B6 — Compression uses part.allowed_rotations_deg, not hardcoded [0,90,180,270].

## Tests

- [x] phase_optimizer_invokes_real_phases_non_stub_diagnostics (phase.rs)
- [x] phase_result_unplaced_matches_layout_unplaced (phase.rs)
- [x] phase_result_score_matches_layout_score (phase.rs)
- [x] same_seed_phase_optimizer_determinism (phase.rs)
- [x] infeasible_pool_best_returns_lowest_loss (explore.rs — renamed + fixed assertion)
- [x] infeasible_pool_capacity_retains_lowest_losses (explore.rs — new, checks best() after capacity)
- [x] large_item_swap_disruption_some_is_violation_free (explore.rs — new)
- [x] compression_scores_actual_try_result_before_commit (compress.rs — new)
- [x] compression_uses_part_allowed_rotations_not_hardcoded_list (compress.rs — new)

## Verify

- [x] cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib: 170 passed, 0 failed.
- [x] verify.sh: RUN (see report AUTO_VERIFY section).

## Production scope

- [x] phase.rs módosítva (B1 wiring).
- [x] explore.rs módosítva (B2, B3, B4).
- [x] compress.rs módosítva (B3, B5, B6).
- [x] mod.rs nem módosítva (nem volt szükséges).
- [x] moves.rs nem módosítva.
- [x] Tiltott scope (BPP loop, rotation policy, smooth loss, CDE, DXF, IO, Python): NEM módosítva.

## Documentation

- [x] docs/egyedi_solver/sgh_q04r_phase_orchestration_correction_notes.md elkészült.
- [x] codex/codex_checklist/egyedi_solver/sgh_q04r_phase_orchestration_wiring_and_pool_fix.md elkészült.
- [x] codex/reports/egyedi_solver/sgh_q04r_phase_orchestration_wiring_and_pool_fix.md elkészült.
