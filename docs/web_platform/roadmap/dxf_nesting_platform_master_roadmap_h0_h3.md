# DXF Nesting Platform — Master Roadmap (H0–H3)

## Dokumentum célja

Ez a dokumentum a DXF Nesting platform **összevont, fázisolt master roadmapja**, amely egységes keretbe rendezi a korábban külön bontott:

- **H0** — platformalap és domain/snapshot gerinc
- **H1** — működő DXF → geometry → run → eredmény csatorna
- **H2** — manufacturing és postprocess domain aktiválása
- **H3** — stratégiai optimalizálás, scoring, ranking, remnant és döntéstámogatás

szakaszokat.

A cél nem pusztán az, hogy “mi következik mi után”, hanem hogy világos legyen:

- milyen **architekturális döntések** rögzülnek,
- milyen **domainrétegek** épülnek fel,
- milyen **Supabase/PostgreSQL adatmodell** szükséges,
- milyen **szolgáltatásrétegek** kellenek,
- és a rendszer hogyan jut el egy egyszerű nesting platformból egy **ipari döntéstámogató és gyártásközeli rendszerig**.

---

# 1. A platform végső célképe

A rendszer végső célja nem egyetlen nesting engine köré épített segédprogram, hanem egy **moduláris, auditálható, verziózott, Supabase-alapú gyártási workflow platform**, amelyben a nesting engine csak egy jól körülhatárolt számítómodul.

A végső platform fő rétegei:

1. **Platform Core**
   - projektek
   - profilok
   - technológiai kiválasztások
   - requirementek
   - run orchestration

2. **Geometry Pipeline**
   - fájlfeltöltés
   - DXF parse
   - normalizálás
   - validáció
   - canonical belső geometria
   - derivative réteg

3. **Nesting Engine Adapter**
   - snapshot → solver input
   - solver futtatás
   - raw output kezelés
   - projection és artifact visszaírás

4. **Viewer / Reporting Layer**
   - sheet és placement projection
   - SVG/DXF/report artifactok
   - strukturált lekérdezési réteg

5. **Manufacturing Layer**
   - manufacturing profile-ok
   - contour classification
   - cut rule rendszer
   - lead-in / lead-out
   - manufacturing plan

6. **Postprocess Layer**
   - machine-neutral export
   - machine-specific adapterek
   - machine-ready artifactok

7. **Decision / Optimization Layer**
   - multi-run stratégia
   - scoring
   - ranking
   - remnant és inventory
   - review és selected run workflow

---

# 2. Globális architekturális alapelvek

Ezek a teljes roadmapen végig kötelező elvek.

## 2.1. A nesting engine külön modul

A solver nem olvassa közvetlenül a domain táblákat, és nem válik a teljes alkalmazás központi adatforrásává.

A helyes modell:

1. platform snapshotot képez
2. worker a snapshotból solver inputot állít elő
3. solver fut
4. platform normalizálja az eredményt

## 2.2. Definíció, használat, snapshot és artifact külön világ

Egy entitásnak külön kell kezelni:

- élő definícióját
- projektbeli használatát
- run-szintű snapshotját
- artifactként való kimenetét

Ez a teljes adatmodell kulcselve.

## 2.3. A Supabase a központi állapot- és metaadattár

A Supabase/Postgres tárolja:

- üzleti definíciókat
- revíziókat
- kiválasztásokat
- snapshotokat
- projectionöket
- metrikákat
- artifact hivatkozásokat

A solver belső memóriája nem domain truth.

## 2.4. Snapshot-first futási modell

Minden futás snapshotból fusson.

A worker ne élő projektállapotból, ne élő technológiai profilból, ne élő manufacturing profile-ból dolgozzon.

## 2.5. A belső geometria ne DXF és ne SVG legyen

- **DXF** = bemeneti és exportformátum
- **SVG** = viewer/artifact formátum
- **canonical geometry** = belső, verziózott JSON-alapú modell

## 2.6. Két külön belső geometriai világ kell

- `nesting_canonical`
- `manufacturing_canonical`

Ezek nem azonos célra léteznek, és nem szabad őket összemosni.

## 2.7. A platform truth rétege nem egyenlő a machine-ready exporttal

A machine-ready output csak artifact.  
A domain truth marad:

- revision
- snapshot
- projection
- manufacturing plan
- metrics
- review és selection state

---

# 3. Roadmap áttekintés fázisonként

## H0 — Platformalap és gerinc

### Fő cél
A rendszer strukturális alapjainak lezárása.

