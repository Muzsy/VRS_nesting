# Runner — SGH-Q21R1 full Sparrow-aligned collision severity hardening

You are working in the `VRS_nesting` repo.

## Mission

Do not implement a minimal fix. The target is the full jagua_rs/Sparrow-aligned collision severity/evaluate_transform core.

Q21 added a useful first layer, but it is not enough. Q21R1 must harden it into a reliable solver-core component that future SparrowState / separation / exploration-compression tasks can build on.

If you cannot implement the full requirements, report `REVISE`. Do not mark PASS for partial work.

## Required reading

Read first:

```text
codex/reports/egyedi_solver/sgh_q21_cde_sparrow_collision_severity_evaluate_transform.md
codex/reports/egyedi_solver/sgh_q21_cde_sparrow_collision_severity_evaluate_transform.verify.log
codex/codex_checklist/egyedi_solver/sgh_q21_cde_sparrow_collision_severity_evaluate_transform.md
canvases/egyedi_solver/sgh_q21_cde_sparrow_collision_severity_evaluate_transform.md
canvases/egyedi_solver/sgh_q21r1_collision_severity_full_sparrow_alignment.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q21r1_collision_severity_full_sparrow_alignment.yaml
rust/vrs_solver/src/optimizer/collision_severity.rs
rust/vrs_solver/src/optimizer/search_position.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/phase.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/adapter.rs
scripts/smoke_sgh_q21_collision_severity.py
```

## Hard requirements

### 1. Config and defaults

`CollisionSeverityConfig` must support industrial-scale, precise probe behavior:

```rust
probe_max_initial_step_mm
probe_bracket_growth
probe_binary_refine_steps
probe_tolerance_mm
probe_use_diagonal_directions
probe_use_center_direction
probe_use_pair_center_direction
```

The effective initial probe step must be capped:

```text
initial_step = min(sheet_diag * factor, probe_max_initial_step_mm)
initial_step = max(initial_step, probe_min_step)
```

No 1500×3000 sheet should start with a 167 mm step by default.

### 2. Multi-direction adaptive oracle probe

Replace cardinal-only probe with deterministic multi-direction probe.

Pair collision directions:

```text
cardinal + diagonal + pair-center-away
```

Boundary directions:

```text
cardinal + diagonal + sheet-center
```

Each direction must use:

```text
bracket first clear distance
binary-refine between last colliding and first clear
return best refined resolution distance
```

Do not just double the step and return the first clear step as the final severity.

### 3. Complete accounting

Every severity-purpose backend query must be counted:

```text
pair_queries
boundary_queries
probe_queries
probe_pair_queries or documented pair query inclusion
probe_boundary_queries or documented boundary query inclusion
unsupported_queries
probe_resolved/probe_unresolved/probe_unsupported if implemented
```

This includes:

```text
evaluate_transform_loss
oracle pair probe
oracle boundary probe
VrsCollisionTracker::compute_backend_decisions
VrsCollisionTracker::update_backend_decisions_for_item
```

No `Unsupported { .. } => break` without stats.

### 4. Unsupported loss contract

Use `cfg.hard_unsupported_loss` for scoring unsupported cases. Do not leak `f64::MAX` as the public severity/evaluation loss when a config value exists.

### 5. No bbox source-of-truth under exact backends

Under `Cde` and `JaguaPolygonExact`:

```text
backend NoCollision => no collision severity, even if bbox overlaps;
backend Collision => oracle-probe severity;
bbox proxy severity only if probe explicitly disabled or backend is Bbox;
bbox proxy uses must be counted.
```

### 6. Integration

Ensure `search_position`, `separator` tracker/GLS, `phase`, `adapter`, and output diagnostics all use and expose the improved severity stats.

Do not create a parallel scoring layer that bypasses the central `collision_severity` contract.

## Required tests

Add tests or map existing tests to all of these:

```text
severity_initial_step_is_capped_on_large_sheet
severity_pair_probe_uses_diagonal_and_pair_center_directions
severity_boundary_probe_uses_diagonal_and_sheet_center_directions
severity_probe_binary_refines_resolution_distance
severity_probe_unsupported_increments_unsupported_queries
severity_tracker_counts_pair_and_boundary_queries
severity_tracker_update_counts_pair_and_boundary_queries
severity_hard_unsupported_loss_used_instead_of_f64_max
severity_bbox_false_positive_exact_backend_no_collision_zero_loss
severity_bbox_proxy_only_when_explicitly_enabled_or_bbox_backend
search_position_uses_improved_severity_stats
separator_gls_uses_improved_backend_confirmed_severity
```

## Required smoke

Expand `scripts/smoke_sgh_q21_collision_severity.py` with at least:

```text
large sheet capped/binary refined small-overlap severity
bbox false-positive exact/CDE no-collision
confirmed pair collision probe stats
boundary violation probe stats
unsupported geometry stats + hard loss
tracker build/update query accounting
search_position CDE/Jagua no bbox fallback
```

## Verification

Run:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::collision_severity
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::search_position
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator
cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q20r_sparrow_search_position.py
python3 scripts/smoke_sgh_q21_collision_severity.py
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q21r1_collision_severity_full_sparrow_alignment.md
```

If any required command fails or cannot run, do not claim PASS unless an equivalent repo-standard evidence path is provided and justified.

## Report

Create:

```text
codex/reports/egyedi_solver/sgh_q21r1_collision_severity_full_sparrow_alignment.md
codex/reports/egyedi_solver/sgh_q21r1_collision_severity_full_sparrow_alignment.verify.log
```

The first line must be exactly:

```text
PASS
```

or:

```text
REVISE
```

or:

```text
BLOCKED
```

PASS requires these markers:

```text
SGH-Q21R1_STATUS: READY_FOR_AUDIT
SGH-Q21_STATUS: READY_FOR_AUDIT
SGH-Q22_STATUS: READY
Q19_STATUS: HOLD
Q18B_RECOMMENDATION: REQUIRED|NOT_REQUIRED_NOW|INCONCLUSIVE_NEEDS_BIGGER_FIXTURE
```

PASS report must explicitly document:

```text
changed files
config defaults and rationale
multi-direction directions
bracket + binary refinement evidence
query/probe/unsupported accounting evidence
hard_unsupported_loss evidence
bbox false-positive no-collision evidence
search_position/separator integration evidence
tests and command results
known limitations
```

Known limitations that are NOT allowed in PASS:

```text
cardinal-only probe
no binary refinement
uncapped 5% sheet diagonal initial step
unsupported probe not counted
tracker query count missing
f64::MAX public unsupported loss
bbox proxy source-of-truth under CDE/Jagua
```
