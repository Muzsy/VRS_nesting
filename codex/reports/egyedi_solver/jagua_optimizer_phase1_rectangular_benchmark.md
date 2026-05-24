# Phase 1 Rectangular Benchmark — JG-14

PHASE1_GATE_DECISION: PASS

- **solver_bin:** `/home/muszy/projects/VRS_nesting/rust/vrs_solver/target/release/vrs_solver`
- **seed:** 42
- **profile:** `jagua_optimizer_phase1_outer_only`
- **baseline:** row/cursor fallback (no `solver_profile`)

## Case results

| case_id | status | placed | unplaced | sheets | utilization | dur_s | validation | baseline_status |
|---------|--------|--------|----------|--------|-------------|-------|------------|-----------------|
| smoke | pass | 2 | 0 | 1 | 0.180 | 0.00 | pass | available |
| small | pass | 9 | 0 | 1 | 0.373 | 0.00 | pass | available |
| medium | pass | 3 | 3 | 3 | 0.490 | 0.00 | pass | available |
| realistic_no_hole | pass | 26 | 0 | 2 | 0.832 | 0.00 | pass | available |

## Baseline compare

Baseline: row/cursor fallback path in `adapter.rs` (no `solver_profile` set).
This is the only repo-supported alternative solver path.

| case_id | baseline_placed | baseline_sheets | baseline_util | baseline_dur_s |
|---------|----------------|-----------------|---------------|----------------|
| smoke | 2 | 1 | 0.180 | 0.00 |
| small | 9 | 1 | 0.373 | 0.00 |
| medium | 3 | 3 | 0.490 | 0.00 |
| realistic_no_hole | 26 | 2 | 0.832 | 0.00 |

## Validation evidence

All accepted layouts carry `validation_status=pass` from the exact validation bridge.
Any `validation_status=fail` case is reported as status=fail and not accepted as success.

## Phase 1 gate decision

**PHASE1_GATE_DECISION: PASS**

Decision rules:
- PASS: all required fixtures ran, all accepted layouts validation_status=pass.
- REVISE: infrastructure works, but quality/metrics need improvement.
- STOP: any invalid layout accepted (validation_status=fail).