### Eredmény
- stabil domainmodell
- Supabase alapséma
- geometry revision modell
- run snapshot gerinc
- artifact/projection szétválasztás
- manufacturing és postprocess helyének kijelölése

### Fő fókusz
“Jól legyen felépítve a rendszer.”

---

## H1 — Működő platformcsatorna

### Fő cél
A teljes DXF → geometry → part/sheet → snapshot → run → eredmény lánc működőképessé tétele.

### Eredmény
- DXF upload
- geometry parse/validation
- part és sheet revision workflow
- run create
- queue és worker
- solver adapter
- projection és artifact output

### Fő fókusz
“Végig működjön a platform.”

---

## H2 — Manufacturing és postprocess aktiválása

### Fő cél
A nesting eredményből manufacturing plan és gyártásközeli köztes réteg létrehozása.

### Eredmény
- manufacturing profile domain
- contour classification
- cut rule setek
- lead-in / lead-out alaplogika
- manufacturing plan
- preview és postprocess alap

### Fő fókusz
“A platform ne csak elhelyezzen, hanem gyártási szándékot is kezeljen.”

---

## H3 — Optimalizálás, összehasonlítás, remnant és döntéstámogatás

### Fő cél
A platform tudjon több runból választani, ezeket értékelni, rangsorolni, és a remnant világot újrafelhasználható erőforrásként kezelni.

### Eredmény
- strategy és scoring profilok
- batch runok
- ranking
- remnant domain
- stock/remnant input resolver
- business metrics
- review és selected run workflow

### Fő fókusz
“A platform ne csak számoljon, hanem választható opciókat és döntéstámogatást adjon.”

---

# 4. Fázisok részletesen

# 4.1. H0 — Platformalap

## H0 fő célja
A teljes rendszer hosszú távon helyes szerkezeti alapjának lezárása.

## H0 kulcselemei
- projekt- és profilalapú domain
- technológiai profilok
- fájlobjektumok
- geometry revisionök
- derivative helyének előkészítése
- part/sheet definíciók és revíziók
- run/snapshot/queue/log gerinc
- artifact/projection alapréteg
- RLS és storage stratégia

## H0 fő DoD
- a domainstruktúra konzisztens
- a solver helye tiszta
- a snapshot-first modell rögzített
- a frontend később projectionből építkezhet
- a manufacturing/postprocess később architekturális törés nélkül ráépíthető

## H0 kritikus döntések
- a placement priority projektigény-szintű
- a belső geometria saját canonical modell
- az artifact és projection külön tárolódik
- a worker csak snapshotból dolgozik

---

# 4.2. H1 — Működő DXF → run csatorna

## H1 fő célja
Valós, végigvezetett platformfolyamat létrehozása.

## H1 kulcselemei
- upload és storage flow
- DXF parse és validation
- geometry derivative generation
- part/sheet revision workflow
- project part requirement és sheet input kezelés
- run create és snapshot builder
- queue, lease és worker
- solver adapter
- result normalizer
- sheet SVG/DXF/report artifactok

## H1 fő DoD
- egy DXF-ből teljes run hozható létre
- a solver input snapshotból keletkezik
- a run eredménye projection táblákba kerül
- a viewer nem raw solver outputot fogyaszt
- a pipeline auditálható

## H1 kritikus döntések
- geometry revision státuszgép tényleges használata
- approved derivative alapú part revision használat
- result normalization kötelező
- projection a frontend truth réteg

---

# 4.3. H2 — Manufacturing és postprocess

## H2 fő célja
A nesting eredményből gyártásközeli köztes világ létrehozása.

## H2 kulcselemei
- manufacturing profile-ok
- manufacturing profile versionök
- contour classification
- cut rule setek
- contour rule-k
- manufacturing snapshot bővítés
- run_manufacturing_plans
- run_manufacturing_contours
- manufacturing preview
- postprocessor adapter alap
- manufacturing metrics

## H2 fő DoD
- a platform külön kezeli a nesting és manufacturing geometriát
- contourok technológiailag osztályozhatók
- outer/inner szabályok működnek
- manufacturing plan keletkezik run után
- preview és machine-neutral export elérhető
- a postprocessor külön modul marad

## H2 kritikus döntések
- manufacturing domain külön marad a technology_profile-tól
- a cut rule rendszer szerkeszthető és auditálható
- a machine-ready export nem válik domain truth adattá
- a contour classification tárolt, visszakereshető eredmény

---

