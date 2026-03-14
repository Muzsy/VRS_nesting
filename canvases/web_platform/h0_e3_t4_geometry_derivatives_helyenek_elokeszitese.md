# canvases/web_platform/h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.md

# H0-E3-T4 geometry derivatives helyenek elokeszitese

## Funkcio
A feladat a web platform geometry gerincenek kovetkezo schema-lepese:
az `app.geometry_derivatives` tabla letetele, amely formalizalt helyet ad a
canonical geometry revisionokbol eloallitott kulonbozo belso derivalt
reprezentacioknak.

Ez a task kozvetlenul a H0-E3-T2/T3 utan kovetkezik.
A cel, hogy a rendszerben kulon, explicit helye legyen legalabb ezeknek a
belso derivaltaknak:

- `nesting_canonical`
- `manufacturing_canonical`
- `viewer_outline`

A geometry revision marad a canonical geometry truth, a derivative tabla pedig
a cel-specifikus, ujraeloallithato, hash-elheto, snapshotba hivatkozhato
szarmaztatott reteg.

Ez tovabbra is kontrollalt H0 scope:
- part/sheet binding kulon task,
- run snapshot/orchestration kulon task,
- export/manufacturing artifact kulon task,
- RLS es API meg nincs scope-ban.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - uj Supabase migracio letrehozasa az `app.geometry_derivatives` tablaval;
  - a `geometry_derivative_kind` enum gyakorlati hasznalata;
  - kapcsolat az `app.geometry_revisions` tablaval;
  - minimalis derivative metadata + payload + hash hely letetele;
  - olyan integritas, hogy ugyanahhoz a geometry revisionhoz es derivative kindhoz
    kontrollaltan lehessen derivalt rekordot tarolni;
  - PK/FK kapcsolatok, alap indexek es derivative-integritas letetele;
  - minimal docs szinkron, ha a fo architecture/H0 doksikban a derivative blokk
    meg stale, `public.*` schemaju vagy ownership szempontbol pontatlan.
- Nincs benne:
  - part/sheet binding tabla;
  - run request / snapshot / attempt tabla;
  - export/manufacturing artifact tabla;
  - derivative file object vagy storage artifact tabla;
  - RLS policy;
  - API endpoint implementacio.

### Fo kerdesek, amiket le kell zarni
- [ ] Mi legyen a derivative tabla minimalis, de mar hasznalhato oszlopkeszlete?
- [ ] Egy geometry revision + derivative kind parhoz egyetlen aktiv rekord legyen,
      vagy mar most tobb generaciozhato derivaltat engedjunk?
- [ ] Mi legyen explicit oszlop, es mi maradjon JSON payload vilag?
- [ ] Hogyan rogzitjuk a producer/format verziot es a derivative hash-t?
- [ ] Hogyan kulonuljon el a derivative tabla a geometry revision truth-tol es az
      export artifact vilagtol?

### Feladatlista
- [ ] Kesz legyen a task teljes artefaktlanca.
- [ ] Letrejojjon a kovetkezo H0 migracio az `app.geometry_derivatives` tablaval.
- [ ] A migracio kapcsolja a derivative rekordot egy source `app.geometry_revisions`
      rekordhoz.
- [ ] A migracio hasznalja az `app.geometry_derivative_kind` enumot.
- [ ] A migracio biztositson payload/helyet a derivative reprezentacionak.
- [ ] A migracio tarolja a derivative format/producer verziojat es hash-et.
- [ ] A task ne hozzon letre binding / run / export tablakat.
- [ ] Minimal docs szinkron tortenjen, ha szukseges.
- [ ] Repo gate le legyen futtatva a reporton.

### Erintett fajlok
- `canvases/web_platform/h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.md`
- `codex/goals/canvases/web_platform/fill_canvas_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.yaml`
- `codex/prompts/web_platform/h0_e3_t4_geometry_derivatives_helyenek_elokeszitese/run.md`
- `codex/codex_checklist/web_platform/h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.md`
- `codex/reports/web_platform/h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.md`
- `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`

