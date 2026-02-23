# Feature Canvas: Pre-Nesting Clusters (Smart Pairing & Mini-Nest)

**Epic / Modul:** Előoptimalizálás és Felhasználói Klaszterezés  
**Státusz:** Tervezet (Draft)  
**Fázis:** Phase 3+ (vagy NFP motor integrációjával párhuzamosan)  
**Típus:** Termékfunkció (UX + Geometriai Backend)

## 1. A Probléma (Problem Statement)
A szabálytalan (irregular) nesting egyik legnagyobb kihívása a kombinatorikus robbanás és a konkáv (bonyolult) alkatrészek egymásba csúsztatása (NFP generálás). 
* Ha a táblán 1000 darab apró, de összeillő alkatrész van (pl. "L" vagy háromszög alakzatok), az optimalizáló motor feleslegesen pazarol időt ezek véletlenszerű próbálgatására.
* A profi gépkezelők "szabad szemmel" sokszor azonnal látják, hogy két-három alkatrész hogyan ad ki egy tökéletes téglalapot vagy maradéktalanul kitöltött blokkot, de jelenleg nincs eszközük ezt a tudást átadni a gépnek (black-box optimalizálás).
* A futás végén keletkező lyukak kitöltéséhez rugalmasságra van szükség.

## 2. A Megoldás (Proposed Solution)
A megoldás egy kétlépcsős "Előoptimalizáló" (Pre-Nesting) modul, amely a felhasználó kezébe adja az irányítást, és tehermentesíti a Rust magot (Truth Layer).

### Szint 1: "Smart Pair" (Okos Párosítás - Gyors)
Automatikus ajánlórendszer az importált, azonos típusú alkatrészekre.
* **Működés:** A rendszer (Python szinten) megvizsgálja az alkatrészt, és ha azonosból több darab van, kiszámol egy olyan összeforgatást (pl. 180 fokkal két háromszög), ami minimalizálja a közös Bounding Box-ot (befoglaló dobozt).
* **UX:** Az alkatrészlista mellett megjelenik egy "Párosítás tesztelése" gomb. Rákattintva a felhasználó látja a létrejött blokk előképét, és egy "Elfogad" gombbal jóváhagyhatja.
* **Backend:** Nem igényel Rust hívást, a Python (Shapely) elvégzi a geometriai egyesítést.

### Szint 2: "Mini-Nest / Cluster Builder" (Klaszter Építő - Profi)
Különálló szerkesztőfelület különböző alkatrészek manuális összefűzésére (Part-in-Part, Interlocking).
* **Működés:** A felhasználó kiválaszt 2-3 különböző alkatrészt (pl. egy nagy "C" alakút és két kicsit, ami befér az öblébe). A rendszer létrehoz egy éppen elegendő méretű virtuális táblát, és **beküldi a meglévő Rust Nesting Motornak**. A motor kidobja a lokális optimumot.
* **UX:** Drag & Drop felület, dedikált "Lokális Optimalizálás" indítógombbal. Az eredmény vizuális ellenőrzése és mentése új "Makro-alkatrészként".
* **Backend:** Újrahasznosítja a meglévő V2 IO Contractot, a Rust motort "mikroszolgáltatásként" hívja meg kis adatkészlettel.

## 3. Architektúra és Adatmodell

A funkció megvalósítása megköveteli a "Szülő-Gyermek" (Parent-Child) hierarchia bevezetését a szoftverben. A Rust motor (Solver) a klasztereket **egyetlen tömör poligonként** fogja kezelni, és sosem látja a belső felépítésüket.

### 3.1. Adatbázis sémabővítés (Supabase / Projekt Modell)
* `parts` tábla bővítése:
  * `is_cluster` (boolean, default: false)
  * `cluster_children` (JSON vagy relációs tábla): Tartalmazza, hogy ez a blokk mely eredeti `part_id`-kból épül fel, és azokon belül milyen relatív `x, y, rotation` eltolással rendelkeznek a klaszter origójához képest.

### 3.2. A Futtatási Csővezeték (Pipeline)
1. **Pre-processing:** A Python futtató a V2 JSON összeállításakor a gyermek alkatrészeket kihagyja, és csak a `cluster` makro-alkatrészek külső burkát (outer contour) küldi be a Rust nesting motornak.
2. **Solving:** A Rust motor a szokásos módon (BLF + NFP + SA) elhelyezi a makro-alkatrészt a nagy táblán.
3. **Post-processing & Unpacking:** A futás végén a Python feldolgozza a `nesting_output.json`-t. A DXF Exportáló modul észleli az `is_cluster: true` taget, és a globális (táblán lévő) koordinátákhoz hozzáadja a klaszteren belüli relatív koordinátákat, így **a DXF-re már a tényleges, különálló eredeti vágási kontúrok kerülnek fel.**

## 4. Kockázatok és Kezelésük (Mitigations)
* **Kockázat:** A nagy blokkok a futás végén nem férnek be a megmaradt lyukakba, rontva a táblakihasználtságot.
* **Kezelés (Jövőbeli Scope):** "Dynamic Un-grouping". Ha a táblakitöltés megakad, a solver visszaszól a Pythonnak, ami felbontja a maradék be nem rakott klasztereket eredeti darabjaikra, és azokkal próbálja betömni a réseket. (A Phase 3 MVP-ben elég, ha a klaszter fix marad).
* **Kockázat:** A klaszterek belső vágási vonalai összeérhetnek (0 gap), amit a vágógép (CAM szoftver) hibának vehet.
* **Kezelés:** A Smart Pair és a Mini-Nest generálásánál is alkalmazni kell a meglévő `spacing` paramétert a darabok között, a klaszter külső burkára pedig a meglévő `margin`-t.

## 5. Elfogadási Kritériumok (Definition of Done - DoD)
- [ ] A UI/UX biztosít felületet egyazon alkatrész 1 kattintásos "Smart Pair" párosítására.
- [ ] A UI/UX biztosít dedikált "Mini-Nest" képernyőt több különböző alkatrész lokális optimalizálására.
- [ ] Az adatbázis (Project Model) képes szülő-gyermek relációban eltárolni a klasztereket a relatív transzformációs mátrixokkal (x, y, rotáció).
- [ ] A Rust nesting motor lefut a klasztereket tartalmazó bemeneten anélkül, hogy a motor kódját módosítani kellene.
- [ ] A DXF export tökéletesen kicsomagolja (unpack) a klasztereket: a kimeneti fájlban a vágási vonalak az eredeti alkatrészek kontúrjai, pontos pozícióban.
- [ ] End-to-end smoke test a Python rétegben, amely verifikálja, hogy egy klaszterezett projekt DXF exportján nincs önmetszés, és be van tartva az elvárt `spacing`.