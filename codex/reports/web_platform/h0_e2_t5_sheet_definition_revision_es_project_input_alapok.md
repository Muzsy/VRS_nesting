PASS

## 1) Meta
- Task slug: `h0_e2_t5_sheet_definition_revision_es_project_input_alapok`
- Kapcsolodo canvas: `canvases/web_platform/h0_e2_t5_sheet_definition_revision_es_project_input_alapok.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.yaml`
- Futas datuma: `2026-03-12`
- Branch / commit: `main @ 9b43d02 (dirty working tree)`
- Fokusz terulet: `Schema + Docs`

## 2) Scope

### 2.1 Cel
- H0-E2-T5 migracio letrehozasa a `sheet_definitions`, `sheet_revisions`, `project_sheet_inputs` tablavilaghoz.
- Definition / revision / project input vilag explicit szeparacioja.
- Project input kapcsolasa a revision vilaghoz (nem definitionhoz).
- `current_revision_id` ownership integritas relacios vedelme.

### 2.2 Nem-cel
- Remnant/inventory/file/geometry/run/export domain tablak.
- RLS policy.
- `api/sql/phase1_schema.sql` modositas.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `supabase/migrations/20260311000000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
- `codex/codex_checklist/web_platform/h0_e2_t5_sheet_definition_revision_es_project_input_alapok.md`
- `codex/reports/web_platform/h0_e2_t5_sheet_definition_revision_es_project_input_alapok.md`

### 3.2 Miert valtoztak?
- A part-domain bazis utan a sheet domain core szeparaciojanal a kovetkezo stabil schema-lepes a definition/revision/project-input vilag letetele.
- A fo docs sheet-domain SQL blokkja stale volt (public schema es definitionhez kotott project input), ezt a T5 iranyhoz szinkronizaltuk.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/h0_e2_t5_sheet_definition_revision_es_project_input_alapok.md` -> PASS

### 4.2 Ha valami kimaradt
- Nincs kihagyott kotelezo ellenorzes.

## 5) Vegleges schema inventory (T5 scope)

### 5.1 `app.sheet_definitions` oszlopok
- `id uuid primary key default gen_random_uuid()`
- `owner_user_id uuid not null references app.profiles(id) on delete restrict`
- `code text not null`
- `name text not null`
- `description text`
- `current_revision_id uuid`
- `created_at timestamptz not null default now()`
- `updated_at timestamptz not null default now()`
- `unique (owner_user_id, code)`
- check-ek: nem ures `code` es `name`

### 5.2 `app.sheet_revisions` oszlopok
- `id uuid primary key default gen_random_uuid()`
- `sheet_definition_id uuid not null references app.sheet_definitions(id) on delete cascade`
- `revision_no integer not null`
- `lifecycle app.revision_lifecycle not null default 'draft'`
- `width_mm numeric(12,3) not null`
- `height_mm numeric(12,3) not null`
- `grain_direction text`
- `source_label text`
- `source_checksum_sha256 text`
- `notes text`
- `created_at timestamptz not null default now()`
- `updated_at timestamptz not null default now()`
- `unique (sheet_definition_id, revision_no)`
- `unique (id, sheet_definition_id)` (current revision ownership integrityhez)
- check-ek: `revision_no > 0`, `width_mm > 0`, `height_mm > 0`

### 5.3 `app.project_sheet_inputs` oszlopok
- `id uuid primary key default gen_random_uuid()`
- `project_id uuid not null references app.projects(id) on delete cascade`
- `sheet_revision_id uuid not null references app.sheet_revisions(id) on delete restrict`
- `required_qty integer not null`
- `is_active boolean not null default true`
- `is_default boolean not null default false`
- `placement_priority smallint not null default 50`
- `notes text`
- `created_at timestamptz not null default now()`
- `updated_at timestamptz not null default now()`
- `unique (project_id, sheet_revision_id)`
- check-ek: `required_qty > 0`, `placement_priority between 0 and 100`

### 5.4 PK/FK kapcsolatok
- PK: `sheet_definitions(id)`, `sheet_revisions(id)`, `project_sheet_inputs(id)`
- FK: `sheet_definitions.owner_user_id -> app.profiles(id)`
- FK: `sheet_revisions.sheet_definition_id -> app.sheet_definitions(id)`
- FK: `(sheet_definitions.current_revision_id, sheet_definitions.id) -> (app.sheet_revisions.id, app.sheet_revisions.sheet_definition_id)` (`on delete set null (current_revision_id)`)
- FK: `project_sheet_inputs.project_id -> app.projects(id)`
- FK: `project_sheet_inputs.sheet_revision_id -> app.sheet_revisions(id)`

