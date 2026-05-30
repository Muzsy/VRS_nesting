# SGH-Q23 full Sparrow parity cutover — benchmark measurements

Production path = `sparrow_cde` (CDE-first). `sparrow_experimental` and `phase_optimizer` are comparison-only, not acceptance.

**Accounting:** every production `sparrow_cde` run counts in the denominator (ok / partial / unsupported / timeout / error). Zero/false render as themselves; only missing fields as `-`.

| fixture | pipeline | backend | seed | status | placed/req | runtime_ms | conv | iters | moves a/att | pairs i→f | raw i→f | cde_q | engine_builds | bphase_pruned | bbox_fb | lbf_fb |
|---|---|---|---:|---|---|---:|---|---:|---|---|---|---:|---:|---:|---:|---:|
| tiny | sparrow_cde | cde | 1 | ok | 2/2 | 226.1 | True | 2 | 1/1 | 1→0 | 20.0→0.0 | 96 | 71 | 25 | 0 | 0 |
| tiny | sparrow_experimental | cde | 1 | ok | 2/2 | 233.9 | True | 2 | 1/1 | 1→0 | 20.0→0.0 | 96 | 71 | 25 | 0 | 0 |
| tiny | phase_optimizer | bbox | 1 | ok | 2/2 | 1.9 | - | - | -/- | -→- | -→- | - | - | - | 0 | 0 |
| two_rect_overlap | sparrow_cde | cde | 1 | ok | 2/2 | 803.5 | True | 2 | 1/1 | 1→0 | 30.0→0.0 | 464 | 255 | 209 | 0 | 0 |
| two_rect_overlap | sparrow_experimental | cde | 1 | ok | 2/2 | 750.6 | True | 2 | 1/1 | 1→0 | 30.0→0.0 | 464 | 255 | 209 | 0 | 0 |
| two_rect_overlap | phase_optimizer | bbox | 1 | ok | 2/2 | 1.8 | - | - | -/- | -→- | -→- | - | - | - | 0 | 0 |
| boundary_recovery | sparrow_cde | cde | 1 | ok | 1/1 | 4.5 | True | 0 | 0/0 | 0→0 | 0.0→0.0 | 2 | 2 | 0 | 0 | 0 |
| boundary_recovery | sparrow_experimental | cde | 1 | ok | 1/1 | 4.7 | True | 0 | 0/0 | 0→0 | 0.0→0.0 | 2 | 2 | 0 | 0 | 0 |
| boundary_recovery | phase_optimizer | bbox | 1 | ok | 1/1 | 1.6 | - | - | -/- | -→- | -→- | - | - | - | 0 | 0 |
| medium_10_to_20_items | sparrow_cde | cde | 1 | unsupported | 0/12 | 25017.8 | False | 5 | 4/4 | 66→28 | 1320.0→560.0 | 11236 | 7650 | 3586 | 0 | 0 |
| medium_10_to_20_items | sparrow_experimental | cde | 1 | unsupported | 0/12 | 25250.4 | False | 5 | 4/4 | 66→28 | 1320.0→560.0 | 11236 | 7650 | 3586 | 0 | 0 |
| medium_10_to_20_items | phase_optimizer | bbox | 1 | ok | 12/12 | 3.3 | - | - | -/- | -→- | -→- | - | - | - | 0 | 0 |

## Production (`sparrow_cde`) outcome accounting

| outcome | count |
|---|---:|
| ok | 3 |
| partial | 0 |
| unsupported | 1 |
| timeout | 0 |
| error | 0 |
| **total** | **4** |
| **converged** | **3** |


