# JG-19 Remnant Score Model V1

## Overview

JG-19 extends the Phase 1 ScoreModel with remnant/sheet-cost awareness. The goal is a
V1 nesting objective proxy that makes the solver prefer cheaper (remnant) sheets over
full new sheets when both options produce valid layouts.

This is **not** a final inventory/costing system. It is a V1 proxy to enable
testable, explainable sheet-choice behaviour for mixed normal + remnant stock scenarios.

## Sheet-cost metadata strategy (V1 proxy/inference)

### Decision

JG-19 uses **explicit optional `cost_per_use` on `Stock`**, backed by inference default.

Rationale: The `Stock` struct already carries material-specific metadata (`width`, `height`,
`outer_points`). Adding an optional `cost_per_use: Option<f64>` is backward-compatible (via
`#[serde(default)]`) and makes the cost semantics explicit in the input JSON without requiring
a full inventory/costing schema.

### `Stock.cost_per_use` field

```json
{
  "id": "remnant_A3",
  "width": 297,
  "height": 420,
  "quantity": 3,
  "cost_per_use": 0.2
}
```

- `None` (or absent from JSON) → defaults to `1.0`.
- Clamped to `>= 0.0` in `stock_to_shape`.
- Propagated to `SheetShape.cost_per_use: f64`.
- This is a **V1 nesting proxy** — it is not a material price, an inventory asset, or an ERP field.

### Inference default

Absent `cost_per_use` → `1.0`. This preserves exact backward-compatibility with all existing
fixtures and tests: `sheet_count_contribution` = `sheet_cost_total * weight` = `sheet_count_used * weight`.

## Default weight profile

| Component | Default weight | Notes |
|---|---|---|
| `placed_area_reward` | 1.0 | Reward per unit² |
| `unplaced_penalty_per_item` | 1_000_000.0 | Strong incentive to place all |
| `sheet_count_penalty_per_sheet` | 10_000.0 | Applied as `sheet_cost_total * weight` (JG-19) |
| `overlap_penalty_per_pair` | 1_000_000_000.0 | Validity guard — dominates all |
| `boundary_penalty_per_item` | 1_000_000_000.0 | Validity guard — dominates all |
| `compactness_weight` | 0.001 | Tie-breaker only |

## Penalty hierarchy (unchanged)

```
overlap/boundary (1e9) >> unplaced (1e6) >> sheet_cost (1e4 * cost_per_use) >> placed_area (1.0) >> compactness (0.001)
```

An invalid layout (overlap or boundary violation) **always** scores worse than any valid layout,
regardless of sheet cost savings. Remnant preference cannot override validity.

## ObjectiveBreakdown JG-19 additions

Two new fields in `optimizer::score::ObjectiveBreakdown`:

| Field | Type | Meaning |
|---|---|---|
| `sheet_cost_total` | `f64` | Sum of `cost_per_use` for each used sheet slot |
| `usable_area_utilization` | `f64` | `placed_area / total_used_sheet_area` in [0, 1] |

`sheet_count_contribution` is now `sheet_cost_total * sheet_count_penalty_per_sheet` instead
of `sheet_count_used * sheet_count_penalty_per_sheet`. For all-default-cost fixtures this is
identical (backward-compat).

## ScoreBreakdownOutput in JSON (JG-19)

For `solver_profile = jagua_optimizer_phase1_outer_only`, the `SolverOutput` now includes
an optional `score_breakdown` field:

```json
{
  "score_breakdown": {
    "total_cost": -3000.0,
    "placed_area_contribution": -7500.0,
    "unplaced_contribution": 0.0,
    "sheet_cost_contribution": 2000.0,
    "sheet_cost_total": 0.2,
    "usable_area_utilization": 0.1875,
    "overlap_contribution": 0.0,
    "boundary_contribution": 0.0,
    "compactness_contribution": 4500.0
  }
}
```

This field is absent for legacy profiles (`skip_serializing_if = "Option::is_none"`) — no
breaking change to existing clients.

## Sheet-choice decision example

Scenario: 3 × 50×50 items, two available sheets (200×200 bbox):
- Sheet 0: `cost_per_use = 1.0` (full regular sheet)
- Sheet 1: `cost_per_use = 0.2` (remnant)

Score comparison (same valid placement, only sheet differs):

| Scenario | sheet_cost_total | sheet_cost_contribution | total_cost |
|---|---|---|---|
| Items on regular sheet | 1.0 | 1.0 × 10,000 = 10,000 | ~2,500 |
| Items on remnant sheet | 0.2 | 0.2 × 10,000 = 2,000 | ~-5,500 |

Score model prefers remnant (lower total_cost). If the BLF construction places all items on
sheet 0 (regular), the layout is still valid; the score model correctly signals that using the
remnant would have been cheaper, guiding future SA/optimization iterations.

## Invalid-vs-valid dominance evidence

`test_invalid_layout_dominates_over_remnant_benefit` (score.rs):
- Valid layout on regular sheet: `total_cost ≈ -500`
- Overlapping layout on remnant (cost=0.001): `overlap_contribution = 1e9` → `total_cost >> 1e9`
- Valid layout ALWAYS wins, regardless of remnant cost savings.

## SheetSummary JG-19 addition

`optimizer::multisheet::SheetSummary` now includes `sheet_usable_area: f64` (from
`SheetShape.area`). Available for diagnostic use in `MultiSheetDiagnostics`.

## Utilization interpretation

`usable_area_utilization = placed_area / total_used_sheet_area`:
- 1.0: all usable area is covered by items (theoretical maximum for non-overlapping rectangular items).
- 0.0: no items placed.
- Typical Phase 1 values: 0.15–0.75 depending on item mix and sheet dimensions.

For irregular sheets, `sheet.area` is the polygon area (shoelace formula), not the bbox area.

## What JG-19 is NOT

- Not a final inventory/costing system or ERP integration.
- Not a material price model or quote calculator.
- Not a remnant tracking system (no persistence or remnant ID management).
- Not a new boundary validator or candidate generator.
- `cost_per_use` is a V1 nesting optimization hint — the solver is free to use any valid sheet.

## Next steps

JG-20: Phase 2 irregular/remnant benchmark matrix — uses the JG-19 score model to evaluate
optimized layouts on mixed regular + remnant fixture sets.
