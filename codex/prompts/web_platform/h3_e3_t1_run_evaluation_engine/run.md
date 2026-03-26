# DXF Nesting Platform Codex Task - H3-E3-T1 Run evaluation engine
TASK_SLUG: h3_e3_t1_run_evaluation_engine

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
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql`
- `worker/result_normalizer.py`
- `supabase/migrations/20260322030000_h2_e4_t3_manufacturing_metrics_calculator.sql`
- `api/services/manufacturing_metrics_calculator.py`
- `supabase/migrations/20260324110000_h3_e1_t2_scoring_profile_modellek.sql`
- `api/services/scoring_profiles.py`
- `supabase/migrations/20260324120000_h3_e1_t3_project_level_selectionok.sql`
- `api/services/project_strategy_scoring_selection.py`
- `canvases/web_platform/h3_e1_t2_scoring_profile_modellek.md`
- `canvases/web_platform/h3_e1_t3_project_level_selectionok.md`
- `canvases/web_platform/h3_e2_t2_batch_run_orchestrator.md`
- `api/main.py`
- `canvases/web_platform/h3_e3_t1_run_evaluation_engine.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_e3_t1_run_evaluation_engine.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez a task csak a H3 evaluation truth-reteget vezeti be.
- A task nem ranking engine, nem batch comparison, nem best-by-objective,
  nem business metrics, nem remnant/inventory es nem review workflow.
- A H3 detailed doc minimalis outputja:
  - `run_evaluations`
- Ne talalj ki uj "decision engine" gyujtotablat vagy mas, docsban nem letezo
  domain kifejezest. A naming maradjon run evaluation nyelven.
- Ne vezesd be ebben a taskban:
  - `run_ranking_results`
  - `project_selected_runs`
  - `run_reviews`
  - comparison projection vagy batch summary projection
  - remnant domain tablakat
  - inventory-aware resolver logikat
  - H3-E5 business metric truthot.
- Ne modositd a `run_snapshot_builder`, worker futasi folyamatot, H1 projection
  normalizert vagy H2 manufacturing metrics calculator truthjat csak azert,
  hogy az evaluation "mindent tudjon". Ezek input truthok, nem ennek a tasknak
  a modositasi celpontjai.
- A H3-E3-T1 task tree dependency-jebol kovetkezik, hogy az explicit
  `scoring_profile_version_id` utvonalnak onmagaban is mukodnie kell. A
  `project_scoring_selection` fallback csak opcionalis convenience lehet, nem
  kotelezo egyetlen ut.

Implementacios elvarasok:
- Keszits uj migraciot az `app.run_evaluations` tablaval.
- A tabla legalabb a `run_id`, `scoring_profile_version_id`, `total_score`,
  `evaluation_jsonb`, `created_at` mezoket tartalmazza.
- A write modell legyen run-szintu canonical evaluation:
  - egy runhoz egy persisted evaluation sor;
  - ujraertekeles replace-eli a korabbit;
  - ne vezess be multi-profile evaluation history tablat.
- Keszits dedikalt `api/services/run_evaluations.py` service-t.
- A service legalabb ezt tudja:
  - evaluation calculate/persist explicit scoring versionnel;
  - optionalis fallback a project aktiv scoring selectionjere, ha nincs
    explicit version a kerelben;
  - persisted evaluation get;
  - optionalis evaluation delete/reset.
- Keszits dedikalt `api/routes/run_evaluations.py` route-ot legalabb a:
  - `POST /projects/{project_id}/runs/{run_id}/evaluation`
  - `GET /projects/{project_id}/runs/{run_id}/evaluation`
  - optionalisan `DELETE /projects/{project_id}/runs/{run_id}/evaluation`
  kontraktussal.
- Kotsd be a route-ot az `api/main.py`-ba.
- A route es a service maradjon tisztan evaluation-domain; ne vallaljon batch,
  ranking vagy comparison felelosseget.

Scoring formula elvarasok:
- Dokumentalt, bounded H3 minimum formula kell.
- Minimum tamogatott komponensek:
  - `utilization_weight`
  - `unplaced_penalty`
  - `sheet_count_penalty`
