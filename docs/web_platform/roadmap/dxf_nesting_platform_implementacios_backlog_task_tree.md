# DXF Nesting Platform — Implementációs Backlog / Task Tree

## Dokumentum célja

Ez a dokumentum a H0–H3 master roadmap **végrehajtható, task-orientált bontása**.  
A cél az, hogy a stratégiai roadmapből egy olyan strukturált implementációs fa jöjjön létre, amely alapján a fejlesztés:

- fázisokra,
- epicekre,
- konkrét taskokra,
- függőségekre,
- és Definition of Done szintű lezárási feltételekre

bontható.

Ez a dokumentum nem helyettesíti a részletes specifikációkat, hanem azokat **szállítható fejlesztési egységekké** fordítja le.

---

# 1. Használati elv

A task tree négy szintből áll:

1. **Phase**
   - H0 / H1 / H2 / H3

2. **Epic**
   - nagyobb témakör vagy fejlesztési csomag

3. **Task**
   - konkrét implementációs egység

4. **Subtask / Checkpoint**
   - opcionális, ha a task tovább bontható

Minden taskhoz ideálisan tartozik:
- cél
- input
- output
- fő függőségek
- DoD

---

# 2. Átfogó végrehajtási stratégia

A teljes roadmap végrehajtása során ezt az alapelvet kell követni:

- előbb a **szerkezetet** zárjuk le,
- utána a **működő platformcsatornát**,
- utána a **gyártási réteget**,
- végül a **döntéstámogató és optimalizációs réteget**.

Ennek megfelelően a backlog fő sorrendje:

1. **H0** — platform gerinc
2. **H1** — működő DXF/run pipeline
3. **H2** — manufacturing/postprocess
4. **H3** — strategy/scoring/remnant/comparison

---

# 3. H0 — Platformalap backlog

## H0-E1 — Architektúra és domain alapok

### H0-E1-T1 — Modulhatárok véglegesítése
**Cél:** A platform fő logikai moduljainak lezárása.  
**Output:** architektúra-dokumentum, modulhatár definíció.  
**Függőség:** nincs.  
**DoD:** egyértelmű a Platform Core, Geometry Pipeline, Engine Adapter, Viewer, Manufacturing, Postprocess, Decision Layer határa.

### H0-E1-T2 — Domain entitástérkép véglegesítése
**Cél:** A fő entitáscsoportok és kapcsolataik meghatározása.  
**Output:** domainmodell-dokumentum.  
**Függőség:** H0-E1-T1.  
**DoD:** külön entitásként definiált a definíció, használat, snapshot, artifact.

### H0-E1-T3 — Snapshot-first alapelv formális rögzítése
**Cél:** A futási modell szerződésének lezárása.  
**Output:** run contract váz.  
**Függőség:** H0-E1-T2.  
**DoD:** dokumentált, hogy worker kizárólag snapshotból dolgozik.

---

## H0-E2 — Supabase core schema

### H0-E2-T1 — Enumok és core schema létrehozása
**Cél:** A fő enumok és `app` schema létrehozása.  
**Output:** első migrációs csomag.  
**Függőség:** H0-E1-T2.  
**DoD:** minden szükséges H0 enum létezik.

### H0-E2-T2 — Core projekt- és profile táblák
**Cél:** `profiles`, `projects`, `project_settings` létrehozása.  
**Output:** migráció.  
**Függőség:** H0-E2-T1.  
**DoD:** projekt alapvilág működik.

### H0-E2-T3 — Technology domain alapok
**Cél:** machine/material/kerf/technology profile táblák létrehozása.  
**Output:** migráció + seed váz.  
**Függőség:** H0-E2-T1.  
**DoD:** technológiai profilverzió és projektkiválasztás tárolható.

---

## H0-E3 — Geometry és revision gerinc

### H0-E3-T1 — File object modell
**Cél:** fájlmetaadat és storage hivatkozási réteg kialakítása.  
**Output:** `file_objects`.  
**Függőség:** H0-E2-T2.  
**DoD:** fájl upload metaadat tárolható.

