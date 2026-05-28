# SGH-Q20R — Sparrow `search_position()` + coordinate descent port, updated after Q20

## Context after original Q20

The original SGH-Q20 ran and passed. Do **not** discard it. It added useful prerequisites:

```text
RotationPolicy::Continuous deterministic 16-sample linspace
continuous_refinement_angles(...)
CompressionPhase local rotation refinement
rotation_refinement_* diagnostics
Q20 smoke evidence and CDE bbox_fallback_queries == 0 regression
```

However, Q20 did **not** port the central Sparrow positioning logic. The main separator still relocates colliding target items through finite LBF/bbox candidate points:

```text
rust/vrs_solver/src/optimizer/separator.rs
VrsSeparator::find_best_candidate_for_target(...)
  -> generate_candidates_with_sheets(...)
```

That is the remaining architectural mismatch. Sparrow-style optimization should search candidate transforms in continuous `(x, y, rotation)` space, evaluate through the active collision backend, and refine top candidates with coordinate descent. Q20R must build that missing kernel and wire it into `VrsSeparator`.

## Dependency gate

Required reports must be PASS/READY:

```text
codex/reports/egyedi_solver/sgh_q16_cde_final_commit_gate_consistency_fix.md
codex/reports/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability.md
codex/reports/egyedi_solver/sgh_q18a_r1_phase_timing_report_consistency_fix.md
codex/reports/egyedi_solver/sgh_q20_continuous_rotation_refinement.md
```

The Q20 report must contain:

```text
SGH-Q20_STATUS: READY_FOR_AUDIT
```

If missing, stop with `BLOCKED` and no production changes.

## Goal

Implement VRS-native Sparrow `search_position()`:

```text
colliding target item selected by existing VrsSeparator / GLS logic
→ deterministic transform sampling in continuous sheet space
→ backend-aware evaluation with CDE/Jagua/Bbox policy
→ top-k coordinate descent over x/y and rotation if allowed
→ best transform returned to VrsSeparator
→ existing GLS commit/rollback/weight update behavior preserved
```

This task replaces the separator's LBF/bbox candidate search as the **default PhaseOptimizer/Sparrow separator path**. A compatibility fallback may remain, but it must be explicit, counted, documented, and not silently used as the primary path.

## Non-goals

Do not implement now:

```text
Q19 LV8 acceptance benchmark gate
Q18B CDE session/cache rewrite
full Q21 shape-based collision severity rewrite
main solver hole-aware collision
multi-sheet objective redesign
full Sparrow strip-shrink algorithm
```

Q20R may still use existing bbox/smooth severity as a temporary scoring proxy **after** active-backend collision existence is queried. That gap must be documented as Q21.

## Required implementation

### 1. New module

Create:

```text
rust/vrs_solver/src/optimizer/search_position.rs
```

Export it from `rust/vrs_solver/src/optimizer/mod.rs`.

Suggested public API, adapt to repo style if needed:

```rust
pub struct SearchPositionConfig {
    pub global_sample_count: usize,
    pub focused_sample_count: usize,
    pub refine_top_k: usize,
    pub translation_step_init: f64,
    pub translation_step_min: f64,
    pub rotation_step_init_deg: f64,
    pub rotation_step_min_deg: f64,
    pub max_coord_descent_iters: usize,
    pub allow_lbf_fallback: bool,
}

pub struct SearchPositionDiagnostics {
    pub calls: usize,
    pub global_samples_evaluated: usize,
    pub focused_samples_evaluated: usize,
    pub samples_supported: usize,
    pub samples_unsupported: usize,
    pub refined_samples: usize,
    pub coord_descent_steps: usize,
    pub backend_boundary_queries: usize,
    pub backend_pair_queries: usize,
    pub lbf_fallback_used: usize,
    pub best_eval: f64,
}

pub struct TransformCandidate {
    pub sheet_index: usize,
    pub x: f64,
    pub y: f64,
    pub rotation_deg: f64,
    pub eval: f64,
}
```

### 2. Sampling

Sampling must include both:

```text
global uniform sheet samples
focused samples around the current placement
```

Sampling must be deterministic for:

```text
solver seed
iteration
worker_id
target instance_id
target_idx
```

Rotation handling:

```text
Locked/HalfTurn/Orthogonal/FortyFive/Discrete: only legal angles from resolved policy
Continuous: use Q20 coarse continuous candidate list + Q20 continuous_refinement_angles + coordinate descent rotation axis
```

Do not create illegal rotations for non-continuous policies.

### 3. Backend-aware evaluation

For each sample candidate:

1. Convert bbox-min sample to placement anchor using existing rotation helpers.
2. Check boundary using active backend:
   - Bbox: existing bbox boundary logic allowed.
   - JaguaPolygonExact/CDE: backend `placement_within_sheet`.
