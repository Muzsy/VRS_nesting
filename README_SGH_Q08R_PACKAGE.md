# SGH-Q08R package

Javító csomag az SGH-Q08 CollisionBackend exact backend minőségi blokkolóira.

## Tartalom

```text
canvases/egyedi_solver/sgh_q08r_exact_backend_no_silent_downgrade_fix.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q08r_exact_backend_no_silent_downgrade_fix.yaml
codex/prompts/egyedi_solver/sgh_q08r_exact_backend_no_silent_downgrade_fix/run.md
README_SGH_Q08R_PACKAGE.md
```

## Cél

Q08 után ne menjünk Q09-re addig, amíg az exact backendben nincs javítva:

```text
Malformed outer_points -> Unsupported, nem bbox fallback
Degenerate/invalid geometry -> Unsupported, nem NoCollision
Rect exact geometry -> valós rotált rectangle, nem AABB
Boundary exact path -> rotation-aware
Touching policy -> explicit és tesztelt
Q08 contract -> pontosított PARTIAL/exact scope
```

Q09 csak SGH-Q08R PASS és `SGH-Q09_STATUS: READY` marker után indulhat.