### H0-E3-T2 — Geometry revision modell
**Cél:** canonical geometry revision tábla létrehozása.  
**Output:** `geometry_revisions`.  
**Függőség:** H0-E3-T1.  
**DoD:** source file → geometry revision kapcsolat létezik.

### H0-E3-T3 — Validation és review táblák
**Cél:** audit és review réteg létrehozása.  
**Output:** `geometry_validation_reports`, `geometry_review_actions`.  
**Függőség:** H0-E3-T2.  
**DoD:** geometry revision auditálható.

### H0-E3-T4 — Geometry derivatives helyének előkészítése
**Cél:** derivative alapstruktúra létrehozása.  
**Output:** `geometry_derivatives`.  
**Függőség:** H0-E3-T2.  
**DoD:** legalább nesting/manufacturing/viewer derivative helye létezik.

---

## H0-E4 — Part, sheet és project input gerinc

Megjegyzes (H0 audit mapping):
- A H0 vegleges taskfaban ez a resz tartalmilag a `H0-E2-T4` (part) es `H0-E2-T5` (sheet) taskokban kerult vegrehajtasra.
- A jelen szekcio historikus bontas, a completion matrixban az E2-T4/E2-T5 tasknevek az elsodlegesek.

### H0-E4-T1 — Part definition és revision modellek
**Cél:** part definíciók és revíziók létrehozása.  
**Output:** `part_definitions`, `part_revisions`.  
**Függőség:** H0-E3-T2.  
**DoD:** geometry revisionből part revision képezhető.

### H0-E4-T2 — Sheet definition és revision modellek
**Cél:** sheet definíciók és revíziók.  
**Output:** `sheet_definitions`, `sheet_revisions`.  
**Függőség:** H0-E2-T2.  
**DoD:** alap sheet revision tárolható.

### H0-E4-T3 — Project part requirement modell
**Cél:** projektigények tárolása priority/policy mezőkkel.  
**Output:** `project_part_requirements`.  
**Függőség:** H0-E4-T1.  
**DoD:** required_qty + placement_priority + placement_policy tárolható.

### H0-E4-T4 — Project sheet input modell
**Cél:** projektbe választott táblák kezelése.  
**Output:** `project_sheet_inputs`.  
**Függőség:** H0-E4-T2.  
**DoD:** sheet input quantity/priority rögzíthető.

---

## H0-E5 — Run gerinc

### H0-E5-T1 — Nesting run és snapshot modellek
**Cél:** futási entitások létrehozása.  
**Output:** `nesting_runs`, `nesting_run_snapshots`.  
**Függőség:** H0-E4-T3, H0-E4-T4.  
**DoD:** snapshot hash-el tárolható run.

### H0-E5-T2 — Queue és log modellek
**Cél:** queue/lease/log alapréteg létrehozása.  
**Output:** `run_queue`, `run_logs`.  
**Függőség:** H0-E5-T1.  
**DoD:** pending/leased/done/error queue modell adott.

### H0-E5-T3 — Artifact és projection modellek
**Cél:** output táblák létrehozása.  
**Output:** `run_artifacts`, `run_layout_*`, `run_metrics`.  
**Függőség:** H0-E5-T1.  
**DoD:** artifact és projection külön tárolható.

---

## H0-E6 — Security és storage alapok

### H0-E6-T1 — Storage bucket stratégia
**Cél:** source/artifact bucketek definiálása.  
**Output:** bucket naming és path policy.  
**Függőség:** H0-E3-T1.  
**DoD:** strukturált storage naming dokumentált.

### H0-E6-T2 — RLS policy alapok
**Cél:** alap hozzáférés-védelem.  
**Output:** RLS policy migrációk.  
**Függőség:** H0-E2-T2, H0-E5-T3.  
**DoD:** user csak saját projektjeit és kapcsolt entitásait látja.

---

## H0-E7 — H0 lezárás

