# SGH-Q42 Report - Full276 LV8 continuous rotation benchmark

## Verdict: FAIL / NOT ACHIEVED

## Goal

- Full276 LV8 package, max 3 x 1500x3000 mm sheets.
- Target: valid nesting on <= 2 sheets.
- Technology: margin 5.0 mm, spacing 8.0 mm, kerf 0.0 mm.
- Rotation: global `rotation_policy = continuous` with part-level legacy lists removed from Q42 input.

## Runs

| run | status | placed | unplaced | used sheets | used indices | util physical % | final pairs | boundary | margin viol | spacing viol | wall s | runtime ms | acceptance |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| q42_full276_3x1500x3000_margin5_spacing8_continuous_1200 | ok | 276 | 0 | 3 | [0, 1, 2] | 49.4037 | 0 | 0 | 0 | 0 | 716.692 | 706582.953092 | FAIL |
| q42_full276_3x1500x3000_margin5_spacing8_continuous_2400 | ok | 276 | 0 | 3 | [0, 1, 2] | 49.4037 | 0 | 0 | 0 | 0 | 1315.501 | 1305567.990552 | FAIL |

## Continuous rotation evidence

### q42_full276_3x1500x3000_margin5_spacing8_continuous_1200

- input `rotation_policy`: `continuous`
- part-level `allowed_rotations_deg` count in generated input: `0`
- handling: `removed_from_q42_generated_input`
- unique rotation values count: `236`
- non-orthogonal rotation count: `259`
- min/max rotation: `0.0` / `349.86328125`
- continuous proven by output: `True`
- non-orthogonal examples: `[{'instance_id': 'LV8_00035_28db_M__0001', 'part_id': 'LV8_00035_28db_M', 'sheet_index': 2, 'rotation_deg': 209.667188}, {'instance_id': 'LV8_00035_28db_M__0002', 'part_id': 'LV8_00035_28db_M', 'sheet_index': 0, 'rotation_deg': 56.625}, {'instance_id': 'LV8_00035_28db_M__0004', 'part_id': 'LV8_00035_28db_M', 'sheet_index': 0, 'rotation_deg': 11.625}, {'instance_id': 'LV8_00035_28db_M__0005', 'part_id': 'LV8_00035_28db_M', 'sheet_index': 1, 'rotation_deg': 315.0}, {'instance_id': 'LV8_00035_28db_M__0006', 'part_id': 'LV8_00035_28db_M', 'sheet_index': 1, 'rotation_deg': 304.195312}, {'instance_id': 'LV8_00035_28db_M__0007', 'part_id': 'LV8_00035_28db_M', 'sheet_index': 2, 'rotation_deg': 98.695312}, {'instance_id': 'LV8_00035_28db_M__0008', 'part_id': 'LV8_00035_28db_M', 'sheet_index': 0, 'rotation_deg': 131.98125}, {'instance_id': 'LV8_00035_28db_M__0009', 'part_id': 'LV8_00035_28db_M', 'sheet_index': 0, 'rotation_deg': 348.75}, {'instance_id': 'LV8_00035_28db_M__0010', 'part_id': 'LV8_00035_28db_M', 'sheet_index': 1, 'rotation_deg': 164.990625}, {'instance_id': 'LV8_00035_28db_M__0011', 'part_id': 'LV8_00035_28db_M', 'sheet_index': 0, 'rotation_deg': 185.68125}]`

### q42_full276_3x1500x3000_margin5_spacing8_continuous_2400

- input `rotation_policy`: `continuous`
- part-level `allowed_rotations_deg` count in generated input: `0`
- handling: `removed_from_q42_generated_input`
- unique rotation values count: `236`
- non-orthogonal rotation count: `259`
- min/max rotation: `0.0` / `349.86328125`
- continuous proven by output: `True`
- non-orthogonal examples: `[{'instance_id': 'LV8_00035_28db_M__0001', 'part_id': 'LV8_00035_28db_M', 'sheet_index': 2, 'rotation_deg': 209.667188}, {'instance_id': 'LV8_00035_28db_M__0002', 'part_id': 'LV8_00035_28db_M', 'sheet_index': 0, 'rotation_deg': 56.625}, {'instance_id': 'LV8_00035_28db_M__0004', 'part_id': 'LV8_00035_28db_M', 'sheet_index': 0, 'rotation_deg': 11.625}, {'instance_id': 'LV8_00035_28db_M__0005', 'part_id': 'LV8_00035_28db_M', 'sheet_index': 1, 'rotation_deg': 315.0}, {'instance_id': 'LV8_00035_28db_M__0006', 'part_id': 'LV8_00035_28db_M', 'sheet_index': 1, 'rotation_deg': 304.195312}, {'instance_id': 'LV8_00035_28db_M__0007', 'part_id': 'LV8_00035_28db_M', 'sheet_index': 2, 'rotation_deg': 98.695312}, {'instance_id': 'LV8_00035_28db_M__0008', 'part_id': 'LV8_00035_28db_M', 'sheet_index': 0, 'rotation_deg': 131.98125}, {'instance_id': 'LV8_00035_28db_M__0009', 'part_id': 'LV8_00035_28db_M', 'sheet_index': 0, 'rotation_deg': 348.75}, {'instance_id': 'LV8_00035_28db_M__0010', 'part_id': 'LV8_00035_28db_M', 'sheet_index': 1, 'rotation_deg': 164.990625}, {'instance_id': 'LV8_00035_28db_M__0011', 'part_id': 'LV8_00035_28db_M', 'sheet_index': 0, 'rotation_deg': 185.68125}]`

## Margin / spacing validation

| run | margin | spacing | kerf | sheet margin applied | part spacing applied | margin violations | spacing violations |
| --- | ---: | ---: | ---: | --- | --- | ---: | ---: |
| q42_full276_3x1500x3000_margin5_spacing8_continuous_1200 | 5.0 | 8.0 | 0.0 | True | True | 0 | 0 |
| q42_full276_3x1500x3000_margin5_spacing8_continuous_2400 | 5.0 | 8.0 | 0.0 | True | True | 0 | 0 |

## Best result

- Best run: `q42_full276_3x1500x3000_margin5_spacing8_continuous_1200`
- Best valid sheet count: `3`
- Acceptance achieved: `False`

## Render evidence

- `q42_full276_3x1500x3000_margin5_spacing8_continuous_1200`: `artifacts/benchmarks/sgh_q42/renders/q42_full276_3x1500x3000_margin5_spacing8_continuous_1200/render_manifest.json`
- `q42_full276_3x1500x3000_margin5_spacing8_continuous_2400`: `artifacts/benchmarks/sgh_q42/renders/q42_full276_3x1500x3000_margin5_spacing8_continuous_2400/render_manifest.json`
