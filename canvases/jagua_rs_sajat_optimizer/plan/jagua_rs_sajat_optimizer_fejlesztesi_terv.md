# Fejlesztési terv: átállás `jagua-rs` + saját optimizer architektúrára

**Projekt:** DXF Nesting / VRS_nesting  
**Dátum:** 2026-05-20  
**Cél:** az eddigi exact polygon NFP-alapú solver-vonal stratégiai kiváltása egy `jagua-rs` ütközéskezelő / geometriai backend + saját, ipari célú optimizer architektúrával.

---

## 0. Vezetői összefoglaló

A tervezett irány érthető és logikus:

1. **Első lépés:** `jagua-rs` backend + saját optimizer, kezdetben egyszerű **téglalap sheet / multi-sheet nestingre**, hole-ok kizárásával.
2. **Második lépés:** ugyanez az optimizer kiterjesztve **alakos / remnant sheetekre**, továbbra is hole-ok nélkül.
3. **Harmadik lépés:** **hole / part-in-hole kezelés cavity-prepack rétegen keresztül**, az első két fázisban stabilizált solverre alapozva.
4. **Végig kötelező:** saját exact final validation, DXF-szemantika megőrzése, darablista-helyesség, reprodukálható mérések.

A fő döntés nem az, hogy „Sparrow-t forkolunk és kész”, hanem az, hogy:

> A Sparrow-ból a keresési filozófiát, repair-search / penalty / separation-alapú optimalizáló szemléletet és a hasznos moduláris mintákat vesszük át, de a projekt saját optimizer-core-t kap, amely a VRS_nesting ipari fixed-sheet, multi-sheet, remnant és cavity-prepack céljaihoz van igazítva.

---

## 1. Kiinduló stratégiai döntés

### 1.1 Miért kell váltani?

A jelenlegi exact polygon NFP-alapú irány a projektben erős geometriai pontosságot ad, de a nagyobb ipari csomagoknál kritikus korlátba fut:

- sok alkatrész esetén a pair-NFP számítás drága;
- sok rotációval a számítási tér tovább robban;
- konkáv, sokcsúcsú geometriáknál a NFP union / pair computation túl nehéz;
- a greedy-alapú elhelyezés nem elég a jó interlocking layouthoz;
- ipari összevetésben nem csak „valid elhelyezés” kell, hanem magas kihasználtság gyakorlati futási idő alatt.

Ezért a projektnek olyan architektúrára kell váltania, amelyben:

- az ütközésvizsgálat gyors;
- a keresés sok próbát tud futtatni;
- a solver nem minden döntésnél drága exact NFP-et számol;
- az exact geometriai ellenőrzés a végső validációs rétegben marad;
- a hole-szemantika nem vész el, de nem terheljük vele rögtön a solver első verzióját.

### 1.2 Célarchitektúra egy mondatban

> A `jagua-rs` legyen a gyors collision / geometry engine, erre épüljön egy saját, Sparrow-elvű optimizer, amely először rectangular multi-sheet, majd irregular sheet/remnant, végül cavity-prepack + hole workflow felé bővül, a VRS_nesting exact final validation rétegével lezárva.

---

## 2. Scope és nem-scope

### 2.1 Első nagy scope

A terv első nagy scope-ja nem egy teljes ipari nesting rendszer azonnali megírása, hanem egy mérhető, fokozatos átállási út:

- `jagua-rs` integrációs spike;
- belső adatformátum normalizálása;
- téglalap sheet multi-bin nesting;
- saját optimizer-váz;
- egyszerű rotációs kezelési stratégia;
- determinisztikus benchmark fixture-ök;
- exportálható layout;
- exact final validation;
- majd fokozatos bővítés irregular sheet és cavity-prepack irányba.

### 2.2 Tudatosan kizárt az első fázisból

Az első fázisban tilos túl sok problémát egyszerre beemelni:

- nincs hole / inner contour nesting;
- nincs part-in-hole;
- nincs alakos remnant;
- nincs teljesen szabad, kontinuus rotációs optimalizáció;
- nincs gyártási sorrend / toolpath optimalizáció;
- nincs lead-in / lead-out pack integráció;
- nincs nesting utáni CAM optimalizálás;
- nincs automatikus production-grade DXF repair minden esetre.

Ezek későbbi rétegek.

---

## 3. Alapelvek

### 3.1 `jagua-rs` szerepe

A `jagua-rs` a tervben nem üzleti workflow-motor, hanem geometriai / collision backend:

- item és bin reprezentáció;
- gyors collision detection;
- gyors feasibility check;
- separation / overlap információk, ha elérhetők;
- optimizer által mozgatott állapot validálása;
- később irregular container támogatás vizsgálata.

A projekt saját oldalán marad:

