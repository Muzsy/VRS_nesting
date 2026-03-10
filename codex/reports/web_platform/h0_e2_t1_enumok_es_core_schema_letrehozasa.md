PASS

## 1) Meta
- Task slug: `h0_e2_t1_enumok_es_core_schema_letrehozasa`
- Kapcsolodo canvas: `canvases/web_platform/h0_e2_t1_enumok_es_core_schema_letrehozasa.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h0_e2_t1_enumok_es_core_schema_letrehozasa.yaml`
- Futas datuma: `2026-03-10`
- Branch / commit: `main @ 8dccdc1 (dirty working tree)`
- Fokusz terulet: `Schema + Docs`

## 2) Scope

### 2.1 Cel
- H0-E2-T1 bazis migracio letrehozasa (`app` schema + extension + enum inventory).
- Snapshot-first elvekhez igazodva a run lifecycle enumok request/snapshot/attempt szetvalasztasa.
- Minimal docs szinkron a migracios iranyhoz.

### 2.2 Nem-cel
- Domain tablakschema letrehozasa.
- RLS, trigger, queue, API vagy worker implementacio.
- `api/sql/phase1_schema.sql` modositas.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
- `codex/codex_checklist/web_platform/h0_e2_t1_enumok_es_core_schema_letrehozasa.md`
- `codex/reports/web_platform/h0_e2_t1_enumok_es_core_schema_letrehozasa.md`

### 3.2 Miert valtoztak?
- A H0-E1 dokumentumok alapjan szukseges volt a valos migration baseline letetele.
- Az architecture/H0 dokumentumokban a korabbi leegyszerusitett enum irany stale lehetett, ezt minimalisan szinkronizalni kellett.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/h0_e2_t1_enumok_es_core_schema_letrehozasa.md` -> PASS

### 4.2 Ha valami kimaradt
- Nincs kihagyott kotelezo ellenorzes.

## 5) Vegleges enum inventory

- `app.project_lifecycle`
- `app.revision_lifecycle`
- `app.file_kind`
- `app.geometry_role`
- `app.geometry_validation_status`
- `app.geometry_derivative_kind`
- `app.sheet_geometry_type`
- `app.sheet_source_kind`
- `app.sheet_availability_status`
- `app.run_request_status`
- `app.run_snapshot_status`
- `app.run_attempt_status`
- `app.artifact_kind`
- `app.placement_policy`

Megjegyzes:
- A task szandekosan NEM hoz letre domain tablakat (`profiles`, `projects`, `run_*`, stb.).

## 6) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Letrejon a `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql` fajl. | PASS | `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql:1` | A bazismigracio fajl letrejott. | `./scripts/verify.sh --report ...` |
| A migracio letrehozza az `app` schema-t es a szukseges extension(ok)et. | PASS | `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql:5`; `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql:7` | `pgcrypto` extension es `app` schema letrejon. | `./scripts/verify.sh --report ...` |
| A migracio letrehozza a H0/H1 core enumokat a H0-E1-T1/T2/T3 dokumentumokkal osszhangban. | PASS | `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql:9`; `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql:270` | A teljes enum inventory request/snapshot/attempt split modellel rogzitve van. | `./scripts/verify.sh --report ...` |
| A migracio nem hoz letre meg core domain tablakat. | PASS | `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql:272` | Explicit scope note rogziti, hogy tabla nem letesul. | `./scripts/verify.sh --report ...` |
| A task nem modositja a `api/sql/phase1_schema.sql` fajlt. | PASS | `api/sql/phase1_schema.sql` (valtozatlan) | A task outputjai nem tartalmazzak ezt a fajlt, es nincs modositas rajta. | `./scripts/verify.sh --report ...` |
| `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md` es `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md` minimalisan szinkronba kerul. | PASS | `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md:468`; `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md:278` | Minimal docs-sync jelzi a migracio source-of-truth iranyt. | `./scripts/verify.sh --report ...` |
| A report DoD -> Evidence Matrix konkret fajl- es line-hivatkozasokkal kitoltott. | PASS | `codex/reports/web_platform/h0_e2_t1_enumok_es_core_schema_letrehozasa.md:64` | A matrix kitoltve, hivatkozasokkal. | `./scripts/verify.sh --report ...` |
| `./scripts/verify.sh --report codex/reports/web_platform/h0_e2_t1_enumok_es_core_schema_letrehozasa.md` PASS. | PASS | `codex/reports/web_platform/h0_e2_t1_enumok_es_core_schema_letrehozasa.verify.log:1` | A gate sikeresen lefutott. | `./scripts/verify.sh --report ...` |

## 7) Advisory notes
- A migracio duplicate-safe enum create mintat hasznal (`DO $$ IF NOT EXISTS ... CREATE TYPE ... $$`).
- A run lifecycle enum modell szetvalasztja a request/snapshot/attempt statusz vilagokat a snapshot-first elvhez.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-10T22:56:30+01:00 → 2026-03-10T23:00:00+01:00 (210s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h0_e2_t1_enumok_es_core_schema_letrehozasa.verify.log`
- git: `main@8dccdc1`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 ...ing_platform_architektura_es_supabase_schema.md | 101 +++++----------------
 .../roadmap/dxf_nesting_platform_h0_reszletes.md   |  77 +++++-----------
 2 files changed, 43 insertions(+), 135 deletions(-)
```

**git status --porcelain (preview)**

```text
 M docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md
 M docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md
?? canvases/web_platform/h0_e2_t1_enumok_es_core_schema_letrehozasa.md
?? codex/codex_checklist/web_platform/h0_e2_t1_enumok_es_core_schema_letrehozasa.md
?? codex/goals/canvases/web_platform/fill_canvas_h0_e2_t1_enumok_es_core_schema_letrehozasa.yaml
?? codex/prompts/web_platform/h0_e2_t1_enumok_es_core_schema_letrehozasa/
?? codex/reports/web_platform/h0_e2_t1_enumok_es_core_schema_letrehozasa.md
?? codex/reports/web_platform/h0_e2_t1_enumok_es_core_schema_letrehozasa.verify.log
?? supabase/migrations/
```

<!-- AUTO_VERIFY_END -->
