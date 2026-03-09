# DXF Nesting Platform — Priorizált Sprint / Backlog (P0 / P1 / P2)

## Dokumentum célja

Ez a dokumentum a DXF Nesting platform H0–H3 roadmapjének és az implementációs task tree-nek a **priorizált, végrehajtásközeli backlog-verziója**.

A cél az, hogy a teljes fejlesztési anyag ne csak fázisok és epicek szerint legyen érthető, hanem **üzemi prioritási sorrendben** is:

- mi az, ami **kötelezően kell** a platform életképességéhez,
- mi az, ami **erősen ajánlott következő lépés**,
- és mi az, ami **értékes, de már későbbi mélyítés**.

Ezért a backlog három fő prioritási szintre bomlik:

- **P0** — kritikus alap és működőképesség
- **P1** — gyártásközeli és operatív értéknövelő réteg
- **P2** — optimalizációs, összehasonlító és bővítő réteg

---

# 1. Prioritási rendszer értelmezése

## P0 — Kritikus
Ami nélkül a platform nem stabil, nem auditálható, vagy nem működik végig.  
Ha ezek hiányoznak, minden későbbi réteg kockázatos vagy értelmetlen.

## P1 — Erősen ajánlott
Ami nélkül a rendszer ugyan működhet, de még nem lesz igazán gyártásközeli, ipari használatra alkalmas vagy jól bővíthető.

## P2 — Stratégiai bővítés
Ami jelentős értéknövekedést ad, de nem előfeltétele az első komolyan használható rendszernek.

---

# 2. Összkép: mi tartozik hova

## P0 magja
A P0 lényegében a **H0 + H1 döntő többsége**.

Fókusz:
- helyes domainmodell
- stabil Supabase séma
- geometry revision és derivative alapok
- part/sheet workflow
- run snapshot
- worker + solver adapter
- result normalization
- artifact/projection
- alap RLS és auditálhatóság

Ez adja az első valóban működő platformot.

## P1 magja
A P1 lényegében a **H2 döntő többsége**, plusz néhány olyan H1/H0 stabilizáló elem, ami ipari használathoz kell.

Fókusz:
- manufacturing profile-ok
- manufacturing geometry
- contour classification
- cut rule rendszer
- manufacturing plan
- preview
- postprocess alap
- gyártási metrikák

Ez emeli a rendszert gyártásközeli állapotba.

## P2 magja
A P2 lényegében a **H3**, illetve a stratégiai optimalizáció és döntéstámogatás.

Fókusz:
- multi-run
- scoring
- ranking
- remnant
- stock/remnant input resolver
- business metrics
- review és selected run
- comparison layer

Ez emeli a rendszert döntéstámogató ipari platformmá.

---

# 3. P0 backlog — Kritikus alap és működőképesség

# P0-A — Architektúra és core domain

## P0-A1 — Modulhatárok véglegesítése
**Miért P0?**  
Ha ez nincs lezárva, minden későbbi implementáció szétfolyik.

**Cél**
- Platform Core
- Geometry Pipeline
- Nesting Engine Adapter
- Viewer/Reporting
- Manufacturing (helye)
- Postprocess (helye)
- Decision Layer (helye)

**DoD**
- dokumentált modulhatárok
- nincs solver-központú architektúra
- tiszta boundary-k

---

## P0-A2 — Domainmodell véglegesítése
**Miért P0?**  
A teljes adat- és workflow-rendszer erre épül.

**Cél**
- definíció vs használat vs snapshot vs artifact szétválasztása
- geometry / part / sheet / run / artifact domain rögzítése

**DoD**
- domain entitástérkép elkészült
- kulcs relációk véglegesítve
- H1 implementáció elkezdhető rajta

---

## P0-A3 — Snapshot-first run contract
**Miért P0?**  
Ez a reprodukálhatóság és az audit alapja.

**Cél**
- worker csak snapshotból dolgozzon
- solver input ne élő DB-ből képződjön ad-hoc módon

**DoD**
- run contract dokumentált
- snapshot tartalom minimuma definiált
- engine adapter input boundary rögzített

---

# P0-B — Supabase core schema

## P0-B1 — App schema, enumok, extensionök
**Cél**
- `app` schema
- enumok
- alap extensionök

**DoD**
- minden H0/H1 core enum létrehozva
- migrációs alapcsomag stabil

---

## P0-B2 — Profiles / projects / project_settings
**Cél**
- projektvilág alapja

**DoD**
- projekt létrehozható
- tulajdonos és alapbeállítás tárolható

---

## P0-B3 — Machine / material / kerf / technology profile domain
**Cél**
- alap technológiai oldal

**DoD**
- technology profile version tárolható
- project technology selection működik
- spacing/margin/kerf paraméterek kezelhetők

