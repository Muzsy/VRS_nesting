# Checklist — SGH-Q05 `sgh_q05_bpp_phase_loop_sheet_elimination`

## Dependency gate

- [x] SGH-Q04R report létezik.
- [x] SGH-Q04R report első sora PASS.
- [x] SGH-Q04R report tartalmazza: `SGH-Q05_STATUS: READY`.

## Preflight reads

- [x] AGENTS.md átolvasva.
- [x] docs/codex/overview.md átolvasva.
- [x] docs/codex/yaml_schema.md átolvasva.
- [x] docs/codex/report_standard.md átolvasva.
- [x] docs/qa/testing_guidelines.md átolvasva.
- [x] docs/egyedi_solver/sgh_q01_corrected_task_roadmap.md átolvasva.
- [x] docs/egyedi_solver/sgh_q04_phase_orchestration_contract.md átolvasva.
- [x] docs/egyedi_solver/sgh_q04r_phase_orchestration_correction_notes.md átolvasva.
- [x] codex/reports/egyedi_solver/sgh_q04r_phase_orchestration_wiring_and_pool_fix.md átolvasva.
- [x] codex/codex_checklist/egyedi_solver/sgh_q04r_phase_orchestration_wiring_and_pool_fix.md átolvasva.

## Code audit

- [x] rust/vrs_solver/src/optimizer/phase.rs auditálva.
- [x] rust/vrs_solver/src/optimizer/explore.rs auditálva.
- [x] rust/vrs_solver/src/optimizer/compress.rs auditálva.
- [x] rust/vrs_solver/src/optimizer/sheet_elimination.rs auditálva — SheetEliminationEngine API megértve.
- [x] rust/vrs_solver/src/optimizer/multisheet.rs auditálva — compute_sheet_count_used API.
- [x] rust/vrs_solver/src/optimizer/working.rs auditálva — WorkingLayout::new() signature.
- [x] rust/vrs_solver/src/optimizer/repair.rs ref — find_violations API.
- [x] rust/vrs_solver/src/optimizer/score.rs ref — ScoreModel API.
- [x] rust/vrs_solver/src/optimizer/stopping.rs auditálva — StoppingPolicy API.

## Implementation

- [x] rust/vrs_solver/src/optimizer/bpp_phase.rs létrehozva (BppPhase, BppPhaseDiagnostics).
- [x] rust/vrs_solver/src/optimizer/mod.rs frissítve (pub mod bpp_phase).
- [x] rust/vrs_solver/src/optimizer/phase.rs frissítve:
  - [x] PhaseConfig: bpp_budget és bpp_max_eliminations mezők hozzáadva.
  - [x] PhaseConfig::default(): bpp_budget = PhaseBudget::new(16, 30.0), bpp_max_eliminations = 16.
  - [x] PhaseOptimizer::run() → run_bpp() bekötés (exploration → compression → BPP).
  - [x] run_bpp() privát helper BppPhase::new(config).run() hívással.

## BPP contract

- [x] Iteratív loop: SheetEliminationEngine többszöri hívása.
- [x] Commit gate: successful_eliminations > 0 ÉS new_sheet_count < incumbent ÉS find_violations == [] ÉS count/set invariant.
- [x] Rollback: clone-alapú, implicit (sikertelen attempt nem módosítja az incumbentet).
- [x] sheet_count soha nem nő.
- [x] PhaseResult.score == score(PhaseResult.layout) a BPP után is.
- [x] PhaseResult.unplaced == PhaseResult.layout.unplaced.

## Tests

- [x] bpp_phase_iteratively_reduces_multiple_sheets (bpp_phase.rs)
- [x] bpp_phase_failed_attempt_rolls_back_exact_incumbent (bpp_phase.rs)
- [x] bpp_phase_never_increases_sheet_count (bpp_phase.rs)
- [x] bpp_phase_output_is_violation_free (bpp_phase.rs)
- [x] bpp_budget_limits_attempts (bpp_phase.rs)
- [x] same_seed_bpp_phase_determinism (bpp_phase.rs)
- [x] phase_optimizer_invokes_bpp_phase_loop (phase.rs)
- [x] phase_result_score_layout_consistency_after_bpp (phase.rs)

## Verify

- [x] cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib: 178 passed, 0 failed.
- [x] verify.sh: RUN (see report AUTO_VERIFY section).

## Production scope

- [x] bpp_phase.rs létrehozva (új modul).
- [x] mod.rs frissítve (pub mod bpp_phase).
- [x] phase.rs frissítve (PhaseConfig bővítés, run_bpp bekötés).
- [x] sheet_elimination.rs nem módosítva.
- [x] Tiltott scope: NEM módosítva.

## Documentation

- [x] docs/egyedi_solver/sgh_q05_bpp_phase_loop_contract.md elkészült.
- [x] codex/codex_checklist/egyedi_solver/sgh_q05_bpp_phase_loop_sheet_elimination.md elkészült.
- [x] codex/reports/egyedi_solver/sgh_q05_bpp_phase_loop_sheet_elimination.md elkészült.
