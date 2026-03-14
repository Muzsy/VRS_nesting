# H0-E5-T3 artifact es projection modellek

## Funkcio
A feladat a web platform H0 run gerincenek harmadik schema-lepese:
az output oldali artifact- es projection-tablavilag letetele.

Ez a task kozvetlenul a H0-E5-T2 utan kovetkezik.
A cel, hogy a run-vilagnak ne csak request/snapshot/queue/log retege legyen,
hanem legyen kulon, explicit helye:

- a file/blob jellegu output artifactoknak,
- a frontend/riport oldalon query-zheto layout projectionnek,
- es a tomoritett run-level metrikaknak.

Fontos modell-dontes ehhez a taskhoz:
- a fizikai output H0-ban a backlog szerint maradjon:
  - `app.run_artifacts`
  - `app.run_layout_sheets`
  - `app.run_layout_placements`
  - `app.run_layout_unplaced`
  - `app.run_metrics`
- **kulon `app.run_results` tabla most ne jojjon letre**;
- a fogalmi result reteg H0-E5-T3-ban a `run_metrics` + `run_layout_*` +
  `run_artifacts` egyuttessel legyen formalizalva;
- a projection es az artifact ne mosodjon ossze.

Ez tovabbra is kontrollalt H0 scope:
- request/snapshot bazis mar kesz a T1-ben,
- queue/log bazis mar kesz a T2-ben,
- storage bucket strategia kulon task,
- RLS kulon task,
- API / worker implementacio meg nincs scope-ban.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - uj Supabase migracio letrehozasa az `app.run_artifacts`,
    `app.run_layout_sheets`, `app.run_layout_placements`,
    `app.run_layout_unplaced`, `app.run_metrics` tablakkal;
  - az `app.artifact_kind` enum gyakorlati hasznalata;
  - projection vs artifact formalizalt szetvalasztasa;
  - minimalis, de mar stabil layout projection reteg letetele;
  - run-level metrics tabla letetele;
  - minimal docs szinkron a T3 source-of-truth iranyhoz,
    kulonosen a stale `public.run_layout_*`, `public.run_metrics`
    es `run_results` maradvanyok helyretetele.
- Nincs benne:
  - kulon `run_results` tabla;
  - artifact byte-level storage policy;
  - storage bucket policy / naming reszletes szabalyai;
  - SVG/DXF/report artifact generalas;
  - worker result normalizer implementacio;
  - API endpoint vagy worker kod;
  - RLS policy.

### Fo kerdesek, amiket le kell zarni
- [ ] Mi legyen a minimalis, de mar hasznalhato artifact tabla oszlopkeszlet?
- [ ] Mi legyen a minimalis layout projection oszlopkeszlet H0-ban ugy,
      hogy H1-ben bovitheto maradjon?
- [ ] Hogyan legyen kulon a query-zheto projection es a file/blob artifact?
- [ ] Hogyan legyen formalizalva a run-level metrika tabla kulon `run_results`
      aggregate nelkul?
- [ ] Hogyan legyen docs-szinten egyertelmu, hogy a T3-ban nincs kulon
      `run_results` tabla, es ez nem hiany, hanem szandekos modell-dontes?

### Feladatlista
- [ ] Kesz legyen a task teljes artefaktlanca.
- [ ] Letrejojjon a kovetkezo H0 migracio az `app.run_artifacts` tablaval.
- [ ] Letrejojjon a kovetkezo H0 migracio az `app.run_layout_sheets` tablaval.
- [ ] Letrejojjon a kovetkezo H0 migracio az `app.run_layout_placements` tablaval.
- [ ] Letrejojjon a kovetkezo H0 migracio az `app.run_layout_unplaced` tablaval.
- [ ] Letrejojjon a kovetkezo H0 migracio az `app.run_metrics` tablaval.
- [ ] Az artifact tabla hasznalja az `app.artifact_kind` enumot.
- [ ] Az artifact es projection reteg fizikailag kulon maradjon.
- [ ] A task ne hozzon letre kulon `app.run_results` tablat.
- [ ] A task ne vezessen be meg storage bucket policy / RLS / worker logikat.
- [ ] Minimal docs szinkron tortenjen a T3 source-of-truth iranyhoz.
- [ ] Repo gate le legyen futtatva a reporton.