---

# P0-C — File, geometry és revision gerinc

## P0-C1 — File object és storage metadata
**Cél**
- feltöltött fájlok metaadat-nyilvántartása

**DoD**
- file_objects működik
- bucket/path naming van
- storage kapcsolat strukturált

---

## P0-C2 — Geometry revision modell
**Cél**
- source file → canonical geometry revision kapcsolat

**DoD**
- geometry revision létrehozható
- geometry revision file-ra hivatkozik
- canonical format version tárolt

---

## P0-C3 — Validation és review alapréteg
**Cél**
- geometry auditálhatóság

**DoD**
- validation report menthető
- review action menthető
- geometry state követhető

---

## P0-C4 — Geometry derivatives alap
**Cél**
- derivative réteg bevezetése

**Minimum P0 derivative-ek**
- `nesting_canonical`
- `viewer_outline`

**DoD**
- geometry_derivatives működik
- derivative part revisionből hivatkozható

---

# P0-D — Part, sheet és projekt inputok

## P0-D1 — Part definition + part revision
**Cél**
- geometriából üzletileg használható alkatrész legyen

**DoD**
- part revision létrehozható
- approved derivative kapcsolható

---

## P0-D2 — Sheet definition + sheet revision
**Cél**
- táblák revision-alapon kezelhetők legyenek

**DoD**
- sheet revision tárolható
- projektbe bevonható

---

## P0-D3 — Project part requirements
**Cél**
- required_qty és placement priority/policy kezelése

**DoD**
- projektben part requirement létrehozható
- placement_priority és placement_policy működik

---

## P0-D4 — Project sheet inputs
**Cél**
- projektbe választott sheet inputok kezelése

**DoD**
- mennyiség és prioritás tárolható
- run input alapja megvan

---

# P0-E — Run gerinc és solver útvonal

## P0-E1 — Nesting run + snapshot modellek
**Cél**
- futtatható run objektumok

**DoD**
- run létrehozható
- snapshot hash tárolható
- snapshot schema version előkészített

---

## P0-E2 — Queue és lease modell
**Cél**
- pending → leased → done/error útvonal

**DoD**
- worker fel tud venni runokat
- duplafutás megelőzhető
- retry count kezelhető

---

## P0-E3 — Run logok
**Cél**
- diagnosztika és visszakövethetőség

**DoD**
- run log bejegyzések menthetők
- komponensszintű üzenetek tárolhatók

---

## P0-E4 — Run create + snapshot builder service
**Cél**
- projektből teljes futási snapshot képzése

**DoD**
- aktív requirementek és sheet inputok bekerülnek
- technology selection bekerül
- solver számára elegendő input képződik

---

## P0-E5 — Engine adapter input mapping
**Cél**
- snapshot → solver input

**DoD**
- stabil input JSON generálható
- input determinisztikusan előállítható

---

## P0-E6 — Solver process runner
**Cél**
- a worker ténylegesen futtassa a solver folyamatot

**DoD**
- run állapotok helyesen frissülnek
- success/fail kezelhető

---

## P0-E7 — Raw solver output artifact
**Cél**
- raw output megőrzése

**DoD**
- raw output visszakereshető
- hibás futás esetén is van diagnosztikai nyom

---

# P0-F — Result normalization és viewer truth

## P0-F1 — Result normalizer
**Cél**
- solver output → run_layout_sheets / placements / unplaced / metrics

**DoD**
- projection táblák feltöltődnek
- run_metrics kitöltődik
- frontend nem raw solver outputot olvas

---

## P0-F2 — Sheet SVG artifact generator
**Cél**
- viewer alap renderelés

**DoD**
- sheet szintű SVG artifact készül
- layout visszanézhető

---

## P0-F3 — Sheet DXF artifact generator
**Cél**
- alap export artifact

**DoD**
- runhoz DXF artifact rendelhető
- export visszakereshető

---

## P0-F4 — Artifact metadata és integritás
**Cél**
- artifact hash / byte_size / source component mezők

**DoD**
- artifact auditálható
- letöltési/integritási információ tárolt

---

# P0-G — Security, storage, stabilizálás

## P0-G1 — Storage bucket stratégia véglegesítése
**DoD**
- source-files / geometry-artifacts / run-artifacts policy lezárt

## P0-G2 — RLS policyk
**DoD**
- user csak saját projekt adatait látja
- storage hozzáférés projektalapú

## P0-G3 — H1 end-to-end pilot
**DoD**
- DXF feltöltés → geometry → part/sheet → run → projection → artifact végigfut

## P0-G4 — P0 audit és hibajavítás
**DoD**
- a rendszer stabil, auditálható és továbbépíthető P1-re

---