3. Check pair collisions with active backend:
   - Bbox: existing bbox loss allowed.
   - JaguaPolygonExact/CDE: backend `placement_overlaps`.
4. Unsupported means reject candidate / max eval.
5. CDE/Jagua must not silently downgrade to bbox.

Until Q21, collision severity can reuse existing `LossModelKind`/bbox proxy for collided pairs, but collision existence must come from the active backend. Document this explicitly.

### 4. Coordinate descent

Refine top-k candidates.

Axes:

```text
x + step, x - step
y + step, y - step
rotation + step, rotation - step only when effective policy is Continuous
```

Required behavior:

```text
step-halving or equivalent convergence rule
max iteration cap
candidate remains within active backend boundary
unsupported candidates rejected
incumbent layout never mutated during refinement
result deterministic
```

### 5. VrsSeparator integration

Modify `VrsSeparator::find_best_candidate_for_target(...)` or replace it cleanly.

Required behavior:

```text
search_position is used before generate_candidates_with_sheets
LBF/bbox finite candidates are not the default PhaseOptimizer/Sparrow path anymore
fallback, if retained, is explicit and diagnostic-counted
existing GLS pair/boundary weights remain active
existing restore_but_keep_weights behavior remains active
worker_count / worker_seed determinism preserved
allowed_sheet_indices honored
```

A good minimal integration:

```text
find_best_candidate_for_target
  -> SearchPosition::search(...)
  -> if Some(best) return placement
  -> if allow_lbf_fallback then old generate_candidates_with_sheets path with lbf_fallback_used += 1
  -> else None
```

### 6. Diagnostics

Extend separator/phase/optimizer diagnostics with search-position data.

Minimum output/report fields:

```text
search_position_calls
search_position_global_samples_evaluated
search_position_focused_samples_evaluated
search_position_samples_unsupported
search_position_refined_samples
search_position_coord_descent_steps
search_position_best_eval
search_position_lbf_fallback_used
```

If output struct bloat is a concern, at least keep these in `VrsSeparatorDiagnostics` and map the most important ones to `OptimizerDiagnosticsOutput`. The report must show evidence.

### 7. Tests

Required tests:

```text
search_position_global_sampling_is_deterministic
search_position_focused_sampling_is_deterministic
search_position_respects_non_continuous_rotation_policy
search_position_uses_q20_continuous_candidates
search_position_continuous_uses_rotation_axis_in_coord_descent
search_position_rejects_backend_unsupported_samples
search_position_uses_cde_backend_without_bbox_fallback
separator_uses_search_position_before_lbf_candidates
separator_search_position_reduces_simple_overlap
coord_descent_improves_or_preserves_candidate_eval
q20_rotation_refinement_regression_still_passes
```

### 8. Smoke

Create:

```text
scripts/smoke_sgh_q20r_sparrow_search_position.py
```

Minimum smoke scenarios:

```text
1. two overlapping rectangles: separator reduces/removes overlap using search_position
2. boundary-violating item: search_position returns an in-boundary placement
3. Continuous rotation rescue: CDE/phase path can place or improve a case orthogonal cannot
4. CDE backend: bbox_fallback_queries == 0 and search_position_lbf_fallback_used == 0 for primary path
5. determinism: repeated runs with same seed produce identical JSON/canonical diagnostics
```

## Verification commands

Run at least:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::search_position
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::compress
cargo test --manifest-path rust/vrs_solver/Cargo.toml rotation_policy
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q20_continuous_rotation_refinement.py
python3 scripts/smoke_sgh_q20r_sparrow_search_position.py
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q20r_sparrow_search_position_coord_descent.md
```

## PASS criteria

PASS only if all are true:

```text
Q20 remains green.
SearchPosition module exists and is used by VrsSeparator.
The primary separator path no longer depends on generate_candidates_with_sheets.
LBF fallback, if retained, is explicit and counted.
CDE/Jagua sample evaluation does not silently fallback to bbox.
Continuous rotation reuses Q20 candidate/refinement infrastructure.
Coordinate descent over x/y and Continuous rotation exists.
GLS rollback/update behavior remains intact.
Determinism smoke is green.
Smoke proves simple overlap/boundary/continuous/CDE cases.
cargo test --lib and verify.sh are green.
```

## Report markers

Create:

```text
codex/reports/egyedi_solver/sgh_q20r_sparrow_search_position_coord_descent.md
codex/reports/egyedi_solver/sgh_q20r_sparrow_search_position_coord_descent.verify.log
```

First line must be exactly one of:

```text
PASS
REVISE
BLOCKED
```

PASS markers:

```text
SGH-Q20R_STATUS: READY_FOR_AUDIT
SGH-Q21_STATUS: READY
Q19_STATUS: HOLD
Q18B_RECOMMENDATION: REQUIRED|NOT_REQUIRED_NOW|INCONCLUSIVE_NEEDS_BIGGER_FIXTURE
```
