# H1-E3-T4 Project sheet input management (H1 minimum)

## Funkcio
A feladat a H1-E3 sheet workflow kovetkezo lepese: a mar letezo owner-szintu
`sheet_definition` + `sheet_revision` truth projekt-szintu felhasznalhato inputta
alakitasa a `app.project_sheet_inputs` tablavilagon keresztul.

A H0 mar letette a `app.project_sheet_inputs` schema- es RLS-alapjait, a
H1-E3-T2 pedig mar adott explicit sheet creation service-t. Ennek a tasknak a
celja ezekre epitve egy minimalis, de tenylegesen hasznalhato project-level
sheet input workflow bevezetese.

Ez a task meg mindig nem inventory/remnant logika, nem run snapshot builder, es
nem solver-input generalas. A cel kizarolag az, hogy egy projekt tulajdonosa a
sajat owner-szintu `sheet_revision` rekordjai kozul tudjon projektbe aktiv
sheet inputot rogzitani, frissiteni es listazni.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - explicit service reteg bevezetese projekt-szintu `project_sheet_inputs`
    create-or-update workflowhoz;
  - minimalis API endpoint(ok) a sheet input letrehozasra/frissitesre es
    listazasra;
  - `project_id` + `sheet_revision_id` alapu egyertelmu binding a H0 truth-ra;
  - `required_qty`, `is_active`, `is_default`, `placement_priority`, `notes`
    mezok kezelesenek H1-minimum workflowja;
  - unique `(project_id, sheet_revision_id)` helyzet kezelese ugy, hogy a task
    ne termeljen duplikalt input sort;
  - task-specifikus smoke a sikeres es hibas agakra.
- Nincs benne:
  - remnant/inventory/stock logika;
  - solver-input vagy run snapshot generalas;
  - sheet geometry import vagy nem-teglalap sheet modellek;
  - bulk/batch project sheet input import;
  - UI;
  - manufacturing sheet sourcing.

### Talalt relevans fajlok
- `supabase/migrations/20260310240000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql`
  - a `project_sheet_inputs` tabla H0 truth-ja.
- `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql`
  - projekt-owner RLS policyk a `project_sheet_inputs` tablára.
- `api/services/sheet_creation.py`
  - friss H1 minta az owner-szintu sheet revision workflowra.
- `api/routes/sheets.py`
  - friss H1 minta minimalis sheet-domain endpoint strukturara.
- `api/routes/projects.py`
  - projekt-szintu endpoint mintakhoz relevans.
- `api/main.py`
  - uj sheet-input router ide kotheto be.
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
  - H1-ben a project requirements es sheet inputs a kovetkezo reteg.
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - H1-E3-T4 task source-of-truth.

### Konkret elvarasok

#### 1. A workflow a H0 truth-ra uljon, ne legacy phase modellekre
A task kizarolag ezekre a mar letezo tablákra epuljon:
- `app.projects`
- `app.sheet_definitions`
- `app.sheet_revisions`
- `app.project_sheet_inputs`

Ne keruljon elo semmilyen regi `phase1_*` vagy ad hoc sheet-input tarolas.

#### 2. A project sheet input mindig projekt + sheet revision binding legyen
A minimum elvart request kontraktus H1-ben:
- `sheet_revision_id`
- `required_qty`
- opcionálisan `is_active`, `is_default`, `placement_priority`, `notes`

A service ellenorizze, hogy:
- a projekt a jelenlegi user tulajdona;
- a `sheet_revision_id` a jelenlegi user altal birtokolt sheet definitionhoz
  tartozik;
- a `required_qty` pozitiv;
- a `placement_priority` a schema-hataron belul marad.

#### 3. Create-or-update viselkedes ugyanarra a projektre es revisionre
A H0 schema `(project_id, sheet_revision_id)` unique constraintet hasznal.
A task H1 minimum viselkedese legyen egyertelmu:
- ha az adott projektben az adott `sheet_revision_id` meg nem szerepel, jojjon
  letre uj `project_sheet_input` rekord;
- ha mar szerepel, akkor ne duplikaljon, hanem frissitse a meglevo rekordot a
  megadott input mezokkel;
- a response adja vissza, hogy uj rekord jott letre vagy meglevo lett frissitve.

