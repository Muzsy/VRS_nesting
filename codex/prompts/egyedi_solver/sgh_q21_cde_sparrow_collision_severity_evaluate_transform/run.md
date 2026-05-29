# Runner — SGH-Q21 CDE/Sparrow collision severity + evaluate_transform score

You are working in the `VRS_nesting` repo. Implement SGH-Q21 according to:

```text
canvases/egyedi_solver/sgh_q21_cde_sparrow_collision_severity_evaluate_transform.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q21_cde_sparrow_collision_severity_evaluate_transform.yaml
codex/codex_checklist/egyedi_solver/sgh_q21_cde_sparrow_collision_severity_evaluate_transform.md
```

## Hard dependency gate

Before edits, read:

```text
codex/reports/egyedi_solver/sgh_q20r_r1_topk_report_consistency_fix.md
```

It must start with `PASS` and contain:

```text
SGH-Q21_STATUS: READY
```

If not, stop with a `BLOCKED` report.

## Goal

Q20R created the Sparrow-style `search_position()` relocation kernel. Q21 must fix the next core gap: candidate and tracker scoring still rely on bbox/proxy severity after backend-confirmed collision existence.

Implement a central backend-aware collision severity / evaluate_transform layer and route both `search_position` and separator/GLS loss through it.

## Must-read code

```text
rust/vrs_solver/src/optimizer/search_position.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/loss_model.rs
rust/vrs_solver/src/optimizer/collision_backend.rs
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/optimizer/phase.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/adapter.rs
```

## Required implementation

### 1. Central severity/evaluate_transform module

Add a module such as:

```text
rust/vrs_solver/src/optimizer/collision_severity.rs
```

The exact API can follow repo style, but it must centralize:

```text
pair severity
boundary severity
candidate transform evaluation
stats/diagnostics
unsupported handling
```

Avoid duplicating another local bbox-eval path in `search_position.rs`.

### 2. Backend policy

Bbox backend:

```text
preserve legacy loss_model behavior.
```

CDE/Jagua backend:

```text
placement_overlaps / placement_within_sheet decide collision/boundary existence.
NoCollision -> severity 0.
Unsupported -> reject or hard unsupported loss, with diagnostics.
Collision -> backend-confirmed severity.
```

If exact depth is unavailable, implement deterministic oracle-probe severity estimation:

```text
try translations in +x/-x/+y/-y,
find smallest step that resolves collision according to active backend,
convert it to smooth severity.
```

This is acceptable as Q21 v1 if clearly documented and tested.

### 3. SearchPosition integration

Replace or delegate these local helpers:

```text
eval_with_backend_trait
eval_candidate_loss
```

Candidate ranking should use the shared evaluate_transform result.

Preserve:

```text
unsupported -> reject / f64::MAX
zero loss early return behavior if still valid
coord_descent_top_k behavior from Q20R-R1
CDE bbox_fallback_queries == 0 invariant
```

### 4. Separator/GLS integration

`VrsCollisionTracker` pair and boundary losses must use backend-confirmed severity under exact/CDE backends.

Required:

```text
pair_loss(i,j) returns backend-confirmed severity under CDE/Jagua.
boundary_loss(i) returns backend-confirmed severity under CDE/Jagua.
update_weights() uses these values.
weighted_loss_for_item() uses these values.
colliding_indices() uses these values.
```

Do not leave collision severity under CDE/Jagua as bbox-only source-of-truth.

### 5. Diagnostics

Expose severity diagnostics through optimizer/adapter output.

Suggested fields:

```text
collision_severity_backend
collision_severity_enabled
collision_severity_pair_queries
collision_severity_boundary_queries
collision_severity_probe_queries
collision_severity_backend_confirmed_collisions
collision_severity_backend_confirmed_no_collisions
collision_severity_unsupported_queries
collision_severity_bbox_proxy_uses
```

Exact names may vary, but the report must map them.

## Tests

Add/ensure tests for:

```text
collision_severity_bbox_backend_preserves_legacy_pair_loss
collision_severity_exact_backend_no_collision_zeroes_bbox_false_positive
collision_severity_exact_backend_collision_returns_positive_severity
collision_severity_shallow_vs_deep_collision_is_monotonic
collision_severity_boundary_valid_is_zero
collision_severity_boundary_violation_positive
collision_severity_unsupported_returns_hard_loss_or_reject
search_position_uses_collision_severity_engine
separator_tracker_uses_backend_confirmed_pair_severity
separator_tracker_weight_update_uses_backend_severity
cde_path_reports_no_bbox_collision_source_of_truth
q20r_search_position_smoke_still_passes
```

Names can differ, but map them in the report.

## Smoke

Create:

```text
scripts/smoke_sgh_q21_collision_severity.py
```

It must cover:

```text
shallow vs deep overlap severity
bbox false-positive exact no-collision -> zero severity
boundary violation positive severity
search_position ranking affected by severity
CDE path diagnostics + bbox_fallback_queries == 0
```

Keep this small. Do not run LV8 here.

## Verify

Run at least:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::collision_severity
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::search_position
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator
cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q20r_sparrow_search_position.py
python3 scripts/smoke_sgh_q21_collision_severity.py
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q21_cde_sparrow_collision_severity_evaluate_transform.md
```

No false PASS. If a required command cannot run, report `BLOCKED` or `REVISE` with exact reason.

## Report

Create:

```text
codex/reports/egyedi_solver/sgh_q21_cde_sparrow_collision_severity_evaluate_transform.md
codex/reports/egyedi_solver/sgh_q21_cde_sparrow_collision_severity_evaluate_transform.verify.log
```

First line must be exactly:

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

PASS report must include:

```text
SGH-Q21_STATUS: READY_FOR_AUDIT
SGH-Q22_STATUS: READY|HOLD
Q19_STATUS: HOLD
Q18B_RECOMMENDATION: REQUIRED|NOT_REQUIRED_NOW|INCONCLUSIVE_NEEDS_BIGGER_FIXTURE
```