# 4. P1 backlog — Gyártásközeli réteg

# P1-A — Manufacturing profile domain

## P1-A1 — Manufacturing profiles és versions
**Miért P1?**  
A rendszer P0-ban működik, de még nem gyártásközeli.

**Cél**
- manufacturing profile CRUD
- version kezelés

**DoD**
- manufacturing profile version projektből választható

---

## P1-A2 — Project manufacturing selection
**Cél**
- projekt manufacturing kiválasztás

**DoD**
- manufacturing selection tárolható
- run snapshotba emelhető

---

# P1-B — Manufacturing geometry

## P1-B1 — manufacturing_canonical derivative generation
**Cél**
- külön gyártási derivative

**DoD**
- part revisionhöz manufacturing derivative kapcsolható
- manufacturing pipeline nem nesting derivative-re épül vakon

---

## P1-B2 — Contour classification
**Cél**
- outer / inner / feature class meghatározása

**DoD**
- geometry_contour_classes töltődik
- classification auditálható

---

# P1-C — Cut rule rendszer

## P1-C1 — Cut rule set domain
**Cél**
- rule setek létrehozása

**DoD**
- rule setek verziózhatók
- machine/material/thickness meta kezelhető

---

## P1-C2 — Cut contour rule domain
**Cél**
- contour-szintű szabályok

**DoD**
- outer/inner szabályok tárolhatók
- lead_in / lead_out mezők kezelhetők

---

## P1-C3 — Rule matching engine
**Cél**
- contour class → cut rule hozzárendelés

**DoD**
- contourokra automatikusan szabály rendelhető
- hozzárendelés visszakereshető

---

# P1-D — Manufacturing plan és metrics

## P1-D1 — Manufacturing snapshot bővítés
**Cél**
- manufacturing selection és rule setek snapshotolása

**DoD**
- includes_manufacturing / includes_postprocess jelölhető
- manufacturing input reprodukálható

---

## P1-D2 — Manufacturing plan builder
**Cél**
- run projection → manufacturing plan

**DoD**
- run_manufacturing_plans és run_manufacturing_contours feltölthető
- contour-level technológiai terv létrejön

---

## P1-D3 — Manufacturing metrics
**Cél**
- pierce count, cut length, alap időbecslés

**DoD**
- run_manufacturing_metrics elérhető
- gyártási összehasonlítás minimálisan támogatott

---

# P1-E — Preview és postprocess

## P1-E1 — Manufacturing preview SVG
**Cél**
- gyártási terv vizuális ellenőrzése

**DoD**
- contour-, entry-, lead-meta megjeleníthető

---

## P1-E2 — Postprocessor profile/version aktiválás
**Cél**
- postprocessor domain gyakorlati használata

**DoD**
- manufacturing profile postprocessorra mutathat
- postprocessor selection működik

---

## P1-E3 — Machine-neutral export
**Cél**
- manufacturing planből generikus export artifact

**DoD**
- manufacturing_plan_json / manufacturing_preview / export artifact létrejöhet

---

## P1-E4 — Első machine-specific adapter (opcionális, de erősen ajánlott)
**Cél**
- egy konkrét exportirány kipróbálása

**DoD**
- adapter interfész validált
- machine-ready artifact demonstrálható

---

# P1-F — P1 lezárás

## P1-F1 — End-to-end manufacturing pilot
**DoD**
- nesting runból manufacturing plan és preview/export készül

## P1-F2 — P1 audit és stabilizálás
**DoD**
- manufacturing réteg elég stabil P2-höz

---

# 5. P2 backlog — Optimalizálás, remnant, döntéstámogatás

# P2-A — Strategy és scoring domain

## P2-A1 — Run strategy profiles
**Cél**
- külön futtatási stratégiák

**DoD**
- strategy profile projektből választható

---

## P2-A2 — Scoring profiles
**Cél**
- explicit scoring és tie-breaker rendszer

**DoD**
- scoring profile verziózható és kiválasztható

---

## P2-A3 — Project strategy/scoring selection
**Cél**
- project-level selection

**DoD**
- run strategy és scoring selection aktív projekthez menthető

---

# P2-B — Batch és ranking

## P2-B1 — Run batch modell
**Cél**
- több run egy batchben

**DoD**
- batch létrehozható
- runok hozzárendelhetők

---

## P2-B2 — Batch orchestrator
**Cél**
- több candidate run indítása

**DoD**
- strategy variánsokkal több run generálható

---

## P2-B3 — Run evaluation engine
**Cél**
- metrikákból score

**DoD**
- run_evaluations feltölthető
- komponensbontás tárolt

---

## P2-B4 — Ranking engine
**Cél**
- batch candidate-ek sorrendje

**DoD**
- run_ranking_results működik
- ranking reason tárolt