### Erintett fajlok
- `canvases/web_platform/h0_e5_t3_artifact_es_projection_modellek.md`
- `codex/goals/canvases/web_platform/fill_canvas_h0_e5_t3_artifact_es_projection_modellek.yaml`
- `codex/prompts/web_platform/h0_e5_t3_artifact_es_projection_modellek/run.md`
- `codex/codex_checklist/web_platform/h0_e5_t3_artifact_es_projection_modellek.md`
- `codex/reports/web_platform/h0_e5_t3_artifact_es_projection_modellek.md`
- `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`

### Elvart tabla-irany
A konkret oszlopok kod kozben finomithatok, de az irany ez legyen:

- `app.run_artifacts`
  - `id uuid primary key default gen_random_uuid()`
  - `run_id uuid not null references app.nesting_runs(id) on delete cascade`
  - opcionálisan `snapshot_id uuid references app.nesting_run_snapshots(id) on delete set null`
  - `artifact_kind app.artifact_kind not null`
  - `storage_bucket text not null`
  - `storage_path text not null`
  - `metadata_jsonb jsonb not null default '{}'::jsonb`
  - `created_at timestamptz not null default now()`

- `app.run_layout_sheets`
  - `id uuid primary key default gen_random_uuid()`
  - `run_id uuid not null references app.nesting_runs(id) on delete cascade`
  - `sheet_index integer not null`
  - `sheet_revision_id uuid references app.sheet_revisions(id) on delete set null`
  - `width_mm numeric(12,3)`
  - `height_mm numeric(12,3)`
  - `utilization_ratio numeric(8,5)`
  - `metadata_jsonb jsonb not null default '{}'::jsonb`
  - opcionálisan `created_at timestamptz not null default now()`
  - `unique (run_id, sheet_index)`

- `app.run_layout_placements`
  - `id uuid primary key default gen_random_uuid()`
  - `run_id uuid not null references app.nesting_runs(id) on delete cascade`
  - `sheet_id uuid not null references app.run_layout_sheets(id) on delete cascade`
  - `placement_index integer not null`
  - `part_revision_id uuid references app.part_revisions(id) on delete set null`
  - `quantity integer not null default 1`
  - `transform_jsonb jsonb not null`
  - `bbox_jsonb jsonb not null default '{}'::jsonb`
  - `metadata_jsonb jsonb not null default '{}'::jsonb`
  - opcionálisan `created_at timestamptz not null default now()`
  - `unique (sheet_id, placement_index)`

- `app.run_layout_unplaced`
  - `id uuid primary key default gen_random_uuid()`
  - `run_id uuid not null references app.nesting_runs(id) on delete cascade`
  - `part_revision_id uuid references app.part_revisions(id) on delete set null`
  - `remaining_qty integer not null`
  - `reason text`
  - `metadata_jsonb jsonb not null default '{}'::jsonb`
  - opcionálisan `created_at timestamptz not null default now()`

- `app.run_metrics`
  - `run_id uuid primary key references app.nesting_runs(id) on delete cascade`
  - `placed_count integer not null default 0`
  - `unplaced_count integer not null default 0`
  - `used_sheet_count integer not null default 0`
  - `utilization_ratio numeric(8,5)`
  - `remnant_value numeric(14,2)`
  - `metrics_jsonb jsonb not null default '{}'::jsonb`
  - opcionálisan `created_at timestamptz not null default now()`

### Elvart integritas es indexek
- `app.run_artifacts`
  - check legalabb:
    - `length(btrim(storage_bucket)) > 0`
    - `length(btrim(storage_path)) > 0`
  - index legalabb:
    - `idx_run_artifacts_run` on `(run_id)`
  - opcionálisan uniqueness:
    - `unique (storage_bucket, storage_path)` ha ez nem okoz blast radius novelest
