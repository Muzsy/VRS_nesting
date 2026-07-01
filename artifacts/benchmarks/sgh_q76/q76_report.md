# SGH-Q76 Report - Skeleton-first seed + residual-fill (contour residual-space objective)

## Verdict: ACCEPT

- time limit/run: **240s**
- accept rule: skeleton-first valid (final_pairs=0) AND >= default placed AND >= default util on EVERY package

## A/B per package (default vs skeleton-first)

| package | arm | status | placed | unplaced | used | util % | final_pairs | wall s |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| full276 | default | partial | 252 | 24 | 2 | 37.96 | 0 | 86.6 |
| full276 | skeleton_first | partial | 274 | 2 | 2 | 65.07 | 0 | 139.6 |
| mixedmed | default | ok | 120 | 0 | 2 | 78.85 | 0 | 15.6 |
| mixedmed | skeleton_first | ok | 120 | 0 | 2 | 78.85 | 0 | 15.2 |

## Q76 skeleton diagnostics (skeleton-first arm)

| package | skel_count | skel_area_frac | free_after_skel | fill_placed | fill_unplaced | final_free |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| full276 | 11 | 0.4866 | 7716268.0 | 272 | 2 | 1059681.0 |
| mixedmed | 10 | 0.0967 | 8955050.0 | 91 | 29 | 1174107.0 |

## Per-package verdict

- **full276**: ACCEPT - placed 274>=252, util 65.07>=~37.96
- **mixedmed**: ACCEPT - placed 120>=120, util 78.85>=~78.85
