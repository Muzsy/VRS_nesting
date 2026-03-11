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

create unique index if not exists idx_file_objects_bucket_path
  on app.file_objects(storage_bucket, storage_path);

create table if not exists app.geometry_revisions (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references app.projects(id) on delete cascade,
  source_file_object_id uuid not null references app.file_objects(id) on delete restrict,
  canonical_format_version text not null,
  geometry_jsonb jsonb not null,
  bbox_jsonb jsonb not null default '{}'::jsonb,
  area_mm2 numeric(18,4),
  perimeter_mm numeric(18,4),
  status app.geometry_status not null default 'uploaded',
  source_hash text,
  created_by uuid references app.profiles(id) on delete set null,
  created_at timestamptz not null default now()
);

create index if not exists idx_geometry_revisions_project
  on app.geometry_revisions(project_id);

create table if not exists app.geometry_validation_reports (
  id uuid primary key default gen_random_uuid(),
  geometry_revision_id uuid not null references app.geometry_revisions(id) on delete cascade,
  report_jsonb jsonb not null,
  severity_summary_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists app.geometry_review_actions (
  id uuid primary key default gen_random_uuid(),
  geometry_revision_id uuid not null references app.geometry_revisions(id) on delete cascade,
  action_type text not null,
  action_notes text,
  created_by uuid references app.profiles(id) on delete set null,
  created_at timestamptz not null default now()
);

create table if not exists app.geometry_derivatives (
  id uuid primary key default gen_random_uuid(),
  geometry_revision_id uuid not null references app.geometry_revisions(id) on delete cascade,
  derivative_kind app.derivative_kind not null,
  format_version text not null,
  geometry_jsonb jsonb not null,
  bbox_jsonb jsonb not null default '{}'::jsonb,
  area_mm2 numeric(18,4),
  source_hash text,
  created_at timestamptz not null default now(),
  unique (geometry_revision_id, derivative_kind, format_version)
);
```

---

## 6. Part és sheet definíciók

```sql
create table if not exists app.part_definitions (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references app.profiles(id) on delete restrict,
  code text not null,
  name text not null,
  description text,
  created_at timestamptz not null default now(),
  unique (owner_user_id, code)
);

create table if not exists app.part_revisions (
  id uuid primary key default gen_random_uuid(),
  part_definition_id uuid not null references app.part_definitions(id) on delete cascade,
  revision_no integer not null,
  geometry_revision_id uuid not null references app.geometry_revisions(id) on delete restrict,
  approved_nesting_derivative_id uuid references app.geometry_derivatives(id) on delete restrict,
  approved_manufacturing_derivative_id uuid references app.geometry_derivatives(id) on delete restrict,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (part_definition_id, revision_no)
);

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
  unique (project_id, part_revision_id)
);

create index if not exists idx_project_part_requirements_project
  on app.project_part_requirements(project_id);

create table if not exists app.sheet_definitions (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references app.profiles(id) on delete restrict,
  code text not null,
  name text not null,
  created_at timestamptz not null default now(),
  unique (owner_user_id, code)
);

create table if not exists app.sheet_revisions (
  id uuid primary key default gen_random_uuid(),
  sheet_definition_id uuid not null references app.sheet_definitions(id) on delete cascade,
  revision_no integer not null,
  width_mm numeric(12,3) not null,
  height_mm numeric(12,3) not null,
  usable_geometry_jsonb jsonb,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (sheet_definition_id, revision_no)
);

create table if not exists app.project_sheet_inputs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references app.projects(id) on delete cascade,
  sheet_revision_id uuid not null references app.sheet_revisions(id) on delete restrict,
  quantity integer not null check (quantity > 0),
  priority smallint not null default 50,
  cost_hint numeric(14,2),
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);
```

---

## 7. Run orchestration

```sql
create table if not exists app.nesting_runs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references app.projects(id) on delete cascade,
  requested_by uuid references app.profiles(id) on delete set null,
  status app.run_status not null default 'draft',
  engine_version text,
  started_at timestamptz,
  finished_at timestamptz,
  error_message text,
  created_at timestamptz not null default now()
);

create table if not exists app.nesting_run_snapshots (
  run_id uuid primary key references app.nesting_runs(id) on delete cascade,
  snapshot_jsonb jsonb not null,
  snapshot_hash text not null,
  created_at timestamptz not null default now()
);

create unique index if not exists idx_nesting_run_snapshots_hash
  on app.nesting_run_snapshots(snapshot_hash);

create table if not exists app.run_queue (
  run_id uuid primary key references app.nesting_runs(id) on delete cascade,
  status app.queue_status not null default 'pending',
  lease_token uuid,
  leased_until timestamptz,
  worker_id text,
  retry_count integer not null default 0,
  available_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create index if not exists idx_run_queue_status_available
  on app.run_queue(status, available_at);

create table if not exists app.run_logs (
  id bigint generated always as identity primary key,
  run_id uuid not null references app.nesting_runs(id) on delete cascade,
  level text not null,
  message text not null,
  payload_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
```

---

## 8. Artifact és projection táblák

```sql
create table if not exists app.run_artifacts (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references app.nesting_runs(id) on delete cascade,
  artifact_kind app.artifact_kind not null,
  storage_bucket text not null,
  storage_path text not null,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
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
  unique (run_id, sheet_index)
);

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
  unique (sheet_id, placement_index)
);

create table if not exists app.run_layout_unplaced (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references app.nesting_runs(id) on delete cascade,
  part_revision_id uuid references app.part_revisions(id) on delete set null,
  remaining_qty integer not null,
  reason text,
  metadata_jsonb jsonb not null default '{}'::jsonb
);

create table if not exists app.run_metrics (
  run_id uuid primary key references app.nesting_runs(id) on delete cascade,
  placed_count integer not null default 0,
  unplaced_count integer not null default 0,
  used_sheet_count integer not null default 0,
  utilization_ratio numeric(8,5),
  remnant_value numeric(14,2),
  metrics_jsonb jsonb not null default '{}'::jsonb
);
```

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

- `docs/platform/h0_architecture.md`
- `docs/platform/h0_domain_model.md`
- `docs/platform/h0_run_contract.md`
- `docs/platform/h0_storage_and_artifacts.md`
- `docs/platform/h0_security_rls.md`
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