# 4.4. H3 — Optimalizálás és döntéstámogatás

## H3 fő célja
A platformból többfutásos, értékelő és döntéstámogató rendszer legyen.

## H3 kulcselemei
- run strategy profilok
- scoring profilok
- project-level scoring/strategy selection
- run batch-ek
- run evaluation
- ranking
- selected run
- review workflow
- remnant domain
- stock vs remnant input source tracking
- business metrics
- comparison projection

## H3 fő DoD
- több run kezelhető ugyanarra a projektre
- a scoring és ranking reprodukálható
- a remnant újrafelhasználható entitás
- a selected run külön nyilvántartott
- a platform decision layerként is működik

## H3 kritikus döntések
- a ranking külön domain
- a remnant nem csak artifact
- a stock és remnant külön világ
- a review és approval külön a technikai run állapottól

---

# 5. Összevont domainmodell

Az alábbi a teljes H0–H3 domainstruktúra összevont nézete.

## 5.1. Identitás és projektvilág
- `profiles`
- `projects`
- `project_settings`

## 5.2. Technológia
- `machine_catalog`
- `material_catalog`
- `kerf_lookup_rules`
- `technology_profiles`
- `technology_profile_versions`
- `project_technology_selection`

## 5.3. Geometry
- `file_objects`
- `geometry_revisions`
- `geometry_validation_reports`
- `geometry_review_actions`
- `geometry_derivatives`
- `geometry_contour_classes`

## 5.4. Part és sheet
- `part_definitions`
- `part_revisions`
- `project_part_requirements`
- `sheet_definitions`
- `sheet_revisions`
- `project_sheet_inputs`

## 5.5. Run orchestration
- `nesting_runs`
- `nesting_run_snapshots`
- `run_queue`
- `run_logs`

## 5.6. Eredmény és megjelenítés
- `run_artifacts`
- `run_layout_sheets`
- `run_layout_placements`
- `run_layout_unplaced`
- `run_metrics`

## 5.7. Manufacturing
- `manufacturing_profiles`
- `manufacturing_profile_versions`
- `project_manufacturing_selection`
- `cut_rule_sets`
- `cut_contour_rules`
- `run_manufacturing_plans`
- `run_manufacturing_contours`
- `run_manufacturing_metrics`

## 5.8. Postprocess
- `postprocessor_profiles`
- `postprocessor_profile_versions`

## 5.9. Strategy / scoring / comparison
- `run_strategy_profiles`
- `run_strategy_profile_versions`
- `scoring_profiles`
- `scoring_profile_versions`
- `project_run_strategy_selection`
- `project_scoring_selection`
- `run_batches`
- `run_batch_items`
- `run_evaluations`
- `run_ranking_results`
- `project_selected_runs`
- `run_reviews`
- `run_business_metrics`

## 5.10. Inventory / remnant
- `stock_sheet_items`
- `remnant_definitions`
- `remnant_revisions`
- `remnant_stock_items`
- `run_input_sheet_sources`

---

# 6. Összevont szolgáltatásréteg

A roadmap során a következő fő szolgáltatások épülnek ki.

## H0–H1 fókusz
- file ingest service
- geometry import service
- part creation service
- sheet creation service
- run snapshot builder
- worker lease service
- engine adapter service
- result normalizer service

## H2 fókusz
- manufacturing profile resolver
- contour classification service
- manufacturing plan builder
- manufacturing preview generator
- postprocessor adapter service

## H3 fókusz
- batch run orchestrator
- run evaluation engine
- ranking engine
- remnant extractor
- inventory-aware input resolver
- business metrics calculator
- comparison projection builder
- review workflow service

---

# 7. Összevont SQL roadmap szemlélet

A teljes fejlesztés során az SQL migrációk logikája így érdemes épüljön.

## H0 migrációk
- enumok
- core táblák
- revision és run gerinc
- artifact/projection alapok

## H1 migrációk
- geometry pipeline bővítések
- part/sheet és run meta mezők
- snapshot schema version
- artifact metadata bővítések
- viewer célú projection mezők

## H2 migrációk
- manufacturing profile bővítések
- cut rule set és contour rule táblák
- contour class táblák
- manufacturing plan táblák
- postprocessor bővítések
- manufacturing metrics

## H3 migrációk
- strategy és scoring profilok
- batch és ranking táblák
- selected run és review workflow
- remnant és stock domain
- business metrics és source tracking

---

# 8. Fázisok közötti függőségek