### H0-E7-T1 — H0 end-to-end struktúra audit
**Cél:** ellenőrizni, hogy a H0 szerkezeti céljai teljesülnek-e.  
**Output:** H0 audit checklista / report.  
**Függőség:** H0 összes előző epic.  
**DoD:** a H1 tiszta alapra építhető.

H0 zaro gate source-of-truth:
- `docs/web_platform/roadmap/h0_lezarasi_kriteriumok_es_h1_entry_gate.md`

---

# 4. H1 — Működő platformcsatorna backlog

## H1-E1 — File ingest és upload flow

### H1-E1-T1 — Upload endpoint/service
**Cél:** DXF feltöltés backend oldali fogadása.  
**Output:** működő upload flow.  
**Függőség:** H0-E3-T1, H0-E6-T1.  
**DoD:** fájl feltölthető és regisztrálható.

### H1-E1-T2 — File hash és metadata kezelés
**Cél:** hash, byte_size, mime és storage meta kezelése.  
**Output:** ingest metadata pipeline.  
**Függőség:** H1-E1-T1.  
**DoD:** duplikációvizsgálat és audit alap adott.

---

## H1-E2 — Geometry import pipeline

### H1-E2-T1 — DXF parser integráció
**Cél:** feltöltött DXF parse-olása.  
**Output:** parse service.  
**Függőség:** H1-E1-T1.  
**DoD:** tipikus DXF-ekből geometry revision képezhető.

### H1-E2-T2 — Geometry normalizer
**Cél:** canonical geometry előállítása.  
**Output:** normalized geometry pipeline.  
**Függőség:** H1-E2-T1.  
**DoD:** geometry_jsonb kitölthető determinisztikusan.

### H1-E2-T3 — Validation report generator
**Cél:** geometry problémák és figyelmeztetések előállítása.  
**Output:** validation report.  
**Függőség:** H1-E2-T2.  
**DoD:** parse és geometry hibák auditálhatók.

### H1-E2-T4 — Geometry derivative generator (H1 minimum)
**Cél:** nesting_canonical és viewer_outline derivative képzése.  
**Output:** derivative generálás.  
**Függőség:** H1-E2-T2.  
**DoD:** approved derivative hivatkozható part revisionből.

---

## H1-E3 — Part/sheet workflow

### H1-E3-T1 — Part creation service
**Cél:** geometry revisionből part revision létrehozása.  
**Output:** part workflow.  
**Függőség:** H1-E2-T4, H0-E4-T1.  
**DoD:** approved part revision létrehozható.

### H1-E3-T2 — Sheet creation service
**Cél:** alap sheet revision létrehozása.  
**Output:** sheet workflow.  
**Függőség:** H0-E4-T2.  
**DoD:** projektbe választható sheet revision kezelhető.

### H1-E3-T3 — Project requirement management
**Cél:** UI/API oldali part requirement kezelés.  
**Output:** requirement flow.  
**Függőség:** H0-E4-T3, H1-E3-T1.  
**DoD:** projektigények kezelhetők.

### H1-E3-T4 — Project sheet input management
**Cél:** UI/API oldali sheet input kezelés.  
**Output:** sheet input flow.  
**Függőség:** H0-E4-T4, H1-E3-T2.  
**DoD:** projekt sheet inputok kezelhetők.

---

## H1-E4 — Run orchestration

### H1-E4-T1 — Run snapshot builder
**Cél:** projektből futtatható snapshot képezése.  
**Output:** snapshot builder service.  
**Függőség:** H1-E3-T3, H1-E3-T4, H0-E5-T1.  
**DoD:** minden solver-input releváns adat snapshotba kerül.

### H1-E4-T2 — Run create API/service
**Cél:** run és queue rekord létrehozása.  
**Output:** run creation flow.  
**Függőség:** H1-E4-T1.  
**DoD:** queued run keletkezik.

### H1-E4-T3 — Queue lease mechanika
**Cél:** pending runok worker általi felvétele.  
**Output:** worker lease logic.  
**Függőség:** H0-E5-T2.  
**DoD:** duplafutás elkerülhető.

