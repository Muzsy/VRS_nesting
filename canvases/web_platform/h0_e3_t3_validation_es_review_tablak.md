
# H0-E3-T3 validation es review tablak

## Funkcio
A feladat a web platform geometry audit es review retegenek kovetkezo schema-lepese:
az `app.geometry_validation_reports` es az `app.geometry_review_actions` tablavilag
letetele.

Ez a task kozvetlenul a H0-E3-T2 `geometry_revisions` tabla utan kovetkezik.
A cel, hogy a canonical geometry truth es a kesobbi derivative / part-binding /
run vilag koze bekeruljon egy formalizalt audit es emberi review reteg:

- a geometry revisionhoz tobbszori validator-futas / audit riport tarolhato,
- a review dontesek kulon, explicit entitaskent jelennek meg,
- a validation report es review action ownershipja nem csuszik ossze a geometry
  revision truth-tal.

Ez a task meg mindig kontrollalt H0 scope:
- derivative tabla kulon task,
- part/sheet binding kulon task,
- run snapshot/orchestration kulon task,
- RLS es API meg nincs scope-ban.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - uj Supabase migracio letrehozasa a `geometry_validation_reports` es
    `geometry_review_actions` tablakkal;
  - a validation report audit-reteg formalizalasa;
  - a review action emberi/jovahagyo reteg formalizalasa;
  - kapcsolatok az `app.geometry_revisions` tablaval;
  - ha szukseges, minimalis uj enum(ok) vagy check constraint a review action
    tipusanak vedelmere;
  - kompozit integritas annak vedelmere, hogy egy review action csak ugyanahhoz a
    geometry revisionhoz tartozo validation reportot hivatkozhasson;
  - PK/FK kapcsolatok, alap indexek es audit integritas letetele;
  - minimal docs szinkron, ha a fo architecture/H0 doksikban a validation/review
    blokk meg stale, `public.*` schemaju vagy ownership szempontbol pontatlan.
- Nincs benne:
  - `geometry_derivatives` tabla;
  - part/sheet geometry binding tabla;
  - run request / snapshot / attempt tabla;
  - export/manufacturing artifact tabla;
  - RLS policy;
  - API endpoint implementacio.

### Fo kerdesek, amiket le kell zarni
- [ ] Mi a validation report minimalis, de mar hasznalhato oszlopkeszlete?
- [ ] Mi legyen explicit oszlop, es mi maradjon JSON report/szummary vilag?
- [ ] Hogyan taroljuk a tobbszori validation futasokat egy geometry revision alatt?
- [ ] Mi legyen a review action minimalis, de audit-szinten korrekt modellje?
- [ ] Hogyan vedjuk meg, hogy a review action csak a sajat geometry revision
      validation reportjara mutathasson?
- [ ] Hogyan maradjon kulon a geometry truth, a validation report es a review action?

### Feladatlista
- [ ] Kesz legyen a task teljes artefaktlanca.
- [ ] Letrejojjon a kovetkezo H0 migracio a validation es review tablakkal.
- [ ] A migracio letrehozza az `app.geometry_validation_reports` tablata.
- [ ] A migracio letrehozza az `app.geometry_review_actions` tablata.
- [ ] A validation report kapcsolodjon az `app.geometry_revisions` tablaho.
- [ ] A review action kapcsolodjon az `app.geometry_revisions` tablaho, es ha van
      hivatkozott validation report, annak geometry-egyezese adatbazis-szinten
      legyen vedve.
- [ ] A task ne hozzon letre derivative / binding / run / export tablakat.
- [ ] Minimal docs szinkron tortenjen, ha szukseges.
- [ ] Repo gate le legyen futtatva a reporton.

