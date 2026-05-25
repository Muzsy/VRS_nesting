# SGH-Q03 package — Multi-worker `move_items_multi`

Ez a csomag a következő SGH-Qxx taskhoz készült a friss VRS repo SGH-Q02 állapota alapján.

## Tartalom

```text
canvases/egyedi_solver/sgh_q03_multi_worker_move_items_multi.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q03_multi_worker_move_items_multi.yaml
codex/prompts/egyedi_solver/sgh_q03_multi_worker_move_items_multi/run.md
README_SGH_Q03_PACKAGE.md
```

## Cél

SGH-Q03 a Sparrow `move_items_multi()` irányú multi-worker separator keresést vezeti be:

```text
worker_count=1 → SGH-Q02 single-worker kompatibilis viselkedés
worker_count>1 → több seedelt worker, shuffled collider sorrend, best-worker-wins döntés
azonos input + seed + worker_count → determinisztikus output
3-worker dense fixture → best_loss <= 1-worker best_loss
```

## Scope

Production fájlok:

```text
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/Cargo.toml        # csak ha dependency kell
```

Tilos ebben a taskban phase orchestrationt, solution poolt, continuous rotationt, smooth loss-t vagy CDE backendet nyitni.

## Következő marker

Sikeres futás esetén a report vége:

```text
SGH-Q04_STATUS: READY
```