---

## H1-E5 — Solver integráció

### H1-E5-T1 — Engine adapter input mapping
**Cél:** snapshot → solver input JSON.  
**Output:** input adapter.  
**Függőség:** H1-E4-T1.  
**DoD:** solver számára stabil input generálható.

### H1-E5-T2 — Solver process futtatás
**Cél:** workerből tényleges solver indítás.  
**Output:** process runner.  
**Függőség:** H1-E5-T1, H1-E4-T3.  
**DoD:** run running/succeeded/failed állapotba megy.

### H1-E5-T3 — Raw output mentés
**Cél:** solver stdout/stderr/raw result tárolása.  
**Output:** raw artifact.  
**Függőség:** H1-E5-T2.  
**DoD:** hibák és eredmények visszakereshetők.

---

## H1-E6 — Result normalization és viewer output

### H1-E6-T1 — Result normalizer
**Cél:** solver output → projection táblák.  
**Output:** normalized placement output.  
**Függőség:** H1-E5-T3, H0-E5-T3.  
**DoD:** run_layout_* és run_metrics feltöltődik.

### H1-E6-T2 — Sheet SVG generator
**Cél:** sheet szintű viewer artifact generálása.  
**Output:** SVG artifactok.  
**Függőség:** H1-E6-T1.  
**DoD:** viewer basic render lehetséges.

### H1-E6-T3 — Sheet DXF/export artifact generator
**Cél:** exportálható sheet artifactok.  
**Output:** DXF artifactok.  
**Függőség:** H1-E6-T1.  
**DoD:** alap export visszatölthető.

---

## H1-E7 — H1 pilot és stabilizálás

### H1-E7-T1 — End-to-end pilot projekt
**Cél:** teljes H1 lánc kipróbálása mintaprojekten.  
**Output:** pilot run.  
**Függőség:** H1 összes fő epic.  
**DoD:** DXF → run → projection → artifact végigfut.

### H1-E7-T2 — H1 audit és hibajavítás
**Cél:** a H1 kritikus hiányainak zárása.  
**Output:** H1 stabilizációs report.  
**Függőség:** H1-E7-T1.  
**DoD:** H2 ráépíthető.

Aktualis statusz (2026-03-20):
- H1 closure audit lefutott, celzott route stabilizacios javitassal.
- H2 entry gate eredmeny: `PASS WITH ADVISORIES`.
- Kapcsolodo gate dokumentum:
  `docs/web_platform/roadmap/h1_lezarasi_kriteriumok_es_h2_entry_gate.md`

---

# 5. H2 — Manufacturing backlog

## H2-E1 — Manufacturing profile domain

### H2-E1-T1 — Manufacturing profile CRUD
**Cél:** manufacturing profilok kezelése.  
**Output:** profile flow.  
**Függőség:** H0 manufacturing placeholder táblák.  
**DoD:** manufacturing profile version kiválasztható projekthez.

### H2-E1-T2 — Project manufacturing selection
**Cél:** projekt manufacturing kiválasztás bekötése.  
**Output:** selection flow.  
**Függőség:** H2-E1-T1.  
**DoD:** project_manufacturing_selection működik.

---

## H2-E2 — Manufacturing geometry pipeline

### H2-E2-T1 — manufacturing_canonical derivative generation
**Cél:** külön manufacturing derivative képzése.  
**Output:** manufacturing derivative pipeline.  
**Függőség:** H1-E2-T2.  
**DoD:** part revisionhöz manufacturing derivative kapcsolható.

### H2-E2-T2 — Contour classification service
**Cél:** contour outer/inner/feature class osztályozása.  
**Output:** classification pipeline.  
**Függőség:** H2-E2-T1.  
**DoD:** geometry_contour_classes feltölthető.

---

## H2-E3 — Cut rule rendszer

### H2-E3-T1 — Cut rule set modell
**Cél:** cut_rule_sets tábla és CRUD.  
**Output:** rule set domain.  
**Függőség:** H2-E1-T1.  
**DoD:** rule setek verziózhatók.