### Elvart tabla-irany
A konkret oszlopok kod kozben finomithatok, de az irany ez legyen:

- `app.geometry_derivatives`
  - `id uuid primary key default gen_random_uuid()`
  - `geometry_revision_id uuid not null references app.geometry_revisions(id) on delete cascade`
  - `derivative_kind app.geometry_derivative_kind not null`
  - `producer_version text not null`
  - `format_version text not null`
  - `derivative_jsonb jsonb not null`
  - `derivative_hash_sha256 text`
  - opcionálisan `source_geometry_hash_sha256 text`
  - `created_at timestamptz not null default now()`

### Elvart integritas es indexek
A task szandekosan „helyet keszit elo”, ezert itt az egyszerubb, kontrollalt modell a jo:

- `unique (geometry_revision_id, derivative_kind)`
  - ugyanahhoz a geometry revisionhoz ugyanabbol a derivative kindbol
    H0-ban egy aktiv rekord eleg
- check-ek:
  - `length(btrim(producer_version)) > 0`
  - `length(btrim(format_version)) > 0`
- index legalabb:
  - `idx_geometry_derivatives_geometry_revision_id` on `(geometry_revision_id)`
  - opcionálisan `idx_geometry_derivatives_kind` on `(derivative_kind)`

### Fontos modellezesi elvek
- A `geometry_revisions` marad a canonical geometry truth helye.
- A `geometry_derivatives` a cel-specifikus, ujraeloallithato derivalt reteg.
- Ez nem binding tabla.
- Ez nem run snapshot tabla.
- Ez nem export artifact tabla.
- A derivative payload lehet JSON-alapu, de ez nem valtja ki a geometry revisiont.
- A kesobbi run snapshot mar derivative-hivatkozasokra fog tamaszkodni.
- Az `app` schema marad a canonical celterulet.

### DoD
- [ ] Letrejon a `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql`
      fajl.
- [ ] A migracio letrehozza az `app.geometry_derivatives` tablata.
- [ ] A derivative rekord visszavezetheto egy source `app.geometry_revisions` rekordra.
- [ ] A tabla hasznalja az `app.geometry_derivative_kind` enumot.
- [ ] A tabla rendelkezik payload hellyel es derivative hash / version mezokkel.
- [ ] A migracio nem hoz letre binding / run / export tablakat.
- [ ] A task nem ad hozza RLS policyt.
- [ ] A `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
      es a `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
      minimalisan szinkronba kerul a konkret migracios irannyal, ha szukseges.
- [ ] A report DoD -> Evidence Matrix konkret fajl- es line-hivatkozasokkal kitoltott.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.md`
      PASS.

### Kockazat + rollback
- Kockazat:
  - a derivative tabla tul sok run vagy export logikat kap;
  - a tabla tul sovany lesz es nem ad eleg fogodzkodot a snapshot vilagnak;
  - a derivative ownership osszemosodik a geometry revision truth-tal;
  - a docs tovabbra is `public.*` vagy ownership-szinten pontatlan iranyt sugaroz.
- Mitigacio:
  - a tabla maradjon source geometryhez kotott derivalt reteg;
  - binding/run/export explicit out-of-scope;
  - egyertelmu uniqueness H0-ban `(geometry_revision_id, derivative_kind)`;
  - minimal docs sync a canonical `app.*` iranyhoz.
- Rollback:
  - a migracio + checklist/report + minimal docs edit egy commitban visszavonhato.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.md`
- Manualis ellenorzes:
  - pontosan csak az `app.geometry_derivatives` tabla jon letre;
  - nincs binding/run/export tabla;
  - a geometry lineage megvan;
  - a derivative kind enum hasznalatban van;
  - van payload + version + hash hely;
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
- `supabase/migrations/20260312005000_h0_e3_t3_validation_es_review_tablak.sql`
