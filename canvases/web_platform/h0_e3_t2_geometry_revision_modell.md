
# H0-E3-T2 geometry revision modell

## Funkcio
A feladat a web platform geometry es revision gerincenek kovetkezo schema-lepese:
az `app.geometry_revisions` tabla letetele, amely a nyers file-object vilag es a
kesobbi validation / review / derivative / binding retegek koze helyezi a
formalizalt canonical geometry revision reget.

Ez a task kozvetlenul a H0-E3-T1 `file_objects` tabla utan kovetkezik.
A cel, hogy a rendszerben letezzen kulon, verziozhato belso geometria-objektum:
- ami visszavezetheto egy source file-ra,
- ami JSON-alapu canonical geometry truth-ot tud hordozni,
- ami tarolja a canonical format versiont,
- de meg nem keveredik ossze sem a validation reporttal, sem a review actionnel,
  sem a derivative vilaggal.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - uj Supabase migracio letrehozasa az `app.geometry_revisions` tablaval;
  - canonical geometry revision metadata + source lineage lerakasa;
  - kapcsolat az `app.file_objects`, `app.projects`, es ha indokolt, `app.profiles`
    tablakkal;
  - `geometry_role`, `geometry_validation_status` es canonical format version
    gyakorlati hasznalata;
  - minimalis JSON-alapu canonical geometry truth helye a tablaban;
  - PK/FK kapcsolatok, alap indexek es revision-integritas letetele;
  - minimal docs szinkron, ha a fo architecture/H0 doksikban a geometry-revision
    blokk meg stale, `public.*` schemaju vagy ownership szempontbol pontatlan.
- Nincs benne:
  - `geometry_validation_reports` tabla;
  - `geometry_review_actions` tabla;
  - `geometry_derivatives` tabla;
  - part/sheet binding vagy mapping tabla;
  - run request / snapshot / attempt tabla;
  - export/manufacturing artifact tabla;
  - RLS policy;
  - API endpoint implementacio.

### Fo kerdesek, amiket le kell zarni
- [ ] Mi a geometry revision minimalis, de mar hasznalhato oszlopkeszlete?
- [ ] Mely mezok legyenek explicit oszlopok, es mi maradjon a canonical JSON-ban?
- [ ] Hogyan legyen a source file -> geometry revision kapcsolat egyertelmu?
- [ ] Kell-e projekt-szintu direkt FK is, vagy eleg a file-object lineage?
- [ ] Milyen revision-szintu uniqueness kell?
- [ ] Hogyan kulonuljon el a geometry revision a validation / review / derivative vilagtol?

### Feladatlista
- [ ] Kesz legyen a task teljes artefaktlanca.
- [ ] Letrejojjon a kovetkezo H0 migracio az `app.geometry_revisions` tablaval.
- [ ] A migracio kapcsolja a geometry revision rekordot egy source `app.file_objects`
      rekordhoz.
- [ ] A migracio tarolja a canonical format versiont.
- [ ] A migracio biztositson JSON-alapu canonical geometry helyet.
- [ ] A task ne hozzon letre validation/review/derivative/run/export tablakat.
- [ ] Minimal docs szinkron tortenjen, ha szukseges.
- [ ] Repo gate le legyen futtatva a reporton.

### Erintett fajlok
- `canvases/web_platform/h0_e3_t2_geometry_revision_modell.md`
- `codex/goals/canvases/web_platform/fill_canvas_h0_e3_t2_geometry_revision_modell.yaml`
- `codex/prompts/web_platform/h0_e3_t2_geometry_revision_modell/run.md`
- `codex/codex_checklist/web_platform/h0_e3_t2_geometry_revision_modell.md`
- `codex/reports/web_platform/h0_e3_t2_geometry_revision_modell.md`
- `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`

### Elvart tabla-irany
A konkret oszlopok kod kozben finomithatok, de az irany ez legyen:

- `app.geometry_revisions`
  - `id uuid primary key default gen_random_uuid()`
  - `project_id uuid not null references app.projects(id) on delete cascade`
  - `source_file_object_id uuid not null references app.file_objects(id) on delete restrict`
  - `geometry_role app.geometry_role not null`
  - `revision_no integer not null`
  - `status app.geometry_validation_status not null default 'uploaded'`
  - `canonical_format_version text not null`
  - `canonical_geometry_jsonb jsonb`
  - `canonical_hash_sha256 text`
  - opcionálisan `source_hash_sha256 text`
  - opcionálisan `bbox_jsonb jsonb`
  - opcionálisan `created_by uuid references app.profiles(id) on delete set null`
  - `created_at timestamptz not null default now()`
  - `updated_at timestamptz not null default now()`

### Elvart integritas es indexek
- `check (revision_no > 0)`
- `check (length(btrim(canonical_format_version)) > 0)`
- revision uniqueness legalabb egyik iranyban:
  - `unique (source_file_object_id, revision_no)`
- index legalabb:
  - `idx_geometry_revisions_project_id` on `(project_id)`
  - `idx_geometry_revisions_source_file_object_id` on `(source_file_object_id)`
  - opcionálisan `idx_geometry_revisions_status` ha indokolt
- ha a projekt lineage direkt FK-val is bekerul, legyen egyertelmu, hogy ez nem valtja ki
  a source-file lineage-t, csak query/ownership segedlet

### Fontos modellezesi elvek
- A geometry revision a canonical geometry truth helye.
- Ez nem validation report tabla.
- Ez nem review action tabla.
- Ez nem derivative tabla.
- A canonical geometry a H0 source-of-truth elv szerint JSON-alapu es verziozott.
- A validation/review kulon taskban jon.
- A derivative vilag kulon taskban jon.
- Az `app` schema maradjon canonical celterulet.

### DoD
- [ ] Letrejon a `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql`
      fajl.
- [ ] A migracio letrehozza az `app.geometry_revisions` tablata.
- [ ] A geometry revision rekord visszavezetheto egy source `app.file_objects` rekordra.
- [ ] A tabla tarolja a canonical format versiont.
- [ ] A tabla rendelkezik JSON-alapu canonical geometry hellyel.
- [ ] A migracio nem hoz letre validation/review/derivative/run/export tablakat.
- [ ] A task nem ad hozza RLS policyt.
- [ ] A `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
      es a `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
      minimalisan szinkronba kerul a konkret migracios irannyal, ha szukseges.
- [ ] A report DoD -> Evidence Matrix konkret fajl- es line-hivatkozasokkal kitoltott.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h0_e3_t2_geometry_revision_modell.md`
      PASS.

### Kockazat + rollback
- Kockazat:
  - a geometry revision tabla tul sok validation vagy derivative logikat kap;
  - a canonical geometry csak metadata-vaza marad, es nem lesz egyertelmu truth helye;
  - a source lineage nincs eleg eros integritassal rogzitve;
  - a docs tovabbra is `public.*` vagy ownership-szinten pontatlan iranyt sugaroz.
- Mitigacio:
  - a tabla maradjon canonical geometry revision truth;
  - validation/review/derivative explicit out-of-scope;
  - source file lineage kotelezo FK legyen;
  - minimal docs sync a canonical `app.*` iranyhoz.
- Rollback:
  - a migracio + checklist/report + minimal docs edit egy commitban visszavonhato.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h0_e3_t2_geometry_revision_modell.md`
- Manualis ellenorzes:
  - pontosan csak az `app.geometry_revisions` tabla jon letre;
  - nincs validation/review/derivative/run/export tabla;
  - a source file lineage megvan;
  - a canonical format version tarolt;
  - van JSON-alapu canonical geometry hely;
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
- `docs/web_platform/roadmap/dxf_nesting_platform_priorizalt_sprint_backlog_p0_p1_p2.md`
- `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql`
