# H0-E5-T2 queue es log modellek

## Funkcio
A feladat a web platform H0 run gerincenek masodik schema-lepese:
az `app.run_queue` es `app.run_logs` tablavilag letetele.

Ez a task kozvetlenul a H0-E5-T1 utan kovetkezik.
A cel, hogy a run-vilag ne csak request/snapshot bazissal rendelkezzen,
hanem legyen kulon, explicit helye:

- a futtatasra varo / lease-elt / terminalis queue allapotnak,
- a worker attempt jellegu allapotnak,
- es a futas kozbeni / futas kornyezeti log esemenyeknek.

Fontos modell-dontes ehhez a taskhoz:
- a fizikai output H0-ban maradjon a backlog szerint `app.run_queue` es
  `app.run_logs`;
- **kulon `run_attempts` tabla most ne jojjon letre**;
- a fogalmi attempt/lease vilag H0-E5-T2-ben a `run_queue` tablaban
  jelenjen meg `attempt_no` + `attempt_status` + lease mezokkel;
- a `run_logs` legyen kulon append-only audit/log reteg.

Ez tovabbra is kontrollalt H0 scope:
- request/snapshot bazis mar kesz a T1-ben,
- result / artifact / projection kulon task,
- RLS kulon task,
- API / worker implementacio meg nincs scope-ban.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - uj Supabase migracio letrehozasa az `app.run_queue` es `app.run_logs`
    tablakkal;
  - a queue entry explicit kapcsolata az `app.nesting_runs` es
    `app.nesting_run_snapshots` rekordokkal;
  - lease / heartbeat / retry alapmezok letetele;
  - a `app.run_attempt_status` enum gyakorlati hasznalata;
  - kulon queue-level allapot (`pending` / `leased` / `done` / `error` /
    `cancel_requested` / `cancelled`) formalizalasa;
  - log esemenyek kulon append-only tablaja;
  - minimal docs szinkron a queue/lease/log source-of-truth iranyhoz.
- Nincs benne:
  - kulon `run_attempts` tabla;
  - `run_results`, `run_artifacts`, `run_layout_*`, `run_metrics` tablavilag;
  - worker lease algoritmus implementacio;
  - API endpoint vagy worker kod;
  - RLS policy.

### Fo kerdesek, amiket le kell zarni
- [ ] Mi legyen a minimalis, de mar hasznalhato queue oszlopkeszlet?
- [ ] Hogyan legyen egyszerre jelen a queue-level es az attempt-level allapot?
- [ ] Milyen lease mezok kellenek mar H0-ban a kesobbi workerhez?
- [ ] Mi legyen append-only a log vilagban, es mi maradjon strukturalt JSON payload?
- [ ] Hogyan mondjuk ki docs-szinten, hogy a fogalmi attempt vilag H0-E5-T2-ben
      nem kulon tablaban, hanem a queue sorban jelenik meg?

### Feladatlista
- [ ] Kesz legyen a task teljes artefaktlanca.
- [ ] Letrejojjon a kovetkezo H0 migracio az `app.run_queue` tablaval.
- [ ] Letrejojjon a kovetkezo H0 migracio az `app.run_logs` tablaval.
- [ ] A queue tabla kapcsolodjon a T1-ben letett `app.nesting_runs` es
      `app.nesting_run_snapshots` tablavilaghoz.
- [ ] A queue tabla hasznalja az `app.run_attempt_status` enumot.
- [ ] A queue tabla formalizalja a pending/leased/done/error jellegu allapotokat.
- [ ] A queue tabla tartalmazzon lease/heartbeat/retry mezoket.
- [ ] A log tabla append-only legyen.
- [ ] A task ne hozzon letre kulon `run_attempts` tablat.
- [ ] A task ne hozzon letre result/artifact/projection tablakat.
- [ ] Minimal docs szinkron tortenjen a queue/lease/log iranyhoz.
- [ ] Repo gate le legyen futtatva a reporton.

### Erintett fajlok
- `canvases/web_platform/h0_e5_t2_queue_es_log_modellek.md`
- `codex/goals/canvases/web_platform/fill_canvas_h0_e5_t2_queue_es_log_modellek.yaml`
- `codex/prompts/web_platform/h0_e5_t2_queue_es_log_modellek/run.md`
- `codex/codex_checklist/web_platform/h0_e5_t2_queue_es_log_modellek.md`
- `codex/reports/web_platform/h0_e5_t2_queue_es_log_modellek.md`
- `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`

### Elvart tabla-irany
A konkret oszlopok kod kozben finomithatok, de az irany ez legyen:

- `app.run_queue`
  - `run_id uuid primary key references app.nesting_runs(id) on delete cascade`
  - `snapshot_id uuid not null unique references app.nesting_run_snapshots(id) on delete cascade`
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

