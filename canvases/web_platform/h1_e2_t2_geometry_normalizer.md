# H1-E2-T2 Geometry normalizer

## Funkció
A feladat a H1 geometry import pipeline második, közvetlenül a H1-E2-T1-re épülő lépése:
a minimum parse-payloadból determinisztikus, stabil canonical geometry truth képzése.

A H1-E2-T1 már létrehozza a `geometry_revisions` rekordot és betölti a `part_raw.v1`
alap payloadot. Ez még jó belépőpont, de túl közel van az importer nyers kimenetéhez.
A H1-E2-T2 célja, hogy a geometry revision `canonical_geometry_jsonb` mezője már
valódi, normalizált platform-truth legyen:

- determinisztikus pontsorrenddel,
- explicit ring-szerkezettel,
- stabil metaadatokkal,
- solver/viewer deriválásra előkészített formában,
- és ugyanabból a DXF-ből ismételten ugyanazt a canonical hash-et adja.

Ez a task azért kell most, mert a következő H1-E2-T3 validation report és H1-E2-T4
derivative generator csak akkor tud stabilan ráülni a geometry truth-ra, ha a
normalizálás már nem a nyers importer-kimenetre, hanem egy lezárt canonical szerkezetre épül.

## Fejlesztési részletek

### Scope
- Benne van:
  - a H1-E2-T1-ben létrejövő `part_raw.v1` payload normalizálása stabil canonical formára;
  - determinisztikus ring-normalizálás és hash-elhető JSON szerkezet;
  - a `geometry_revisions` rekord frissítése normalizált payloadra és friss canonical hash-re;
  - explicit normalizer service réteg bevezetése a parser fölé;
  - task-specifikus smoke script, amely bizonyítja, hogy ugyanabból a source file-ból
    ugyanaz a normalized canonical payload és hash áll elő.
- Nincs benne:
  - `geometry_validation_reports` generálás;
  - `geometry_review_actions` workflow;
  - `geometry_derivatives` generálás (`nesting_canonical`, `viewer_outline` még nem most);
  - part/sheet revision vagy binding workflow;
  - új geometry list/query endpoint;
  - új domain migráció, ha a meglévő H0 schema elegendő.

### Talált releváns fájlok
- `api/services/dxf_geometry_import.py`
  - a H1-E2-T1 parser service; most erre kell ráültetni a normalizer lépést.
- `api/routes/files.py`
  - a `source_dxf` complete flow innen indítja a background parse láncot.
- `vrs_nesting/dxf/importer.py`
  - a meglévő importer és a `PartRaw` szerkezet source-of-truthja.
- `vrs_nesting/geometry/clean.py`
  - a gyűrűk tisztításához és determinisztikus előkészítéséhez releváns meglévő geometriai helper.
- `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql`
  - a `geometry_revisions` tábla és a kötelező truth mezők source-of-truthja.
- `supabase/migrations/20260312005000_h0_e3_t3_validation_es_review_tablak.sql`
  - fontos scope-határ: validation report még nem most készül.
- `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql`
  - fontos scope-határ: derivative generálás még nem most készül.
- `scripts/smoke_h1_e2_t1_dxf_parser_integracio.py`
  - jó kiinduló minta a normalizer smoke-hoz.

### Konkrét elvárások

#### 1. A normalizer a meglévő importerre épüljön, ne mellé épüljön
A taskban nem szabad új, párhuzamos DXF parser logikát bevezetni.
A helyes irány:
- a parse továbbra is a meglévő `vrs_nesting.dxf.importer.import_part_raw` helperrel történik;
- a normalizer a `PartRaw` eredményre épül;
- a parser + normalizer együtt egy stabil H1 geometry truth-ot állít elő.

#### 2. A canonical payload legyen explicit és determinisztikus
A `canonical_geometry_jsonb` ne maradjon laza `outer_points_mm` / `holes_points_mm`
struktúra. A minimum elfogadható H1 normalized payload:
- `geometry_role`
- `format_version` vagy ezzel egyenértékű explicit normalized verzió string
- `outer_ring`
- `hole_rings`
- `bbox`
- `units`
- `normalizer_meta`
- `source_lineage`

