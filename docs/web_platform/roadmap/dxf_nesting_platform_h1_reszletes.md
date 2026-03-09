# DXF Nesting Platform — H1 részletes terv

## Cél

A **H1** a H0-ra épülő első valóban funkcionális platformszint.  
Míg a H0 célja a szerkezeti gerinc és a stabil adattér létrehozása volt, a H1 célja az, hogy a rendszerben **valós, végigvezetett DXF → geometry → part/sheet → snapshot → run → eredmény** folyamat jöjjön létre.

A H1 még nem a végleges ipari optimalizációs minőség szintje.  
A H1 feladata az, hogy a platform:

- valódi DXF-eket fogadjon,
- azokat ellenőrizhetően és auditálhatóan feldolgozza,
- part- és sheet-oldalról használható entitásokká alakítsa,
- nesting runokat tudjon előállítani,
- worker útvonalon futtatni tudjon,
- és a kapott eredményeket strukturált, lekérdezhető, vizualizálható formában visszaadja.

A H1 tehát az a szakasz, ahol a rendszer **már nem csak jól megtervezett**, hanem **végig működő platformcsatornává** válik.

---

## H1 fő célképe

A H1 végére a rendszernek az alábbiakat kell tudnia:

1. **DXF import és geometry revision pipeline működjön**
   - feltöltés
   - parse
   - audit
   - canonical geometry előállítás
   - derivative képzés

2. **Part és sheet alapobjektumok használhatók legyenek projektben**
   - revisionök
   - part requirementek
   - sheet inputok
   - priority mezők

3. **Run lifecycle működjön**
   - run létrehozás
   - snapshot készítés
   - queue
   - worker lease
   - solver hívás
   - eredmény visszaírás

4. **Viewer- és riport-alap eredményréteg működjön**
   - sheet projection
   - placement projection
   - unplaced lista
   - metrikák
   - SVG/DXF/report artifactok

5. **A geometry és a run lánc auditálható legyen**
   - hash-ek
   - logok
   - validációs riportok
   - engine/output metaadatok

6. **A platform készen álljon a H2-re**
   - manufacturing bővítés
   - cut rule modellek
   - fejlettebb solver workflowk
   - postprocessor ág

---

## H1 szerepe a roadmapban

A H1 nem még egy “alapozás”, hanem a platform első teljes, ténylegesen működő **operációs szintje**.

### H0 után mi hiányzik még?
A H0-ban megvan:
- a domainstruktúra,
- a táblák helye,
- a snapshot-first modell,
- az artifact/projection szétválasztás,
- a jövőbeni manufacturing és postprocess helye.

De önmagában ez még csak váz.

### H1-ben mi történik?
A H1-ben ez a váz **élő csatornává** válik:
- a fájlokból tényleges geometry revisionök lesznek,
- a revisionökből part/sheet entitások,
- ezekből futási snapshot,
- a snapshotból worker input,
- és az eredményből viewer/projection + artifact kimenet.

Ez az első olyan fázis, ahol már ténylegesen vizsgálható:
- mennyire jó a modell,
- mennyire stabil a run pipeline,
- mennyire működik a frontend/backoffice integráció,
- és hol vannak a valódi technológiai hiányok.

---

## H1 scope

## H1-be tartozik

- DXF upload flow
- geometry parse és audit pipeline minimum működő szintje
- geometry revision státuszgép
- geometry derivative képzés minimum nesting/viewer célra
- part és sheet revision workflow
- project part requirement kezelés
- project sheet input kezelés
- run creation + snapshot build
- run queue + worker lease + retry alaplogika
- engine adapter első működő implementációja
- raw solver output mentése
- projection táblák feltöltése
- SVG/DXF/report artifact generálás minimum szintje
- run metrics alapcsomag
- platform smoke-flow
- RLS és alap jogosultság éles működése

## H1-be nem tartozik teljes mélységben

- végleges manufacturing rule engine
- full lead-in/lead-out authoring UI
- teljes gépspecifikus postprocessor készlet
- inventory/remnant stock üzleti mélylogika
- multi-run batch stratégiaoptimalizálás
- fejlett solver tuning és metaheurisztikus felsőréteg
- végleges production scheduling
- végleges CAD-szintű szerkesztés

A H1 célja a **megbízható platformcsatorna**, nem a teljes gyártási ökoszisztéma lezárása.

---

