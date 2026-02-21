Ipari 2D Irreguláris Nesting Motor: Fejlesztési Dokumentáció és Ütemterv
Vezetői Összefoglaló (Executive Summary)
A projekt célja egy saját tulajdonú, ipari kategóriájú, fix táblaméretű 2D irreguláris nesting (vágási és csomagolási) motor kifejlesztése.  A rendszer alapja egy szigorú, lexikografikusan rendezett célfüggvény, amely hierarchikus sorrendben elégíti ki a gyártási kényszereket:

P0 (Kivitelezhetőségi kapu): Zéró tolerancia a geometriai hibákkal szemben (nincs átfedés, nincs tábláról való lelógás, szigorú távolságtartás).

P1 (Táblaszám minimalizálása): A legfőbb gazdasági cél a felhasznált alapanyag (és ezáltal a költségek) drasztikus csökkentése.

P2 (Maradék értékének maximalizálása): A leeső hulladék minél nagyobb, egybefüggő darabokká formálása az újrahasznosíthatóság érdekében.

P3 (Vágási idő minimalizálása): Proxy metrikák (pl. közös vonal menti vágás) használata a CNC gépek hatékonyságának növelésére.

A rendszer kimenete nem nyers G-kód vagy DXF, hanem egy szigorúan determinisztikus, sémával validált JSON struktúra, amely integrálható ERP és MES rendszerekkel.

I. Rendszerarchitektúra
A szoftver hat, szigorúan elkülönített felelősségi körű modulból áll:

Geometriai Mag: Csakis 64 bites skálázott egészeket (i64) használ a lebegőpontos kerekítési hibák elkerülése végett. A Clipper2 könyvtárra épül FFI (Foreign Function Interface) hívásokon keresztül.

Import/Inflate: Felelős a CAD fájlok folytonos görbéinek (ARC/SPLINE) egyenesekké tördeléséért, valamint a vágási rés (kerf) miatti poligon-növelésért (felfújás).

Feasibility Engine (Orákulum): R-Fa (R-Tree) térbeli indexeléssel végzi a gyors, kétlépcsős (Broad és Narrow phase) ütközésvizsgálatot.

Search/Placement: Heurisztikus réteg, amely a Bottom-Left-Fill (BLF) elvet és a Szimulált Lehűtés (Simulated Annealing) metaheurisztikát használja a darabok elhelyezésére és sorrendezésére.

Kompaktáló Modul: Fizika-alapú erőirányított modellel vagy Lineáris Programozással (LP) utólagosan sűríti az elrendezést.

Multi-bin Vezérlő: Több nyersanyagtábla kezelését és a maradékok (remnants) újrahasznosíthatósági értékelését végzi.

II. Részletes Fejlesztési Ütemterv (Sprints)
A fejlesztés iteratív, négy fő fázisra (Phase) bomlik, melyek mindegyike egy Működőképes Minimum Terméket (MVP) és egy szigorú Technikai Elfogadási Kaput (Technical Acceptance Gate) tartalmaz.

Phase 1: Az "Igazság" Rétege (The Truth Layer)
Ebben a fázisban az algoritmus még "buta", a cél a hibátlan, determinisztikus alapgeometria megteremtése.

Sprint 1.1: A C++ Clipper2 és a Rust közötti biztonságos FFI híd kiépítése, valamint a skálázott egész számok (i64) konverziós logikájának implementálása.

Sprint 1.2: A DXF poligonok beolvasása, az ívek diszkretizálása (tördelése), és az ofszetelés (InflatePaths64) megírása a topológiai torzulások kiszűrésével.

Sprint 1.3: Az R-Fa (rstar) integrációja és az Orákulum can_place? metódusának megírása.

Elfogadási Kapu (Gate 1): Egy 100 000 randomizált tesztesetből álló futás során az átfedés-vizsgálónak zéró hamis pozitív vagy hamis negatív eredményt kell hoznia.

Phase 2: Egytáblás Elhelyezés és Tömörítés
A rendszer képessé válik önálló elrendezések generálására egyetlen táblán.

Sprint 2.1: A Bottom-Left-Fill (BLF) és a Collision-Free Region (CFR) logikájának kódolása.

