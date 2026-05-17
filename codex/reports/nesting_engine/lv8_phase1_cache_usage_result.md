# LV8 Phase1 Cache Usage Result

## T10B run (current — 2026-05-17)

- command:
  - `python3 scripts/experiments/lv8_phase1_cache_usage_matrix.py --out-root tmp/lv8_density_phase1_cache_usage_t10b --time-limit-sec 60 --lv8-time-limit-sec 180 --seed 42 --include-lv8-179 auto --profiles quality_default_no_sa_shadow,quality_aggressive_no_sa_shadow`
- exit_code: `3`

### Decision snapshot (T10B)

- phase2a_unblocked: `NO`
- phase2a_ready_source: `blocked`
- lv8_stats_available: `NO`
- sa_guard_stats_available: `YES`
- cache_stats_available_all_required_runs: `NO`
- polygon_gate_available_all_required_runs: `YES`
- blocked_reason: `null`

### Root cause note

`lv8_276` 180s engine time-limit mellett is `timed_out=True` (`runtime_sec ≈ 241s` = subprocess kill-guard: `180+60=240s`). A Rust engine `greedy_multi_sheet()` 276 alkatrészre >240s futási időt vesz igénybe; a `NEST_NFP_STATS_V1` sor csak a sikeres visszatérés után emittálódik, SIGKILL esetén nem. 600s+ futás szükséges az LV8 stats megszerzéséhez.

### Run-level summary (T10B)

| family | profile | timed_out | return_code | engine_stats_available | clear_all_events | valid_polygon_gate | valid |
|---|---|---|---:|---|---:|---|---|
| lv8_276 | quality_default_no_sa_shadow | true | 2 | false | null | true | false |
| lv8_276 | quality_aggressive_no_sa_shadow | true | 2 | false | null | true | false |
| sa_guard | quality_default_no_sa_shadow | false | 0 | true | 0 | true | true |
| sa_guard | quality_aggressive_no_sa_shadow | false | 0 | true | 0 | true | true |
| lv8_179 | quality_default_no_sa_shadow | true | 2 | false | null | true | false |
| lv8_179 | quality_aggressive_no_sa_shadow | true | 2 | false | null | true | false |

### Artifacts (T10B)

- `tmp/lv8_density_phase1_cache_usage_t10b/cache_usage_matrix.json`
- `tmp/lv8_density_phase1_cache_usage_t10b/cache_usage_matrix.md`
- `tmp/lv8_density_phase1_cache_usage_t10b/runs.jsonl`

---

## T10 run (előzmény — 2026-05-17)

- command:
  - `python3 scripts/experiments/lv8_phase1_cache_usage_matrix.py --out-root tmp/lv8_density_phase1_cache_usage --time-limit-sec 60 --seed 42 --include-lv8-179 auto --profiles quality_default_no_sa_shadow,quality_aggressive_no_sa_shadow`
- exit_code: `3`

### Decision snapshot (T10)

- phase2a_ready: `NO`
- lru_followup_required: `NO`
- cache_stats_available_all_required_runs: `NO`
- polygon_gate_available_all_required_runs: `YES`
- blocked_reason: `null`

### Run-level summary (T10)

| family | profile | return_code | timed_out | engine_stats_available | clear_all_events | valid_polygon_gate | valid |
|---|---|---:|---|---|---:|---|---|
| lv8_276 | quality_default_no_sa_shadow | 2 | true | false | null | true | false |
| lv8_276 | quality_aggressive_no_sa_shadow | 2 | true | false | null | true | false |
| sa_guard | quality_default_no_sa_shadow | 0 | false | true | 0 | true | true |
| sa_guard | quality_aggressive_no_sa_shadow | 0 | false | true | 0 | true | true |
| lv8_179 | quality_default_no_sa_shadow | 2 | true | false | null | true | false |
| lv8_179 | quality_aggressive_no_sa_shadow | 2 | true | false | null | true | false |

### Artifacts (T10)

- `tmp/lv8_density_phase1_cache_usage/cache_usage_matrix.json`
- `tmp/lv8_density_phase1_cache_usage/cache_usage_matrix.md`
- `tmp/lv8_density_phase1_cache_usage/runs.jsonl`
