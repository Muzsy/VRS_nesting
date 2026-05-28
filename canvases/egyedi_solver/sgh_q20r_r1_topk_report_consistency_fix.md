# SGH-Q20R-R1 — search_position top-k coordinate descent + report consistency fix

## Status

Corrective task after Q20R audit.

Q20R is partially successful: `optimizer/search_position.rs` exists, `VrsSeparator::find_best_candidate_for_target` calls it before the old `generate_candidates_with_sheets` path, CDE/Jagua evaluation uses the active backend, unsupported samples are rejected, and diagnostics are propagated.

However, the Q20R report/checklist claim things that are not true in code:

1. `SearchPositionConfig` does **not** contain `refine_top_k` / `coord_descent_top_k`.
2. There is no `TransformCandidate` struct.
3. `search_position_for_target()` refines only the single best sample found, via one `coord_descent_from(...)` call.
4. The report explicitly claims top-k refinement with default k=3, but the source has no such field or loop.

This is not a full rollback. Q20R stays, but it needs R1 before we treat it as a clean Sparrow `search_position` kernel.

## Goal

Make Q20R truthful and stronger:

```text
sample candidates globally/focused
→ keep deterministic evaluated candidates
→ sort/tie-break them deterministically
→ refine top-k candidates with coordinate descent
→ choose best refined candidate
→ keep CDE/Jagua no-bbox-fallback invariant
→ fix report/checklist so they match the code
```

## Non-goals

Do not do:

```text
Q21 shape-aware collision severity
Q22 exploration/compression shrink-loop redesign
Q19 LV8 acceptance benchmark
Q18B CDE session/cache rewrite
main solver hole-aware collision
```

## Required code changes

### 1. SearchPositionConfig

Add a real top-k field, for example:

```rust
pub refine_top_k: usize,
```

or:

```rust
pub coord_descent_top_k: usize,
```

Default should be `3`, unless you document a better repo-consistent value.

### 2. TransformCandidate

Introduce a concrete candidate struct, for example:

```rust
struct TransformCandidate {
    sheet_index: usize,
    rect_min_x: f64,
    rect_min_y: f64,
    rotation_deg: f64,
    eval: f64,
    placement: Placement,
}
```

It can stay private if public API is not needed, but the checklist/report must be accurate.

### 3. Candidate collection

Replace the current one-best-only variables:

```rust
best_loss
best_x
best_y
best_rot
best_sheet
```

with a deterministic finite candidate collection.

Required behavior:

```text
global samples are evaluated and collected when finite
focused samples are evaluated and collected when finite
unsupported samples are counted and rejected
candidate list is sorted by eval ascending
tie-breaker is deterministic: sheet_index, rotation bits, x bits, y bits, instance/part if needed
cap the list to top-k before coordinate descent
```

If a zero-loss sample is found, do not claim top-k refinement unless top-k refinement is actually skipped intentionally and documented. Prefer not to early-return before at least preserving deterministic top-k behavior for nonzero-loss cases.

### 4. Top-k coordinate descent

Refine up to `refine_top_k` / `coord_descent_top_k` finite candidates.

Required:

```text
stats.refined_samples increments once per refined candidate
stats.coord_descent_steps accumulates all descent steps
best refined candidate selected deterministically
non-improving descent candidate cannot worsen selected eval
incumbent layout is not mutated during refinement
rotation axis only for Continuous
```

### 5. Tests

Add or update tests:

```text
search_position_refines_top_k_candidates_when_configured
search_position_top_k_tie_break_is_deterministic
search_position_refine_top_k_zero_disables_refinement_or_is_rejected_by_config_validation
search_position_reported_refined_samples_matches_top_k_for_nonzero_loss_fixture
search_position_existing_cde_no_bbox_fallback_still_passes
separator_search_position_reduces_simple_overlap_still_passes
```

Use a fixture with unavoidable nonzero loss, such as a full-sheet blocker, so top-k refinement is forced.

### 6. Report/checklist consistency

Fix:

```text
codex/reports/egyedi_solver/sgh_q20r_sparrow_search_position_coord_descent.md
codex/codex_checklist/egyedi_solver/sgh_q20r_sparrow_search_position_coord_descent.md
```

The report must no longer claim nonexistent fields or nonexistent top-k behavior.

Create a new R1 report:

```text
codex/reports/egyedi_solver/sgh_q20r_r1_topk_report_consistency_fix.md
codex/reports/egyedi_solver/sgh_q20r_r1_topk_report_consistency_fix.verify.log
```

## Verification

Run at least:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::search_position
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::compress
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q20r_sparrow_search_position.py
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q20r_r1_topk_report_consistency_fix.md
```

## PASS criteria

PASS only if:

```text
Q20R search_position remains primary separator path
real top-k refinement is implemented or the report/checklist no longer claims it
CDE/Jagua active backend evaluation still has no silent bbox fallback
search_position_lbf_fallback_used remains explicit and counted
new top-k tests pass
cargo test --lib passes
Q20R smoke passes
verify.sh passes
```

## Report markers

First line must be one of:

```text
PASS
REVISE
BLOCKED
```

PASS markers:

```text
SGH-Q20R_R1_STATUS: READY_FOR_AUDIT
SGH-Q21_STATUS: READY
Q19_STATUS: HOLD
Q18B_RECOMMENDATION: REQUIRED|NOT_REQUIRED_NOW|INCONCLUSIVE_NEEDS_BIGGER_FIXTURE
```