## H0 → H1
H1 csak akkor építhető tisztán, ha H0-ban már megvan:
- geometry revision modell
- part/sheet revíziós világ
- run snapshot gerinc
- artifact/projection szétválasztás

## H1 → H2
H2 csak akkor stabil, ha H1-ben már működik:
- derivative pipeline
- run projection
- result normalization
- part revision és approved derivative logika

## H2 → H3
H3 csak akkor értelmes, ha H2-ben már van:
- manufacturing metrics
- manufacturing plan
- postprocess-kompatibilis köztes világ
- gyártási döntési metaadatok

---

# 9. Kockázati pontok

## 9.1. Túl korai összemosás
Ha a technology, manufacturing és postprocess világ túl korán összecsúszik, a rendszer hamar kaotikussá válik.

## 9.2. Solver-központú torzulás
Ha a platform minden döntést a solver raw output köré szervez, a későbbi gyártási és üzleti rétegek nehezen lesznek ráépíthetők.

## 9.3. JSON-zsákutca
Ha a szabályrendszerek mind egy-egy hatalmas JSON mezőben végzik, a UI, az audit és a diffelhetőség sérül.

## 9.4. Remnant alultervezése
Ha a remnant csak artifactként él tovább, a H3 döntéstámogató és újrafelhasználási logikája nem tud tisztán kialakulni.

## 9.5. Frontendre tolt üzleti logika
A ranking, scoring és comparison nem csúszhat át teljesen a frontendbe.

---

# 10. Ajánlott végrehajtási sorrend

## Első blokk — H0
1. architektúra véglegesítés
2. domainmodell lezárása
3. Supabase alapséma
4. storage stratégia
5. RLS alapok

## Második blokk — H1
6. upload és geometry pipeline
7. part/sheet workflow
8. run snapshot builder
9. worker + engine adapter
10. result normalization
11. artifact + projection flow
12. H1 pilot

## Harmadik blokk — H2
13. manufacturing profile domain
14. manufacturing derivative pipeline
15. contour classification
16. cut rule rendszer
17. manufacturing plan builder
18. preview és postprocessor alap
19. H2 pilot

## Negyedik blokk — H3
20. run strategy és scoring domain
21. batch és ranking
22. remnant + stock domain
23. business metrics
24. review és selected run workflow
25. comparison projection
26. H3 pilot

---

# 11. Összevont smoke-flow vízió

A roadmap végére a teljes platform ideális folyamata így néz ki:

1. user létrehoz projektet
2. kiválaszt technology profile-t
3. kiválaszt manufacturing profile-t
4. opcionálisan kiválaszt strategy és scoring profile-t
5. feltölt DXF-eket
6. geometry revision és derivative-ek keletkeznek
7. part revision és sheet revision létrejön
8. project requirementek és sheet inputok rögzülnek
9. run vagy run batch jön létre
10. snapshotok készülnek
11. worker futtatja a solver(eke)t
12. projection és artifact eredmények létrejönnek
13. manufacturing plan képződik
14. preview és export artifactok képződnek
15. scoring és ranking lefut
16. selected run kiválasztás történik
17. remnant entitások képződnek
18. remnant későbbi inputként újrahasználható

Ez a teljes platformciklus.

---

# 12. Mit nem szabad összemosni

Ez az egész roadmap egyik legfontosabb fejezete.

## Nem szabad összemosni:
- source file vs canonical geometry
- geometry revision vs part revision
- project requirement vs run snapshot
- solver output vs platform projection
- nesting geometry vs manufacturing geometry
- manufacturing plan vs machine-ready output
- stock sheet vs remnant
- scoring logic vs frontend megjelenítés
- technical run success vs business selection

Ha ez a szétválasztás megmarad, a platform skálázható és bővíthető marad.

---

# 13. Lezáró összefoglalás

A H0–H3 roadmap lényege:

- **H0**: jó alap
- **H1**: működő csatorna
- **H2**: gyártásközeli logika
- **H3**: döntéstámogató és optimalizáló réteg

A teljes fejlesztési irány kulcsa, hogy a platform végig:

- moduláris maradjon,
- snapshot-first legyen,
- auditálható maradjon,
- külön kezelje a geometriai, gyártási és üzleti rétegeket,
- és soha ne csússzon vissza egy solver-központú, ad-hoc felépítésbe.

Ha ez a roadmap fegyelmezetten végig van vive, a rendszerből nem csak egy nesting alkalmazás lesz, hanem egy **ipari szintű, bővíthető, Supabase-alapú gyártási optimalizációs platform**.
