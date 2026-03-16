# H1-E2-T4 Geometry derivative generator (H1 minimum)

## Funkcio
A feladat a H1 geometry import pipeline negyedik, a H1-E2-T2 es H1-E2-T3
utan kovetkezo lepese: a validalt canonical geometry truth-bol tenyleges,
query-zheto es determinisztikus derivative rekordok eloallitasa a meglévo
`app.geometry_derivatives` tablaba.

A H0-E3-T4 mar letette a derivative tabla helyet, a H1-E2-T2 normalizalta a
canonical geometry truth-ot, a H1-E2-T3 pedig bevezette a validation report
reteget. A kovetkezo minimum az, hogy a platformban ne csak `geometry_revisions`
letezzen, hanem a H1 minimumhoz tenylegesen keletkezzen legalabb ket, celra
szabott derivative:

- `nesting_canonical`
- `viewer_outline`

Ez a task meg mindig nem manufacturing ag, nem part/sheet workflow es nem run
snapshot epites. A cel az, hogy a kovetkezo H1-E3 part/sheet workflow mar
ne kozvetlenul a nyers geometry revision payloadra, hanem explicit derivative
truth-ra tudjon epiteni.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - explicit geometry derivative generator service bevezetese a validalt
    `app.geometry_revisions` truth fole;
  - legalabb `nesting_canonical` es `viewer_outline` derivative eloallitasa;
  - a meglévo `app.geometry_derivatives` tabla tenyleges hasznalatba vetele;
  - determinisztikus `derivative_jsonb`, `format_version`, `producer_version`,
    `derivative_hash_sha256` es `source_geometry_hash_sha256` kitoltese;
  - olyan idempotens vagy kontrollalt ujrageneralasi logika, amely nem torik el
    a `(geometry_revision_id, derivative_kind)` uniqueness mellett;
  - a H1 geometry import/validation lanc kiegeszitese ugy, hogy valid geometry
    eseten automatikusan kepzodjenek a minimum derivative-ek;
  - task-specifikus smoke script a valid, ujrageneralasi es rejected ag
    bizonyitasara.
- Nincs benne:
  - `manufacturing_canonical` generator;
  - part/sheet binding vagy `part_revisions` frissites;
  - review workflow / emberi approval;
  - uj domain migracio, ha a meglévo H0 `app.geometry_derivatives` schema
    elegendo;
  - uj list/query API endpoint csak a derivative-ek szemleltesere;
  - run snapshot vagy solver adapter input build.

### Talalt relevans fajlok
- `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql`
  - a `geometry_derivatives` tabla es a uniqueness/integritas H0 source-of-truthja.
- `api/services/dxf_geometry_import.py`
  - a H1 geometry import pipeline aktualis gerince; ide kell a derivative
    generator lancot bekotni a validation utan.
- `api/services/geometry_validation_report.py`
  - a H1-E2-T3 ota a validated/rejected verdict innen jon; a derivative-ek csak
    erre epithetnek.
- `scripts/smoke_h1_e2_t3_validation_report_generator.py`
  - jo kiindulopont a derivative smoke-hoz.
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
  - kimondja, hogy H1 minimumben a `geometry_derivatives` tabla mar aktiv reteg,
    legalabb `nesting_canonical` es `viewer_outline` derivative-ekkel.
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - a kovetkezo task a H1-E2-T4 geometry derivative generator.

### Konkret elvarasok

#### 1. A derivative generator csak validalt geometry truth-ra uljon
A service ne a nyers DXF-re es ne a file objectre, hanem a mar letrehozott,
normalizalt `geometry_revisions` rekordra epuljon.
A minimum gate:
- `geometry_revision.status == 'validated'` eseten johet derivative generalas;
- `rejected` geometrybol nem johet letre minimum derivative;
- `approved` statuszt ez a task meg nem oszt ki.

#### 2. Keszuljon ket kulon, cel-specifikus derivative
Minimum ket derivative legyen:
- `nesting_canonical`
  - solver-barát, stabil, determinisztikus polygon payload;
- `viewer_outline`
  - viewer-barát outline payload, amely tovabbra sem export artifact.

A ket derivative ne legyen ugyanaz a rekord mas `derivative_kind` cimkevel.
Legyen vilagosan dokumentalva, mi a ket payload szerepe es kulonbsege.

