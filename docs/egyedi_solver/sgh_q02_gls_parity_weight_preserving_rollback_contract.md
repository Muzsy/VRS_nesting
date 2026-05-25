# SGH-Q02 GLS parity + weight-preserving rollback contract

## Decision

SGH-Q02 replaces the additive GLS formula in `VrsCollisionTracker::update_weights` with a
multiplicative formula matching Sparrow Algorithm 8. It also introduces `LossSnapshot` /
`snapshot_loss` / `restore_but_keep_weights` for weight-preserving rollback at every failed
tentative move in `VrsSeparator::run`.

**Mandatory decisions from SGH-Q01 preserved:**
- SGH-06 remains PAUSED.
- No multi-worker, no stochastic ordering, no phase orchestration (SGH-Q03+).
- No new PROXY introduced without `// QUALITY_RISK:` annotation.
- All G01–G08 gates satisfied.

---

## Source Sparrow feature mapping

| Sparrow component | VRS equivalent after SGH-Q02 |
|---|---|
| `tracker.rs` Algorithm 8 `update_weights()` | `VrsCollisionTracker::update_weights()` |
| `GLS_WEIGHT_DECAY` (multiplicative decay, no-collision) | `VrsSeparatorConfig::gls_weight_decay` (default 0.98) |
| `GLS_WEIGHT_MIN_INC_RATIO` (min multiplier) | `VrsSeparatorConfig::gls_weight_min_inc_ratio` (default 1.01) |
| `GLS_WEIGHT_MAX_INC_RATIO` (max multiplier, max-loss pair) | `VrsSeparatorConfig::gls_weight_max_inc_ratio` (default 1.05) |
| `restore_but_keep_weights()` | `VrsCollisionTracker::restore_but_keep_weights(LossSnapshot)` |
| `snapshot_loss_state()` | `VrsCollisionTracker::snapshot_loss()` |

---

## VRS implementation summary

**File changed:** `rust/vrs_solver/src/optimizer/separator.rs`

Changes:
1. New `LossSnapshot` pub struct (bboxes + boundary_valid, no weights).
2. `VrsSeparatorConfig`: two new pub fields `gls_weight_min_inc_ratio` + `gls_weight_max_inc_ratio`; `gls_weight_decay` default changed from 0.01 (additive param) to 0.98 (multiplicative param).
3. `VrsCollisionTracker::update_weights` signature: added `min_inc_ratio: f64, max_inc_ratio: f64` params. Implementation: multiplicative formula with max_loss normalization.
4. `VrsCollisionTracker::snapshot_loss()` + `restore_but_keep_weights(LossSnapshot)` added.
5. `VrsCollisionTracker::pair_weight` visibility: private → `pub`. New `boundary_weight` pub accessor.
6. `VrsSeparator::run()` rollback: replaced per-item `restore_item` with `snapshot_loss()` + `restore_but_keep_weights(snap)`.
7. AdditiveGlsProxy `// QUALITY_RISK:` annotation removed from `update_weights` (formula now matches Sparrow Algorithm 8).

---

## GLS formula

### Old (SGH-Q01, additive proxy):
```rust
*w = (*w + 1.0 / (1.0 + *w * decay)).min(weight_max)
```

### New (SGH-Q02, multiplicative, Sparrow Algorithm 8):
```
max_loss = max over all active pair/boundary losses

for each pair/boundary:
  if loss == 0:
    new_weight = max(old_weight * decay, 1.0)        // decay, floor at 1.0
  else:
    ratio = loss / max_loss                           // ∈ [0, 1]
    mult = min_inc_ratio + (max_inc_ratio - min_inc_ratio) * ratio
    new_weight = min(old_weight * mult, weight_max)  // increase, cap at weight_max
```

**Key properties:**
- Max-loss pair/boundary always gets multiplier = `max_inc_ratio`.
- Lower-loss pairs get proportionally smaller increment.
- Non-colliding pairs with existing entries decay back toward 1.0.
- Non-colliding pairs with no entry: no entry created (no memory waste).

---

## Config semantics

| Field | Type | Default | Semantics |
|---|---|---|---|
| `gls_weight_decay` | f64 | 0.98 | Multiplicative decay per iteration for non-colliding entries. Was 0.01 (additive param, different semantics). |
| `gls_weight_max` | f64 | 100.0 | Maximum weight cap. Unchanged. |
| `gls_weight_min_inc_ratio` | f64 | 1.01 | Multiplier for the smallest-loss colliding pair in each iteration. |
| `gls_weight_max_inc_ratio` | f64 | 1.05 | Multiplier for the largest-loss colliding pair in each iteration. |
| `max_strikes` | usize | 20 | Unchanged. |
| `max_inner_iterations` | usize | 200 | Unchanged. |
| `allowed_sheet_indices` | Option<Vec<usize>> | None | Unchanged. |

