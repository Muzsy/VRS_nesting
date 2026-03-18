# H0-E5-T1 nesting run es snapshot modellek

## Funkcio
A feladat a web platform H0 run gerincenek elso schema-lepese:
az `app.nesting_runs` es `app.nesting_run_snapshots` tablavilag letetele.

Ez a task kozvetlenul a H0-E3-T4 utan kovetkezik.
A cel, hogy a run-vilag ne elvontan, hanem mar konkret adatbazis-szinten is
elkulonitse:

- a **Run Request** aggregate-et,
- az ahhoz tartozo **Run Snapshot** immutable truthot,
- es ezzel megalapozza a kesobbi queue / attempt / result / projection retegeket.

Fontos modell-dontes ehhez a taskhoz:
- a fizikai tabla-nevek H0-ban maradjanak `app.nesting_runs` es
  `app.nesting_run_snapshots`;
- a dokumentacio mondja ki expliciten, hogy ezek a fogalmi
  **Run Request** illetve **Run Snapshot** taroloi;
- queue / attempt / result / artifact meg nincs scope-ban.

Ez tovabbra is kontrollalt H0 scope:
- queue / lease / run_logs kulon task,
- result / artifact / projection kulon task,
- RLS kulon task,
- API / worker implementacio meg nincs scope-ban.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - uj Supabase migracio letrehozasa az `app.nesting_runs` es
    `app.nesting_run_snapshots` tablakkal;
  - az `app.run_request_status` es `app.run_snapshot_status` enumok
    gyakorlati hasznalata;
  - 1:1 kapcsolat a run request aggregate es a hozza tartozo snapshot kozott;
  - minimalis, de mar hasznalhato request metadata hely letetele;
  - minimalis, immutable snapshot payload blokk letetele;
  - snapshot hash es alap indexek / integritas letetele;
  - minimal docs szinkron a run-vilag source-of-truth iranyahoz.
- Nincs benne:
  - `run_queue` vagy `run_attempts` tabla;
  - `run_logs` tabla;
  - `run_results`, `run_artifacts`, `run_layout_*`, `run_metrics` tablavilag;
  - worker lease / heartbeat / timeout implementacio;
  - API endpoint vagy worker kod;
  - RLS policy.

### Fo kerdesek, amiket le kell zarni
- [ ] Mi legyen a minimalis, de mar hasznalhato request-oldali oszlopkeszlet?
- [ ] Mi legyen a snapshot minimalis payload-bontas: egy nagy blob vagy strukturalt
      manifest reszek?
- [ ] Hogyan rogzitjuk a snapshot immutabilitast mar schema-szinten?
- [ ] Milyen hash es statuszmezok szuksegesek H0-ban, hogy a kesobbi queue/result
      vilag stabil alapot kapjon?
- [ ] Hogyan legyen kimondva a docsban a fogalmi Run Request / Run Snapshot es a
      fizikai `nesting_runs` / `nesting_run_snapshots` viszony?

### Feladatlista
- [ ] Kesz legyen a task teljes artefaktlanca.
- [ ] Letrejojjon a kovetkezo H0 migracio az `app.nesting_runs` tablaval.
- [ ] Letrejojjon a kovetkezo H0 migracio az `app.nesting_run_snapshots` tablaval.
- [ ] A run tabla az `app.run_request_status` enumot hasznalja.
- [ ] A snapshot tabla az `app.run_snapshot_status` enumot hasznalja.
- [ ] A snapshot rekord 1:1 kapcsolatban legyen egy run rekorddal.
- [ ] A snapshot tabla tartalmazzon hash-et es strukturalt payload-helyet.
- [ ] A task ne hozzon letre queue/log/result/artifact/projection tablakat.
- [ ] Minimal docs szinkron tortenjen a run-vilag source-of-truth iranyahoz.
- [ ] Repo gate le legyen futtatva a reporton.

### Erintett fajlok
- `canvases/web_platform/h0_e5_t1_nesting_run_es_snapshot_modellek.md`
- `codex/goals/canvases/web_platform/fill_canvas_h0_e5_t1_nesting_run_es_snapshot_modellek.yaml`
- `codex/prompts/web_platform/h0_e5_t1_nesting_run_es_snapshot_modellek/run.md`
- `codex/codex_checklist/web_platform/h0_e5_t1_nesting_run_es_snapshot_modellek.md`
- `codex/reports/web_platform/h0_e5_t1_nesting_run_es_snapshot_modellek.md`
- `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`

### Elvart tabla-irany
A konkret oszlopok kod kozben finomithatok, de az irany ez legyen:

