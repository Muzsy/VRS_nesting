
# canvases/web_platform/h0_e2_t4_part_definition_revision_es_demand_alapok.md

# H0-E2-T4 part definition, revision es demand alapok

## Funkcio
A feladat a web platform part-domain bazis schemajanak letetele:
a `part_definitions`, `part_revisions` es `project_part_requirements` tablavilag
bevezetese Supabase/Postgres oldalon.

Ez a task a technology domain utan a kovetkezo logikus H0 schema-lepes.
A cel, hogy a projekt mar ne csak technology setupot tudjon hordozni, hanem
legyen kulon:
- hosszu eletu part torzs-definicio,
- verziozott part revision vilag,
- es attol kulon, projekt-specifikus demand/quantity/input vilag.

A task szandekosan meg mindig kontrollalt scope-u:
- geometry/file/revision pipeline teljes bekotese meg nincs keszen,
- sheet domain kulon task marad,
- run snapshot/orchestration meg nincs scope-ban,
- RLS es API meg nincs scope-ban.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - uj Supabase migracio letrehozasa a part-domain alap tablakkal;
  - `app.part_definitions` letrehozasa;
  - `app.part_revisions` letrehozasa;
  - `app.project_part_requirements` letrehozasa;
  - PK/FK kapcsolatok es alap indexek letetele;
  - a domain ownership doksikkal osszhangban a definition / revision / demand
    szeparacio rogzitese;
  - minimal docs szinkron, ha a fo architecture/H0 doksikban a part-domain
    SQL-peldak meg stale, `public.*` schemajuak, vagy a demand vilagot rossz
    aggregate-hez kotik.
- Nincs benne:
  - geometry_revisions tabla letrehozasa;
  - geometry_derivatives tabla letrehozasa;
  - uploaded file metadata tabla;
  - sheet_definitions / sheet_revisions / project_sheet_inputs;
  - run request / snapshot / attempt tabla;
  - remnant / stock inventory tabla;
  - export/manufacturing package tabla;
  - RLS policy;
  - API endpoint implementacio.

### Fo kerdesek, amiket le kell zarni
- [ ] Mi legyen a part definition minimalis, de stabil oszlopkeszlete?
- [ ] Mi legyen a part revision minimalis, de mar hasznalhato H0 bazisa ugy,
      hogy geometry pipeline meg nincs bekotve?
- [ ] A project demand a part definitionre vagy a part revisionre mutasson?
- [ ] Kell-e mar most `current_revision_id`, vagy eleg a revision tabla + ordering?
- [ ] Mi legyen dedikalt oszlop, es mi maradjon metadata JSONB?
- [ ] Hogyan tartsuk a scope-ot ugy, hogy ne csusszon at geometry/file/run vilagba?

### Feladatlista
- [ ] Kesz legyen a task teljes artefaktlanca.
- [ ] Letrejojjon a kovetkezo H0-E2 migracio a part-domain alapokhoz.
- [ ] A migracio letrehozza az `app.part_definitions` tablata.
- [ ] A migracio letrehozza az `app.part_revisions` tablata.
- [ ] A migracio letrehozza az `app.project_part_requirements` tablata.
- [ ] A `project_part_requirements` a veglegesitett domain entitasterkepnek
      megfeleloen a `part_revisions` vilagra uljon ra, ne kozvetlenul a definitionre.
- [ ] A task ne hozzon letre geometry/file/sheet/run/remnant/export tablakat.
- [ ] Minimal docs szinkron tortenjen, ha szukseges.
- [ ] Repo gate le legyen futtatva a reporton.

### Erintett fajlok
- `canvases/web_platform/h0_e2_t4_part_definition_revision_es_demand_alapok.md`
- `codex/goals/canvases/web_platform/fill_canvas_h0_e2_t4_part_definition_revision_es_demand_alapok.yaml`
- `codex/prompts/web_platform/h0_e2_t4_part_definition_revision_es_demand_alapok/run.md`
- `codex/codex_checklist/web_platform/h0_e2_t4_part_definition_revision_es_demand_alapok.md`
- `codex/reports/web_platform/h0_e2_t4_part_definition_revision_es_demand_alapok.md`
- `supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`

