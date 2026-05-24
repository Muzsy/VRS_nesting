# SGH-03 LBF + separator construction contract

## Purpose

SGH-03 integrates two new construction strategies into the initial layout phase of the VRS solver:

1. **LBF-scored clear candidate selection** — replaces the earlier "accept first valid candidate" heuristic with an explicit, deterministic scoring that prefers compaction (bottom-left placement on already-used sheets).
2. **Separator fallback** — when no collision-free LBF candidate exists, attempts to resolve conflicts using `VrsSeparator` (from SGH-02) inside a `WorkingLayout` before committing.

SGH-03 accepted output must remain violation-free. Separator fallback may use an infeasible `WorkingLayout` internally, but never commits it unless `validate_for_commit` passes.

---

## Current initializer gap

Before SGH-03, `build_initial_layout()` used a **first-valid-candidate** approach: for each instance (ordered by area descending), it iterated candidates in sheet→y→x order, checked boundary validity and collision freedom, and accepted the first candidate that passed. This is equivalent to a basic First-Fit Decreasing (FFD) packer, without explicit scoring or any recovery mechanism for items that cannot be placed without collision.

Known gaps:
- No preference for already-used sheets (unnecessary sheet-count growth).
- No LBF (lowest-y, lowest-x) tie-breaking among valid candidates.
- No fallback when all candidates produce collisions.
- `ConstructionDiagnostics` did not track LBF or separator activity.

---

## LBF candidate scoring V1

### Algorithm

For each instance, collect all candidate points from `generate_candidates_with_sheets()`. For each candidate × rotation:

1. Call `dims_for_rotation()` to get (w, h).
2. Call `rect_within_boundary()` to check boundary validity.
3. Check collision freedom: the candidate bbox must not overlap any entry in `placed_bboxes` (via `PlacedBbox::overlaps()`).
4. If all checks pass, compute the **LBF key**:
   - `is_unused`: `true` if the candidate's sheet has zero placed items, `false` if already used.
   - `(is_unused, y_min, x_min, sheet_index)`

5. If this key is better than the current best (lower = better), update the best candidate.
6. Only the first valid rotation per candidate point is considered (stable rotation order, no duplicate scoring).

### Priority order (lower = better)

```
primary:   is_unused = false  beats  is_unused = true
secondary: smaller y_min
tertiary:  smaller x_min
quaternary: smaller sheet_index
tie:       stable (first-encountered rotation, then instance_id)
```

This ensures the solver fills already-opened sheets before opening new ones, while placing items as low-left as possible on the chosen sheet.

### Key functions

- `generate_candidates_with_sheets()` — deterministic, EPS-deduped, sorted by sheet→y→x.
- `rect_within_boundary()` — canonical boundary policy.
- `dims_for_rotation()` + `placement_anchor_from_rect_min()` — geometry helpers.
- `PlacedBbox::overlaps()` — collision check.
- `lbf_select_clear_candidate()` — private helper in `initializer.rs`.

---

## Separator fallback V1

### Trigger

Separator fallback is attempted only when `lbf_select_clear_candidate()` returns `None` (no collision-free candidate found).

### Steps

1. **Seed sheet selection** (`find_seed_sheet_index()`): Among used sheets (sheets with ≥1 placed item), choose the one with the most free estimated area (`sheet.area - placed_area_on_sheet`). If no used sheet exists, default to sheet index 0.

2. **Seed placement**: Use the first rotation that fits at origin `(0.0, 0.0)` on the seed sheet (boundary-valid), or fall back to the first supported rotation regardless. Compute the anchor via `placement_anchor_from_rect_min(0.0, 0.0, ...)`.

3. **WorkingLayout construction**: Build `WorkingLayout::new()` from the list `current_placements + [seed_placement]`. This layout may contain overlaps — WorkingLayout explicitly allows infeasible states.

