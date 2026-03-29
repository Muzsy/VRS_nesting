# H3-Quality-T2 Benchmark pack es quality summary harness

## Funkcio
Ez a task a H3 quality lane masodik lepese.
A cel nem meg a `nesting_engine_v2` bekotese, hanem az, hogy a jelenlegi
web_platform + trial tool vilagban legyen **repo-local, determinisztikus
benchmark pack** es **gepileg olvashato quality summary**, amire a kesobbi
v2 adapter / dual-engine A-B osszehasonlitas ra tud ulni.

A T1 utan mar van canonical `solver_input` truth es explicit `engine_meta`.
A kovetkezo hiany most ez:
- nincs repo-ban formalizalt quality benchmark esetkeszlet a trial toolhoz;
- nincs egyetlen, stabil `quality_summary.json`, amit case-enkent merge-elni
  vagy benchmark reportta alakithatunk;
- a `scripts/run_trial_run_tool.py` ma alapvetoen egy single-case CLI,
  benchmark orchestration nelkul;
- a quality problemakrol ma foleg `summary.md`, `viewer_data.json`,
  `runner_meta.json` es `solver_output.json` alapjan, kezzel kell kovetkeztetni.

Ez a task ezt rendezi el egy minimalis, de hasznalhato benchmark lane-re.

## Scope

### Benne van
- determinisztikus, repo-local benchmark fixture generator a trial toolhoz;
- benchmark manifest, ami explicit case-eket, sheet mereteket,
  qty override-okat es elvart quality-jeleket rogzit;
- gepileg olvashato `quality_summary.json` a trial tool futas vegere;
- dedikalt benchmark runner, ami a manifest alapjan egymas utan futtatja a
  case-eket es egy merged benchmark JSON-t ir;
- olyan smoke, ami live platform nelkul bizonyitja:
  - a fixture generator determinisztikus;
  - a manifest ervenyes;
  - a `quality_summary.json` schema es KPI-k kepzese stabil;
  - a benchmark runner `--plan-only` modban helyesen oldja fel a case-eket.

### Nincs benne
- `nesting_engine_v2` input adapter;
- worker backend valtas / dual-engine switch;
- viewer v2 output parse;
- H3-E4 remnant / inventory domain;
- DXF preflight/normalize implementacio;
- automatikus quality verdict, ami a tenyleges geometriai optimalitast
  "kitalalja" a rendelkezere allo evidence-en tul.

## Talalt relevans fajlok / meglvo mintak
- `scripts/trial_run_tool_core.py`
  - mar kezeli a teljes API orchestrationt es run evidence menteset;
  - mar ir `summary.md`-t es letolti a fo artifactokat;
  - a T1 utan mar van `engine_meta` es artifact evidence logika.
- `scripts/run_trial_run_tool.py`
  - jelenleg single-case CLI entrypoint;
  - benchmark mode meg nincs.
- `scripts/smoke_trial_run_tool_cli_core.py`
  - jo minta fake-transportos, live platform nelkuli smoke-hoz.
- `samples/dxf_demo/stock_rect_1000x2000.dxf`
  - letezo repo stock minta.
- `samples/dxf_demo/part_arc_spline_chaining_ok.dxf`
  - letezo repo part minta.
- tobb repo smoke script is generál DXF-et programbol `ezdxf`-fel, pl.:
  - `scripts/smoke_h1_real_infra_closure.py`
  - `scripts/smoke_h1_e2_t1_dxf_parser_integracio.py`
  - `scripts/smoke_h2_e2_t1_manufacturing_canonical_derivative_generation.py`
- a repo-ban mar leteznek benchmark/tooling mintak:
  - `scripts/bench_nesting_engine_f2_3_large_fixture.py`
  - `scripts/gen_nesting_engine_real_dxf_quality_fixture.py`

## Mi legyen a task konkret kimenete

### 1. Benchmark fixture generator
Keszits dedikalt generatort, pl.:
- `scripts/gen_h3_quality_benchmark_fixtures.py`

A generator celja:
- `ezdxf`-fel hozzon letre determinisztikus `CUT_OUTER` layeres benchmark
  DXF packokat egy target konyvtarba;
- legalabb 3 benchmark case legyen:
  1. `triangles_rotation_pair`
  2. `circles_dense_pack`
  3. `lshape_rect_mix`
- ugyanarra a case-re ket futas ugyanazokat a fajlneveket es ugyanazt a
  geometriai tartalmat adja;
- a generator ne talaljon ki uj import policy-t: maradjon a jelenlegi H1/H2 DXF
  import szabalyoknak megfelelo, egyszeru `CUT_OUTER` outputnal.

### 2. Benchmark manifest
Keszits repo-local manifestet, pl.:
- `samples/trial_run_quality/benchmark_manifest_v1.json`

