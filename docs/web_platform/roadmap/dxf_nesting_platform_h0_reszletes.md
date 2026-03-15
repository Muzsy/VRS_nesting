# DXF Nesting Platform — H0 részletes terv

## Cél

A **H0** a teljes platform alapozó szakasza. Nem a “látványos funkciók” fázisa, hanem az a réteg, amely nélkül a későbbi nesting, manufacturing és postprocess modulok törékenyek, nehezen auditálhatók vagy később drágán újratervezendők lennének.

A H0 célja, hogy létrejöjjön egy olyan **stabil, moduláris, verziózott és reprodukálható platformalap**, amelyre később biztonságosan ráépíthető:

- a DXF import és geometria-audit,
- a projekt- és technológiamenedzsment,
- a nesting run orchestration,
- a viewer/artifact rendszer,
- a manufacturing szabályrendszer,
- a gépfüggő postprocess/export réteg.

A H0 tehát nem “egy kis setup”, hanem a platform **szerkezeti gerince**.

---

## H0 fő célképe

A H0 végére a rendszernek az alábbi alapelveket kell teljesítenie:

1. **A nesting engine külön modul**  
   Nem a teljes alkalmazás magja, hanem egy jól definiált input/output szerződés szerint működő számítómodul.

2. **A Supabase a központi állapot- és metaadattár**  
   A platform üzleti állapotát, revízióit, snapshotjait, artifactjeit és projectionjeit tárolja, nem pedig az engine futás közbeni belső memóriáját.

3. **Definíció, használat, snapshot és artifact külön világ**  
   Ugyanazt az entitást nem szabad keverten kezelni “élő definícióként” és “lefagyasztott futási inputként”.

4. **Minden futás reprodukálható legyen**  
   A worker csak snapshotból dolgozzon. Ne élő technológiai profilból, ne élő projektállapotból.

5. **A geometria belső formátuma ne DXF és ne SVG legyen**  
   A belső reprezentáció saját, verziózott canonical geometry modell legyen.

6. **A nesting, manufacturing és postprocess külön réteg legyen**  
   Ezek egymásra épülnek, de nem keverhetők össze.