4. **VrsSeparator run**: Call `VrsSeparator::new(VrsSeparatorConfig::default()).run(working, parts, sheets)` to attempt collision resolution. The separator uses GLS-like weights and a deterministic relocation loop.

5. **Commit gate**: Accept the fallback result only if:
   - `sep_diag.best_loss == 0.0 || sep_diag.converged == true`, **and**
   - `working.validate_for_commit(parts, sheets)` returns `Ok(...)`.

6. **Success path**: Extract the committed placements, rebuild the entire `placed_bboxes` cache via `rebuild_placed_bboxes()`, and update `used_sheets` from scratch.

7. **Failure path**: Leave `current_placements`, `placed_bboxes`, and `used_sheets` unchanged. Mark the current instance as `Unplaced` with reason `NO_CANDIDATE`.

### Key invariant

The separator fallback may move previously placed items (it operates on the full WorkingLayout). The `placed_bboxes` cache must be fully rebuilt after a successful fallback — incremental updates are not sufficient.

---

## Commit/rollback rules

| Situation | Action |
|---|---|
| LBF clear candidate found | Accept. Append to `placements` + `placed_bboxes`. |
| Separator fallback succeeds (commit gate passes) | Replace all `placements`, rebuild full `placed_bboxes`. |
| Separator fallback fails (loss > 0 or validate fails) | Rollback: `placements`/`placed_bboxes` unchanged. Item → Unplaced. |
| Separator fallback rejected by commit gate | Increment `separator_fallback_rejected_by_commit_gate`. Item → Unplaced. |

The public signature of `build_initial_layout()` is unchanged:

```rust
pub fn build_initial_layout(
    instances: &[Instance],
    parts: &[Part],
    sheets: &[SheetShape],
) -> (Vec<Placement>, Vec<Unplaced>, ConstructionDiagnostics)
```

---

## Diagnostics

`ConstructionDiagnostics` was extended with the following fields:

```rust
pub lbf_candidates_scored: usize,
pub lbf_clear_accepts: usize,
pub separator_fallback_attempts: usize,
pub separator_fallback_successes: usize,
pub separator_fallback_failures: usize,
pub separator_fallback_rejected_by_commit_gate: usize,
```

The `summary()` method outputs these alongside existing fields:

```
... lbf_scored=N lbf_clear=N sep_attempts=N sep_ok=N sep_fail=N sep_commit_reject=N
```

The existing pre-SGH-03 fields (`candidates_tried`, `rejected_boundary`, `rejected_collision`, `irregular_*`) remain unchanged.

---

## Scope exclusions

The following were explicitly excluded from SGH-03:

- `sheet_elimination.rs` — not modified.
- `moves.rs` — transfer/swap execution not implemented.
- `multisheet.rs` — not rewritten.
- `score.rs` — objective model not changed.
- `io.rs` — solver IO contract unchanged.
- `adapter.rs` — not modified.
- Python runner / exact validator — not modified.
- External SparrowGH backend — not added.
- Sparrow/SparrowGH vendor/submodule — not added.
- Continuous rotation — not introduced.
- Solution pool / perturbation — not introduced.

---

## Preparation for SGH-04

SGH-03 establishes the construction baseline that SGH-04 will build on:

- The `ConstructionDiagnostics` new fields expose LBF and separator activity, making it possible to tune or replace the fallback strategy in SGH-04.
- `rebuild_placed_bboxes()` is a reusable private helper that any future post-construction repair or improvement step can call after bulk placement changes.
- `VrsSeparator` is now exercised inside the construction loop. SGH-04 can extend this to multi-item separator passes or sheet-level recovery.
- The `used_sheets` tracking pattern inside `build_initial_layout()` is the natural hook for sheet-count-aware strategies in SGH-04 (e.g., deferred sheet opening, sheet score coupling).
- The commit/rollback discipline established here (no partial accept, no best-effort invalid output) must be preserved by all SGH-04 move operators.
