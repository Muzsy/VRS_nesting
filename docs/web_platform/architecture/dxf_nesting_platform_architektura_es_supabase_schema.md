# DXF Nesting alkalmazás – architektúra, folyamat, technológiai modell, roadmap és javasolt Supabase SQL séma

## 1. Dokumentum célja

Ez a dokumentum egy egységesített, kibővített tervezési alap a DXF Nesting alkalmazáshoz.  
A cél nem egy „webapp, ami néha meghív egy nestert”, hanem egy **workflow-platform**, amelyben a nesting engine egy **szerződésvezérelt számítási modul**.

A dokumentum összefoglalja:

- a rendszer architekturális alapelveit,
- a moduláris felépítést,
- az end-to-end folyamatot,
- a technológiai és gyártási rétegek szétválasztását,
- a fejlesztési roadmap-et,
- valamint egy **konkrét, Supabase/PostgreSQL alapú, tábla- és mezőszintű javasolt sémát**.

Modulhatar es ownership szerzodes source-of-truth:
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
Domain entitas- es aggregate ownership source-of-truth:
- `docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md`
Snapshot-first futasi es adatkontraktus source-of-truth:
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`

Ez a dokumentum az architekturalis kontextust adja; a konkret boundary donteseket a fenti hivatkozas rogziti normativan.

## 2. Vezérelvek

### 2.1 A nesting engine ne legyen maga a teljes rendszer
A jelenlegi repo és a korábbi auditok alapján a nesting engine már nem alapkutatási fázisban van, hanem stabilizált számítási magként kezelhető. Emiatt a következő nagy munka nem az „alap matematika”, hanem a köré épített platform: projekt, technológia, DXF ingest, audit, snapshot, queue, artifact, viewer, export.

### 2.2 Definíció, használat, snapshot és artifact ne keveredjen
Ez a legfontosabb adatmodellezési szabály.

Példák:

- a part definíció nem ugyanaz, mint a part adott revíziója,
- a projektbeli darabszámigény nem ugyanaz, mint maga az alkatrész,
- a technológiai profil nem ugyanaz, mint az adott futásba befagyasztott snapshot,
- a solver output nem ugyanaz, mint a UI által query-zhető projection,
- a viewer SVG nem ugyanaz, mint a rendszer source of truth-ja.

### 2.3 A worker csak snapshotból dolgozzon
A worker ne élő üzleti táblákból „okoskodjon”, hanem kizárólag run snapshotból dolgozzon.  
Ez biztosítja a reprodukálhatóságot, auditálhatóságot és a későbbi újrafuttathatóságot.

### 2.4 A belső geometria ne DXF és ne SVG legyen
A helyes modell:

- **DXF** = forrás- és exportformátum,
- **SVG** = viewer / preview artifact,
- **belső geometria** = verziózott, kanonikus JSON-alapú reprezentáció.

### 2.5 Két belső geometriai derivált kell
A rendszer hosszabb távon két eltérő célú belső geometriai deriváltat igényel:

- **nesting_canonical**: polygonizált, determinisztikus, solver-barát,
- **manufacturing_canonical**: gyártásközelibb, lead-in/lead-out és gépfüggő export felé alkalmas.

### 2.6 A nesting, a gyártási szabályrendszer és a gépfüggő export külön modul maradjon
A solver ne tudjon gépspecifikus kimenetet.  
A helyes lánc:

1. normalizált input
2. nesting
3. univerzális placement eredmény
4. manufacturing szabályok alkalmazása
5. postprocess / export adapter
6. gépspecifikus kimenet

## 3. Javasolt moduláris felépítés

## 3.1 Project & Identity modul
Feladat:

- felhasználó, profil, projekt
- projekt státusz
- projekt szintű beállítások
- UI és workflow preference-ek

Fő entitások:

- profiles
- projects
- project_settings

## 3.2 Technology modul
Feladat:

- reusable technology preset katalogus
- projekt-szintu technology setup truth
- kerf/spacing/margin/rotation policy alapbeallitasok
- preset -> project setup kapcsolat

Fő entitások:

- technology_presets
- project_technology_setups

## 3.3 Manufacturing modul
Feladat:

- gyártási szabályrendszer
- lead-in / lead-out
- contour policy
- cut order, pierce, entry policy
- postprocess kapcsolat

Fő entitások:

- manufacturing_profiles
- manufacturing_profile_versions
- project_manufacturing_selection
- cut_rule_sets
- cut_contour_rules
- postprocessor_profiles
- postprocessor_profile_versions

## 3.4 Files & Geometry modul
Feladat:

- nyers feltöltött fájlok
- normalizált geometria
- geometry audit
- review queue
- derivált geometriai reprezentációk

Fő entitások:

- file_objects
- geometry_revisions
- geometry_derivatives
- geometry_validation_reports
- geometry_review_actions

## 3.5 Parts modul
Feladat:

- alkatrész definíció
- revíziók
- projektbeli darabszámigény
- placement priority

Fő entitások:

- part_definitions
- part_revisions
- project_part_requirements

## 3.6 Sheets modul
Feladat:

- kézi téglalap tábla
- DXF alapú alakos tábla
- szabványméret katalógus
- projektben bevont táblák
- sheet prioritás / cost hint

Fő entitások:

- sheet_definitions
- sheet_revisions
- standard_sheet_catalog
- project_sheet_inputs

## 3.7 Run Orchestration modul
Feladat:

- nesting run törzs
- befagyasztott run snapshot
- queue
- logok
- státuszkezelés
- artifact manifest

Fő entitások:

- nesting_runs
- nesting_run_snapshots
- run_queue
- run_logs
- run_artifacts

## 3.8 Results / Viewer / Export modul
Feladat:

- query-zhető UI projection
- structured layout data
- viewer overlay
- report és letölthető bundle
- machine-ready export artifactok

Fő entitások:

- run_layout_sheets
- run_layout_placements
- run_layout_unplaced
- run_metrics

## 3.9 Későbbi külön modulok
Tudatosan későbbre hagyandó:

- Inventory / stock / remnants
- Composite / mini-nest blocks
- szervezeti / RBAC mélyítés
- audit trail és abuse/quota mélyítés

## 4. End-to-end folyamat

## 4.1 Projekt létrehozás
A felhasználó létrehoz egy projektet.  
A projekt a teljes workflow fő konténere.

## 4.2 Technológiai kiválasztás
A projekthez kiválasztásra kerül egy aktív `technology_profile_version`.

Ebben van:

- machine
- material
- thickness
- spacing
- margin
- kerf source
- effective kerf
- allowed rotations
- default time limit

## 4.3 Gyártási profil kiválasztás
A projekthez kiválasztásra kerül egy aktív `manufacturing_profile_version`.

Ebben van:

- outer és inner contour rule set
- cut order policy
- entry point policy
- pierce strategy
- kapcsolt postprocessor profil verzió

## 4.4 Fájl feltöltés
A nyers DXF fájl storage-ba kerül, metaadata a `file_objects` táblába.

## 4.5 Geometria normalizálás és audit
A feltöltött DXF-ből létrejön egy `geometry_revision`, majd abból derivált reprezentációk:

- `nesting_canonical`
- `manufacturing_canonical`
- opcionálisan `viewer_outline`

Ezután külön audit pipeline fut:

- issue detektálás
- severity / confidence
- auto-fix
- review queue

## 4.6 Part és sheet revíziók képzése
A validált geometria alapján:

- part_definition + part_revision
- sheet_definition + sheet_revision

## 4.7 Projektigény rögzítése
A projekt megmondja:

- mely partból mennyi kell,
- milyen placement priority-val,
- mely táblákból mennyi áll rendelkezésre,
- milyen prioritással / cost hinttel.

## 4.8 Run snapshot fagyasztás
Run indításkor a rendszer nem élő üzleti állapotból dolgozik, hanem befagyasztja:

- part requirement snapshot
- sheet input snapshot
- technology snapshot
- manufacturing snapshot
- geometry snapshot
- engine input contract szerinti payload

## 4.9 Queue + worker futás
A worker:

- snapshotot vesz át
- engine adapterként fut
- artifactokat állít elő
- UI projection táblákat tölt
- státuszt ír vissza

## 4.10 Eredmény és export
Az eredmény több rétegben él:

- nyers artifactok
- query-zhető projection táblák
- viewer SVG
- DXF export
- ZIP bundle
- később machine-ready export

## 5. Kritikus technológiai döntések

## 5.1 Alkatrész-prioritás a nestingben
A prioritást nem a part definícióra, hanem a projektbeli igényre kell tenni.

Ezért a kulcstábla:
- `project_part_requirements`

Javasolt mezők:
- `placement_priority`
- `placement_policy`

Ajánlott jelentés:

- `hard_first`: előrehozott placement, akár optimalizációs ár árán is
- `soft_prefer`: rendezési előny, de nem kényszer
- `normal`: normál
- `defer`: később próbáljuk

Fontos:
**placement order priority != final run scoring**

## 5.2 Lead-in / lead-out
A ráfutás/kifutás nem a nesting alapgeometria része.  
Ez gyártási szabályrendszer.

Ezért:

- ne torzítsa el a solver geometriát,
- contour rule setből jöjjön,
- outer és inner contour külön szabályozható legyen,
- gép + anyag + vastagság függő legyen.

## 5.3 Gépfüggő postprocessor
A nesting engine univerzális placement eredményt adjon.  
A gépfüggő kimenet külön adapterrétegben keletkezzen.

## 5.4 Viewer source of truth
A viewer ne kizárólag SVG-t olvasson.  
A valódi source of truth a strukturált projection réteg:

- run_layout_sheets
- run_layout_placements
- run_layout_unplaced
- run_metrics

Az SVG csak render artifact.

## 6. Fejlesztési roadmap

## 6.1 Fázis A – Contract + Domain Freeze
Cél:

- normalized geometry contract
- run input contract
- run output contract
- run snapshot contract
- artifact taxonomy
- viewer contract

Ezt előbb kell lezárni, mint a képernyőket.

## 6.2 Fázis B – Core platform v1
Cél:

- profiles
- projects
- project_settings
- technology domain
- rect sheets
- part requirements
- run wrapper
- queue
- artifact mentés

Ez az első használható rendszer.

## 6.3 Fázis C – DXF ingest + audit + normalized parts
Cél:

- DXF upload
- parse
- normalize
- audit
- review queue
- geometry revisions
- part revisions

Ez a kritikus korai modul.

## 6.4 Fázis D – Standard sheet catalog + irregular sheets
Cél:

- standard catalog
- DXF alapú alakos táblák
- közös sheet domain
- egységes project_sheet_inputs

## 6.5 Fázis E – Viewer + export + reporting
Cél:

- per-sheet SVG viewer
- structured overlay
- report projection
- ZIP bundle
- export manifest

## 6.6 Fázis F – Manufacturing rules + postprocess
Cél:

- manufacturing profile verziózás
- cut rule setek
- lead-in / lead-out
- postprocessor adapter
- machine-ready artifactok

## 6.7 Fázis G – Inventory / remnants
Cél:

- stock transactions
- remnant életciklus
- reservations
- inbound/outbound mozgások

## 6.8 Fázis H – Composite / mini-nest
Cél:

- placeable unit általánosítás
- composite definíciók
- blokk geometria
- editor

## 7. SQL tervezési alapelvek

## 7.1 Supabase kompatibilitás
A séma PostgreSQL / Supabase kompatibilis.  
A `profiles.id` az `auth.users(id)`-re mutat.

## 7.2 UUID alapú kulcsok
Minden üzleti entitás UUID primary key-t kap.

## 7.3 Verziózás
A „profile”, „revision”, „snapshot”, „artifact” típusú entitások külön táblában élnek.

## 7.4 JSONB használat
JSONB csak ott legyen, ahol valóban félig strukturált mező kell:

- geometry_jsonb
- bbox_jsonb
- issues_jsonb
- fixes_applied_jsonb
- settings_jsonb
- snapshot_jsonb
- metrics_jsonb
- meta_jsonb

## 7.5 Enumok
Supabase/Postgres oldalon érdemes explicit enumokkal dolgozni, mert ettől a séma olvashatóbb és konzisztens lesz.

---

# 8. Javasolt Supabase SQL séma

## 8.1 Extensions és enumok

A H0-E2-T1 óta a tényleges schema source of truth a
`supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql`.
Az alábbi blokk a bázis migráció irányát rögzíti (nem teljes táblaséma).

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

## 8.2 Identity és Project Core

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

## 8.3 Technology Domain

A H0-E2-T3 ota a technology domain aktualis source of truth migracioja:
`supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql`.
Ez a bazis ketretegu: reusable preset katalogus + projekt-szintu setup truth.

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

create unique index if not exists uq_project_technology_setups_default_per_project
  on app.project_technology_setups(project_id)
  where is_default;
```

