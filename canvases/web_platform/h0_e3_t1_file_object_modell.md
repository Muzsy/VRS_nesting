# H0-E3-T1 file object modell

## Funkcio
A feladat a web platform H0-E3 geometry es revision gerincenek elso valodi schema-lepese:
az `app.file_objects` tabla letetele, amely a storage-ban tarolt nyers fajlok
metaadat- es hivatkozasi reteget adja.

Ez a task a projekt-, technology-, part- es sheet-domain bazis utan a kovetkezo
helyes lepés: el kell kuloniteni a nyers file-vilagot a geometry revision,
derivative, run snapshot es artifact vilagtol.

A cel, hogy a platformnak legyen canonical file-referencialis truth-ja:
- melyik projecthez tartozik a fajl,
- hol van storage-ban,
- mi a fajl tipusa,
- ki toltotte fel,
- mi a tartalmi hash / byte size / MIME alapmeta,
mikozben meg mindig kontrollalt scope-ban maradunk.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - uj Supabase migracio letrehozasa az `app.file_objects` tablaval;
  - a storage-metaadat es project-kapcsolat lerakasa;
  - PK/FK kapcsolatok es alap indexek letetele;
  - `file_kind` enum gyakorlati hasznalata;
  - egyertelmu ownership: file object != geometry revision != artifact;
  - minimal docs szinkron, ha a fo architecture/H0 doksikban a file-domain
    blokk meg stale, `public.*` schemaju vagy ownership szempontbol pontatlan.
- Nincs benne:
  - storage bucket policy;
  - storage bucket letrehozas;
  - geometry_revisions tabla;
  - geometry_validation_reports tabla;
  - geometry_review_actions tabla;
  - geometry_derivatives tabla;
  - run request / snapshot / attempt tabla;
  - export / artifact tabla;
  - RLS policy;
  - API endpoint implementacio.

### Fo kerdesek, amiket le kell zarni
- [ ] Mi a file object minimalis, de elegseges oszlopkeszlete?
- [ ] Mi maradjon explicit oszlop, es mi maradjon kesobbi metadata/JSON vilag?
- [ ] Milyen egyedi constraint kell a storage hivatkozas vedelmere?
- [ ] Hogyan kulonuljon el a file object a geometry revisiontol?
- [ ] Hogyan keruljuk el, hogy a file object mar most artifact- vagy export-tabla legyen?

### Feladatlista
- [ ] Kesz legyen a task teljes artefaktlanca.
- [ ] Letrejojjon a kovetkezo H0 migracio az `app.file_objects` tablaval.
- [ ] A migracio helyesen kapcsolodjon az `app.projects` es `app.profiles` tablakhhoz.
- [ ] Legyen egyedi vedelme a storage-beli hivatkozasnak.
- [ ] A task ne hozzon letre geometry / derivative / review / run / export tablakat.
- [ ] Minimal docs szinkron tortenjen, ha szukseges.
- [ ] Repo gate le legyen futtatva a reporton.

### Erintett fajlok
- `canvases/web_platform/h0_e3_t1_file_object_modell.md`
- `codex/goals/canvases/web_platform/fill_canvas_h0_e3_t1_file_object_modell.yaml`
- `codex/prompts/web_platform/h0_e3_t1_file_object_modell/run.md`
- `codex/codex_checklist/web_platform/h0_e3_t1_file_object_modell.md`
- `codex/reports/web_platform/h0_e3_t1_file_object_modell.md`
- `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`

### Elvart tabla-irany
A konkret oszlopok kod kozben finomithatok, de az irany ez legyen:

- `app.file_objects`
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

### Elvart integritas es indexek
- `unique (storage_bucket, storage_path)`
- check-ek:
  - `storage_bucket` nem ures
  - `storage_path` nem ures
  - `file_name` nem ures
  - ha van `byte_size`, akkor `byte_size >= 0`
- index legalabb:
  - `idx_file_objects_project_id` on `(project_id)`
  - opcionálisan `idx_file_objects_uploaded_by` ha indokolt

### Fontos modellezesi elvek
- `file_objects` a nyers storage-referenciás objektumvilag.
- Ez nem geometry revision truth.
- Ez nem derivative tabla.
- Ez nem export artifact tabla.
- A geometry pipeline kovetkezo taskban erre fog ulni, de most meg nem kell
  geometry JSON vagy audit report mezot beletenni.
- Az `app` schema maradjon canonical celterulet.

### DoD
- [ ] Letrejon a `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql`
      fajl.
- [ ] A migracio letrehozza az `app.file_objects` tablata.
- [ ] A tabla helyesen kapcsolodik az `app.projects` es `app.profiles` tablakhhoz.
- [ ] A storage hivatkozas egyedisege vedett.
- [ ] A migracio nem hoz letre geometry/review/derivative/run/export tablakat.
- [ ] A task nem ad hozza RLS policyt.
- [ ] A `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
      es a `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
      minimalisan szinkronba kerul a konkret migracios irannyal, ha szukseges.
- [ ] A report DoD -> Evidence Matrix konkret fajl- es line-hivatkozasokkal kitoltott.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h0_e3_t1_file_object_modell.md`
      PASS.

### Kockazat + rollback
- Kockazat:
  - a file object tabla tul sok geometry vagy artifact logikat kap;
  - a storage referenciak nincsenek eleg eros uniqueness vedelm alatt;
  - a docs tovabbra is `public.*` vagy ownership-szinten pontatlan iranyt sugaroz.
- Mitigacio:
  - a tabla maradjon metadata + storage-reference vilag;
  - explicit unique `(storage_bucket, storage_path)`;
  - minimal docs sync a canonical `app.*` iranyhoz.
- Rollback:
  - a migracio + checklist/report + minimal docs edit egy commitban visszavonhato.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h0_e3_t1_file_object_modell.md`
- Manualis ellenorzes:
  - pontosan csak az `app.file_objects` tabla jon letre;
  - nincs geometry/review/derivative/run/export tabla;
  - a storage uniqueness megvan;
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
