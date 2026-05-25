PASS

# Report - SGH-Q09 `sgh_q09_phase_optimizer_production_solve_path_wiring`

## Status

PASS. The PhaseOptimizer production solve path is wired as explicit opt-in, and the full repo gate completed successfully.

## Dependency gate

- `codex/reports/egyedi_solver/sgh_q08r_exact_backend_no_silent_downgrade_fix.md`: first line `PASS`
- `SGH-Q09_STATUS: READY`: present

## Pre-audit

Command:

```bash
rg -n "PhaseOptimizer|PhaseConfig|MultiSheetManager::new|find_violations\(|run_repair|SheetEliminationEngine" rust/vrs_solver/src
```

Findings:

| Audit point | Evidence | Q09 decision |
|---|---|---|
| Current production Phase1 path | `rust/vrs_solver/src/adapter.rs` calls `MultiSheetManager::new_with_rotation_context(...).run(...)` in the Phase1 branch. | Keep as default and for explicit `legacy_multisheet`. |
| PhaseOptimizer exists as library/test path | `rust/vrs_solver/src/optimizer/phase.rs` defines `PhaseConfig` and `PhaseOptimizer`; tests instantiate `PhaseOptimizer::new(config).run(...)`. | Wire into `adapter::solve()` only under explicit opt-in. |
| Existing commit gate | `rust/vrs_solver/src/optimizer/working.rs` exposes `WorkingLayout::validate_and_commit(...)` and rejects `find_violations(...)`. | Use as the final phase output gate. |
| Existing BPP/sheet elimination layer | `rust/vrs_solver/src/optimizer/bpp_phase.rs` and `multisheet.rs` use `SheetEliminationEngine`. | Reuse through `PhaseOptimizer::run(...)`, no new algorithm. |

## Implementation summary

| Requirement | Implementation | Tests |
|---|---|---|
| Backward-compatible pipeline input | Added optional `SolverInput.optimizer_pipeline` and `OptimizerPipelineKind::{LegacyMultisheet, PhaseOptimizer}` with snake_case JSON. | `solver_input_optimizer_pipeline_defaults_to_legacy` |
| Legacy default unchanged | Missing and explicit `legacy_multisheet` both route to the existing `MultiSheetManager` branch. | `legacy_explicit_matches_implicit_output` |
| PhaseOptimizer production route | Explicit `phase_optimizer` runs prefilter, `build_initial_layout_with_rotation_context`, `WorkingLayout`, `PhaseOptimizer::run`, and commit validation. | `phase_optimizer_pipeline_invokes_phase_optimizer` |
| Rotation context preserved | PhaseConfig receives the already resolved global/part-level `RotationResolveContext`. | `phase_optimizer_pipeline_preserves_rotation_context` |
| Deterministic same seed | PhaseConfig receives input seed and fixed worker count. | `phase_optimizer_pipeline_is_deterministic_for_same_seed` |
| Accepted output violation-free | Phase output is checked by `find_violations` and `validate_and_commit`. | `phase_optimizer_pipeline_output_has_no_violations` |
| No silent fallback | Invalid phase commit returns `unsupported` with `PHASE_OPTIMIZER_COMMIT_VIOLATION`; no legacy layout is returned. | `phase_optimizer_invalid_commit_does_not_silently_fallback_to_legacy` |

## Budget split

Phase optimizer opt-in route derives deterministic sub-budgets from `time_limit_s`:

```text
exploration: 60%
compression: 25%
bpp: 15%
```

`time_limit_s` is clamped to at least `1.0` before splitting.

## Tests run

- `cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter`: PASS
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::phase`: PASS
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::multisheet`: PASS
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::working`: PASS
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`: PASS
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring.md`: PASS

SGH-Q10_STATUS: READY

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-26T00:20:53+02:00 → 2026-05-26T00:23:58+02:00 (185s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring.verify.log`
- git: `main@fe4270f`
- módosított fájlok (git status): 11

**git diff --stat**

```text
 rust/vrs_solver/src/adapter.rs         | 306 +++++++++++++++++++++++++++++----
 rust/vrs_solver/src/io.rs              |  29 ++++
 rust/vrs_solver/src/optimizer/phase.rs | 295 ++++++++++++++++++++-----------
 3 files changed, 496 insertions(+), 134 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/phase.rs
?? README_SGH_Q09_PACKAGE.md
?? canvases/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring.md
?? codex/codex_checklist/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q09_phase_optimizer_production_solve_path_wiring.yaml
?? codex/prompts/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring/
?? codex/reports/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring.md
?? codex/reports/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring.verify.log
?? docs/egyedi_solver/sgh_q09_phase_optimizer_production_wiring_contract.md
```

<!-- AUTO_VERIFY_END -->
