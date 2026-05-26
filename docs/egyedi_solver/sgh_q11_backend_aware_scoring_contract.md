# SGH-Q11 Backend-Aware Scoring + Separator Loss Path Contract

## Overview

Q11 wires `CollisionBackendKind` through the PhaseOptimizer's internal search paths so that when `jagua_polygon_exact` is specified, the internal search (separator, score model, move executor, exploration/compression/BPP phases) uses exact geometry rather than only bbox.

## What changed

### `PhaseConfig.collision_backend`

`PhaseConfig` gains a `pub collision_backend: CollisionBackendKind` field (default: `Bbox`). The adapter propagates it from `SolverInput.collision_backend` via `phase_config_from_input`. All internal phases and helpers receive this config and route through it.

### `validate_placements_for_backend` (repair.rs)

Central no-fallback helper used by all internal search paths:

| Backend | Behaviour |
|---|---|
| `Bbox` | Delegates to `find_violations` — pre-Q11 behaviour unchanged |
| `JaguaPolygonExact` | Uses `JaguaPolygonExactBackend`; if `unsupported_queries > 0`, appends sentinel `(usize::MAX, BoundaryOrSheet)` so `is_empty()` correctly rejects |
| `Cde` | Always `Unsupported`; sentinel always appended |

The sentinel pattern ensures callers checking `violations.is_empty()` can never silently accept an unsupported result.

### `ScoreModel::score_with_backend` (score.rs)

```rust
pub fn score_with_backend(
    &self,
    placements: &[Placement],
    unplaced: &[Unplaced],
    parts: &[Part],
    sheets: &[SheetShape],
    backend_kind: &CollisionBackendKind,
) -> ScoreResult
```

- `Bbox` → bit-identical to `score()` (no change to existing callers)
- Non-Bbox → `validate_placements_for_backend` provides violations; `score_layout_from_violations` computes the score from those violations

`score_layout_from_violations` is a new `pub(super)` helper that allows reuse between `score_layout` (bbox path) and `score_with_backend` (exact/cde path).

### `MoveExecutor` (moves.rs)

- New field: `collision_backend: CollisionBackendKind` (default `Bbox`)
- New constructor: `new_with_backend_and_rotation_context`
- `commit_gate_ok`: now calls `validate_placements_for_backend(..., &self.collision_backend)` instead of `find_violations`
- `run_separator_fix`: passes `collision_backend: self.collision_backend.clone()` to `VrsSeparatorConfig`

### `VrsSeparatorConfig` and `VrsCollisionTracker` (separator.rs)

- `VrsSeparatorConfig.collision_backend: CollisionBackendKind` (default `Bbox`)
- `VrsCollisionTracker::build_with_model` takes an additional `collision_backend: CollisionBackendKind` parameter
- Q11 transitional loss strategy:
  - `NoCollision` → `pair_loss = 0`
  - `Collision` → bbox surrogate loss (unchanged)
  - `Unsupported` → hard penalty `1_000_000.0`

### `ExplorationPhase`, `CompressionPhase`, `BppPhase`

All three phases now:
- Pass `collision_backend: self.config.collision_backend.clone()` to `VrsSeparatorConfig`
- Create `MoveExecutor` via `new_with_backend_and_rotation_context`
- Replace `find_violations` with `validate_placements_for_backend(..., &self.config.collision_backend)`
- Replace `score_model.score` with `score_model.score_with_backend(..., &self.config.collision_backend)` where applicable

## No-silent-bbox-fallback guarantee

For any internal search path:
- `collision_backend = Bbox` → behaviour identical to pre-Q11
- `collision_backend = JaguaPolygonExact` → exact polygon geometry used for all commit gates and scoring; no silent fallback to bbox
- `collision_backend = Cde` → all commit gates reject (always Unsupported); layout stays unchanged

## Backward compatibility

- `PhaseConfig::deterministic_default()` sets `collision_backend = Bbox` — no behaviour change for existing callers
- All existing constructors (`MoveExecutor::new`, `MoveExecutor::new_with_rotation_context`, `LargeItemSwapDisruption::new_with_rotation_context`) default to `Bbox`
- No breaking JSON output changes

## Parts without `outer_points`

For `JaguaPolygonExact`: parts without `outer_points` use a rect polygon path (`rect_polygon_from_placement`), which is exact for axis-aligned items. These parts do NOT trigger `Unsupported`. Only degenerate `outer_points` (e.g. fewer than 3 points) return `Unsupported`.
