PASS

## 1) Meta
- Task slug: `h0_e5_t2_queue_es_log_modellek`
- Kapcsolodo canvas: `canvases/web_platform/h0_e5_t2_queue_es_log_modellek.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h0_e5_t2_queue_es_log_modellek.yaml`
- Futas datuma: `2026-03-14`
- Branch / commit: `main @ bed2ae8 (dirty working tree)`
- Fokusz terulet: `Schema + Docs`

## 2) Scope

### 2.1 Cel
- H0-E5-T2 migracio letrehozasa az `app.run_queue` es `app.run_logs` tablakkal.
- Queue-level es attempt-level allapot formalizalasa ugyanabban a queue rekordban.
- `app.run_attempt_status` enum gyakorlati hasznalata.
- Kulon append-only log event reteg letetele a run-vilaghoz.

### 2.2 Nem-cel
- Kulon `run_attempts` tabla.
- Result / artifact / projection tablavilag.
- RLS policy.
- API / worker implementacio.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `canvases/web_platform/h0_e5_t2_queue_es_log_modellek.md`
- `codex/goals/canvases/web_platform/fill_canvas_h0_e5_t2_queue_es_log_modellek.yaml`
- `codex/prompts/web_platform/h0_e5_t2_queue_es_log_modellek/run.md`
- `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
- `codex/codex_checklist/web_platform/h0_e5_t2_queue_es_log_modellek.md`
- `codex/reports/web_platform/h0_e5_t2_queue_es_log_modellek.md`

### 3.2 Miert valtoztak?
- A T1 request/snapshot bazis utan kellett explicit queue/lease/log tarolo reteg.
- A docsban egyertelmuen ki kellett mondani, hogy T2-ben az attempt szemantika a queue sorban el.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/h0_e5_t2_queue_es_log_modellek.md` -> PASS

### 4.2 Ha valami kimaradt
- Nincs kihagyott kotelezo ellenorzes.

## 5) Vegleges schema inventory (T2 scope)

### 5.1 `app.run_queue` oszlopok
- `run_id uuid primary key references app.nesting_runs(id) on delete cascade`
- `snapshot_id uuid not null unique`
- `queue_state text not null default 'pending'`
- `attempt_no integer not null default 0`
- `attempt_status app.run_attempt_status`
- `priority integer not null default 100`
- `available_at timestamptz not null default now()`
- `leased_by text`
- `lease_token uuid`
- `leased_at timestamptz`
- `lease_expires_at timestamptz`
- `heartbeat_at timestamptz`
- `started_at timestamptz`
- `finished_at timestamptz`
- `last_error_code text`
- `last_error_message text`
- `retry_count integer not null default 0`
- `created_at timestamptz not null default now()`
- `updated_at timestamptz not null default now()`

### 5.2 `app.run_logs` oszlopok
- `id uuid primary key default gen_random_uuid()`
- `run_id uuid not null references app.nesting_runs(id) on delete cascade`
- `snapshot_id uuid references app.nesting_run_snapshots(id) on delete set null`
- `attempt_no integer not null default 0`
- `log_level text not null`
- `log_kind text not null`
- `message text not null`
- `payload_jsonb jsonb not null default '{}'::jsonb`
- `created_at timestamptz not null default now()`

### 5.3 Integritas, PK/FK, indexek
- Queue-level allapot check: `pending`, `leased`, `done`, `error`, `cancel_requested`, `cancelled`.
- Attempt-level enum: `attempt_status app.run_attempt_status`.
- Lease check: leased allapotban `lease_token` es `lease_expires_at` kotelezo.
- Queue indexek: `(queue_state, available_at)`, `(lease_expires_at)`.
- Log checkek: `log_level`, `log_kind`, `message` nem lehet ures.
- Log indexek: `(run_id, created_at)`, `(snapshot_id, created_at)`.

### 5.4 Kulon kiemelt modellpontok
- T2-ben nincs kulon `run_attempts` tabla; az attempt szemantika a `run_queue` sorban jelenik meg.
- A `run_logs` append-only audit/log reteg.
- A result/artifact/projection vilag szandekosan T3-ban marad.

### 5.5 Szandekosan out-of-scope maradt
- `run_attempts`
- `run_results`, `run_artifacts`, `run_layout_*`, `run_metrics`
- RLS policy