## H1 architekturális döntések

## 1. A geometry pipeline már nem lehet kézi/implicit

H1-ben a geometry feldolgozásnak formalizált pipeline-ná kell válnia.

A kötelező szakaszok:

1. source file regisztráció
2. parse
3. alap kontúr- és entitásellenőrzés
4. normalizálás
5. canonical geometry revision mentés
6. validation report mentés
7. derivative képzés

A “feltöltöm a DXF-et és valami valahol majd használja” modell itt már nem megengedhető.

---

## 2. A part és sheet világ revízió-alapon működjön

H1-ben már tilos közvetlenül nyers geometry fájlból futtatni.

A helyes lánc:

- source file
- geometry revision
- part revision / sheet revision
- project requirement / project sheet input
- run snapshot

Ez azért kritikus, mert:
- a geometria auditálható,
- ugyanaz a part több projektben is használható,
- ugyanaz a source file több iteráción át is kezelhető,
- és a snapshot pontosan meg tudja mondani, hogy melyik revision ment a solverbe.

---

## 3. A geometry derivative modell legyen ténylegesen használatban

H1-ben a `geometry_derivatives` tábla már ne csak “jövőbeni hely” legyen, hanem aktív réteg.

Minimum derivative-k:
- `nesting_canonical`
- `viewer_outline`

Opcionálisan előkészítve:
- `manufacturing_canonical`

Ez azért fontos, mert:
- a solver geometriája nem ugyanaz, mint a viewer geometriája,
- és később a manufacturing ág sem támaszkodhat vakon a nesting polygonokra.

---

## 4. A run pipeline teljesen snapshot-driven legyen

A H1-ben a run létrehozáskor már ténylegesen snapshotot kell építeni.

A snapshotnak tartalmaznia kell legalább:
- selected technology profile version
- project part requirements
- project sheet inputs
- approved geometry derivative hivatkozások
- solver config
- placement priority/policy
- engine adapter számára szükséges input metaadatok

A worker **csak ebből** dolgozhat.

---

## 5. A solver outputból normalizált platformeredmény kell

A H1-ben nem elég elmenteni valami raw JSON-t.

A helyes feldolgozás:

- raw solver output → artifact
- normalized result → projection táblák
- aggregate metrics → `run_metrics`
- viewer renderables → SVG/DXF artifactok

Ez a H1 egyik legfontosabb minőségi határa.

---

## H1 részletes domainbővítés

A H0-s modellhez képest a H1-ben néhány tábla új mezőket és működési szabályokat kap.

## 1. Geometry revision státuszgép

A `geometry_revisions.status` mező legyen ténylegesen használt állapotgép:

- `uploaded`
- `parsed`
- `validated`
- `approved`
- `rejected`

H1-ben ehhez szükséges:
- parse worker vagy job
- validation report
- review action
- approval folyamat minimum admin/backoffice szinten

### Javasolt plusz mezők

```sql
alter table app.geometry_revisions
  add column if not exists parser_version text,
  add column if not exists validation_version text,
  add column if not exists normalized_at timestamptz,
  add column if not exists approved_at timestamptz,
  add column if not exists approved_by uuid references app.profiles(id) on delete set null;
```

Ezek kellenek a későbbi auditálhatósághoz.

---

## 2. Geometry validation report részletesebb szerkezete

A H1-ben a validation reportot már ne puszta blobként kezeljük, hanem legyen benne legalább:

- issue lista
- severity összesítés
- topológiai problémák
- open contour / self intersection / duplicate entity / unsupported entity jelzések
- feldolgozási figyelmeztetések
- parser/normalizer meta

Javasolt kiegészítés:

```sql
alter table app.geometry_validation_reports
  add column if not exists is_pass boolean,
  add column if not exists issue_count integer,
  add column if not exists warning_count integer,
  add column if not exists error_count integer;
```

Ez gyors query-zhetőséget ad.

---

## 3. Part revision bővítések

A H1-ben a `part_revisions` legyen egyértelműbb a nesting használat felől.

```sql
alter table app.part_revisions
  add column if not exists unit_code text default 'pcs',
  add column if not exists is_active boolean not null default true,
  add column if not exists approval_status text default 'approved';
```

H1-ben a minimum szabály:
- csak jóváhagyott revision mehet projekt requirementbe
- a solver inputban csak explicit approved derivative hivatkozás lehet

