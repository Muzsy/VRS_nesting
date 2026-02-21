# **Phase 1: Az "Igazság" Rétege (The Truth Layer)**

## **Célkitűzés**
A Geometriai Mag, az Import/Inflate alrendszer és a Feasibility Engine (Kivitelezhetőségi Motor) felépítése. Ebben a kezdeti fázisban az algoritmus még "buta"; semmilyen intelligens optimalizálás vagy metaheurisztika nem kap helyet. A kizárólagos cél a hibátlan alapgeometria és a tökéletes, determinisztikus ütközésvizsgálat (P0 kapu) garantálása. A tervezet alapelve szerint: ha az Igazság Rétege hibás, minden rá épülő heurisztika összeomlik.

---

## **Szoftveres Alapozás és Spontek (Sprints)**

### **Sprint 1.1: FFI és Skálázott Aritmetika (Scaled Arithmetic)**
Az alapvető adatszerkezetek és a memóriabiztos áthidalás megteremtése.
* **Aritmetika:** A lebegőpontos számok (f64) elvetése, helyettük 64 bites előjeles skálázott egészek (`i64`) bevezetése a geometriai számításokhoz.
* **FFI (Foreign Function Interface) híd:** Biztonságos szoftveres kapcsolat kiépítése a Rust memóriakezelési rendszere és a C++ alapú Clipper2 könyvtár között. 
* **Implementáció:** A konverziós logikák és az adatstruktúrák (Point64, Path64, Paths64) kidolgozása ezen a biztonságos hídon keresztül.

### **Sprint 1.2: Diszkretizáció és Infláció (Import modul)**
A bemeneti adatok feldolgozása és gyártásra (vágásra) való előkészítése.
* **DXF Beolvasás és Tördelés:** A névleges DXF poligonok betöltése, valamint a folytonos görbék (ívek) egyenes szakaszokká történő diszkretizálása. Ennek során a maximális húrhiba (max chord error) dinamikus kalkulálását kell alkalmazni. 
* **Ofszetelés (Infláció):** A Clipper2 `InflatePaths64` műveletének integrálása, amellyel a vágási rés (kerf) és a kötelező margó (margin) hozzáadódik az alkatrész kontúrjához.
* **Topológiai Tisztítás:** A `Simplify` (Douglas-Peucker) eljárás kötelező integrálása, amely kiszűri a topológiai torzulásokat, az eltűnő lyukakat és az öngyulladó/önhurkoló (self-intersecting) éleket az ofszetelés után.

### **Sprint 1.3: R-Fa (R-Tree) és az Orákulum Integrációja**
A térbeli indexelés és a Kivitelezhetőségi Motor (Feasibility Engine) felépítése.
* **Térbeli Indexelés:** A tengely-párhuzamos befoglaló dobozok (AABB) betöltése a magasan optimalizált `rstar` fába. 
* **Az Orákulum (can_place?):** A központi lekérdező metódus megalkotása, amely eldönti, hogy egy alkatrész elhelyezhető-e az adott pozícióban.
* **Kétlépcsős Vizsgálat:** A lekérdezés összekötése a Broad phase (gyors R-Fa szűrés) és a Narrow phase (Clipper2 Boole-metszetvizsgálat) elágazásokkal.

---

## **MVP (Működőképes Minimum Termék) Útvonal**
A fázis végére elkészítendő szoftver:
* Egy parancssoros (CLI) szoftvereszköz.
* Képes beolvasni két egyszerű poligonfájlt.
* Egy statikusan megadott X-Y pozícióban leellenőrzi a két alakzat közötti esetleges átfedést.
* A vizsgálat végén egy determinisztikus, egyértelmű IGAZ/HAMIS (True/False) értéket ad vissza a standard kimeneten.

---

## **Technikai Elfogadási Kapu 1 (Gate 1: P0 Teszt)**
A következő fázisba lépés szigorú és áttörhetetlen feltétele:
* A motort egy 100 000 elemből álló, randomizált teszteseten kell lefuttatni.
* A tesztkészletnek kötelezően tartalmaznia kell degenerált peremeseteket és egy speciális "Arc-Heavy" (ívekkel extrém módon terhelt) egyedi adathalmazt is.
* **Kritérium:** A motornak naplózottan pontosan **0 darab hamis pozitív** (téves riasztás) és **0 darab hamis negatív** (észre nem vett átfedés) hibát kell jelentenie.