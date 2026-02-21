# **Phase 3: Többtáblás Elosztás és Maradékkezelés (Multi-bin & Remnant Inventory Logic)**

## **Célkitűzés**
A valós, komplex ipari forgatókönyvek támogatása. A rendszernek képessé kell válnia arra, hogy hatalmas megrendelésállományokat optimálisan osszon szét több, esetleg különböző méretű, független nyersanyagtáblán. Kiemelt cél továbbá a hasznos hulladék (remnant) maximalizálása a P2 célfüggvény alapján.

---

## **Szoftveres Alapozás és Spontek (Sprints)**

### **Sprint 3.1: Stratégia-alapú Multi-bin Controller**
A táblák közötti elosztás (Bin-Assignment) logikájának kifejlesztése.
* **Stratégiák Implementálása:** A First-Fit Decreasing (FFD) és az 1D-BPP (Egydimenziós Bin Packing Problem) matematikai stratégiák megalkotása a magas szintű "melyik darabot melyik táblára" döntésekhez. 
* **Virtuális Csoportosítás:** Az alkatrészek területösszeg alapú elosztása "virtuális" vödrökbe, majd ezen csoportok átadása a Kereső Motornak.
* **Visszacsatolási Hurok (Feedback Loop):** Ha egy csoport elhelyezése fizikailag lehetetlen (pl. a formájuk miatt nem férnek el a táblán, bár a területük megengedné), a rendszer értesíti a vezérlőt, amely újratervezi az elosztást.

### **Sprint 3.2: Maradék (Remnant) Kiértékelés**
A P2 célfüggvény algoritmizálása az újrahasznosítható hulladék maximalizálása érdekében.
* **Virtuális Képalkotás:** A táblára felkerült alkatrészek után megmaradó szabad területek vizuális és geometriai elemzése.
* **Újrahasznosíthatósági Index:** A hulladék besorolása; az algoritmus jelentősen magasabb pontszámmal (értékeléssel) jutalmazza azokat a megoldásokat, ahol a szabad terület egyetlen nagy, konvex vagy téglalap alakú régiót alkot.
* **Guillotine-vágás Támogatása:** Külön prioritást kapnak azok az elrendezések, amelyeknél a maradék végigtolásos (Guillotine) vágással könnyen leválasztható. 

### **Sprint 3.3: Lyukba-ágyazás (Part-in-Part / Swiss Cheese)**
A modern ipari nesting elengedhetetlen funkciójának kialakítása.
* **Dinamikus Felismerés:** A nagyméretű, belső lyukakkal (kivágásokkal) rendelkező alkatrészek belső területeinek automatikus felismerése. 
* **Virtuális Al-táblák (Sub-bins):** Ezeknek a lyukaknak a regisztrálása a rendszerben mint új, beágyazott konténerek (al-táblák).
* **Befűzési Logika:** A keresőmotor felkészítése arra, hogy a kisebb méretű alkatrészeket ezekbe a virtuális al-táblákba fűzze be, maximalizálva az anyagkihozatalt.

---

## **Technikai Elfogadási Kapu 3 (Gate 3: Komplex Integrációs Teszt)**
A következő fázisba lépés szigorú feltételei:
* **Benchmark Tesztek:** Sikeres teljesítés az ESICUP Jakobs1 és Jakobs2 benchmarkokon.
* **Ipari Szimuláció:** Egy több táblát igénylő, ezer alkatrészt meghaladó egyedi gyártási rendelés szimulált szétosztása.
* **Kritérium:** A rendszernek bizonyíthatóan és hibátlanul kell alkalmaznia a Part-in-Part (lyukba-ágyazás) mechanizmust a nagyméretű belső vágatok esetén.