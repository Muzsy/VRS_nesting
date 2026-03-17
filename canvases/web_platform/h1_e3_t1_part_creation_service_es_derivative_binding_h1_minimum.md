# H1-E3-T1 Part creation service és derivative binding (H1 minimum)

## Funkcio
A feladat a H1 geometry pipeline utan kovetkezo, elso domain-szintu bekotes:
a mar validalt canonical geometry es az abból eloallitott `nesting_canonical`
derivative alapjan tenyleges, hasznalhato `part_definition` + `part_revision`
letrehozasa.

A H1-E2-T4 vegere a rendszer mar tudja:
- a `source_dxf` fajlt ingestelni;
- `geometry_revision` rekordda alakitani;
- validation reportot generalni;
- `nesting_canonical` es `viewer_outline` derivative-eket eloallitani.

A kovetkezo minimum az, hogy a solverhez szukseges domain truth mar ne kozvetlen
`geometry_revisions` / `geometry_derivatives` rekordokra, hanem `part_revisions`
entitasra epuljon.

Ez a task meg mindig nem requirement management, nem sheet workflow es nem run
snapshot builder. A cel kizárólag az, hogy egy felhasznalo/projekt szamara a
validalt geometry-bol letrehozhato legyen egy domain-szintu part revision,
amely explicit nesting-derivative bindinggel rendelkezik.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - explicit part creation service bevezetese, amely egy projekthez tartozo,
    validalt `geometry_revision`-bol hoz letre `part_definition` +
    `part_revision` rekordot;
  - a `nesting_canonical` derivative kotelezo bekotese a letrejovo
    `part_revision`-hoz;
  - minimalis schema-bovites a `part_revisions` tablaban a geometry/derivative
    binding tarolasara;
  - a `current_revision_id` korrekt frissitese uj vagy meglevo definition eseten;
  - owner- es project-scope ellenorzes a geometry revisionon;
  - minimum HTTP API endpoint a part letrehozashoz;
  - task-specifikus smoke script a sikeres, hibas es meglevo-definition ag
    bizonyitasara.
- Nincs benne:
  - project part requirement kezeles;
  - sheet workflow;
  - review UI vagy kulon approval workflow;
  - run snapshot builder;
  - manufacturing derivative vagy manufacturing binding;
  - tomeges import vagy CSV/batch ingest.

### Talalt relevans fajlok
- `supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql`
  - a `part_definitions` / `part_revisions` / `project_part_requirements` H0 truth-ja.
- `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql`
  - a `geometry_derivatives` tabla H0 truth-ja.
- `api/routes/files.py`
  - a jelenlegi file ingest pont, ahonnan a geometry revision lineage indul.
- `api/services/dxf_geometry_import.py`
  - a geometry import + validation + derivative generalas H1 gerince.
- `api/main.py`
  - uj `parts` router ide kotheto be.
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
  - a H1 reszletes terv szerint a kovetkezo lepés a part creation service.
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - H1-E3-T1 task source-of-truth.

### Konkret elvarasok

#### 1. A part workflow ne kozvetlen geometry truth-ra uljon
A service ne kozvetlen raw file-ra es ne kozvetlen DXF parserre epuljon, hanem
mar a H1-E2-T4 vegere eloalló truth-ra:
- `geometry_revision.status == 'validated'`
- a geometry revision ugyanahhoz a projekthez tartozik, mint a kereso endpoint
- a geometry revisionhoz letezik `nesting_canonical` derivative

A service ne fogadjon el `parsed` vagy `rejected` geometry-t.

#### 2. Legyen explicit derivative binding a part revisionon
A jelenlegi H0 `part_revisions` schema meg nem tarolja, melyik geometry/derivative
alapjan jott letre a domain revision. Ezt most technikailag is le kell tenni.

A minimum elvart bővites:
- `source_geometry_revision_id` jellegu hivatkozas a forras geometry revisionre;
- `selected_nesting_derivative_id` jellegu hivatkozas a solverhez hasznalando
  derivative-re;
- opcionálisan `unit_code` / `is_active` H1-minimum mezok, ha a megvalositas ezt
  egyben rendezi.

Fontos: ne vezess be uj, a meglévo `lifecycle`-fal redundans approval mezot csak
azert, mert a roadmap szovegben szerepel az "approved derivative" kifejezes.
A jelenlegi repo truth-ban a `part_revisions.lifecycle` mar letezik; az uj task
minimuma az explicit binding, nem egy parhuzamos approval-allapotgep.

#### 3. A service kezelje az uj es a meglevo part definition agat
A minimum viselkedes:
- ha az adott ownernel a `code` meg nem letezik, jojjon letre uj
  `part_definition`, majd `revision_no = 1`-gyel uj `part_revision`;
