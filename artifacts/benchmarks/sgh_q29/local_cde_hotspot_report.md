# SGH-Q29 Phase B: Local CDE Hotspot Profiler Report

**Status: PASS**

Profile flag: `SGH_Q29_CDE_PROFILE=1`

## Notes on measurement coverage

- **hazard_loss_ms**: not separately timed; hazard quantification is inside CDE query path (cde_query_collect_ms). Timing both would add overhead without additional insight.
- **deregister_reregister_ms**: deregister measured in search.rs (allowed file); reregister is in worker.rs (not in Q29 allowed file list). Combined metric partially available.
- **session_build_ms**: only fallback/cross-sheet session builds measured (most expensive path); primary live-session is built once per worker pass in worker.rs.
- **specialized_pipeline_ms**: same code path as cde_query_collect_ms (collect_poly_collisions_in_detector_custom); reported as alias.

## Case: medium

- Status: ok
- Runtime: 2583 ms
- Placed: 25
- Final pairs: 0
- Iterations: 1
- Search calls: 0
- Profiling enabled: True
- Search total ms: 0.0

### Cost breakdown (% of search_total_ms)

| Component | ms | % | Bar |
|-----------|-----|---|-----|
| cde_query_collect_ms | 0.0 | 0.0% | ░░░░░░░░░░░░░░░░░░░░ |
| candidate_transform_prepare_ms | 0.0 | 0.0% | ░░░░░░░░░░░░░░░░░░░░ |
| session_build_ms | 0.0 | 0.0% | ░░░░░░░░░░░░░░░░░░░░ |
| deregister_ms | 0.0 | 0.0% | ░░░░░░░░░░░░░░░░░░░░ |
| boundary_check_ms | 0.0 | 0.0% | ░░░░░░░░░░░░░░░░░░░░ |
| other_unaccounted_ms | 0.0 | 0.0% | ░░░░░░░░░░░░░░░░░░░░ |

### Profile fields

| Field | Value |
|-------|-------|
| native_search_calls | 0 |
| candidates_evaluated | 0 |
| session_build_ms | 0.0 |
| deregister_reregister_ms | 0.0 |
| candidate_transform_prepare_ms | 0.0 |
| cde_query_collect_ms | 0.0 |
| specialized_pipeline_ms | 0.0 |
| hazard_loss_ms | not_available — hazard quantification is inside cde_query_collect; not separately timed to avoid double overhead |
| boundary_check_ms | 0.0 |
| broadphase_reject_count | 0 |
| early_termination_count | 0 |

## Case: lv8_subset

- Status: ok
- Runtime: 15847 ms
- Placed: 67
- Final pairs: 0
- Iterations: 1
- Search calls: 11
- Profiling enabled: True
- Search total ms: 137.679

### Cost breakdown (% of search_total_ms)

| Component | ms | % | Bar |
|-----------|-----|---|-----|
| other_unaccounted_ms | 122.4 | 88.9% | ██████████████████░░ |
| cde_query_collect_ms | 10.2 | 7.4% | █░░░░░░░░░░░░░░░░░░░ |
| candidate_transform_prepare_ms | 3.2 | 2.4% | ░░░░░░░░░░░░░░░░░░░░ |
| boundary_check_ms | 1.8 | 1.3% | ░░░░░░░░░░░░░░░░░░░░ |
| deregister_ms | 0.1 | 0.0% | ░░░░░░░░░░░░░░░░░░░░ |
| session_build_ms | 0.0 | 0.0% | ░░░░░░░░░░░░░░░░░░░░ |

### Profile fields

| Field | Value |
|-------|-------|
| native_search_calls | 11 |
| candidates_evaluated | 1664 |
| session_build_ms | 0.0 |
| deregister_reregister_ms | 0.053 |
| candidate_transform_prepare_ms | 3.243 |
| cde_query_collect_ms | 10.225 |
| specialized_pipeline_ms | 10.225 |
| hazard_loss_ms | not_available — hazard quantification is inside cde_query_collect; not separately timed to avoid double overhead |
| boundary_check_ms | 1.786 |
| broadphase_reject_count | 0 |
| early_termination_count | 231 |

## Case: dense191

- Status: partial
- Runtime: 144028 ms
- Placed: 191
- Final pairs: 157
- Iterations: 1
- Search calls: 66
- Profiling enabled: True
- Search total ms: 6447.942

### Cost breakdown (% of search_total_ms)

| Component | ms | % | Bar |
|-----------|-----|---|-----|
| other_unaccounted_ms | 5163.7 | 80.1% | ████████████████░░░░ |
| cde_query_collect_ms | 1236.0 | 19.2% | ████░░░░░░░░░░░░░░░░ |
| candidate_transform_prepare_ms | 35.2 | 0.5% | ░░░░░░░░░░░░░░░░░░░░ |
| boundary_check_ms | 12.2 | 0.2% | ░░░░░░░░░░░░░░░░░░░░ |
| deregister_ms | 0.8 | 0.0% | ░░░░░░░░░░░░░░░░░░░░ |
| session_build_ms | 0.0 | 0.0% | ░░░░░░░░░░░░░░░░░░░░ |

### Profile fields

| Field | Value |
|-------|-------|
| native_search_calls | 66 |
| candidates_evaluated | 10470 |
| session_build_ms | 0.0 |
| deregister_reregister_ms | 0.845 |
| candidate_transform_prepare_ms | 35.171 |
| cde_query_collect_ms | 1236.037 |
| specialized_pipeline_ms | 1236.037 |
| hazard_loss_ms | not_available — hazard quantification is inside cde_query_collect; not separately timed to avoid double overhead |
| boundary_check_ms | 12.163 |
| broadphase_reject_count | 315 |
| early_termination_count | 4891 |

