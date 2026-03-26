# H3-E1-T3 Project-level selectionok

## Funkcio
A feladat a H3 strategy/scoring domain harmadik, projekt-szintu lepese.
A cel, hogy egy projekt kulon persisted truth-retegben rogzitve tudja,
hogy melyik run strategy profile version es melyik scoring profile version az
aktiv preferenciaja.

A jelenlegi repoban mar megvan:
- a H1 stabil project/run/snapshot gerinc;
- a H2 manufacturing es postprocess foag, lezart H2-vel;
- a H3-E1-T1 run strategy profile domain;
- a H3-E1-T2 scoring profile domain.

Ez a task ezekre epulve a projekt-szintu kivalasztasi truth-ot szallitja le.
A hangsuly most nem a runtime alkalmazason, hanem azon van, hogy a projekthez
kulon, auditálhato, owner-validalt preferencia tudjon tartozni mindket
H3-E1 domainhez.

Ez a task szandekosan nem evaluation engine, nem ranking engine, nem batch
orchestrator, nem run snapshot bovitese, es nem frontend settings task. A scope
szigoruan a projekt -> aktiv strategy/scoring version binding persisted truth-ja,
minimalis service/route contracttal es ellenorizheto smoke-kal.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - `app.project_run_strategy_selection` tabla;
  - `app.project_scoring_selection` tabla;
  - project owner scope-alapu create-or-replace selection workflow mindket
    selection truthhoz;
  - explicit GET / PUT / DELETE backend contract mindket selectionhoz;
  - annak validalasa, hogy a projekt ownerje csak a sajat strategy/scoring
    profile versionjeit valaszthassa;
  - aktivitas/allapot ellenorzes ott, ahol a H3-E1-T1/T2 valos schema ezt
    tenylegesen tamogatja;
  - task-specifikus smoke a sikeres es hibas agakra.
- Nincs benne:
  - H3-E1-T1 strategy profile CRUD ujranyitasa;
  - H3-E1-T2 scoring profile CRUD ujranyitasa;
  - run snapshot builder vagy run create flow bekotese;
  - `run_batches`, `run_batch_items`, evaluation, ranking vagy best-by-objective;
  - remnant/inventory domain;
  - frontend preference UI.

### Talalt relevans fajlok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - source-of-truth task tree; a H3-E1-T3 outputjai:
    `project_run_strategy_selection`, `project_scoring_selection`.
- `docs/web_platform/roadmap/dxf_nesting_platform_h3_reszletes.md`
  - a H3 detailed doc SQL-vazlata a ket selection tablaval.
- `docs/web_platform/roadmap/dxf_nesting_platform_master_roadmap_h0_h3.md`
  - megerositi a project-level strategy/scoring selection szerepet.
- `docs/web_platform/roadmap/h2_lezarasi_kriteriumok_es_h3_entry_gate.md`
  - H2 utan a H3 strategy/scoring vilag kulon domainkent indul.
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
  - kritikus boundary: a decision layer ne csusszon at manufacturing,
    preview vagy export scope-ba.
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
  - fontos boundary: a selection persisted truth legyen, de a snapshot/runtime
    alkalmazas nem ennek a tasknak a scope-ja.
- `supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql`
  - minta projekt-szintu selection truthra es create-or-replace viselkedesre.
- `supabase/migrations/20260324100000_h3_e1_t1_run_strategy_profile_modellek.sql`
  - a strategy domain truth, amelyre a project selection mutatni fog.
- `supabase/migrations/20260324110000_h3_e1_t2_scoring_profile_modellek.sql`
  - a scoring domain truth, amelyre a project selection mutatni fog.
- `api/services/project_manufacturing_selection.py`
  - minta project owner + selected version owner validaciora.
- `api/services/run_strategy_profiles.py`
  - a strategy version domain aktualis truth-ja.
- `api/services/scoring_profiles.py`
  - a scoring version domain aktualis truth-ja.
- `api/main.py`
  - ide kell majd az uj route bekotese.

### Konkret elvarasok

#### 1. Kulon project-level selection truth kell mindket H3-E1 domainhez
A task vezesse be a H3 detailed docban javasolt ket selection tablat:
- `app.project_run_strategy_selection`
- `app.project_scoring_selection`

Minimum elvart mezo-struktura:
- `project_id`
- `active_*_profile_version_id`
- `selected_at`

A selection viselkedese projekt-szinten create-or-replace legyen:
- ha nincs rekord, uj jon letre;
- ha mar van, ugyanarra a projektre frissul/cserelodik;
- ne jojjon letre tobb aktiv selection ugyanarra a projektre.

#### 2. A service validalja a projekt tulajdonjat es a selected version owner-scope-jat
Minimum ellenorzesek:
- a projekt a jelenlegi user tulajdona;
- a kivalasztott strategy/scoring profile version a jelenlegi owner scope-jaban van;
- ha a valos strategy/scoring schema tartalmaz `is_active` vagy `lifecycle`
  jelet, csak ervenyesen valaszthato rekord fogadhato el;