---

## 4. Sheet revision bővítések

A sheet oldalon H1-ben már hasznos, ha a jövőbeli bővítésekhez megjelenik a sheet típus és inventory-szerű előkészítés.

```sql
alter table app.sheet_revisions
  add column if not exists sheet_kind text default 'rectangular',
  add column if not exists material_id uuid references app.material_catalog(id) on delete set null,
  add column if not exists thickness_mm numeric(10,3),
  add column if not exists is_active boolean not null default true;
```

Ez azért jó, mert a projekt szintjén választott technológia és a sheet input később jobban ellenőrizhető.

---

## 5. Project part requirements üzleti használata

A H1-ben a `project_part_requirements` már ténylegesen üzleti input.

Javasolt további mezők:

```sql
alter table app.project_part_requirements
  add column if not exists external_ref text,
  add column if not exists due_group text,
  add column if not exists sort_order integer;
```

Miért?
- később ERP/MES vagy külső rendelésazonosító köthető rá
- a priority mellett lehet explicit UI-rendezés
- a requirementek csoportosíthatók

---

## 6. Run szintű metaadatok bővítése

A H1-ben a futásoknál jó, ha már van emberi és technikai azonosító.

```sql
alter table app.nesting_runs
  add column if not exists run_no bigint generated by default as identity,
  add column if not exists requested_via text,
  add column if not exists input_summary_jsonb jsonb not null default '{}'::jsonb;
```

A `run_no` hasznos emberi követéshez, a `requested_via` pedig megmondja, hogy UI, API vagy backoffice indította-e.

---

## 7. Snapshot sorosíthatóság és verziózás

A H1-ben a snapshothoz legyen egy külön verziómező.

```sql
alter table app.nesting_run_snapshots
  add column if not exists snapshot_schema_version text not null default 'v1';
```

Ez később kritikus lesz a backward compatibility miatt.

---

## 8. Run artifact metaadatok bővítése

H1-ben az artifactokat részletesebben le kell írni.

```sql
alter table app.run_artifacts
  add column if not exists content_sha256 text,
  add column if not exists byte_size bigint,
  add column if not exists created_by_component text;
```

Ez segít:
- cache-ben,
- letöltési integritásban,
- komponensszintű diagnosztikában.

---

## 9. Projection táblák viewer-felhasználásra

A H1-ben a placement projectionokat úgy kell kialakítani, hogy frontendből közvetlenül használhatók legyenek.

Javasolt bővítések:

```sql
alter table app.run_layout_sheets
  add column if not exists svg_artifact_id uuid references app.run_artifacts(id) on delete set null,
  add column if not exists dxf_artifact_id uuid references app.run_artifacts(id) on delete set null;

alter table app.run_layout_placements
  add column if not exists rotation_deg numeric(10,3),
  add column if not exists anchor_x_mm numeric(18,4),
  add column if not exists anchor_y_mm numeric(18,4),
  add column if not exists quantity_source integer default 1;
```

Ez kell ahhoz, hogy a viewer ne csak “rajzot”, hanem strukturált elhelyezési adatot kapjon.

---

## H1 Supabase SQL — részletes bővítési váz

Az alábbi SQL a H0 fölötti H1 minimálisan szükséges bővítéseinek mintája.

```sql
alter table app.geometry_revisions
  add column if not exists parser_version text,
  add column if not exists validation_version text,
  add column if not exists normalized_at timestamptz,
  add column if not exists approved_at timestamptz,
  add column if not exists approved_by uuid references app.profiles(id) on delete set null;

alter table app.geometry_validation_reports
  add column if not exists is_pass boolean,
  add column if not exists issue_count integer,
  add column if not exists warning_count integer,
  add column if not exists error_count integer;

alter table app.part_revisions
  add column if not exists unit_code text default 'pcs',
  add column if not exists is_active boolean not null default true,
  add column if not exists approval_status text default 'approved';

alter table app.sheet_revisions
  add column if not exists sheet_kind text default 'rectangular',
  add column if not exists material_id uuid references app.material_catalog(id) on delete set null,
  add column if not exists thickness_mm numeric(10,3),
  add column if not exists is_active boolean not null default true;

alter table app.project_part_requirements
  add column if not exists external_ref text,
  add column if not exists due_group text,
  add column if not exists sort_order integer;

alter table app.nesting_runs
  add column if not exists run_no bigint generated by default as identity,
  add column if not exists requested_via text,
  add column if not exists input_summary_jsonb jsonb not null default '{}'::jsonb;

alter table app.nesting_run_snapshots
  add column if not exists snapshot_schema_version text not null default 'v1';

alter table app.run_artifacts
  add column if not exists content_sha256 text,
  add column if not exists byte_size bigint,
  add column if not exists created_by_component text;

alter table app.run_layout_sheets
  add column if not exists svg_artifact_id uuid references app.run_artifacts(id) on delete set null,
  add column if not exists dxf_artifact_id uuid references app.run_artifacts(id) on delete set null;

alter table app.run_layout_placements
  add column if not exists rotation_deg numeric(10,3),
  add column if not exists anchor_x_mm numeric(18,4),
  add column if not exists anchor_y_mm numeric(18,4),
  add column if not exists quantity_source integer default 1;
```

