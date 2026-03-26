# H3-E2-T1 Run batch modell

## Funkcio
Ez a task nyitja meg a H3 batch-vilagot.
A cel, hogy egy projekten belul tobb run-t strukturaltan egy batch-be lehessen
szervezni, es a batch-item szinten visszakeresheto legyen a candidate cimke,
a strategy/scoring kontextus, valamint a kesobbi ranking/evaluation reteghez
szukseges alapkapcsolat.

A task a H3 strategy/scoring domainre epul, es **azzal az explicit
munkafeltetelezessel** keszul, hogy a `H3-E1-T3 – Project-level selectionok`
mar elkeszult, akkor is, ha a mostani zipben annak artefaktjai meg nem latszanak.

Ez a task szandekosan nem batch orchestrator, nem evaluation engine, nem
ranking engine, es nem comparison projection. A fokusz most kizárólag a
persisted batch truth-retegen es a batch CRUD / item-management contracton van.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - `app.run_batches` tabla bevezetese;
  - `app.run_batch_items` tabla bevezetese;
  - owner/project-scope validacio a batch hozzafereshez;
  - dedikalt batch service es route a batch create/list/get/delete valamint
    item attach/list/remove muveletekhez;
  - candidate label tamogatas;
  - opcionális strategy/scoring version referencia batch-item szinten;
  - task-specifikus smoke a batch es item invariansokra.
- Nincs benne:
  - uj queued run-ok automatikus letrehozasa;
  - batch orchestrator service;
  - `run_evaluations`, `run_ranking_results`, comparison projection;
  - `project_selected_runs`, review workflow;
  - worker vagy snapshot runtime integracio.

### Talalt relevans fajlok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - itt van a H3-E2-T1 task: `run_batches`, `run_batch_items`.
- `docs/web_platform/roadmap/dxf_nesting_platform_h3_reszletes.md`
  - SQL-vazlat a `run_batches` es `run_batch_items` tablákhoz.
- `docs/web_platform/roadmap/dxf_nesting_platform_priorizalt_sprint_backlog_p0_p1_p2.md`
  - a P2-B1 szekcio megerositi, hogy ez kulon batch-model task.
- `docs/web_platform/roadmap/h2_lezarasi_kriteriumok_es_h3_entry_gate.md`
  - H2 utan a H3 batch-vonal nyithato, ha a strategy/scoring alapok megvannak.
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
  - kritikus boundary: a batch truth ne csusszon at evaluation/ranking vagy
    review flow-ba.
- `supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql`
  - minta projekt-szintu owner-validalt binding truthra.
- `supabase/migrations/20260324100000_h3_e1_t1_run_strategy_profile_modellek.sql`
  - strategy version truth, amelyre a batch item opcionálisan hivatkozhat.
- `supabase/migrations/20260324110000_h3_e1_t2_scoring_profile_modellek.sql`
  - scoring version truth, amelyre a batch item opcionálisan hivatkozhat.
- `api/services/project_manufacturing_selection.py`
  - project-owner guard minta.
- `api/routes/runs.py`
  - referencia arra, hogy a run truth mar kulon letezik; ezt a taskot nem
    szabad ujratervezni.
- `api/main.py`
  - ide kell az uj route bekotese.

### Konkret elvarasok

#### 1. Kulon batch truth kell
A task vezesse be a H3 reszletes doksiban javasolt ket tablat:
- `app.run_batches`
- `app.run_batch_items`

Minimum elvart `run_batches` mezok:
- `id`
- `project_id`
- `created_by`
- `batch_kind`
- `notes`
- `created_at`

Minimum elvart `run_batch_items` mezok:
- `batch_id`
- `run_id`
- `candidate_label`
- `strategy_profile_version_id`
- `scoring_profile_version_id`
- a PK: `(batch_id, run_id)`

#### 2. A batch-item a kesobbi rankinghez szukseges kontextust hordozza
A batch-item mar most tudja tarolni, hogy az adott run melyik strategy/scoring
kontextushoz tartozott. Ez a taskban csak persisted truth, nem score-szamitas.

Ne vezesd be meg:
- `run_evaluations`
- `run_ranking_results`
- `ranking_reason_jsonb`
- comparison view/projection

#### 3. Owner-scoped batch CRUD kell
Keszits dedikalt service-t es route-ot, peldaul:
- `api/services/run_batches.py`
- `api/routes/run_batches.py`

Minimum API-scope:
- batch create
- batch list projekten belul
- batch get
- batch delete
- batch item attach (meglevo run-hoz)
- batch item list
- batch item remove

A service validalja, hogy:
- a projekt a user owner-scope-jaban van;
- a batch a megfelelo projekthez tartozik;
- a hozzaadott run ugyanahhoz a projekthez tartozik;
- ha strategy/scoring version referencia is bekerul az itembe, az owner-scope
  szinten ervenyes legyen.

#### 4. A task ne vallaljon uj run letrehozast
Ez meg nem orchestrator.
A task nem hoz letre uj run-okat, csak mar meglevo run truth-okat tud batch-be
szervezni.

Az orchestrator a kovetkezo taskban jon.

#### 5. A candidate label legyen explicit es auditálhato
A `candidate_label` legalabb egyszeru szoveges cimke lehessen, peldaul:
- `baseline`
- `priority_first`
- `fast_turnaround`
- `balanced`

Ez most nem kotelezo enum, csak visszakeresheto persisted metadata.

#### 6. A smoke bizonyitsa a fo invariansokat
A task-specifikus smoke legalabb ezt bizonyitsa:
- batch letrehozhato;
- batch listazhato ugyanazon projektre;
- meglevo run batch-be teheto;
- ugyanaz a run ugyanabba a batch-be nem kerulhet ketszer;
- idegen projekt runja nem teheto be;
- idegen owner strategy/scoring version nem hivatkozhato;
- batch item torolheto;
- a task nem hoz letre `run_evaluations` vagy ranking side effectet.

### DoD
- [ ] Letrejott a `run_batches` truth reteg.
- [ ] Letrejott a `run_batch_items` truth reteg.
- [ ] A batch CRUD owner/project-scope validacioval mukodik.
- [ ] A batch item attach/list/remove contract mukodik.
- [ ] A batch item opcionálisan strategy/scoring kontextust tud hordozni.
- [ ] A task nem hoz letre uj queued run-okat.
- [ ] A task nem csuszik at evaluation / ranking / comparison scope-ba.
- [ ] Keszult dedikalt batch service es route.
- [ ] A route be van kotve az `api/main.py`-ba.
- [ ] Keszult task-specifikus smoke script.
- [ ] Checklist es report evidence-alapon frissitve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h3_e2_t1_run_batch_modell.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a task egybol orchestratorra vagy evaluationre csuszik;
  - a batch-item owner/project validacio gyenge marad;
  - a run truth es a batch truth keveredik;
  - a `candidate_label` enumma vagy runtime logikava valik.
- Mitigacio:
  - explicit no-orchestrator / no-evaluation / no-ranking boundary;
  - service oldali project/run/version owner-validacio;
  - a batch-item csak binding truth, nem run-create workflow.
- Rollback:
  - a migration + service + route + smoke egy task-commitban visszavonhato;
  - a H3-E1 domain es a meglevo H1/H2 run truth erintetlen marad.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h3_e2_t1_run_batch_modell.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/services/run_batches.py api/routes/run_batches.py scripts/smoke_h3_e2_t1_run_batch_modell.py`
  - `python3 scripts/smoke_h3_e2_t1_run_batch_modell.py`