### 5.5 Indexek
- `idx_sheet_revisions_sheet_definition_id`
- `idx_sheet_revisions_lifecycle`
- `idx_project_sheet_inputs_project`
- `idx_project_sheet_inputs_priority`
- `idx_project_sheet_inputs_sheet_revision`

### 5.6 Szandekosan out-of-scope maradt
- Remnant/inventory/file/geometry/run/export domain tablak.
- RLS policy.

## 6) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Letrejon a `supabase/migrations/20260311000000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql` fajl. | PASS | `supabase/migrations/20260311000000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql:1` | A T5 migraciofajl letrejott. | `./scripts/verify.sh --report ...` |
| A migracio letrehozza az `app.sheet_definitions`, `app.sheet_revisions`, `app.project_sheet_inputs` tablakat. | PASS | `supabase/migrations/20260311000000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql:4`; `supabase/migrations/20260311000000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql:18`; `supabase/migrations/20260311000000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql:54` | Mindharom core sheet-domain tabla explicit letrejon. | `./scripts/verify.sh --report ...` |
| A project input tabla a `sheet_revisions` vilagra ul, nem kozvetlenul a definitionre. | PASS | `supabase/migrations/20260311000000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql:57` | A project input FK a `sheet_revision_id` mezon keresztul kotodik. | `./scripts/verify.sh --report ...` |
| A `current_revision_id` integritas a part-domainhez hasonloan helyesen van kezelve. | PASS | `supabase/migrations/20260311000000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql:40`; `supabase/migrations/20260311000000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql:48` | Kompozit unique + kompozit FK biztositja, hogy csak sajat definition revision valaszthato. | `./scripts/verify.sh --report ...` |
| A migracio nem hoz letre remnant/inventory/file/geometry/run/export tablakat. | PASS | `supabase/migrations/20260311000000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql:101` | Explicit scope note rogziti a kizart domaineket. | `./scripts/verify.sh --report ...` |
| A task nem ad hozza RLS policyt. | PASS | `supabase/migrations/20260311000000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql:102` | Explicit note + nincs RLS SQL. | `./scripts/verify.sh --report ...` |
| A `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md` es a `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md` minimalisan szinkronba kerul a konkret migracios irannyal. | PASS | `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md:826`; `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md:541` | A sheet-domain blokk `app.*` schema es revision-based project input iranyra lett szinkronizalva. | `./scripts/verify.sh --report ...` |
| A report DoD -> Evidence Matrix konkret fajl- es line-hivatkozasokkal kitoltott. | PASS | `codex/reports/web_platform/h0_e2_t5_sheet_definition_revision_es_project_input_alapok.md:109` | A matrix kitoltve, path+line referenciakkal. | `./scripts/verify.sh --report ...` |
| `./scripts/verify.sh --report codex/reports/web_platform/h0_e2_t5_sheet_definition_revision_es_project_input_alapok.md` PASS. | PASS | `codex/reports/web_platform/h0_e2_t5_sheet_definition_revision_es_project_input_alapok.verify.log:1` | A gate sikeresen lefutott. | `./scripts/verify.sh --report ...` |

## 7) Advisory notes
- A T5 modell expliciten kuloniti a definition/revision/project-input vilagot.
- A revision tabla minimalis, de ownership-integritassal vedett domain bazis marad ebben a lepesben.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-12T01:42:36+01:00 → 2026-03-12T01:46:09+01:00 (213s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h0_e2_t5_sheet_definition_revision_es_project_input_alapok.verify.log`
- git: `main@9b43d02`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 ...ing_platform_architektura_es_supabase_schema.md | 91 +++++++++++-----------
 .../roadmap/dxf_nesting_platform_h0_reszletes.md   | 40 ++++++++--
 2 files changed, 80 insertions(+), 51 deletions(-)
```

**git status --porcelain (preview)**

```text
 M docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md
 M docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md
?? canvases/web_platform/h0_e2_t5_sheet_definition_revision_es_project_input_alapok.md
?? codex/codex_checklist/web_platform/h0_e2_t5_sheet_definition_revision_es_project_input_alapok.md
?? codex/goals/canvases/web_platform/fill_canvas_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.yaml
?? codex/prompts/web_platform/h0_e2_t5_sheet_definition_revision_es_project_input_alapok/
?? codex/reports/web_platform/h0_e2_t5_sheet_definition_revision_es_project_input_alapok.md
?? codex/reports/web_platform/h0_e2_t5_sheet_definition_revision_es_project_input_alapok.verify.log
?? supabase/migrations/20260311000000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql
```

<!-- AUTO_VERIFY_END -->