Megjegyzes:
- A reszletesebb technology katalogus (`machine_catalog`, `material_catalog`,
  `kerf_lookup_rules`) es a teljes profile-version reteg kesobbi H0-E2/H1 bovites.

## 8.4 Manufacturing Domain

```sql
create table if not exists public.postprocessor_profiles (
  id uuid primary key default gen_random_uuid(),
  machine_id uuid not null references public.machine_catalog(id),
  name text not null,
  adapter_key text not null,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  unique (machine_id, name)
);

create table if not exists public.postprocessor_profile_versions (
  id uuid primary key default gen_random_uuid(),
  postprocessor_profile_id uuid not null references public.postprocessor_profiles(id) on delete cascade,
  version_no integer not null,
  output_format postprocess_output_format not null,
  settings_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (postprocessor_profile_id, version_no)
);

create table if not exists public.cut_rule_sets (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  machine_id uuid not null references public.machine_catalog(id),
  material_id uuid not null references public.material_catalog(id),
  thickness_mm numeric(10,3) not null,
  version_no integer not null default 1,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  check (thickness_mm > 0)
);

create index if not exists idx_cut_rule_sets_match
  on public.cut_rule_sets(machine_id, material_id, thickness_mm);

create table if not exists public.cut_contour_rules (
  id uuid primary key default gen_random_uuid(),
  cut_rule_set_id uuid not null references public.cut_rule_sets(id) on delete cascade,
  contour_kind contour_kind_type not null,
  feature_class feature_class_type not null default 'default',
  lead_in_type lead_type not null default 'none',
  lead_in_length_mm numeric(10,3),
  lead_in_radius_mm numeric(10,3),
  lead_out_type lead_type not null default 'none',
  lead_out_length_mm numeric(10,3),
  lead_out_radius_mm numeric(10,3),
  entry_side_policy entry_side_policy_type not null default 'auto',
  min_contour_length_mm numeric(10,3),
  max_contour_length_mm numeric(10,3),
  enabled boolean not null default true,
  created_at timestamptz not null default now(),
  check (lead_in_length_mm is null or lead_in_length_mm >= 0),
  check (lead_in_radius_mm is null or lead_in_radius_mm >= 0),
  check (lead_out_length_mm is null or lead_out_length_mm >= 0),
  check (lead_out_radius_mm is null or lead_out_radius_mm >= 0),
  check (min_contour_length_mm is null or min_contour_length_mm >= 0),
  check (max_contour_length_mm is null or max_contour_length_mm >= 0)
);

create table if not exists public.manufacturing_profiles (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references app.projects(id) on delete cascade,
  name text not null,
  is_default boolean not null default false,
  created_at timestamptz not null default now(),
  unique (project_id, name)
);

create table if not exists public.manufacturing_profile_versions (
  id uuid primary key default gen_random_uuid(),
  manufacturing_profile_id uuid not null references public.manufacturing_profiles(id) on delete cascade,
  version_no integer not null,
  machine_id uuid not null references public.machine_catalog(id),
  material_id uuid not null references public.material_catalog(id),
  thickness_mm numeric(10,3) not null,
  outer_cut_rule_set_id uuid references public.cut_rule_sets(id),
  inner_cut_rule_set_id uuid references public.cut_rule_sets(id),
  pierce_strategy_jsonb jsonb not null default '{}'::jsonb,
  cut_order_policy_jsonb jsonb not null default '{}'::jsonb,
  entry_point_policy_jsonb jsonb not null default '{}'::jsonb,
  postprocessor_profile_version_id uuid references public.postprocessor_profile_versions(id),
  notes text,
  created_at timestamptz not null default now(),
  unique (manufacturing_profile_id, version_no),
  check (thickness_mm > 0)
);

create table if not exists public.project_manufacturing_selection (
  project_id uuid primary key references app.projects(id) on delete cascade,
  active_manufacturing_profile_version_id uuid not null references public.manufacturing_profile_versions(id),
  selected_at timestamptz not null default now(),
  selected_by uuid references app.profiles(id)
);
```