H0 modulhatar source-of-truth:
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
H0 domain entitasterkep source-of-truth:
- `docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md`
H0 snapshot-first futasi source-of-truth:
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`

---

## H0 scope

A H0-ba azt érdemes betenni, ami:

- minden későbbi fázis előfeltétele,
- architekturálisan nehezen javítható, ha rosszul indul,
- nem domain-opcionális, hanem alapinfrastruktúra,
- támogatja a teljes későbbi roadmapot.

### H0-ba tartozik

- projekt- és profilalapú domain váz
- Supabase alapséma
- verziózott technológiai modell alapjai
- fájlobjektum és geometria-revízió modell
- nesting run / snapshot / artifact / projection gerinc
- worker queue alapmodell
- storage stratégia
- RLS alapelvek
- auditálhatóság
- determinisztikus futás-alapok
- viewer truth modell alapjai
- placement priority helyének kijelölése
- manufacturing és postprocess domain helyének kijelölése
- geometry derivatives helyének előkészítése

### H0-ba nem tartozik teljes mélységben

- végleges DXF normalizáló pipeline teljes implementációja
- teljes nesting solver fejlesztés
- fejlett SA/metaheurisztika
- full manufacturing rule engine
- teljes gépspecifikus postprocessor készlet
- raktárkezelés / remnant inventory mély logika
- composite/mini-nest összetett üzleti workflow
- kész frontend viewer összes kényelmi funkciója

A H0 célja nem ezek leszállítása, hanem hogy **ezeknek legyen helye és szerződése**.

---

## H0 architekturális döntések

## 1. Modulhatárok rögzítése

A teljes rendszer legalább az alábbi logikai modulokra bomlik:

### A. Platform Core
- projektkezelés
- technológiai kiválasztás
- part/sheet input kezelés
- run orchestration
- artifact és projection kezelés

### B. Geometry Pipeline
- fájlfeltöltés
- parse
- normalizálás
- validáció
- canonical belső reprezentáció
- geometry derivative előállítás

### C. Nesting Engine Adapter
- run snapshotból engine input képzése
- CLI/worker hívás
- solver output beolvasása
- canonical run result kialakítása

### D. Viewer/Reporting Layer
- strukturált query model
- svg/dxf/report artifactok
- sheet/placement projection

### E. Manufacturing Layer
- lead-in / lead-out szabályok
- contour-specifikus cut szabályok
- manufacturing canonical geometry
- cut plan előkészítés

### F. Postprocess Layer
- gépfüggő export
- machine-ready programok
- gyártásközeli kimenetek

A H0-ban ezekből nem mind készül el teljesen, de a **határaiknak most kell véglegesedniük**.

---

## 2. Engine mint adapterelt komponens

A nesting engine nem rendelkezzen közvetlen üzleti adatbázis-függéssel.  
Ne olvassa közvetlenül a Supabase táblákat.  
Ne írjon bele közvetlenül domainállapotba.

A helyes modell:

1. Platform létrehoz egy **run snapshotot**
2. Worker snapshot alapján készít **engine inputot**
3. Engine visszaad egy **solver outputot**
4. Platform ezt feldolgozza:
   - artifactokba
   - projection táblákba
   - metrikákba

Ez a H0 egyik legfontosabb elve.  
Ha ez most elcsúszik, később nagyon nehéz lesz a rendszert stabilan fejleszteni.

---

## 3. Belső geometriaformátum rögzítése

A H0-ban ki kell mondani:

- **DXF**: bemeneti és export formátum
- **SVG**: viewer / artifact formátum
- **canonical geometry**: belső modell

A canonical geometry legyen:
- verziózott
- JSON-alapú
- determinisztikusan előállítható
- solver- és pipeline-kompatibilis

A későbbi igények miatt már H0-ban készítsük elő, hogy egy forrásgeometriából több belső derivált is lehessen:

- `nesting_canonical`
- `manufacturing_canonical`
- `viewer_outline`

Ez még nem jelenti, hogy mind teljesen implementált is lesz H0-ban, de a modell helyét most kell kijelölni.

---

## 4. Snapshot-first futási modell

A H0-ban a következő szabály legyen kötelező:

**minden nesting run snapshotból fusson**

A snapshotnak tartalmaznia kell mindent, ami a futási eredményt érdemben befolyásolja:

- kiválasztott technológiai profilverzió
- part requirement adatok
- sheet inputok
- geometry derivative hivatkozások
- solver opciók
- placement priority / policy
- később manufacturing/postprocess kiválasztások is

Ez kell a reprodukálhatósághoz, auditálhatósághoz és a hosszú távú stabilitáshoz.

---

## 5. Viewer truth különválasztása

A H0-ban nem elég artifactokat tárolni.  
A viewer számára strukturált, query-zhető projection réteg kell.

Tehát külön kezeljük:

- **artifact**: fájl vagy blob jellegű kimenet
- **projection**: frontenden és riportban használható strukturált adatok

Ennek alapját már H0-ban ki kell építeni, különben később a frontend SVG parsingra vagy solver raw outputra fog támaszkodni, ami rossz irány.

---

## H0 domainmodell részletesen

## 1. Fő entitáscsoportok

A H0 domainmodell legalább az alábbi csoportokra bomlik:

### Identitás és projektvilág
- profiles
- projects
- project_settings

### Technológiai alapok
- technology_presets
- project_technology_setups

### Fájl és geometria
- file_objects
- geometry_revisions
- geometry_validation_reports
- geometry_review_actions
- geometry_derivatives

### Part és sheet definíciók
- part_definitions
- part_revisions
- project_part_requirements
- sheet_definitions
- sheet_revisions
- project_sheet_inputs

### Run orchestration
- nesting_runs
- nesting_run_snapshots
- run_queue
- run_logs

### Eredmény és megjelenítés
- run_artifacts
- run_layout_sheets
- run_layout_placements
- run_layout_unplaced
- run_metrics

### H0-ban már helyet előkészítünk még ezeknek is
- manufacturing_profiles
- manufacturing_profile_versions
- project_manufacturing_selection
- postprocessor_profiles
- postprocessor_profile_versions

Ezek közül a manufacturing/postprocess rész lehet kezdetben minimális, de a helye legyen meg.

---

## 2. Supabase SQL séma — H0 minimum

Az alábbi blokk a H0-E2-T1 bázismigrációhoz igazított minimum irány.
A tényleges source of truth:
`supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql`.

```sql
create extension if not exists pgcrypto;

create schema if not exists app;

-- H0-E2-T1 core enum inventory:
-- app.project_lifecycle
-- app.revision_lifecycle
-- app.file_kind
-- app.geometry_role
-- app.geometry_validation_status
-- app.geometry_derivative_kind
-- app.sheet_geometry_type
-- app.sheet_source_kind
-- app.sheet_availability_status
-- app.run_request_status
-- app.run_snapshot_status
-- app.run_attempt_status
-- app.artifact_kind
-- app.placement_policy
```

Megjegyzés:
- Ebben a fázisban csak schema + extension + enum baseline készül;
  domain táblák (`profiles`, `projects`, `run_*`) még nem.

---

## 3. Identitás és projekt táblák

```sql
create table if not exists app.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (display_name is null or length(btrim(display_name)) > 0)
);

create table if not exists app.projects (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references app.profiles(id) on delete restrict,
  name text not null,
  description text,
  lifecycle app.project_lifecycle not null default 'draft',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (length(btrim(name)) > 0)
);

create table if not exists app.project_settings (
  project_id uuid primary key references app.projects(id) on delete cascade,
  default_units text not null default 'mm',
  default_rotation_step_deg integer not null default 90,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (default_units in ('mm', 'cm', 'm', 'in')),
  check (default_rotation_step_deg > 0 and default_rotation_step_deg <= 360)
);

create index if not exists idx_projects_owner_user_id
  on app.projects(owner_user_id);

create index if not exists idx_projects_lifecycle
  on app.projects(lifecycle);
