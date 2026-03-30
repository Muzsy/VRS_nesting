# DXF Nesting Platform Codex Task - H3-Quality-T6 local tool backend selector es A/B compare lab
TASK_SLUG: h3_quality_t6_local_tool_backend_selector_and_ab_compare

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `scripts/trial_run_tool_core.py`
- `scripts/run_trial_run_tool.py`
- `scripts/trial_run_tool_gui.py`
- `scripts/run_h3_quality_benchmark.py`
- `docs/nesting_quality/h3_quality_benchmark_harness.md`
- `scripts/smoke_trial_run_tool_cli_core.py`
- `scripts/smoke_h3_quality_t2_benchmark_pack_and_quality_summary_harness.py`
- `canvases/web_platform/h3_quality_t6_local_tool_backend_selector_and_ab_compare.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t6_local_tool_backend_selector_and_ab_compare.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez a task local tooling feladat. Ne nyiss DB/API schema, migration vagy product
  feature-kort az engine backend tarolasara.
- A local tool backend selector defaultja `auto` maradjon; a meglevo egybackendes
  hasznalat ne torjon el.
- A compare summary additive, evidence-first legyen; ne allits optimalitast,
  csak merheto kulonbseget.

Implementacios elvarasok:
- A core/CLI/GUI vilag kapjon explicit backend selectort a kovetkezo ertekekkel:
  `auto`, `sparrow_v1`, `nesting_engine_v2`.
- Konkret backend eseten a `scripts/run_web_platform.sh` start/restart subprocess
  hivasai kapjanak `WORKER_ENGINE_BACKEND=<...>` env override-ot. `auto` eseten ne
  kenyszerits env override-ot.
- A summary / `quality_summary.json` kulon tudja a `requested_engine_backend`, az
  evidence-bol olvasott `effective_engine_backend` es az `engine_backend_match`
  mezoket.
- A benchmark runner kapjon backend matrix kepesseget. Minimum:
  - egy backend explicit futtatasa;
  - tobb backend repeatable valasztasa;
  - `--compare-backends` shortcut a `sparrow_v1` + `nesting_engine_v2` parhoz;
  - `--plan-only` modban is latszodjon a backend x case terv.
- Az output tartalmazzon gepileg olvashato compare blokkot minden olyan case-re,
  ahol legalabb ket backendes quality summary van. Minimum delta mezok:
  `sheet_count_delta`, `utilization_pct_delta`, `runtime_sec_delta`,
  `nonzero_rotation_delta`, `winner_by_sheet_count`, `winner_by_utilization`.
- A compare logika legyen hibaturo: ha valamelyik side hianyzik vagy erroros,
  ezt explicit `incomplete_reason` / `notes` mezovel jelezze.

A smoke bizonyitsa legalabb:
- a CLI es GUI config normalizalas helyesen kezeli a backend selector erteket;
- a subprocess env override start/restart hivasnal helyes `WORKER_ENGINE_BACKEND`
  erteket kap;
- a benchmark runner `--plan-only --compare-backends` modban determinisztikus
  case x backend matrixot ir;
- fake `run_trial` eredmenyekbol a compare delta blokk helyesen epul fel;
- valodi Supabase, valodi solver es valodi worker processz nelkul is PASS.

A reportban kulon nevezd meg:
- hogyan kerul at a kert backend a local tool teljes lancan;
- hogyan lesz szetvalasztva a requested vs effective backend truth;
- hogyan mukodik a benchmark matrix es a compare delta output;
- hogy a task tudatosan meg mindig local tooling scope, nem API/DB feature.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t6_local_tool_backend_selector_and_ab_compare.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