A manifest case-enkent minimum rogzitse:
- `case_id`
- `fixture_kind`
- `sheet_width_mm`
- `sheet_height_mm`
- `default_qty`
- `qty_overrides`
- `notes`
- `expected_signals`

Az `expected_signals` nem legyen "optimalis nesting" allitas, hanem csak olyan,
ami a summary evidence-bol tenyleg kiolvashato. Pelda:
- `expects_nonzero_rotation_signal`
- `expects_multiple_distinct_y_rows`
- `expects_dense_repetition_case`

### 3. Quality summary JSON
A `scripts/trial_run_tool_core.py` a futas vegen irjon stabil, gepileg olvashato
`quality_summary.json` fajlt.

Minimum mezok:
- `status`
- `run_id`
- `project_id`
- `engine_backend`
- `engine_contract_version`
- `engine_profile`
- `final_run_status`
- `placements_count`
- `unplaced_count`
- `sheets_used`
- `solver_utilization_pct` (ha van)
- `sheet_width_mm`, `sheet_height_mm` (ha van)
- `unique_rotations_deg`
- `nonzero_rotation_count`
- `rotation_histogram`
- `occupied_extent_mm`
- `coverage_ratio_x`, `coverage_ratio_y` (ha szamolhato)
- `artifact_completeness`
- `artifact_presence`
- `signals`

A `signals` maradjon evidence-first. Elfogadhato peldak:
- `all_zero_rotation`
- `single_rotation_family`
- `single_sheet`
- `multi_row_layout_signal`
- `coverage_ratio_known`

Nem elfogadhato ebben a taskban:
- "optimal"
- "industrial_grade"
- barmilyen feketedoboz quality score, aminek nincs kozvetlen bizonyiteka.

### 4. Benchmark runner
Keszits dedikalt runner scriptet, pl.:
- `scripts/run_h3_quality_benchmark.py`

Feladata:
- beolvassa a manifestet;
- case-enkent legeneralja a fixture konyvtarat a generatorral;
- meghivja a trial tool core-t (`run_trial`) ugyanazzal a benchmark schema-val;
- egy merged benchmark JSON-t ir, pl. `runs/benchmarks/h3_quality_benchmark_v1.json`;
- tudjon `--plan-only` modot, ami live platform nelkul is ellenorizheto.

Case output minimum:
- `case_id`
- `fixture_kind`
- `run_dir`
- `success`
- `final_run_status`
- `quality_summary_path`
- `quality_summary`
- `notes`

### 5. Dokumentacio
Keszits rovid benchmark lane doksit, pl.:
- `docs/nesting_quality/h3_quality_benchmark_harness.md`

Tartalom minimum:
- mire jo a benchmark pack;
- hogyan kapcsolodik a T1 truth layerhez;
- hogyan kapcsolodik majd a T3/T4 v2 adapter es dual-engine taskhoz;
- hogyan kell futtatni a benchmark runnert valodi lokalis platformon;
- mely KPI-k evidence-first es melyek NEM tekinthetok vegso quality score-nak.

## DoD
- letezik determinisztikus benchmark fixture generator;
- letezik repo-local benchmark manifest legalabb 3 case-szel;
- a trial tool futas vegere letrejon a `quality_summary.json`;
- a benchmark runner `--plan-only` modban live platform nelkul ellenorizheto;
- a dedikalt smoke zold es bizonyitja a generator/manifest/summary schema stabilitast;
- a standard verify wrapper lefut, report + log frissul.

## Erintett fajlok / celzott outputok
- `canvases/web_platform/h3_quality_t2_benchmark_pack_and_quality_summary_harness.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t2_benchmark_pack_and_quality_summary_harness.yaml`
- `codex/prompts/web_platform/h3_quality_t2_benchmark_pack_and_quality_summary_harness/run.md`
- `scripts/gen_h3_quality_benchmark_fixtures.py`
- `samples/trial_run_quality/benchmark_manifest_v1.json`
- `scripts/trial_run_tool_core.py`
- `scripts/run_h3_quality_benchmark.py`
- `docs/nesting_quality/h3_quality_benchmark_harness.md`
- `scripts/smoke_h3_quality_t2_benchmark_pack_and_quality_summary_harness.py`
- `codex/codex_checklist/web_platform/h3_quality_t2_benchmark_pack_and_quality_summary_harness.md`
- `codex/reports/web_platform/h3_quality_t2_benchmark_pack_and_quality_summary_harness.md`

## Nem alkukepes korlatok
- A task maradjon v1 / jelenlegi worker-truth vilagban.
- Ne vezesd be a `nesting_engine_v2`-t ebben a taskban.
- A benchmark runner ne talaljon ki uj API endpointot vagy worker oldali specialis
  benchmark modot.
- A smoke es verify ne koveteljen el live Supabase/API futast;
  erre legyen `--plan-only` / fake-transport / synthetic evidence ut.
- A benchmark signalok maradjanak auditálhato, simple evidence jelek.