```

Megjegyzés:
- A H0-E2-T2 migráció az `updated_at` mezőkhöz minimális, `app.set_updated_at()`
  helper + trigger mintát is ad erre a három táblára.

---

## 4. Technológiai alapok

A H0-E2-T3 ota a technology domain aktualis source of truth migracioja:
`supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql`.
A bazis ketretegu: reusable preset katalogus + project-bound setup truth.

```sql
create table if not exists app.technology_presets (
  id uuid primary key default gen_random_uuid(),
  preset_code text not null unique,
  display_name text not null,
  machine_code text not null,
  material_code text not null,
  thickness_mm numeric(10,3) not null,
  kerf_mm numeric(10,3) not null,
  spacing_mm numeric(10,3) not null default 0,
  margin_mm numeric(10,3) not null default 0,
  rotation_step_deg integer not null default 90,
  allow_free_rotation boolean not null default false,
  lifecycle app.revision_lifecycle not null default 'approved',
  is_active boolean not null default true,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists app.project_technology_setups (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references app.projects(id) on delete cascade,
  preset_id uuid references app.technology_presets(id) on delete set null,
  display_name text not null,
  lifecycle app.revision_lifecycle not null default 'draft',
  is_default boolean not null default false,
  machine_code text not null,
  material_code text not null,
  thickness_mm numeric(10,3) not null,
  kerf_mm numeric(10,3) not null,
  spacing_mm numeric(10,3) not null default 0,
  margin_mm numeric(10,3) not null default 0,
  rotation_step_deg integer not null default 90,
  allow_free_rotation boolean not null default false,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_project_technology_setups_project_id
  on app.project_technology_setups(project_id);
```

Megjegyzés:
- A részletesebb machine/material/kerf lookup katalogus, illetve a full
  technology profile-version réteg későbbi H0-E2/H1 bővítésként kerül be.

---

## 5. Fájl és geometria

A H0-E3-T4 ota a files+geometry/audit/review/derivative domain aktualis source of truth migracioi:
- `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql`
- `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql`
- `supabase/migrations/20260312005000_h0_e3_t3_validation_es_review_tablak.sql`
- `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql`
Ez a lepes a file-object es geometry-revision bazis utan bevezeti az audit/review es derivative reteg tablait.

```sql
create table if not exists app.file_objects (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references app.projects(id) on delete cascade,
  storage_bucket text not null,
  storage_path text not null,
  file_name text not null,
  mime_type text,
  file_kind app.file_kind not null,
  byte_size bigint,
  sha256 text,
  uploaded_by uuid references app.profiles(id) on delete set null,
  created_at timestamptz not null default now()
);

create unique index if not exists uq_file_objects_storage_bucket_path
  on app.file_objects(storage_bucket, storage_path);

create index if not exists idx_file_objects_project_id
  on app.file_objects(project_id);

create index if not exists idx_file_objects_uploaded_by
  on app.file_objects(uploaded_by);

alter table app.file_objects
  add constraint uq_file_objects_project_id_id
  unique (project_id, id);

create table if not exists app.geometry_revisions (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references app.projects(id) on delete cascade,
  source_file_object_id uuid not null,
  geometry_role app.geometry_role not null,
  revision_no integer not null,
  status app.geometry_validation_status not null default 'uploaded',
  canonical_format_version text not null,
  canonical_geometry_jsonb jsonb,
  canonical_hash_sha256 text,
  source_hash_sha256 text,
  bbox_jsonb jsonb,
  created_by uuid references app.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (source_file_object_id, revision_no),
  check (revision_no > 0),
  check (length(btrim(canonical_format_version)) > 0)
);

create index if not exists idx_geometry_revisions_project_id
  on app.geometry_revisions(project_id);

create index if not exists idx_geometry_revisions_source_file_object_id
  on app.geometry_revisions(source_file_object_id);

create index if not exists idx_geometry_revisions_status
  on app.geometry_revisions(status);

alter table app.geometry_revisions
  add constraint fk_geometry_revisions_source_file_project
  foreign key (project_id, source_file_object_id)
  references app.file_objects(project_id, id)
  on delete restrict;

create table if not exists app.geometry_validation_reports (
  id uuid primary key default gen_random_uuid(),
  geometry_revision_id uuid not null references app.geometry_revisions(id) on delete cascade,
  validation_seq integer not null,
  status app.geometry_validation_status not null,
  validator_version text not null,
  summary_jsonb jsonb,
  report_jsonb jsonb not null,
  source_hash_sha256 text,
  created_at timestamptz not null default now(),
  unique (geometry_revision_id, validation_seq),
  check (validation_seq > 0),
  check (length(btrim(validator_version)) > 0)
);

alter table app.geometry_validation_reports
  add constraint uq_geometry_validation_reports_geometry_revision_id_id
  unique (geometry_revision_id, id);

create index if not exists idx_geometry_validation_reports_geometry_revision_id
  on app.geometry_validation_reports(geometry_revision_id);

create index if not exists idx_geometry_validation_reports_status
  on app.geometry_validation_reports(status);

create table if not exists app.geometry_review_actions (
  id uuid primary key default gen_random_uuid(),
  geometry_revision_id uuid not null references app.geometry_revisions(id) on delete cascade,
  validation_report_id uuid,
  action_kind text not null,
  actor_user_id uuid references app.profiles(id) on delete set null,
  note text,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check (action_kind in ('approve', 'reject', 'request_changes', 'comment'))
);

alter table app.geometry_review_actions
  add constraint fk_geometry_review_actions_validation_report_same_geometry
  foreign key (geometry_revision_id, validation_report_id)
  references app.geometry_validation_reports(geometry_revision_id, id)
  on delete restrict;

create index if not exists idx_geometry_review_actions_geometry_revision_id
  on app.geometry_review_actions(geometry_revision_id);

create index if not exists idx_geometry_review_actions_actor_user_id
  on app.geometry_review_actions(actor_user_id);

create index if not exists idx_geometry_review_actions_validation_report_id
  on app.geometry_review_actions(validation_report_id);

create table if not exists app.geometry_derivatives (
  id uuid primary key default gen_random_uuid(),
  geometry_revision_id uuid not null references app.geometry_revisions(id) on delete cascade,
  derivative_kind app.geometry_derivative_kind not null,
  producer_version text not null,
  format_version text not null,
  derivative_jsonb jsonb not null,
  derivative_hash_sha256 text,
  source_geometry_hash_sha256 text,
  created_at timestamptz not null default now(),
  unique (geometry_revision_id, derivative_kind),
  check (length(btrim(producer_version)) > 0),
  check (length(btrim(format_version)) > 0)
);

create index if not exists idx_geometry_derivatives_geometry_revision_id
  on app.geometry_derivatives(geometry_revision_id);

create index if not exists idx_geometry_derivatives_kind
  on app.geometry_derivatives(derivative_kind);
```

Megjegyzes:
- A geometry revision ebben a lepesben a canonical geometry truth helye.
- A geometry_validation_reports audit/report reteget, a geometry_review_actions emberi dontesi reteget ad.
- A same-geometry report-hivatkozas kompozit FK-val vedett.
- A geometry_derivatives a cel-specifikus, ujraeloallithato derivative reteg.
- A derivative kind vilag explicit: `nesting_canonical`, `manufacturing_canonical`, `viewer_outline`.
- A file object ownership tovabbra is storage-reference + metadata truth.

---

## 6. Part és sheet definíciók

A H0-E2-T4 ota a part domain aktualis source of truth migracioja:
`supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql`.

```sql
create table if not exists app.part_definitions (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references app.profiles(id) on delete restrict,
  code text not null,
  name text not null,
  description text,
  current_revision_id uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (owner_user_id, code)
);

create table if not exists app.part_revisions (
  id uuid primary key default gen_random_uuid(),
  part_definition_id uuid not null references app.part_definitions(id) on delete cascade,
  revision_no integer not null,
  lifecycle app.revision_lifecycle not null default 'draft',
  source_label text,
  source_checksum_sha256 text,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (part_definition_id, revision_no)
);

alter table app.part_revisions
  add constraint uq_part_revisions_id_definition
  unique (id, part_definition_id);

alter table app.part_definitions
  add constraint fk_part_definitions_current_revision
  foreign key (current_revision_id, id)
  references app.part_revisions(id, part_definition_id)
  on delete set null (current_revision_id)
  deferrable initially deferred;

create table if not exists app.project_part_requirements (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references app.projects(id) on delete cascade,
  part_revision_id uuid not null references app.part_revisions(id) on delete restrict,
  required_qty integer not null check (required_qty > 0),
  placement_priority smallint not null default 50,
  placement_policy app.placement_policy not null default 'normal',
  is_active boolean not null default true,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (project_id, part_revision_id)
);

create index if not exists idx_project_part_requirements_project
  on app.project_part_requirements(project_id);

create index if not exists idx_project_part_requirements_priority
  on app.project_part_requirements(project_id, placement_priority, placement_policy);

create table if not exists app.sheet_definitions (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references app.profiles(id) on delete restrict,
  code text not null,
  name text not null,
  description text,
  current_revision_id uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (owner_user_id, code)
);

create table if not exists app.sheet_revisions (
  id uuid primary key default gen_random_uuid(),
  sheet_definition_id uuid not null references app.sheet_definitions(id) on delete cascade,
  revision_no integer not null,
  lifecycle app.revision_lifecycle not null default 'draft',
  width_mm numeric(12,3) not null,
  height_mm numeric(12,3) not null,
  grain_direction text,
  source_label text,
  source_checksum_sha256 text,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (sheet_definition_id, revision_no)
);

alter table app.sheet_revisions
  add constraint uq_sheet_revisions_id_definition
  unique (id, sheet_definition_id);

alter table app.sheet_definitions
  add constraint fk_sheet_definitions_current_revision
  foreign key (current_revision_id, id)
  references app.sheet_revisions(id, sheet_definition_id)
  on delete set null (current_revision_id)
  deferrable initially deferred;

create table if not exists app.project_sheet_inputs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references app.projects(id) on delete cascade,
  sheet_revision_id uuid not null references app.sheet_revisions(id) on delete restrict,
  required_qty integer not null check (required_qty > 0),
  is_active boolean not null default true,
  is_default boolean not null default false,
  placement_priority smallint not null default 50,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (project_id, sheet_revision_id),
  check (placement_priority between 0 and 100)
);

create index if not exists idx_sheet_revisions_sheet_definition_id
  on app.sheet_revisions(sheet_definition_id);

create index if not exists idx_project_sheet_inputs_priority
  on app.project_sheet_inputs(project_id, placement_priority, is_active);
```

---

## 7. Run orchestration

A H0-E5-T1/T2 ota a run-vilag source of truth migracioi:
- `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql`
- `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql`

Fogalmi/fizikai megfeleltetes:
- Run Request aggregate -> `app.nesting_runs`
- Run Snapshot immutable truth -> `app.nesting_run_snapshots`

```sql
create table if not exists app.nesting_runs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references app.projects(id) on delete cascade,
  requested_by uuid references app.profiles(id) on delete set null,
  status app.run_request_status not null default 'draft',
  run_purpose text not null default 'nesting',
  idempotency_key text,
  request_payload_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (length(btrim(run_purpose)) > 0),
  check (idempotency_key is null or length(btrim(idempotency_key)) > 0)
);