A payloadból:
- ugyanabból a DXF-ből ismételten ugyanaz a JSON és ugyanaz a hash keletkezzen;
- a ring-ekben ne legyen zajos pontduplikáció vagy esetleges kezdőpont-választás;
- a ring orientáció és kezdőpont-választás determinisztikus legyen.

#### 3. A geometry revision rekord a normalizált truth-ot hordozza
A task végére a `geometry_revisions` rekordban:
- a `canonical_geometry_jsonb` már a normalizált payload legyen;
- a `canonical_hash_sha256` a normalizált payloadból képződjön;
- a `bbox_jsonb` a normalizált geometriával konzisztens maradjon;
- a `canonical_format_version` explicit normalizer-verziót tükrözzön
  (ne maradjon a nyers parser-szintű `part_raw.v1`, ha a payload már nem az).

#### 4. A szolgáltatási határ maradjon tiszta H1-E2-T3/H1-E2-T4 felé
Ez a task még nem validation report generator és nem derivative generator.
A task végére az legyen igaz, hogy:
- van stabil, normalizált geometry revision truth;
- erre a validation report már strukturáltan rá tud ülni;
- és a derivative generator már egy lezárt canonical geometriából tud dolgozni.

#### 5. A smoke script bizonyítsa a determinisztikusságot
Legyen task-specifikus smoke, amely legalább ezt bizonyítja:
- tipikus egyszerű DXF-ből létrejön normalizált geometry revision;
- ugyanarra a source file-ra a normalizer ismételt futása konzisztens canonical payloadot ad;
- a hash a normalizált payloadból jön;
- hibás parse esetén továbbra sem keletkezik hamis normalizált rekord.

### DoD
- [ ] A geometry import láncban külön, explicit normalizer lépés jön létre a parser fölött.
- [ ] A normalizer a meglévő `vrs_nesting.dxf.importer.import_part_raw` eredményére épül, nem új parserre.
- [ ] A `geometry_revisions.canonical_geometry_jsonb` mezője determinisztikus normalized payloadot tartalmaz.
- [ ] A normalized payload explicit outer/hole ring szerkezetet hordoz stabil metaadatokkal.
- [ ] A `canonical_hash_sha256` a normalized payloadból szerveroldalon képződik.
- [ ] A `bbox_jsonb` a normalized geometry-val konzisztensen töltődik.
- [ ] A `canonical_format_version` a normalized truth-ot tükrözi.
- [ ] Ugyanabból a source DXF-ből ismételt feldolgozásnál konzisztens canonical payload/hash keletkezik.
- [ ] Parse hiba esetén nem jön létre félrevezető normalizált geometry revision rekord.
- [ ] Készül task-specifikus smoke script a determinisztikus normalizálás bizonyítására.
- [ ] A checklist és report evidence-alapon ki van töltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h1_e2_t2_geometry_normalizer.md` PASS.

### Kockázat + rollback
- Kockázat:
  - a task idő előtt átcsúszik validation vagy derivative scope-ba;
  - a normalizálás túl erősen összekeveri a parser és a platform-truth felelősségeit;
  - nem lesz elég determinisztikus a pontsorrend / ring-orientáció / hash.
- Mitigáció:
  - explicit scope-határ a validation és derivative világ felé;
  - a normalizer külön service/helper legyen;
  - smoke explicit ismételt futással is ellenőrizze a hash/payload stabilitást.
- Rollback:
  - a route/service változtatások egy task-commitban visszavonhatók.

## Tesztállapot
- Kötelező gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h1_e2_t2_geometry_normalizer.md`
- Feladat-specifikus ellenőrzés:
  - `python3 -m py_compile api/services/dxf_geometry_import.py api/routes/files.py scripts/smoke_h1_e2_t2_geometry_normalizer.py`
  - `python3 scripts/smoke_h1_e2_t2_geometry_normalizer.py`

## Lokalizáció
Nem releváns.

## Kapcsolódások
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql`
- `supabase/migrations/20260312005000_h0_e3_t3_validation_es_review_tablak.sql`
- `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql`
- `api/services/dxf_geometry_import.py`
- `api/routes/files.py`
- `vrs_nesting/dxf/importer.py`
- `vrs_nesting/geometry/clean.py`
- `scripts/smoke_h1_e2_t1_dxf_parser_integracio.py`