Sprint 2.2: A Szimulált Lehűtés (Simulated Annealing) motorjának implementálása a darabok bemeneti sorrendjének és forgatásának optimalizálására.

Sprint 2.3: A fizika-alapú (rugómodell) vagy a Lineáris Programozáson (LP) alapuló Kompaktáló motor integrálása.

Elfogadási Kapu (Gate 2): Az ESICUP Albano benchmarkon a publikált tudományos élvonalbeli eredmények legalább 95%-ának elérése megszabott időn belül, a P0 kapu sérülése nélkül.

Phase 3: Többtáblás Elosztás és Maradékkezelés
Komplex ipari megrendelések támogatása több táblán.

Sprint 3.1: A First-Fit Decreasing (FFD) és az 1D-BPP matematikai stratégiák megalkotása az alkatrészek táblák közötti szétosztására.

Sprint 3.2: A leeső hulladék (Remnant) matematikai modellezése és vizuális értékelése.

Sprint 3.3: A "Lyukba-ágyazás" (Part-in-Part / Swiss Cheese) logika implementálása, amellyel a nagy alkatrészek belső lyukai virtuális al-táblákként funkcionálnak.

Elfogadási Kapu (Gate 3): Sikeres teszt az ESICUP Jakobs1/Jakobs2 benchmarkokon, és egy több mint 1000 alkatrészes megrendelés hibátlan szétosztása, működő Part-in-Part mechanizmussal.

Phase 4: Költségszámítás és Ipari Integráció
A rendszer termelési környezetbe (ERP/MES) való illesztése.

Sprint 4.1: A szigorú, determinisztikus JSON kimeneti szerződés és séma véglegesítése.

Sprint 4.2: Költség-metrikák (P3 proxyk), mint a vágási hosszak, bekezdések (pierce count) és a közös vonalú vágás lehetőségeinek detektálása.

Sprint 4.3: A szoftver páncélozása (hardening) a memóriatúlcsordulások és a súlyosan hibás CAD fájlok okozta végtelen ciklusok ellen.

Elfogadási Kapu (Gate 4): Átfogó, platformfüggetlen (pl. x86_64 vs. ARM64) integrációs teszt, ahol azonos bemenet és fix random seed bit-pontosan megegyező JSON kimenetet kell, hogy eredményezzen.

III. Kockázatelemzés és Mitigációs Stratégiák
A fejlesztés során az alábbi geometriai csapdákat kell szigorúan elkerülni:

Nem-Determinizmus: A lebegőpontos (f64) aritmetika használata tilos; kötelező a megfelelően skálázott (pl. 10 mikrométeres pontosságú) egészes (i64) reprezentáció alkalmazása a kerekítési hibák kiküszöbölésére.

Topológiai Korrupció: A geometriák ofszetelése ("felfújása") során összeomló lyukak vagy önmetsző élek keletkezhetnek. Ennek elkerülésére a Clipper2 Simplify funkcióját kell hívni, és topológiai validációt kell tartani a lyukak számáról.

Diszkretizációs Hibák: A CAD görbék egyenesekre bontásánál szigorúan kifelé kerekítő (outward approximation) algoritmust kell használni egy adaptívan számított maximális húrhiba alapján, megelőzve az alkatrészek egymásba lógását.

Érintés vs. Átfedés: A "Szigorú Biztonsági Oldal" (Strict Safe-Side) politika alapján a geometriailag tökéletesen érintkező, inflált poligonok elfogadottak, de minden bizonytalan, numerikus rács-fluktuációból adódó metszést azonnal hibaként kell kezelni.

IV. Minőségbiztosítási (QA) Stratégia
A kód stabilitását három pillér garantálja:

ESICUP Benchmarkok: A folyamatos integráció (CI) során az Albano, Jakobs és Mao adathalmazokon mérik az algoritmus hatékonyságát és sebességét.

Egyedi Ipari Tesztek: A "Svájci Sajt" teszt a lyukba-ágyazást, míg a "Kígyó" teszt a diszkretizációt, az R-Fa gyengeségeit és a tömörítő modul oszcillációját teszi próbára.

Determinizmus Protokoll: A reprodukálhatóság érdekében rögzített véletlenszám-magot (seed) használnak, és minden futást "Hash-back" teszttel (SHA-256) ellenőriznek, garantálva a platformfüggetlen konzisztenciát.