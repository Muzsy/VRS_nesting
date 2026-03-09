# DXF Nesting Platform — Részletes roadmap

## Cél

Ez a dokumentum a DXF Nesting platform részletes, fázisolt roadmapját írja le.  
A cél az, hogy a platform ne egyszerűen a meglévő nesting engine köré épített webes felület legyen, hanem egy olyan moduláris, auditálható és hosszú távon bővíthető rendszer, amelyben:

- a geometry pipeline külön réteg,
- a nesting engine külön adapterelt számítómodul,
- a manufacturing és postprocess világ külön kezelt,
- a Supabase pedig központi domain- és állapottároló.

A roadmap a fejlesztést több, egymásra épülő szakaszra bontja, hogy világos legyen:

- mi az alapozás,
- mi az első működő platformszint,
- mi a gyártásközeli mélyítés,
- és mi az optimalizációs / döntéstámogató későbbi irány.

---

## Vezérelv

A fejlesztést nem a „mi fér bele gyorsan” logika szerint kell felépíteni, hanem a következő elv szerint:

1. először a **helyes szerkezet**
2. utána a **működő platformcsatorna**
3. utána a **gyártási intelligencia**
4. végül az **optimalizációs és döntéstámogató réteg**

Ez azért fontos, mert ha a platform korán rossz szerkezetet kap, később minden új funkció drágább, törékenyebb és nehezebben auditálható lesz.

---

## A roadmap fő fázisai

A teljes roadmap négy nagy horizont köré szervezhető:

- **H0** — Platformalap és domain/snapshot gerinc
- **H1** — Működő DXF → geometry → run → eredmény csatorna
- **H2** — Manufacturing és postprocess domain
- **H3** — Többfutásos optimalizálás, scoring, remnant, döntéstámogatás

---

# H0 — Platformalap és domain gerinc

## H0 célja

A H0 feladata a teljes platform legfontosabb szerkezeti döntéseinek lezárása.  
Ez még nem a látványos funkciók fázisa, hanem az a szakasz, ahol létrejön:

- a központi domainmodell,
- a Supabase alapséma,
- a geometry revision világ,
- a run snapshot és queue gerinc,
- az artifact/projection szétválasztás,
- és a jövőbeni manufacturing/postprocess irány helye.

## H0 fő kimenete

A H0 végére legyen világos és implementálható:

- mi tartozik a Platform Core-ba,
- mi a Geometry Pipeline feladata,
- hogyan kapcsolódik a Nesting Engine Adapter,
- mi a Viewer / Reporting réteg truth-forrása,
- és hogyan lesz később külön manufacturing és postprocess ág.

## H0 kötelező döntései

### 1. Snapshot-first modell
A worker csak snapshotból dolgozhat.

### 2. Definíció vs használat vs snapshot vs artifact
Ezeket nem szabad összemosni.

### 3. A belső geometry modell saját canonical JSON
Nem DXF, nem SVG.

### 4. Geometry derivative réteg
Minimum:
- `nesting_canonical`
- `manufacturing_canonical`
- `viewer_outline`

### 5. Placement priority helye
Projektigény-szinten, nem globális partdefinícióban.

### 6. Artifact és projection külön tárolása
A frontend ne solver raw outputra vagy csak SVG-re támaszkodjon.

## H0 várható deliverable-jei

- architektúra dokumentum
- domainmodell dokumentum
- Supabase alapséma
- storage és RLS alapstratégia
- geometry revision / part / sheet / run / artifact alapmodellek
- H0 smoke-flow szerkezeti szinten

---

# H1 — Működő platformcsatorna

## H1 célja

A H1 teszi a platformot ténylegesen működőképessé.  
Itt jön létre az első teljes lánc:

**DXF → geometry revision → part/sheet → run snapshot → solver run → projection + artifact**

## H1 fő fókusza

Ez a szakasz már nem csak tervezésről szól, hanem valódi működésről:

- DXF upload
- geometry parse
- normalizálás
- validation
- derivative képzés
- part és sheet workflow
- run create
- queue és worker
- solver adapter
- result normalization
- SVG/DXF/report artifactok

## H1 fő elvei

### 1. A geometry pipeline formalizált legyen
Ne legyen implicit vagy kézi.

### 2. A part és sheet revision-alapon működjön
Ne nyers fájlból induljon a run.

### 3. A derivative réteg ténylegesen használatban legyen
Legalább nesting és viewer célra.

### 4. A run eredményt platformnyelvre kell fordítani
Raw solver output nem elég.

## H1 fő kimenete

A H1 végére a platformnak képesnek kell lennie arra, hogy:

- fogadjon DXF-et,
- abból geometry revisiont képezzen,
- partként és sheetként felhasználható objektumokat hozzon létre,
- run snapshotot állítson elő,
- workerrel futtasson,
- projection táblákba és artifactokba írja vissza az eredményt,
- és ezt a frontend/backoffice vissza tudja nézni.

## H1 deliverable-ek

- upload flow
- geometry import pipeline
- part/sheet revision workflow
- run create + snapshot builder
- queue/worker lease
- engine adapter
- result normalizer
- viewer artifactok
- első end-to-end pilot

---

# H2 — Manufacturing és postprocess világ

## H2 célja

A H2-ben a platform túllép a puszta nesting eredményen, és belép a gyártásközeli működésbe.  
A fő kérdés már nem az, hogy hova került az alkatrész, hanem hogy ebből hogyan lesz:

- technológiailag értelmezett contour-szintű terv,
- manufacturing-ready köztes világ,
- és később gépfüggő export.

## H2 fő fókusza

- manufacturing profile-ok
- manufacturing profile versionök
- manufacturing_canonical derivative
- contour classification
- cut rule setek
- lead-in / lead-out logika
- manufacturing plan
- preview
- postprocessor adapter alap