- DXF import / preflight / normalizálás;
- nesting input contract;
- material / thickness / gap / margin profilok;
- saját optimizer;
- multi-sheet döntési logika;
- cavity-prepack;
- exact final validation;
- report / layout export;
- UI / API integráció.

### 3.2 Sparrow szerepe

Az eredeti Sparrow nem egy az egyben átemelendő termék-core, hanem referencia:

- hogyan szervezi a search state-et;
- hogyan használja a collision backendet;
- milyen move-okat és repair lépéseket alkalmaz;
- hogyan bünteti az overlapet / rossz pozíciókat;
- hogyan közelít a strip/bin packing problémához;
- hogyan lehet egyszerű állapotból iteratívan javuló layoutot építeni.

A saját optimizernek a projekt céljaihoz kell igazodnia:

- fixed rectangular sheet;
- több sheet;
- később irregular remnant;
- később cavity-prepack;
- exact DXF-geometria visszavetítés;
- benchmarkolható, reprodukálható futások;
- ipari spacing/margin szabályok.

---

## 4. Célállapot architektúra

### 4.1 Fő komponensek

A javasolt célarchitektúra fő moduljai:

```text
DXF / project input
      |
      v
Preflight + geometry normalization
      |
      v
NestingInputContract
      |
      +--> ItemGeometryStore
      +--> Quantity / material / thickness profile
      +--> SheetProvider
      +--> SolverProfile
      |
      v
JaguaAdapter
      |
      v
OptimizerCore
      |
      +--> Initializer
      +--> MoveGenerator
      +--> CollisionEvaluator
      +--> RepairEngine
      +--> ScoreModel
      +--> MultiSheetManager
      +--> StoppingPolicy
      |
      v
CandidateLayout
      |
      v
ExactFinalValidator
      |
      v
ExpandedLayout / Report / UI / Export
```

### 4.2 Modulok rövid szerepe

#### `NestingInputContract`

Egységes solver input:

- part id;
- quantity;
- outer polygon;
- optional inner polygons, de Phase 1-ben tiltva;
- allowed rotations;
- gap;
- sheet margin;
- material/thickness;
- sheet list;
- deterministic seed;
- time limit;
- quality profile.

#### `ItemGeometryStore`

Feladata:

- normalizált polygonok tárolása;
- bounding box;
- area;
- vertex count;
- simplified / proxy geometry opcionális tárolása;
- exact geometry külön megőrzése;
- rotált geometriák cache-elése.

#### `SheetProvider`

Fázisonként más implementáció:

- Phase 1: rectangular sheet provider;
- Phase 2: irregular/remnant sheet provider;
- Phase 3: cavity-eredetű virtual placement regions / macro-part kapcsolat.

#### `JaguaAdapter`

Vékony adapterréteg:

- VRS geometria → jagua input;
- jagua state létrehozás;
- item/bin hozzáadás;
- pozíció/frissítés;
- collision lekérdezés;
- feasibility check;
- score-hoz szükséges overlap/separation információ;
- eredmény visszaalakítás VRS layout formátumra.

#### `OptimizerCore`

A saját solver lelke:

- kezdeti elhelyezések generálása;
- move-ok próbálgatása;
- overlap repair;
- sheeten belüli tömörítés;
- sheetek közötti áthelyezés;
- sheet elimináció;
- layout score maximalizálás;
- time budget és iteráció budget kezelése.

#### `ExactFinalValidator`

Nem opcionális.

Feladata:

- exact outer polygon non-overlap;
- sheet boundary check;
- spacing check;
- margin check;
- item quantity check;
- transform correctness;
- később hole-szemantika / cavity-prepack expansion ellenőrzése.

---

## 5. Fejlesztési fázisok áttekintése

```text
Phase 0 — repo audit + integrációs előkészítés
Phase 1 — rectangular multi-sheet, hole nélkül
Phase 2 — irregular/remnant sheet, hole nélkül
Phase 3 — cavity-prepack + hole kezelés
Phase 4 — optimizer minőségjavítás és ipari benchmark
Phase 5 — production hardening, API/UI/export integráció
```

A Phase 1–3 a stratégiai mag. A Phase 4–5 akkor kezdhető, ha a Phase 1–3 validált, mérhető és stabil.

---

# Phase 0 — Integrációs előkészítés

## 6. Phase 0 célja

A Phase 0 célja nem még az optimizer megírása, hanem a kockázatok gyors feltárása:

- `jagua-rs` valós API-k, adatformátumok és korlátok megértése;
- build / dependency / licence / FFI kérdések tisztázása;
- repo integrációs pontok azonosítása;
- minimális proof-of-contact futás;
- benchmark fixture készítése.

## 7. Phase 0 konkrét feladatok

