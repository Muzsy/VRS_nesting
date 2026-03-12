PASS

## 1) Meta
- Task slug: `h0_e2_t4_part_definition_revision_es_demand_alapok`
- Kapcsolodo canvas: `canvases/web_platform/h0_e2_t4_part_definition_revision_es_demand_alapok.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h0_e2_t4_part_definition_revision_es_demand_alapok.yaml`
- Futas datuma: `2026-03-12`
- Branch / commit: `main @ cd8c694 (dirty working tree)`
- Fokusz terulet: `Schema + Docs`

## 2) Scope

### 2.1 Cel
- H0-E2-T4 migracio letrehozasa a `part_definitions`, `part_revisions`, `project_part_requirements` tablavilaghoz.
- Definition / revision / demand vilag explicit szeparacioja.
- Demand kapcsolasa a revision vilaghoz (nem definitionhoz).

### 2.2 Nem-cel
- Geometry/file/sheet/run/remnant/export domain tablak.
- RLS policy.
- `api/sql/phase1_schema.sql` modositas.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
- `codex/codex_checklist/web_platform/h0_e2_t4_part_definition_revision_es_demand_alapok.md`
- `codex/reports/web_platform/h0_e2_t4_part_definition_revision_es_demand_alapok.md`

### 3.2 Miert valtoztak?
- A project + technology bazis utan a part domain core szeparaciojanal a kovetkezo stabil schema-lepes a definition/revision/demand letetele.
- A fo docs part-domain SQL blokkja stale volt (`public.*` referenciak, demand-definition kapcsolat), ezt a T4 iranyhoz szinkronizaltuk.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/h0_e2_t4_part_definition_revision_es_demand_alapok.md` -> PASS

### 4.2 Ha valami kimaradt
- Nincs kihagyott kotelezo ellenorzes.

## 5) Vegleges schema inventory (T4 scope)

### 5.1 `app.part_definitions` oszlopok
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

### 5.2 `app.part_revisions` oszlopok
- `id uuid primary key default gen_random_uuid()`
- `part_definition_id uuid not null references app.part_definitions(id) on delete cascade`
- `revision_no integer not null`
- `lifecycle app.revision_lifecycle not null default 'draft'`
- `source_label text`
- `source_checksum_sha256 text`
- `notes text`
- `created_at timestamptz not null default now()`
- `updated_at timestamptz not null default now()`
- `unique (part_definition_id, revision_no)`
- `unique (id, part_definition_id)` (current revision ownership integrityhez)
- `check (revision_no > 0)`

### 5.3 `app.project_part_requirements` oszlopok
- `id uuid primary key default gen_random_uuid()`
- `project_id uuid not null references app.projects(id) on delete cascade`
- `part_revision_id uuid not null references app.part_revisions(id) on delete restrict`
- `required_qty integer not null`
- `placement_priority smallint not null default 50`
- `placement_policy app.placement_policy not null default 'normal'`
- `is_active boolean not null default true`
- `notes text`
- `created_at timestamptz not null default now()`
- `updated_at timestamptz not null default now()`
- `unique (project_id, part_revision_id)`
- check-ek: `required_qty > 0`, `placement_priority between 0 and 100`

### 5.4 PK/FK kapcsolatok
- PK: `part_definitions(id)`, `part_revisions(id)`, `project_part_requirements(id)`
- FK: `part_definitions.owner_user_id -> app.profiles(id)`
- FK: `part_revisions.part_definition_id -> app.part_definitions(id)`
- FK: `(part_definitions.current_revision_id, part_definitions.id) -> (app.part_revisions.id, app.part_revisions.part_definition_id)` (`on delete set null (current_revision_id)`)
- FK: `project_part_requirements.project_id -> app.projects(id)`
- FK: `project_part_requirements.part_revision_id -> app.part_revisions(id)`

### 5.5 Indexek
- `idx_part_revisions_part_definition_id`
- `idx_part_revisions_lifecycle`
- `idx_project_part_requirements_project`
- `idx_project_part_requirements_priority`
- `idx_project_part_requirements_part_revision`

### 5.6 Szandekosan out-of-scope maradt
- Geometry/file/sheet/run/remnant/export domain tablak.
- RLS policy.

## 6) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Letrejon a `supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql` fajl. | PASS | `supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql:1` | A T4 migraciofajl letrejott. | `./scripts/verify.sh --report ...` |
| A migracio letrehozza az `app.part_definitions`, `app.part_revisions`, `app.project_part_requirements` tablakat. | PASS | `supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql:4`; `supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql:18`; `supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql:49` | Mindharom core part-domain tabla explicit letrejon. | `./scripts/verify.sh --report ...` |
| A demand tabla a `part_revisions` vilagra ul, nem kozvetlenul a definitionre. | PASS | `supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql:52` | A demand FK a `part_revision_id` mezon keresztul kotodik. | `./scripts/verify.sh --report ...` |
| A migracio nem hoz letre geometry/file/sheet/run/remnant/export tablakat. | PASS | `supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql:96` | Explicit scope note rogziti a kizart domaineket. | `./scripts/verify.sh --report ...` |
| A task nem ad hozza RLS policyt. | PASS | `supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql:97` | Explicit note + nincs RLS SQL. | `./scripts/verify.sh --report ...` |
| A `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md` es a `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md` minimalisan szinkronba kerul a konkret migracios irannyal. | PASS | `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md:761`; `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md:479` | A part-domain blokk `app.*` schema es revision-based demand iranyra lett szinkronizalva. | `./scripts/verify.sh --report ...` |
| A report DoD -> Evidence Matrix konkret fajl- es line-hivatkozasokkal kitoltott. | PASS | `codex/reports/web_platform/h0_e2_t4_part_definition_revision_es_demand_alapok.md:105` | A matrix kitoltve, path+line referenciakkal. | `./scripts/verify.sh --report ...` |
| `./scripts/verify.sh --report codex/reports/web_platform/h0_e2_t4_part_definition_revision_es_demand_alapok.md` PASS. | PASS | `codex/reports/web_platform/h0_e2_t4_part_definition_revision_es_demand_alapok.verify.log:1` | A gate sikeresen lefutott. | `./scripts/verify.sh --report ...` |

## 7) Advisory notes
- A T4 modell expliciten kuloniti a definition/revision/demand vilagot.
- A revision tabla minimalis, geometry/file FK nelkuli domain bazis marad ebben a lepesben.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-12T01:27:06+01:00 → 2026-03-12T01:30:37+01:00 (211s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h0_e2_t4_part_definition_revision_es_demand_alapok.verify.log`
- git: `main@cd8c694`
- módosított fájlok (git status): 5

**git diff --stat**

```text
 ...t4_part_definition_revision_es_demand_alapok.md | 11 +--
 ...definition_revision_es_demand_alapok.verify.log | 96 +++++++++++-----------
 ...ing_platform_architektura_es_supabase_schema.md |  8 +-
 .../roadmap/dxf_nesting_platform_h0_reszletes.md   |  8 +-
 ...4_part_definition_revision_es_demand_alapok.sql | 12 ++-
 5 files changed, 78 insertions(+), 57 deletions(-)
```

**git status --porcelain (preview)**

```text
 M codex/reports/web_platform/h0_e2_t4_part_definition_revision_es_demand_alapok.md
 M codex/reports/web_platform/h0_e2_t4_part_definition_revision_es_demand_alapok.verify.log
 M docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md
 M docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md
 M supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql
```

<!-- AUTO_VERIFY_END -->
