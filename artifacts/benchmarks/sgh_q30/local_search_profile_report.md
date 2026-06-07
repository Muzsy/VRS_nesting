# SGH-Q30 local Sparrow search profiler — results

**Profile flag:** `SGH_Q30_SEARCH_PROFILE=1`
**Timing accounting mode:** `mixed_with_notes`

## Admin / future integration notes

- `SearchProfiler::finalize()` in `profile.rs` computes all derived fields.
- Export path: `optimizer_diagnostics.sparrow_q30_*` JSON fields (current).
- Future: call finalize() in optimizer.rs after solve; pipe snapshot to tracing subscriber.

## Timing accounting model

**Exclusive** sub-buckets of `search_total_ms` (sum ≤ search_total):
- `evaluate_sample_total_ms` — ALL evaluate_sample calls (incl. from coord_descent)
- `sample_generation_ms` — UniformBBoxSampler.sample() calls
- `best_samples_insert_dedup_ms` — BestSamples.report() calls
- `deregister_reregister_ms` — deregister_item calls
- `session_build_ms` — fallback fresh-session builds

**Nested** (NOT subtracted in other_unaccounted_ms):
- `coord_descent_total_ms` — wraps evaluate_sample calls within
- `cde_query_collect_ms` — sub of evaluate_sample
- `candidate_transform_prepare_ms` — sub of evaluate_sample
- `boundary_check_ms` — sub of evaluate_sample

`other_unaccounted_ms` = search_total - (exclusive subs)

## Case: medium (status=ok)

- Runtime: 1217 ms
- Placed: 24, final_pairs: 0, iterations: 1
- Q30 profiling enabled: True

*No search profiling data (search_total_ms = 0 or profiler disabled)*

## Case: lv8_subset (status=ok)

- Runtime: 15888 ms
- Placed: 67, final_pairs: 0, iterations: 1
- Q30 profiling enabled: True

### Timing breakdown (search_total_ms = 141.0 ms)

| Bucket | ms | % of search_total | Type |
|---|---|---|---|
| other_unaccounted_ms | 116.4 | 82.6% | exclusive |
| evaluate_sample_total_ms | 23.0 | 16.3% | exclusive |
|   └─ cde_query_collect_ms (nested) | 10.2 | 7.2% | nested_sub |
|   └─ candidate_transform_ms (nested) | 3.0 | 2.1% | nested_sub |
|   └─ boundary_check_ms (nested) | 1.8 | 1.3% | nested_sub |
|   └─ evaluator_orchestration_ms (nested) | 8.0 | 5.7% | nested_sub |
| sample_generation_ms | 0.9 | 0.6% | exclusive |
| best_samples_insert_dedup_ms | 0.7 | 0.5% | exclusive |
| deregister_reregister_ms | 0.1 | 0.0% | exclusive |
| session_build_ms | 0.0 | 0.0% | exclusive |

### Key counters

- Search calls: 11
- evaluate_sample calls: 1664
- Passed bbox (candidates_evaluated): 1664
- Bbox rejected: 0
- CDE early termination: 231
- Coord descent runs: 44
- Coord descent steps: 828
- BestSamples insert attempts: 650
- BestSamples inserted: 100
- BestSamples dedup rejects: 0
- Global samples: 550
- Focused samples: 275

### Per-call averages

- per_search_avg_ms: 12.820 ms
- per_evaluate_sample_avg_ms: 0.013799 ms
- per_candidate_avg_ms: 0.013799 ms

## Case: dense191 (status=partial)

- Runtime: 202907 ms
- Placed: 191, final_pairs: 80, iterations: 1
- Q30 profiling enabled: True

### Timing breakdown (search_total_ms = 26176.3 ms)

| Bucket | ms | % of search_total | Type |
|---|---|---|---|
| other_unaccounted_ms | 20783.8 | 79.4% | exclusive |
| evaluate_sample_total_ms | 5378.4 | 20.5% | exclusive |
|   └─ cde_query_collect_ms (nested) | 4950.0 | 18.9% | nested_sub |
|   └─ candidate_transform_ms (nested) | 138.7 | 0.5% | nested_sub |
|   └─ boundary_check_ms (nested) | 50.8 | 0.2% | nested_sub |
|   └─ evaluator_orchestration_ms (nested) | 238.9 | 0.9% | nested_sub |
| best_samples_insert_dedup_ms | 5.5 | 0.0% | exclusive |
| sample_generation_ms | 5.2 | 0.0% | exclusive |
| deregister_reregister_ms | 3.4 | 0.0% | exclusive |
| session_build_ms | 0.0 | 0.0% | exclusive |

### Key counters

- Search calls: 272
- evaluate_sample calls: 45729
- Passed bbox (candidates_evaluated): 44484
- Bbox rejected: 1245
- CDE early termination: 23537
- Coord descent runs: 1355
- Coord descent steps: 41118
- BestSamples insert attempts: 4107
- BestSamples inserted: 3609
- BestSamples dedup rejects: 148
- Global samples: 2168
- Focused samples: 2171

### Per-call averages

- per_search_avg_ms: 96.237 ms
- per_evaluate_sample_avg_ms: 0.117614 ms
- per_candidate_avg_ms: 0.120906 ms

## Final answer — mi viszi el az időt?

**1. medium case:** No search profiling data (0 separator search calls — converged via constructive seed).
**2. lv8_subset case** (search_total=141 ms):
Top costs: other_unaccounted_ms 82.6%; evaluate_sample_total_ms 16.3%; sample_generation_ms 0.6%
other_unaccounted: 116.4 ms = 82.6%

**3. dense191 case** (search_total=26176 ms):
Top costs: other_unaccounted_ms 79.4%; evaluate_sample_total_ms 20.5%; best_samples_insert_dedup_ms 0.0%
other_unaccounted: 20783.8 ms = 79.4%

**4. other_unaccounted** tartalma és oka:

A Q30 mérés alapján az `other_unaccounted_ms` a search-loop következő részeit tartalmazza,
amelyeket az aktuális instrumentáció nem bont tovább:
- `search_placement` belső loop infrastructure (for-loop overhead, deadline checks)
- `BestSamples::best()` és `.samples.clone()` hívások (pre-coord_descent clone)
- `build_sheet_session` (keresztlap-keresés, de fallback = ritka)
- `prepare_base_shape_native` (egyszer per search call, CDE shape prep)
- Memória allokáció overhead (`Vec::new`, BestSamples inicializáció)
- Egyéb kis overheadek a loop körüli kódban

**5. Következő optimalizációs irány** (mérés alapján indokolt, de NEM implementálva Q30-ban):

Dense191 domináns: evaluate_sample_total 20.5%, sample_generation 0.0%, best_samples_insert 0.0%, other 79.4%

- **Loop overhead mérése**: `prepare_base_shape_native` és `BestSamples::clone()` per-search-call cost
  felbontása a maradék other_unaccounted-ből, hogy kiderüljön, érdemes-e memoizálni.