### 7.1 Kódszintű audit

Meg kell nézni:

- hogyan modellezi a `jagua-rs` az itemet;
- hogyan modellezi a bin/container fogalmát;
- van-e natív BPP/multi-bin réteg;
- mit tud irregular containerre;
- van-e separation vector / penetration / overlap metric;
- hogyan kezeli a rotációt;
- hogyan kezeli az item hole-t;
- hogyan kezeli a container hole-t / inferior zone-t;
- mi az elvárt input topológia;
- mi a stabilitása sok itemnél;
- mennyire thread-safe / parallelizálható;
- hogyan lehet Rust workspace-be integrálni.

### 7.2 Sparrow audit

Az eredeti Sparrow-ból azonosítani kell:

- search loop;
- placement state;
- move generator;
- repair lépés;
- penalty / score modell;
- bin/strip specifikus kód;
- jagua adapter használata;
- export / vizualizáció;
- rectangular feltételezések;
- mit kell elhagyni;
- mit érdemes újraimplementálni.

### 7.3 Integrációs spike

Minimális program:

- 1 rectangular sheet;
- 3–5 egyszerű polygon;
- gap/margin kezelése proxy szinten;
- item transform;
- collision check;
- valid / invalid pozíció felismerése;
- layout visszaalakítása saját struktúrába;
- exact validatorral ellenőrzés.

### 7.4 Elfogadási kritérium

Phase 0 akkor kész, ha:

- a `jagua-rs` buildelhető a fejlesztői környezetben;
- van minimális adapter proof-of-contact;
- egy egyszerű layout collision checkje működik;
- ismertté vált, hogy a Phase 1-hez szükséges API-k közvetlenül elérhetők-e;
- a fő kockázatokról külön rövid audit report készült.

---

# Phase 1 — Rectangular multi-sheet, hole nélkül

## 8. Phase 1 célja

Az első valódi solver-fázis célja:

> A projekt tudjon hole nélküli alkatrészeket több darab 3000×1500 vagy hasonló téglalap sheetre rakni `jagua-rs` collision backenddel és saját optimizerrel.

Ez még nem végső minőségű ipari solver, hanem az új architektúra működőképességi bizonyítása.

## 9. Phase 1 input korlátozásai

Engedélyezett:

- outer polygon;
- konkáv polygon;
- több quantity;
- több sheet;
- fixed rectangular sheet;
- margin;
- inter-part gap;
- diszkrét allowed rotations;
- time limit;
- deterministic seed.

Tiltott:

- item holes;
- container holes;
- irregular sheet;
- remnant shape;
- cavity-prepack;
- nesting inner contours into other parts;
- exact toolpath output.

## 10. Phase 1 fő komponensei

### 10.1 Rectangular bin model

A rectangular sheet modell tartalmazza:

- width;
- height;
- usable area;
- marginból képzett belső használható régió;
- sheet id;
- material / thickness;
- max quantity vagy available count.

### 10.2 Item proxy geometry

Minden itemhez szükséges:

- exact outer polygon;
- solver proxy polygon;
- area;
- bbox;
- allowed rotations;
- quantity expansion;
- stable item instance id.

Fontos szabály:

> A Phase 1-ben a solver csak outer polygonokat lát. A hole-os alkatrészeket vagy ki kell szűrni, vagy explicit unsupported státusszal visszaadni. Nem szabad csendben eldobni a hole-okat.

### 10.3 Jagua adapter

A Phase 1 adapter minimum API-ja:

```rust
trait CollisionBackend {
    fn create_problem(&mut self, bin: BinProxy, items: Vec<ItemProxy>) -> BackendProblemId;
    fn place_item(&mut self, item_id: ItemInstanceId, transform: Transform2D) -> CollisionResult;
    fn move_item(&mut self, item_id: ItemInstanceId, transform: Transform2D) -> CollisionResult;
    fn remove_item(&mut self, item_id: ItemInstanceId);
    fn check_item(&self, item_id: ItemInstanceId, transform: Transform2D) -> CollisionResult;
    fn check_layout(&self) -> LayoutCollisionSummary;
}
```

A valós API ettől eltérhet, de saját oldalon ilyen absztrakció kell, hogy a későbbi backend-csere vagy fallback ne verje szét az optimizer kódot.

### 10.4 Initializer

Az első initializer lehet egyszerű, de determinisztikus:

- area szerint csökkenő sorrend;
- bbox szerint rendezés másodlagosan;
- large-first elhelyezés;
- több seed / perturbáció;
- grid vagy candidate-point alapú indulás;
- sheetenként próbálkozás.

Nem cél rögtön tökéletes layout, de kell stabil induló layout.

### 10.5 Move generator

Kezdeti move típusok:

