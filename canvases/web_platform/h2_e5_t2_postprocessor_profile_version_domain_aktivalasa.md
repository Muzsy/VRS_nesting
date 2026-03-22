# H2-E5-T2 Postprocessor profile/version domain aktiválása

## Funkció
Ez a task a H2 manufacturing/postprocess lánc következő, még mindig szűk
scope-ú lépése.
A cél, hogy a repóban ténylegesen aktiválódjon a postprocessor
profile/version domain, és a már létező `manufacturing_profile_versions`
truth tudjon egy kiválasztott, verziózott postprocessor profilverzióra
hivatkozni.

A jelenlegi repóállapotban már megvan:
- a manufacturing profile/version domain és a project-level manufacturing
  selection (`H2-E1-T1`, `H2-E1-T2`);
- a snapshot manufacturing bővítés, de a postprocess oldal még placeholder
  (`H2-E4-T1`);
- a manufacturing plan + metrics + preview réteg (`H2-E4-T2`, `H2-E4-T3`,
  `H2-E5-T1`).

Ami még hiányzik:
- tényleges `postprocessor_profiles` és
  `postprocessor_profile_versions` truth-réteg;
- owner-scoped CRUD a postprocessor profilokhoz és verziókhoz;
- a `manufacturing_profile_versions` explicit,
  auditálható hivatkozása aktív postprocessor profilverzióra;
- a snapshot builderben a placeholder `postprocess_selection_present=false`
  lecserélése valós, snapshotolt postprocessor selectionre, ha ilyen már van.

Ez a task szándékosan **nem** machine-neutral exporter,
**nem** machine-specific adapter, **nem** preview render redesign,
**nem** új project-level postprocess selection tábla,
és **nem** machine/material catalog bevezetés.

## Fejlesztési részletek

### Scope
- Benne van:
  - `app.postprocessor_profiles` tábla bevezetése owner-scoped logikai
    profilcsoportként;
  - `app.postprocessor_profile_versions` tábla bevezetése owner-scoped,
    verziózott konfigurációs truth-ként;
  - minimális, repo-hű mezők bevezetése a postprocessor domainhez, például:
    - profile szinten: `profile_code`, `display_name`, `adapter_key`,
      `notes`, `metadata_jsonb`, `is_active`;
    - version szinten: `version_no`, `lifecycle`, `output_format`,
      `schema_version`, egyetlen konfigurációs JSONB mező,
      `is_active`, `notes`, `metadata_jsonb`;
  - `app.manufacturing_profile_versions` bővítése
    `active_postprocessor_profile_version_id` nullable hivatkozással;
  - owner-konzisztencia biztosítása úgy, hogy egy manufacturing profile version
    csak ugyanazon owner postprocessor profile versionjére mutathasson;
  - owner-scoped CRUD service + route a postprocessor profile és version
    domainhez;
  - a `project_manufacturing_selection` read-path frissítése, hogy a kiválasztott
    manufacturing profile version postprocessor referenciája visszaadható legyen;
  - a `run_snapshot_builder` frissítése, hogy ha a kiválasztott manufacturing
    profile versionhez aktív postprocessor profilverzió tartozik, akkor:
    - a manufacturing manifest snapshotolja ezt,
    - `postprocess_selection_present=true` legyen,
    - `includes_postprocess=true` legyen;
  - task-specifikus smoke a CRUD / owner-boundary / snapshot invariánsokra.
- Nincs benne:
  - machine-neutral export artifact;
  - machine-specific adapter;
  - `run_artifacts` export bundle vagy machine-ready output;
  - postprocessor alkalmazása a persisted manufacturing planre;
  - új project-level postprocess selection tábla;
  - `machine_catalog`, `material_catalog` vagy más, a repóban nem létező
    catalog-FK világ bevezetése;
  - preview route vagy frontend módosítás.

### Talált releváns fájlok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - itt van a H2-E5-T2 task: postprocessor profile/version domain aktiválása.
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
  - a postprocessor domain aktiválás és a H2 preview/postprocess sorrend.
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
  - kritikus boundary: a postprocess külön modul marad, nem domain truth.
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
  - snapshot-first elv: a worker/export ne élő selectionből dolgozzon.