- idegen owner projektje vagy idegen owner versionje ne legyen allithato,
  olvashato vagy torolheto.

Ne talalj ki uj ownership modellt. A validacio a mar meglevo H3-E1-T1/T2 truth-ra
es a `projects` owner-scope-jara epuljon.

#### 3. A task maradjon selection, ne runtime integracio
A task ne modositja:
- `run_snapshot_builder`;
- `run_create` / `runs` flow;
- worker vagy batch orchestration;
- evaluation / ranking logika.

A selection itt csak projekt-truth, amit a kesobbi H3 taskok fognak runokhoz,
batch-ekhez vagy evaluationhoz kapcsolni.

#### 4. Minimalis API contract kell mindket selectionhoz
Keszits legalabb ezt a minimum backend contractot:
- `PUT /projects/{project_id}/run-strategy-selection`
- `GET /projects/{project_id}/run-strategy-selection`
- `DELETE /projects/{project_id}/run-strategy-selection`
- `PUT /projects/{project_id}/scoring-selection`
- `GET /projects/{project_id}/scoring-selection`
- `DELETE /projects/{project_id}/scoring-selection`

A request a megfelelo aktiv version id-t vigye.
A response legyen tiszta es auditálhato, de ne vallaljon snapshot vagy
comparison scope-ot.

#### 5. A task ne csusszon at batch/evaluation/ranking iranyba
Ez a task meg nem:
- `run_batches` / `run_batch_items`;
- `run_evaluations`;
- `run_ranking_results`;
- `best-by-objective` vagy comparison projection;
- preferred run / approval workflow.

A H3-E1-T3 csak azt szallitja le, hogy a projektnek legyen persisted strategy es
scoring preferencia truth-ja.

#### 6. A smoke script bizonyitsa a fo agakat
A task-specifikus smoke legalabb ezt bizonyitsa:
- uj projektre strategy selection rogzithetö;
- meglevo strategy selection felulirhato ugyanarra a projektre;
- strategy GET visszaadja a selectiont;
- strategy DELETE torli a selectiont;
- ugyanez scoring selectionnel is mukodik;
- hiba jon idegen projektre;
- hiba jon idegen / nem lathato strategy version eseten;
- hiba jon idegen / nem lathato scoring version eseten;
- ha a valos schema tamogatja, inaktiv version tiltott;
- a task nem hoz letre `run_batches`, `run_evaluations`, ranking vagy snapshot
  side effectet.

### DoD
- [ ] Letezik kulon `app.project_run_strategy_selection` persisted truth reteg.
- [ ] Letezik kulon `app.project_scoring_selection` persisted truth reteg.
- [ ] Egy projektnek legfeljebb egy aktiv strategy selectionje van.
- [ ] Egy projektnek legfeljebb egy aktiv scoring selectionje van.
- [ ] A selection project owner scope-ban hozhato letre, modositato, olvashato es torolheto.
- [ ] A selection csak a userhez tartozo ervenyes strategy/scoring profile versionre mutathat.
- [ ] A task nem nyitja ujra a strategy vagy scoring profile CRUD scope-ot.
- [ ] A task nem nyul a snapshot / batch / evaluation / ranking retegekhez.
- [ ] Keszul minimalis GET / PUT / DELETE backend contract mindket selectionhoz.
- [ ] Keszul task-specifikus smoke script a sikeres es hibas agakra.
- [ ] Checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h3_e1_t3_project_level_selectionok.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a task belecsuszik a run snapshot vagy batch runtime integracioba;
  - a strategy/scoring domain CRUD-jat indokolatlanul ujranyitja;
  - a selection route idegen owner verziot is enged projecthez kotni;
  - a selection tablakat tul bonyolult, docs-folotti schema-feltalalassal terheli;
  - a task evaluation/ranking side effectet vallal.
- Mitigacio:
  - maradj szigoruan project-level selection scope-ban;
  - a selection tabla legyen project-id alapu egyedi truth;
  - a validacio a mar meglevo T1/T2 truthra es H2 selection mintara epuljon;
  - snapshot es batch/evaluation retegek erintetlenek maradjanak.
- Rollback:
  - a migration + service + route + smoke valtozasok egy task-commitban
    visszavonhatok;
  - a H3-E1-T1/T2 domain truth erintetlen marad, mert ez a task csak uj,
    rajuk mutato project-level binding reteget vezet be.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h3_e1_t3_project_level_selectionok.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/services/project_strategy_scoring_selection.py api/routes/project_strategy_scoring_selection.py api/main.py scripts/smoke_h3_e1_t3_project_level_selectionok.py`
  - `python3 scripts/smoke_h3_e1_t3_project_level_selectionok.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
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