#### 4. `is_default` kezeles legyen kontrollalt projekt-szinten
Ha a felhasznalo egy adott projektben egy sheet inputot `is_default = true`
allapottal rogzit, a service gondoskodjon arrol, hogy ugyanabban a projektben a
masik sheet input rekord(ok) `is_default` mezoje false-ra alljon.

Nem kell ebbol bonyolult policy-rendszert csinalni, de ne maradjon ugyanabban a
projektben tobb default sheet input veletlenul.

#### 5. Minimalis API contract es listazas
Keszits legalabb ezt a minimum backend contractot:
- projekt-szintu create-or-update endpoint
- projekt-szintu listazo endpoint

Javasolt response create/update utan:
- `project_sheet_input_id`
- `project_id`
- `sheet_revision_id`
- `required_qty`
- `is_active`
- `is_default`
- `placement_priority`
- `notes`
- `was_existing_input`

Listazasnal minimum latszodjon:
- input id
- sheet_revision_id
- required_qty
- is_active
- is_default
- placement_priority
- opcionálisan a kapcsolodo sheet code/name/revision_no, ha a service ezt
  egyszeruen es tisztan vissza tudja adni.

#### 6. A task ne csusszon at run-builder vagy inventory scope-ba
A task ne generaljon solver snapshotot, ne szamoljon remnantot, ne csinaljon
availability aggregationt. A feladata csak a projekt-level input truth
rogzitese.

#### 7. A smoke script bizonyitsa a fo agakat
Legyen task-specifikus smoke, amely legalabb ezt bizonyitja:
- uj project + sheet revision kombinaciora uj `project_sheet_input` jon letre;
- ugyanarra a kombinaciora a kovetkezo hivas frissiti a rekordot, nem duplikal;
- `is_default = true` esetben ugyanabban a projektben a tobbi input defaultja
  lekapcsolodik;
- hiba jon idegen projektre;
- hiba jon idegen/nem lathato `sheet_revision_id` eseten;
- hiba jon ervenytelen `required_qty` / `placement_priority` eseten.

### DoD
- [ ] Keszul explicit project sheet input service a meglévo H0 truth fole.
- [ ] A task a meglévo `app.project_sheet_inputs` tablára epul, nem legacy schema-ra.
- [ ] A service csak a user sajat projektjebe es sajat sheet revisionjaira enged rogziteni.
- [ ] Uj `(project_id, sheet_revision_id)` parra uj `project_sheet_input` jon letre.
- [ ] Meglevo `(project_id, sheet_revision_id)` par eseten frissites tortenik, nem duplikalas.
- [ ] A `required_qty`, `is_active`, `is_default`, `placement_priority`, `notes` H1 minimum szinten kezelheto.
- [ ] Egy projektben az `is_default` kezeles kontrollalt, nem marad tobb default rekord.
- [ ] Keszul minimalis API endpoint a create-or-update workflowhoz.
- [ ] Keszul minimalis listazo endpoint projekt sheet inputokhoz.
- [ ] Keszul task-specifikus smoke script a sikeres es hibas agakra.
- [ ] A checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h1_e3_t4_project_sheet_input_management_h1_minimum.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a task atcsuszik run snapshot vagy inventory scope-ba;
  - a service duplikalt `(project_id, sheet_revision_id)` rekordokat termel;
  - az `is_default` projekt-szinten inkonzisztens marad;
  - idegen projekthez vagy idegen sheet revisionhoz is enged bindinget.
- Mitigacio:
  - maradj szigoruan `project_sheet_inputs` scope-ban;
  - hasznald a H0 unique truth-ot, es kezeld create-or-update modon;
  - a default-kezeles legyen explicit projekt-szintu update;
  - project-owner es sheet-owner ellenorzes legyen service- es endpoint-szinten is.
- Rollback:
  - service/route/smoke valtozasok egy task-commitban visszavonhatok;
  - ha plusz schema-kiegeszites kellene, az csak kulon migraciaban tortenjen.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h1_e3_t4_project_sheet_input_management_h1_minimum.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/services/project_sheet_inputs.py api/routes/project_sheet_inputs.py api/main.py scripts/smoke_h1_e3_t4_project_sheet_input_management_h1_minimum.py`
  - `python3 scripts/smoke_h1_e3_t4_project_sheet_input_management_h1_minimum.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `supabase/migrations/20260310240000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql`
- `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql`
- `api/services/sheet_creation.py`
- `api/routes/sheets.py`
- `api/routes/projects.py`
- `api/main.py`
