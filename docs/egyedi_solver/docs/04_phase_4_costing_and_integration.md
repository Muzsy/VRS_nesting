# **Phase 4: Költségszámítás és Ipari Integráció (Costing Integration & Industrial Polish)**

## **Célkitűzés**
A matematikai koncepció és a heurisztikus motor robusztus, termelési környezetbe (ERP/MES rendszerekbe) azonnal bevezethető szoftvertermékké formálása. A fázis fő fókuszterületei a kimeneti interfészek véglegesítése, az árajánlatadó (Costing) proxy metrikák implementálása, valamint a rendszer páncélzattal való ellátása (hardening) az ipari környezetben előforduló hibás adatokkal szemben.

---

## **Szoftveres Alapozás és Spontek (Sprints)**

### **Sprint 4.1: A JSON Kimeneti Szerződés (Output Contract)**
A rendszer kimenetének standardizálása a mikro-szolgáltatásokhoz.
* **Séma Véglegesítése:** A szigorú JSON Schema definiálása, amely tartalmazza a `solution_id`, `diagnostics`, `bins_used`, `placements` (transzformációs mátrixokkal) és az `unplaced_parts` mezőket. 
* **Determinisztikus Generálás:** A JSON objektumok kulcsainak lexikografikus (ábécé) sorrendbe rendezése.
* **Validáció:** Annak tesztelése és garantálása, hogy a "Seed A" maggal futtatott algoritmus mindig pontosan ugyanazt az "Output A" karakterláncot eredményezi.

### **Sprint 4.2: Költség-metrikák (Costing)**
A P3 célfüggvény (vágási idő minimalizálása) helyettesítő metrikáinak (proxy) bevezetése az árajánlatadáshoz.
* **Útvonal és Bekezdések:** A becsült vágási úthossz és a bekezdések (pierce count) számának kalkulációja.
* **Közös Vonal (Common-line):** A Common-line cutting lehetőségeinek proaktív detektálása (amikor két párhuzamos él megfelelő távolságra van, és egyetlen vágással szétválasztható), drasztikusan csökkentve a lézerfej holtjátékát. 

### **Sprint 4.3: Peremesetek Elleni Védelem (Edge Case Hardening)**
A motor védvonalainak megerősítése a kritikus leállások ellen.
* **Erőforrás-védelem:** A végtelen keresési ciklusok és a memóriatúlcsordulások (Out of Memory - OOM) megakadályozása.
* **Hibás Geometriák Kezelése:** Védelem a súlyosan degenerált, hibás CAD fájlok (például önmetsző nyitott vonalak, mikroszkopikus hézagok) okozta összeomlások ellen.

---

## **Technikai Elfogadási Kapu 4 (Gate 4: Integráció és Cross-Platform Determinizmus)**
A végső, termelésbe állítást megelőző átfogó teszt:
* **Futtatási Környezet:** A motort párhuzamosan kell futtatni több, eltérő processzorarchitektúrán (például egy Ubuntu Linux/x86_64 szerveren és egy Apple Silicon/ARM64 munkaállomáson).
* **Kritérium:** Ugyanazon bemeneti darablista és ugyanazon fix random seed használata esetén az algoritmusnak **garantáltan, bit-pontosan megegyező JSON kimenetet** és végső elrendezést kell eredményeznie mindkét platformon. Ez igazolja az i64 skálázott egészekre épülő Geometriai Mag tökéletes determinizmusát.