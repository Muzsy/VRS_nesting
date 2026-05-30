# SGH-Q23R2 real Sparrow cutover completion — benchmark measurements

Production path = `sparrow_cde` (CDE-first). `sparrow_experimental` and `phase_optimizer` are comparison-only, not acceptance.

**Accounting:** every production `sparrow_cde` run counts in the denominator (ok / partial / unsupported / timeout / error). Zero/false render as themselves; only missing fields as `-`.

| fixture | pipeline | backend | seed | status | placed/req | runtime_ms | conv | iters | moves a/att | pairs i→f | raw i→f | cde_q | engine_builds | bphase_pruned | bbox_fb | lbf_fb |
|---|---|---|---:|---|---|---:|---|---:|---|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|
| tiny | sparrow_cde | cde | 1 | ok | 2/2 | 156.1 | True | 2 | 1/1 | 1→0 | 20.0→0.0 | 94 | 67 | 23 | 67 | 1 | 68 | 1 | 0 | 0 |
| tiny | sparrow_experimental | cde | 1 | ok | 2/2 | 160.3 | True | 2 | 1/1 | 1→0 | 20.0→0.0 | 94 | 67 | 23 | 67 | 1 | 68 | 1 | 0 | 0 |
| tiny | phase_optimizer | bbox | 1 | ok | 2/2 | 1.8 | - | - | -/- | -→- | -→- | - | - | - | - | - | 0 | - | 0 | 0 |
| two_rect_overlap | sparrow_cde | cde | 1 | ok | 2/2 | 372.6 | True | 2 | 1/1 | 1→0 | 30.0→0.0 | 100 | 73 | 23 | 73 | 5 | 78 | 253 | 0 | 0 |
| two_rect_overlap | sparrow_experimental | cde | 1 | ok | 2/2 | 396.5 | True | 2 | 1/1 | 1→0 | 30.0→0.0 | 100 | 73 | 23 | 73 | 5 | 78 | 253 | 0 | 0 |
| two_rect_overlap | phase_optimizer | bbox | 1 | ok | 2/2 | 2.7 | - | - | -/- | -→- | -→- | - | - | - | - | - | 0 | - | 0 | 0 |
| boundary_recovery | sparrow_cde | cde | 1 | ok | 1/1 | 3.5 | True | 0 | 0/0 | 0→0 | 0.0→0.0 | 2 | 1 | 0 | 1 | 0 | 1 | 0 | 0 | 0 |
| boundary_recovery | sparrow_experimental | cde | 1 | ok | 1/1 | 3.3 | True | 0 | 0/0 | 0→0 | 0.0→0.0 | 2 | 1 | 0 | 1 | 0 | 1 | 0 | 0 | 0 |
| boundary_recovery | phase_optimizer | bbox | 1 | ok | 1/1 | 1.9 | - | - | -/- | -→- | -→- | - | - | - | - | - | 0 | - | 0 | 0 |
| medium_10_to_20_items | sparrow_cde | cde | 1 | unsupported | 0/12 | 10094.5 | False | 7 | 6/6 | 66→15 | 1320.0→300.0 | 5826 | 72 | 43 | 72 | 126 | 198 | 7982 | 0 | 0 |
| medium_10_to_20_items | sparrow_experimental | cde | 1 | unsupported | 0/12 | 10117.1 | False | 7 | 6/6 | 66→15 | 1320.0→300.0 | 5826 | 72 | 43 | 72 | 126 | 198 | 7982 | 0 | 0 |
| medium_10_to_20_items | phase_optimizer | bbox | 1 | ok | 12/12 | 3.3 | - | - | -/- | -→- | -→- | - | - | - | - | - | 0 | - | 0 | 0 |

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


