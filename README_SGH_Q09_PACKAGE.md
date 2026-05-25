# SGH-Q09 package

Csomag: `sgh_q09_phase_optimizer_production_solve_path_wiring`

## Cél

A Q02–Q08R alatt elkészült minőségi optimizer komponensek ne csak library/test szinten létezzenek, hanem explicit opt-in production solve-pathként is futtathatók legyenek.

## Tartalom

```text
canvases/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q09_phase_optimizer_production_solve_path_wiring.yaml
codex/prompts/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring/run.md
```

## Rövid lényeg

- Default legacy path marad változatlan.
- Új `optimizer_pipeline = phase_optimizer` opt-in path.
- PhaseOptimizer valós production routing.
- Seed, rotation_context, time budget átadás.
- Commit validation gate.
- No silent fallback.

## Következő lépés

A helyi Codex CLI / Claude Code kapja meg a runner promptot:

```text
codex/prompts/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring/run.md
```

PASS esetén a report végén legyen:

```text
SGH-Q10_STATUS: READY
```
