# H1-E2-T3 Validation report generator

## Funkció
A feladat a H1 geometry import pipeline harmadik, közvetlenül a H1-E2-T2-re épülő lépése:
a normalizált canonical geometry truth fölé egy valódi, query-zhető validation report réteg bevezetése.

A H1-E2-T2 végére a `geometry_revisions` rekord már determinisztikus,
`normalized_geometry.v1` canonical truth-ot hordoz. A következő lépés az,
hogy erre ne csak logolás vagy ad hoc háttérellenőrzés üljön, hanem a H0-ban
már létrehozott `app.geometry_validation_reports` tábla ténylegesen használatba
kerüljön.

A H1-E2-T3 célja, hogy:
- a sikeresen létrejött geometry revisionokhoz validation report készüljön;
- a report ne puszta blob legyen, hanem legyen benne strukturált issue-lista,
  severity összesítés és validator meta;
- a `geometry_revisions.status` mező a validation kimenetéhez igazodjon;
- és a következő H1-E2-T4 derivative generator már egy validált vagy egyértelműen
  elutasított geometry truth-ra tudjon ráülni.

Ez a task még nem emberi review workflow, és még nem derivative generátor.
Itt a cél a gépi auditálhatóság lezárása.

## Fejlesztési részletek

### Scope
- Benne van:
  - explicit geometry validation report service bevezetése a normalized geometry truth fölé;
  - `app.geometry_validation_reports` rekord létrehozása strukturált `summary_jsonb` és `report_jsonb` mezőkkel;
  - `validation_seq` és `validator_version` korrekt kitöltése;
  - a `geometry_revisions.status` frissítése legalább `validated` / `rejected` irányba;
  - a H1-E2-T2 ingest/import lánc kiegészítése úgy, hogy sikeres geometry import után a validation report is létrejöjjön;
  - task-specifikus smoke script, amely bizonyítja a valid geometry -> validated report, illetve hibás geometry -> rejected report viselkedést.
- Nincs benne:
  - `geometry_review_actions` workflow vagy emberi approval flow;
  - `geometry_derivatives` generálás;
  - part/sheet binding vagy revision approval szabályrendszer;
  - új domain migráció, ha a meglévő H0 validation/review schema elegendő;
  - új list/query API endpoint a validation reportokhoz.

### Talált releváns fájlok
- `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql`
  - a `geometry_revisions` truth mezői és státuszmezője innen jön.
- `supabase/migrations/20260312005000_h0_e3_t3_validation_es_review_tablak.sql`
  - a `geometry_validation_reports` és `geometry_review_actions` H0 base schema source-of-truthja.
- `api/services/dxf_geometry_import.py`
  - a H1-E2-T1/T2 geometry import lánc jelenlegi belépési pontja; ide kell a validation report generálást bekötni.
- `api/routes/files.py`
  - a `source_dxf` complete upload flow innen indítja a háttér importot.
- `api/services/dxf_validation.py`
  - meglévő, régi DXF-szintű háttérellenőrzés; ezt most vagy ki kell vezetni a geometry pipeline-ból,
    vagy világosan másodlagos szerepbe kell tenni.
- `scripts/smoke_h1_e2_t2_geometry_normalizer.py`
  - jó kiinduló minta a validation report smoke-hoz.
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
  - kimondja, hogy a H1 geometry pipeline minimum deliverable-je a validation report mentés is.
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - a következő task a H1-E2-T3 validation report generator.

### Konkrét elvárások

#### 1. A validation report a normalized geometry truth-ra üljön
A report ne a nyers fájlmetaadatra vagy a korábbi Phase1-féle `validation_status` mezőkre épüljön.
A helyes input:
- egy létező `app.geometry_revisions` rekord,
- annak `canonical_geometry_jsonb` payloadja,
- a hozzá tartozó `canonical_format_version`, `canonical_hash_sha256`, `source_hash_sha256`, `bbox_jsonb` és status.

#### 2. A report legyen strukturált és query-zhető
A minimum elvárt reportstruktúra:
- `summary_jsonb`:
  - `is_pass`
  - `issue_count`
  - `warning_count`
  - `error_count`
  - `validator_version`
  - `canonical_format_version`
- `report_jsonb`:
  - `issues` lista
  - `severity_summary`
  - `topology_checks`
  - `normalizer_meta` / `source_lineage` átvitt vagy leképzett meta
  - `validated_geometry_ref` vagy ezzel egyenértékű lineage információ

Nem cél most új oszlopmigráció, ha ez a meglévő JSONB struktúrával kulturáltan megoldható.