#### 3. A derivative payload es hash legyen determinisztikus
A minimum elvart mezok:
- `producer_version`
- `format_version`
- `derivative_jsonb`
- `derivative_hash_sha256`
- `source_geometry_hash_sha256`

Ugyanabból a canonical geometry payloadbol ugyanaz a derivative payload es ugyanaz
 a hash jojjon ki. A generator ne epitjen bele nem-determinisztikus idot vagy
 random azonositot a payloadba.

#### 4. Az ujrageneralas legyen kontrollalt
A H0 uniqueness miatt egy geometry revision + derivative kind parhoz egy rekord
letezhet.
A task vegere legyen kulturalt ujrafuttatasi viselkedes:
- vagy update-eli a meglévo rekordot ugyanazzal a kulccsal;
- vagy egyertelmuen ugyanarra a rekordra vezet vissza;
- de ne torjon egyedi megszoritasba egy sima retry/ujrageneralas miatt.

#### 5. A derivative lanc automatikusan fusson a validation utan
A H1 minimum ingest lanc a task vegere legalabb ez legyen:
- file ingest truth,
- geometry parse + normalizer,
- geometry revision insert,
- validation report insert,
- geometry status `validated` / `rejected`,
- validalt geometry eseten derivative generalas.

#### 6. A smoke script bizonyitsa a fo agakat
Legyen task-specifikus smoke, amely legalabb ezt bizonyitja:
- tipikus egyszeru DXF-bol letrejon geometry revision, validation report es
  ket derivative;
- a `nesting_canonical` es `viewer_outline` payload strukturaja helyes;
- a derivative hash-ek determinisztikusak;
- ujrageneralas nem hoz letre duplikalt rekordot ugyanarra a kindra;
- rejected geometry eseten nem jon letre derivative;
- parse/import failure eseten tovabbra sem jon letre hamis geometry revision
  vagy derivative.

### DoD
- [ ] Keszul explicit geometry derivative generator service a validalt geometry truth fole.
- [ ] A task a meglévo `app.geometry_derivatives` tablat hasznalja, nem uj legacy tablakat.
- [ ] Letrejon legalabb a `nesting_canonical` es a `viewer_outline` derivative.
- [ ] A derivative rekordok `producer_version`, `format_version`, `derivative_jsonb`, `derivative_hash_sha256` es `source_geometry_hash_sha256` mezoi korrektul toltodnek.
- [ ] A derivative payloadok determinisztikusak.
- [ ] Ujrafuttatas eseten a `(geometry_revision_id, derivative_kind)` uniqueness nem torik el.
- [ ] A geometry import/validation lanc valid geometry eseten automatikusan general derivative-eket.
- [ ] Rejected geometry eseten nem jon letre derivative rekord.
- [ ] Parse/import failure eseten tovabbra sem jon letre hamis geometry revision vagy derivative.
- [ ] Keszul task-specifikus smoke script a derivative flow bizonyitasara.
- [ ] A checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h1_e2_t4_geometry_derivative_generator_h1_minimum.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a ket derivative payload valojaban ugyanaz marad, csak mas kind cimkevel;
  - a generator osszemossa a geometry truth-ot a derivative reteggel;
  - a uniqueness miatt a retry-k tornek;
  - a task idovel elott manufacturing vagy part-binding scope-ba csuszik.
- Mitigacio:
  - explicit payload-szerepek a ket derivative-re;
  - a service mindig a canonical geometry revisionre epul;
  - kontrollalt update/ujrageneralasi logika ugyanarra a kindra;
  - manufacturing / part workflow / run snapshot explicit out-of-scope.
- Rollback:
  - a service/pipeline/smoke valtozasok egy task-commitban visszavonhatok;
  - ha szukseges, a derivative generator ideiglenesen kikapcsolhato ugy, hogy a
    parse+normalize+validation truth ne seruljon.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h1_e2_t4_geometry_derivative_generator_h1_minimum.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/services/geometry_derivative_generator.py api/services/dxf_geometry_import.py scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py`
  - `python3 scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql`
- `supabase/migrations/20260312005000_h0_e3_t3_validation_es_review_tablak.sql`
- `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql`
- `api/services/dxf_geometry_import.py`
- `api/services/geometry_validation_report.py`
- `scripts/smoke_h1_e2_t3_validation_report_generator.py`