### H2-E3-T2 — Cut contour rules modell
**Cél:** contour-szintű szabályok kezelése.  
**Output:** cut_contour_rules CRUD.  
**Függőség:** H2-E3-T1.  
**DoD:** outer/inner külön szabályok tárolhatók.

### H2-E3-T3 — Rule matching logic
**Cél:** contour class → rule hozzárendelés.  
**Output:** matching engine.  
**Függőség:** H2-E2-T2, H2-E3-T2.  
**DoD:** contouronként meghatározható a használt rule.

---

## H2-E4 — Manufacturing snapshot és plan

### H2-E4-T1 — Snapshot manufacturing bővítés
**Cél:** manufacturing selection snapshotba emelése.  
**Output:** snapshot schema bővítés.  
**Függőség:** H2-E1-T2, H2-E3-T1.  
**DoD:** manufacturing és postprocess kiválasztás snapshotolt.

### H2-E4-T2 — Manufacturing plan builder
**Cél:** run projection → manufacturing plan.  
**Output:** run_manufacturing_plans és contours.  
**Függőség:** H2-E2-T2, H2-E3-T3, H1-E6-T1.  
**DoD:** run után manufacturing plan előállítható.

### H2-E4-T3 — Manufacturing metrics calculator
**Cél:** pierce/cut length/time becslés.  
**Output:** run_manufacturing_metrics.  
**Függőség:** H2-E4-T2.  
**DoD:** alap gyártási metrikák lekérdezhetők.

---

## H2-E5 — Preview és postprocess

### H2-E5-T1 — Manufacturing preview SVG
**Cél:** gyártási terv vizualizálása.  
**Output:** manufacturing preview artifact.  
**Függőség:** H2-E4-T2.  
**DoD:** entry/lead/contour meta megjeleníthető.

### H2-E5-T2 — Postprocessor profile/version domain aktiválása
**Cél:** postprocessor kiválasztási világ működése.  
**Output:** active postprocessor selection.  
**Függőség:** H2-E1-T1.  
**DoD:** manufacturing profil postprocessorra hivatkozhat.

### H2-E5-T3 — Machine-neutral exporter
**Cél:** manufacturing planből generikus export.  
**Output:** manufacturing/export artifact.  
**Függőség:** H2-E4-T2, H2-E5-T2.  
**DoD:** machine-neutral artifact előállítható.

### H2-E5-T4 — Első machine-specific adapter (opcionális)
**Cél:** 1 célgép-család prototípus export.  
**Output:** machine-ready artifact.  
**Függőség:** H2-E5-T3.  
**DoD:** adapter-interfész validált.

---

## H2-E6 — H2 pilot és stabilizálás

### H2-E6-T1 — End-to-end manufacturing pilot
**Cél:** nesting run → manufacturing plan → preview → export.  
**Output:** pilot manufacturing flow.  
**Függőség:** H2 összes fő epic.  
**DoD:** H2 lánc végigfut.

### H2-E6-T2 — H2 audit és hibajavítás
**Cél:** manufacturing réteg stabilizálása.
**Output:** H2 audit report.
**Függőség:** H2-E6-T1.
**DoD:** H3 ráépíthető.

Aktualis statusz (2026-03-24):
- H2 closure audit lefutott, evidence-alapu completion matrixszal.
- H3 entry gate eredmeny: `PASS WITH ADVISORIES`.
- Kapcsolodo gate dokumentum:
  `docs/web_platform/roadmap/h2_lezarasi_kriteriumok_es_h3_entry_gate.md`

---

# 6. H3 — Decision layer backlog

## H3-E1 — Strategy és scoring domain

### H3-E1-T1 — Run strategy profile modellek
**Cél:** futtatási stratégiák külön domainje.  
**Output:** run_strategy_profiles, versions.  
**Függőség:** H1 stabil run flow.  
**DoD:** strategy profil projektből választható.

