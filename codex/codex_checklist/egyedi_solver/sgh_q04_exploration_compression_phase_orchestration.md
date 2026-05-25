# Checklist — SGH-Q04 `sgh_q04_exploration_compression_phase_orchestration`

## Dependency

- [x] SGH-Q03R report létezik (or SGH-Q03 if SGH-Q03R not ready).
- [x] SGH-Q03/SGH-Q03R report első sora PASS/PASS_WITH_NOTES.
- [x] SGH-Q03/SGH-Q03R report tartalmazza: `SGH-Q04_STATUS: READY`.

## Inputs

- [x] AGENTS + Codex workflow és report/yaml szabvány átolvasva.
- [x] SGH-Q00/Q01/Q03 dokumentumok átolvasva.
- [x] `rust/vrs_solver/src/optimizer/mod.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/separator.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/moves.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/working.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/score.rs` auditálva.
- [x] Dependency preflight: SGH-Q03 report ellenőrizve.

## Outputs

- [x] `rust/vrs_solver/src/optimizer/phase.rs` létrehozva.
- [x] `rust/vrs_solver/src/optimizer/explore.rs` létrehozva.
- [x] `rust/vrs_solver/src/optimizer/compress.rs` létrehozva.
- [x] `rust/vrs_solver/src/optimizer/mod.rs` frissítve (phase, explore, compress export).
- [x] `docs/egyedi_solver/sgh_q04_phase_orchestration_contract.md` elkészült.
- [x] `codex/codex_checklist/egyedi_solver/sgh_q04_exploration_compression_phase_orchestration.md` elkészült.
- [x] `codex/reports/egyedi_solver/sgh_q04_exploration_compression_phase_orchestration.md` elkészült.

## Implementation

- [x] PhaseConfig + PhaseBudget + PhaseDiagnostics + PhaseResult + PhaseStopReason API.
- [x] PhaseOptimizer orchestration (ExplorationPhase + CompressionPhase).
- [x] InfeasibleSolutionPool (bounded, loss-ascending, deterministic tie-break).
- [x] LargeItemSwapDisruption (top-percentile, deterministic pair selection).
- [x] ExplorationPhase (feasible incumbent preservation, separator usage).
- [x] CompressionPhase (score-non-worsening only, find_violations check).
- [x] worker_count továbbítva VrsSeparatorConfig felé.
- [x] seed explicit kezelés.

## Scope tiltás

- [x] BPP phase loop / sheet elimination iteratív loop nem nyílt meg.
- [x] continuous rotation / RotationPolicy nem nyílt meg.
- [x] smooth LossModel / pole penetration nem nyílt meg.
- [x] collision backend (CDE) nem nyílt meg.
- [x] IO contract / Python runner nem változott.
- [x] Production fájl scope: phase.rs, explore.rs, compress.rs, mod.rs, moves.rs (ha kell).

## Tests

- [x] PhaseConfig default/budget smoke.
- [x] InfeasibleSolutionPool capacity + loss ordering + deterministic tie-break.
- [x] Exploration preserves feasible incumbent.
- [x] Exploration stores infeasible candidate without accepting infeasible output.
- [x] LargeItemSwapDisruption selects top-percentile large items deterministically.
- [x] Compression no-downgrade: best_score <= initial_score or unchanged baseline.
- [x] Compression accepted output find_violations == empty.
- [x] Same seed determinism smoke.
- [x] Phase budget stop reason.

## Verify

- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` PASS (162/162).
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q04_exploration_compression_phase_orchestration.md` zöld.
- [x] Report első sora PASS.
- [x] `SGH-Q05_STATUS: READY` marker a report végén.