---

## H1 szükséges szolgáltatásrétegek

A H1 nem csak adatmodell, hanem szolgáltatási logika is.

## 1. File ingest service

Feladata:
- upload metadata rögzítése
- storage path ellenőrzés
- hash számítás
- file_objects létrehozás

Bemenet:
- project_id
- fájl
- file_kind

Kimenet:
- `file_objects.id`

---

## 2. Geometry import service

Feladata:
- DXF parse
- normalizálás
- geometry revision mentés
- validation report mentés
- derivative képzés

Kimenet:
- `geometry_revisions.id`
- `geometry_validation_reports.id`
- derivative ID-k

H1-ben ez lehet még szinkron vagy külön worker job, de legyen dokumentált.

---

## 3. Part creation service

Feladata:
- geometry revision vagy derivative alapján part revision létrehozás
- default metadata rögzítése
- approved derivative kapcsolás

Ez biztosítja, hogy a solver ne közvetlen geometry revisiont kapjon, hanem part revisiont.

---

## 4. Sheet creation service

Feladata:
- sheet definition/revision létrehozása
- téglalap vagy később shape-alapú tábla rögzítése
- projektben használható inputtá alakítás

---

## 5. Run snapshot builder

Ez a H1 egyik kulcs-szolgáltatása.

Feladata:
- project selectionök összeolvasása
- aktív part requirementek összegyűjtése
- aktív sheet inputok összegyűjtése
- approved derivative ID-k kiválasztása
- solver config összeállítása
- snapshot hash képzése
- `nesting_runs` + `nesting_run_snapshots` + `run_queue` létrehozása

Ez gyakorlatilag a platform és a worker közötti határ egyik oldala.

---

## 6. Worker lease service

Feladata:
- pending run kiválasztása
- lease_token kiosztása
- leased_until frissítése
- retry kezelés

A cél az, hogy H1-ben már stabilan kezelhető legyen:
- 1 worker
- később több worker
- duplafutás elkerülése

---

## 7. Engine adapter service

Feladata:
- snapshot → solver input mapping
- solver process hívás
- stdout/stderr/raw output mentés
- exit státusz kezelése
- hibaformátum egységesítése

A H1-ben már legyen világos, hogy:
- hol képződik a solver input JSON,
- hol kerül mentésre a raw solver output,
- és melyik komponens alakítja ezt projection adattá.

---

## 8. Result normalizer service

Feladata:
- raw solver outputból run_layout_sheets feltöltése
- run_layout_placements feltöltése
- run_layout_unplaced feltöltése
- run_metrics számítása
- artifactok regisztrálása

Ez a szolgáltatás garantálja, hogy a frontend nem solver-specific adatmodellt kap.

---

## H1 alfeladatok részletes bontásban

## H1-1 — DXF upload és storage flow

### Cél
A DXF feltöltés stabil és auditálható legyen.

### Deliverable
- upload endpoint / service
- `file_objects` rekord
- storage bucket path-stratégia
- hash és metaadat mentés

### DoD
- egy DXF feltöltése után a storage és DB oldal konzisztens
- duplikátumvizsgálat legalább hash szinten lehetséges
- a fájl visszakereshető project alapján

### Kockázat
Ha ez gyenge, a teljes geometry pipeline ingatag lesz.

---

## H1-2 — Geometry parse és validation pipeline

### Cél
A feltöltött DXF-ből létrejöjjön canonical geometry revision és validation report.

