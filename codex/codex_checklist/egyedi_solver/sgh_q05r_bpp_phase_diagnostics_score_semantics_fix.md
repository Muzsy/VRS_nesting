# Checklist — SGH-Q05R `sgh_q05r_bpp_phase_diagnostics_score_semantics_fix`

## Dependency gate

- [x] SGH-Q05 report létezik.
- [x] SGH-Q05 report első sora PASS.
- [x] SGH-Q05 report tartalmazza: `SGH-Q06_STATUS: READY`.

## Preflight reads

- [x] AGENTS.md átolvasva.
- [x] docs/codex/overview.md átolvasva.
- [x] docs/codex/yaml_schema.md átolvasva.
- [x] docs/codex/report_standard.md átolvasva.
- [x] docs/qa/testing_guidelines.md átolvasva.
- [x] docs/egyedi_solver/sgh_q05_bpp_phase_loop_contract.md átolvasva.
- [x] canvases/egyedi_solver/sgh_q05_bpp_phase_loop_sheet_elimination.md átolvasva.
- [x] codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q05_bpp_phase_loop_sheet_elimination.yaml átolvasva.
- [x] codex/reports/egyedi_solver/sgh_q05_bpp_phase_loop_sheet_elimination.md átolvasva.
- [x] canvases/egyedi_solver/sgh_q05r_bpp_phase_diagnostics_score_semantics_fix.md átolvasva.
- [x] codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q05r_bpp_phase_diagnostics_score_semantics_fix.yaml átolvasva.

## Code audit

- [x] rust/vrs_solver/src/optimizer/bpp_phase.rs auditálva — BppPhaseDiagnostics hiányzó mezői azonosítva.
- [x] rust/vrs_solver/src/optimizer/phase.rs auditálva — best_score szemantikai hiba azonosítva.
- [x] rust/vrs_solver/src/optimizer/score.rs auditálva — ScoreModel API megértve.
- [x] rust/vrs_solver/src/optimizer/sheet_elimination.rs auditálva — SheetEliminationDiagnostics mezők.

## Implementation

- [x] bpp_phase.rs: `initial_score: f64` mező hozzáadva `BppPhaseDiagnostics`-hoz.
- [x] bpp_phase.rs: `best_score: f64` mező hozzáadva `BppPhaseDiagnostics`-hoz.
- [x] bpp_phase.rs: `per_attempt: Vec<SheetEliminationDiagnostics>` mező hozzáadva.
- [x] bpp_phase.rs: `summary()` frissítve — új mezők megjelennek.
- [x] bpp_phase.rs: `BppPhase` struct `score_model: ScoreModel` fielddel bővítve.
- [x] bpp_phase.rs: `BppPhase::new()` létrehozza `ScoreModel`-t `config.score_weights.clone()`-ból.
- [x] bpp_phase.rs: `run()` — initial_score számítás a loop előtt; `diag.initial_score` és `diag.best_score` beállítva.
- [x] bpp_phase.rs: `run()` — `diag.per_attempt.push(elim_diag)` minden iterációban.
- [x] bpp_phase.rs: `run()` — sikeres commit után `committed_score` számítás, `diag.best_score` frissítve.
- [x] phase.rs: `best_score = final_score.total_cost` (nem min).
- [x] phase.rs: Komment javítva.

## Tests

- [x] `bpp_phase_iteratively_reduces_multiple_sheets` — szigorítva: `final_count == 1 || eliminations >= 2`.
- [x] `bpp_phase_diagnostics_records_per_attempt` — új teszt hozzáadva.
- [x] `bpp_phase_diagnostics_score_fields_are_real` — új teszt hozzáadva.
- [x] `phase_result_best_score_equals_final_layout_score_after_bpp` — új teszt hozzáadva.

## Verify

- [x] cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::bpp_phase: 8 passed, 0 failed.
- [x] cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::phase: 10 passed, 0 failed.
- [x] cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib: 181 passed, 0 failed.
- [x] verify.sh: RUN (see report AUTO_VERIFY section).

## Documentation

- [x] docs/egyedi_solver/sgh_q05_bpp_phase_loop_contract.md frissítve (BppPhaseDiagnostics mezők tábla + per_attempt audit + score semantics szekció).
- [x] codex/codex_checklist/egyedi_solver/sgh_q05r_bpp_phase_diagnostics_score_semantics_fix.md elkészült.
- [x] codex/reports/egyedi_solver/sgh_q05r_bpp_phase_diagnostics_score_semantics_fix.md elkészült.

## Production scope

- [x] bpp_phase.rs módosítva (BppPhaseDiagnostics bővítés, ScoreModel integráció).
- [x] phase.rs módosítva (best_score fix, komment javítás).
- [x] docs/egyedi_solver/sgh_q05_bpp_phase_loop_contract.md frissítve.
- [x] Tiltott scope: NEM módosítva (SheetEliminationEngine, Q06/Q07/Q08, DXF/API/frontend).