## 8.5 Files & Geometry Domain

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
  created_at timestamptz not null default now(),
  unique (storage_bucket, storage_path),
  check (length(btrim(storage_bucket)) > 0),
  check (length(btrim(storage_path)) > 0),
  check (length(btrim(file_name)) > 0),
  check (byte_size is null or byte_size >= 0)
);

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

## 8.6 Part Domain

A H0-E2-T4 ota a part domain aktualis source of truth migracioja:
`supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql`.
Ez a bazis expliciten kuloniti a definition / revision / demand retegeket.

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
  required_qty integer not null,
  placement_priority smallint not null default 50 check (placement_priority between 0 and 100),
  placement_policy app.placement_policy not null default 'normal',
  is_active boolean not null default true,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (project_id, part_revision_id),
  check (required_qty > 0)
);

create index if not exists idx_part_revisions_part_definition_id
  on app.part_revisions(part_definition_id);

create index if not exists idx_project_part_requirements_priority
  on app.project_part_requirements(project_id, placement_priority, placement_policy);
```

## 8.7 Sheet Domain

A H0-E2-T5 ota a sheet domain aktualis source of truth migracioja:
`supabase/migrations/20260310240000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql`.
Ez a bazis expliciten kuloniti a definition / revision / project-input retegeket.

```sql
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
  required_qty integer not null,
  is_active boolean not null default true,
  is_default boolean not null default false,
  placement_priority smallint not null default 50,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (project_id, sheet_revision_id),
  check (required_qty > 0),
  check (placement_priority between 0 and 100)
);

