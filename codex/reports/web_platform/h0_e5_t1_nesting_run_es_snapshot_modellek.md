PASS

## 1) Meta
- Task slug: `h0_e5_t1_nesting_run_es_snapshot_modellek`
- Kapcsolodo canvas: `canvases/web_platform/h0_e5_t1_nesting_run_es_snapshot_modellek.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h0_e5_t1_nesting_run_es_snapshot_modellek.yaml`
- Futas datuma: `2026-03-14`
- Branch / commit: `main @ c032634 (dirty working tree)`
- Fokusz terulet: `Schema + Docs`

## 2) Scope

### 2.1 Cel
- H0-E5-T1 migracio letrehozasa az `app.nesting_runs` es `app.nesting_run_snapshots` tablakkal.
- Run Request es Run Snapshot fogalmi kulonvalasztas explicit schema-vilagban.
- `app.run_request_status` es `app.run_snapshot_status` enumok gyakorlati hasznalata.
- Snapshot hash + strukturalt manifest hely letetele append-only szemantikaval.

### 2.2 Nem-cel
- Queue / attempt / log tablavilag (`run_queue`, `run_attempts`, `run_logs`).
- Result / artifact / projection tablavilag.
- RLS policy.
- API / worker implementacio.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `canvases/web_platform/h0_e5_t1_nesting_run_es_snapshot_modellek.md`
- `codex/goals/canvases/web_platform/fill_canvas_h0_e5_t1_nesting_run_es_snapshot_modellek.yaml`
- `codex/prompts/web_platform/h0_e5_t1_nesting_run_es_snapshot_modellek/run.md`
- `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
- `codex/codex_checklist/web_platform/h0_e5_t1_nesting_run_es_snapshot_modellek.md`
- `codex/reports/web_platform/h0_e5_t1_nesting_run_es_snapshot_modellek.md`

### 3.2 Miert valtoztak?
- A run-vilag H0 gerincehez kulon fizikai tarolot kapott a request aggregate es az immutable snapshot.
- A docs run-szakaszait minimalisan szinkronizalni kellett az `app.*` schema + enum iranyhoz.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/h0_e5_t1_nesting_run_es_snapshot_modellek.md` -> PASS

### 4.2 Ha valami kimaradt
- Nincs kihagyott kotelezo ellenorzes.

## 5) Vegleges schema inventory (T1 scope)

### 5.1 `app.nesting_runs` oszlopok
- `id uuid primary key default gen_random_uuid()`
- `project_id uuid not null references app.projects(id) on delete cascade`
- `requested_by uuid references app.profiles(id) on delete set null`
- `status app.run_request_status not null default 'draft'`
- `run_purpose text not null default 'nesting'`
- `idempotency_key text`
- `request_payload_jsonb jsonb not null default '{}'::jsonb`
- `created_at timestamptz not null default now()`
- `updated_at timestamptz not null default now()`

### 5.2 `app.nesting_run_snapshots` oszlopok
- `id uuid primary key default gen_random_uuid()`
- `run_id uuid not null unique references app.nesting_runs(id) on delete cascade`
- `status app.run_snapshot_status not null default 'building'`
- `snapshot_version text not null`
- `snapshot_hash_sha256 text`
- `project_manifest_jsonb jsonb not null default '{}'::jsonb`
- `technology_manifest_jsonb jsonb not null default '{}'::jsonb`
- `parts_manifest_jsonb jsonb not null default '[]'::jsonb`
- `sheets_manifest_jsonb jsonb not null default '[]'::jsonb`
- `geometry_manifest_jsonb jsonb not null default '[]'::jsonb`
- `solver_config_jsonb jsonb not null default '{}'::jsonb`
- `manufacturing_manifest_jsonb jsonb not null default '{}'::jsonb`
- `created_by uuid references app.profiles(id) on delete set null`
- `created_at timestamptz not null default now()`

### 5.3 Integritas, PK/FK, indexek
- `nesting_runs` check: `length(btrim(run_purpose)) > 0`
- `nesting_runs` partial uniqueness: `(project_id, idempotency_key)` ahol kulcs nem null
- `nesting_runs` indexek: `(project_id, created_at desc)`, `(status)`
- `nesting_run_snapshots` 1:1 vedelme: `unique (run_id)`
- `nesting_run_snapshots` check: `length(btrim(snapshot_version)) > 0`
- `nesting_run_snapshots` hash uniqueness: partial unique index `snapshot_hash_sha256` mezon
- `nesting_run_snapshots` index: `(status)`

### 5.4 Kulon kiemelt modellpontok
- Run Request fizikai tarolo: `app.nesting_runs`.
- Run Snapshot fizikai tarolo: `app.nesting_run_snapshots`.
- Snapshot append-only szemantikaju: nincs `updated_at` mezo a snapshot tablaban.
- Snapshot hash + strukturalt manifest blokkok explicit oszlopokban taroltak.

