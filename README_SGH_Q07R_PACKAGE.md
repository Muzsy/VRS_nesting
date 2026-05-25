# SGH-Q07R package

Task: `sgh_q07r_rotation_policy_global_wiring_fix`

Cél: az SGH-Q07-ben bevezetett `RotationPolicy` réteg kódszintű javítása: a globális `SolverInput.rotation_policy` ne csak parse-olva legyen, hanem a valós solve pathban is érvényesüljön, és a continuous candidate generation ne hardcoded `None, 0, 8` paraméterekkel fusson.

Tartalom:

```text
canvases/egyedi_solver/sgh_q07r_rotation_policy_global_wiring_fix.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q07r_rotation_policy_global_wiring_fix.yaml
codex/prompts/egyedi_solver/sgh_q07r_rotation_policy_global_wiring_fix/run.md
README_SGH_Q07R_PACKAGE.md
```

Fontos: ez javító task. SGH-Q08 CDE/exact collision backend csak Q07R PASS után következhet.