#### 3. Minimum validációs szabályok legyenek tényleg értelmesek
A generator legalább ilyen jellegű hibákat vagy figyelmeztetéseket tudjon jelenteni:
- hiányzó vagy rossz canonical payload;
- hibás `format_version`;
- hiányzó/érvénytelen outer ring;
- bbox inkonzisztencia;
- topológiai hiba (pl. önmetszés vagy érvénytelen polygon), ha ezt a repo meglévő függőségei mellett kulturáltan ellenőrizni lehet;
- hole / outer kapcsolat nyilvánvaló sérülése;
- meta vagy lineage hiányok.

A report legyen determinisztikus: ugyanabból a normalized payloadból ugyanaz az issue-rendezés és ugyanaz az összesítés jöjjön létre.

#### 4. A geometry revision státusza igazodjon a validációhoz
A task végére legalább ez legyen igaz:
- ha nincs error severity issue, a geometry revision státusza `validated` lehet;
- ha van error severity issue, a státusz `rejected` legyen;
- `approved` státuszt ez a task még nem adhat, mert az már review/approval scope.

A `geometry_validation_reports.status` is legyen konzisztens a report verdicttel.

#### 5. A validation report lánc automatikusan fusson le geometry import után
A H1 upload -> import flow itt már ne álljon meg a geometry revision insertnél.
A helyes minimum lánc:
- file feltöltés és metadata truth,
- geometry import + normalizer,
- geometry revision insert,
- validation report insert,
- geometry revision státuszfrissítés.

Ez még mindig nem derivative generator és nem review workflow.

#### 6. A smoke script bizonyítsa a fő ágakat
Legyen task-specifikus smoke, amely legalább ezt bizonyítja:
- tipikus egyszerű DXF-ből létrejön geometry revision és validation report;
- a validation report summary/query-szerkezete helyes;
- a geometry revision státusza valid geometry esetén `validated`;
- direkt hibás vagy szándékosan sérült canonical payload esetén `rejected` report jön létre;
- parse/import failure esetén továbbra sem jön létre hamis parsed geometry revision.

### DoD
- [ ] Készül explicit geometry validation report service a normalized geometry truth fölé.
- [ ] A validation a meglévő `app.geometry_validation_reports` táblát használja, nem Phase1-féle legacy mezőket.
- [ ] A report strukturált `summary_jsonb` és `report_jsonb` tartalmat ír issue-listával és severity összesítéssel.
- [ ] A `validation_seq` és `validator_version` korrekt módon töltődik.
- [ ] A `geometry_revisions.status` a validation verdicthez igazodik (`validated` / `rejected`, de nem `approved`).
- [ ] A geometry import lánc sikeres futás után automatikusan létrehozza a validation reportot.
- [ ] Valid geometry esetén query-zhető PASS-szerű report jön létre.
- [ ] Hibás canonical geometry esetén query-zhető rejected report jön létre.
- [ ] Parse/import failure esetén továbbra sem jön létre félrevezető parsed geometry revision.
- [ ] Készül task-specifikus smoke script a validation report flow bizonyítására.
- [ ] A checklist és report evidence-alapon ki van töltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h1_e2_t3_validation_report_generator.md` PASS.

### Kockázat + rollback
- Kockázat:
  - a task idő előtt review workflow-vá vagy derivative gate-té nő;
  - a validáció túl erősen összekeveri a DXF fájl-szintű és a geometry-truth szintű felelősséget;
  - a report JSON struktúrája rendezetlen vagy nem determinisztikus lesz;
  - a státuszfrissítés túl agresszív lesz, és később akadályozza a review/approval lépést.
- Mitigáció:
  - explicit scope-határ a review és derivative taskok felé;
  - a validator közvetlenül a normalized geometry revisiont validálja;
  - determinisztikus issue-rendezés és severity összesítés;
  - csak `validated` / `rejected` státuszfrissítés, `approved` nélkül.
- Rollback:
  - a service/route változtatások egy task-commitban visszavonhatók;
  - ha szükséges, a background validation bekötés ideiglenesen kikapcsolható anélkül, hogy a H1-E2-T2 normalizer truth sérülne.

## Tesztállapot
- Kötelező gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h1_e2_t3_validation_report_generator.md`
- Feladat-specifikus ellenőrzés:
  - `python3 -m py_compile api/services/geometry_validation_report.py api/services/dxf_geometry_import.py api/routes/files.py scripts/smoke_h1_e2_t3_validation_report_generator.py`
  - `python3 scripts/smoke_h1_e2_t3_validation_report_generator.py`

## Lokalizáció
Nem releváns.

## Kapcsolódások
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql`
- `supabase/migrations/20260312005000_h0_e3_t3_validation_es_review_tablak.sql`
- `api/services/dxf_geometry_import.py`
- `api/services/dxf_validation.py`
- `api/routes/files.py`
- `scripts/smoke_h1_e2_t2_geometry_normalizer.py`
