# canvases/web_platform/h0_e2_t5_sheet_definition_revision_es_project_input_alapok.md

# H0-E2-T5 sheet definition, revision es project input alapok

## Funkcio
A feladat a web platform sheet-domain bazis schemajanak letetele:
a `sheet_definitions`, `sheet_revisions` es `project_sheet_inputs` tablavilag
bevezetese Supabase/Postgres oldalon.

Ez a task kozvetlenul a H0-E2-T4 part-domain bazis utan kovetkezik.
A cel, hogy a projekt mar ne csak part demandot, hanem kulon kezelt
sheet/input vilagot is tudjon hordozni, a veglegesitett domain elvek szerint
szetvalasztva:

- hosszu eletu sheet torzs-definicio,
- verziozott sheet revision vilag,
- es attol kulon, projekt-specifikus sheet input / availability vilag.

Ez szandekosan meg mindig H0-bazis:
- remnant es valodi inventory meg kulon task,
- run snapshot/orchestration meg nincs scope-ban,
- geometry/file pipeline sheet-oldali bekotese meg nincs keszen,
- RLS es API meg nincs scope-ban.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - uj Supabase migracio letrehozasa a sheet-domain alap tablakkal;
  - `app.sheet_definitions` letrehozasa;
  - `app.sheet_revisions` letrehozasa;
  - `app.project_sheet_inputs` letrehozasa;
  - PK/FK kapcsolatok es alap indexek letetele;
  - a domain ownership doksikkal osszhangban a definition / revision / project-input
    szeparacio rogzitese;
  - minimal docs szinkron, ha a fo architecture/H0 doksikban a sheet-domain
    SQL-peldak meg stale, `public.*` schemajuak, vagy a project input vilagot
    hibasan a definitionhoz kotik.
- Nincs benne:
  - remnant tabla letrehozasa;
  - stock inventory unit tabla letrehozasa;
  - uploaded file metadata tabla;
  - geometry_revisions / geometry_derivatives tabla;
  - run request / snapshot / attempt tabla;
  - export/manufacturing package tabla;
  - RLS policy;
  - API endpoint implementacio.

### Fo kerdesek, amiket le kell zarni
- [ ] Mi legyen a sheet definition minimalis, de stabil oszlopkeszlete?
- [ ] Mi legyen a sheet revision minimalis, de H0-ban mar hasznalhato bazisa?
- [ ] A projekt sheet input a definitionre vagy a revisionre mutasson?
- [ ] Hogyan kulonuljon el a sheet catalog truth es a projektben hasznalt
      availability/input vilag?
- [ ] Mi legyen dedikalt oszlop, es mi maradjon metadata JSONB?
- [ ] Hogyan maradjon kivul a remnant es inventory vilag ebbol a taskbol?

### Feladatlista
- [ ] Kesz legyen a task teljes artefaktlanca.
- [ ] Letrejojjon a kovetkezo H0-E2 migracio a sheet-domain alapokhoz.
- [ ] A migracio letrehozza az `app.sheet_definitions` tablata.
- [ ] A migracio letrehozza az `app.sheet_revisions` tablata.
- [ ] A migracio letrehozza az `app.project_sheet_inputs` tablata.
- [ ] A `project_sheet_inputs` a veglegesitett domain entitasterkepnek megfeleloen
      a `sheet_revisions` vilagra uljon ra, ne kozvetlenul a definitionre.
- [ ] A task ne hozzon letre remnant/inventory/file/geometry/run/export tablakat.
- [ ] Minimal docs szinkron tortenjen, ha szukseges.
- [ ] Repo gate le legyen futtatva a reporton.

### Erintett fajlok
- `canvases/web_platform/h0_e2_t5_sheet_definition_revision_es_project_input_alapok.md`
- `codex/goals/canvases/web_platform/fill_canvas_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.yaml`
- `codex/prompts/web_platform/h0_e2_t5_sheet_definition_revision_es_project_input_alapok/run.md`
- `codex/codex_checklist/web_platform/h0_e2_t5_sheet_definition_revision_es_project_input_alapok.md`
- `codex/reports/web_platform/h0_e2_t5_sheet_definition_revision_es_project_input_alapok.md`
- `supabase/migrations/20260310240000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`

### Elvart tabla-irany
A konkret oszlopok kod kozben finomithatok, de az irany ez legyen:

- `app.sheet_definitions`
  - `id uuid primary key default gen_random_uuid()`
  - `owner_user_id uuid not null references app.profiles(id) on delete restrict`
  - `code text not null`
  - `name text not null`
  - `description text`
  - opcionális `current_revision_id uuid`
  - `created_at`, `updated_at`
  - `unique (owner_user_id, code)`

