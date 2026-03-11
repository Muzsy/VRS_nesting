PASS

## 1) Meta
- Task slug: `h0_e2_t3_technology_domain_alapok`
- Kapcsolodo canvas: `canvases/web_platform/h0_e2_t3_technology_domain_alapok.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h0_e2_t3_technology_domain_alapok.yaml`
- Futas datuma: `2026-03-12`
- Branch / commit: `main @ 3670bc1 (dirty working tree)`
- Fokusz terulet: `Schema + Docs`

## 2) Scope

### 2.1 Cel
- H0-E2-T3 migracio letrehozasa a technology domain bazisahoz.
- Reusable preset catalog es project-bound setup truth kulonvalasztasa.
- Minimal docs szinkron a konkret migracios iranyhoz.

### 2.2 Nem-cel
- Part/file/revision/run/snapshot/remnant/export/manufacturing package tablak.
- RLS policy.
- `api/sql/phase1_schema.sql` modositas.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
- `codex/codex_checklist/web_platform/h0_e2_t3_technology_domain_alapok.md`
- `codex/reports/web_platform/h0_e2_t3_technology_domain_alapok.md`

### 3.2 Miert valtoztak?
- A H0-E2-T2 project root utan szukseges volt a technology domain minimum tablagepe.
- A docs technology SQL-blokkjai stale/all-in-one iranyt mutattak, ezt a T3 bazismigraciohoz igazitottuk.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/h0_e2_t3_technology_domain_alapok.md` -> PASS

### 4.2 Ha valami kimaradt
- Nincs kihagyott kotelezo ellenorzes.

## 5) Vegleges schema inventory (T3 scope)

### 5.1 `app.technology_presets` oszlopok
- `id uuid primary key default gen_random_uuid()`
- `preset_code text not null unique`
- `display_name text not null`
- `machine_code text not null`
- `material_code text not null`
- `thickness_mm numeric(10,3) not null`
- `kerf_mm numeric(10,3) not null`
- `spacing_mm numeric(10,3) not null default 0`
- `margin_mm numeric(10,3) not null default 0`
- `rotation_step_deg integer not null default 90`
- `allow_free_rotation boolean not null default false`
- `lifecycle app.revision_lifecycle not null default 'approved'`
- `is_active boolean not null default true`
- `notes text`
- `created_at timestamptz not null default now()`
- `updated_at timestamptz not null default now()`
- domain check-ek: ures string tiltasa + numeric bound check-ek

### 5.2 `app.project_technology_setups` oszlopok
- `id uuid primary key default gen_random_uuid()`
- `project_id uuid not null references app.projects(id) on delete cascade`
- `preset_id uuid references app.technology_presets(id) on delete set null`
- `display_name text not null`
- `lifecycle app.revision_lifecycle not null default 'draft'`
- `is_default boolean not null default false`
- `machine_code text not null`
- `material_code text not null`
- `thickness_mm numeric(10,3) not null`
- `kerf_mm numeric(10,3) not null`
- `spacing_mm numeric(10,3) not null default 0`
- `margin_mm numeric(10,3) not null default 0`
- `rotation_step_deg integer not null default 90`
- `allow_free_rotation boolean not null default false`
- `notes text`
- `created_at timestamptz not null default now()`
- `updated_at timestamptz not null default now()`
- domain check-ek + `unique (project_id, display_name)`

### 5.3 FK kapcsolatok
- `project_technology_setups.project_id -> app.projects(id)`
- `project_technology_setups.preset_id -> app.technology_presets(id)`

### 5.4 Indexek
- `idx_technology_presets_is_active`
- `idx_technology_presets_material_machine_thickness`
- `idx_project_technology_setups_project_id`
- `idx_project_technology_setups_preset_id`
- `idx_project_technology_setups_project_lifecycle`
- `uq_project_technology_setups_default_per_project` (partial unique index)

### 5.5 Szandekosan out-of-scope maradt
- Part/file/revision/run/snapshot/remnant/export domain tablak.
- Manufacturing package domain.
- RLS policy.

## 6) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Letrejon a `supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql` fajl. | PASS | `supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql:1` | A T3 migraciofajl letrejott. | `./scripts/verify.sh --report ...` |
| A migracio letrehoz egy reusable technology catalog/preset tablavilagot. | PASS | `supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql:4` | `app.technology_presets` kulon tabela a reusable preset truthhoz. | `./scripts/verify.sh --report ...` |
| A migracio letrehoz egy projekt-szintu technology setup/profile tablavilagot. | PASS | `supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql:33` | `app.project_technology_setups` kulon tabela a project-bound setup truthhoz. | `./scripts/verify.sh --report ...` |
| A technology setup megfelelo FK-val kapcsolodik az `app.projects` tablaho. | PASS | `supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql:35` | A setup rekord projekt-szinten kotelezetten kotott az `app.projects` aggregate-hez. | `./scripts/verify.sh --report ...` |
| A migracio nem hoz letre file/revision/run/remnant/export domain tablakat. | PASS | `supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql:97` | Explicit scope note rogziti a kizart domaineket. | `./scripts/verify.sh --report ...` |
| A task nem ad hozza RLS policyt. | PASS | `supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql:98` | Explicit note + nincs RLS SQL. | `./scripts/verify.sh --report ...` |
| A `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md` es a `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md` minimalisan szinkronba kerul a konkret migracios irannyal. | PASS | `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md:530`; `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md:352` | A technology baseline irany a T3 migraciohoz lett igazitva. | `./scripts/verify.sh --report ...` |
| A report DoD -> Evidence Matrix konkret fajl- es line-hivatkozasokkal kitoltott. | PASS | `codex/reports/web_platform/h0_e2_t3_technology_domain_alapok.md:102` | A matrix kitoltve, path+line referenciakkal. | `./scripts/verify.sh --report ...` |
| `./scripts/verify.sh --report codex/reports/web_platform/h0_e2_t3_technology_domain_alapok.md` PASS. | PASS | `codex/reports/web_platform/h0_e2_t3_technology_domain_alapok.verify.log:1` | A gate sikeresen lefutott. | `./scripts/verify.sh --report ...` |

## 7) Advisory notes
- A T3 model expliciten kulon kezeli a preset catalogot es a project-bound setup truthot.
- A setup tabla nem snapshot: elo konfiguracios allapot, amit kesobb a run snapshot pipeline masol immutable bemenette.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-12T00:47:25+01:00 → 2026-03-12T00:50:57+01:00 (212s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h0_e2_t3_technology_domain_alapok.verify.log`
- git: `main@3670bc1`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 ...ing_platform_architektura_es_supabase_schema.md | 118 ++++++++-------------
 .../roadmap/dxf_nesting_platform_h0_reszletes.md   | 100 +++++++----------
 2 files changed, 86 insertions(+), 132 deletions(-)
```

**git status --porcelain (preview)**

```text
 M docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md
 M docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md
?? canvases/web_platform/h0_e2_t3_technology_domain_alapok.md
?? codex/codex_checklist/web_platform/h0_e2_t3_technology_domain_alapok.md
?? codex/goals/canvases/web_platform/fill_canvas_h0_e2_t3_technology_domain_alapok.yaml
?? codex/prompts/web_platform/h0_e2_t3_technology_domain_alapok/
?? codex/reports/web_platform/h0_e2_t3_technology_domain_alapok.md
?? codex/reports/web_platform/h0_e2_t3_technology_domain_alapok.verify.log
?? supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql
```

<!-- AUTO_VERIFY_END -->