### Elvart tabla-irany
A konkret oszlopok kod kozben finomithatok, de az irany ez legyen:

- `app.part_definitions`
  - `id uuid primary key default gen_random_uuid()`
  - `owner_user_id uuid not null references app.profiles(id) on delete restrict`
  - `code text not null`
  - `name text not null`
  - `description text`
  - opcionális `current_revision_id uuid`
  - `created_at`, `updated_at`
  - `unique (owner_user_id, code)`

- `app.part_revisions`
  - `id uuid primary key default gen_random_uuid()`
  - `part_definition_id uuid not null references app.part_definitions(id) on delete cascade`
  - `revision_no integer not null`
  - `lifecycle app.revision_lifecycle not null default 'draft'`
  - minimalis revision-szintu metadata / notes / checksum / source reference mezok,
    de geometry/file FK-k nelkul, ha azok meg nincsenek letrehozva
  - `created_at`, `updated_at`
  - `unique (part_definition_id, revision_no)`

- `app.project_part_requirements`
  - `id uuid primary key default gen_random_uuid()`
  - `project_id uuid not null references app.projects(id) on delete cascade`
  - `part_revision_id uuid not null references app.part_revisions(id) on delete restrict`
  - `required_qty integer not null check (required_qty > 0)`
  - `placement_priority smallint not null default 50`
  - `placement_policy app.placement_policy not null default 'normal'`
  - `is_active boolean not null default true`
  - `notes text`
  - `created_at`, `updated_at`
  - `unique (project_id, part_revision_id)`

### Fontos modellezesi elvek
- `Part Definition` != `Part Revision` != `Part Demand`
- A demand vilag projekt-specifikus usage/input, nem a definition resze.
- A demand a revisionra mutasson, ne a definitionre.
- A `part_revisions` most meg NEM geometry pipeline truth; ez csak a domain bazis.
- Ha geometry/file FK meg nincs stabilan lerakva, ne eroszakold bele ebbe a taskba.
- Az `app` schema maradjon canonical celterulet.
- A task egyben docs-tisztitas is legyen a part-domain `public.*` maradvanyok ellen.

### DoD
- [ ] Letrejon a `supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql`
      fajl.
- [ ] A migracio letrehozza az `app.part_definitions`, `app.part_revisions`,
      `app.project_part_requirements` tablakat.
- [ ] A demand tabla a `part_revisions` vilagra ul, nem kozvetlenul a definitionre.
- [ ] A migracio nem hoz letre geometry/file/sheet/run/remnant/export tablakat.
- [ ] A task nem ad hozza RLS policyt.
- [ ] A `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
      es a `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
      minimalisan szinkronba kerul a konkret migracios irannyal, ha szukseges.
- [ ] A report DoD -> Evidence Matrix konkret fajl- es line-hivatkozasokkal kitoltott.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h0_e2_t4_part_definition_revision_es_demand_alapok.md`
      PASS.

### Kockazat + rollback
- Kockazat:
  - a regi doksik reszben a demandot meg a definitionhoz kotik;
  - a geometry pipeline meg hianyzik, ezert a revision tabla tul sovany vagy tul
    bonyolult lehet;
  - a task belecsuszhat sheet/file/run vilagba.
- Mitigacio:
  - a H0 domain entitasterkep legyen az elsosegi forras;
  - revision tabla csak minimalis, geometry-FK nelkuli bazist kapjon, ha kell;
  - explicit out-of-scope lista;
  - minimal docs sync a `public.*` es a rossz aggregate-kotes javitasara.
- Rollback:
  - a migracio + checklist/report + minimal docs edit egy commitban visszavonhato.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h0_e2_t4_part_definition_revision_es_demand_alapok.md`
- Manualis ellenorzes:
  - pontosan ez a 3 tabla jon letre;
  - a demand a revisionra mutat;
  - nincs geometry/file/sheet/run tabla;
  - nincs RLS;
  - a docs mar nem sugall `public.*` part-domain source-of-truth iranyt.

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
