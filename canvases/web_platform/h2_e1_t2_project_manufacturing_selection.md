# H2-E1-T2 Project manufacturing selection

## Funkcio
A feladat a H2 manufacturing profile domain masodik, projekt-szintu lepese.
A cel, hogy a projekt tulajdonosa egy konkret manufacturing profile versiont
tudjon a projekthez kivalasztani, visszaolvasni, modositani vagy torolni, es
ennek a truth-ja egy dedikalt `project_manufacturing_selection` retegben
rogzuljon.

Ez a task nem manufacturing profile CRUD, nem contour classification, nem
cut rule rendszer, nem snapshot manufacturing bovites, nem manufacturing plan
builder, es nem postprocess/export feladat. A scope szigoruan a projekt →
aktiv manufacturing profile version binding tartos es auditálhato rogzitese.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - a projekt-szintu manufacturing selection truth bevezetese vagy bekotese;
  - minimalis schema, ha a H2-E1-T1 utan a `app.project_manufacturing_selection`
    tabla meg nem letezik;
  - project owner alapu create-or-replace selection workflow;
  - explicit GET / PUT / DELETE backend contract a project manufacturing selectionhoz;
  - a manufacturing profile version ownership / aktivitas validalasa;
  - minimalis, repo-hu technology/manufacturing konzisztencia ellenorzes ott,
    ahol a jelenlegi schema erre tenylegesen kepes;
  - task-specifikus smoke a sikeres es hibas agakra.
- Nincs benne:
  - `app.manufacturing_profiles` es `app.manufacturing_profile_versions`
    CRUD-domain ujranyitasa;
  - cut rule set, contour rule, contour classification;
  - snapshot builder vagy `manufacturing_manifest_jsonb` aktiv bekotese;
  - manufacturing resolver, plan builder, preview vagy postprocessor;
  - UI vagy frontend allapotkezeles;
  - gepkatalogus / anyagkatalogus kitalalasa, ha a T1 schema erre nem adott
    valos truth-ot.

### Talalt relevans fajlok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - a H2-E1-T2 source-of-truth task definicioja; kimondja, hogy ez a task a
    project manufacturing selection flow.
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
  - a H2 detailed roadmap; kimondja a manufacturing profile domain aktiválását,
    a `project_manufacturing_selection` bekötését es a technology /
    manufacturing alapkonzisztencia igenyet.
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
  - a H0 korabbi placeholder schema-terve; itt szerepel a
    `app.project_manufacturing_selection` minimalis SQL-vazlata.
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
  - architekturalis SQL-vazlat a manufacturing profile version es a
    project manufacturing selection kapcsolatarol.
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
  - rögzíti, hogy a manufacturing kulon domain, nem keverheto a solver,
    projection vagy export vilaggal.
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
  - fontos boundary: a manufacturing selection kesobb snapshotolhato, de a
    snapshotolas nem ennek a tasknak a scope-ja.
- `supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql`
  - a `app.projects` jelenlegi truth-ja.
- `supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql`
  - a `app.project_technology_setups` jelenlegi technology truth-ja.
- `api/routes/projects.py`
  - projekt-szintu nested route mintakhoz relevans.
- `api/services/run_snapshot_builder.py`
  - fontos boundary-fajl; jelenleg technology setupot olvas, a manufacturing
    manifest pedig placeholder. Ez a task ezt nem aktiválja snapshot iranyba.
- `api/main.py`
  - uj router ide kotheto be.

### Konkret elvarasok

#### 1. A task a projekt-szintu selection truth-ot szallitsa le, ne a teljes manufacturing domaint
A task H2-E1-T1 utan fut. A H2-E1-T1 adja a valaszthato manufacturing
profile/version vilagot. Ez a task azt koti projekthez.

A perzisztens truth:
- vagy a H2-E1-T1 altal mar letrehozott `app.project_manufacturing_selection`,
- vagy ha az T1-ben meg nem jott letre, akkor ennek a tasknak a minimalis
  sajat migracioja hozza letre ugyanazt a selection tablát.

A task ne nyisson ujra profile CRUD scope-ot.

#### 2. Egy projektnek egy aktiv manufacturing selectionje legyen
A minimum elvart adatmodell:
- `project_id`
- `active_manufacturing_profile_version_id`
- `selected_at`
- `selected_by`

A viselkedes legyen create-or-replace:
- ha a projektnek nincs selectionje, letrejon uj rekord;
- ha mar van, ugyanarra a projektre a selection cserelodik / frissul;
- ne jojjon letre tobb aktiv selection rekord ugyanarra a projektre.

#### 3. A service validalja a tulajdont es a valaszthato version ervenyesseget
A minimum ellenorzes:
- a projekt a jelenlegi user tulajdona;
- a kivalasztott manufacturing profile version a jelenlegi owner scope-jaban van;
- ha a T1 schema tartalmaz aktivitasjelzot, csak aktiv version valaszthato;
- torles vagy ujrakivalasztas se tudjon idegen projektet vagy idegen versiont
  erinteni.

