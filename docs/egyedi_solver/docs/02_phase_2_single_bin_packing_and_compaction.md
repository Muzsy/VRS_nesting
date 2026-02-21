# **Phase 2: Egytáblás Elhelyezés és Tömörítés (Single-bin Packing & Compaction)**

## **Célkitűzés**
A Kereső és Elhelyező (Search/Placement) heurisztikák felépítése, amellyel a motor "életre kel". A fázis végére a rendszer képessé válik az első működő, egyetlen táblára korlátozódó elrendezések önálló generálására. Ezt követően a rendszer ezen elrendezések sűrűségét utólagos, iteratív módon növeli (kompaktálja).

---

## **Szoftveres Alapozás és Spontek (Sprints)**

### **Sprint 2.1: A Bottom-Left-Fill (BLF) és a CFR Reprezentáció**
A kezdeti, laza elrendezések felépítését végző alapvető heurisztika implementálása.
* **Gyorsítótárazás (Caching):** A geometriai mag kiegészítése a No-Fit Polygon (NFP) és az Inner-Fit Polygon (IFP) lekérdezések gyorsítótárazásával, lerövidítve a számítási időt. 
* **CFR (Collision-Free Region):** Az IFP és az NFP különbségeként előálló szabad elhelyezési zónák matematikai előállítása.
* **BLF Algoritmus:** A "Legalacsonyabb Súlypont" elvének kódolása, amely egy virtuális gravitációs mezőt szimulálva a darabokat folyamatosan balra és lefelé ejti a táblán, amíg azok egy stabil, ütközésmentes pozícióban meg nem akadnak. 

### **Sprint 2.2: Alapszintű Metaheurisztika**
A BLF algoritmus önmagában ritkán ad globális optimumot, ezért a darabok beillesztési sorrendjét optimalizálni kell.
* **Szimulált Lehűtés (Simulated Annealing - SA):** A metaheurisztikus motor megírása, amely iteratívan, véletlenszerűen módosítja a bemeneti darabok sorrendjét és lehetséges rotációs szögeit (pl. **90°**, **180°**, vagy ipari igény esetén folytonos forgatással). 
* **Állapottér bejárása:** Az SA logika alapján az algoritmus kiszámítja az új elrendezés célfüggvény-értékét (P1 és P2 metrikák), és egy termodinamikai valószínűségi függvény alapján képes elfogadni rosszabb megoldásokat is, hogy elkerülje a lokális optimumokban való elakadást.

### **Sprint 2.3: A Kompaktáló Modul Integrációja**
Az SA és a BLF által létrehozott elrendezések utólagos "összepréselése", a sűrűség javítása és a hézagok csökkentése érdekében.
* **Fizika-alapú Erőirányított Modell:** A poligonok modellezése egy virtuális tömegpontokból és rugókból álló rendszerként, ahol a tábla sarka vonzóerőt, míg az egymásba csúszó alkatrészek taszítóerőt (Minimum Translation Vector) generálnak.
* **Lineáris Programozás (LP) Modell:** Alternatív, determinisztikusabb megoldásként egy szeleteléses (slice) modell alkalmazása, ahol a geometriai nem-átfedési feltételeket horizontális és vertikális egyenletekké linearizálják, majd egy szimplex (simplex) algoritmussal tömörítik. 

---

## **MVP (Működőképes Minimum Termék) Útvonal**
A fázis végére elkészítendő szoftver:
* Egy teljes értékű, de még korlátozott parancssoros vagy asztali eszköz.
* Képes beolvasni egy teljes DXF darablistát.
* A darabokat egyetlen, végtelen hosszúságú szalagként (Strip Packing) kezelt konténerbe tömöríti a BLF és a kezdetleges sorrend-optimalizáló segítségével.

---

## **Technikai Elfogadási Kapu 2 (Gate 2: ESICUP Validáció)**
A következő fázisba lépés szigorú és áttörhetetlen feltétele:
* A rendszeren le kell futtatni az ipari sztenderd ESICUP Albano benchmark készletet.
* **Kritérium 1 (P0):** A rendszernek garantáltan érvényes, a P0 kaput sérülésmentesen (0 átfedés) teljesítő elrendezést kell adnia.
* **Kritérium 2 (Hatékonyság):** A kitöltési hatékonyságnak (utilization rate) belátható futási időn (pl. 5 perc) belül el kell érnie a publikált tudományos élvonalbeli átlageredmények minimum **95%-át**.