create index if not exists idx_sheet_revisions_sheet_definition_id
  on app.sheet_revisions(sheet_definition_id);

create index if not exists idx_project_sheet_inputs_priority
  on app.project_sheet_inputs(project_id, placement_priority, is_active);
```

## 8.8 Runs, Snapshots, Queue, Logs (H0-E5-T1/T2 source of truth)

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
  check (length(btrim(run_purpose)) > 0)
);

create index if not exists idx_nesting_runs_project_id_created_at_desc
  on app.nesting_runs(project_id, created_at desc);

create index if not exists idx_nesting_runs_status
  on app.nesting_runs(status);

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
- A result/artifact/projection tablavilag kulon H0-E5-T3 taskban jon.

## 8.9 Results / Viewer Projection

```sql
create table if not exists public.run_layout_sheets (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references app.nesting_runs(id) on delete cascade,
  sheet_no integer not null,
  sheet_definition_id uuid references app.sheet_definitions(id),
  sheet_revision_id uuid references app.sheet_revisions(id),
  width_mm numeric(12,3),
  height_mm numeric(12,3),
  utilization_ratio numeric(8,6),
  remnant_area_mm2 numeric(18,3),
  remnant_value numeric(18,4),
  bbox_jsonb jsonb,
  meta_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (run_id, sheet_no)
);