- item translation;
- item rotation választás allowed rotations listából;
- item swap;
- item remove + reinsert;
- item move to other sheet;
- local compaction move;
- random jitter;
- boundary-near move;
- neighbor-near move.

### 10.6 Repair engine

A repair engine feladata:

- overlap csökkentése;
- sheet boundary violation javítása;
- rossz item újrapozicionálása;
- collision-heavy item priorizálása;
- sikertelen repair esetén item parkolása / unplaced listára tétele.

### 10.7 Score model

A Phase 1 score ne csak area utilization legyen.

Javasolt score komponensek:

```text
score =
  + placed_area_weight * placed_area
  - sheet_count_weight * used_sheet_count
  - overlap_penalty_weight * overlap_measure
  - boundary_penalty_weight * outside_measure
  - fragmentation_penalty_weight * wasted_space_proxy
  - unplaced_penalty_weight * unplaced_area
  + compactness_weight * compactness
```

Első verzióban a legfontosabb:

- minden collision / boundary violation nagyon nagy büntetés;
- unplaced area nagy büntetés;
- kevesebb sheet használata erős pozitív cél;
- sheeten belüli compactness csak másodlagos.

### 10.8 MultiSheetManager

A multi-sheet logika ne csak „ha nem fér, nyit új sheet” legyen.

Minimális stratégia:

1. initial layout több sheetre;
2. sheetenként compaction;
3. leggyengébb sheet azonosítása;
4. azon lévő itemek megpróbálása áthelyezni más sheetekre;
5. ha minden item átment, sheet eliminálása;
6. ha nem, rollback;
7. iteráció.

Ez ipari szempontból kulcsfontosságú, mert a cél sokszor nem csak kihasználtság, hanem sheet count minimalizálás.

## 11. Phase 1 mérési fixture-ök

Kell legalább 4 szint:

### 11.1 Smoke fixture

- 5–10 egyszerű polygon;
- 1 sheet;
- ismert valid eredmény;
- gyors unit/integration teszt.

### 11.2 Small realistic fixture

- 30–50 alkatrész;
- konkáv polygonok;
- 1–2 sheet;
- hole nélkül;
- 10 mm gap, 5/10 mm margin.

### 11.3 Medium fixture

- 100–300 alkatrész;
- 2–5 sheet;
- több rotáció;
- time limit 60–180 sec.

### 11.4 LV6/LV8-derived no-hole fixture

- valós DXF-ből kivett outer-only részhalmaz;
- holes explicit kizárva;
- cél: architektúra sebesség és stabilitás mérése.

## 12. Phase 1 elfogadási kritériumok

Phase 1 akkor tekinthető késznek, ha:

- hole nélküli fixture-ökön stabilan fut;
- nincs invalid final layout;
- exact validator minden elfogadott layoutot PASS-ra értékel;
- több sheetet kezel;
- képes sheet count csökkentési próbákra;
- determinisztikus seed mellett reprodukálható;
- JSON/MD reportot ír;
- benchmark scriptből futtatható;
- legalább egy realistic fixture-ön jobb, mint a primitív BLF fallback;
- nincs silent geometry loss.

---

# Phase 2 — Alakos / remnant sheet, hole nélkül

## 13. Phase 2 célja

A második lépésben a rectangular container helyett alakos táblát/remnantot kell kezelni:

> A solver tudjon outer-only alkatrészeket nem téglalap alakú sheet / remnant containerbe optimalizálni, hole-ok nélkül.

Ez nagyon fontos ipari funkció, mert a valós gyártásban a maradéktáblák értékesek.

## 14. Phase 2 input

Engedélyezett:

- irregular outer sheet polygon;
- outer-only items;
- margin;
- gap;
- több remnant / több irregular bin;
- több rectangular és irregular sheet vegyesen;
- diszkrét rotations;
- exact final validation.

Tiltott:

- item holes;
- container holes;
- part-in-hole;
- nested cavity usage.

## 15. Alakos tábla modell

A sheet modell bővül:

```text
SheetGeometry:
  id
  type: rectangular | irregular
  outer_polygon
  forbidden_regions: []
  usable_polygon_after_margin
  area
  bbox
  priority / cost
  metadata
```

Phase 2-ben a `forbidden_regions` még üres, mert hole-ok kizárva vannak.

## 16. Margin kezelés alakos sheetnél

A margin már nem egyszerű width/height shrink.

Szükséges:

- sheet polygon inward offset;
- ha offset szétesik több régióra, kezelni kell;
- túl kicsi régiókat el kell dobni;
- exact validatorban boundary + margin ellenőrzés;
- reportban margin utáni usable area.

Kockázat:

- robust polygon offset nehéz;
- nem szabad pontatlan offset miatt valid layoutot invalidnak, vagy invalid layoutot validnak minősíteni.