create table if not exists app.nesting_run_snapshots (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null unique references app.nesting_runs(id) on delete cascade,
  status app.run_snapshot_status not null default 'building',
  snapshot_version text not null,
  snapshot_hash_sha256 text,
  project_manifest_jsonb jsonb not null default '{}'::jsonb,
  technology_manifest_jsonb jsonb not null default '{}'::jsonb,
  parts_manifest_jsonb jsonb not null default '[]'::jsonb,
  sheets_manifest_jsonb jsonb not null default '[]'::jsonb,
  geometry_manifest_jsonb jsonb not null default '[]'::jsonb,
  solver_config_jsonb jsonb not null default '{}'::jsonb,
  manufacturing_manifest_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check (length(btrim(snapshot_version)) > 0)
);

create index if not exists idx_nesting_runs_project_id_created_at_desc
  on app.nesting_runs(project_id, created_at desc);

create index if not exists idx_nesting_runs_status
  on app.nesting_runs(status);

create unique index if not exists uq_nesting_runs_project_idempotency_key
  on app.nesting_runs(project_id, idempotency_key)
  where idempotency_key is not null;

create unique index if not exists uq_nesting_run_snapshots_snapshot_hash_sha256
  on app.nesting_run_snapshots(snapshot_hash_sha256)
  where snapshot_hash_sha256 is not null;