### 5.5 Szandekosan out-of-scope maradt
- `run_queue`, `run_attempts`, `run_logs`
- `run_results`, `run_artifacts`, `run_layout_*`, `run_metrics`
- RLS policy

## 6) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Letrejon a `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql` fajl. | PASS | `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql:1` | A T1 migraciofajl letrejott. | `./scripts/verify.sh --report ...` |
| A migracio letrehozza az `app.nesting_runs` tablata. | PASS | `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql:4` | A run request fizikai tarolo tabla letrejott. | `./scripts/verify.sh --report ...` |
| A migracio letrehozza az `app.nesting_run_snapshots` tablata. | PASS | `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql:35` | A snapshot fizikai tarolo tabla letrejott. | `./scripts/verify.sh --report ...` |
| A run tabla az `app.run_request_status` enumot hasznalja. | PASS | `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql:8` | A request status enum tipizaltan jelenik meg. | `./scripts/verify.sh --report ...` |
| A snapshot tabla az `app.run_snapshot_status` enumot hasznalja. | PASS | `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql:38` | A snapshot status enum tipizaltan jelenik meg. | `./scripts/verify.sh --report ...` |
| A snapshot rekord 1:1 kapcsolatban van a run rekorddal. | PASS | `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql:37` | A `run_id` unique FK biztosítja az egy-run-egy-snapshot modellt. | `./scripts/verify.sh --report ...` |
| A snapshot tabla tartalmaz hash-et es strukturalt payload-helyet. | PASS | `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql:40`; `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql:41` | Hash oszlop + manifest blokkok explicit le vannak teve. | `./scripts/verify.sh --report ...` |
| A run tabla rendelkezik minimalis request-oldali metadata hellyel. | PASS | `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql:9`; `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql:11` | Run purpose, idempotency key es payload mezok biztosítottak. | `./scripts/verify.sh --report ...` |
| A migracio nem hoz letre queue/log/result/artifact/projection tablakat. | PASS | `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql:62` | Scope note explicit tiltja ezeket a tablakat. | `./scripts/verify.sh --report ...` |
| A task nem ad hozza RLS policyt. | PASS | `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql:64` | RLS SQL nincs a migracioban. | `./scripts/verify.sh --report ...` |
| A `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`, a `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md` es a `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md` minimalisan szinkronba kerul a konkret H0-E5-T1 irannyal. | PASS | `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md:176`; `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md:976`; `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md:689` | A run szakaszok az `app.*` + request/snapshot fogalmi megfeleltetesre frissultek. | `./scripts/verify.sh --report ...` |
| A report DoD -> Evidence Matrix konkret fajl- es line-hivatkozasokkal kitoltott. | PASS | `codex/reports/web_platform/h0_e5_t1_nesting_run_es_snapshot_modellek.md:99` | A matrix minden DoD ponthoz konkret bizonyitekot tartalmaz. | `./scripts/verify.sh --report ...` |
| `./scripts/verify.sh --report codex/reports/web_platform/h0_e5_t1_nesting_run_es_snapshot_modellek.md` PASS. | PASS | `codex/reports/web_platform/h0_e5_t1_nesting_run_es_snapshot_modellek.verify.log:1` | A kotelezo gate loggal igazoltan PASS. | `./scripts/verify.sh --report ...` |

## 7) Advisory notes
- A T1 tudatosan csak request+snapshot bazist tesz le, hogy T2/T3 kulon migraciokban maradjon a queue/result vilag.
- A snapshot tablaban strukturalt manifest blokkok vannak, de tovabbi normalizalas kesobbi taskban is megfontolhato.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-14T09:40:11+01:00 → 2026-03-14T09:43:43+01:00 (212s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h0_e5_t1_nesting_run_es_snapshot_modellek.verify.log`
- git: `main@c032634`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 ...ing_platform_architektura_es_supabase_schema.md | 106 +++++++++------------
 .../h0_snapshot_first_futasi_es_adatkontraktus.md  |  28 ++++--
 .../roadmap/dxf_nesting_platform_h0_reszletes.md   |  79 ++++++++-------
 3 files changed, 109 insertions(+), 104 deletions(-)
```

**git status --porcelain (preview)**

```text
 M docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md
 M docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md
 M docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md
?? canvases/web_platform/h0_e5_t1_nesting_run_es_snapshot_modellek.md
?? codex/codex_checklist/web_platform/h0_e5_t1_nesting_run_es_snapshot_modellek.md
?? codex/goals/canvases/web_platform/fill_canvas_h0_e5_t1_nesting_run_es_snapshot_modellek.yaml
?? codex/prompts/web_platform/h0_e5_t1_nesting_run_es_snapshot_modellek/
?? codex/reports/web_platform/h0_e5_t1_nesting_run_es_snapshot_modellek.md
?? codex/reports/web_platform/h0_e5_t1_nesting_run_es_snapshot_modellek.verify.log
?? supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql
```

<!-- AUTO_VERIFY_END -->
