# H1-E2-T1 DXF parser integráció

## Funkció
A feladat a H1 geometry import pipeline első valódi belépési pontja:
a feltöltött `source_dxf` forrásfájlokból minimum működő, query-zhető `app.geometry_revisions` rekord jöjjön létre.

Ez a task közvetlenül a H1-E1 ingest láncra épül.
A cél most még nem a teljes validation/derivative/part workflow leszállítása,
hanem annak lezárása, hogy a már kanonikus storage-truth alapján feltöltött DXF-ből a backend
valóban parseren átmenő geometry revisiont tudjon képezni.

A tasknak arra kell ráülnie, ami a repóban már létezik:
- H0 `app.geometry_revisions` séma,
- a H1-E1 upload + server-side metadata truth,
- a meglévő `vrs_nesting.dxf.importer.import_part_raw` DXF/JSON importer,
- és a H0 storage/source lineage modell.

## Fejlesztési részletek

### Scope
- Benne van:
  - minimum H1 parser service bevezetése a feltöltött `source_dxf` fájlokhoz;
  - a source storage object szerveroldali letöltése és ideiglenes lokális parse-ja;
  - `app.geometry_revisions` rekord létrehozása a sikeresen parse-olt part-geometriához;
  - determinisztikus `canonical_geometry_jsonb`, `canonical_hash_sha256`, `bbox_jsonb`, `source_hash_sha256` kitöltése;
  - `revision_no` képzése source file-onként;
  - minimum státuszhasználat: sikeres parse után `status='parsed'`;
  - task-specifikus smoke script, amely bizonyítja a source file -> geometry revision láncot.
- Nincs benne:
  - `geometry_validation_reports` létrehozása vagy kitöltése;
  - `geometry_review_actions` workflow;
  - `geometry_derivatives` generálás;
  - part/sheet revision létrehozás;
  - új route a geometry revisionök lekérdezésére, ha a szolgáltatási lánc smoke-kal bizonyítható;
  - új domain migráció, ha a H0 `app.geometry_revisions` oszlopai elegendőek;
  - sheet-role DXF ingest vagy irregular sheet parser.

### Talált releváns fájlok
- `api/routes/files.py`
  - a jelenlegi H1 ingest végpont; innen indul a `source_dxf` utófeldolgozás.
- `api/services/file_ingest_metadata.py`
  - már létező szerveroldali source object letöltési/helper réteg.
- `api/services/dxf_validation.py`
  - jelenleg csak basic readability/log réteg; ezt nem szabad összekeverni a geometry revision truth-tal.
- `api/supabase_client.py`
  - a szükséges select/insert/update képességek már megvannak a geometry revision mentéshez.
- `vrs_nesting/dxf/importer.py`
  - meglévő, valós DXF importer; erre kell építeni, nem új parservilágot feltalálni.
- `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql`
  - a H0 geometry revision truth és a kötelező mezők source-of-truthja.
- `supabase/migrations/20260312005000_h0_e3_t3_validation_es_review_tablak.sql`
  - fontos scope-határ: validációs report még nem most készül.
- `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql`
  - fontos scope-határ: derivative generálás még nem most készül.
- `scripts/smoke_h1_e1_t2_file_hash_es_metadata_kezeles.py`
  - jó minta a fake storage + TestClient-alapú H1 smoke bizonyításra.

### Konkrét elvárások

#### 1. A parser a meglévő importerre épüljön
A taskban nem szabad új DXF parser logikát kitalálni párhuzamosan.
A helyes irány:
- a feltöltött source object ideiglenes fájlba kerül;
- a parse a meglévő `vrs_nesting.dxf.importer.import_part_raw` helperen keresztül történik;
- a task minimum H1-ben csak a part-szerű `source_dxf` importot zárja le.

#### 2. A source file -> geometry revision lineage legyen explicit
Sikeres parse esetén jöjjön létre `app.geometry_revisions` rekord, amely legalább ezeket tölti:
- `project_id`
- `source_file_object_id`
- `geometry_role='part'`
- `revision_no` (source file-onként növekvő)
- `status='parsed'`
- `canonical_format_version` (explicit, stabil string; pl. `part_raw.v1`)
- `canonical_geometry_jsonb`
- `canonical_hash_sha256`
- `source_hash_sha256` a `file_objects.sha256` értékéből
- `bbox_jsonb`
- `created_by`

