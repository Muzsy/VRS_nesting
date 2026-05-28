# Runner — SGH-Q20R-R1 top-k coordinate descent + report consistency fix

Fix the Q20R discrepancy found by code audit.

## Problem

Q20R report/checklist claim real top-k coordinate descent:

```text
config.coord_descent_top_k / refine_top_k, default k=3
TransformCandidate struct
top-k refinement
```

But the current source only refines one best sample:

```rust
stats.refined_samples += 1;
let (cd_x, cd_y, cd_rot, cd_loss) = coord_descent_from(best_x, best_y, best_rot, best_loss, ...);
```

There is no `refine_top_k`, `coord_descent_top_k`, or `TransformCandidate` in `optimizer/search_position.rs`.

## Task

Implement real top-k coordinate descent or make the report/checklist truthful. Preferred: implement it.

Required:

1. Add `refine_top_k` or `coord_descent_top_k` to `SearchPositionConfig`.
2. Add a real candidate struct.
3. Collect finite global/focused candidates.
4. Sort/tie-break deterministically.
5. Refine top-k candidates.
6. Select the best refined candidate.
7. Keep CDE/Jagua no-bbox-fallback behavior.
8. Add tests proving top-k behavior.
9. Fix Q20R report/checklist and create R1 report.

## Verify

Run:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::search_position
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::compress
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q20r_sparrow_search_position.py
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q20r_r1_topk_report_consistency_fix.md
```

## Report markers

PASS report must contain:

```text
SGH-Q20R_R1_STATUS: READY_FOR_AUDIT
SGH-Q21_STATUS: READY
Q19_STATUS: HOLD
Q18B_RECOMMENDATION: REQUIRED|NOT_REQUIRED_NOW|INCONCLUSIVE_NEEDS_BIGGER_FIXTURE
```
