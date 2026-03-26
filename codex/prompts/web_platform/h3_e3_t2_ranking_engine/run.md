# DXF Nesting Platform Codex Task - H3-E3-T2 Ranking engine
TASK_SLUG: h3_e3_t2_ranking_engine

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
- `supabase/migrations/20260324130000_h3_e2_t1_run_batch_modell.sql`
- `api/services/run_batches.py`
- `api/services/run_batch_orchestrator.py`
- `supabase/migrations/20260324140000_h3_e3_t1_run_evaluation_engine.sql`
- `api/services/run_evaluations.py`
- `api/routes/run_evaluations.py`
- `canvases/web_platform/h3_e2_t2_batch_run_orchestrator.md`
- `canvases/web_platform/h3_e3_t1_run_evaluation_engine.md`
- `api/main.py`
- `canvases/web_platform/h3_e3_t2_ranking_engine.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_e3_t2_ranking_engine.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez a task csak a H3 batch ranking truth-reteget vezeti be.
- A task nem run evaluation engine, nem batch orchestrator, nem comparison
  projection, nem best-by-objective projection, nem selected-run workflow,
  nem review workflow, nem business metrics es nem remnant/inventory task.
- A H3 detailed doc minimalis outputja:
  - `run_ranking_results`
- Ne talalj ki uj "decision bundle" vagy mas, docsban nem letezo gyujtotablat.
  A naming maradjon ranking / run_ranking_results nyelven.
- Ne vezesd be ebben a taskban:
  - `project_selected_runs`
  - `run_reviews`
  - `run_business_metrics`
  - comparison summary projection vagy batch dashboard payload
  - objective-specifikus toplistak (`material-best`, `time-best`, stb.)
  - evaluation ujraszamitas vagy batch auto-orchestration.
- Ne modositd a H1/H2 metrika truthot, a run snapshot buildert, a run create
  workflowt vagy a H3-E3-T1 evaluation formulajat csak azert, hogy a ranking
  "kenyelmesebb" legyen. Ezek input truthok, nem ennek a tasknak a celpontjai.

Implementacios elvarasok:
- Keszits uj migraciot az `app.run_ranking_results` tablaval.
- A tabla legalabb a `id`, `batch_id`, `run_id`, `rank_no`,
  `ranking_reason_jsonb`, `created_at` mezoket tartalmazza.
- Legyen egyertelmu egyediseg ugyanazon batchen belul:
  - `unique (batch_id, run_id)`
  - `unique (batch_id, rank_no)`
- A write modell legyen batch-szintu canonical ranking halmaz:
  - egy batchhez egy persisted rangsor;
  - ujrarankolas replace-eli a korabbi ranking sorokat;
  - ne vezess be ranking history tablat.
- Keszits dedikalt `api/services/run_rankings.py` service-t.
- A service legalabb ezt tudja:
  - batch ranking calculate/persist;
  - persisted ranking list read;
  - opcionálisan delete/reset, ha a route kontraktus ezt igenyli.
- Keszits dedikalt `api/routes/run_rankings.py` route-ot legalabb a:
  - `POST /projects/{project_id}/run-batches/{batch_id}/ranking`
  - `GET /projects/{project_id}/run-batches/{batch_id}/ranking`
  - opcionálisan `DELETE /projects/{project_id}/run-batches/{batch_id}/ranking`
  kontraktussal.
- Kotsd be a route-ot az `api/main.py`-ba.
- A route es a service maradjon tisztan ranking-domain; ne vallaljon
  comparison, business vagy selected-run felelosseget.

Ranking input boundary:
- A ranking kizarolag mar persisted truthra epuljon:
  - `app.run_batches`
  - `app.run_batch_items`
  - `app.run_evaluations`
- Opcionálisan olvashato a kapcsolodo `app.scoring_profile_versions`, ha a
  tie-break policy vagy indoklas ezt tenylegesen igenyli.
- A ranking ne szamoljon uj `total_score`-t.
- A ranking ne irjon `app.run_evaluations`-t.
- A ranking ne olvassa vissza a H1/H2 truthot uj scoreformula kedveert.

Konzisztencia elvarasok:
- Ha egy batch-item runjahoz nincs persisted evaluation, a ranking hibazzon.
  Ne gyartson reszleges sorrendet.
- Ha a batch-itemben van `scoring_profile_version_id`, akkor a kapcsolodo
  `run_evaluations.scoring_profile_version_id` egyezzen vele.
- Ha mismatch van, a ranking hibazzon; ne rangsoroljon csendes kevert
  allapottal.
- Ha a batch-itemben nincs scoring version, de az evaluationben van, a ranking
  mukodhet, de a `ranking_reason_jsonb` figyelmeztetesben jelezze ezt.

Determinista ranking elvarasok:
- Elsoleges rendezes: `run_evaluations.total_score` DESC.
- Azonos `total_score` eseten deterministic tie-break kell.
- Elso korben hasznald a persisted `evaluation_jsonb.tie_breaker_inputs`
  es/vagy a scoring profile version `tie_breaker_jsonb` ismert kulcsait, ha ez
  tenylegesen osszehasonlithato.
- Ha ez nem eleg a donteshez, legyen dokumentalt canonical fallback, peldaul:
  - `utilization_ratio` DESC
  - `unplaced_ratio` ASC
  - `used_sheet_count` ASC
  - `estimated_process_time_s` ASC, ha mindket candidate-nel elerheto
  - `candidate_label` ASC
  - `run_id` ASC
- Ne hasznalj implicit SQL orderre vagy instabil dict/set iteraciora epulo
  dontest.
- Ugyanarra a batch truthra a rankingnek minden futasban ugyanazt a sorrendet
  kell adnia.

`ranking_reason_jsonb` minimum tartalma:
- `total_score` snapshot
- `scoring_profile_version_id`
- `candidate_label`, ha van
- `tie_break_trace` vagy ezzel egyenerteku magyarazhato ranking-dontesi nyom
- annak jelzese, hogy profile tie-break vagy canonical fallback dontott-e
- relevans warningok
- rovid evaluation-summary referencia, ami mutatja, hogy a ranking a persisted
  evaluation truthra epult

A smoke script bizonyitsa legalabb:
- tobb evaluated batch-itembol ranking sikeresen letrehozhato;
- a `rank_no` egyedi es stabil;
- ujrarankolas replace-eli a korabbi ranking sorokat;
- azonos `total_score` eseten deterministic tie-break ervenyesul;
- hianyzo evaluation eseten hiba jon;
- batch-item scoring version es evaluation scoring version mismatch eseten hiba jon;
- idegen owner batch tiltott;
- nincs `run_evaluations` write, comparison projection vagy selected-run side effect.

A reportban kulon nevezd meg:
- milyen schema-val lett bevezetve a `run_ranking_results` truth;
- hogy a ranking mely persisted truthokra epul;
- hogy a ranking miert nem szamol uj score-t;
- milyen tie-break sorrend vagy policy ervenyesul;
- hogyan lesz a ranking reason auditálhato;
- miert nincs ebben a taskban comparison projection, best-by-objective vagy
  selected-run workflow;
- hogyan kezeli a task a hianyzo evaluation es a scoring-context mismatch esetet.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h3_e3_t2_ranking_engine.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
