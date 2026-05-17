# LV8 Phase1 Cache Usage Result

- generated_at: 2026-05-17
- command:
  - `python3 scripts/experiments/lv8_phase1_cache_usage_matrix.py --out-root tmp/lv8_density_phase1_cache_usage --time-limit-sec 60 --seed 42 --include-lv8-179 auto --profiles quality_default_no_sa_shadow,quality_aggressive_no_sa_shadow`
- exit_code: `3`

## Decision snapshot

- phase2a_ready: `NO`
- lru_followup_required: `NO`
- cache_stats_available_all_required_runs: `NO`
- polygon_gate_available_all_required_runs: `YES`
- blocked_reason: `null`

## Run-level summary

| family | profile | return_code | timed_out | engine_stats_available | clear_all_events | valid_polygon_gate | valid |
|---|---|---:|---|---|---:|---|---|
| lv8_276 | quality_default_no_sa_shadow | 2 | true | false | null | true | false |
| lv8_276 | quality_aggressive_no_sa_shadow | 2 | true | false | null | true | false |
| sa_guard | quality_default_no_sa_shadow | 0 | false | true | 0 | true | true |
| sa_guard | quality_aggressive_no_sa_shadow | 0 | false | true | 0 | true | true |
| lv8_179 | quality_default_no_sa_shadow | 2 | true | false | null | true | false |
| lv8_179 | quality_aggressive_no_sa_shadow | 2 | true | false | null | true | false |

## Artifacts

- `tmp/lv8_density_phase1_cache_usage/cache_usage_matrix.json`
- `tmp/lv8_density_phase1_cache_usage/cache_usage_matrix.md`
- `tmp/lv8_density_phase1_cache_usage/runs.jsonl`
