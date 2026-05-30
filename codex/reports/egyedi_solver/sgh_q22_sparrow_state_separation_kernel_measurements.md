# SGH-Q22 Sparrow benchmark measurements

Quick local matrix run. Each row = (fixture, pipeline, backend, seed) → metrics.

| fixture | pipeline | backend | seed | status | placed | runtime_ms | sp_init_raw | sp_final_raw | sp_iters | sp_moves | sp_pairs_i→f | bbox_fb | cde_total |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|---:|---:|
| medium_10_to_20_items | phase_optimizer | bbox | 1 | ok | 12 | 3.9 | - | - | - | - / - | -→- | 0 | - |
| medium_10_to_20_items | phase_optimizer | bbox | 2 | ok | 12 | 4.2 | - | - | - | - / - | -→- | 0 | - |
| medium_10_to_20_items | phase_optimizer | bbox | 3 | ok | 12 | 3.4 | - | - | - | - / - | -→- | 0 | - |
| medium_10_to_20_items | phase_optimizer | cde | 1 | timeout | - | 30030.6 | - | - | - | - / - | -→- | - | - |
| medium_10_to_20_items | phase_optimizer | cde | 2 | timeout | - | 30031.0 | - | - | - | - / - | -→- | - | - |
| medium_10_to_20_items | phase_optimizer | cde | 3 | timeout | - | 30030.7 | - | - | - | - / - | -→- | - | - |
| medium_10_to_20_items | sparrow_experimental | bbox | 1 | ok | 12 | 2.3 | 39600.0 | - | 12 | 11 / 11 | 66→- | 0 | - |
| medium_10_to_20_items | sparrow_experimental | bbox | 2 | ok | 12 | 2.3 | 39600.0 | - | 12 | 11 / 11 | 66→- | 0 | - |
| medium_10_to_20_items | sparrow_experimental | bbox | 3 | ok | 12 | 3.1 | 39600.0 | - | 12 | 11 / 11 | 66→- | 0 | - |
| medium_10_to_20_items | sparrow_experimental | cde | 1 | unsupported | - | 20233.6 | - | - | - | - / - | -→- | 0 | 8352 |
| medium_10_to_20_items | sparrow_experimental | cde | 2 | unsupported | - | 20400.8 | - | - | - | - / - | -→- | 0 | 8352 |
| medium_10_to_20_items | sparrow_experimental | cde | 3 | unsupported | - | 20309.2 | - | - | - | - / - | -→- | 0 | 8352 |
| synthetic_30_items | phase_optimizer | bbox | 1 | ok | 30 | 19.8 | - | - | - | - / - | -→- | 0 | - |
| synthetic_30_items | phase_optimizer | bbox | 2 | ok | 30 | 19.8 | - | - | - | - / - | -→- | 0 | - |
| synthetic_30_items | phase_optimizer | bbox | 3 | ok | 30 | 22.2 | - | - | - | - / - | -→- | 0 | - |
| synthetic_30_items | phase_optimizer | cde | 1 | timeout | - | 30030.5 | - | - | - | - / - | -→- | - | - |
| synthetic_30_items | phase_optimizer | cde | 2 | timeout | - | 30030.4 | - | - | - | - / - | -→- | - | - |
| synthetic_30_items | phase_optimizer | cde | 3 | timeout | - | 30030.6 | - | - | - | - / - | -→- | - | - |
| synthetic_30_items | sparrow_experimental | bbox | 1 | ok | 30 | 8.0 | 241125.0 | - | 30 | 29 / 29 | 435→- | 0 | - |
| synthetic_30_items | sparrow_experimental | bbox | 2 | ok | 30 | 8.1 | 241125.0 | - | 30 | 29 / 29 | 435→- | 0 | - |
| synthetic_30_items | sparrow_experimental | bbox | 3 | ok | 30 | 9.6 | 241125.0 | - | 30 | 29 / 29 | 435→- | 0 | - |
| synthetic_30_items | sparrow_experimental | cde | 1 | timeout | - | 30020.6 | - | - | - | - / - | -→- | - | - |
| synthetic_30_items | sparrow_experimental | cde | 2 | timeout | - | 30025.0 | - | - | - | - / - | -→- | - | - |
| synthetic_30_items | sparrow_experimental | cde | 3 | timeout | - | 30020.8 | - | - | - | - / - | -→- | - | - |

## Summary

- Configurations run: **24**
- Sparrow runs converged: **6 / 9**
- Total runtime: **331301 ms**

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