## H2 fő elvei

### 1. Nesting geometry ≠ manufacturing geometry
A solver-barát és a gyártásbarát belső geometria külön világ.

### 2. A manufacturing profil ne a technology profile túlterhelt JSON-ja legyen
Külön domain kell neki.

### 3. A cut rule rendszer legyen szerkeszthető
Ne egyetlen nagy blob.

### 4. A machine-ready output ne legyen truth
Csak artifact.

## H2 fő kimenete

A H2 végére a platformnak képesnek kell lennie arra, hogy:

- a run placement eredményből manufacturing tervet képezzen,
- a contourokat osztályozza,
- outer/inner contour szabályokat alkalmazzon,
- lead-in / lead-out alapadatokat hozzon létre,
- preview artifactot generáljon,
- és egy machine-neutral export vagy első machine-specific adapter irányába is nyisson.

## H2 deliverable-ek

- manufacturing profile domain
- contour classification pipeline
- cut rule set és contour rule táblák
- manufacturing snapshot bővítés
- run_manufacturing_plans / contours
- manufacturing preview
- postprocessor profile/version aktiválás
- manufacturing pilot

---

# H3 — Optimalizálás, scoring, remnant, döntéstámogatás

## H3 célja

A H3 a platformot döntéstámogató és stratégiai optimalizáló irányba viszi el.  
Ekkor már nem egyetlen futást kezelünk egy projekthez, hanem:

- több candidate run-t,
- különböző stratégiákat,
- scoring és ranking logikát,
- remnant újrahasználást,
- review és selected run workflow-t.

## H3 fő fókusza

- run strategy profile-ok
- scoring profile-ok
- batch runok
- evaluation és ranking
- remnant domain
- stock vs remnant inputforrás
- business metrics
- review és selected run világ
- comparison projection

## H3 fő elvei

### 1. Egy run nem elég
Több megoldás közül kell választani.

### 2. A scoring legyen explicit és verziózott
Ne frontend-hardcode vagy ad-hoc SQL.

### 3. A remnant ne csak artifact legyen
Legyen újrahasználható domain entitás.

### 4. A review és approval különüljön el a technikai run állapottól
A sikeres futás nem automatikusan a kiválasztott futás.

## H3 fő kimenete

A H3 végére a platform képes legyen arra, hogy:

- ugyanarra a projektre több run-variánst generáljon,
- ezeket metrikák és scoring szerint rangsorolja,
- remnantokat képezzen és nyilvántartson,
- stock és remnant forrásokat külön kezeljen,
- review és selected run döntési folyamatot támogasson,
- és a felhasználónak összehasonlítható, üzletileg értelmezhető opciókat adjon.

## H3 deliverable-ek

- strategy/scoring domain
- run batch domain
- run evaluation és ranking
- remnant inventory alapok
- business metrics
- review workflow
- selected run flow
- H3 comparison pilot

---

# Fázisok közötti függőség

## H0 → H1
A H1 csak akkor lesz stabil, ha a H0-ban már tiszta:
- a revision világ,
- a snapshot gerinc,
- az artifact/projection különválasztás,
- a geometry derivative helye.

## H1 → H2
A H2 csak akkor lesz kezelhető, ha a H1-ben már van:
- működő geometry pipeline,
- approved derivative használat,
- run projection,
- result normalization.

## H2 → H3
A H3 csak akkor lesz értelmes, ha a H2 már létrehozta:
- a manufacturing plan világot,
- a gyártási metrikákat,
- a postprocess-kompatibilis köztes réteget.

---

# Prioritási értelmezés a roadmapon belül

## Első kötelező blokk
- teljes H0
- H1 magja

Ez adja az első, valóban működő platformot.

## Második blokk
- H2 magja

Ez adja az első, komolyan vehető gyártásközeli rendszert.

## Harmadik blokk
- H3 magja

Ez adja a döntéstámogató és optimalizációs többletértéket.

---

# Javasolt megvalósítási sorrend

## 1. blokk
- domain véglegesítés
- Supabase alapséma
- storage / RLS
- geometry revision gerinc
- part/sheet domain
- run/snapshot/queue gerinc

## 2. blokk
- DXF upload
- geometry parse és validation
- derivative generation
- part/sheet workflow
- run create
- worker + engine adapter
- result normalization
- artifact generation

## 3. blokk
- manufacturing profiles
- manufacturing derivative
- contour classification
- cut rule rendszer
- manufacturing plan
- preview
- postprocessor alap

## 4. blokk
- run strategy profiles
- scoring
- ranking
- remnant domain
- review/selected run workflow
- comparison layer

---

# Mit nem szabad összemosni a roadmap során

Ez a platform egész életciklusa alatt kritikus:

- source file vs canonical geometry
- geometry revision vs part revision
- project requirement vs run snapshot
- solver output vs platform projection
- nesting geometry vs manufacturing geometry
- manufacturing plan vs machine-ready export
- stock sheet vs remnant
- technical run success vs business selection

Ha ezek összecsúsznak, a rendszer gyorsan kaotikussá válik.

---

# Záró összefoglalás

A részletes roadmap lényege:

- **H0**: helyes platformalap
- **H1**: működő platformcsatorna
- **H2**: gyártásközeli intelligencia
- **H3**: optimalizációs és döntéstámogató réteg

A teljes fejlesztési irány célja, hogy a rendszerből ne egy egyszerű nesting webapp legyen, hanem egy olyan **moduláris, verziózott, Supabase-alapú gyártási workflow platform**, amelyhez a meglévő nesting engine erős, de jól elkülönített számítómodulként kapcsolódik.