### H3-E1-T2 — Scoring profile modellek
**Cél:** scoring és tie-breaker világ explicit kezelése.  
**Output:** scoring_profiles, versions.  
**Függőség:** H2 manufacturing metrics alapok.  
**DoD:** scoring profile kiválasztható.

### H3-E1-T3 — Project-level selectionök
**Cél:** strategy és scoring kiválasztás projekthez.  
**Output:** project_run_strategy_selection, project_scoring_selection.  
**Függőség:** H3-E1-T1, H3-E1-T2.  
**DoD:** projectből futtatási és scoring preferencia kezelhető.

---

## H3-E2 — Batch run és candidate világ

### H3-E2-T1 — Run batch modell
**Cél:** több run egy batch-be szervezése.  
**Output:** run_batches, run_batch_items.  
**Függőség:** H3-E1-T3.  
**DoD:** comparison batch létrehozható.

### H3-E2-T2 — Batch run orchestrator
**Cél:** több run automatikus létrehozása különböző variánsokkal.  
**Output:** batch orchestrator service.  
**Függőség:** H3-E2-T1, H1-E4-T2.  
**DoD:** több candidate run generálható.

---

## H3-E3 — Evaluation és ranking

### H3-E3-T1 — Run evaluation engine
**Cél:** run score számítása.  
**Output:** run_evaluations.  
**Függőség:** H3-E1-T2, H2-E4-T3, H1-E6-T1.  
**DoD:** runonként score bontás generálható.

### H3-E3-T2 — Ranking engine
**Cél:** batch candidate-ek rangsorolása.  
**Output:** run_ranking_results.  
**Függőség:** H3-E3-T1, H3-E2-T1.  
**DoD:** batchre stabil rangsor készül.

### H3-E3-T3 — Best-by-objective lekérdezések
**Cél:** külön célfüggvény szerinti toplisták.  
**Output:** comparison queries/projections.  
**Függőség:** H3-E3-T2.  
**DoD:** material-best / cost-best / time-best / priority-best nézetek kérhetők.

---

## H3-E4 — Remnant és inventory

### H3-E4-T1 — Remnant extractor
**Cél:** runból remnant entitások képzése.  
**Output:** remnant_definitions, revisions.  
**Függőség:** H2-E4-T2.  
**DoD:** maradékanyag domain entitásként létrejön.

### H3-E4-T2 — Remnant stock kezelés
**Cél:** remnant készletszerű kezelése.  
**Output:** remnant_stock_items flow.  
**Függőség:** H3-E4-T1.  
**DoD:** remnant reserve/active állapotban kezelhető.

### H3-E4-T3 — Stock sheet domain
**Cél:** szabványos stock világ külön kezelése.  
**Output:** stock_sheet_items.  
**Függőség:** H1-E3-T2.  
**DoD:** stock és remnant külön inputforrás.

### H3-E4-T4 — Inventory-aware input resolver
**Cél:** run inputforrás választása stock/remnant/ad hoc között.  
**Output:** run_input_sheet_sources.  
**Függőség:** H3-E4-T2, H3-E4-T3.  
**DoD:** run inputforrás auditálható.

---

## H3-E5 — Business metrics és decision support

### H3-E5-T1 — Business metrics calculator
**Cél:** priority fulfilment és költségalapú metrikák számítása.  
**Output:** run_business_metrics.  
**Függőség:** H3-E3-T1, H3-E4-T4.  
**DoD:** üzleti összehasonlítás támogatott.

### H3-E5-T2 — Comparison projection builder
**Cél:** frontend-barát összehasonlító aggregációk.  
**Output:** comparison projection / summary view.  
**Függőség:** H3-E3-T2, H3-E5-T1.  
**DoD:** batch summary könnyen lekérdezhető.

---

## H3-E6 — Review és selection workflow

### H3-E6-T1 — Run review workflow
**Cél:** review stage/status világ kezelése.  
**Output:** run_reviews flow.  
**Függőség:** H3-E3-T2.  
**DoD:** reviewk rögzíthetők és nyomon követhetők.

