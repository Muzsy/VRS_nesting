PASS

## 1) Meta
- Task slug: `h0_e3_t1_file_object_modell`
- Kapcsolodo canvas: `canvases/web_platform/h0_e3_t1_file_object_modell.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h0_e3_t1_file_object_modell.yaml`
- Futas datuma: `2026-03-12`
- Branch / commit: `main @ 0cf75df (dirty working tree)`
- Fokusz terulet: `Schema + Docs`

## 2) Scope

### 2.1 Cel
- H0-E3-T1 migracio letrehozasa az `app.file_objects` tablavilaghoz.
- A file-domain ownership storage-reference + metadata truth szinten rogzitese.
- A table kapcsolatainak rogzitese az `app.projects` es `app.profiles` tablakhhoz.
- A storage referencia egyedisegenek vedelme.

### 2.2 Nem-cel
- Geometry revision, validation, review, derivative tablak bevezetese.
- Run vagy export domain tabla bevezetese.
- RLS policy bevezetese.
- `api/sql/phase1_schema.sql` modositas.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `canvases/web_platform/h0_e3_t1_file_object_modell.md`
- `codex/goals/canvases/web_platform/fill_canvas_h0_e3_t1_file_object_modell.yaml`
- `codex/prompts/web_platform/h0_e3_t1_file_object_modell/run.md`
- `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
- `codex/codex_checklist/web_platform/h0_e3_t1_file_object_modell.md`
- `codex/reports/web_platform/h0_e3_t1_file_object_modell.md`

### 3.2 Miert valtoztak?
- A kovetkezo schema-lepesben a file-domain bazist kellett letenni anelkul, hogy geometry/run/export vilag idotlenul osszekeveredjen a forras file-object reteggel.
- A fo docs file-domain SQL blokkja stale volt a konkret `app.file_objects` migraciohoz kepest, ezt minimalisan szinkronizaltuk.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/h0_e3_t1_file_object_modell.md` -> PASS

### 4.2 Ha valami kimaradt
- Nincs kihagyott kotelezo ellenorzes.

## 5) Vegleges schema inventory (T1 scope)

### 5.1 `app.file_objects` oszlopok
- `id uuid primary key default gen_random_uuid()`
- `project_id uuid not null references app.projects(id) on delete cascade`
- `storage_bucket text not null`
- `storage_path text not null`
- `file_name text not null`
- `mime_type text`
- `file_kind app.file_kind not null`
- `byte_size bigint`
- `sha256 text`
- `uploaded_by uuid references app.profiles(id) on delete set null`
- `created_at timestamptz not null default now()`

### 5.2 Integritas es indexek
- `unique (storage_bucket, storage_path)`
- check: `length(btrim(storage_bucket)) > 0`
- check: `length(btrim(storage_path)) > 0`
- check: `length(btrim(file_name)) > 0`
- check: `byte_size is null or byte_size >= 0`
- index: `idx_file_objects_project_id`
- index: `idx_file_objects_uploaded_by`

### 5.3 PK/FK kapcsolatok
- PK: `app.file_objects(id)`
- FK: `project_id -> app.projects(id) on delete cascade`
- FK: `uploaded_by -> app.profiles(id) on delete set null`

### 5.4 Szandekosan out-of-scope maradt
- geometry_revisions, geometry_validation_reports, geometry_review_actions, geometry_derivatives
- run es export domain tablak
- RLS policy

## 6) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Letrejon a `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql` fajl. | PASS | `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql:1` | A T1 migraciofajl letrejott. | `./scripts/verify.sh --report ...` |
| A migracio letrehozza az `app.file_objects` tablata. | PASS | `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql:4` | A tabla explicit letrejon a migracioban. | `./scripts/verify.sh --report ...` |
| A tabla helyesen kapcsolodik az `app.projects` es `app.profiles` tablakhhoz. | PASS | `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql:6`; `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql:14` | A `project_id` es `uploaded_by` FK-k a vart tablakhhoz kotnek. | `./scripts/verify.sh --report ...` |
| A storage hivatkozas egyedisege vedett. | PASS | `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql:16` | A `(storage_bucket, storage_path)` kombinacio unique constrainttel vedett. | `./scripts/verify.sh --report ...` |
| A migracio nem hoz letre geometry/review/derivative/run/export tablakat. | PASS | `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql:29` | A migracio SQL csak `app.file_objects` tablat hoz letre, es ezt explicit scope note is rogziti. | `./scripts/verify.sh --report ...` |
| A task nem ad hozza RLS policyt. | PASS | `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql:33` | RLS SQL nincs a migracioban, az out-of-scope note ezt explicit rogziti. | `./scripts/verify.sh --report ...` |
| A `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md` es a `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md` minimalisan szinkronba kerul a konkret migracios irannyal, ha szukseges. | PASS | `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md:686`; `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md:408` | A file-domain blokkok az `app.file_objects` konkret migracios iranyara lettek szinkronizalva. | `./scripts/verify.sh --report ...` |
| A report DoD -> Evidence Matrix konkret fajl- es line-hivatkozasokkal kitoltott. | PASS | `codex/reports/web_platform/h0_e3_t1_file_object_modell.md:93` | A matrix minden DoD ponthoz konkret path+line bizonyitekot tartalmaz. | `./scripts/verify.sh --report ...` |
| `./scripts/verify.sh --report codex/reports/web_platform/h0_e3_t1_file_object_modell.md` PASS. | PASS | `codex/reports/web_platform/h0_e3_t1_file_object_modell.verify.log:1` | A kotelezo repo gate lefutasa loggal igazolt. | `./scripts/verify.sh --report ...` |

## 7) Advisory notes
- A file-domain jelen lepesben tudatosan csak storage-reference + metadata truth szinten kerult bevezetesre.
- A geometry/review/derivative vilag kovetkezo taskokban vezetheto be anelkul, hogy a file-object ownership keveredne.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-12T21:43:57+01:00 → 2026-03-12T21:47:29+01:00 (212s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h0_e3_t1_file_object_modell.verify.log`
- git: `main@0cf75df`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 ...ing_platform_architektura_es_supabase_schema.md | 85 ++++++----------------
 .../roadmap/dxf_nesting_platform_h0_reszletes.md   | 61 ++++------------
 2 files changed, 38 insertions(+), 108 deletions(-)
```

**git status --porcelain (preview)**

```text
 M docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md
 M docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md
?? canvases/web_platform/h0_e3_t1_file_object_modell.md
?? codex/codex_checklist/web_platform/h0_e3_t1_file_object_modell.md
?? codex/goals/canvases/web_platform/fill_canvas_h0_e3_t1_file_object_modell.yaml
?? codex/prompts/web_platform/h0_e3_t1_file_object_modell/
?? codex/reports/web_platform/h0_e3_t1_file_object_modell.md
?? codex/reports/web_platform/h0_e3_t1_file_object_modell.verify.log
?? supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql
```

<!-- AUTO_VERIFY_END -->