Ajánlott megközelítés:

- solverhez proxy usable polygon;
- exact validatorhoz konzervatív ellenőrzés;
- ha kétséges, inkább reject.

## 17. Jagua irregular bin spike

Phase 2 elején külön spike kell:

- natívan támogatja-e a `jagua-rs` irregular container boundary-t;
- hogyan kell beadni;
- boundary violation mérhető-e;
- milyen performance várható;
- van-e inferior zone / forbidden zone támogatás;
- mi kell hozzá az adapterben.

Ha a natív támogatás korlátozott, két opció:

1. `jagua-rs` irregular bin API használata, ha alkalmas;
2. saját candidate generation + jagua collision check item-itemre, boundary check saját exact/proxy geometriával.

## 18. Candidate generation irregular sheetre

Téglalap sheetnél elég lehet grid/bbox/corner/neighbor pont.

Irregular sheetnél kell:

- boundary-aware candidate point;
- polygon interior sample;
- edge-near candidate;
- vertex-near candidate;
- existing item neighbor candidate;
- largest empty region proxy;
- random interior points;
- repair move, amely visszahúzza az itemet usable polygonba.

## 19. Score model Phase 2 kiegészítés

Új score komponensek:

```text
- outside_usable_region_penalty
- remnant_priority_weight
- irregular_boundary_waste_penalty
- expensive_sheet_penalty
- preferred_sheet_bonus
```

Ha több remnant és normál sheet is van, akkor a sheeteknek költsége lehet:

- remnant használata előnyösebb;
- új teljes tábla nyitása drágább;
- túl fragmentált remnant kihasználása kisebb bónuszt kap.

## 20. Phase 2 elfogadási kritériumok

Phase 2 akkor kész, ha:

- legalább egy egyszerű L-alakú / konkáv remnant fixture működik;
- nincs sheet boundary violation;
- exact validator PASS;
- rectangular sheet továbbra is regresszió nélkül működik;
- vegyes rectangular + irregular bin lista kezelhető;
- több remnant esetén képes sheet választásra;
- margin kezelés konzervatív és dokumentált;
- reportban látszik usable area, placed area, utilization.

---

# Phase 3 — Hole kezelés cavity-prepack-kel

## 21. Phase 3 célja

A harmadik lépés nem az, hogy a solver natívan kezeljen minden item hole-t és part-in-hole interakciót.

A cél:

> A hole-szemantikát cavity-prepack réteg kezelje: a nagyobb alkatrészek belső kivágásaiból opcionálisan használható cavity régiókat képezünk, azokba előre elhelyezünk kisebb alkatrészeket, majd a solver a létrejött macro-partot / virtual parent partot kezeli.

Ez illeszkedik a korábbi projektstratégiához.

## 22. Miért cavity-prepack?

Mert a hole-ok közvetlen solverbe engedése több problémát okoz:

- az item nem egyszerű outer polygon;
- part-in-hole collision szemantika bonyolult;
- ha egy alkatrész hole-jába másik alkatrész kerül, annak koordinátája a parenthez kötött;
- a végső gyártási listában az eredeti alkatrészeknek meg kell maradniuk;
- nem szabad a belső kivágásokat „eldobni”, mert funkcionális geometriák.

A cavity-prepack külön rétegben jobban kontrollálható.

## 23. Cavity-prepack alapfogalmak

### 23.1 Parent part

Olyan alkatrész, amelynek van belső kivágása.

### 23.2 Cavity

A parent egy belső kontúrja, amelybe elvileg más alkatrész elhelyezhető.

### 23.3 Usable cavity

A cavity margin/gap levonása után még elég nagy és topológiailag alkalmas.

### 23.4 Child part

Olyan kisebb alkatrész, amelyet egy cavitybe előre be lehet pakolni.

### 23.5 Macro-part / virtual parent

A parent + benne előre rögzített child placementek együttese, amelyet a fő solver egy darabként kezel.

## 24. Cavity-prepack pipeline

```text
Original item set with holes
      |
      v
Cavity extraction
      |
      v
Cavity usability filter
      |
      v
Candidate child matching
      |
      v
Cavity local nesting / prepack
      |
      v
Macro-part creation
      |
      v
Main solver nesting
      |
      v
Expansion back to original parts
      |
      v
Exact final validation
```

## 25. Cavity extraction

Minden hole-ra ki kell számolni:

- parent part id;
- hole contour id;
- hole polygon;
- area;
- bbox;
- inward offset gap szerint;
- usable polygon;
- min width / height proxy;
- shape complexity;
- allowed child rotations;
- local coordinate system.

## 26. Cavity usability filter

Nem minden hole használható.

Ki kell zárni:

- túl kicsi hole;
- túl keskeny hole;
- önmetsző vagy invalid hole;
- offset után eltűnő hole;
- production rule szerint tiltott hole;
- olyan hole, amelynél lead-in/out vagy vágási logika miatt nem biztonságos a behelyezés;
- olyan belső kontúr, amely nem valódi kivágás, hanem marker/engrave/metadat.

## 27. Candidate child matching

A cavityhez lehetséges child partokat kell keresni:

- bbox alapján;
- area alapján;
- min dimension alapján;
- allowed rotation alapján;
- material/thickness egyezés alapján;
- quantity alapján;
- priority alapján.

Első verzióban elég:

- single child per cavity;
- majd több child per cavity később.

## 28. Local cavity nesting

A cavitybe történő prepack lehet:

### V1

- egy child part egy cavityben;
- candidate rotations;
- candidate positions;
- jagua collision / boundary check;
- exact local validation.

### V2

- több child egy cavityben;
- mini local optimizer;
- same backend, de kis problémamérettel;
- local utilization score.

## 29. Macro-part létrehozása

Ha egy parentbe child kerül:

- parent outer polygon marad a fő solver item geometry-ja;
- child placement metadata parent-local koordinátában tárolódik;
- child instance kikerül a fő solver globális item listájából;
- macro-part id létrejön;
- darablista kapcsolat megmarad.

Fontos:

> A fő solver nem „tudja”, hogy a parent belsejében child van. Ő csak a parent outer kontúrját pakolja. Az expansion és exact validation állítja vissza a teljes gyártási layoutot.

## 30. Expansion

A fő solver eredménye után:

```text
global_child_transform =
  global_parent_transform
  * local_child_transform
```

Minden child visszakerül globális koordinátába.

Ellenőrizni kell:

- parent transform;
- rotation composition;
- translation;
- quantity;
- no duplicate instance;
- no missing child;
- no child outside parent cavity;
- child nem ütközik parent material geometriával.

## 31. Exact final validation Phase 3-ban

A final validator bővül:

- parent outer vs sheet boundary;
- parent outer vs other parts;
- child inside cavity;
- child vs parent solid region;
- child vs other child ugyanabban cavityben;
- child vs globally placed parts;
- spacing;
- margin;
- quantity;
- original item identity;
- hole contour preservation.

## 32. Phase 3 elfogadási kritériumok

Phase 3 akkor kész, ha:

- hole-os inputot nem dobja el;
- hole metadata megmarad;
- cavity extraction report készül;
- legalább single-child cavity-prepack működik;
- macro-part expansion valid;
- exact final validation PASS;
- ha cavity nem használható, a parent akkor is normál alkatrészként kezelhető;
- a darablista nem sérül;
- reportban látszik:
  - total cavities;
  - usable cavities;
  - used cavities;
  - placed child count;
  - saved sheet area proxy;
  - invalid/ignored cavity okok.

---

# Phase 4 — Optimizer minőségjavítás

## 33. Miért külön Phase 4?

Az első három fázis a funkcionális architektúrát bizonyítja.

A Phase 4 célja már a minőség:

- jobb kihasználtság;
- kevesebb sheet;
- jobb interlocking;
- gyorsabb futás;
- több rotáció;
- stabilabb eredmény több seed mellett.

## 34. Fejlesztendő optimizer elemek

### 34.1 Adaptive rotation strategy

Nem kell rögtön teljesen szabad forgás.

Lépcsők:

1. fixed rotations: 0/90/180/270;
2. 15°;
3. 10°;
4. 5°;
5. 3°;
6. candidate-specific fine rotation;
7. local continuous refine, ha backend támogatja / megéri.

Fontos:

> A finomabb rotáció csak akkor hasznos, ha a search elég gyors ahhoz, hogy ki is használja. Önmagában a több rotáció nem minőségjavítás, ha emiatt kevesebb layout-próba fér bele.

### 34.2 Multi-start search

- több seed;
- több initial order;
- több sheet order;
- időkeret elosztása;
- legjobb valid layout kiválasztása.

### 34.3 Guided Local Search

A Sparrow-szerű szemléletből itt jöhet:

- rossz itemek büntetése;
- gyakran ütköző párok büntetése;
- boundary-heavy itemek priorizálása;
- sheet eliminációs penalty;
- stagnálás esetén perturbáció.

### 34.4 Beam / pool alapú search

Egyetlen layout állapot helyett több jelölt:

- top-K candidate layout;
- divergence fenntartása;
- invalid, de javítható layout megtartása rövid ideig;
- valid layoutok elit poolja;
- idő végén best valid kiválasztása.

### 34.5 Compaction

Többféle tömörítés:

