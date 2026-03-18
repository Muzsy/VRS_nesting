# H1-E3-T3 Project requirement management (H1 minimum)

## Funkcio
A feladat a H1-E3 part workflow kovetkezo lepese: a mar letezo owner-szintu
`part_definition` + `part_revision` truth projekt-szintu igenykezelese a
`app.project_part_requirements` tablavilagon keresztul.

A H0 mar letette a `app.project_part_requirements` schema- es RLS-alapjait, a
H1-E3-T1 pedig mar adott explicit part creation service-t. Ennek a tasknak a
celja ezekre epitve egy minimalis, de tenylegesen hasznalhato project-level
part requirement workflow bevezetese.

Ez a task meg mindig nem run snapshot builder, nem solver-input generalas es
nem UI. A cel kizarolag az, hogy egy projekt tulajdonosa a sajat owner-szintu
`part_revision` rekordjai kozul tudjon projektbe aktiv igenyt rogzitani,
frissiteni es listazni.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - explicit service reteg bevezetese projekt-szintu `project_part_requirements`
    create-or-update workflowhoz;
  - minimalis API endpoint(ok) a requirement letrehozasra/frissitesre es
    listazasra;
  - `project_id` + `part_revision_id` alapu egyertelmu binding a H0 truth-ra;
  - `required_qty`, `placement_priority`, `placement_policy`, `is_active`,
    `notes` mezok kezelesenek H1-minimum workflowja;
  - unique `(project_id, part_revision_id)` helyzet kezelese ugy, hogy a task
    ne termeljen duplikalt requirement sort;
  - task-specifikus smoke a sikeres es hibas agakra.
- Nincs benne:
  - run snapshot vagy solver payload generalas;
  - demand aggregation vagy bulk import;
  - sheet input workflow;
  - inventory/remnant/manufacturing scope;
  - UI vagy frontend allapotkezeles.

### Talalt relevans fajlok
- `supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql`
  - a `project_part_requirements` tabla H0 truth-ja.
- `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql`
  - projekt-owner RLS policyk a `project_part_requirements` tablára.
- `api/services/part_creation.py`
  - friss H1 minta az owner-szintu part revision workflowra.
- `api/routes/parts.py`
  - friss H1 minta minimalis part-domain endpoint strukturara.
- `api/main.py`
  - uj requirement router ide kotheto be.
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
  - H1-ben a project requirements es sheet inputs a kovetkezo reteg.
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - H1-E3-T3 task source-of-truth.

### Konkret elvarasok

#### 1. A workflow a H0 truth-ra uljon, ne legacy phase modellekre
A task kizarolag ezekre a mar letezo tablákra epuljon:
- `app.projects`
- `app.part_definitions`
- `app.part_revisions`
- `app.project_part_requirements`

Ne keruljon elo semmilyen regi `phase1_*` vagy ad hoc requirement tarolas.

#### 2. A project requirement mindig projekt + part revision binding legyen
A minimum elvart request kontraktus H1-ben:
- `part_revision_id`
- `required_qty`
- opcionálisan `placement_priority`, `placement_policy`, `is_active`, `notes`

A service ellenorizze, hogy:
- a projekt a jelenlegi user tulajdona;
- a `part_revision_id` a jelenlegi user altal birtokolt `part_definition`-hoz
  tartozik;
- a `required_qty` pozitiv;
- a `placement_priority` a schema-hataron belul marad;
- a `placement_policy` csak a meglevo enum truth elfogadott erteke legyen.

#### 3. Create-or-update viselkedes ugyanarra a projektre es revisionre
A H0 schema `(project_id, part_revision_id)` unique constraintet hasznal.
A task H1 minimum viselkedese legyen egyertelmu:
- ha az adott projektben az adott `part_revision_id` meg nem szerepel, jojjon
  letre uj `project_part_requirement` rekord;
