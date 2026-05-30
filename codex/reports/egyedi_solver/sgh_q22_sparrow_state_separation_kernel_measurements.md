# SGH-Q22 Sparrow benchmark measurements

Quick local matrix run. Each row = (fixture, pipeline, backend, seed) → metrics.

**Q22R1 accounting**: every `sparrow_experimental` run counts towards the denominator, including `unsupported` and `timeout`. Zero/false values render as `0` / `false`, only missing fields as `-`.

| fixture | pipeline | backend | seed | status | placed | runtime_ms | sp_init_raw | sp_final_raw | sp_iters | sp_moves | sp_pairs_i→f | bbox_fb | cde_total |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|---:|---:|
| medium_10_to_20_items | phase_optimizer | bbox | 1 | ok | 12 | 4.7 | - | - | - | - / - | -→- | 0 | - |
| medium_10_to_20_items | phase_optimizer | bbox | 2 | ok | 12 | 4.2 | - | - | - | - / - | -→- | 0 | - |
| medium_10_to_20_items | phase_optimizer | bbox | 3 | ok | 12 | 4.1 | - | - | - | - / - | -→- | 0 | - |
| medium_10_to_20_items | phase_optimizer | cde | 1 | timeout | - | 30031.1 | - | - | - | - / - | -→- | - | - |
| medium_10_to_20_items | phase_optimizer | cde | 2 | timeout | - | 30030.3 | - | - | - | - / - | -→- | - | - |
| medium_10_to_20_items | phase_optimizer | cde | 3 | timeout | - | 30031.1 | - | - | - | - / - | -→- | - | - |
| medium_10_to_20_items | sparrow_experimental | bbox | 1 | ok | 12 | 2.2 | 39600.0 | 0.0 | 12 | 11 / 11 | 66→0 | 0 | - |
| medium_10_to_20_items | sparrow_experimental | bbox | 2 | ok | 12 | 2.1 | 39600.0 | 0.0 | 12 | 11 / 11 | 66→0 | 0 | - |
| medium_10_to_20_items | sparrow_experimental | bbox | 3 | ok | 12 | 2.1 | 39600.0 | 0.0 | 12 | 11 / 11 | 66→0 | 0 | - |
| medium_10_to_20_items | sparrow_experimental | cde | 1 | unsupported | 0 | 20588.7 | 1320.0 | 720.0 | 4 | 3 / 3 | 66→36 | 0 | 8352 |
| medium_10_to_20_items | sparrow_experimental | cde | 2 | unsupported | 0 | 20363.1 | 1320.0 | 720.0 | 4 | 3 / 3 | 66→36 | 0 | 8352 |
| medium_10_to_20_items | sparrow_experimental | cde | 3 | unsupported | 0 | 20497.0 | 1320.0 | 720.0 | 4 | 3 / 3 | 66→36 | 0 | 8352 |
| synthetic_30_items | phase_optimizer | bbox | 1 | ok | 30 | 20.7 | - | - | - | - / - | -→- | 0 | - |
| synthetic_30_items | phase_optimizer | bbox | 2 | ok | 30 | 20.1 | - | - | - | - / - | -→- | 0 | - |
| synthetic_30_items | phase_optimizer | bbox | 3 | ok | 30 | 18.8 | - | - | - | - / - | -→- | 0 | - |
| synthetic_30_items | phase_optimizer | cde | 1 | timeout | - | 30030.5 | - | - | - | - / - | -→- | - | - |
| synthetic_30_items | phase_optimizer | cde | 2 | timeout | - | 30009.9 | - | - | - | - / - | -→- | - | - |
| synthetic_30_items | phase_optimizer | cde | 3 | timeout | - | 30031.1 | - | - | - | - / - | -→- | - | - |
| synthetic_30_items | sparrow_experimental | bbox | 1 | ok | 30 | 8.2 | 241125.0 | 0.0 | 30 | 29 / 29 | 435→0 | 0 | - |
| synthetic_30_items | sparrow_experimental | bbox | 2 | ok | 30 | 10.6 | 241125.0 | 0.0 | 30 | 29 / 29 | 435→0 | 0 | - |
| synthetic_30_items | sparrow_experimental | bbox | 3 | ok | 30 | 10.0 | 241125.0 | 0.0 | 30 | 29 / 29 | 435→0 | 0 | - |
| synthetic_30_items | sparrow_experimental | cde | 1 | timeout | - | 30031.2 | - | - | - | - / - | -→- | - | - |
| synthetic_30_items | sparrow_experimental | cde | 2 | timeout | - | 30031.4 | - | - | - | - / - | -→- | - | - |
| synthetic_30_items | sparrow_experimental | cde | 3 | timeout | - | 30030.9 | - | - | - | - / - | -→- | - | - |

## Summary

- Configurations run: **24**
- Sparrow runs converged: **6 / 12** (denominator includes ok/partial/unsupported/timeout)
- Total runtime: **331814 ms**

### Per-backend Sparrow summary

| backend | sparrow_total | converged | unsupported | timeout |
|---|---:|---:|---:|---:|
| bbox | 6 | 6 | 0 | 0 |
| cde | 6 | 0 | 3 | 3 |

### Notes

- medium_10_to_20_items/phase_optimizer/cde/seed=1 solver error: timeout after 30.0s
- medium_10_to_20_items/phase_optimizer/cde/seed=2 solver error: timeout after 30.0s
- medium_10_to_20_items/phase_optimizer/cde/seed=3 solver error: timeout after 30.0s
- synthetic_30_items/phase_optimizer/cde/seed=1 solver error: timeout after 30.0s
- synthetic_30_items/phase_optimizer/cde/seed=2 solver error: timeout after 30.0s
- synthetic_30_items/phase_optimizer/cde/seed=3 solver error: timeout after 30.0s
- synthetic_30_items/sparrow_experimental/cde/seed=1 solver error: timeout after 30.0s
- synthetic_30_items/sparrow_experimental/cde/seed=2 solver error: timeout after 30.0s
- synthetic_30_items/sparrow_experimental/cde/seed=3 solver error: timeout after 30.0s