---

## P2-B5 — Best-by-objective projections
**Cél**
- material-best / time-best / priority-best nézetek

**DoD**
- objective-specifikus toplisták lekérdezhetők

---

# P2-C — Remnant és inventory

## P2-C1 — Remnant extractor
**Cél**
- runból maradékanyag entitás képzése

**DoD**
- remnant_definitions / remnant_revisions létrejönnek

---

## P2-C2 — Remnant stock management
**Cél**
- remnant készletszerű állapotkezelése

**DoD**
- remnant stock itemek létrehozhatók
- reserve/active kezelés van

---

## P2-C3 — Stock sheet domain
**Cél**
- stock külön világa

**DoD**
- stock_sheet_items működik
- stock és remnant külön entitás

---

## P2-C4 — Inventory-aware input resolver
**Cél**
- stock/remnant/ad hoc inputforrás választása

**DoD**
- run_input_sheet_sources kitöltődik
- forrás auditálható

---

# P2-D — Business metrics és review

## P2-D1 — Business metrics calculator
**Cél**
- priority fulfilment, anyagköltség, remnant érték, total cost

**DoD**
- run_business_metrics működik
- üzleti összehasonlítás lehetséges

---

## P2-D2 — Run review workflow
**Cél**
- review stage / status világ

**DoD**
- run reviewk nyomon követhetők

---

## P2-D3 — Selected run workflow
**Cél**
- preferred / approved run kijelölése

**DoD**
- project_selected_runs működik

---

## P2-D4 — Comparison projection builder
**Cél**
- frontend-barát batch summary és összehasonlító nézetek

**DoD**
- batch összesítések könnyen lekérdezhetők

---

# P2-E — P2 lezárás

## P2-E1 — Multi-run comparison pilot
**DoD**
- több candidate run összevethető és rangsorolható

## P2-E2 — Remnant reuse pilot
**DoD**
- remnant következő runban inputként használható

## P2-E3 — P2 audit és stabilizálás
**DoD**
- H0–H3 fő fejlesztési ív lezárt

---

# 6. Ajánlott sprint/ütemezési csomagok

## Sprint 1–2
- P0-A
- P0-B
- P0-C részben

## Sprint 3–4
- P0-C lezárás
- P0-D
- P0-E részben

## Sprint 5–6
- P0-E lezárás
- P0-F
- P0-G
- első end-to-end pilot

## Sprint 7–8
- P1-A
- P1-B
- P1-C

## Sprint 9–10
- P1-D
- P1-E
- P1-F

## Sprint 11–12
- P2-A
- P2-B

## Sprint 13–14
- P2-C
- P2-D
- P2-E

Ez csak logikai csomagolás; a valós sprintméret a csapatkapacitástól függ.

---

# 7. Mi ne csússzon ki P0-ból

Ez fontos, mert tipikus hiba lenne későbbre tolni:

- snapshot-first run modell
- artifact vs projection szétválasztás
- geometry revision réteg
- derivative alapok
- result normalizer
- RLS és storage stratégia
- placement priority projektigény-szintű kezelése

Ha ezek kicsúsznak P0-ból, a rendszer később drágán javítható.

---

# 8. Mi halasztható nyugodtan P2-re

Szintén fontos, hogy ne terheljük túl a korai fázisokat:

- batch scoring/ranking
- remnant inventory teljes üzleti kezelése
- selected run workflow kifinomítása
- comparison dashboard jellegű nézetek
- több stratégia közti automatikus választás
- mély business metrics

Ezek értékesek, de nem P0/P1 blokkerek.

---

# 9. Egyszerű döntési szabály a backlog használatához

Ha egy feladatnál kérdés, hogy hova tartozik, ezt a három kérdést kell feltenni:

1. **Ha ez nincs kész, a platform végig tud működni?**
   - ha nem: valószínűleg P0

2. **Ha ez nincs kész, a platform ipari/gyártási szempontból komolyan használható?**
   - ha nem: valószínűleg P1

3. **Ha ez nincs kész, a platform tud működni, csak kevésbé okosan és kevésbé üzletileg optimalizáltan?**
   - ha igen: valószínűleg P2

---

# 10. Záró összefoglalás

A backlog priorizált értelmezése egy mondatban:

- **P0**: építsünk egy helyes és végig működő platformot
- **P1**: tegyük gyártásközelivé
- **P2**: tegyük összehasonlíthatóvá, optimalizálhatóvá és döntéstámogatóvá

Ez a bontás segít abban, hogy a projekt ne egyszerre próbáljon meg mindent megoldani, hanem először a valóban kötelező gerincet, utána a gyártási használhatóságot, végül az optimalizációs és üzleti értéknövelő rétegeket zárja le.
