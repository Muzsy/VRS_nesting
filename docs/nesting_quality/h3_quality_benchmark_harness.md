# H3 Quality Benchmark Harness

## Cel
Ez a benchmark pack a trial tool futasok quality-jeleit teszi osszehasonlithatova
repo-local, determinisztikus fixture-ekkel es gepileg olvashato summary outputtal.

## Kapcsolat a T1 truth reteggel
- A T1-ben rögzitett canonical `solver_input` es `engine_meta` artefaktokra epul.
- A benchmark lane ugyanebbol az evidence-vilagbol olvas (`run_artifacts`, `viewer_data`, `summary`, `quality_summary`).
- Nem vezet be uj worker backendet vagy uj perszisztalt quality tablat.

## Kapcsolat a kesobbi T3/T4 feladatokkal
- T3 (`v2 adapter`) utan ugyanaz a benchmark case-pack futtathato v2 inputtal.
- T4 (`dual-engine`) utan ugyanaz a harness adhat A/B osszehasonlitast backendenkent.
- A jelen task outputja direkt evidence-first, igy az A/B osszehasonlitas nem black-box score-okra epul.

## Benchmark case-ek
- `triangles_rotation_pair`
  - cel: nonzero rotation es tobb sor jellegu elrendezes jelzese.
- `circles_dense_pack`
  - cel: suru ismétlodesi case, egyetlen forma-csaladdal.
- `lshape_rect_mix`
  - cel: vegyes (konkav + teglalap) geometriaknal extent/row jellegu jelek.

## Futtatas

1. Fixture pack generalas:
```bash
python3 scripts/gen_h3_quality_benchmark_fixtures.py
```

2. Plan-only benchmark ellenorzes (live platform nelkul):
```bash
python3 scripts/run_h3_quality_benchmark.py --plan-only
```

3. Valos benchmark futas (lokalis platform + token mellett):
```bash
python3 scripts/run_h3_quality_benchmark.py \
  --api-base-url http://127.0.0.1:8000/v1 \
  --token "$API_BEARER_TOKEN"
```

## Evidence-first KPI-k
- `placements_count`, `unplaced_count`, `sheets_used`
- `solver_utilization_pct` (ha elerheto)
- `sheet_width_mm`, `sheet_height_mm` (ha ismert)
- `unique_rotations_deg`, `nonzero_rotation_count`, `rotation_histogram`
- `occupied_extent_mm`, `coverage_ratio_x`, `coverage_ratio_y` (ha szamolhato)
- `artifact_completeness`, `artifact_presence`
- `signals` (pl. `single_sheet`, `multi_row_layout_signal`, `coverage_ratio_known`)

## Mit NEM jelent ez a harness
- Nem ad vegso "optimalis" vagy "industrial_grade" score-t.
- Nem allit geometriai optimumot bizonyitott evidence nelkul.
- Nem helyettesiti a kesobbi v2/dual-engine celzott minosegi benchmarkokat.