create index if not exists idx_nesting_run_snapshots_status
  on app.nesting_run_snapshots(status);

create table if not exists app.run_queue (
  run_id uuid primary key references app.nesting_runs(id) on delete cascade,
  snapshot_id uuid not null unique,
  queue_state text not null default 'pending',
  attempt_no integer not null default 0,
  attempt_status app.run_attempt_status,
  priority integer not null default 100,
  available_at timestamptz not null default now(),
  leased_by text,
  lease_token uuid,
  leased_at timestamptz,
  lease_expires_at timestamptz,
  heartbeat_at timestamptz,
  started_at timestamptz,
  finished_at timestamptz,
  last_error_code text,
  last_error_message text,
  retry_count integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (queue_state in ('pending', 'leased', 'done', 'error', 'cancel_requested', 'cancelled')),
  check (attempt_no >= 0),
  check (retry_count >= 0),
  check (queue_state <> 'leased' or (lease_token is not null and lease_expires_at is not null))
);

alter table app.run_queue
  add constraint fk_run_queue_snapshot_same_run
  foreign key (run_id, snapshot_id)
  references app.nesting_run_snapshots(run_id, id)
  on delete cascade;

create index if not exists idx_run_queue_state_available_at
  on app.run_queue(queue_state, available_at);

create index if not exists idx_run_queue_lease_expires_at
  on app.run_queue(lease_expires_at);

create table if not exists app.run_logs (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references app.nesting_runs(id) on delete cascade,
  snapshot_id uuid references app.nesting_run_snapshots(id) on delete set null,
  attempt_no integer not null default 0,
  log_level text not null,
  log_kind text not null,
  message text not null,
  payload_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check (attempt_no >= 0),
  check (length(btrim(log_level)) > 0),
  check (length(btrim(log_kind)) > 0),
  check (length(btrim(message)) > 0)
);

create index if not exists idx_run_logs_run_id_created_at
  on app.run_logs(run_id, created_at);

create index if not exists idx_run_logs_snapshot_id_created_at
  on app.run_logs(snapshot_id, created_at);
