# SGH-Q24 Sparrow parity quality hardening — LV8 ladder measurements

Production `sparrow_cde` + CDE backend. LV8 subsets are OUTER-ONLY (holes stripped).
Assumptions: sheet 1500x3000 (LV8 fixture), seed 11, rotation orthogonal, pipeline sparrow_cde, backend cde. Every production run counts in the denominator.

| row | hard | status | placed/req | conv | final_pairs | runtime_ms | loss_model | bbox_primary | search_samples | bbox_fb | lbf_fb |
|---|---|---|---|---|---:|---:|---|---|---:|---:|---:|
| medium_10_to_20_items | Y | ok | 12/12 | True | 0 | 24088.5 | CdeSeparationLoss | False | 316 | 0 | 0 |
| lv8_12types_x1 | Y | timeout | -/12 | - | - | 35035.8 | - | - | - | - | - |
| lv8_24_instances | Y | timeout | -/24 | - | - | 35035.6 | - | - | - | - | - |
| lv8_50_instances | n | timeout | -/50 | - | - | 45046.5 | - | - | - | - | - |

## Outcome accounting (all production rows)

| outcome | count |
|---|---:|
| ok | 1 |
| partial | 0 |
| unsupported | 0 |
| timeout | 3 |
| error | 0 |
| **total** | **4** |
| **hard gates passed** | **1/3** |
