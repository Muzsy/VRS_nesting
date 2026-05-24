# SGH-02 VrsSeparator contract

Document date: 2026-05-25. Describes the design, rules, and invariants of
`VrsSeparator` and `VrsCollisionTracker` as introduced in SGH-02.

---

## Purpose

`VrsSeparator` is a deterministic, GLS-inspired relocation loop that operates
on a `WorkingLayout` and attempts to resolve placement collisions.  It is the
VRS-native replacement for the Sparrow `BinSeparator` pattern.

The separator does **not** build a `LayoutState` or `SolverOutput`.  It takes a
`WorkingLayout` as input (which may contain overlapping or boundary-violating
placements) and returns a `WorkingLayout` that is as close to violation-free as
possible, plus a `VrsSeparatorDiagnostics` record.

---

## Relationship to WorkingLayout

```
WorkingLayout (may have violations)
    │
    ▼
VrsSeparator::run(layout, parts, sheets)
    │  — deterministic relocation loop —
    ▼
(WorkingLayout, VrsSeparatorDiagnostics)
    │
    │  (if best_loss == 0)
    ▼
WorkingLayout.validate_and_commit(parts, sheets)
    │
    ▼
(Vec<Placement>, Vec<Unplaced>)   ← violation-free accepted output
```

- The separator never calls `validate_and_commit` itself.
- The caller is responsible for the commit gate after the separator returns.
- If `best_loss > 0` the separator could not fully resolve conflicts; the caller
  must decide whether to commit the best partial state or discard it.

---

## Collision loss model V1

`VrsCollisionTracker` computes pair losses as the intersection area of two
bounding boxes that are on the same sheet:

```rust
fn bbox_overlap_area(a: &PlacedBbox, b: &PlacedBbox) -> f64 {
    if a.sheet_index != b.sheet_index { return 0.0; }
    let dx = (a.x2.min(b.x2) - a.x1.max(b.x1)).max(0.0);
    let dy = (a.y2.min(b.y2) - a.y1.max(b.y1)).max(0.0);
    dx * dy
}
```

- Items on different sheets never contribute pair loss.
- Adjacent (touching) items contribute 0.0 pair loss.
- `total_loss()` is the sum of all pair losses plus all boundary losses.
- `total_weighted_loss()` applies GLS weights to each pair and boundary term.

---

## Boundary loss policy V1

An item's boundary loss is a positive constant proxy (`BOUNDARY_LOSS_PROXY = 1.0`) when:
- `sheet_index >= sheets.len()` (invalid sheet), OR
- `bbox_from_placement()` returns `None` (invalid rotation or unknown part), OR
- `rect_within_boundary(rect, sheet)` returns `false` (outside sheet shape).

When the item is boundary-valid: `boundary_loss(i) = 0.0`.

This proxy is intentionally coarse for V1.  SGH-03 and later may refine it to
a distance-to-boundary metric.

---

## GLS-like weight update V1

Weights are maintained per (i, j) pair and per item boundary.  The update rule
mirrors Guided Local Search Algorithm 8 from the Sparrow paper:

```
weight(i, j) ← min(weight(i,j) + 1 / (1 + weight(i,j) × decay), weight_max)
```

`update_weights()` is called only on rollback (when no improving move is found).
This increases the weighted cost of persistent collisions, steering subsequent
iterations toward resolving them.

Initial weights are 1.0 for all pairs and boundaries.  Weights grow monotonically
(capped at `gls_weight_max`).  They are never reset across iterations.

---

## Separator loop

```
config: max_strikes, max_inner_iterations, gls_weight_decay, gls_weight_max
```

```
if total_loss == 0 → return immediately (converged)

while iterations < max_inner_iterations AND strikes < max_strikes:
    colliders ← tracker.colliding_indices()
    if empty → break (converged)

    target ← argmax_i colliders: weighted_loss_for_item(i)
        (tie broken by index → deterministic)

    placed_without ← bboxes for all placements except target

    candidates ← generate_candidates_with_sheets(sheets, placed_without)
        (deterministic, sorted sheet→y→x)

    best_cand ← candidate minimising sum of bbox_overlap_area against placed_without,
        skipping boundary-invalid positions (rect_within_boundary check)

    if no candidate found:
        strikes++; update_weights()

    elif new_loss < current_loss:
        accept move; update best_snapshot if new_loss < best_loss; strikes ← 0 or ++

    else:
        rollback; strikes++; update_weights()

return best_snapshot
```

The separator always terminates: bounded by `max_inner_iterations` and `max_strikes`.
There is no RNG in V1 — the loop is fully deterministic for identical inputs.

---

## Commit and rollback rules

- **Snapshot:** `WorkingLayout::snapshot()` (full `Clone`) is taken whenever a
  new global-best is found.
- **Rollback:** when a move does not reduce `total_loss`, the placement is
  restored to `old_placement`, and the tracker's bbox/boundary_valid for that
  item are restored via `tracker.restore_item()`.
- **Commit:** the caller, not the separator, calls `WorkingLayout::validate_and_commit()`.
  The separator returns the best found `WorkingLayout` (may still have violations
  if the problem was not fully resolved).

Rule: **the separator never calls `validate_and_commit` internally**.

---

## Scope exclusions

The following are explicitly out of scope for SGH-02:

- Integration into `initializer.rs` LBF construction.
- Integration into `sheet_elimination.rs`.
- `moves.rs` transfer/swap execution between sheets.
- `MultiSheetManager` changes.
- `io.rs` or `SolverOutput` changes.
- Python runner or exact validator changes.
- Continuous rotation (only 0/90/180/270° are supported).
- Solution pool or perturbation (SGH-06).
- External SparrowGH backend adapter.

---

## Preparation for SGH-03 / SGH-04

SGH-03 (LBF + separator construction) will call `VrsSeparator::run()` after
placing each item in the LBF loop if a collision is introduced.  The separator
returns a `WorkingLayout` that LBF can inspect before committing.

SGH-04 (sheet elimination + separator) will call `VrsSeparator::run()` after
redistributing items from the eliminated sheet, to resolve any collisions
introduced by redistribution.

Both SGH-03 and SGH-04 will use `WorkingLayout::validate_and_commit()` as the
gate before accepting the result.

The `VrsCollisionTracker` may be extended in SGH-03/SGH-04 with:
- Per-pair loss caching (incremental update instead of O(n²) rebuild).
- Distance-to-boundary metric instead of the proxy constant.
- Weighted candidate scoring (not just overlap area minimisation).