## 6) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Letrejon a `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql` fajl. | PASS | `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql:1` | A T2 migraciofajl letrejott. | `./scripts/verify.sh --report ...` |
| A migracio letrehozza az `app.run_queue` tablata. | PASS | `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql:11` | A queue tabla explicit letrejott. | `./scripts/verify.sh --report ...` |
| A migracio letrehozza az `app.run_logs` tablata. | PASS | `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql:58` | A log tabla explicit letrejott. | `./scripts/verify.sh --report ...` |
| A queue tabla kapcsolodik az `app.nesting_runs` es `app.nesting_run_snapshots` tablavilaghoz. | PASS | `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql:12`; `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql:45` | A queue rekord run+snapshot kapcsolata FK-val vedett. | `./scripts/verify.sh --report ...` |
| A queue tabla hasznalja az `app.run_attempt_status` enumot. | PASS | `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql:16` | Attempt-level allapot enum tipizalt. | `./scripts/verify.sh --report ...` |
| A queue tabla formalizalja a pending/leased/done/error jellegu queue allapotot. | PASS | `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql:29` | `queue_state` check explicit allapotlistaval vedett. | `./scripts/verify.sh --report ...` |
| A queue tabla rendelkezik lease/heartbeat/retry mezokkel. | PASS | `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql:20`; `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql:27` | Lease/heartbeat/retry mezokeszlet letett. | `./scripts/verify.sh --report ...` |
| A log tabla append-only, kulon log event tarolo. | PASS | `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql:58` | A log tabla kulon, timestampelt event tarolo. | `./scripts/verify.sh --report ...` |
| A task nem hoz letre kulon `run_attempts` tablat. | PASS | `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql:81` | Scope note explicit tiltja a kulon attempt tablazatot. | `./scripts/verify.sh --report ...` |
| A migracio nem hoz letre result/artifact/projection tablakat. | PASS | `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql:82` | Scope note explicit tiltja a T3 tablavilagot. | `./scripts/verify.sh --report ...` |
| A task nem ad hozza RLS policyt. | PASS | `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql:83` | RLS SQL nincs a migracioban. | `./scripts/verify.sh --report ...` |
| A `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`, a `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md` es a `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md` minimalisan szinkronba kerul a konkret H0-E5-T2 irannyal. | PASS | `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md:176`; `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md:976`; `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md:689` | A queue/lease/log es attempt szemantika T2 source-of-truth iranyra frissult. | `./scripts/verify.sh --report ...` |
| A report DoD -> Evidence Matrix konkret fajl- es line-hivatkozasokkal kitoltott. | PASS | `codex/reports/web_platform/h0_e5_t2_queue_es_log_modellek.md:99` | A matrix minden DoD ponthoz konkret bizonyitekot ad. | `./scripts/verify.sh --report ...` |
| `./scripts/verify.sh --report codex/reports/web_platform/h0_e5_t2_queue_es_log_modellek.md` PASS. | PASS | `codex/reports/web_platform/h0_e5_t2_queue_es_log_modellek.verify.log:1` | A kotelezo gate loggal igazoltan PASS. | `./scripts/verify.sh --report ...` |

## 7) Advisory notes
- T2-ben a queue-szintu es attempt-szintu jelentes egy tablaban egyesul; T3/T4 soran erdemes ujraertekelni, mikor jon el a kulon attempt tabla ideje.
- A stale `public.nesting_runs` hivatkozasok kozel-run blokkokban csak minimalisan lettek igaziva.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-14T10:43:41+01:00 → 2026-03-14T10:47:11+01:00 (210s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h0_e5_t2_queue_es_log_modellek.verify.log`
- git: `main@bed2ae8`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 ...ing_platform_architektura_es_supabase_schema.md | 76 ++++++++++++++++++++--
 .../h0_snapshot_first_futasi_es_adatkontraktus.md  | 14 ++--
 .../roadmap/dxf_nesting_platform_h0_reszletes.md   | 65 +++++++++++++++++-
 3 files changed, 142 insertions(+), 13 deletions(-)
```

**git status --porcelain (preview)**

```text
 M docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md
 M docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md
 M docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md
?? canvases/web_platform/h0_e5_t2_queue_es_log_modellek.md
?? codex/codex_checklist/web_platform/h0_e5_t2_queue_es_log_modellek.md
?? codex/goals/canvases/web_platform/fill_canvas_h0_e5_t2_queue_es_log_modellek.yaml
?? codex/prompts/web_platform/h0_e5_t2_queue_es_log_modellek/
?? codex/reports/web_platform/h0_e5_t2_queue_es_log_modellek.md
?? codex/reports/web_platform/h0_e5_t2_queue_es_log_modellek.verify.log
?? supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql
```

<!-- AUTO_VERIFY_END -->
