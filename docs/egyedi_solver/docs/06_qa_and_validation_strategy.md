# **IV. Minőségbiztosítási és Validációs Stratégia (QA Pipeline)**

## **Célkitűzés**
A rendszer pontosságának, teljesítményének és a publikált algoritmusokhoz viszonyított hatékonyságának igazolása objektív, tudományosan és iparilag is elfogadott mérőszámokon. A regressziós hibák elkerülése érdekében a Continuous Integration (CI) folyamatba egy kiterjedt, szigorúan reprodukálható tesztelési csővezetéket kell integrálni.

---

### **1. Az ESICUP Benchmark Készlet Használata**
Az Európai Vágási és Csomagolási Különleges Érdeklődési Csoport (ESICUP) standard referencia adathalmazainak kötelező használata a heurisztikák hiteles összevetéséhez a "State-of-the-Art" megoldásokkal.
* **Albano:** 24 darab közepesen komplex, nem-konvex forma (ruházati/textiliparból) a P1 kitöltési hatékonyság és a diszkrét elforgatási kényszerek vizuális és numerikus tesztelésére.
* **Jakobs1 / Jakobs2:** 25 darab "fűrészfogas" (jigsaw), egymásba illeszthető geometria. A tudott optimális kitöltés 100%, így ideális a Kompaktáló Modul hatékonyságának validálására.
* **Mao:** Extrém irreguláris, nagyszámú csúcsponttal rendelkező poligonok a tiszta teljesítmény (Performance Benchmark) mérésére, az R-Fa lekérdezések és a Boole-metszetek időkomplexitásának teszteléséhez.
* **Kritérium:** Minden nagyobb verziófrissítéskor a motornak kötelezően hoznia kell a publikált kihozatali (utilization) arányok minimum 95-98%-át egy adott futási időablakon (pl. 300 másodperc) belül; ellenkező esetben a CI rendszer blokkolja a frissítést.

### **2. Egyedi Ipari Teszt-geometriák (Custom Industrial Fixtures)**
Az ipari valóság peremeseteit modellező agresszív tesztkészlet alkalmazása.
* **A "Svájci Sajt" (The Swiss Cheese) Teszt:** Masszív, komplex, aszimmetrikus belső lyukakkal rendelkező alkatrészek. A Part-in-Part logika, a lyukak irányításának (Winding Rule), és a belső szabad zónák (CFR) generálásának validálására szolgál. Ha a motor nem tud kisebb alkatrészt a lyukba illeszteni, az az inflációs fázis topológiai bukását jelenti.
* **A "Kígyó" (The Snake) Teszt:** Extrém hosszú, elnyújtott, "S" betű formájú vékony alakzatok. A Spline diszkretizáció pontosságát, valamint az R-Fa (R-Tree) térbeli indexelésének gyengeségeit tárja fel (a hatalmas üres területeket tartalmazó befoglaló dobozok miatt). Továbbá a spirális elhelyezkedés extrém próba a fizika alapú Kompaktáló Modul számára, kikényszerítve az oszcilláció elleni hibatűrést.

### **3. A Determinizmus Protokoll**
A megjósolhatóság és ismételhetőség garantálása a CAM operátorok és a költségszámító automatikák számára.
* **Mag Rögzítés (Seed Fixation):** A keresőmotorok és pszeudo-véletlenszám-generátorok (PRNG) kizárólag egy rögzített seed értékkel inicializálódhatnak, amelyet a JSON output is tartalmaz.
* **Hash-alapú Visszacsatolás (Hash-back Test):** A teszt pipeline a fix bemenetekkel kapott JSON outputból egy SHA-256 hash értéket képez. Bármilyen apró változás a hash-ben (pl. egy alkatrész minimális elfordulása) automatikus riasztást vált ki, megelőzve a regressziót.
* **Architektúra-független konzisztencia (Cross-Platform Execution):** A tesztek párhuzamos futtatása Ubuntu Linux (x86_64) és Apple Silicon (ARM64) gépeken. A szigorú `i64` alapú Geometriai Mag garantálja a platformfüggetlen, 100%-os egyezést.