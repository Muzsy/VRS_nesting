# SGH-Q71 Report - Anchor edge-lock and flush alignment

## Verdict: PARTIAL / FAIL FOR TARGET QUALITY

## Run

| run | status | placed | unplaced | used sheets | util % | non-orth rotations | wall s |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| q71_A_edge_lock_2sheet_sp5 | partial | 215 | 61 | 2 | 53.81611027571408 | 186 | 158.5 |

## Forced-latest anchor diagnostics

| check | value |
| --- | --- |
| forced latest lock active | true |
| accepted anchor secondary policy | corner_low |
| selected anchor path | catalog |
| final primary gap mm | 0.011901920409854938 |
| final secondary gap mm | 0.005401936627491555 |
| final min edge gap mm | 0.005401936627491555 |
| final rotation drift deg | 1.0 |
| direct fallback blocked | true |

## Largest-part edge gaps

- Avg min edge gap across the 2 largest part families: `65.609` mm
- Worst min edge gap across the 2 largest part families: `337.831` mm
- Edge-locked placements (`<=40 mm`): `7`

### Lv8_11612_6db

- area mm2: `597467.949`
- placement_count: `4`
- avg_min_edge_gap_mm: `66.294`
- worst_min_edge_gap_mm: `160.036`

| sheet | rot deg | nearest edge | min edge gap mm | left | right | bottom | top |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 280.5 | left | 17.942 | 17.942 | 301.932 | 336.57 | 50.126 |
| 0 | 90.0 | bottom | 5.005 | 761.231 | 5.969 | 5.005 | 473.001 |
| 1 | 268.0 | left | 160.036 | 160.036 | 519.594 | 287.074 | 166.895 |
| 1 | 88.5 | bottom | 82.195 | 500.984 | 200.449 | 82.195 | 377.493 |

### Lv8_15348_6db_GRAVIR

- area mm2: `127379.951`
- placement_count: `6`
- avg_min_edge_gap_mm: `65.151`
- worst_min_edge_gap_mm: `337.831`

| sheet | rot deg | nearest edge | min edge gap mm | left | right | bottom | top |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 240.0 | right | 337.831 | 611.022 | 337.831 | 1065.107 | 1270.278 |
| 0 | 180.0 | bottom | 7.5 | 23.153 | 876.847 | 7.5 | 2702.5 |
| 0 | 180.0 | left | 23.153 | 23.153 | 876.847 | 307.0 | 2403.0 |
| 1 | 80.0 | left | 7.424 | 7.424 | 1102.793 | 1510.009 | 848.748 |
| 1 | 90.0 | left | 7.5 | 7.5 | 1202.5 | 2036.44 | 363.56 |
| 1 | 179.5 | bottom | 7.5 | 23.196 | 874.296 | 7.5 | 2697.275 |

## Comparison vs Q70

| metric | Q70 | Q71 |
| --- | ---: | ---: |
| placed_count | 237 | 215 |
| avg min edge gap (largest parts) | 226.103 | 65.609 |
| worst min edge gap (largest parts) | 553.177 | 337.831 |
| edge_locked_count | 3 | 7 |

## Visual Proxy

- Render manifest: `artifacts/benchmarks/sgh_q71/renders/q71_A_edge_lock_2sheet_sp5/render_manifest.json`
- Input: `inputs/q71_full276_2x1500x3000_margin5_spacing5_continuous_600.json`

## Visual Audit

- A nagy `Lv8_11612_6db` csalad edge-lockja lathatoan jobb lett a Q70-hez kepest.
- A masodik tabla tovabbra sem eleg jo minosegu: a kihasznaltsag gyengebb a Q70-nel, es a
  szerkezet meg mindig nem mutat meggyozo, production-ready residual-space hasznalatot.
- A jelenlegi iteracio nem regresszio a korabbi teljesen kozepre sodrodo allapothoz kepest,
  de nem eri el a vart "jol kitoltott 2 tablas" minoseget.

## Finding

Az aktualis Q71 futas mar valodi edge-lock authorityt mutat a kritikus nagy daraboknal, de ezt
jelentosen romlo darabszammal es tablakitoltesi minoseggel eri el. Emiatt ez a futas szakmailag
inkabb "jobb irany, de meg nem elfogadhato eredmeny", nem pedig kesz megoldas.

## Artifact evidence

- summary: `artifacts/benchmarks/sgh_q71/q71_summary.json`
- output: `artifacts/benchmarks/sgh_q71/outputs/q71_A_edge_lock_2sheet_sp5_output.json`
- log: `artifacts/benchmarks/sgh_q71/logs/q71_A_edge_lock_2sheet_sp5.log`