### Deliverable
- parse modul
- normalizáló modul
- validation report generálás
- geometry revision státuszfrissítés
- derivative generálás

### DoD
- legalább tipikus egyszerű DXF-ek végigmennek
- a hibák riportálhatók
- geometry revision query-zhető
- nesting/viewer derivative legalább minimum szinten elkészül

---

## H1-3 — Part és sheet revision workflow

### Cél
A geometry revision üzletileg használható entitássá váljon.

### Deliverable
- part definition/revision létrehozás
- sheet definition/revision létrehozás
- project requirement és project sheet input kezelés

### DoD
- projektből kiválasztható usable part revision
- projektben megadható required_qty és priority
- projektben megadható sheet quantity és priority

---

## H1-4 — Run create és snapshot build

### Cél
Egy projektből szabályosan létrejöjjön futtatható run.

### Deliverable
- run create service
- snapshot builder
- snapshot hash
- queue rekord

### DoD
- egy run teljes inputja snapshotban rögzített
- a worker minden szükséges adatot ebből kap
- nincs közvetlen “élő DB-ből solver inputot olvasok” rövidítés

---

## H1-5 — Worker és engine adapter

### Cél
A queue-ból tényleges futás legyen.

### Deliverable
- lease logika
- worker process
- engine adapter
- raw output mentés
- státuszkezelés

### DoD
- egy queued run elindul, lefut vagy hibázik szabályosan
- a státusz átmenetek helyesek
- a logok visszakereshetők

---

## H1-6 — Result normalization és projection

### Cél
A solver eredmény platformnyelvre fordítása.

### Deliverable
- `run_layout_sheets` töltés
- `run_layout_placements` töltés
- `run_layout_unplaced` töltés
- `run_metrics` számítás

### DoD
- a frontend projectionból tud dolgozni
- unplaced listát külön kapjuk
- aggregate metrikák külön lekérdezhetők

---

## H1-7 — Artifact generálás

### Cél
Legalább alap viewer- és export artifactok jöjjenek létre.

### Minimum artifactok
- raw solver output
- report_json
- sheet_svg
- sheet_dxf
- bundle_zip opcionálisan

### DoD
- futás után visszakereshető artifact lista van
- sheet szintű vizualizáció lehetséges
- export csatorna legalább alapformában működik

---

## H1-8 — RLS és jogosultsági zárás

### Cél
A H0-ban definiált policyk valóban működjenek H1-ben a teljes flow-ra.

### Deliverable
- policy testek
- storage hozzáférési ellenőrzés
- service role boundary dokumentáció

### DoD
- felhasználó nem lát más projektet
- más projekt artifactjai nem hozzáférhetők
- worker és backend működése nem sérül

---

## H1-9 — Observability és hibakereshetőség

### Cél
A H1 platform legyen diagnosztizálható.

### Deliverable
- strukturált run logs
- component source mezők
- parser/validation/engine verziók
- error envelope formátum

### DoD
- egy hibás runról visszafejthető, hol bukott el
- geometry és run oldali hibák külön választhatók
- support és fejlesztés számára használható információ jön vissza

---

## H1-10 — End-to-end pilot flow

### Cél
Valódi mintaprojekten végigfusson a teljes platformcsatorna.

### Deliverable
- legalább 1-2 tipikus projekt
- egyszerű partok
- egyszerű sheet input
- sikeres run
- vizualizálható eredmény

### DoD
- a rendszer a teljes láncot végigviszi
- az eredmény visszanézhető
- az adatok reprodukálhatóan újrafuttathatók

---

## H1 ajánlott megvalósítási sorrend

1. upload és file ingest
2. geometry parse/validation
3. geometry derivative generation
4. part/sheet revision workflow
5. project requirements és sheet inputs
6. run snapshot builder
7. queue + worker lease
8. engine adapter
9. result normalizer
10. artifact generation
11. RLS/policy test
12. end-to-end pilot

Ez a sorrend azért helyes, mert:
- először a bemenet stabilizálódik,
- utána a köztes entitások,
- és csak ezután a futtatási csatorna.

---

## H1 első teljes smoke-flow

A H1 végén minimum ezt kell tudni:

