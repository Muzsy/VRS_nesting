# Phase 2 Irregular/Remnant Benchmark — JG-20

PHASE2_GATE_DECISION: PASS

- **solver_bin:** `/home/muszy/projects/VRS_nesting/rust/vrs_solver/target/release/vrs_solver`
- **seed:** 42
- **profile:** `jagua_optimizer_phase1_outer_only`
- **date:** 2026-05-24

## Case results

| case_id | status | placed | unplaced | sheets | utilization | dur_s | validation | stock_type |
|---------|--------|--------|----------|--------|-------------|-------|------------|------------|
| l_shape | pass | 4 | 0 | 1 | 0.1185 | 0.00 | pass | irregular |
| concave_remnant | pass | 4 | 0 | 1 | 0.1185 | 0.00 | pass | irregular |
| mixed_rectangular_remnant | pass | 3 | 0 | 1 | 0.1875 | 0.00 | pass | mixed |
| rectangular_phase1_regression | pass | 9 | 0 | 1 | 0.3733 | 0.00 | pass | rectangular |

## Score breakdown (Phase 1 profile)

| case_id | total_cost | placed_area_contrib | sheet_cost_contrib | sheet_cost_total | usable_area_util | overlap | boundary |
|---------|-----------|--------------------|--------------------|-----------------|-----------------|---------|----------|
| l_shape | 8000.00 | -2000.00 | 10000.00 | 1.00 | 0.1185 | 0.00 | 0.00 |
| concave_remnant | 0.00 | -2000.00 | 2000.00 | 0.20 | 0.1185 | 0.00 | 0.00 |
| mixed_rectangular_remnant | 2500.00 | -7500.00 | 10000.00 | 1.00 | 0.1875 | 0.00 | 0.00 |
| rectangular_phase1_regression | -1191.20 | -11200.00 | 10000.00 | 1.00 | 0.3733 | 0.00 | 0.00 |

## Boundary rejects

Boundary reject counts are not exposed in `solver_output.json` v1 (not a standard meta field).
Proxy evidence: `score_breakdown.boundary_contribution` = 0.0 for all valid placements above,
confirming no boundary violations accepted.

## Invalid boundary fail evidence

- Source: `smoke_jagua_irregular_boundary_validation.py (JG-17 boundary policy)`
- Result: **PASS** (exit=0)

```
  PASS: cargo test PASS (97 tests)

[Check 10: JG-16 smoke regression (smoke_jagua_irregular_sheet_provider.py)]
  PASS: JG-16 smoke PASS (smoke_jagua_irregular_sheet_provider.py)

[Check 11: Exact validation bridge regression (smoke_jagua_exact_validation_bridge.py)]
  PASS: exact validation bridge PASS

=== RESULTS: 11 PASS, 0 FAIL ===
OVERALL: PASS
```

## Validation evidence

All accepted layouts carry `validation_status=pass` from the exact Python validation bridge.
`validation_status=fail` results are marked as `status=fail` and not accepted as successful benchmarks.

## Rectangular Phase 1 regression

Case `rectangular_phase1_regression` replicates the JG-14 'small' fixture.
If this case passes, rectangular Phase 1 behavior is unaffected by Phase 2 irregular/remnant changes.

## Gate 2 decision

**PHASE2_GATE_DECISION: PASS**

Decision rules:
- PASS: all required Phase 2 cases ran, all accepted layouts validation_status=pass,
  rectangular regression PASS, invalid boundary fail evidence present.
- REVISE: partial results or non-critical gap (boundary evidence not confirmed).
- STOP: any invalid layout accepted as success or rectangular regression fails.

