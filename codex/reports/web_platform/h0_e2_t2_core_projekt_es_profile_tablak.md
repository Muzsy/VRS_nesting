PASS

## 1) Meta
- Task slug: `h0_e2_t2_core_projekt_es_profile_tablak`
- Kapcsolodo canvas: `canvases/web_platform/h0_e2_t2_core_projekt_es_profile_tablak.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h0_e2_t2_core_projekt_es_profile_tablak.yaml`
- Futas datuma: `2026-03-12`
- Branch / commit: `main @ e65cc33 (dirty working tree)`
- Fokusz terulet: `Schema + Docs`

## 2) Scope

### 2.1 Cel
- H0-E2-T2 migracio letrehozasa az `app.profiles`, `app.projects`, `app.project_settings` tablakkal.
- Core ownership kapcsolatok letetele (`auth.users -> profiles -> projects -> project_settings`).
- Minimal docs szinkron a `app.*` canonical iranyhoz.

### 2.2 Nem-cel
- RLS policy, auth signup provisioning trigger.
- Technology/file/revision/run/snapshot/artifact domain tablak.
- `api/sql/phase1_schema.sql` modositas.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
- `codex/codex_checklist/web_platform/h0_e2_t2_core_projekt_es_profile_tablak.md`
- `codex/reports/web_platform/h0_e2_t2_core_projekt_es_profile_tablak.md`

### 3.2 Miert valtoztak?
- A H0-E2-T1 enum baseline utan a core projekt/profil tablakep konkret schema letetele kovetkezett.
- A docsban a core tabla-blokk tobb helyen stale (`public.*`, `status` vs `lifecycle`) volt, ezt minimalisan szinkronizaltuk.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/h0_e2_t2_core_projekt_es_profile_tablak.md` -> PASS

### 4.2 Ha valami kimaradt
- Nincs kihagyott kotelezo ellenorzes.

## 5) Vegleges schema inventory (T2 scope)

### 5.1 `app.profiles` oszlopok
- `id uuid primary key references auth.users(id) on delete cascade`
- `display_name text`
- `created_at timestamptz not null default now()`
- `updated_at timestamptz not null default now()`
- `check (display_name is null or length(btrim(display_name)) > 0)`

### 5.2 `app.projects` oszlopok
- `id uuid primary key default gen_random_uuid()`
- `owner_user_id uuid not null references app.profiles(id) on delete restrict`
- `name text not null`
- `description text`
- `lifecycle app.project_lifecycle not null default 'draft'`
- `created_at timestamptz not null default now()`
- `updated_at timestamptz not null default now()`
- `check (length(btrim(name)) > 0)`

### 5.3 `app.project_settings` oszlopok
- `project_id uuid primary key references app.projects(id) on delete cascade`
- `default_units text not null default 'mm'`
- `default_rotation_step_deg integer not null default 90`
- `notes text`
- `created_at timestamptz not null default now()`
- `updated_at timestamptz not null default now()`
- `check (default_units in ('mm', 'cm', 'm', 'in'))`
- `check (default_rotation_step_deg > 0 and default_rotation_step_deg <= 360)`

### 5.4 PK/FK kapcsolatok
- PK: `profiles(id)`, `projects(id)`, `project_settings(project_id)`
- FK: `profiles.id -> auth.users(id)`
- FK: `projects.owner_user_id -> app.profiles(id)`
- FK: `project_settings.project_id -> app.projects(id)`

### 5.5 Indexek
- `idx_projects_owner_user_id on app.projects(owner_user_id)`
- `idx_projects_lifecycle on app.projects(lifecycle)`

### 5.6 Szandekosan out-of-scope maradt
- Technology/file/revision/run/snapshot/artifact tablak.
- RLS policy.
- Auth auto-provisioning (signup -> profile) workflow.

## 6) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Letrejon a `supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql` fajl. | PASS | `supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql:1` | A T2 migraciofajl letrejott. | `./scripts/verify.sh --report ...` |
| A migracio letrehozza az `app.profiles`, `app.projects`, `app.project_settings` tablakat. | PASS | `supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql:4`; `supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql:12`; `supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql:23` | Mindharom core tabla explicit letrejon. | `./scripts/verify.sh --report ...` |
| A PK/FK kapcsolatok osszhangban vannak a H0-E1 domain es ownership doksikkal. | PASS | `supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql:5`; `supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql:14`; `supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql:24` | Ownership-lanc: auth.users -> profiles -> projects -> project_settings. | `./scripts/verify.sh --report ...` |
| A migracio nem hoz letre technology/file/revision/run domain tablakat. | PASS | `supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql:66` | Explicit scope note jelzi a kizart domaineket. | `./scripts/verify.sh --report ...` |
| A task nem ad hozza RLS policyt es nem vezet be auth auto-provisioning logikat. | PASS | `supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql:67` | Explicit note, es nincs RLS/provisioning SQL. | `./scripts/verify.sh --report ...` |
| A `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md` es a `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md` minimalisan szinkronba kerul a konkret migracios irannyal. | PASS | `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md:494`; `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md:310` | A core tabla-blokkok es `app.*` irany szinkronizalva. | `./scripts/verify.sh --report ...` |
| A report DoD -> Evidence Matrix konkret fajl- es line-hivatkozasokkal kitoltott. | PASS | `codex/reports/web_platform/h0_e2_t2_core_projekt_es_profile_tablak.md:88` | A matrix kitoltve, path+line referenciakkal. | `./scripts/verify.sh --report ...` |
| `./scripts/verify.sh --report codex/reports/web_platform/h0_e2_t2_core_projekt_es_profile_tablak.md` PASS. | PASS | `codex/reports/web_platform/h0_e2_t2_core_projekt_es_profile_tablak.verify.log:1` | A gate sikeresen lefutott. | `./scripts/verify.sh --report ...` |

## 7) Advisory notes
- A migracio `app.set_updated_at()` helper functiont es 3 table-scoped triggert ad a konzisztens `updated_at` kezeleshez.
- A task szigoruan a core 3 tabla scope-ban maradt; sem technology, sem run vilag nem lett bevezetve.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-12T00:23:26+01:00 → 2026-03-12T00:26:54+01:00 (208s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h0_e2_t2_core_projekt_es_profile_tablak.verify.log`
- git: `main@e65cc33`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 ...ing_platform_architektura_es_supabase_schema.md | 65 +++++++++++-----------
 .../roadmap/dxf_nesting_platform_h0_reszletes.md   | 25 +++++++--
 2 files changed, 53 insertions(+), 37 deletions(-)
```

**git status --porcelain (preview)**

```text
 M docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md
 M docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md
?? canvases/web_platform/h0_e2_t2_core_projekt_es_profile_tablak.md
?? codex/codex_checklist/web_platform/h0_e2_t2_core_projekt_es_profile_tablak.md
?? codex/goals/canvases/web_platform/fill_canvas_h0_e2_t2_core_projekt_es_profile_tablak.yaml
?? codex/prompts/web_platform/h0_e2_t2_core_projekt_es_profile_tablak/
?? codex/reports/web_platform/h0_e2_t2_core_projekt_es_profile_tablak.md
?? codex/reports/web_platform/h0_e2_t2_core_projekt_es_profile_tablak.verify.log
?? supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql
```

<!-- AUTO_VERIFY_END -->
