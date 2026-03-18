# H1-E3-T2 Sheet creation service (H1 minimum)

## Funkcio
A feladat a H1-E3 part/sheet workflow kovetkezo minimum lepese: owner-szintu
`shet_definition` + `sheet_revision` letrehozasa olyan formaban, hogy a kesobbi
`project_sheet_inputs` workflow mar stabil, valaszthato sheet truth-ra tudjon
raepulni.

A H0 mar letette a `app.sheet_definitions`, `app.sheet_revisions` es
`app.project_sheet_inputs` schema alapokat, valamint az ezekhez tartozo RLS
politikakat. A H1-E3-T2 celja ezekre epitve egy explicit backend service es
minimalis API endpoint bevezetese, amely a felhasznalo sajat owner scope-jaban
uj lemezdefiniciot vagy uj lemezreviziot tud letrehozni.

Ez a task meg mindig nem project sheet input management, nem run snapshot
builder, es nem manufacturing inventory. A cel kizarolag az, hogy a platformban
legyen tenyleges, hasznalhato sheet-domain truth, amire a H1-E3-T4 mar ra tud
kotni.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - explicit sheet creation service bevezetese owner-szintu `sheet_definition`
    + `sheet_revision` letrehozashoz;
  - minimalis API endpoint a sheet revision letrehozasara;
  - uj es meglevo `sheet_definition` ag kezelese `code` alapjan;
  - `current_revision_id` korrekt frissitese uj vagy meglevo definition eseten;
  - H1-minimum teglalap alapu lemezmodell (`width_mm`, `height_mm`, opcionális
    `grain_direction`);
  - task-specifikus smoke a sikeres es hibas agakra.
- Nincs benne:
  - `project_sheet_inputs` letrehozas vagy szerkesztes;
  - maradeklap / inventory / remnant logika;
  - nem-teglalap vagy geometry-alapu sheet import;
  - manufacturing sheet profilok;
  - run snapshot builder vagy solver input generalas;
  - UI.

### Talalt relevans fajlok
- `supabase/migrations/20260311000000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql`
  - a `sheet_definitions` / `sheet_revisions` / `project_sheet_inputs` H0 truth-ja.
- `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql`
  - owner-szintu RLS alapok a sheet tablakhoz.
- `api/services/part_creation.py`
  - friss H1 minta uj/meglevo definition + revision workflowra.
- `api/routes/parts.py`
  - friss H1 minta minimalis domain endpoint strukturara.
- `api/main.py`
  - uj `sheets` router ide kotheto be.
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
  - a H1 reszletes terv szerint a kovetkezo lepes a sheet creation service.
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - H1-E3-T2 task source-of-truth.

### Konkret elvarasok

#### 1. H1-minimum sheet truth: teglalap alap
A service H1-ben meg ne akarjon geometry pipeline-rol vagy DXF importrol
lemezprofilt kepezni. A minimum elvart request kontraktus:
- `code`
- `name`
- `width_mm`
- `height_mm`
- opcionálisan `description`, `grain_direction`, `notes`, `source_label`

A lemez truth most owner-szintu definicio + revision maradjon, tisztan numerikus
meretekkel. `width_mm` es `height_mm` legyen pozitiv, a grain direction pedig
legfeljebb normalizalt text mezokent menjen at.

#### 2. Uj es meglevo definition ag
A minimum viselkedes:
- ha az adott ownernel a `code` meg nem letezik, jojjon letre uj
  `sheet_definition`, majd `revision_no = 1`-gyel uj `sheet_revision`;
- ha a `code` mar letezik ugyanannal az ownernel, akkor a meglevo definition ala
  jojjon uj revision a kovetkezo `revision_no`-val;
- sikeres letrehozas utan a `sheet_definitions.current_revision_id` az uj
  revisionre mutasson.

A task ne torjon el a H0-ban mar vedett `current_revision_id` integritason.

