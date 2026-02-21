# **III. Kockázatelemzés és Mitigációs Stratégiák (The "Pitfalls")**

## **Célkitűzés**
Egy geometriai algoritmusokra épülő irreguláris nesting motor nulláról történő fejlesztése hemzseg az alattomos matematikai és szoftverarchitekturális csapdáktól. Ez a szekció a leggyakoribb, gyakran csak extrém adatterhelésnél jelentkező hibákat és azok kötelező, szigorú mitigációs (elhárítási) eljárásait definiálja.

---

### **1. Lebegőpontos Nem-Determinizmus vs. Skálázott Egészek**
* **A Kockázat:** A klasszikus `f64` (double-precision) lebegőpontos számok használata az ütközésvizsgálatban katasztrofális. Az IEEE 754 szabvány ellenére a különböző hardverarchitektúrák (Intel AVX vs. ARM Neoverse SIMD) vagy fordítói optimalizációk (Fast-Math) eltérő kerekítési hibákat produkálnak. Ez ahhoz vezethet, hogy ami az egyik gépen érintőleges, a másikon átfedést jelez, megbuktatva a P0 kaput és tönkretéve a reprodukálhatóságot.
* **A Mitigáció:** Kötelező architekturális átállás a skálázott egészes (scaled integer, `i64`) reprezentációra. A lépték (scale factor) megválasztása kritikus: ha túl kicsi, a finom részletek elvesznek, ha túl nagy, a terület-számításoknál végzetes túlcsordulás (integer overflow) lép fel. Az iparilag validált beállítás a $10^5$ szorzó alkalmazása, amely 10 mikrométeres ($0.01$ mm) felbontást biztosít a valós térben, biztonságos számítási határokon belül.

### **2. Topológiai Korrupció az Infláció (Felfújás) Során**
* **A Kockázat:** Komplex formájú, éles belső sarkokat vagy apró lyukakat tartalmazó darabok ofszetelésekor (a vágási rés beépítésekor) a poligon topológiája drasztikusan megváltozhat. A kontúr önmagába metszhet (self-intersection), "tüskék" (spikes) képződhetnek, vagy a kis lyukak észrevétlenül eltűnhetnek (collapsed holes). Ha egy lyuk eltűnik, a "Part-in-Part" logika érvénytelen belső területre próbálhat beágyazni egy másik alkatrészt.
* **A Mitigáció:** A Clipper2 beépített `Simplify` funkciójának (amely a Douglas-Peucker algoritmus elveire épít) kötelező meghívása minden inflációs lépés után, tisztítva az önmetsző éleket. Szöglimit (Miter limit) beállítása a tüskék ellen, és egy Validációs Lépés (Topology Check) beiktatása: a névleges és az ofszetelt alkatrész lyukszámának egyeznie kell. A bezáródó lyukakat a nesting motor számára véglegesen hozzáférhetetlenné kell tenni. 

### **3. ARC/SPLINE Diszkretizációs Hibák**
* **A Kockázat:** Ha a parametrikus görbék egyenesekre bontásánál (diszkretizáció) a megengedett húrhiba (chord error) túl nagy, a közelítő egyenes "belóghat" az elméleti görbe alatti területre (under-approximation). Így a nesting motor érvényesnek minősítheti a csonkolt poligont, de a fizikai CNC vágás során az elemek beleharaphatnak egymásba.
* **A Mitigáció:** Szigorúan kifelé kerekítő (outward approximation) görbediszkretizáció alkalmazása. A poligonális burkoknak mindig tartalmazniuk kell az eredeti ívet; így, ha a durvább burkok nem ütköznek (P0 feltétel), a fizikai munkadarabok között is garantáltan megmarad a biztonságos távolság.

### **4. Az "Érintés vs. Átfedés" Éleseset-Politikája**
* **A Kockázat:** Ha két darab éle tökéletesen egybeesik (érintkezik), a metszetük területe matematikailag nulla, ami a valóságban a lézerfej vastagsága miatt selejtet okozhat, ha nincs megfelelően lekezelve.
* **A Mitigáció:** A "Szigorú Biztonsági Oldal" (Strict Safe-Side) politika bevezetése. Mivel az infláció során a biztonsági távolságot és a vágási rést már hozzáadtuk a geometriához, az inflált poligonok "érintkezése" érvényes állapotnak minősül. Azonban kollineáris él-átfedések esetén minden apró, rácsfelbontásból adódó numerikus bizonytalanságot azonnal büntetni kell, és "átfedésként" kell visszautasítani a pozíciót.