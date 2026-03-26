# DXF Nesting Platform Codex Task - H3-E3-T3 Best-by-objective lekerdezesek
TASK_SLUG: h3_e3_t3_best_by_objective_lekerdezesek

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h3_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_priorizalt_sprint_backlog_p0_p1_p2.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql`
- `supabase/migrations/20260322030000_h2_e4_t3_manufacturing_metrics_calculator.sql`
- `supabase/migrations/20260324150000_h3_e3_t2_ranking_engine.sql`
- `api/services/run_rankings.py`
- `api/routes/run_rankings.py`
- `api/services/run_evaluations.py`
- `api/services/run_snapshot_builder.py`
- `worker/result_normalizer.py`
- `api/main.py`
- `canvases/web_platform/h3_e3_t2_ranking_engine.md`
- `canvases/web_platform/h3_e3_t3_best_by_objective_lekerdezesek.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_e3_t3_best_by_objective_lekerdezesek.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez a task read-side objective query/projection task.
- A task nem ranking engine, nem evaluation engine, nem comparison summary
  builder, nem business metrics calculator, nem selected-run workflow es nem
  remnant/inventory task.
- A H3-E3-T3 outputja itt objective-specifikus query/projection, nem uj
  persisted comparison truth tabla.
- Ne talalj ki uj `run_comparison_results`, `batch_summary_results` vagy mas,
  docsban nem letezo gyujtotablat csak azert, hogy objective-toplistat adj.
- Ne vezesd be ebben a taskban:
  - `run_business_metrics`
  - `project_selected_runs`
  - `run_reviews`
  - full comparison dashboard payload
  - ranking vagy evaluation ujraszamitas
  - remnant vagy inventory domain truthokat.

Implementacios elvarasok:
- Keszits dedikalt `api/services/run_best_by_objective.py` service-t.
- A service a mar letezo persisted truthokat olvassa:
  - `app.run_batches`
  - `app.run_batch_items`
  - `app.run_ranking_results`
  - `app.run_evaluations`
  - `app.run_metrics`
  - `app.run_manufacturing_metrics`
- A `priority-best` objectivehoz read-side modon olvashatod:
  - `app.nesting_run_snapshots`
  - `app.run_layout_unplaced`
- Ne toltsd le a nyers solver artifactokat, ha a persisted truth eleg.
- Ne triggereld automatikusan a ranking vagy evaluation calculate pathot.
- Ha a batchhez nincs persisted ranking, ne gyarts csendes fallback rankinget.

Objective-contract:
- Tamasd minimum ezeket az objective kulcsokat:
  - `material-best`
  - `time-best`
  - `priority-best`
  - `cost-best`
- `material-best` legyen valos metric-ordering, ne a `total_score` aliasa.
- `time-best` a `run_manufacturing_metrics.estimated_process_time_s` truthra
  epuljon.
- `priority-best` legyen minimalis, deterministic read-side priority
  fulfilment projection snapshot + unplaced truthbol.
- `cost-best` legyen expliciten kezelt query objective, de unsupported/allapotolt
  valasszal; ne talalj ki uzleti koltseg proxyt vagy pseudo-formulat.

Javasolt objective-ordering szabalyok:
- `material-best`:
  - `utilization_ratio` DESC
  - `used_sheet_count` ASC
  - `unplaced_count` ASC
  - `remnant_value` DESC, ha van
  - `run_ranking_results.rank_no` ASC
  - `run_id` ASC
- `time-best`:
  - `estimated_process_time_s` ASC
  - `used_sheet_count` ASC
  - `utilization_ratio` DESC
  - `run_ranking_results.rank_no` ASC
  - `run_id` ASC
- `priority-best`:
  - a snapshot `parts_manifest_jsonb` alapjan hasznald a `required_qty` es
    `placement_priority` adatokat;
  - a `run_layout_unplaced` alapjan szamold a teljesitetlen mennyiseget;
  - a sulyozas legyen explicit, pl. `priority_weight = 101 - placement_priority`;
  - a `priority_fulfilment_ratio` legyen: teljesitett sulyozott mennyiseg /
    teljes sulyozott igeny;
  - fallback:
    - magas-prioritasu hiany suly ASC
    - `run_metrics.unplaced_count` ASC
    - `run_ranking_results.rank_no` ASC
    - `run_id` ASC

Projection payload minimum:
- `objective`
- `status`
- `batch_id`
- `run_id` (ha van winner)
- `rank_no` (ha van)
- `candidate_label` (ha van)
- `objective_value`
- `objective_reason_jsonb`

Az `objective_reason_jsonb` minimum tartalma:
- `source_tables`
- `metric_snapshot`
- `ordering_trace`
- `used_fallbacks`
- `unsupported_reason` vagy `missing_sources`, ha relevans

Route kontraktus:
- Keszits dedikalt `api/routes/run_best_by_objective.py` route-ot legalabb a:
  - `GET /projects/{project_id}/run-batches/{batch_id}/best-by-objective`
  kontraktussal.
- Opcionálisan johet objective-szintu GET is.
- A route legyen read-only es objective-query domain.
- Ne adjon full comparison summaryt.
- Ne allitson selected/preferred run state-et.

A smoke script bizonyitsa legalabb:
- `material-best` sikeres;
- `time-best` sikeres;
- `priority-best` sikeres;
- `cost-best` explicit unsupported;
- ranking hianyaban nincs fallback ranking;
- idegen owner batch tiltott;
- nincs evaluation/ranking/selected-run/business write;
- a projection deterministic ugyanarra az inputra.

A reportban kulon nevezd meg:
- hogy ez a task miert read-side query/projection, es miert nem uj persisted
  comparison truth;
- mely truthokra epul az egyes objective view;
- hogyan kezeli a task a `cost-best` objective-ot a business metrics truth
  hianyaban;
- mi a `priority-best` minimalis read-side keplete;
- hogyan lesz auditálhato az `objective_reason_jsonb`;
- miert nincs ebben a taskban ranking/evaluation write vagy selected-run side
  effect.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h3_e3_t3_best_by_objective_lekerdezesek.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
