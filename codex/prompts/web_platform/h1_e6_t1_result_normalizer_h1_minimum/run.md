# DXF Nesting Platform Codex Task - H1-E6-T1 Result normalizer (H1 minimum)
TASK_SLUG: h1_e6_t1_result_normalizer_h1_minimum

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `docs/solver_io_contract.md`
- `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql`
- `worker/main.py`
- `worker/engine_adapter_input.py`
- `worker/raw_output_artifacts.py`
- `api/services/run_snapshot_builder.py`
- `api/routes/runs.py`
- `canvases/web_platform/h1_e6_t1_result_normalizer_h1_minimum.md`
- `codex/goals/canvases/web_platform/fill_canvas_h1_e6_t1_result_normalizer_h1_minimum.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ne talalj ki nem letezo schema-t, enumot, artifact kindot vagy projection
  mezot: a H0 tablavilagbol, a solver IO contractbol es a snapshot manifest
  truth-bol indulj ki.
- Ez a task H1 minimum **result normalizer / projection truth** scope: ne
  csussz at viewer SVG/DXF, export artifact vagy nagy runs API redesign iranyba.
- A projection write a H0 canonical tablavilagra epuljon:
  `app.run_layout_sheets`, `app.run_layout_placements`,
  `app.run_layout_unplaced`, `app.run_metrics`.
- A mapping part/sheet oldalon a snapshot manifestekre uljon, ne ad hoc raw
  heuristikara.
- A write viselkedes legyen run-szintu idempotens replace; retry utan se maradjon
  stale vagy duplikalt projection sor.
- A worker `done` zarasa csak sikeres normalizer utan tortenhet.

Implementacios elvarasok:
- Legyen explicit worker-oldali result normalizer helper/boundary.
- A `solver_output.json` v1 placements/unplaced lista platformszintu projectionra
  forduljon.
- A `run_layout_sheets` sorok hasznalt sheet indexenkent jojjenek letre, a
  snapshot sheet truth alapjan.
- A `run_layout_placements` sorok placementenkent jojjenek letre
  `transform_jsonb` + determinisztikus `bbox_jsonb` adattal.
- A `run_layout_unplaced` ne nyers instance lista legyen, hanem aggregalt
  `remaining_qty` projection.
- A `run_metrics` counts/utilization ertekek determinisztikusan szamolodjanak.
- A jelenlegi `_read_run_metrics(run_dir)` ne maradjon canonical truth; a final
  run completion counts a normalizer summary-bol jojjenek.
- A smoke script fake snapshot + fake DB gateway mellett bizonyitsa a mapping,
  aggregacio, idempotencia es hibagak helyes viselkedeset.

A reportban kulon nevezd meg:
- hogyan tortenik a part/sheet feloldas a snapshot manifestekbol;
- hogyan keletkezik a `run_layout_*` es `run_metrics` vegallapot;
- hogyan lett megoldva a run-szintu idempotens projection replace;
- hogy a task mit NEM vallal meg (viewer SVG/DXF, export, nagy route-redesign);
- ha a `utilization_ratio` szamitas kompromisszumot igenyel, azt pontosan es
  egyenesen dokumentald.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h1_e6_t1_result_normalizer_h1_minimum.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