- ha mar szerepel, akkor ne duplikaljon, hanem frissitse a meglevo rekordot a
  megadott input mezokkel;
- a response adja vissza, hogy uj rekord jott letre vagy meglevo lett frissitve.

#### 4. Minimalis API contract es listazas
Keszits legalabb ezt a minimum backend contractot:
- projekt-szintu create-or-update endpoint
- projekt-szintu listazo endpoint

Javasolt response create/update utan:
- `project_part_requirement_id`
- `project_id`
- `part_revision_id`
- `required_qty`
- `placement_priority`
- `placement_policy`
- `is_active`
- `notes`
- `was_existing_requirement`

Listazasnal minimum latszodjon:
- requirement id
- part_revision_id
- required_qty
- placement_priority
- placement_policy
- is_active
- opcionálisan a kapcsolodo part code/name/revision_no, ha a service ezt
  egyszeruen es tisztan vissza tudja adni.

#### 5. A task ne csusszon at run-builder scope-ba
A task ne generaljon solver snapshotot, ne valasszon derivative-et es ne szamoljon
aggregate solver-inputot. A feladata csak a projekt-level requirement truth
rogzitese.

#### 6. A smoke script bizonyitsa a fo agakat
Legyen task-specifikus smoke, amely legalabb ezt bizonyitja:
- uj project + part revision kombinaciora uj `project_part_requirement` jon letre;
- ugyanarra a kombinaciora a kovetkezo hivas frissiti a rekordot, nem duplikal;
- hiba jon idegen projektre;
- hiba jon idegen/nem lathato `part_revision_id` eseten;
- hiba jon ervenytelen `required_qty` / `placement_priority` / `placement_policy`
  eseten.

### DoD
- [ ] Keszul explicit project part requirement service a meglévo H0 truth fole.
- [ ] A task a meglévo `app.project_part_requirements` tablára epul, nem legacy schema-ra.
- [ ] A service csak a user sajat projektjebe es sajat part revisionjaira enged rogziteni.
- [ ] Uj `(project_id, part_revision_id)` parra uj `project_part_requirement` jon letre.
- [ ] Meglevo `(project_id, part_revision_id)` par eseten frissites tortenik, nem duplikalas.
- [ ] A `required_qty`, `placement_priority`, `placement_policy`, `is_active`, `notes` H1 minimum szinten kezelheto.
- [ ] Keszul minimalis API endpoint a create-or-update workflowhoz.
- [ ] Keszul minimalis listazo endpoint projekt requirementekhez.
- [ ] Keszul task-specifikus smoke script a sikeres es hibas agakra.
- [ ] A checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h1_e3_t3_project_requirement_management_h1_minimum.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a task atcsuszik run snapshot vagy solver-input scope-ba;
  - a service duplikalt `(project_id, part_revision_id)` rekordokat termel;
  - idegen projekthez vagy idegen part revisionhoz is enged bindinget;
  - a `placement_policy` input nem a schema truth-hoz igazodik.
- Mitigacio:
  - maradj szigoruan `project_part_requirements` scope-ban;
  - hasznald a H0 unique truth-ot, es kezeld create-or-update modon;
  - project-owner es part-owner ellenorzes legyen service- es endpoint-szinten is;
  - `placement_policy` csak a valos enum truth-bol legyen feloldva.
- Rollback:
  - service/route/smoke valtozasok egy task-commitban visszavonhatok;
  - ha plusz schema-kiegeszites kellene, az csak kulon migraciaban tortenjen.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h1_e3_t3_project_requirement_management_h1_minimum.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/services/project_part_requirements.py api/routes/project_part_requirements.py api/main.py scripts/smoke_h1_e3_t3_project_requirement_management_h1_minimum.py`
  - `python3 scripts/smoke_h1_e3_t3_project_requirement_management_h1_minimum.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql`
- `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql`
- `api/services/part_creation.py`
- `api/routes/parts.py`
- `api/main.py`
