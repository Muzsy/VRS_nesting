# DXF Nesting Platform Codex Task - H3-Quality-T7 quality profile-ok es runtime policy / snapshot integration
TASK_SLUG: h3_quality_t7_quality_profiles_and_run_config_integration

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/nesting_quality/nesting_quality_konkret_feladatok.md`
- `worker/main.py`
- `vrs_nesting/runner/nesting_engine_runner.py`
- `api/services/run_snapshot_builder.py`
- `scripts/trial_run_tool_core.py`
- `scripts/run_trial_run_tool.py`
- `scripts/trial_run_tool_gui.py`
- `scripts/run_h3_quality_benchmark.py`
- `docs/nesting_quality/h3_quality_benchmark_harness.md`
- `scripts/smoke_h3_quality_t6_local_tool_backend_selector_and_ab_compare.py`
- `canvases/web_platform/h3_quality_t7_quality_profiles_and_run_config_integration.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t7_quality_profiles_and_run_config_integration.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez a task **nem** SQL migration es nem uj API schema feladat. A quality profile
  truth a snapshot / worker / local tooling vilagban legyen bekotve, schema-bontas
  nelkul.
- A quality-profile registry legyen az egyetlen source of truth; ne duplikald a
  preset mappinget kulon a workerben, kulon a toolban, kulon a benchmark scriptben.
- A task ne allits optimalitast. A benchmark es a report csak evidence-first
  kulonbseget jelentsen.
- Ha regresszios GUI smoke-frissites nem szukseges, ne nyulj a
  `scripts/smoke_trial_run_tool_tkinter_gui.py` fajlhoz. Ha szukseges, az mar
  szerepel az outputsban, es evidence-szel indokold a reportban.

Implementacios elvarasok:
- Hozz letre kozos quality-profile regisztert minimum ezekkel a nevekkel:
  - `fast_preview`
  - `quality_default`
  - `quality_aggressive`
- A regiszter legalabb a kovetkezo v2 runtime dimenziokat irja le:
  - `placer`
  - `search`
  - `part_in_part`
  - opcionlisan SA parameterek (`sa_iters`, `sa_temp_start`, `sa_temp_end`,
    `sa_eval_budget_sec`), ha a preset ezt hasznalja.
- A `nesting_engine_runner.py` tudjon opcionisan ilyen CLI flag-eket tovabbitani a
  Rust `nesting_engine nest` subprocessnek. A runner metadata / report oldalon legyen
  visszakovetheto, milyen flag-ek mentek ki.
- A `run_snapshot_builder.py` irjon explicit quality-profile truthot a
  `solver_config_jsonb`-be. Minimum: `quality_profile`, plusz egy egyertelmu,
  nesting-engine specifikus runtime policy blokk, amit a worker kozvetlenul fel tud
  hasznalni.
- A `worker/main.py` a snapshotbol vagy runtime override-bol resolved profile alapjan
  epitse a v2 runner invokaciot, es az `engine_meta.json`-ben kulon jelezze:
  - `requested_engine_profile`
  - `effective_engine_profile`
  - `engine_profile_match`
  - `nesting_engine_cli_args`
- DONTSD EL es dokumentald: hogyan viselkedik a rendszer, ha a backend nem
  `nesting_engine_v2`, de explicit quality profile van megadva. A dontes legyen
  egyertelmu (noop vagy fail-fast), es a report nevezzze meg.
- A local tool core/CLI/GUI kapjon explicit `quality_profile` valasztast.
- A `run_h3_quality_benchmark.py` tudjon legalabb case x profile matrixot epiteni
  `nesting_engine_v2` backendhez, es a benchmark output / quality summary
  profile-szintu requested vs effective truthot adjon.
- A compare / plan-only output legalabb ezeket kezelje profile-szinten:
  - `sheet_count`
  - `utilization_pct`
  - `runtime_sec`
  - `nonzero_rotation_count`

A dedikalt smoke bizonyitsa legalabb:
- a profile registry a vart preseteket adja;
- a worker a vart nesting-engine CLI argokat allitja elo a harom profilra;
- a snapshot builder default quality-profile truthot ad;
- a local tool config normalizalas a profile mezot is hordozza;
- a benchmark runner `--plan-only` modban profile matrixot tud epiteni;
- valodi Supabase, worker es solver nelkul is PASS.

A reportban kulon nevezd meg:
- mi a kanonikus profile-registry es miert ott van;
- hogyan kerul a quality-profile truth a snapshotba;
- hogyan epiti a worker a v2 runner CLI flagjeit;
- hogyan kezeli a task a `sparrow_v1` + explicit profile kombinaciot;
- hogyan mukodik a local tool / benchmark profile selector;
- hogy a task tudatosan meg mindig runtime/policy integracios kor, nem tuning es nem schema-munka.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t7_quality_profiles_and_run_config_integration.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
