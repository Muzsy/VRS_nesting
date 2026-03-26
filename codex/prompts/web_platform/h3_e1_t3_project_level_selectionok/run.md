# DXF Nesting Platform Codex Task - H3-E1-T3 Project-level selectionok
TASK_SLUG: h3_e1_t3_project_level_selectionok

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h3_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_master_roadmap_h0_h3.md`
- `docs/web_platform/roadmap/h2_lezarasi_kriteriumok_es_h3_entry_gate.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql`
- `supabase/migrations/20260324100000_h3_e1_t1_run_strategy_profile_modellek.sql`
- `supabase/migrations/20260324110000_h3_e1_t2_scoring_profile_modellek.sql`
- `api/services/project_manufacturing_selection.py`
- `api/services/run_strategy_profiles.py`
- `api/services/scoring_profiles.py`
- `api/main.py`
- `canvases/web_platform/h3_e1_t3_project_level_selectionok.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_e1_t3_project_level_selectionok.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez a task csak a project-level strategy/scoring selection truthot vezeti be.
- A task nem strategy profile CRUD, nem scoring profile CRUD, nem snapshot task,
  nem batch/orchestrator, nem evaluation engine, nem ranking, es nem frontend
  preference UI.
- A selection truth a H3 detailed doc minimalis SQL-vazlatahoz igazodjon:
  - `project_run_strategy_selection`
  - `project_scoring_selection`
- Ne talalj ki uj generic "decision engine" vagy mas, docsban nem letezo
  gyujtofogalmat. A naming maradjon strategy/scoring selection nyelven.
- Ne vezesd be ebben a taskban:
  - `run_batches`
  - `run_batch_items`
  - `run_evaluations`
  - `run_ranking_results`
  - `best-by-objective` projectiont
  - `preferred_run` / approval workflow logikat.
- Ne modositd a `run_snapshot_builder`, `run_create`, `runs` vagy worker fo
  folyamatot csak azert, hogy a selection runtime mar most ervenyesuljon.
- A H3-E1 task tree rovid DoD-jet ugy ertelmezd, hogy a projekt mar tudjon
  persisted strategy/scoring preferenciat kezelni, de ezek runokhoz vagy
  batch-ekhez valo tenyleges alkalmazasa kesobbi H3 taskokban jon.

Implementacios elvarasok:
- Keszits uj migraciot az `app.project_run_strategy_selection` es
  `app.project_scoring_selection` tablakkal.
- A selection viselkedese legyen projekt-szintu create-or-replace.
- Validald:
  - a projekt owner scope-jat,
  - a selected strategy/scoring version owner scope-jat,
  - ahol a valos T1/T2 schema lehetove teszi, az aktiv / ervenyes allapotot.
- Keszits dedikalt `api/services/project_strategy_scoring_selection.py`
  service-t.
- A service legalabb ezt tudja:
  - strategy selection set/get/delete
  - scoring selection set/get/delete
- Keszits dedikalt `api/routes/project_strategy_scoring_selection.py`
  route-ot a hat endpointtal.
- Kotsd be a route-ot az `api/main.py`-ba.
- A route es a service maradjon tisztan selection-domain; ne vegyen at
  snapshot, batch vagy evaluation felelosseget.

A smoke script bizonyitsa legalabb:
- strategy selection letrehozhato, felulirhato, visszaolvashato, torolheto;
- scoring selection letrehozhato, felulirhato, visszaolvashato, torolheto;
- idegen owner projektje tiltott;
- idegen owner strategy/scoring versionje tiltott;
- ahol a valos schema tamogatja, inaktiv version tiltott;
- nincs `run_batches`, `run_evaluations`, ranking vagy snapshot write side effect.

A reportban kulon nevezd meg:
- hogyan lett a project-level strategy/scoring selection kulon truth reteggé emelve;
- hogyan epul a H3-E1-T1/T2 domain truthra;
- miert marad out-of-scope ebben a taskban:
  - run snapshot binding,
  - batch run world,
  - evaluation/ranking,
  - review/approval workflow;
- hogyan kell ertelmezni a H3-E1 rovid DoD-jet ugy, hogy a selection persisted
  truth mar meglehessen, de a runtime decision pipeline meg ne legyen osszekeverve
  ezzel a taskkal.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h3_e1_t3_project_level_selectionok.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