### H3-E6-T2 — Selected run workflow
**Cél:** preferred/approved run kijelölése.  
**Output:** project_selected_runs flow.  
**Függőség:** H3-E6-T1.  
**DoD:** projekt szintű kiválasztott run létezik.

---

## H3-E7 — H3 pilot és stabilizálás

### H3-E7-T1 — Multi-run comparison pilot
**Cél:** több runból választási helyzet demonstrálása.  
**Output:** batch pilot.  
**Függőség:** H3-E2, H3-E3, H3-E5.  
**DoD:** top candidate-ek összehasonlíthatók.

### H3-E7-T2 — Remnant reuse pilot
**Cél:** remnant következő runban inputként való kipróbálása.  
**Output:** remnant reuse flow.  
**Függőség:** H3-E4.  
**DoD:** remnant tényleges újrahasználása demonstrált.

### H3-E7-T3 — H3 audit és hibajavítás
**Cél:** H3 decision layer stabilizálása.  
**Output:** H3 audit report.  
**Függőség:** H3-E7-T1, H3-E7-T2.  
**DoD:** master roadmap H0–H3 fő íve lezárt.

---

# 7. Függőségi összefoglaló

## Kritikus útvonal
1. H0 core schema és run gerinc
2. H1 geometry pipeline
3. H1 run snapshot + worker + solver adapter
4. H1 result normalization
5. H2 manufacturing derivative + contour classification
6. H2 cut rule rendszer
7. H2 manufacturing plan builder
8. H3 scoring/ranking
9. H3 remnant domain
10. H3 selected run és comparison

Ez a platform legfontosabb építési tengelye.

---

# 8. Javasolt implementációs csomagolás

## Sprint/ütem csomagolás logika

### Csomag A — H0 schema + security
- H0-E1
- H0-E2
- H0-E6

### Csomag B — H0 geometry + run backbone
- H0-E3
- H0-E4
- H0-E5
- H0-E7

### Csomag C — H1 ingest + geometry pipeline
- H1-E1
- H1-E2

### Csomag D — H1 run orchestration + solver integration
- H1-E3
- H1-E4
- H1-E5

### Csomag E — H1 output + pilot
- H1-E6
- H1-E7

### Csomag F — H2 manufacturing core
- H2-E1
- H2-E2
- H2-E3

### Csomag G — H2 plan + export
- H2-E4
- H2-E5
- H2-E6

### Csomag H — H3 strategy + ranking
- H3-E1
- H3-E2
- H3-E3

### Csomag I — H3 remnant + business metrics
- H3-E4
- H3-E5

### Csomag J — H3 review + pilot
- H3-E6
- H3-E7

---

# 9. Globális Definition of Done

Egy phase/epic/task akkor tekinthető késznek, ha:

1. **Adatmodell oldalról lezárt**
   - szükséges táblák, enumok, indexek és constraint-ek létrejöttek

2. **Szolgáltatásréteg oldalról működik**
   - a kapcsolódó service vagy workflow ténylegesen végrehajtható

3. **Auditálható**
   - log, metadata, hash, state vagy report alapján visszafejthető

4. **Jogosultságilag helyes**
   - RLS / access control nem lyukas

5. **Dokumentált**
   - a kapcsolódó contract és működés le van írva

6. **Pilot vagy smoke-flow szinten validált**
   - legalább egy minimális végponti teszten átment

---

# 10. Záró összefoglalás

Ez a task tree a H0–H3 roadmapet végrehajtható szerkezetbe fordítja le.

A lényege:

- **H0**: építsük fel helyesen
- **H1**: tegyük működőképessé
- **H2**: emeljük gyártásközelivé
- **H3**: tegyük összehasonlíthatóvá és döntéstámogatóvá

Ha a fejlesztés ezt a fát követi, akkor a rendszer nem eseti fejlesztések laza láncolata lesz, hanem egy tudatosan rétegzett, ipari szintre bővíthető platform.