- bottom-left compaction;
- left/down slide;
- sheet boundary irányú húzás;
- cluster compaction;
- pairwise settle;
- remnant shape boundary-aware compaction.

### 34.6 Sheet elimination

Külön stratégia:

- legkevésbé kihasznált sheet kiválasztása;
- itemek áthelyezési sorrendje;
- nagy itemek előbb;
- rare-shape itemek előbb;
- rollback;
- partial success megőrzése.

## 35. Phase 4 benchmark célok

Nem kell azonnal nest&cut szintet ígérni, de kell mérés.

Minden benchmarkban szerepeljen:

- runtime;
- placed count;
- unplaced count;
- used sheet count;
- placed area;
- utilization;
- exact validation status;
- collision count;
- boundary violations;
- seed;
- profile;
- rotations;
- backend mode;
- optimizer mode.

Javasolt összevetések:

- régi BLF fallback;
- régi exact NFP solver, ahol lefut;
- új jagua optimizer baseline;
- új jagua optimizer advanced profile;
- etalon report, ha van összevethető input.

---

# Phase 5 — Production hardening és integráció

## 36. API integráció

A solver legyen futtatható:

- CLI-ből;
- benchmark scriptből;
- backend API-ból;
- később UI new run wizardból.

Szükséges mezők:

- solver type: `jagua_custom_optimizer`;
- profile;
- time limit;
- seed;
- rotations;
- sheet source;
- allow holes: false/true;
- cavity prepack: false/true;
- exact validation required: true.

## 37. Report formátum

A report legyen géppel és emberrel olvasható:

```json
{
  "solver": "jagua_custom_optimizer",
  "phase_capabilities": {
    "rectangular_multi_sheet": true,
    "irregular_sheet": false,
    "holes": false,
    "cavity_prepack": false
  },
  "input": {
    "part_count": 0,
    "instance_count": 0,
    "sheet_count_available": 0
  },
  "result": {
    "placed_instances": 0,
    "unplaced_instances": 0,
    "used_sheets": 0,
    "utilization": 0.0,
    "runtime_sec": 0.0,
    "validation": "PASS"
  },
  "diagnostics": {}
}
```

## 38. UI integráció

A UI-ban látszódjon:

- solver profile;
- unsupported input warning;
- hole ignored / blocked / cavity-prepacked státusz;
- exact validation result;
- sheet utilization;
- unplaced parts;
- export artifacts.

Kiemelten:

> Phase 1-ben hole-os inputnál a UI ne engedje úgy futtatni a solvert, hogy a felhasználó azt higgye, a hole-ok kezelve vannak.

## 39. Export

Export szinten kell:

- layout JSON;
- preview SVG;
- debug SVG;
- final validation report;
- cavity-prepack report;
- optional DXF export későbbi fázisban.

---

# 40. Fejlesztési task bontás

## Task JG-00 — Jagua/Sparrow kódszintű audit

Cél:

- pontos API és korlátok feltárása;
- döntés, hogy mit veszünk át, mit írunk újra.

Kimenet:

- audit markdown;
- kockázati lista;
- ajánlott adapter contract;
- Phase 1 implementációs döntések.

## Task JG-01 — Repo integrációs előkészítés

Cél:

- dependency / workspace / feature flag előkészítése.

Kimenet:

- buildelhető minimal integration;
- feature flag;
- no-op adapter.

## Task JG-02 — Minimal Jagua adapter proof-of-contact

Cél:

- egyszerű polygon collision check.

Kimenet:

- 3–5 item smoke test;
- valid/invalid placement tesztek;
- adapter skeleton.

## Task JG-03 — NestingInputContract outer-only validáció

Cél:

- Phase 1 input explicit szűrése.

Kimenet:

- outer-only item extraction;
- hole-os input explicit reject/warning;
- contract tests.

## Task JG-04 — Rectangular single-sheet baseline optimizer

Cél:

- 1 sheet, outer-only, egyszerű initializer + collision check.

Kimenet:

- valid layout;
- exact validator PASS;
- smoke benchmark.

## Task JG-05 — Rectangular multi-sheet support

Cél:

- több sheet kezelése.

Kimenet:

- sheet assignment;
- used sheet count;
- unplaced list;
- exact validation.

## Task JG-06 — Repair-search loop V1

Cél:

- Sparrow-szerű repair/penalty search első verzió.

Kimenet:

- move generator;
- score model;
- repair loop;
- deterministic seed.

## Task JG-07 — Sheet elimination V1

Cél:

- sheet count csökkentési próbák.

Kimenet:

- weakest sheet detection;
- reinsert attempts;
- rollback;
- report metrics.

## Task JG-08 — Benchmark matrix Phase 1

Cél:

- mérhető összevetés.

Kimenet:

- smoke/small/medium/realistic no-hole fixture;
- JSON/MD report;
- runtime/utilization metrics.