```

Megjegyzes:
- A snapshot tabla append-only szemantikaju (nincs `updated_at` mezo).
- A T2-ben az attempt szemantika a `run_queue` rekordban jelenik meg (`attempt_no`, `attempt_status`), kulon `run_attempts` tabla nelkul.
- A `run_artifacts` / `run_layout_*` / `run_metrics` tablavilag H0-E5-T3 scope, kulon `run_results` tabla nelkul.

---

## 8. Artifact és projection táblák

```sql
create table if not exists app.run_artifacts (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references app.nesting_runs(id) on delete cascade,
  snapshot_id uuid references app.nesting_run_snapshots(id) on delete set null,
  artifact_kind app.artifact_kind not null,
  storage_bucket text not null,
  storage_path text not null,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check (length(btrim(storage_bucket)) > 0),
  check (length(btrim(storage_path)) > 0)
);

create index if not exists idx_run_artifacts_run
  on app.run_artifacts(run_id);

create table if not exists app.run_layout_sheets (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references app.nesting_runs(id) on delete cascade,
  sheet_index integer not null,
  sheet_revision_id uuid references app.sheet_revisions(id) on delete set null,
  width_mm numeric(12,3),
  height_mm numeric(12,3),
  utilization_ratio numeric(8,5),
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check (sheet_index >= 0),
  unique (run_id, sheet_index)
);

create index if not exists idx_run_layout_sheets_run
  on app.run_layout_sheets(run_id);

create table if not exists app.run_layout_placements (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references app.nesting_runs(id) on delete cascade,
  sheet_id uuid not null references app.run_layout_sheets(id) on delete cascade,
  placement_index integer not null,
  part_revision_id uuid references app.part_revisions(id) on delete set null,
  quantity integer not null default 1,
  transform_jsonb jsonb not null,
  bbox_jsonb jsonb not null default '{}'::jsonb,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check (placement_index >= 0),
  check (quantity > 0),
  unique (sheet_id, placement_index)
);

create index if not exists idx_run_layout_placements_sheet_id_placement_index
  on app.run_layout_placements(sheet_id, placement_index);

create index if not exists idx_run_layout_placements_run
  on app.run_layout_placements(run_id);

create table if not exists app.run_layout_unplaced (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references app.nesting_runs(id) on delete cascade,
  part_revision_id uuid references app.part_revisions(id) on delete set null,
  remaining_qty integer not null,
  reason text,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check (remaining_qty > 0)
);

create index if not exists idx_run_layout_unplaced_run
  on app.run_layout_unplaced(run_id);

create table if not exists app.run_metrics (
  run_id uuid primary key references app.nesting_runs(id) on delete cascade,
  placed_count integer not null default 0,
  unplaced_count integer not null default 0,
  used_sheet_count integer not null default 0,
  utilization_ratio numeric(8,5),
  remnant_value numeric(14,2),
  metrics_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check (placed_count >= 0),
  check (unplaced_count >= 0),
  check (used_sheet_count >= 0)
);
```

### 8.1 Storage bucket strategia es path policy (H0-E6-T1, docs-only)

- H0 kanonikus bucket inventory: `source-files`, `geometry-artifacts`, `run-artifacts`.
- `app.file_objects` -> `source-files`; `app.run_artifacts` -> `run-artifacts`.
- `geometry-artifacts` reserved bucket a jovobeli file-backed geometry artifactokhoz.
- `app.geometry_derivatives` nem storage bucket/path truth, hanem DB-ben tarolt derivalt reteg.
- Bucket/path source-of-truth dokumentum: `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md`.
- H0-E6-T1 szandekosan nem hoz migraciot, provisioning scriptet vagy RLS policyt.
- A tenyleges storage access enforcement H0-E6-T2-ben split rollouttal valosult meg:
  - `app.*` baseline RLS policyk migracios uton;
  - `storage.objects` minimal policyk manualis Dashboard/Studio provisioninggel.

### 8.2 H0-E6-T2 RLS policy alapok (migracios task)

- Repo migracio: `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql` (`app.*` baseline RLS).
- `anon` uzleti tabla-hozzaferes tiltva, policyk `authenticated` role-ra celzottak.
- `app.profiles` self-row, `app.projects` owner-only, project child tablavilag project-owner policy alatt.
- `part_*`/`sheet_*` definicio+revision vilag owner-bound policy alatt.
- `app.technology_presets` authenticated read-only.
- `nesting_run_snapshots` es `run_*` output tablavilag user-oldalon read-only.
- Hosted storage allapot:
  - bucketek: `source-files`, `geometry-artifacts`, `run-artifacts` (mind `private`);
  - `storage.objects` minimal policyk manualisan provisionalva, funkcionalis matrix szerint:
    - `source-files`: authenticated `select` + `insert`, owner/project-bound path;
    - `geometry-artifacts`: authenticated `select`, owner/project-bound;
    - `run-artifacts`: authenticated `select`, owner/project-bound;
    - `anon`: nincs policy.
- A storage rollout utja elter a sima migracios uttol: a `storage.objects` DDL/policy szegmens
  hosted owner-limit miatt splitelve maradt a repoban.
- Policynev-egyezes helyett a functionalis szabaly-egyezes az elvart.
- Security source-of-truth: `docs/web_platform/architecture/h0_security_rls_alapok.md`.

---

## 9. Manufacturing és postprocess helyének előkészítése

Még ha H0-ban nem is töltjük meg teljes üzleti logikával, a helyüket érdemes kijelölni.

```sql
create table if not exists app.manufacturing_profiles (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references app.profiles(id) on delete restrict,
  name text not null,
  description text,
  created_at timestamptz not null default now()
);

