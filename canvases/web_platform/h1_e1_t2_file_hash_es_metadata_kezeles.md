# H1-E1-T2 File hash és metadata kezelés

## Funkció
A feladat a H1 ingest csatorna második, közvetlenül a H1-E1-T1-re épülő keményítési lépése:
a `file_objects` metadata-truth szerveroldali lezárása.

A cél az, hogy a feltöltés befejezésekor a rendszer ne a kliens által visszaküldött
`storage_bucket` / `byte_size` / `mime_type` / `sha256` mezőkre támaszkodjon,
hanem a ténylegesen feltöltött objektumból számolja és rögzítse a kanonikus ingest metadata-t.

Ez a task azért kell közvetlenül a H1-E1-T1 után, mert a mostani upload flow már H0-kompatibilis,
de a metadata truth még nincs teljesen szerverre húzva. A H1-E2 geometry import pipeline előtt ezt le kell zárni,
hogy a parse/validation réteg már megbízható source file metaadatra épüljön.

## Fejlesztési részletek

### Scope
- Benne van:
  - a `complete_upload` flow metadata-hardeningje;
  - szerveroldali `byte_size`, `sha256`, `mime_type`, `file_name` truth előállítása a tényleges storage objektumból;
  - a source bucket kanonikus rögzítése a H0 `source-files` / `settings.storage_bucket` truth-ra;
  - minimális duplicate-detection alap biztosítása szerveroldali hash mentéssel;
  - task-specifikus smoke script, amely bizonyítja, hogy a kliensoldali metadata-override nem írja felül a szerver truth-ot.
- Nincs benne:
  - új domain migráció;
  - geometry parse / geometry revision workflow;
  - automatikus duplicate merge vagy dedikált duplicate linking modell;
  - multi-bucket refaktor vagy artifact bucket kezelés;
  - run/snapshot/worker réteg módosítása.

### Talált releváns fájlok
- `api/routes/files.py`
  - a jelenlegi H1-E1-T1 upload-url + complete/list/delete flow helye.
- `api/services/dxf_validation.py`
  - a DXF háttér-validáció innen indul, ezért fontos, hogy már megbízható file metadata-t kapjon.
- `api/supabase_client.py`
  - létezik signed download és object letöltési helper, erre érdemes építeni a metadata számítást.
- `api/config.py`
  - itt van a kanonikus source bucket default (`API_STORAGE_BUCKET`, default: `source-files`).
- `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql`
  - a meglévő H0 `app.file_objects` truth: `storage_bucket`, `storage_path`, `file_name`, `mime_type`, `byte_size`, `sha256`.
- `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md`
  - a H0 source-files bucket és path policy source-of-truth.
- `scripts/smoke_h1_e1_t1_upload_endpoint_service_h0_schema_realignment.py`
  - jó minta a következő, metadata-fókuszú smoke scripthez.

### Konkrét elvárások

#### 1. A source file metadata truth legyen szerveroldali
A `complete_upload` során a következő mezők ne a kliens payloadból kerüljenek végleges truth-ként a DB-be:
- `storage_bucket`
- `byte_size`
- `mime_type`
- `sha256`
- `file_name`

A helyes működés:
- `storage_bucket` a kanonikus source bucketből jön (`settings.storage_bucket`, H0 szerint alapból `source-files`);
- `file_name` a kanonikus `storage_path` basename-jéből jön;
- a feltöltött objektum letöltésre kerül szerveroldalon;
- ebből számolódik a `byte_size` és a `sha256`;
- a `mime_type` legalább determinisztikus szerveroldali szabállyal képződik (pl. extension + fallback), nem a kliens input a truth.

#### 2. A storage bucket override záródjon le
A jelenlegi flow-ban a kliens még tud `storage_bucket` értéket küldeni a complete requestben.
Ez legfeljebb backward-compat request mező maradhat, de nem lehet DB-truth.

A helyes viselkedés:
- a source upload DB-be írt bucketje mindig a kanonikus source bucket legyen;
- ha kell, a route explicit ignorálja a kliens bucket override-ot;
- a validációs helper is ugyanebből a kanonikus bucket truth-ból induljon.

#### 3. Az objektum létezése legyen ellenőrzött
A `complete_upload` ne csak path-prefix alapján fogadja el a feltöltést,
hanem ellenőrizze, hogy a megadott kanonikus source object valóban elérhető/letölthető.

Minimum elvárás:
- ha a signed download vagy a tényleges letöltés nem sikerül,
  a complete upload ne írjon be sikeres `app.file_objects` rekordot.

#### 4. Duplicate-detection alap legyen adott
Ebben a taskban nem kell teljes duplicate policy.
De a task végére legyen biztos, hogy a `sha256` már szerveroldali, megbízható ingest truth,
így a későbbi duplikátumvizsgálat valódi alapra épül.

#### 5. H1-E2 felé stabil határ
A geometry import pipeline a következő fázisban jön.
Ebben a taskban nem kell `geometry_revisions` rekordot írni, státuszgépet kezelni vagy derivative-et generálni.
A feladat itt az, hogy a H1-E2 már megbízható source file metaadatot kapjon.

### DoD
- [ ] A `complete_upload` a DB-be írt `storage_bucket` értéket nem a kliens requestből veszi, hanem a kanonikus source bucketből.
- [ ] A `complete_upload` a DB-be írt `file_name` értéket a kanonikus `storage_path` basename-jéből képzi.
- [ ] A `complete_upload` szerveroldalon számolja a `byte_size` értéket a tényleges storage objektumból.
- [ ] A `complete_upload` szerveroldalon számolja a `sha256` értéket a tényleges storage objektumból.
- [ ] A `complete_upload` szerveroldalon állítja elő a `mime_type` truth-ot determinisztikus szabállyal.
- [ ] Sikertelen object letöltés esetén nem jön létre félrevezető `app.file_objects` rekord.
- [ ] A route legfeljebb backward-compat request parsing miatt fogad legacy metadata mezőket, de azok nem írják felül a szerver truth-ot.
- [ ] Készül task-specifikus smoke script, amely bizonyítja, hogy a hamis kliensoldali metadata ellenére a szerveroldali truth kerül a DB-be.
- [ ] A checklist és report evidence-alapon ki van töltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h1_e1_t2_file_hash_es_metadata_kezeles.md` PASS.

### Kockázat + rollback
- Kockázat:
  - a metadata számítás túl szorosan kötődik a storage letöltéshez, és emiatt a complete flow érzékenyebb lesz;
  - a jelenlegi backward-compat request mezők kezelése félúton marad;
  - a DXF validációs helper eltérő metadata truth-tal indul a route-hoz képest.
- Mitigáció:
  - külön, kis helperben érdemes kezelni a metadata számítást;
  - a kanonikus source bucket/path logika maradjon egyértelmű;
  - smoke script explicit ellenőrizze a bucket/file_name/hash/byte_size truth-ot.
- Rollback:
  - route/service változtatások egy task-commitban visszavonhatók.

## Tesztállapot
- Kötelező gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h1_e1_t2_file_hash_es_metadata_kezeles.md`
- Feladat-specifikus ellenőrzés:
  - `python3 scripts/smoke_h1_e1_t2_file_hash_es_metadata_kezeles.py`

## Lokalizáció
Nem releváns.

## Kapcsolódások
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md`
- `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql`
- `api/routes/files.py`
- `api/services/dxf_validation.py`
- `api/supabase_client.py`
- `api/config.py`
- `scripts/smoke_h1_e1_t1_upload_endpoint_service_h0_schema_realignment.py`
