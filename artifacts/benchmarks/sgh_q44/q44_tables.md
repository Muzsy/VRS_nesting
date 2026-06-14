# SGH-Q44 extracted per-attempt tables

## 1. Baseline confirmation

| run_id | time_limit_s | placed | unplaced | used_sheets | ms_attempts | ms_subsets | ms_runtime_ms | wall_s | cde_batch_cand_q | cde_batch_eng_builds | cde_batch_hazards | cde_batch_collisions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q42_full276_3x1500x3000_margin5_spacing8_continuous_1200 | 1200 | 276 | 0 | 3 | 3 | 3 | 701691.205062 |  | 5262621 | 102649 | 3934775 | 9524164 |
| q42_full276_3x1500x3000_margin5_spacing8_continuous_2400 | 2400 | 276 | 0 | 3 | 3 | 3 | 1301397.81773 |  | 8566449 | 200255 | 7949860 | 17310353 |

### Per-attempt CDE delta sum vs aggregate (consistency)

| run | counter | aggregate | sum_of_attempt_deltas | residual(post-loop) |
| --- | --- | --- | --- | --- |
| 1200 | cde_engine_builds | 34916 | 34916 | 0 |
| 1200 | cde_batch_candidate_queries | 5262621 | 5262621 | 0 |
| 1200 | cde_batch_engine_builds | 102649 | 102649 | 0 |
| 1200 | cde_batch_hazards_registered | 3934775 | 3934775 | 0 |
| 1200 | cde_batch_collisions_returned | 9524164 | 9524164 | 0 |
| 1200 | cde_candidate_session_builds | 0 | 0 | 0 |
| 1200 | cde_candidate_session_reuses | 0 | 0 | 0 |
| 2400 | cde_engine_builds | 61678 | 61678 | 0 |
| 2400 | cde_batch_candidate_queries | 8566449 | 8566449 | 0 |
| 2400 | cde_batch_engine_builds | 200255 | 200255 | 0 |
| 2400 | cde_batch_hazards_registered | 7949860 | 7949860 | 0 |
| 2400 | cde_batch_collisions_returned | 17310353 | 17310353 | 0 |
| 2400 | cde_candidate_session_builds | 0 | 0 | 0 |
| 2400 | cde_candidate_session_reuses | 0 | 0 | 0 |

## 2. Candidate subset schedule

| run | attempt | subset_indices | size | signature | full_pool | 2nd_to_last | alloc_s | actual_s | rem_before_s | rem_after_s | deadline_hit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1200 | 0 | [0] | 1 | 1500.0x3000.0 | False | False | 30.0 | 52.4 | 1200.0 | 1147.6 | False |
| 1200 | 1 | [0, 1] | 2 | 1500.0x3000.0+1500.0x3000.0 | False | True | 600.0 | 615.5 | 1147.6 | 532.1 | False |
| 1200 | 2 | [0, 1, 2] | 3 | 1500.0x3000.0+1500.0x3000.0+1500.0x3000.0 | True | False | 442.11 | 33.8 | 532.1 | 498.3 | False |
| 2400 | 0 | [0] | 1 | 1500.0x3000.0 | False | False | 30.0 | 51.3 | 2400.0 | 2348.7 | False |
| 2400 | 1 | [0, 1] | 2 | 1500.0x3000.0+1500.0x3000.0 | False | True | 1200.0 | 1216.4 | 2348.7 | 1132.3 | False |
| 2400 | 2 | [0, 1, 2] | 3 | 1500.0x3000.0+1500.0x3000.0+1500.0x3000.0 | True | False | 1042.29 | 33.7 | 1132.3 | 1098.6 | False |

## 3. Attempt outcome table

| run | attempt | core_feasible | core_status | placed | unplaced | used_sheets | final_pairs | boundary | sanitized | score | incumbent | stop_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1200 | 0 | False | infeasible_collisions | 145 | 131 | 1 | 445 | 0 | True | 999999998406066.5 | True | partial_sanitized |
| 1200 | 1 | False | infeasible_collisions | 238 | 38 | 2 | 98 | 2 | True | 999999995212239.6 | True | partial_sanitized |
| 1200 | 2 | True | feasible | 276 | 0 | 3 | 0 | 0 | False | 13500000.003 | True | valid_full_solution |
| 2400 | 0 | False | infeasible_collisions | 145 | 131 | 1 | 445 | 0 | True | 999999998406066.5 | True | partial_sanitized |
| 2400 | 1 | False | infeasible_collisions | 240 | 36 | 2 | 96 | 1 | True | 999999996147512.8 | True | partial_sanitized |
| 2400 | 2 | True | feasible | 276 | 0 | 3 | 0 | 0 | False | 13500000.003 | True | valid_full_solution |