- `app.run_logs`
  - `id uuid primary key default gen_random_uuid()`
  - `run_id uuid not null references app.nesting_runs(id) on delete cascade`
  - `snapshot_id uuid references app.nesting_run_snapshots(id) on delete set null`
  - `attempt_no integer not null default 0`
  - `log_level text not null`
  - `log_kind text not null`
  - `message text not null`
  - `payload_jsonb jsonb not null default '{}'::jsonb`
  - `created_at timestamptz not null default now()`

### Elvart integritas es indexek
- `app.run_queue`
  - `queue_state` legyen kontrollalt check-kel legalabb ezekre:
    - `pending`
    - `leased`
    - `done`
    - `error`
    - `cancel_requested`
    - `cancelled`
  - `attempt_no >= 0`
  - `retry_count >= 0`
  - ha `queue_state = 'leased'`, akkor `lease_token` es `lease_expires_at`
    ne maradhasson uresen
  - index legalabb:
    - `idx_run_queue_state_available_at` on `(queue_state, available_at)`
    - `idx_run_queue_lease_expires_at` on `(lease_expires_at)`
- `app.run_logs`
  - check legalabb:
    - `length(btrim(log_level)) > 0`
    - `length(btrim(log_kind)) > 0`
    - `length(btrim(message)) > 0`
  - index legalabb:
    - `idx_run_logs_run_id_created_at` on `(run_id, created_at)`
    - opcionálisan `idx_run_logs_snapshot_id_created_at` on `(snapshot_id, created_at)`

### Fontos modellezesi elvek
- A `nesting_runs` marad a Run Request aggregate fizikai taroloja.
- A `nesting_run_snapshots` marad a Run Snapshot immutable truth fizikai taroloja.
- A T2-ben a fogalmi attempt/lease vilag **nem kulon tablaban**, hanem a
  `run_queue` sorban jelenik meg.
- A `attempt_status` az `app.run_attempt_status` enumot hasznalja.
- A `run_logs` append-only audit/log reteg.
- A `run_queue` nem result tabla.
- A `run_logs` nem export artifact tabla.
- A result / artifact / projection vilag kulon T3 task marad.
- Az `app` schema marad a canonical celterulet.

### DoD
- [ ] Letrejon a `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql`
      fajl.
- [ ] A migracio letrehozza az `app.run_queue` tablata.
- [ ] A migracio letrehozza az `app.run_logs` tablata.
- [ ] A queue tabla kapcsolodik az `app.nesting_runs` es `app.nesting_run_snapshots`
      tablavilaghoz.
- [ ] A queue tabla hasznalja az `app.run_attempt_status` enumot.
- [ ] A queue tabla formalizalja a pending/leased/done/error jellegu queue allapotot.
- [ ] A queue tabla rendelkezik lease/heartbeat/retry mezokkel.
- [ ] A log tabla append-only, kulon log event tarolo.
- [ ] A task nem hoz letre kulon `run_attempts` tablat.
- [ ] A migracio nem hoz letre result/artifact/projection tablakat.
- [ ] A task nem ad hozza RLS policyt.
- [ ] A `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`,
      a `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
      es a `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
      minimalisan szinkronba kerul a konkret H0-E5-T2 irannyal.
- [ ] A report DoD -> Evidence Matrix konkret fajl- es line-hivatkozasokkal kitoltott.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h0_e5_t2_queue_es_log_modellek.md`
      PASS.

### Kockazat + rollback
- Kockazat:
  - a task veletlenul kulon `run_attempts` tablat hoz letre, es szetszedi a backlog
    egyszerubb H0 T2 scope-jat;
  - a queue tabla tul sok result/projection logikat kap;
  - a log tabla export artifact jellegu tarolova valik;
  - a docs tovabbra is nem egyertelmu az attempt fogalmi/fizikai helyevel kapcsolatban.
- Mitigacio:
  - backlog-outputhoz ragaszkodo fizikai output: `run_queue` + `run_logs`;
  - attempt semantics a queue sorban (`attempt_no`, `attempt_status`, lease mezok);
  - result/artifact/projection explicit out-of-scope;
  - minimal docs sync a T2 source-of-truth iranyhoz.
- Rollback:
  - a migracio + checklist/report + minimal docs edit egy commitban visszavonhato.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h0_e5_t2_queue_es_log_modellek.md`
- Manualis ellenorzes:
  - pontosan csak `app.run_queue` es `app.run_logs` jon letre;
  - nincs kulon `run_attempts` tabla;
  - a queue kapcsolodik a T1 run + snapshot vilaghoz;
  - van queue_state + attempt_status + lease/heartbeat/retry mezokeszlet;
  - a log tabla append-only es kulon van;
  - nincs result/artifact/projection tabla;
  - nincs RLS.

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql`
- `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql`