- `app.sheet_revisions`
  - `id uuid primary key default gen_random_uuid()`
  - `sheet_definition_id uuid not null references app.sheet_definitions(id) on delete cascade`
  - `revision_no integer not null`
  - `lifecycle app.revision_lifecycle not null default 'draft'`
  - sheet-szintu alapparameterek legalabb:
    - `width_mm numeric(...) not null`
    - `height_mm numeric(...) not null`
    - opcionális `grain_direction text` vagy enum, ha mar van stabil enum
    - opcionális `notes`
    - opcionális metadata/checksum/source reference mezok
  - `created_at`, `updated_at`
  - `unique (sheet_definition_id, revision_no)`
  - a `current_revision_id` integritasanal ugyanaz az elv ervenyes, mint a
    part-domain taskban: ne lehessen mas definitionhoz tartozo revisionra mutatni

- `app.project_sheet_inputs`
  - `id uuid primary key default gen_random_uuid()`
  - `project_id uuid not null references app.projects(id) on delete cascade`
  - `sheet_revision_id uuid not null references app.sheet_revisions(id) on delete restrict`
  - `required_qty integer not null check (required_qty > 0)`
  - opcionális `is_active boolean not null default true`
  - opcionális `is_default boolean not null default false`
  - opcionális `placement_priority smallint not null default 50`
  - opcionális `notes text`
  - `created_at`, `updated_at`
  - `unique (project_id, sheet_revision_id)`

### Fontos modellezesi elvek
- `Sheet Definition` != `Sheet Revision` != `Project Sheet Input`
- A project sheet input projekt-specifikus input/availability vilag, nem a definition resze.
- A project input a revisionra mutasson, ne a definitionre.
- A `sheet_revisions` most meg NEM inventory truth es NEM remnant vilag.
- A task ne probalja most meg az inventory unit vagy remnant modellezest bevezetni.
- Ha file/geometry pipeline FK meg nincs stabilan lerakva, ne eroszakold bele ebbe a taskba.
- Az `app` schema maradjon canonical celterulet.
- A task egyben docs-tisztitas is legyen a sheet-domain `public.*` maradvanyok ellen.

### DoD
- [ ] Letrejon a `supabase/migrations/20260310240000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql`
      fajl.
- [ ] A migracio letrehozza az `app.sheet_definitions`, `app.sheet_revisions`,
      `app.project_sheet_inputs` tablakat.
- [ ] A project input tabla a `sheet_revisions` vilagra ul, nem kozvetlenul a definitionre.
- [ ] A `current_revision_id` integritas a part-domainhez hasonloan helyesen van kezelve.
- [ ] A migracio nem hoz letre remnant/inventory/file/geometry/run/export tablakat.
- [ ] A task nem ad hozza RLS policyt.
- [ ] A `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
      es a `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
      minimalisan szinkronba kerul a konkret migracios irannyal, ha szukseges.
- [ ] A report DoD -> Evidence Matrix konkret fajl- es line-hivatkozasokkal kitoltott.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h0_e2_t5_sheet_definition_revision_es_project_input_alapok.md`
      PASS.

### Kockazat + rollback
- Kockazat:
  - a regi doksik reszben a project sheet inputot meg a definitionhoz kotik;
  - a remnant/inventory vilag belecsuszik a taskba;
  - a `current_revision_id` integritas hibasan vagy felig kerul csak be;
  - a sheet revision tabla tul sovany vagy future-scope tulterhelt lesz.
- Mitigacio:
  - a H0 domain entitasterkep legyen az elsosegi forras;
  - revision tabla csak minimalis, de stabil bazist kapjon;
  - explicit out-of-scope lista;
  - minimal docs sync a `public.*` es a rossz aggregate-kotes javitasara.
- Rollback:
  - a migracio + checklist/report + minimal docs edit egy commitban visszavonhato.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h0_e2_t5_sheet_definition_revision_es_project_input_alapok.md`
- Manualis ellenorzes:
  - pontosan ez a 3 tabla jon letre;
  - a project input a revisionra mutat;
  - nincs remnant/inventory/file/geometry/run tabla;
  - nincs RLS;
  - a docs mar nem sugall `public.*` sheet-domain source-of-truth iranyt.

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_priorizalt_sprint_backlog_p0_p1_p2.md`
- `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql`
- `supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql`
- `supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql`
- `supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql`