Ne talalj ki olyan ownership modellt, ami nincs a T1 schema-ban. A task a
valos T1 truth-ra epuljon.

#### 4. A technology/manufacturing konzisztencia ellenorzes legyen minimalis es repo-hu
A H2 detailed doc elvarja az alapkonzisztenciat, de a jelenlegi repoban nincs
tenyleges `machine_catalog` / `material_catalog` truth.

Ezert:
- ha a T1 schema ad tenylegesen osszevetheto mezo(ke)t, hasznald azt;
- ha csak `thickness_mm` a biztos, valos kozos pont, minimum azt validald;
- ne talalj ki catalog joinokat vagy gep-/anyag-azonosito logikat, ha arra
  nincs valos schema;
- ha a kovetkezo reteghez tobb adat kellene, azt a reportban nevezd meg
  explicit korlatkent.

#### 5. Minimalis API contract legyen, ne snapshot-integracio
Keszits legalabb ezt a minimum backend contractot:
- `PUT /projects/{project_id}/manufacturing-selection`
- `GET /projects/{project_id}/manufacturing-selection`
- `DELETE /projects/{project_id}/manufacturing-selection`

Javasolt request:
- `active_manufacturing_profile_version_id`

Javasolt response:
- `project_id`
- `active_manufacturing_profile_version_id`
- `selected_at`
- `selected_by`
- opcionálisan `manufacturing_profile_id`, `version_no`, `profile_name`,
  ha ez a valos schema alapjan egyszeruen es tisztan feloldhato.

Ez a task nem modositja a `run_snapshot_builder` manufacturing manifest reszet.

#### 6. A task ne csusszon at resolver vagy snapshot scope-ba
A feladat nem:
- manufacturing profile resolver;
- run snapshot manufacturing bővítés;
- live profile → worker → plan pipeline;
- postprocessor kivalasztas;
- export adapter.

A selection itt csak projekt-truth, amit a kesobbi H2-E4 taskok fognak
snapshotolni es felhasznalni.

#### 7. A smoke script bizonyitsa a fo agakat
Legyen task-specifikus smoke, amely legalabb ezt bizonyitja:
- uj projektre selection rogzithetö;
- meglevo selection felulirhato ugyanarra a projektre;
- GET visszaadja a selectiont;
- DELETE torli a selectiont;
- hiba jon idegen projektre;
- hiba jon idegen / nem lathato manufacturing profile version eseten;
- hiba jon inaktiv version eseten, ha a valos schema tartalmaz `is_active`-ot;
- hiba jon konzisztencia-serto valasztas eseten ott, ahol a valos schema ezt
  tenylegesen ellenorizheto modon lehetove teszi.

### DoD
- [ ] A task repo-hu modon bevezeti vagy bekoti a `project_manufacturing_selection` truth-ot.
- [ ] Egy projektnek legfeljebb egy aktiv manufacturing selectionje van.
- [ ] A selection project owner scope-ban hozhato letre, modositato es torolheto.
- [ ] A selection csak a userhez tartozó ervenyes manufacturing profile versionra mutathat.
- [ ] A task nem nyitja ujra a manufacturing profile CRUD scope-ot.
- [ ] A task nem nyul a snapshot / plan / preview / postprocess reteghez.
- [ ] Keszul minimalis GET / PUT / DELETE backend contract.
- [ ] A technology/manufacturing alapkonzisztencia ellenorzes csak valos schema mezokre tamaszkodik.
- [ ] Keszul task-specifikus smoke script a sikeres es hibas agakra.
- [ ] A checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h2_e1_t2_project_manufacturing_selection.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a task belenyit a teljes manufacturing profile domainbe;
  - a selection route snapshot vagy resolver scope-ot kezd el vallalni;
  - a konzisztencia-ellenorzes kitalalt catalog truth-ra epul;
  - a projektre tobb selection rekord marad aktivan.
- Mitigacio:
  - maradj szigoruan project-level selection scope-ban;
  - a table legyen project-id primary key vagy ugyanilyen eros egyedisegu truth;
  - csak a tenylegesen letezo T1 schema-mezokre epits;
  - snapshot builder erintetlen maradjon.
- Rollback:
  - migration + service + route + smoke valtozasok egy task-commitban
    visszavonhatok;
  - ha a technology/manufacturing konzisztencia tul erosnek bizonyul, a
    validacios resz a selection truth megtartasa mellett kesobb lazithato.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h2_e1_t2_project_manufacturing_selection.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/services/project_manufacturing_selection.py api/routes/project_manufacturing_selection.py api/main.py scripts/smoke_h2_e1_t2_project_manufacturing_selection.py`
  - `python3 scripts/smoke_h2_e1_t2_project_manufacturing_selection.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql`
- `supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql`
- `api/routes/projects.py`
- `api/services/run_snapshot_builder.py`
- `api/main.py`

