# Runner — SGH-Q05R BPP diagnostics + score semantics fix

Hajtsd végre a `canvases/egyedi_solver/sgh_q05r_bpp_phase_diagnostics_score_semantics_fix.md` canvas és a hozzá tartozó goal YAML alapján a Q05R javító taskot.

## Kötelező bemenetek

Olvasd el:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
docs/egyedi_solver/sgh_q05_bpp_phase_loop_contract.md
canvases/egyedi_solver/sgh_q05_bpp_phase_loop_sheet_elimination.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q05_bpp_phase_loop_sheet_elimination.yaml
codex/reports/egyedi_solver/sgh_q05_bpp_phase_loop_sheet_elimination.md
canvases/egyedi_solver/sgh_q05r_bpp_phase_diagnostics_score_semantics_fix.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q05r_bpp_phase_diagnostics_score_semantics_fix.yaml
```

## Javítandó konkrétumok

1. `BppPhaseDiagnostics` legyen teljesebb:

```text
initial_score
best_score
per_attempt: Vec<SheetEliminationDiagnostics>
```

2. Minden `SheetEliminationEngine::run()` attempt diagnosztikája kerüljön `per_attempt`-be.

3. `PhaseOptimizer::run()` ne állítsa azt, hogy `best_score` final layout score, miközben `min(exploration, compression, final, initial)` értéket használ. Minimum javítás:

```text
PhaseResult.best_score == PhaseResult.score.total_cost
```

4. Szigorítsd a Q05 teszteket:

```text
iterative 3-sheet fixture tényleg 1 sheetig vagy >=2 eliminációig jusson
attempts == per_attempt.len()
score mezők valós layout score-ok
PhaseResult.best_score == result.score.total_cost
```

## Tilos

Ne nyisd meg:

```text
Q06 LossModel
Q07 RotationPolicy
Q08 CDE
SheetEliminationEngine stratégiai átírása
DXF/API/frontend/runner módosítás
```

## Verify

Futtasd:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::bpp_phase
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::phase
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q05r_bpp_phase_diagnostics_score_semantics_fix.md
```

PASS esetén a report végén:

```text
SGH-Q06_STATUS: READY
```
