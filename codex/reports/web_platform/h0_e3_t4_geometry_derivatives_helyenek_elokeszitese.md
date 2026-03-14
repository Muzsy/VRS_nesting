PASS

## 1) Meta
- Task slug: `h0_e3_t4_geometry_derivatives_helyenek_elokeszitese`
- Kapcsolodo canvas: `canvases/web_platform/h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.yaml`
- Futas datuma: `2026-03-13`
- Branch / commit: `main @ b53faad (dirty working tree)`
- Fokusz terulet: `Schema + Docs`

## 2) Scope

### 2.1 Cel
- H0-E3-T4 migracio letrehozasa az `app.geometry_derivatives` tablavilaghoz.
- Derivative lineage explicit kapcsolasa a source `geometry_revisions` vilaghoz.
- Derivative kind enum gyakorlati hasznalata (`app.geometry_derivative_kind`).
- Payload + version + hash mezok es H0-s uniqueness vedelmek lerakasa.

### 2.2 Nem-cel
- Part/sheet binding tablak.
- Run/snapshot/export domain tablak.
- RLS policy.
- `api/sql/phase1_schema.sql` modositas.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `canvases/web_platform/h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.md`
- `codex/goals/canvases/web_platform/fill_canvas_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.yaml`
- `codex/prompts/web_platform/h0_e3_t4_geometry_derivatives_helyenek_elokeszitese/run.md`
- `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
- `codex/codex_checklist/web_platform/h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.md`
- `codex/reports/web_platform/h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.md`

### 3.2 Miert valtoztak?
- A geometry truth es audit/review retegek utan szukseges volt explicit derivative tarolo reteg a cel-specifikus belso reprezentaciokhoz.
- A docs SQL blokkot minimalisan T4 source-of-truth iranyra kellett szinkronizalni.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.md` -> PASS

### 4.2 Ha valami kimaradt
- Nincs kihagyott kotelezo ellenorzes.

## 5) Vegleges schema inventory (T4 scope)

### 5.1 `app.geometry_derivatives` oszlopok
- `id uuid primary key default gen_random_uuid()`
- `geometry_revision_id uuid not null references app.geometry_revisions(id) on delete cascade`
- `derivative_kind app.geometry_derivative_kind not null`
- `producer_version text not null`
- `format_version text not null`
- `derivative_jsonb jsonb not null`
- `derivative_hash_sha256 text`
- `source_geometry_hash_sha256 text`
- `created_at timestamptz not null default now()`

### 5.2 Integritas es indexek
- `unique (geometry_revision_id, derivative_kind)`
- check: `length(btrim(producer_version)) > 0`
- check: `length(btrim(format_version)) > 0`
- index: `idx_geometry_derivatives_geometry_revision_id`
- index: `idx_geometry_derivatives_kind`

### 5.3 PK/FK kapcsolatok
- PK: `app.geometry_derivatives(id)`
- FK: `geometry_revision_id -> app.geometry_revisions(id) on delete cascade`
- enum: `derivative_kind` mezon `app.geometry_derivative_kind`

### 5.4 Kulon kiemelt modellpontok
- A derivative payload helye: `derivative_jsonb`.
- A producer/format verziok explicit oszlopban taroltak.
- A derivative hash explicit mezoben tarolhato.
- H0-s uniqueness: egy geometry revision + derivative kind parhoz egy rekord.

### 5.5 Szandekosan out-of-scope maradt
- part/sheet binding
- run/snapshot/export tablavilag
- RLS policy

## 6) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Letrejon a `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql` fajl. | PASS | `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql:1` | A T4 migraciofajl letrejott. | `./scripts/verify.sh --report ...` |
| A migracio letrehozza az `app.geometry_derivatives` tablata. | PASS | `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql:4` | A derivative tabla explicit letrejon. | `./scripts/verify.sh --report ...` |
| A derivative rekord visszavezetheto egy source `app.geometry_revisions` rekordra. | PASS | `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql:6` | A source lineage kotelezo FK-val vedett. | `./scripts/verify.sh --report ...` |
| A tabla hasznalja az `app.geometry_derivative_kind` enumot. | PASS | `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql:7` | A derivative kind mezot az app enum tipizalja. | `./scripts/verify.sh --report ...` |
| A tabla rendelkezik payload hellyel es derivative hash / version mezokkel. | PASS | `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql:8`; `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql:10`; `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql:11` | A producer+format version, JSON payload es hash oszlopok explicit lettek. | `./scripts/verify.sh --report ...` |
| A migracio nem hoz letre binding / run / export tablakat. | PASS | `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql:25` | A scope note explicit rogziti a kizart tablavilagokat. | `./scripts/verify.sh --report ...` |
| A task nem ad hozza RLS policyt. | PASS | `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql:28` | RLS SQL nincs a migracioban. | `./scripts/verify.sh --report ...` |
| A `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md` es a `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md` minimalisan szinkronba kerul a konkret migracios irannyal, ha szukseges. | PASS | `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md:688`; `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md:410` | A docs T4 source-of-truth migracios iranyra frissult, explicit derivative SQL blokkot tartalmaz. | `./scripts/verify.sh --report ...` |
| A report DoD -> Evidence Matrix konkret fajl- es line-hivatkozasokkal kitoltott. | PASS | `codex/reports/web_platform/h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.md:104` | A matrix minden DoD ponthoz konkret bizonyitekot ad. | `./scripts/verify.sh --report ...` |
| `./scripts/verify.sh --report codex/reports/web_platform/h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.md` PASS. | PASS | `codex/reports/web_platform/h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.verify.log:1` | A kotelezo repo gate loggal igazoltan PASS. | `./scripts/verify.sh --report ...` |

## 7) Advisory notes
- A derivative tabla H0-ban tudatosan egyszeru, de mar elegendo a snapshot-hivatkozhato belso reteghez.
- A derivative payload explicit JSONB helyet kapott, mikozben a geometry truth ownership tovabbra is a `geometry_revisions` tablaban marad.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-14T09:25:52+01:00 → 2026-03-14T09:29:23+01:00 (211s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.verify.log`
- git: `main@7e41142`
- módosított fájlok (git status): 3

**git diff --stat**

```text
 ...4_geometry_derivatives_helyenek_elokeszitese.md |  1 +
 ...4_geometry_derivatives_helyenek_elokeszitese.md | 27 ++++----
 ...ry_derivatives_helyenek_elokeszitese.verify.log | 78 +++++++++++-----------
 3 files changed, 52 insertions(+), 54 deletions(-)
```

**git status --porcelain (preview)**

```text
 M canvases/web_platform/h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.md
 M codex/reports/web_platform/h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.md
 M codex/reports/web_platform/h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.verify.log
```

<!-- AUTO_VERIFY_END -->