- `supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql`
  - manufacturing profile/version domain meglévő truth-ja.
- `supabase/migrations/20260322020000_h2_e4_t1_snapshot_manufacturing_bovites.sql`
  - a snapshot postprocess placeholder kiindulópontja.
- `api/services/project_manufacturing_selection.py`
  - a kiválasztott manufacturing profile version visszaolvasási pontja.
- `api/routes/project_manufacturing_selection.py`
  - a selection API response mintája.
- `api/services/run_snapshot_builder.py`
  - a manufacturing/postprocess manifest snapshotolás jelenlegi helye.
- `api/routes/cut_rule_sets.py`
  - owner-scoped CRUD route minta.
- `api/routes/cut_contour_rules.py`
  - nested version/rule route minta.
- `api/main.py`
  - route-regisztráció.

### Konkrét elvárások

#### 1. A postprocessor domain legyen minimális, de valós truth-réteg
A task vezessen be két új, owner-scoped táblát:
- `app.postprocessor_profiles`
- `app.postprocessor_profile_versions`

A cél nem egy teljes CAM/postprocess világ, hanem a későbbi exporterhez szükséges
legkisebb, de már verziózható, query-zhető truth-réteg.

Fontos boundary:
- ne jöjjön be `machine_catalog` / `material_catalog` FK világ;
- ne jelenjen meg machine-ready program vagy export bundle;
- a task maradjon selection + domain aktiválás szinten.

Repo-hű irány:
- text-kódok vagy egyszerű mezők használata megengedett;
- nem szabad a repó fölé nem létező catalogokat kitalálni.

#### 2. A manufacturing profile version tudjon aktív postprocessor versionre mutatni
A task bővítse a `manufacturing_profile_versions` truth-ot
`active_postprocessor_profile_version_id` mezővel.

Minimum elvárás:
- nullable referencia, mert a postprocess továbbra is opcionális lehet;
- ugyanazon owner-höz tartozó postprocessor profile versionre mutathasson;
- ne hozzon létre új `project_postprocess_selection` táblát;
- a postprocessor kiválasztás a manufacturing profile version része maradjon.

#### 3. Owner-scoped CRUD kell a postprocessor profile/version világra
A task szállítson dedikált service + route réteget.

Minimum elvárás:
- profile CRUD;
- version CRUD egy profile alatt;
- owner-boundary ellenőrzések;
- logikus route-szerkezet, például:
  - `POST/GET /v1/postprocessor-profiles`
  - `GET/PATCH/DELETE /v1/postprocessor-profiles/{profile_id}`
  - `POST/GET /v1/postprocessor-profiles/{profile_id}/versions`
  - `GET/PATCH/DELETE /v1/postprocessor-profiles/{profile_id}/versions/{version_id}`

A route és service mintája igazodjon a meglévő H2 owner-scoped CRUD mintákhoz.

#### 4. A snapshot builder végre valós postprocess selectiont snapshotoljon
A H2-E4-T1 még szándékosan placeholder volt:
- `postprocess_selection_present=false`
- `includes_postprocess=false`

Ebben a taskban ez csak akkor váltson át, ha a kiválasztott manufacturing
profile version ténylegesen tartalmaz aktív postprocessor profilverziót.

Minimum elvárás:
- ha nincs aktív postprocessor ref:
  - `postprocess_selection_present=false`
  - `includes_postprocess=false`
- ha van aktív, owner-valid postprocessor ref:
  - `postprocess_selection_present=true`
  - `includes_postprocess=true`
  - a manufacturing/postprocess manifest tartalmazza legalább:
    - `active_postprocessor_profile_version_id`
    - profile/version alap meta
    - `adapter_key`
    - `output_format`
    - `schema_version`

Fontos:
- ez még mindig snapshotolt selection, nem exporter futtatás.