- ha a `code` mar letezik ugyanannal az ownernel, akkor a meglevo definition ala
  jojjon uj revision a kovetkezo `revision_no`-val;
- sikeres letrehozas utan a `part_definitions.current_revision_id` az uj revisionre
  mutasson.

A service ne torjon el a H0-ban mar vedett `current_revision_id` integritason.

#### 4. Legyen egyertelmu minimalis API contract
Készüljön legalabb egy backend endpoint, peldaul projekt-szintu kontextusban,
amelyből a part revision letrehozhato.

Javasolt H1-minimum request contract:
- `code`
- `name`
- `geometry_revision_id`
- opcionálisan `description`, `notes`, `source_label`

A service maga oldja fel a `nesting_canonical` derivative-et, ne a kliensnek kelljen
alacsony szintu derivative ID-t ismernie ehhez az elso workflowhoz.

#### 5. A forrasintegritas legyen vedett
A task vegere legyen bizonyithato, hogy:
- mas projekt geometry revisionjabol nem hozhato letre part;
- olyan geometry revisionbol, amelyhez nincs `nesting_canonical` derivative,
  nem hozhato letre part;
- `rejected` vagy `parsed` geometrybol nem hozhato letre part;
- a `part_revision`-on tarolt derivative binding tenyleg a megadott geometry
  revisionhoz tartozik.

#### 6. A smoke script bizonyitsa a fo agakat
Legyen task-specifikus smoke, amely legalabb ezt bizonyitja:
- validalt geometry + meglevo `nesting_canonical` derivative mellett letrejon
  `part_definition` + `part_revision`;
- uj `code` eseten `revision_no = 1`, meglevo `code` eseten kovetkezo revision jon;
- a `current_revision_id` az uj revisionre frissul;
- a part revisionon tarolt geometry/derivative binding helyes;
- hiba jon, ha a geometry nem validalt;
- hiba jon, ha a derivative hianyzik vagy nem `nesting_canonical`;
- hiba jon, ha a geometry mas projektbol szarmazik.

### DoD
- [ ] Keszul explicit part creation service a validalt geometry + derivative truth fole.
- [ ] A task a meglévo `app.part_definitions` es `app.part_revisions` tablakra epul, nem legacy phase schema-ra.
- [ ] A `part_revisions` schema megkapja a minimum geometry/derivative binding mezo(ke)t.
- [ ] A service csak a projektbe tartozo, `validated` geometry revisionbol enged part letrehozast.
- [ ] A service kotelezoen `nesting_canonical` derivative-et kot a letrejovo part revisionhoz.
- [ ] Uj `code` eseten uj `part_definition` + `revision_no = 1` jon letre.
- [ ] Meglevo `code` eseten a kovetkezo `revision_no` jon letre ugyanazon definition alatt.
- [ ] A `part_definitions.current_revision_id` sikeresen az uj revisionre frissul.
- [ ] Keszul minimalis API endpoint a part creation workflowhoz.
- [ ] Keszul task-specifikus smoke script a sikeres es hibas agakra.
- [ ] A checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h1_e3_t1_part_creation_service_es_derivative_binding_h1_minimum.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a service kozvetlen geometry truth-ra drotozza a kovetkezo retegeket, es nem
    `part_revision`-re;
  - a schema-bovites redundans vagy ellentmondo approval mezoeket vezet be;
  - a derivative binding nincs valosan vedve, es idegen geometryra mutathat;
  - a task atcsuszik requirement management vagy run snapshot scope-ba.
- Mitigacio:
  - explicit geometry + nesting-derivative binding a `part_revision`-on;
  - a meglévo `lifecycle` mezot hasznald, ne vezess be masodik approval allapotot
    csak megszokasbol;
  - projekt- es derivative-integritas ellenorzes az endpointban es service-ben;
  - requirement/run/manufacturing explicit out-of-scope.
- Rollback:
  - a service/route/smoke valtozasok egy task-commitban visszavonhatok;
  - a schema-bovites kulon migracioban legyen, hogy egyertelmu rollback pont legyen.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h1_e3_t1_part_creation_service_es_derivative_binding_h1_minimum.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/services/part_creation.py api/routes/parts.py scripts/smoke_h1_e3_t1_part_creation_service_es_derivative_binding_h1_minimum.py`
  - `python3 scripts/smoke_h1_e3_t1_part_creation_service_es_derivative_binding_h1_minimum.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql`
- `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql`
- `api/services/dxf_geometry_import.py`
- `api/routes/files.py`
- `api/main.py`
