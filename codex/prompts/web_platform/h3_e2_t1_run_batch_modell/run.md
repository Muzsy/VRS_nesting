# DXF Nesting Platform Codex Task - H3-E2-T1 Run batch modell
TASK_SLUG: h3_e2_t1_run_batch_modell

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h3_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_priorizalt_sprint_backlog_p0_p1_p2.md`
- `docs/web_platform/roadmap/h2_lezarasi_kriteriumok_es_h3_entry_gate.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql`
- `supabase/migrations/20260324100000_h3_e1_t1_run_strategy_profile_modellek.sql`
- `supabase/migrations/20260324110000_h3_e1_t2_scoring_profile_modellek.sql`
- `api/services/project_manufacturing_selection.py`
- `api/routes/runs.py`
- `api/main.py`
- `canvases/web_platform/h3_e2_t1_run_batch_modell.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_e2_t1_run_batch_modell.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez a task csak a batch truth-reteget es a batch item managementet vezeti be.
- Ne csussz at orchestrator, evaluation, ranking vagy comparison scope-ba.
- Ne hozz letre uj queued run-okat ebben a taskban.
- A task azzal az explicit munkafeltetelezessel keszul, hogy a
  `H3-E1-T3 – Project-level selectionok` elkeszult, meg akkor is, ha a mostani
  zipben ennek artefaktjai nem latszanak.
- A batch item strategy/scoring referencia csak binding truth legyen, ne
  indits run create workflow-t.
- A run truth mar meglevo entitas: a batch modell ezekre a runokra mutat.
- Ne talalj ki uj H3 fogalmakat a docs fole.

Implementacios elvarasok:
- Keszits uj migraciot az `app.run_batches` es `app.run_batch_items` tablakkal.
- A `run_batches` projekt alatti csoportosito entitas legyen.
- A `run_batch_items` mar meglevo run-okat kapcsoljon batch-hez.
- Keszits dedikalt `api/services/run_batches.py` service-t.
- A service legalabb ezt tudja:
  - batch create/list/get/delete
  - item attach/list/remove
- Validald a projekt owner scope-jat, a run projekt-hovatartozasat, valamint
  az opcionális strategy/scoring version owner-scope-jat.
- Keszits dedikalt `api/routes/run_batches.py` route-ot.
- Kotsd be a route-ot az `api/main.py`-ba.

A smoke script bizonyitsa legalabb:
- batch letrehozhato;
- batch listazhato/lekérdezheto;
- meglevo run batch-be teheto;
- ugyanaz a run ugyanabba a batch-be nem teheto be ketszer;
- idegen projekt runja tiltott;
- idegen owner strategy/scoring version tiltott;
- batch item torolheto;
- nincs orchestrator/evaluation/ranking side effect.

A reportban kulon nevezd meg:
- hogyan lett a `run_batches` es `run_batch_items` kulon truth-reteggé emelve;
- hogyan tarolhato a candidate cimke es a strategy/scoring kontextus;
- miert nem resze ennek a tasknak az uj run-ok inditasa;
- miert marad out-of-scope az orchestrator, evaluation es ranking.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h3_e2_t1_run_batch_modell.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