#### 5. A selection read-path adjon vissza postprocessor referenciát
A `project_manufacturing_selection` jelenlegi response-a a kiválasztott
manufacturing profile versionre fókuszál.

Minimum elvárás:
- a read/upsert response vagy az ott visszaadott version payload jelezze,
  hogy van-e `active_postprocessor_profile_version_id`;
- ne legyen új selection API a postprocessorra;
- a selection továbbra is a manufacturing profile versionön keresztül érthető.

#### 6. A task maradjon távol az exportertől és adaptertől
Ez a task **nem** szállít le még:
- machine-neutral exportert;
- `machine_ready_bundle` artifactot;
- machine-specific adaptert;
- postprocessor settings alkalmazását a toolpathra;
- preview/export route-ot.

A task vége az, hogy a postprocessor kiválasztási világ domain-szinten már
létezik, CRUD-olható, és snapshotolható.

#### 7. A smoke bizonyítsa a fő invariánsokat
A task-specifikus smoke legalább ezt bizonyítsa:
- postprocessor profile és version owner-scoped CRUD működik;
- version csak a saját profile-ja alatt kezelhető;
- manufacturing profile version csak ugyanazon owner postprocessor versionjére
  mutathat;
- idegen owner postprocessor ref elutasításra kerül;
- a `project_manufacturing_selection` read-path visszaadja a postprocessor refet;
- a snapshot builder aktív postprocessor refnél `includes_postprocess=true`-ra vált;
- postprocessor ref nélkül a placeholder false marad;
- a task nem hoz létre export artifactot vagy machine-ready outputot;
- a task nem vezet be nem létező catalog-FK világot.

### DoD
- [ ] Letezik `app.postprocessor_profiles` owner-scoped truth-réteg.
- [ ] Letezik `app.postprocessor_profile_versions` owner-scoped, verziózott truth-réteg.
- [ ] Készül owner-scoped CRUD service + route a postprocessor domainhez.
- [ ] A `manufacturing_profile_versions` tud nullable
      `active_postprocessor_profile_version_id` hivatkozást tárolni.
- [ ] A manufacturing → postprocessor referencia owner-konzisztens.
- [ ] A `project_manufacturing_selection` read-path vissza tudja adni a
      kapcsolt postprocessor refet.
- [ ] A `run_snapshot_builder` valós postprocess selectiont snapshotol, ha van aktív ref.
- [ ] `includes_postprocess` csak aktív ref esetén lesz true.
- [ ] A task nem hoz létre export / adapter / machine-ready scope-ot.
- [ ] A task nem vezet be nem létező catalog-FK világot.
- [ ] Készül task-specifikus smoke script.
- [ ] Checklist és report evidence-alapon ki van töltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.md` PASS.

### Kockázat + rollback
- Kockázat:
  - a task túl korán machine-neutral export vagy adapter scope-ba csúszik;
  - új, nem létező machine/material catalog világot talál ki;
  - a postprocessor selection külön project-szintű táblába kerül, és széttöri
    a meglévő manufacturing selection logikát;
  - a snapshot továbbra is placeholder marad aktív ref mellett is;
  - a manufacturing profile version idegen owner postprocessor refre tud mutatni.
- Mitigáció:
  - explicit no-export / no-adapter / no-catalog boundary;
  - owner-consistency ellenőrzések migration + service + smoke szinten;
  - a selection továbbra is manufacturing-profile-version driven marad;
  - snapshot-smoke aktív és inaktív ref esetre is.
- Rollback:
  - a migration + route/service + smoke együtt egy task-commitban visszavonható;
  - a preview / plan / metrics réteg érintetlen marad;
  - a postprocess placeholder logika szükség esetén visszaállítható.

### Ellenőrzési parancsok
- Kötelező:
  - `./scripts/verify.sh --report codex/reports/web_platform/h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.md`
- Ajánlott:
  - `python3 -m py_compile api/services/postprocessor_profiles.py api/routes/postprocessor_profiles.py scripts/smoke_h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.py`
  - `python3 scripts/smoke_h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.py`