create table if not exists public.run_layout_placements (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references app.nesting_runs(id) on delete cascade,
  run_layout_sheet_id uuid not null references public.run_layout_sheets(id) on delete cascade,
  stable_placement_key text not null,
  part_definition_id uuid references app.part_definitions(id),
  part_revision_id uuid references app.part_revisions(id),
  project_part_requirement_id uuid references app.project_part_requirements(id),
  placement_index integer not null,
  x_mm numeric(18,6) not null,
  y_mm numeric(18,6) not null,
  rotation_deg numeric(10,4) not null default 0,
  mirrored boolean not null default false,
  bbox_jsonb jsonb,
  centroid_jsonb jsonb,
  meta_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (run_id, stable_placement_key)
);

create index if not exists idx_run_layout_placements_run_sheet
  on public.run_layout_placements(run_layout_sheet_id, placement_index);

create table if not exists public.run_layout_unplaced (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references app.nesting_runs(id) on delete cascade,
  part_definition_id uuid references app.part_definitions(id),
  part_revision_id uuid references app.part_revisions(id),
  project_part_requirement_id uuid references app.project_part_requirements(id),
  missing_qty integer not null default 1,
  reason text,
  meta_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check (missing_qty > 0)
);

create table if not exists public.run_metrics (
  run_id uuid primary key references app.nesting_runs(id) on delete cascade,
  placed_count integer not null default 0,
  unplaced_count integer not null default 0,
  sheet_count integer not null default 0,
  total_part_area_mm2 numeric(18,3),
  total_sheet_area_mm2 numeric(18,3),
  global_utilization_ratio numeric(8,6),
  total_remnant_area_mm2 numeric(18,3),
  total_remnant_value numeric(18,4),
  solver_runtime_ms bigint,
  metrics_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
```

## 8.10 Opcionális segédfüggvények és updated_at trigger

```sql
create or replace function app.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_profiles_set_updated_at on app.profiles;
create trigger trg_profiles_set_updated_at
before update on app.profiles
for each row execute function app.set_updated_at();

drop trigger if exists trg_projects_set_updated_at on app.projects;
create trigger trg_projects_set_updated_at
before update on app.projects
for each row execute function app.set_updated_at();

drop trigger if exists trg_project_settings_set_updated_at on app.project_settings;
create trigger trg_project_settings_set_updated_at
before update on app.project_settings
for each row execute function app.set_updated_at();
```

---

# 9. Minimális RLS irány

Ez itt még nem teljes policy-csomag, de a modell alap logikája:

- minden projecthez kapcsolódó üzleti adat `projects.owner_user_id` alapján szűrhető,
- storage objektumok is projekt-alapú tulajdonosi logikára épüljenek,
- worker szolgáltatás külön service role-lal írja:
  - run_queue
  - run_logs
  - run_artifacts
  - run_layout_*
  - run_metrics

Ajánlott mintázat:

1. felhasználói oldal csak a saját projectjeit látja,
2. projekt alatti összes child tábla parent projecthez kötött policy-vel olvasható,
3. worker csak service role-ból ír,
4. public anon hozzáférés nincs üzleti táblákra.

---

# 10. Mi kerüljön V1-be, V1.5-be és későbbre

## 10.1 V1 – azonnal érdemes bevezetni
- profiles
- projects
- project_settings
- technology_presets
- project_technology_setups
- file_objects
- geometry_revisions
- geometry_validation_reports
- geometry_review_actions
- part_definitions
- part_revisions
- project_part_requirements
- sheet_definitions
- sheet_revisions
- project_sheet_inputs
- nesting_runs
- nesting_run_snapshots
- run_queue
- run_logs
- run_artifacts
- run_layout_sheets
- run_layout_placements
- run_layout_unplaced
- run_metrics

## 10.2 V1.5 – nagyon korai bővítés
- geometry_derivatives
- manufacturing_profiles
- manufacturing_profile_versions
- project_manufacturing_selection
- standard_sheet_catalog

## 10.3 V2
- cut_rule_sets
- cut_contour_rules
- postprocessor_profiles
- postprocessor_profile_versions
- machine-ready export artifactok
- bővített viewer meta és reporting

## 10.4 V3+
- inventory_lots
- inventory_movements
- remnant_items
- reservation_locks
- composite_definitions
- composite_definition_items
- composite_geometry_revisions
- RBAC / team / org mélyítés
- quota / abuse prevention
- teljes audit trail

---

# 11. Javasolt implementációs sorrend

## 11.1 Első kör
- contract freeze
- DB schema v1
- auth + projects
- basic storage
- run wrapper
- basic artifact mentés

## 11.2 Második kör
- DXF ingest
- geometry normalization
- validation
- review queue
- part lifecycle

## 11.3 Harmadik kör
- sheet lifecycle
- standard catalog
- irregular sheets
- structured viewer projection

## 11.4 Negyedik kör
- manufacturing domain
- contour rules
- lead-in / lead-out
- postprocessor adapter

## 11.5 Ötödik kör
- inventory és remnants
- composite / mini-nest
- advanced planning

---

# 12. Nyitott kérdések

1. A manufacturing_canonical geometria mennyire őrizze meg az eredeti ív/spline információt?
2. A postprocessor adapterek egy közös belső cut-plan formátumra épüljenek-e?
3. A part priority legyen-e csak rendezési súly, vagy opcionálisan kötelező placement policy?
4. A run snapshot hash része legyen-e a geometry derivative hash is?  
   Igen, javasolt.
5. A standard sheet catalog projektfüggetlen globális törzs legyen-e?  
   Igen, javasolt.
6. A remnant value modell mikor lépjen át külön inventory domainbe?  
   Amint a maradék nemcsak run eredmény, hanem újrafelhasználható készlet is lesz.

---

# 13. Tömör végkövetkeztetés

A helyes irány nem az, hogy gyorsan felkerül pár Supabase tábla, hanem az, hogy már az elején domain-alapon különválasztjuk:

- projekt,
- technológia,
- gyártási szabályrendszer,
- nyers fájl,
- normalizált geometria,
- geometriai derivált,
- alkatrész-definíció,
- tábla-definíció,
- projekt-specifikus igény,
- run snapshot,
- artifact,
- viewer/report projection.

Ha ez most tisztán le van rakva, akkor a későbbi inventory, remnants, composite és machine export modulok nem szétverik a rendszert, hanem szabályosan ráépülnek.

---

# 14. Forrásalap

A dokumentum az alábbi projektanyagok és beszélgetések szintézise alapján készült:

- VRS Nesting – Felhős Web Platform Specifikáció
- VRS Nesting Web Platform Implementációs Útmutató
- ChatGPT – DXF Nesting alkalmazás beszélgetés
- DXF Nesting alkalmazás – Repo áttekintés és fázis 3 beszélgetés

A mostani verzió ezekből kiindulva már egy továbbfejlesztett, egységesített architekturális és adatmodellezési javaslatot ad.