- `app.run_layout_sheets`
  - `sheet_index >= 0` vagy `sheet_index > 0`, de ez legyen egyertelmu es docsban is ugyanaz
  - `unique (run_id, sheet_index)`
- `app.run_layout_placements`
  - `placement_index >= 0` vagy `placement_index > 0`, de ez legyen egyertelmu es docsban is ugyanaz
  - `quantity > 0`
  - `unique (sheet_id, placement_index)`
  - index legalabb:
    - `idx_run_layout_placements_sheet_id_placement_index` on `(sheet_id, placement_index)`
- `app.run_layout_unplaced`
  - `remaining_qty > 0`
- `app.run_metrics`
  - `placed_count >= 0`
  - `unplaced_count >= 0`
  - `used_sheet_count >= 0`

### Fontos modellezesi elvek
- Az `app.run_artifacts` file/blob jellegu output reteg.
- Az `app.run_layout_*` query-zheto projection reteg.
- Az `app.run_metrics` a run-level osszegzett eredmeny reteg.
- **Kulon `app.run_results` tabla H0-E5-T3-ban nincs.**
- A projection es az artifact nem ugyanaz, es fizikailag kulon marad.
- A T3 nem storage policy task.
- A T3 nem RLS task.
- A T3 nem worker implementacios task.
- Az `app` schema marad a canonical celterulet.

### DoD
- [ ] Letrejon a `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql`
      fajl.
- [ ] A migracio letrehozza az `app.run_artifacts` tablata.
- [ ] A migracio letrehozza az `app.run_layout_sheets` tablata.
- [ ] A migracio letrehozza az `app.run_layout_placements` tablata.
- [ ] A migracio letrehozza az `app.run_layout_unplaced` tablata.
- [ ] A migracio letrehozza az `app.run_metrics` tablata.
- [ ] Az artifact tabla hasznalja az `app.artifact_kind` enumot.
- [ ] Az artifact es projection reteg fizikailag kulon marad.
- [ ] A task nem hoz letre kulon `app.run_results` tablat.
- [ ] A task nem ad hozza storage bucket policyt vagy RLS policyt.
- [ ] A `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`,
      a `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
      es a `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
      minimalisan szinkronba kerul a konkret H0-E5-T3 irannyal.
- [ ] A docsban a stale `public.run_layout_*`, `public.run_metrics` es `run_results`
      maradvanyok a T3-kozelben helyre vannak teve.
- [ ] A report DoD -> Evidence Matrix konkret fajl- es line-hivatkozasokkal kitoltott.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h0_e5_t3_artifact_es_projection_modellek.md`
      PASS.

### Kockazat + rollback
- Kockazat:
  - a task veletlenul kulon `run_results` tablat hoz letre;
  - a projection es artifact egy tablaba mosodik;
  - a docs tovabbra is `public.*` projection maradvanyokat hordoz;
  - a task belecsuszik storage policy vagy worker implementacios iranyba.
- Mitigacio:
  - backlog-outputhoz ragaszkodo fizikai output: `run_artifacts` + `run_layout_*` + `run_metrics`;
  - kulon modell-dontes: nincs `run_results` tabla;
  - minimal docs sync a T3 source-of-truth iranyhoz;
  - storage/RLS/worker explicit out-of-scope.
- Rollback:
  - a migracio + checklist/report + minimal docs edit egy commitban visszavonhato.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h0_e5_t3_artifact_es_projection_modellek.md`
- Manualis ellenorzes:
  - pontosan csak `app.run_artifacts`, `app.run_layout_sheets`,
    `app.run_layout_placements`, `app.run_layout_unplaced`, `app.run_metrics` jon letre;
  - nincs kulon `app.run_results` tabla;
  - az artifact tabla enumos es kulon marad a projectiontol;
  - a projection tablavilag runhoz kotott;
  - nincs storage policy / RLS / worker kod;
  - a docsban a kozeli stale `public.*` projection maradvanyok el vannak takaritva.

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
- `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql`