- `app.nesting_runs`
  - `id uuid primary key default gen_random_uuid()`
  - `project_id uuid not null references app.projects(id) on delete cascade`
  - `requested_by uuid references app.profiles(id) on delete set null`
  - `status app.run_request_status not null default 'draft'`
  - `run_purpose text not null default 'nesting'`
  - `idempotency_key text`
  - `request_payload_jsonb jsonb not null default '{}'::jsonb`
  - `created_at timestamptz not null default now()`
  - `updated_at timestamptz not null default now()`

- `app.nesting_run_snapshots`
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
  - opcionálisan `manufacturing_manifest_jsonb jsonb not null default '{}'::jsonb`
  - `created_by uuid references app.profiles(id) on delete set null`
  - `created_at timestamptz not null default now()`

### Elvart integritas es indexek
- `app.nesting_runs`
  - check: `length(btrim(run_purpose)) > 0`
  - index legalabb:
    - `idx_nesting_runs_project_id_created_at_desc` on `(project_id, created_at desc)`
    - opcionálisan `idx_nesting_runs_status` on `(status)`
- `app.nesting_run_snapshots`
  - `unique (run_id)` a 1:1 kapcsolathoz
  - check: `length(btrim(snapshot_version)) > 0`
  - unique index vagy legalabb dedikalt index a `snapshot_hash_sha256` mezon,
    ahol ez ertelmesen hasznalhato
  - index legalabb:
    - `idx_nesting_run_snapshots_status` on `(status)`

### Fontos modellezesi elvek
- A `nesting_runs` H0-ban a fogalmi **Run Request** aggregate fizikai taroloja.
- A `nesting_run_snapshots` H0-ban a fogalmi **Run Snapshot** immutable truth
  fizikai taroloja.
- A worker kesobb csak snapshotbol dolgozhat, de worker/attempt mechanika most
  meg nincs scope-ban.
- A snapshot append-only szemantikaju legyen: ne kapjon `updated_at` mezot.
- A request es a snapshot ne mosodjon ossze egyetlen tablava.
- A queue / attempt / result / artifact / projection vilag kulon task marad.
- Az `app` schema marad a canonical celterulet.

### DoD
- [ ] Letrejon a `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql`
      fajl.
- [ ] A migracio letrehozza az `app.nesting_runs` tablata.
- [ ] A migracio letrehozza az `app.nesting_run_snapshots` tablata.
- [ ] A run tabla az `app.run_request_status` enumot hasznalja.
- [ ] A snapshot tabla az `app.run_snapshot_status` enumot hasznalja.
- [ ] A snapshot rekord 1:1 kapcsolatban van a run rekorddal.
- [ ] A snapshot tabla tartalmaz hash-et es strukturalt payload-helyet.
- [ ] A run tabla rendelkezik minimalis request-oldali metadata hellyel.
- [ ] A migracio nem hoz letre queue/log/result/artifact/projection tablakat.
- [ ] A task nem ad hozza RLS policyt.
- [ ] A `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`,
      a `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
      es a `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
      minimalisan szinkronba kerul a konkret H0-E5-T1 irannyal.
- [ ] A report DoD -> Evidence Matrix konkret fajl- es line-hivatkozasokkal kitoltott.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h0_e5_t1_nesting_run_es_snapshot_modellek.md`
      PASS.

### Kockazat + rollback
- Kockazat:
  - a run es snapshot megint egy tablava olvad;
  - a task veletlenul atcsuszik queue/result/artifact iranyba;
  - a docs tovabbra is fogalmi es fizikai naming konfliktust hordoz;
  - a snapshot tabla tul „elo” lesz, es elveszik az immutabilitas jelentese.
- Mitigacio:
  - expliciten kulon tabla a request es a snapshot szamara;
  - `updated_at` csak a request-oldalon, snapshoton nem;
  - queue/result/artifact explicit out-of-scope;
  - minimal docs sync a run-vilag canonical H0 iranyahoz.
- Rollback:
  - a migracio + checklist/report + minimal docs edit egy commitban visszavonhato.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h0_e5_t1_nesting_run_es_snapshot_modellek.md`
- Manualis ellenorzes:
  - pontosan csak `app.nesting_runs` es `app.nesting_run_snapshots` jon letre;
  - nincs `run_queue`, `run_logs`, `run_results`, `run_artifacts`, `run_layout_*`, `run_metrics` tabla;
  - a request es a snapshot fizikailag kulon van;
  - a statusz enumok helyesen hasznaltak;
  - van snapshot hash es strukturalt manifest-hely;
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
- `supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql`
- `supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql`
- `supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql`
- `supabase/migrations/20260311000000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql`
- `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql`
- `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql`
- `supabase/migrations/20260312005000_h0_e3_t3_validation_es_review_tablak.sql`
- `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql`