## 4. Attempt-level CDE cost table

| run | attempt | size | actual_ms | engine_builds_d | batch_cand_q_d | batch_eng_builds_d | hazards_d | collisions_d | rt% | cand_q% | batch_eng% | hazard% | coll% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1200 | 0 | 1 | 52417.2 | 2127 | 374665 | 2527 | 35985 | 688273 | 7.47 | 7.12 | 2.46 | 0.91 | 7.23 |
| 1200 | 1 | 2 | 615471.5 | 28363 | 3787883 | 93989 | 3789025 | 7902255 | 87.71 | 71.98 | 91.56 | 96.3 | 82.97 |
| 1200 | 2 | 3 | 33802.0 | 4426 | 1100073 | 6133 | 109765 | 933636 | 4.82 | 20.9 | 5.97 | 2.79 | 9.8 |
| 2400 | 0 | 1 | 51314.6 | 2248 | 382719 | 2639 | 37167 | 723551 | 3.94 | 4.47 | 1.32 | 0.47 | 4.18 |
| 2400 | 1 | 2 | 1216396.8 | 55004 | 7083657 | 191483 | 7802928 | 15653166 | 93.47 | 82.69 | 95.62 | 98.15 | 90.43 |
| 2400 | 2 | 3 | 33686.0 | 4426 | 1100073 | 6133 | 109765 | 933636 | 2.59 | 12.84 | 3.06 | 1.38 | 5.39 |

## 5. Attempt-level Sparrow/search cost table

| run | attempt | iters | moves_att | moves_acc | rollbacks | search_calls | search_samples | coord_steps | edges_recomputed | full_rebuilds | incr_updates |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1200 | 0 | 2 | 481 | 481 | 0 | 891 | 240284 | 236748 | 972073 | 3 | 919 |
| 1200 | 1 | 383 | 9655 | 9016 | 639 | 19251 | 10023614 | 9884514 | 30027548 | 32 | 19253 |
| 1200 | 2 | 28 | 146 | 140 | 6 | 287 | 186536 | 189394 | 600013 | 15 | 286 |
| 2400 | 0 | 3 | 543 | 543 | 0 | 1026 | 273799 | 270278 | 1132471 | 3 | 1054 |
| 2400 | 1 | 756 | 19610 | 18302 | 1308 | 39264 | 20484069 | 20220420 | 60251394 | 56 | 39266 |
| 2400 | 2 | 28 | 146 | 140 | 6 | 287 | 186536 | 189394 | 600013 | 15 | 286 |

## 6. 1200s vs 2400s delta analysis

| metric | 1200s_total | 2400s_total | delta | subset_size_most_delta | delta_pct_in_that_attempt | per_attempt_delta_by_subset_size |
| --- | --- | --- | --- | --- | --- | --- |
| sparrow_ms_runtime_ms | 701691.205062 | 1301397.81773 | 599706.612668 | 2 | 100.2 | {1: -1102.6109179999985, 2: 600925.260078, 3: -116.06987700000172} |
| cde_batch_candidate_queries | 5262621 | 8566449 | 3303828 | 2 | 99.76 | {1: 8054, 2: 3295774, 3: 0} |
| cde_batch_engine_builds | 102649 | 200255 | 97606 | 2 | 99.89 | {1: 112, 2: 97494, 3: 0} |
| cde_batch_hazards_registered | 3934775 | 7949860 | 4015085 | 2 | 99.97 | {1: 1182, 2: 4013903, 3: 0} |
| cde_batch_collisions_returned | 9524164 | 17310353 | 7786189 | 2 | 99.55 | {1: 35278, 2: 7750911, 3: 0} |
| cde_engine_builds | 34916 | 61678 | 26762 | 2 | 99.55 | {1: 121, 2: 26641, 3: 0} |

**Did the additional ~599 s in the 2400s run mostly go into the 2-sheet attempt?**

- Answer: **YES**
- subset_size receiving most runtime delta: `2`
- runtime delta share in that attempt: `100.2%`
- evidence: `runtime delta 599707 ms; subset_size=2 attempt received 100.2% of it (per-attempt ms delta by subset size: {1: -1102.6109179999985, 2: 600925.260078, 3: -116.06987700000172})`

