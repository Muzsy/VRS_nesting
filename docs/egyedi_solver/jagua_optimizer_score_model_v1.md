# ScoreModel V1 — Phase 1 Rectangular Nesting Objective

## Overview

The Phase 1 ScoreModel V1 is a minimization objective function for the VRS rectangular nesting solver. Lower `total_cost` is better.

Implemented in: `rust/vrs_solver/src/optimizer/score.rs`

## Score direction

**Minimization**: lower `total_cost` is always strictly better.

`is_better(a, b)` returns `true` if and only if `a.total_cost < b.total_cost`.

## Components and default weight profile

| Component | Field | Default weight | Sign |
|---|---|---|---|
| Placed area reward | `placed_area_reward` | 1.0 | Negative (reward) |
| Unplaced penalty | `unplaced_penalty_per_item` | 1,000,000.0 | Positive |
| Sheet count penalty | `sheet_count_penalty_per_sheet` | 10,000.0 | Positive |
| Overlap penalty | `overlap_penalty_per_pair` | 1,000,000,000.0 | Positive |
| Boundary penalty | `boundary_penalty_per_item` | 1,000,000,000.0 | Positive |
| Compactness weight | `compactness_weight` | 0.001 | Positive |

```
total_cost =
  - placed_area * placed_area_reward
  + unplaced_count * unplaced_penalty_per_item
  + sheet_count_used * sheet_count_penalty_per_sheet
  + overlap_violations * overlap_penalty_per_pair
  + boundary_violations * boundary_penalty_per_item
  + compactness_proxy * compactness_weight
```

## Penalty hierarchy

```
overlap / boundary  (1e9)  >  unplaced  (1e6)  >  sheet_count  (1e4)  >
placed_area_reward  (1.0)  >  compactness  (0.001)
```

This hierarchy guarantees that **no combination of quality improvements (placed area, compactness) can make an invalid layout score better than a valid one**.

## Component definitions

### Placed area reward

`placed_area` = sum of `rotated_width * rotated_height` for all placed instances.

Only rectangularly-placed items count (Phase 1: no holes, no irregular polygons).
Contributes `-(placed_area * placed_area_reward)` to cost.

### Unplaced penalty

`unplaced_count` = `len(unplaced)` from the `Vec<Unplaced>` output.

Any item in the unplaced list (regardless of reason: `NO_CAPACITY`, `REPAIR_FAILED`, etc.) incurs the full penalty. This incentivizes placing all items.

### Sheet count penalty

`sheet_count_used` = `max(sheet_index) + 1` over all placed items. Zero if no items are placed.

Penalizes spreading items across many sheets. Does not override validity penalties.

### Overlap penalty

Detected via `find_violations()` from `optimizer/repair.rs`, which performs a sequential scan identifying items whose bboxes overlap an earlier valid item's bbox on the same sheet.

`overlap_violations` = count of `ViolationType::Overlap` entries.

### Boundary penalty

Also detected via `find_violations()`: items with `sheet_index >= sheets.len()` or whose bbox falls outside `rect_inside_sheet_shape()`.

`boundary_violations` = count of `ViolationType::BoundaryOrSheet` entries.

### Compactness proxy

Per used sheet:
```
proxy_per_sheet = max(0, bounding_rect_area - sum(item_areas_on_sheet))
```
where `bounding_rect_area` is the area of the minimum axis-aligned rectangle containing all placed item bboxes on that sheet.

`compactness_proxy` = sum over all used sheets.

Weight (0.001) is intentionally tiny — this is a **tie-breaker only**. A single unplaced item (1,000,000 cost) is equivalent to 1,000,000,000 units² of compactness waste (36 km² at 1mm²/unit). In practice, compactness only differentiates layouts that are otherwise score-equivalent.

## Invalid layout policy

Invalid layouts (with overlap or boundary violations) always score strictly worse than valid layouts. This is enforced by the penalty magnitude: a single violation incurs 1e9 cost, which exceeds any realistic placed_area reward or compactness contribution.

**Invalid layout can never be reported as success.** The exact validation bridge (`validate_multi_sheet_output` in Python, running on the final output) remains the definitive gate.

## Determinism

`score_layout()` is deterministic: given identical `placements`, `unplaced`, `parts`, and `sheets` arguments, the output is bit-identical. No RNG dependency. All iteration over vectors is in stable insertion order.

## ObjectiveBreakdown

`ObjectiveBreakdown` provides full per-component auditability:

```rust
pub struct ObjectiveBreakdown {
    pub placed_count: usize,
    pub unplaced_count: usize,
    pub sheet_count_used: usize,
    pub placed_area: f64,
    pub overlap_violations: usize,
    pub boundary_violations: usize,
    pub compactness_proxy: f64,
    pub placed_area_contribution: f64,   // negative (reward)
    pub unplaced_contribution: f64,
    pub sheet_count_contribution: f64,
    pub overlap_contribution: f64,
    pub boundary_contribution: f64,
    pub compactness_contribution: f64,
    pub total_cost: f64,
}
```

## Known limitations

- Phase 1 only: rectangular items, 0/90/180/270° rotations. No irregular polygon area used.
- `placed_area` is computed as `rotated_w * rotated_h` — proxy area, not actual polygon area.
- Compactness proxy is coarse: bounding-rect gap, not actual nesting density.
- Weight profile is hand-tuned for Phase 1. JG-12/JG-13 may expose tuning opportunities.
- No stagnation detection in the score model itself — that is the StoppingPolicy's responsibility.

## Relation to future tasks

- **JG-12 (multi-sheet manager)**: ScoreModel V1 will be used to compare layouts across multi-sheet attempts.
- **JG-13 (benchmark)**: ScoreModel V1 outputs will appear in benchmark tables alongside utilization.
- **JG-14 (phase gate)**: Gate decisions will use ScoreModel V1 as the objective reference.
- Weight tuning is out of scope for JG-11. The profile is designed to be correct, not optimal.