1. user létrehoz egy projektet
2. kiválaszt egy technology profile versiont
3. feltölt egy DXF-et
4. létrejön `file_objects`
5. a geometry import service parse-olja
6. létrejön `geometry_revisions`
7. létrejön `geometry_validation_reports`
8. létrejön `geometry_derivatives(nesting_canonical, viewer_outline)`
9. a felhasználó vagy backoffice létrehoz egy `part_revision`-t
10. létrehoz egy `sheet_revision`-t
11. létrehoz egy `project_part_requirement` rekordot
12. létrehoz egy `project_sheet_input` rekordot
13. run create
14. snapshot build
15. queue record
16. worker lease-eli
17. engine adapter solver inputot generál
18. solver lefut
19. raw output artifact mentődik
20. result normalizer projection táblákat tölt
21. sheet SVG/DXF artifact elkészül
22. run metrics kitöltődik
23. a frontend lekérdezi az eredményt

Ha ez megbízhatóan működik, a H1 késznek tekinthető.

---

## H1 siker kritériumai

A H1 akkor tekinthető sikeresnek, ha:

- a DXF-től az eredményig végigfut a platformcsatorna
- nincs közvetlen, ad-hoc solverfüggő adatkezelés
- a geometry audit visszakereshető
- a part és sheet világ revision-alapon működik
- a runok snapshot-first módon jönnek létre
- a worker lease és retry minimálisan stabil
- az eredmény projection táblákba kerül
- a viewer nem raw solver outputot fogyaszt
- az artifactok letölthetők és típusosan nyilvántartottak
- a rendszer készen áll a H2 manufacturing/postprocess mélyítésre

---

## H1 technikai adósságok, amiket nem szabad bent hagyni

A H1 végére nem maradhat bent ilyen “majd egyszer rendberakjuk” típusú hiba:

- geometry import közvetlenül production runra kötve revision réteg nélkül
- solver input élő DB-ből olvasva snapshot helyett
- frontend solver raw JSON-ra támaszkodik
- artifact és projection össze van mosva
- part priority globális part mezőként van kezelve projekt input helyett
- validation report csak emberi olvasásra jó, gépi query-re nem
- worker lease nincs formalizálva
- raw output nincs megőrizve

Ezek később aránytalanul drágák lennének.

---

## H1 kimeneti dokumentumcsomag

A H1 lezárásához ideális esetben legyen:

- `docs/platform/h1_geometry_pipeline.md`
- `docs/platform/h1_part_sheet_workflow.md`
- `docs/platform/h1_run_snapshot_contract.md`
- `docs/platform/h1_worker_and_engine_adapter.md`
- `docs/platform/h1_result_normalization.md`
- `docs/platform/h1_artifacts_and_viewer.md`
- `supabase/migrations/...`
- `supabase/seed.sql` minimum catalog és demo adatokkal
- smoke-flow tesztdokumentum

---

## H1 tesztstratégia minimum

### Adatmodell tesztek
- FK és unique konzisztencia
- approved derivative hivatkozások
- project ownership és RLS

### Pipeline tesztek
- DXF upload → geometry revision
- geometry revision → part revision
- part/sheet → run snapshot
- run → worker → projection

### Hibatesztek
- hibás DXF
- hiányzó derivative
- hiányzó technology selection
- solver error
- artifact generation failure

### Jogosultsági tesztek
- más user projektje nem látható
- más user artifactja nem tölthető le
- service role működik worker pathon

---

## H1 utáni logikus következő szakasz

A H1 után már el lehet kezdeni a valódi mélyítést:

- manufacturing profile modell kibontása
- lead-in/lead-out rule setek
- manufacturing_canonical derivative használata
- postprocessor profilok aktiválása
- több solver stratégia és fejlettebb placement policy
- remnant és inventory logika
- cost/time alapú rangsorolás
- komolyabb viewer és review workflow

A H1 tehát az a pont, ahol a platform **már végig működik**, és innentől a fejlesztés már nem szerkezeti mentés, hanem képességbővítés.

---

## Egyenes összefoglalás

A H0 azt oldja meg, hogy a rendszer **jól legyen felépítve**.  
A H1 azt oldja meg, hogy a rendszer **ténylegesen végig működjön**.

A H1 végére a platformnak képesnek kell lennie arra, hogy egy DXF-ből, auditált és verziózott köztes rétegeken keresztül, futtatható nesting run és lekérdezhető eredmény legyen — úgy, hogy az egész folyamat reprodukálható, naplózott, és a későbbi manufacturing/postprocess irányok számára is tiszta maradjon.
