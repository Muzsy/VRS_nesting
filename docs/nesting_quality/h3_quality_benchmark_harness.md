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

4. Explicit backend kivalasztas:
```bash
python3 scripts/run_h3_quality_benchmark.py --engine-backend sparrow_v1
```

5. Explicit quality profile kivalasztas:
```bash
python3 scripts/run_h3_quality_benchmark.py --quality-profile quality_default
```

6. Backend matrix futas (case x backend):
```bash
python3 scripts/run_h3_quality_benchmark.py \
  --engine-backend sparrow_v1 --engine-backend nesting_engine_v2
```

7. Profile matrix futas (case x profile):
```bash
python3 scripts/run_h3_quality_benchmark.py \
  --engine-backend nesting_engine_v2 \
  --quality-profile fast_preview \
  --quality-profile quality_default \
  --quality-profile quality_aggressive
```

8. Backend + profile matrix futas (case x backend x profile):
```bash
python3 scripts/run_h3_quality_benchmark.py \
  --engine-backend sparrow_v1 \
  --engine-backend nesting_engine_v2 \
  --quality-profile fast_preview \
  --quality-profile quality_default \
  --quality-profile quality_aggressive
```

9. A/B compare convenience mod:
```bash
python3 scripts/run_h3_quality_benchmark.py --compare-backends
```

10. Plan-only compare matrix ellenorzes:
```bash
python3 scripts/run_h3_quality_benchmark.py --plan-only --compare-backends
```

11. Plan-only profile matrix ellenorzes:
```bash
python3 scripts/run_h3_quality_benchmark.py \
  --plan-only \
  --engine-backend nesting_engine_v2 \
  --quality-profile fast_preview \
  --quality-profile quality_default \
  --quality-profile quality_aggressive
```

## Backend/Profile matrix es compare delta

A `--compare-backends` flag automatikusan a `sparrow_v1` + `nesting_engine_v2` backend
part futtatja minden case-re. Ha tobb quality profile van kerve, akkor a compare
delta profile-onkent keszul (case + profile kulccsal). Az output `compare_results`
tombje gepileg olvashato delta blokkokat ad minden olyan case/profile csoportra,
ahol ket backendes quality summary letezik.

Delta mezok:
- `quality_profile`
- `sheet_count_delta`
- `utilization_pct_delta`
- `runtime_sec_delta`
- `nonzero_rotation_delta`
- `remnant_value_ppm_delta`
- `occupied_extent_width_delta_mm`
- `occupied_extent_height_delta_mm`
- `compaction_moved_items_delta`
- `winner_by_sheet_count`
- `winner_by_utilization`
- `incomplete_reason` / `notes` (ha valamelyik side hianyzik vagy erroros)

## Evidence-first KPI-k
- `placements_count`, `unplaced_count`, `sheets_used`
- `solver_utilization_pct` (ha elerheto)
- `remnant_value_ppm`, `remnant_compactness_score_ppm`
- `sheet_width_mm`, `sheet_height_mm` (ha ismert)
- `unique_rotations_deg`, `nonzero_rotation_count`, `rotation_histogram`
- `occupied_extent_mm`, `coverage_ratio_x`, `coverage_ratio_y` (ha szamolhato)
- `compaction_mode`, `compaction_applied`, `compaction_moved_items_count`
- `occupied_extent_before_mm`, `occupied_extent_after_mm`
- `artifact_completeness`, `artifact_presence`
- `signals` (pl. `single_sheet`, `multi_row_layout_signal`, `coverage_ratio_known`)

## Mit NEM jelent ez a harness
- Nem ad vegso "optimalis" vagy "industrial_grade" score-t.
- Nem allit geometriai optimumot bizonyitott evidence nelkul.
- Nem helyettesiti a kesobbi v2/dual-engine celzott minosegi benchmarkokat.