## Task JG-09 — Irregular sheet model spike

Cél:

- `jagua-rs` irregular container képesség tisztázása.

Kimenet:

- irregular bin proof;
- boundary validation;
- döntés natív vagy saját boundary check irányról.

## Task JG-10 — Irregular sheet provider

Cél:

- alakos sheet input és usable polygon.

Kimenet:

- L-shape/remnant fixture;
- margin handling;
- exact validator integration.

## Task JG-11 — Irregular optimizer candidate generation

Cél:

- boundary-aware placement.

Kimenet:

- interior sample;
- edge-near candidate;
- repair moves;
- benchmark.

## Task JG-12 — Cavity extraction

Cél:

- hole-okból cavity model.

Kimenet:

- cavity report;
- usability filter;
- no geometry loss guarantee.

## Task JG-13 — Single-child cavity-prepack

Cél:

- egy child behelyezése egy cavitybe.

Kimenet:

- local validation;
- macro-part metadata;
- quantity update.

## Task JG-14 — Macro-part expansion

Cél:

- fő solver után childok visszavetítése globális layoutba.

Kimenet:

- transform composition;
- exact validation;
- report.

## Task JG-15 — Multi-child cavity-prepack V2

Cél:

- több child egy cavityben.

Kimenet:

- local mini optimizer;
- cavity utilization;
- exact validation.

## Task JG-16 — Production API/UI integration

Cél:

- új solver profil használható legyen alkalmazásból.

Kimenet:

- API paraméterek;
- UI státuszok;
- artifacts;
- e2e smoke.

---

# 41. Kockázatok

## 41.1 `jagua-rs` API nem illik pontosan a célhoz

Lehetséges, hogy a natív modell nem pont fixed multi-sheet/remnant/cavity célra készült.

Kezelés:

- adapter absztrakció;
- Phase 0 spike;
- ne kössük az üzleti logikát közvetlenül a jagua típusaihoz.

## 41.2 Irregular sheet támogatás korlátozott

Ha natív irregular bin nem elég:

- saját boundary validator;
- saját candidate generation;
- jagua csak item-item collision backend.

## 41.3 Hole kezelés túl komplex

Ezért nem Phase 1.

Kezelés:

- explicit reject Phase 1-ben;
- cavity-prepack külön pipeline;
- macro-part metadata;
- exact expansion validation.

## 41.4 Optimizer minőség nem elég

A collision backend önmagában nem optimizer.

Kezelés:

- Sparrow-szerű repair-search;
- multi-start;
- score tuning;
- benchmark matrix;
- sheet elimination;
- guided penalties.

## 41.5 Pontosság vs sebesség konfliktus

A solver gyors proxyval dolgozhat, de a gyártási output csak exact validator PASS után fogadható el.

Kezelés:

- exact geometry megőrzése;
- final validator kötelező;
- invalid layout soha nem lehet sikeres eredmény.

---

# 42. Döntési kapuk

## Gate 0 — Integrációs döntés

Tovább Phase 1-be csak akkor:

- jagua adapter proof működik;
- collision check megbízható;
- build/integration nem blokkol;
- nincs licence vagy technikai showstopper.

## Gate 1 — Rectangular viability

Tovább Phase 2-be csak akkor:

- rectangular multi-sheet valid;
- exact validation stabil;
- benchmark report reprodukálható;
- legalább kis/közepes fixture-ön értelmes minőség van.

## Gate 2 — Irregular viability

Tovább Phase 3-ba csak akkor:

- irregular boundary check megbízható;
- margin handling konzervatív;
- exact validation PASS;
- rectangular működés nem romlott el.

## Gate 3 — Cavity viability

Production irányba csak akkor:

- cavity-prepack nem veszít geometriát;
- darablista helyes;
- expansion valid;
- final layout exact PASS;
- report auditálható.

---

# 43. Rövid végkövetkeztetés

A javasolt átállási terv jó és következetes:

1. **Ne hole-okkal kezdjünk.**
2. **Ne remnanttal kezdjünk.**
3. **Először legyen stabil rectangular multi-sheet solver.**
4. **A `jagua-rs` legyen backend, ne teljes üzleti solver.**
5. **A Sparrow inkább optimizer-minta legyen, ne vakon átvett core.**
6. **Irregular sheet legyen a második nagy képesség.**
7. **Hole/part-in-hole kezelés cavity-prepacken keresztül jöjjön.**
8. **Exact final validation minden fázisban kötelező.**

Ez a sorrend a legkisebb kockázatú út ahhoz, hogy a projekt a jelenlegi nehezen skálázódó exact NFP-vonalról egy gyorsabb, iparilag reálisabb nesting architektúra felé mozduljon.
