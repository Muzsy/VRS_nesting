# Runner — SGH-Q20R Sparrow search_position + coordinate descent, updated after Q20

## Purpose

Implement the actual Sparrow positioning kernel on top of the completed Q20 rotation refinement work.

Q20 was useful, but it did not replace the separator's finite LBF/bbox candidate search. Q20R must add and wire a `search_position()`-style module: global/focused transform sampling, coordinate descent, active-backend evaluation, and separator integration.

## Dependency gate

Before edits, read:

```text
codex/reports/egyedi_solver/sgh_q16_cde_final_commit_gate_consistency_fix.md
codex/reports/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability.md
codex/reports/egyedi_solver/sgh_q18a_r1_phase_timing_report_consistency_fix.md
codex/reports/egyedi_solver/sgh_q20_continuous_rotation_refinement.md
```

If Q20 is not PASS / `SGH-Q20_STATUS: READY_FOR_AUDIT`, stop with BLOCKED.

## Required source audit

Read:

```text
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/candidates.rs
rust/vrs_solver/src/optimizer/collision_backend.rs
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/optimizer/loss_model.rs
rust/vrs_solver/src/optimizer/compress.rs
rust/vrs_solver/src/optimizer/phase.rs
rust/vrs_solver/src/rotation_policy.rs
rust/vrs_solver/src/item.rs
```

Confirm in the report:

```text
VrsSeparator::find_best_candidate_for_target still calls generate_candidates_with_sheets.
Q20 added continuous_refinement_angles and compression diagnostics, but not Sparrow search_position.
```

## Implementation

### 1. Create `optimizer/search_position.rs`

Implement config, diagnostics, transform candidates, deterministic seed mixing, global/focused sampling, active-backend evaluation, and coordinate descent.

### 2. Sampling

Required:

```text
global uniform sheet samples
focused samples around current placement
same seed/instance/iteration/worker -> same candidates
allowed_sheet_indices honored
```

Rotation:

```text
Use Q20 resolved rotation candidates.
Continuous may use rotation-axis coordinate descent.
Non-continuous policies must never get illegal angles.
```

### 3. Coordinate descent

Axes:

```text
x ± step
y ± step
rotation ± step only for Continuous
```

Use step halving or equivalent. Never mutate the incumbent while refining a candidate.

### 4. Active backend evaluation

Use active backend boundary and pair checks. Unsupported means reject/max eval. CDE/Jagua must not fallback to bbox for collision existence. Existing bbox/smooth severity proxy is allowed only as a documented Q21 gap after backend collision existence has been established.

### 5. Separator integration

`VrsSeparator::find_best_candidate_for_target` should use SearchPosition first.

If `generate_candidates_with_sheets` remains, it must be an explicit compatibility fallback:

```text
allow_lbf_fallback = true/false
search_position_lbf_fallback_used counter
report evidence that primary path did not use fallback in smoke
```

Preserve GLS:

```text
restore_but_keep_weights
pair/boundary weight updates
worker_count determinism
worker_seed behavior
```

### 6. Diagnostics

Expose at least:

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

### 7. Required tests

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

Cover:

```text
overlap reduction
boundary correction
continuous rotation rescue
CDE no bbox fallback
no primary LBF fallback used
determinism
```

## Verify

Run:

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

## Report

Create:

```text
codex/reports/egyedi_solver/sgh_q20r_sparrow_search_position_coord_descent.md
codex/reports/egyedi_solver/sgh_q20r_sparrow_search_position_coord_descent.verify.log
```

First line: `PASS`, `REVISE`, or `BLOCKED`.

PASS markers:

```text
SGH-Q20R_STATUS: READY_FOR_AUDIT
SGH-Q21_STATUS: READY
Q19_STATUS: HOLD
Q18B_RECOMMENDATION: REQUIRED|NOT_REQUIRED_NOW|INCONCLUSIVE_NEEDS_BIGGER_FIXTURE
```
