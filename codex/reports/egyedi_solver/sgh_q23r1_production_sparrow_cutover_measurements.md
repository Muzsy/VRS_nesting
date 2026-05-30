# SGH-Q23R1 production Sparrow cutover — benchmark measurements

Production path = `sparrow_cde` (CDE-first). `sparrow_experimental` and `phase_optimizer` are comparison-only, not acceptance.

**Accounting:** every production `sparrow_cde` run counts in the denominator (ok / partial / unsupported / timeout / error). Zero/false render as themselves; only missing fields as `-`.

| fixture | pipeline | backend | seed | status | placed/req | runtime_ms | conv | iters | moves a/att | pairs i→f | raw i→f | cde_q | engine_builds | bphase_pruned | bbox_fb | lbf_fb |
|---|---|---|---:|---|---|---:|---|---:|---|---|---|---:|---:|---:|---|---:|---:|
| tiny | sparrow_cde | cde | 1 | ok | 2/2 | 168.6 | True | 2 | 1/1 | 1→0 | 20.0→0.0 | 96 | 67 | 23 | 2/88 | 0 | 0 |
| tiny | sparrow_experimental | cde | 1 | ok | 2/2 | 165.0 | True | 2 | 1/1 | 1→0 | 20.0→0.0 | 96 | 67 | 23 | 2/88 | 0 | 0 |
| tiny | phase_optimizer | bbox | 1 | ok | 2/2 | 2.7 | - | - | -/- | -→- | -→- | - | - | - | -/- | 0 | 0 |
| two_rect_overlap | sparrow_cde | cde | 1 | ok | 2/2 | 527.9 | True | 2 | 1/1 | 1→0 | 30.0→0.0 | 464 | 251 | 207 | 2/452 | 0 | 0 |
| two_rect_overlap | sparrow_experimental | cde | 1 | ok | 2/2 | 499.8 | True | 2 | 1/1 | 1→0 | 30.0→0.0 | 464 | 251 | 207 | 2/452 | 0 | 0 |
| two_rect_overlap | phase_optimizer | bbox | 1 | ok | 2/2 | 1.8 | - | - | -/- | -→- | -→- | - | - | - | -/- | 0 | 0 |
| boundary_recovery | sparrow_cde | cde | 1 | ok | 1/1 | 2.6 | True | 0 | 0/0 | 0→0 | 0.0→0.0 | 2 | 1 | 0 | 0/0 | 0 | 0 |
| boundary_recovery | sparrow_experimental | cde | 1 | ok | 1/1 | 2.7 | True | 0 | 0/0 | 0→0 | 0.0→0.0 | 2 | 1 | 0 | 0/0 | 0 | 0 |
| boundary_recovery | phase_optimizer | bbox | 1 | ok | 1/1 | 1.7 | - | - | -/- | -→- | -→- | - | - | - | -/- | 0 | 0 |
| medium_10_to_20_items | sparrow_cde | cde | 1 | unsupported | 0/12 | 9404.6 | False | 8 | 7/7 | 66→10 | 1320.0→200.0 | 27350 | 4246 | 2401 | 20043/6253 | 0 | 0 |
| medium_10_to_20_items | sparrow_experimental | cde | 1 | unsupported | 0/12 | 9463.8 | False | 8 | 7/7 | 66→10 | 1320.0→200.0 | 27350 | 4246 | 2401 | 20043/6253 | 0 | 0 |
| medium_10_to_20_items | phase_optimizer | bbox | 1 | ok | 12/12 | 4.0 | - | - | -/- | -→- | -→- | - | - | - | -/- | 0 | 0 |

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


