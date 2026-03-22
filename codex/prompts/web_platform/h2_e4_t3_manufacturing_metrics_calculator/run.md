# DXF Nesting Platform Codex Task - H2-E4-T3 manufacturing metrics calculator
TASK_SLUG: h2_e4_t3_manufacturing_metrics_calculator

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_priorizalt_sprint_backlog_p0_p1_p2.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql`
- `supabase/migrations/20260322023000_h2_e4_t2_manufacturing_plan_builder.sql`
- `supabase/migrations/20260322004000_h2_e2_t2_contour_classification_service.sql`
- `supabase/migrations/20260322013000_h2_e3_t2_cut_contour_rules_model.sql`
- `api/services/manufacturing_plan_builder.py`
- `api/services/cut_contour_rules.py`
- `worker/result_normalizer.py`
- `canvases/web_platform/h2_e4_t3_manufacturing_metrics_calculator.md`
- `codex/goals/canvases/web_platform/fill_canvas_h2_e4_t3_manufacturing_metrics_calculator.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- A metrics calculator a mar persisted H2 plan truthra epul:
  - `run_manufacturing_plans`
  - `run_manufacturing_contours`
  - kapcsolodo `geometry_contour_classes`
  - kapcsolodo `cut_contour_rules`
- A calculator ne olvasson live `project_manufacturing_selection` allapotot,
  ne legyen resolver, es ne hasznaljon machine/material catalog logikat.
- A H2 manufacturing metrics maradjon kulon tabla a H1 `run_metrics` mellett;
  ne olvaszd ossze a ket reteget.
- A `pierce_count` a matched rule truthbol jojjon (`cut_contour_rules.pierce_count`).
- Az `estimated_cut_length_mm` a contour class perimeter truthbol jojjon
  (`geometry_contour_classes.perimeter_mm`).
- Az `estimated_rapid_length_mm` legyen egyszeru, determinisztikus,
  gepfuggetlen proxy az egymas utani entry pontokbol.
- Az `estimated_process_time_s` legyen dokumentalt, egyszeru proxy formula;
  ne talalj ki gepresolvert, anyagprofilt vagy valodi CAM-idomodellt.
- A task scope-ja keskeny marad:
  - kulon `run_manufacturing_metrics` truth reteg
  - calculator service
  - task-specifikus smoke
- Kifejezetten out-of-scope:
  - preview SVG
  - postprocessor aktivacio
  - export artifact
  - pricing / quoting / costing engine
  - korabbi truth tablak visszairasa

Implementacios fokusz:
- Hasznald mintanak:
  - `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql`
  - `supabase/migrations/20260322023000_h2_e4_t2_manufacturing_plan_builder.sql`
  - `api/services/manufacturing_plan_builder.py`
  - `worker/result_normalizer.py`
- A metrics rekord legyen idempotens per `run_id`.
- A `metrics_jsonb` tartalmazzon bontott, auditálhato reszleteket es a timing
  proxy feltetelezeseit.
- A smoke legyen bizonyito ereju, ne csak happy-path demo.

A reportban kulon nevezd meg:
- hogy a task mit szallit le a H2-E4-T3 metrics retegre;
- hogy mit NEM szallit le meg:
  - preview,
  - postprocessor,
  - export,
  - costing/quote engine,
  - machine-specific timing;
- a timing proxy pontos alapfelteveset (pl. default cut speed / rapid speed /
  pierce time), hogy a reprodukalhatosag egyertelmu legyen.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h2_e4_t3_manufacturing_metrics_calculator.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