**Backward compat:** `..VrsSeparatorConfig::default()` struct update syntax continues to work. No public field removed or renamed.

---

## Collision/boundary weight handling

Both pair weights and boundary weights use the same multiplicative formula:
- Boundary violation (BOUNDARY_LOSS_PROXY = 1.0) is treated as a loss value in the same pool as pair losses.
- `max_loss` is computed across the union of all boundary and pair losses.
- When boundary loss == 1.0 and it is the only active loss, ratio = 1.0 → multiplier = max_inc_ratio.

---

## restore_but_keep_weights contract

```rust
pub struct LossSnapshot {
    bboxes: Vec<Option<PlacedBbox>>,
    boundary_valid: Vec<bool>,
}

impl VrsCollisionTracker {
    pub fn snapshot_loss(&self) -> LossSnapshot { ... }
    pub fn restore_but_keep_weights(&mut self, snap: LossSnapshot) { ... }
}
```

**Invariants:**
- After `restore_but_keep_weights(snap)`: `self.bboxes == snap.bboxes` and `self.boundary_valid == snap.boundary_valid`.
- `self.pair_weights` and `self.boundary_weights` are NOT modified by restore.
- `total_loss()` after restore equals the loss computed from `snap.bboxes` / `snap.boundary_valid`.

---

## Rollback invariants

In `VrsSeparator::run`, at each failed tentative move:

```rust
let old_placement = current.placements[target_idx].clone();
let loss_snap = tracker.snapshot_loss();

current.placements[target_idx] = new_p;
tracker.update_placement(target_idx, &current, parts, sheets);
let new_loss = tracker.total_loss();

if new_loss >= current_loss {
    // Rollback: restore layout AND loss-state, keep GLS weights.
    current.placements[target_idx] = old_placement;
    tracker.restore_but_keep_weights(loss_snap);
    tracker.update_weights(...);   // runs on unchanged weights + original loss-state
}
```

After rollback:
- `current.placements[target_idx]` == pre-move placement.
- `tracker.bboxes[target_idx]` and `tracker.boundary_valid[target_idx]` == pre-move state.
- `pair_weights` and `boundary_weights` == accumulated value (not restored).
- `update_weights` correctly reads the restored loss-state when computing new multipliers.

---

## Tests and acceptance gates

| # | Test | Gate |
|---|---|---|
| 11 | `multiplicative_gls_larger_loss_gets_larger_weight` | G01, req #1 |
| 12 | `multiplicative_gls_max_loss_pair_gets_max_ratio` | G01, req #2 |
| 13 | `multiplicative_gls_no_collision_decay` | G01, req #3 |
| 14 | `multiplicative_gls_boundary_weight_updates` | G01, req #4 |
| 15 | `restore_but_keep_weights_preserves_gls` | G01, req #5 |
| 16 | `multiplicative_gls_no_spurious_entries_for_zero_loss` | G01 |
| (existing) | `separator_fixes_simple_overlap` → best_loss == 0.0 | G01, req #6 |
| (existing) | `separator_is_deterministic` | G01, G05, req #7 |

All 146 tests pass (`cargo test --lib`). `verify.sh` exit 0 (G02).

---

## Remaining quality gaps after SGH-Q02

| Feature | Status before | Status after |
|---|---|---|
| F07 GLS dynamic weights | PARTIAL (additive) | **FULL** (multiplicative + max_loss normalization + decay) |
| F08 Separator incumbent / restore | PARTIAL | **PARTIAL→improved** (restore_but_keep_weights at every rollback point) |
| F09 multi-worker (SGH-Q03) | MISSING | MISSING (next task) |
| F02 stochastic sampling | MISSING | MISSING |
| F11–F14 phase orchestration | MISSING/PARTIAL | MISSING (SGH-Q04) |

---

## Next task: SGH-Q03

SGH-Q03 will implement `move_items_multi` with N parallel `SeparatorWorker` instances (rayon `par_iter_mut`), stochastic item-order shuffle per worker, and best-worker-wins weighted loss selection.

Dependency: SGH-Q02 PASS (this document).
