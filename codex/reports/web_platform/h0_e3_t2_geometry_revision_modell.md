PASS

## 1) Meta
- Task slug: `h0_e3_t2_geometry_revision_modell`
- Kapcsolodo canvas: `canvases/web_platform/h0_e3_t2_geometry_revision_modell.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h0_e3_t2_geometry_revision_modell.yaml`
- Futas datuma: `2026-03-12`
- Branch / commit: `main @ a5e42b4 (dirty working tree)`
- Fokusz terulet: `Schema + Docs`

## 2) Scope

### 2.1 Cel
- H0-E3-T2 migracio letrehozasa az `app.geometry_revisions` tablavilaghoz.
- A source file lineage explicit relacios rogzitese (`file_objects` -> `geometry_revisions`).
- A canonical format version es JSON-alapu canonical geometry truth hely bevezetese.
- A revision-integritas es alap indexek lerakasa.

### 2.2 Nem-cel
- `geometry_validation_reports`, `geometry_review_actions`, `geometry_derivatives` tablak.
- Run vagy export domain tablak.
- RLS policy.
- `api/sql/phase1_schema.sql` modositas.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `canvases/web_platform/h0_e3_t2_geometry_revision_modell.md`
- `codex/goals/canvases/web_platform/fill_canvas_h0_e3_t2_geometry_revision_modell.yaml`
- `codex/prompts/web_platform/h0_e3_t2_geometry_revision_modell/run.md`
- `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
- `codex/codex_checklist/web_platform/h0_e3_t2_geometry_revision_modell.md`
- `codex/reports/web_platform/h0_e3_t2_geometry_revision_modell.md`

### 3.2 Miert valtoztak?
- A file-object bazis utan kellett egy explicit, verziozhato canonical geometry revision reteg, amely forrasfajl lineage-re epul.
- A fo docs geometriablokkot minimalisan szinkronizalni kellett a tenyleges T2 migracios irannyal.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/h0_e3_t2_geometry_revision_modell.md` -> PASS

### 4.2 Ha valami kimaradt
- Nincs kihagyott kotelezo ellenorzes.

## 5) Vegleges schema inventory (T2 scope)

### 5.1 `app.geometry_revisions` oszlopok
- `id uuid primary key default gen_random_uuid()`
- `project_id uuid not null references app.projects(id) on delete cascade`
- `source_file_object_id uuid not null references app.file_objects(id) on delete restrict`
- `geometry_role app.geometry_role not null`
- `revision_no integer not null`
- `status app.geometry_validation_status not null default 'uploaded'`
- `canonical_format_version text not null`
- `canonical_geometry_jsonb jsonb`
- `canonical_hash_sha256 text`
- `source_hash_sha256 text`
- `bbox_jsonb jsonb`
- `created_by uuid references app.profiles(id) on delete set null`
- `created_at timestamptz not null default now()`
- `updated_at timestamptz not null default now()`

### 5.2 Integritas es indexek
- `unique (source_file_object_id, revision_no)`
- check: `revision_no > 0`
- check: `length(btrim(canonical_format_version)) > 0`
- index: `idx_geometry_revisions_project_id`
- index: `idx_geometry_revisions_source_file_object_id`
- index: `idx_geometry_revisions_status`
- trigger: `trg_geometry_revisions_set_updated_at` (`app.set_updated_at`)

### 5.3 PK/FK kapcsolatok
- PK: `app.geometry_revisions(id)`
- FK: `project_id -> app.projects(id) on delete cascade`
- FK: `source_file_object_id -> app.file_objects(id) on delete restrict`
- FK: `created_by -> app.profiles(id) on delete set null`

### 5.4 Kulon kiemelt modellpontok
- Source-file lineage: `source_file_object_id` kotelezo FK-val rogzitett.
- Canonical format version: `canonical_format_version` kotelezo es nem-ures check-kel vedett.
- JSON-alapu canonical geometry hely: `canonical_geometry_jsonb jsonb`.