- Feltetelesen, csak ertelmes normalizalas es tenyleges input mellett:
  - `remnant_value_weight`
  - `process_time_penalty`
- A formula a valos persisted truthra epuljon:
  - H1 `app.run_metrics`:
    `placed_count`, `unplaced_count`, `used_sheet_count`,
    `utilization_ratio`, `remnant_value`
  - H2 `app.run_manufacturing_metrics`:
    `estimated_process_time_s`, `estimated_cut_length_mm`,
    `estimated_rapid_length_mm`, `pierce_count`
- Ne keverj nyers, skala nelkuli countokat ugy a `total_score`-ba, hogy azok
  elnyomjak a bounded komponenseket. A score legyen dokumentaltan bounded /
  normalizalt.
- `sheet_count_penalty` eseten bounded normalizalas kell; jo irany:
  `0`, ha `used_sheet_count <= 1`, kulonben `1 - (1 / used_sheet_count)`.
- `unplaced_penalty` eseten a ratio legyen:
  `unplaced_count / max(placed_count + unplaced_count, 1)`.
- `remnant_value_weight` csak akkor alkalmazhato, ha van `remnant_value` es a
  thresholdok adnak hozza normalizalasi pontot (pl. `target_remnant_value` vagy
  `max_remnant_value`).
- `process_time_penalty` csak akkor alkalmazhato, ha van
  `run_manufacturing_metrics` sor es threshold oldali normalizalasi pont
  (pl. `max_estimated_process_time_s`).
- A jelenleg nem letezo metrikahoz tartozo weights, peldaul
  `priority_fulfilment_weight` es `inventory_consumption_penalty`, ne
  produkaljanak kitalalt score-t. Ezek `evaluation_jsonb` alatt
  `unsupported` / `not_applied_yet` komponenskent jelenjenek meg
  `contribution = 0` mellett.

`evaluation_jsonb` minimum tartalma:
- `scoring_profile_snapshot`
- `input_metrics`
- `components`
  - komponensenkent `raw_value`, `normalized_value`, `weight`,
    `contribution`, `status`
- `threshold_results`
- `tie_breaker_inputs`
- `warnings` / `unsupported_components`

Threshold es tie-breaker boundary:
- A `threshold_jsonb` ismert kulcsaira boolean eredmeny keletkezzen:
  - `min_utilization`
  - `max_unplaced_ratio`
  - `max_used_sheet_count`
  - `max_estimated_process_time_s`
  - `min_remnant_value`
- A `tie_breaker_jsonb` ismert kulcsaihoz a relevans input metrikak keruljenek
  snapshotkent az evaluation JSON-ba.
- Ne keszuljon `rank_no`, batch sorrend vagy `run_ranking_results` sor.

A smoke script bizonyitsa legalabb:
- explicit scoring profile versionnel evaluation sikeresen letrehozhato;
- ugyanazon run ujraertekelese replace-eli a korabbi evaluation sort;
- azonos inputra azonos `total_score` es komponensbontas keletkezik;
- `run_metrics` hianyaban hiba jon;
- `run_manufacturing_metrics` hianyaban a H1-komponensek mukodnek, de a
  `process_time_penalty` `not_applied` / `missing_metric`;
- idegen owner scoring profile version tiltott;
- optionalis selection fallback, ha implementalod, tenylegesen mukodik;
- `priority_fulfilment_weight` es `inventory_consumption_penalty`
  unsupported allapotban, zero contributionnel jelenik meg;
- nincs `run_ranking_results`, batch vagy selection write side effect.

A reportban kulon nevezd meg:
- milyen schema-val lett bevezetve a `run_evaluations` truth;
- mely H1/H2 metric truthokra epul a score;
- hogyan lesz a score komponensenkent indokolhato;
- mely scoring kulcsok alkalmazhatok most tenyleges persisted inputra;
- mely scoring kulcsok maradnak tudatosan unsupported / not_applied allapotban;
- miert nincs ebben a taskban ranking, batch comparison vagy business metrics;
- hogyan kell ertelmezni a project-level scoring selection fallbackot ugy, hogy
  az explicit `scoring_profile_version_id` ut megmaradjon elsosegesnek.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h3_e3_t1_run_evaluation_engine.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