#### 3. A service ne csusszon at project input scope-ba
A H0 schema mar tartalmazza a `project_sheet_inputs` tablát, de ezt a taskot
kifejezetten ne nyisd meg idovel elott. Ne jojjon letre automatikus projekt-
hozzarendeles, ne legyen `project_id` a sheet create endpoint requestjeben.
A letrejovo sheet revision kesobb valaszthato legyen projektben, de maga a
projekthez rendeles majd a H1-E3-T4 feladata.

#### 4. Minimalis API contract
Keszits legalabb egy backend endpointot, peldaul owner-szintu route alatt,
amelybol a sheet revision letrehozhato.

Javasolt H1-minimum request contract:
- `code`
- `name`
- `width_mm`
- `height_mm`
- opcionálisan `description`, `grain_direction`, `notes`, `source_label`

A response adja vissza legalabb:
- `sheet_definition_id`
- `sheet_revision_id`
- `revision_no`
- `lifecycle`
- `current_revision_id`
- `width_mm`
- `height_mm`
- `grain_direction`
- `was_existing_definition`

#### 5. Forrasintegritas es owner scope
Legyen bizonyithato, hogy:
- a `sheet_definition` ownerhez kotott;
- ugyanazon owner + `code` alatt nem jon letre duplikalt definition;
- meglevo definition eseten a kovetkezo revision jon letre;
- a `current_revision_id` mindig a friss revisionre mutat;
- negativ vagy zéró meretekkel nem jon letre revision.

#### 6. A smoke script bizonyitsa a fo agakat
Legyen task-specifikus smoke, amely legalabb ezt bizonyitja:
- uj `code` eseten letrejon `sheet_definition` + `sheet_revision` es
  `revision_no = 1`;
- meglevo `code` eseten ugyanazon definition ala a kovetkezo revision jon;
- a `current_revision_id` a friss revisionre mutat;
- a meretek es a grain direction helyesen perzisztalodik;
- hiba jon negativ vagy zéró `width_mm` / `height_mm` eseten;
- hiba jon ures `code` / `name` eseten.

### DoD
- [ ] Keszul explicit sheet creation service a meglévo H0 sheet domain truth fole.
- [ ] A task a meglévo `app.sheet_definitions` es `app.sheet_revisions` tablakra epul, nem legacy schema-ra.
- [ ] A service H1 minimum teglalap alapu sheet revisiont hoz letre (`width_mm`, `height_mm`, opcionális `grain_direction`).
- [ ] Uj `code` eseten uj `sheet_definition` + `revision_no = 1` jon letre.
- [ ] Meglevo `code` eseten a kovetkezo `revision_no` jon letre ugyanazon definition alatt.
- [ ] A `sheet_definitions.current_revision_id` sikeresen az uj revisionre frissul.
- [ ] Keszul minimalis API endpoint a sheet creation workflowhoz.
- [ ] A task nem nyitja meg idovel elott a `project_sheet_inputs` workflowt.
- [ ] Keszul task-specifikus smoke script a sikeres es hibas agakra.
- [ ] A checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h1_e3_t2_sheet_creation_service_h1_minimum.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a task atcsuszik project sheet input vagy inventory scope-ba;
  - a meglevo definition ag versenyhelyzetben hibas revision-szamot ad;
  - a service kitalal nem-dokumentalt sheet geometry modellt.
- Mitigacio:
  - maradj owner-szintu definition/revision workflowban;
  - csak a H0 schema mezoit hasznald, es ha kell, kezeld a revision-szamot
    kontrollalt modon a service-ben vagy kulon DB segedfuggvennyel;
  - H1 minimum csak teglalap alapu meretek.
- Rollback:
  - a service/route/smoke valtozasok egy task-commitban visszavonhatok;
  - ha kell schema kiegeszites, az kulon migracioban tortenjen.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h1_e3_t2_sheet_creation_service_h1_minimum.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/services/sheet_creation.py api/routes/sheets.py scripts/smoke_h1_e3_t2_sheet_creation_service_h1_minimum.py`
  - `python3 scripts/smoke_h1_e3_t2_sheet_creation_service_h1_minimum.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `supabase/migrations/20260311000000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql`
- `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql`
- `api/services/part_creation.py`
- `api/routes/parts.py`
- `api/main.py`