### 5.5 Szandekosan out-of-scope maradt
- geometry_validation_reports, geometry_review_actions, geometry_derivatives
- run es export domain tablak
- RLS policy

## 6) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Letrejon a `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql` fajl. | PASS | `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql:1` | A T2 migraciofajl letrejott. | `./scripts/verify.sh --report ...` |
| A migracio letrehozza az `app.geometry_revisions` tablata. | PASS | `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql:4` | A tabla explicit letrejon a migracioban. | `./scripts/verify.sh --report ...` |
| A geometry revision rekord visszavezetheto egy source `app.file_objects` rekordra. | PASS | `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql:7` | A source lineage kotelezo FK-val vedett. | `./scripts/verify.sh --report ...` |
| A tabla tarolja a canonical format versiont. | PASS | `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql:11` | A canonical format version kulon oszlopban jelenik meg. | `./scripts/verify.sh --report ...` |
| A tabla rendelkezik JSON-alapu canonical geometry hellyel. | PASS | `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql:12` | A canonical geometry JSONB oszlopban tarolhato. | `./scripts/verify.sh --report ...` |
| A migracio nem hoz letre validation/review/derivative/run/export tablakat. | PASS | `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql:38` | A migracio csak a `geometry_revisions` tablat vezeti be, es ezt explicit scope note is rogziti. | `./scripts/verify.sh --report ...` |
| A task nem ad hozza RLS policyt. | PASS | `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql:41` | RLS SQL nincs, az out-of-scope note explicit rogziti. | `./scripts/verify.sh --report ...` |
| A `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md` es a `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md` minimalisan szinkronba kerul a konkret migracios irannyal, ha szukseges. | PASS | `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md:686`; `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md:408` | A file+geometry blokk a T2 geometry_revisions iranyara szinkronizalva lett. | `./scripts/verify.sh --report ...` |
| A report DoD -> Evidence Matrix konkret fajl- es line-hivatkozasokkal kitoltott. | PASS | `codex/reports/web_platform/h0_e3_t2_geometry_revision_modell.md:102` | A matrix minden DoD ponthoz konkret path+line bizonyitekot ad. | `./scripts/verify.sh --report ...` |
| `./scripts/verify.sh --report codex/reports/web_platform/h0_e3_t2_geometry_revision_modell.md` PASS. | PASS | `codex/reports/web_platform/h0_e3_t2_geometry_revision_modell.verify.log:1` | A kotelezo repo gate lefutasa loggal igazolt. | `./scripts/verify.sh --report ...` |

## 7) Advisory notes
- A T2 lepes a geometry truth reteg minimalis, de hasznalhato bazisara fokuszal.
- A validation/review/derivative vilag tudatosan kulon taskban marad, hogy a ownership retegek ne keveredjenek.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-12T22:16:23+01:00 → 2026-03-12T22:19:49+01:00 (206s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h0_e3_t2_geometry_revision_modell.verify.log`
- git: `main@a5e42b4`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 ...ing_platform_architektura_es_supabase_schema.md | 42 ++++++++++++++++++----
 .../roadmap/dxf_nesting_platform_h0_reszletes.md   | 42 ++++++++++++++++++----
 2 files changed, 72 insertions(+), 12 deletions(-)
```

**git status --porcelain (preview)**

```text
 M docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md
 M docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md
?? canvases/web_platform/h0_e3_t2_geometry_revision_modell.md
?? codex/codex_checklist/web_platform/h0_e3_t2_geometry_revision_modell.md
?? codex/goals/canvases/web_platform/fill_canvas_h0_e3_t2_geometry_revision_modell.yaml
?? codex/prompts/web_platform/h0_e3_t2_geometry_revision_modell/
?? codex/reports/web_platform/h0_e3_t2_geometry_revision_modell.md
?? codex/reports/web_platform/h0_e3_t2_geometry_revision_modell.verify.log
?? supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql
```

<!-- AUTO_VERIFY_END -->