#### 3. A canonical payload legyen determinisztikus minimum-formátum
Ebben a taskban még nem kell a teljes H1-E2-T2 normalizer mélysége,
de a `canonical_geometry_jsonb` már ne legyen esetleges vagy nyers DXF dump.
A minimum elfogadható payload:
- az importer `PartRaw` eredményére épül;
- determinisztikusan sorba rendezhető / hash-elhető;
- tartalmazza az outer ringet, a hole-okat és a parse lineage minimum metaadatait;
- ugyanabból a blobból ugyanazt a canonical hash-et adja.

#### 4. Parse hiba ne hozzon létre hamis parsed rekordot
Ha a source object nem tölthető le vagy a parse elbukik,
akkor nem jöhet létre félrevezető `status='parsed'` geometry revision rekord.
Ebben a taskban elfogadható minimum viselkedés:
- logolás;
- sikertelen parse esetén nincs új geometry revision sor.

#### 5. H1-E2-T2 felé tiszta határ maradjon
Ez a task még nem validation report generátor és nem derivative generator.
A task végére az legyen igaz, hogy:
- van működő source file -> parsed geometry revision lánc,
- és erre a H1-E2-T2/H1-E2-T3/H1-E2-T4 már tisztán rá tud ülni.

### DoD
- [ ] A feltöltött `source_dxf` utófeldolgozása a meglévő `vrs_nesting.dxf.importer.import_part_raw` logikára épül.
- [ ] Sikeres parse esetén létrejön `app.geometry_revisions` rekord a source file-hoz kötve.
- [ ] A rekord `geometry_role='part'` és `status='parsed'` értékkel jön létre.
- [ ] A rekord `revision_no` értéke source file-onként konzisztensen képződik.
- [ ] A rekord `canonical_geometry_jsonb` mezője nem üres, hanem determinisztikus minimum geometry payload.
- [ ] A rekord `canonical_hash_sha256` mezője a canonical payloadból szerveroldalon képződik.
- [ ] A rekord `source_hash_sha256` mezője a `file_objects.sha256` truth-ra ül.
- [ ] A rekord `bbox_jsonb` mezője a parse-olt geometriából képződik.
- [ ] Sikertelen object letöltés vagy parse hiba esetén nem jön létre hamis `parsed` geometry revision rekord.
- [ ] Készül task-specifikus smoke script, amely bizonyítja a source file -> parsed geometry revision láncot.
- [ ] A checklist és report evidence-alapon ki van töltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h1_e2_t1_dxf_parser_integracio.md` PASS.

### Kockázat + rollback
- Kockázat:
  - a task idő előtt átcsúszik a normalizer/validation/derivative scope-ba;
  - a parser új, párhuzamos logikát kezd használni a meglévő importer helyett;
  - a background parse lánc csendben hibázik, és nehezen ellenőrizhető marad.
- Mitigáció:
  - explicit scope-határ a validation/derivative világ felé;
  - kötelezően a meglévő `vrs_nesting.dxf.importer` használata;
  - smoke script sikeres és hibás parse scenarióval.
- Rollback:
  - a route/service változtatások egy task-commitban visszavonhatók.

## Tesztállapot
- Kötelező gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h1_e2_t1_dxf_parser_integracio.md`
- Feladat-specifikus ellenőrzés:
  - `python3 scripts/smoke_h1_e2_t1_dxf_parser_integracio.py`

## Lokalizáció
Nem releváns.

## Kapcsolódások
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md`
- `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql`
- `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql`
- `supabase/migrations/20260312005000_h0_e3_t3_validation_es_review_tablak.sql`
- `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql`
- `api/routes/files.py`
- `api/services/file_ingest_metadata.py`
- `api/services/dxf_validation.py`
- `api/supabase_client.py`
- `vrs_nesting/dxf/importer.py`
- `scripts/smoke_h1_e1_t2_file_hash_es_metadata_kezeles.py`
