# SGH-Q23R3 real Sparrow search lifecycle completion — benchmark measurements

Production path = `sparrow_cde` (CDE-first). `sparrow_experimental` and `phase_optimizer` are comparison-only, not acceptance.

**Accounting:** every production `sparrow_cde` run counts in the denominator (ok / partial / unsupported / timeout / error). Zero/false render as themselves; only missing fields as `-`.

| fixture | pipeline | backend | seed | status | placed/req | runtime_ms | conv | iters | moves a/att | pairs i->f | raw i->f | workers | topk | graph incr/full | restarts | compression | cde_q | engine_builds | bbox_fb | lbf_fb |
|---|---|---|---:|---|---|---:|---|---:|---|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| tiny | sparrow_cde | cde | 1 | ok | 2/2 | 408.7 | True | 2 | 4/4 | 1→0 | 20.0→0.0 | 4 | 2 | 7/1 | 0 | 1 | 282 | 249 | 0 | 0 |
| tiny | sparrow_experimental | cde | 1 | ok | 2/2 | 397.3 | True | 2 | 4/4 | 1→0 | 20.0→0.0 | 4 | 2 | 7/1 | 0 | 1 | 282 | 249 | 0 | 0 |
| tiny | phase_optimizer | bbox | 1 | ok | 2/2 | 2.1 | - | - | -/- | -→- | -→- | - | - | -/- | - | - | - | 0 | 0 | 0 |
| two_rect_overlap | sparrow_cde | cde | 1 | ok | 2/2 | 342.7 | True | 2 | 4/4 | 1→0 | 30.0→0.0 | 4 | 2 | 7/1 | 0 | 1 | 288 | 255 | 0 | 0 |
| two_rect_overlap | sparrow_experimental | cde | 1 | ok | 2/2 | 334.6 | True | 2 | 4/4 | 1→0 | 30.0→0.0 | 4 | 2 | 7/1 | 0 | 1 | 288 | 255 | 0 | 0 |
| two_rect_overlap | phase_optimizer | bbox | 1 | ok | 2/2 | 1.9 | - | - | -/- | -→- | -→- | - | - | -/- | - | - | - | 0 | 0 | 0 |
| boundary_recovery | sparrow_cde | cde | 1 | ok | 1/1 | 3.1 | True | 0 | 0/0 | 0→0 | 0.0→0.0 | 0 | 0 | 0/0 | 0 | 0 | 2 | 1 | 0 | 0 |
| boundary_recovery | sparrow_experimental | cde | 1 | ok | 1/1 | 3.0 | True | 0 | 0/0 | 0→0 | 0.0→0.0 | 0 | 0 | 0/0 | 0 | 0 | 2 | 1 | 0 | 0 |
| boundary_recovery | phase_optimizer | bbox | 1 | ok | 1/1 | 1.8 | - | - | -/- | -→- | -→- | - | - | -/- | - | - | - | 0 | 0 | 0 |
| medium_10_to_20_items | sparrow_cde | cde | 1 | ok | 12/12 | 20577.6 | True | 2 | 24/24 | 66→0 | 1320.0→0.0 | 4 | 6 | 54/2 | 1 | 1 | 11870 | 1808 | 0 | 0 |
| medium_10_to_20_items | sparrow_experimental | cde | 1 | ok | 12/12 | 20281.2 | True | 2 | 24/24 | 66→0 | 1320.0→0.0 | 4 | 6 | 54/2 | 1 | 1 | 11870 | 1808 | 0 | 0 |
| medium_10_to_20_items | phase_optimizer | bbox | 1 | ok | 12/12 | 4.0 | - | - | -/- | -→- | -→- | - | - | -/- | - | - | - | 0 | 0 | 0 |
| lv8_subset | sparrow_cde | cde | 1 | ok | 3/3 | 36921.9 | True | 2 | 4/12 | 3→0 | 98.90625→0.0 | 4 | 3 | 17/2 | 1 | 1 | 1813 | 1059 | 0 | 0 |
| lv8_subset | sparrow_experimental | cde | 1 | ok | 3/3 | 36663.3 | True | 2 | 4/12 | 3→0 | 98.90625→0.0 | 4 | 3 | 17/2 | 1 | 1 | 1813 | 1059 | 0 | 0 |
| lv8_subset | phase_optimizer | bbox | 1 | ok | 3/3 | 4.4 | - | - | -/- | -→- | -→- | - | - | -/- | - | - | - | 0 | 0 | 0 |

## Production (`sparrow_cde`) outcome accounting

| outcome | count |
|---|---:|
| ok | 5 |
| partial | 0 |
| unsupported | 0 |
| timeout | 0 |
| error | 0 |
| **total** | **5** |
| **converged** | **5** |