create table if not exists app.manufacturing_profile_versions (
  id uuid primary key default gen_random_uuid(),
  manufacturing_profile_id uuid not null references app.manufacturing_profiles(id) on delete cascade,
  version_no integer not null,
  machine_id uuid references app.machine_catalog(id) on delete restrict,
  material_id uuid references app.material_catalog(id) on delete restrict,
  thickness_mm numeric(10,3),
  config_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (manufacturing_profile_id, version_no)
);

create table if not exists app.project_manufacturing_selection (
  project_id uuid primary key references app.projects(id) on delete cascade,
  active_manufacturing_profile_version_id uuid not null references app.manufacturing_profile_versions(id) on delete restrict,
  selected_at timestamptz not null default now()
);

create table if not exists app.postprocessor_profiles (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references app.profiles(id) on delete restrict,
  name text not null,
  adapter_key text not null,
  created_at timestamptz not null default now()
);

create table if not exists app.postprocessor_profile_versions (
  id uuid primary key default gen_random_uuid(),
  postprocessor_profile_id uuid not null references app.postprocessor_profiles(id) on delete cascade,
  version_no integer not null,
  output_format text not null,
  settings_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (postprocessor_profile_id, version_no)
);
```

---

## H0 fejlesztési célok részletes bontásban

## H0-1 — Alap platform- és adattérkép lezárása

### Cél
A teljes platform logikai felépítésének véglegesítése.

### Deliverable
- architektúra dokumentum
- modulhatár leírás
- domainmodell leírás
- engine adapter szerződés
- artifact/projection elv dokumentálása

### DoD
- egyértelmű, mi hova tartozik
- nesting vs manufacturing vs postprocess nincs összemosva
- élő definíció vs snapshot külön van kezelve

### Kockázat, ha elmarad
A későbbi fejlesztések során a solver köré ad-hoc módon nő rá az egész rendszer.

---

## H0-2 — Supabase alapséma létrehozása

### Cél
A központi domain- és futási adattér kialakítása.

### Deliverable
- migrációk
- enumok
- alap táblák
- indexek
- updated_at triggerek
- storage bucket stratégia

### DoD
- projekt, technológia, geometria, run, artifact, projection táblák működnek
- alap relációk konzisztensen felépítve
- séma későbbi bővítésre alkalmas

### Kockázat, ha elmarad
Később nehéz lesz fájdalommentesen átállni verziózott és auditálható modellre.

---

## H0-3 — Fájlfeltöltés és storage stratégia

### Cél
A forrásfájlok és artifactok strukturált tárolásának rögzítése.

### Minimum bucket javaslat
- `source-files`
- `geometry-artifacts`
- `run-artifacts`

### Naming stratégia
- projektazonosító alapú path
- run-azonosító alapú artifact path
- tartalomhash használata, ahol indokolt

### DoD
- feltöltött DXF-ek tárolhatók
- artifactok strukturáltan menthetők
- path naming konzisztens és migrálható

---

## H0-4 — Geometry revision modell

### Cél
A nyers fájl és a jóváhagyott belső geometria közé kerüljön egy formális revíziós réteg.

### Deliverable
- `file_objects`
- `geometry_revisions`
- `geometry_validation_reports`
- `geometry_review_actions`
- `geometry_derivatives`

### DoD
- minden geometry revision visszavezethető source file-ra
- audit riport külön entitás
- derivative helye megvan
- canonical geometry verziózható

### Miért kritikus
Ha ez nincs rendesen felépítve, a későbbi normalizálás, viewer és manufacturing ág nem lesz kezelhető.

---

## H0-5 — Part és sheet domain

### Cél
A geometriát ne közvetlenül projektszinten kezeljük, hanem definíció/revízió alapon.

### Deliverable
- `part_definitions`
- `part_revisions`
- `project_part_requirements`
- `sheet_definitions`
- `sheet_revisions`
- `project_sheet_inputs`

### Kötelező döntés
Az alkatrész-prioritás nem globális part tulajdonság, hanem **projektigény-szintű** mező.

### DoD
- ugyanaz a part több projektben más prioritással használható
- ugyanaz a geometria több revízióban is kezelhető
- sheet inputok projektfüggően megadhatók

---

## H0-6 — Run orchestration és snapshot

### Cél
A futások életciklusának és reprodukálhatóságának lezárása.

### Deliverable
- `nesting_runs`
- `nesting_run_snapshots`
- `run_queue`
- `run_logs`

### Snapshot tartalom minimum
- kiválasztott technology profile version
- project part requirement lista
- sheet input lista
- geometry derivative hivatkozások
- solver config
- placement priority / policy

### DoD
- worker csak snapshotból tudjon dolgozni
- run állapotgép dokumentált
- queue lease mechanika dokumentált

---

## H0-7 — Artifact és projection réteg

### Cél
A futási eredményeket külön kezeljük fájl és strukturált nézet formában.

### Deliverable
- `run_artifacts`
- `run_layout_sheets`
- `run_layout_placements`
- `run_layout_unplaced`
- `run_metrics`

### DoD
- frontendnek nem kell solver raw outputot értelmezni
- viewer query-zhető adatokból épülhet
- dxf/svg/json artifactok külön tárolhatók

---

## H0-8 — RLS és jogosultsági alapok

### Cél
A többprojektű, többfelhasználós működés alapjainak védelme.

### Minimum elv
- a user csak a saját projektjeit lássa
- kapcsolódó entitások a projekten keresztül legyenek korlátozva
- storage objektumok is projekt-alapon védettek legyenek

### Deliverable
- RLS policy-k fő táblákra
- authenticated role támogatás
- service role használati szabály leírás

### DoD
- direkt query-vel sem látható más user projektje
- worker/service path dokumentált
- policy-k nem nyitnak túl széles hozzáférést

---

## H0-9 — Worker contract és adapter interfész

### Cél
A platform és a solver közötti szerződés rögzítése.

### Deliverable
- snapshot → engine input mapping leírás
- solver output → platform projection mapping leírás
- hibaformátum
- logformátum
- artifact naming szabályok

### DoD
- engine cserélhető vagy fejleszthető anélkül, hogy a teljes platformot át kellene írni
- input/output contract dokumentált
- raw solver output elhelyezése és normalizálása tisztázott

---

## H0-10 — Audit, observability, determinism alapok

### Cél
Már az elején támasszuk meg a rendszert.

### Minimum elemek
- snapshot hash
- source hash
- artifact metadata
- run log struktúra
- engine_version tárolás
- canonical format version tárolás

### DoD
- egy run később vizsgálható
- ugyanazon inputból ugyanazon engine-verzión reprodukálható eredmény várható
- eltérések nyomon követhetők

---

## H0 ajánlott megvalósítási sorrend

1. architektúra és domain véglegesítés  
2. Supabase enumok és alap táblák  
3. storage bucket stratégia  
4. geometry revision + derivatives modell  
5. part/sheet + project requirement modell  
6. run/snapshot/queue modell  
7. artifact/projection modell  
8. RLS policyk  
9. worker contract dokumentálás  
10. első end-to-end smoke flow

Ez a sorrend azért jó, mert előbb a szerkezet áll össze, csak utána a működés.

---

## H0 első end-to-end smoke flow

A H0 végén minimum ezt a folyamatot működésközelivé kell tenni:

1. projekt létrehozás
2. technológiai profil kiválasztás
3. DXF feltöltés
4. geometry revision létrejön
5. part revision létrejön
6. sheet input rögzítés
7. project part requirement rögzítés
8. run létrehozás
9. snapshot lefagyasztás
10. queue-ba kerül
11. worker lefuttat egy dummy vagy alap solver hívást
12. artifact mentés
13. projection táblák feltöltése
14. eredmény lekérdezhető

Nem kell még tökéletes nesting minőség.  
A cél a **platformcsatorna lezárása**.

---

## H0 technikai adósságok, amiket tilos későbbre tolni

Van pár dolog, amit H0-ban kell elintézni, mert később túl drága lesz:

- snapshot-first modell
- projection vs artifact szétválasztás
- geometry revision és derivative réteg
- technológiai profilverziózás
- part requirement projekt-szintű prioritás
- engine adapter boundary
- storage naming stratégia
- RLS alapok

Ezeket nem szabad “majd később rendbe rakjuk” alapon eltolni.

---

## H0 kimeneti dokumentumcsomag

A H0 lezárásához ideális esetben legyen:

- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md`
- `docs/web_platform/architecture/h0_security_rls_alapok.md`
- `docs/web_platform/roadmap/h0_lezarasi_kriteriumok_es_h1_entry_gate.md`
- `supabase/migrations/...`
- opcionálisan első seed fájlok machine/material cataloghoz

---

## H0 siker kritériumai

A H0 akkor tekinthető késznek, ha:

- a platform szerkezete stabil
- a fő domain táblák létrejöttek
- a projekt → geometria → part/sheet → run → artifact/projection lánc végig van vezetve
- a solver integráció helye és szerződése tiszta
- a későbbi manufacturing/postprocess bővítéshez nem kell architekturális törés
- a frontend később strukturált projectionre tud épülni
- a reprodukálhatóság alapjai készen állnak

---

## H0 utáni logikus következő szakasz

A H0 után jöhet a tényleges funkcionális mélyítés:

- geometry import/validation pipeline részletezése
- viewer/projection fejlesztés
- run orchestration élesítése
- solver integráció mélyítése
- manufacturing és cut rule modellek kibontása
- postprocessor modul konkretizálása

A H0 nem a végcél, hanem az a szint, ahol **már jó alapra építkezünk, nem improvizálunk**.
