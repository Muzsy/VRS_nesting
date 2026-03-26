# DXF Nesting Platform Codex Task - H3-E2-T2 Batch run orchestrator
TASK_SLUG: h3_e2_t2_batch_run_orchestrator

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h3_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_priorizalt_sprint_backlog_p0_p1_p2.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `canvases/web_platform/h1_e4_t2_run_create_api_service_h1_minimum.md`
- `api/services/run_creation.py`
- `api/routes/runs.py`
- `api/services/run_batches.py`
- `api/routes/run_batches.py`
- `api/main.py`
- `canvases/web_platform/h3_e2_t2_batch_run_orchestrator.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_e2_t2_batch_run_orchestrator.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez a task batch orchestrator task, nem evaluation engine, nem ranking,
  nem comparison projection es nem review workflow.
- Az orchestrator a canonical H1-E4-T2 run create flow-ra epuljon. Ne keruld
  meg a `api/services/run_creation.py` szolgaltatast sajat inline
  `nesting_runs`/`run_queue` insert logikaval.
- A task azzal az explicit munkafeltetelezessel keszul, hogy a
  `H3-E1-T3 – Project-level selectionok` elkeszult, meg akkor is, ha a mostani
  zipben ennek artefaktjai nem latszanak.
- A H3-E2-T1 batch truth legyen a binding source-of-truth. A keletkezo runok
  batch-itemkent legyenek visszakotve.
- Ne vezesd be ebben a taskban:
  - `run_evaluations`
  - `run_ranking_results`
  - comparison queryket
  - selected/preferred run workflow-t
  - worker scheduling redesign-t.

Implementacios elvarasok:
- Keszits dedikalt `api/services/run_batch_orchestrator.py` service-t.
- A service explicit candidate listabol dolgozzon.
- Minden candidate minimum tudjon hordozni:
  - `candidate_label`
  - `strategy_profile_version_id`
  - `scoring_profile_version_id`
  - opcionálisan `run_purpose`/`idempotency_key`, ha ez tisztan osszefesulheto
    a canonical run create contracttal.
- A service hozzon letre batch-et (vagy hasznaljon mar meglevo batch-et, ha a
  vegleges contract ezt mondja ki), majd candidate-enkent queued run-t,
  es azonnal kotse vissza batch-itemkent.
- Dokumentald explicit modon a hiba-szemantikat. Alapertelmezett jo irany:
  fail-fast, hogy a batch truth ne maradjon felemás candidate-allapotban.
- A `api/routes/run_batches.py` route kapjon orchestrator endpointet.

A smoke script bizonyitsa legalabb:
- tobb candidate-del batch orchestrator sikeresen fut;
- minden candidate-hez queued run keletkezik;
- a runok batch-itemkent visszakotodnek;
- a `candidate_label` es strategy/scoring kontextus tarolodik;
- idegen owner strategy/scoring version tiltott;
- a dokumentalt fail-fast (vagy explicit modon valasztott) szemantika ervenyesul;
- nincs evaluation/ranking side effect.

A reportban kulon nevezd meg:
- hogyan reuse-olja az orchestrator a H1-E4-T2 canonical run create-ot;
- hogyan kapcsolja vissza a queued run-okat batch-itemkent;
- milyen hiba-szemantikaval dolgozik;
- miert marad out-of-scope az evaluation/ranking/comparison/review.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h3_e2_t2_batch_run_orchestrator.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