### Erintett fajlok
- `canvases/web_platform/h0_e3_t3_validation_es_review_tablak.md`
- `codex/goals/canvases/web_platform/fill_canvas_h0_e3_t3_validation_es_review_tablak.yaml`
- `codex/prompts/web_platform/h0_e3_t3_validation_es_review_tablak/run.md`
- `codex/codex_checklist/web_platform/h0_e3_t3_validation_es_review_tablak.md`
- `codex/reports/web_platform/h0_e3_t3_validation_es_review_tablak.md`
- `supabase/migrations/20260312005000_h0_e3_t3_validation_es_review_tablak.sql`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`

### Elvart tabla-irany
A konkret oszlopok kod kozben finomithatok, de az irany ez legyen:

- `app.geometry_validation_reports`
  - `id uuid primary key default gen_random_uuid()`
  - `geometry_revision_id uuid not null references app.geometry_revisions(id) on delete cascade`
  - `validation_seq integer not null`
  - `status app.geometry_validation_status not null`
  - `validator_version text not null`
  - `summary_jsonb jsonb`
  - `report_jsonb jsonb not null`
  - opcionálisan `source_hash_sha256 text`
  - `created_at timestamptz not null default now()`
  - `unique (geometry_revision_id, validation_seq)`

- `app.geometry_review_actions`
  - `id uuid primary key default gen_random_uuid()`
  - `geometry_revision_id uuid not null references app.geometry_revisions(id) on delete cascade`
  - `validation_report_id uuid`
  - `action_kind` vagy dedikalt enum/checkkel vedett action mezo
    (pl. `approve`, `reject`, `request_changes`, `comment`)
  - `actor_user_id uuid references app.profiles(id) on delete set null`
  - `note text`
  - `created_at timestamptz not null default now()`
  - opcionálisan `metadata_jsonb jsonb`

### Elvart integritas es indexek
- `geometry_validation_reports`
  - `check (validation_seq > 0)`
  - `check (length(btrim(validator_version)) > 0)`
  - index legalabb:
    - `idx_geometry_validation_reports_geometry_revision_id`
    - opcionálisan `idx_geometry_validation_reports_status`
  - kompozit uniqueness / referalhatosag vedelme:
    - `unique (geometry_revision_id, id)` vagy ezzel ekvivalens megoldas,
      hogy a review action kompozit FK-val ugyanarra a geometry revisionre
      tudjon csak reportot hivatkozni

- `geometry_review_actions`
  - index legalabb:
    - `idx_geometry_review_actions_geometry_revision_id`
    - opcionálisan `idx_geometry_review_actions_actor_user_id`
    - opcionálisan `idx_geometry_review_actions_validation_report_id`
  - ha van `validation_report_id`, akkor a geometry-egyezes legyen vedett:
    - `(geometry_revision_id, validation_report_id)` -> same-geometry validation report
  - ha action tipus text/check formaban van, legyen nem-ures es ellenorzott

### Fontos modellezesi elvek
- A `geometry_revisions` marad a canonical geometry truth helye.
- A `geometry_validation_reports` audit/report reteg.
- A `geometry_review_actions` emberi review / dontesi reteg.
- Ezeket nem szabad egy tablaba osszemosni.
- A review action nem modosithatja visszamenoleg a reportot truth-kent.
- A derivative vilag kulon task.
- Az `app` schema maradjon canonical celterulet.

### DoD
- [ ] Letrejon a `supabase/migrations/20260312005000_h0_e3_t3_validation_es_review_tablak.sql`
      fajl.
- [ ] A migracio letrehozza az `app.geometry_validation_reports` tablata.
- [ ] A migracio letrehozza az `app.geometry_review_actions` tablata.
- [ ] A validation report visszavezetheto egy `app.geometry_revisions` rekordra.
- [ ] A review action geometry-szinten kapcsolodik, es ha validation reportot
      hivatkozik, annak geometry-egyezese adatbazis-szinten is vedett.
- [ ] A migracio nem hoz letre derivative / binding / run / export tablakat.
- [ ] A task nem ad hozza RLS policyt.
- [ ] A `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
      es a `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
      minimalisan szinkronba kerul a konkret migracios irannyal, ha szukseges.
- [ ] A report DoD -> Evidence Matrix konkret fajl- es line-hivatkozasokkal kitoltott.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h0_e3_t3_validation_es_review_tablak.md`
      PASS.

### Kockazat + rollback
- Kockazat:
  - a validation report tabla tul sok derivative vagy run logikat kap;
  - a review action nincs geometry-szinten eleg erosen a sajat reportjahoz kotve;
  - a review action es a geometry status frissites szemantikaja osszemosodik;
  - a docs tovabbra is `public.*` vagy ownership-szinten pontatlan iranyt sugaroz.
- Mitigacio:
  - audit es review retegek kulon tablaban maradnak;
  - kompozit FK vagy ezzel egyenerto integritas a same-geometry report-hivatkozasra;
  - derivative/run explicit out-of-scope;
  - minimal docs sync a canonical `app.*` iranyhoz.
- Rollback:
  - a migracio + checklist/report + minimal docs edit egy commitban visszavonhato.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h0_e3_t3_validation_es_review_tablak.md`
- Manualis ellenorzes:
  - pontosan a ket audit/review tabla jon letre;
  - nincs derivative/binding/run/export tabla;
  - a validation report geometry lineage megvan;
  - a review action csak sajat geometry reportot hivatkozhat;
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
- `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql`
