# DXF nesting app – 7) Multi-sheet wrapper (részletes)

## 🎯 Funkció

**Cél ebben a fázisban:**
Ha az összes alkatrész nem fér el egy táblán (W×H), akkor a rendszer automatikusan ossza szét **több táblára** úgy, hogy:
- minden darabszám (instance) elhelyezésre kerüljön,
- táblánként kapjunk placements listát (x, y, rot),
- a folyamat stabilan megálljon, ha valami nem elhelyezhető.

**MVP elv:** egyszerű, determinisztikus, könnyen debugolható wrapper a sparrow köré.

**Kimenet:**
- `SheetsResult`:
  - `sheets[]`: { `index`, `placements[]`, `used_height_mm`, `svg_path`, `final_json_path` }
  - `unplaced_instances[]` (ha hiba)
  - `summary`: sheet_count, total_instances

---

## 🧠 Fejlesztési részletek

### 7.1. Multi-sheet probléma modell és döntés: hogyan használjuk a strip packing outputot?

**Összefoglaló:**
A sparrow alapból strip packing szemléletű (fix szélesség, magasság minimalizálás). A táblád fix H, ezért wrapper kell.

**MVP stratégia:** iteratív „csomagolás” táblánként:
1) futtasd sparrow-t a **remaining** instance halmazra,
2) válaszd ki azokat az instance-eket, amelyek **beleférnek** az adott tábla H-jába,
3) ez lesz a sheet N,
4) vedd ki őket a remainingből,
5) ismételd, amíg üres.

**Miért működik:**
- nem kell a sparrow-t módosítani
- a legnehezebb rész a fit-ellenőrzés (lásd 7.4)

**Feladatlista:**
- [ ] Rögzítsd a wrapper célját és korlátait (nem garantál globális optimumot)
- [ ] Döntsd el: a sparrow-t minden sheetnél külön futtatod (MVP: igen)

**Kimenet:**
- tiszta wrapper koncepció

---

### 7.2. Wrapper loop vezérlése (sheetenkénti iteráció)

**Összefoglaló:**
Ez a vezérlő ciklus felel a több táblás szétosztásért.

**Feladatlista:**
- [ ] Bemenet:
  - `prepared_bin` (insetelt)
  - `prepared_parts` (offsetelt)
  - `part_instances` (példányosítva)
  - `run_cfg` (time_limit, seed, workers)
- [ ] Állapotváltozók:
  - `remaining_instances` (list/dict)
  - `sheets = []`
  - `sheet_index = 1`
- [ ] Ciklus:
  - while remaining nem üres:
    1) build instance.json csak a remaining-re
    2) sparrow run (6)
    3) select „fits this sheet” instances
    4) ha 0 fit → hard error (7.6)
    5) ments sheet eredmény
    6) remaining = remaining - fits
    7) sheet_index++

**Kimenet:**
- sheetenként elkülönített futások

---

### 7.3. Artefakt szerkezet táblánként (runs output rendezése)

**Összefoglaló:**
Több sheet esetén külön mappába kell menteni mindent, hogy debugolható legyen.

**Feladatlista:**
- [ ] Run mappán belül:
  - `out/sheet_001/`
  - `out/sheet_002/`
  - …
- [ ] Sheet mappában tárold:
  - `instance.json` (csak a remaining set inputja)
  - `sparrow_final.json`
  - `sparrow_final.svg`
  - `sparrow_stdout.log`, `sparrow_stderr.log`
  - később: `sheet_XXX.dxf`
- [ ] Report összesítés:
  - sheet_count
  - per-sheet used_height

**Kimenet:**
- átlátható artefakt struktúra

---

### 7.4. Fit-ellenőrzés: mely instance-ek férnek bele a tábla fix H-jába?

**Összefoglaló:**
Ez a wrapper „szíve”. A sparrow ad placements-et, de nekünk dönteni kell: belefér-e a tábla H-jába.

**MVP ajánlott módszer (robosztus): pontos bbox a transzformált pontokból**
- Minden instance-hez ismered a **shape pontjait** (outer+holes) a prepared geometriából.
- A placement transzform:
  - forgatás (deg)
  - eltolás (x,y)
- Transzformáld a **külső ring pontjait**, számolj bbox-ot.
- Beleférés:
  - `bbox.min_y >= bin_bbox.min_y` és `bbox.max_y <= bin_bbox.min_y + H_inset`

**Miért jó:**
- a rotációt pontosan kezeli
- nem kell bonyolult rotált bbox képlet

**Feladatlista:**
- [ ] Tárold az instance-hez a referenciát a shape outer pontlistára
- [ ] Implementáld `transform_points(points, x, y, rot_deg)`
- [ ] Implementáld `bbox_of_points(points)`
- [ ] Implementáld `fits_sheet(instance_id, placement, prepared_bin, board_H_inset)`:
  - transzformált outer pontok bbox-a
  - check max_y <= bin_max_y (bin insetelt téglalap esetén egyszerű)
- [ ] Teljesítmény:
  - MVP-ben oké (pár ezer pont × instance)
  - optimalizálás később: cache rotált pontok rotációnként

**Kimenet:**
- `fits_instances` halmaz sheetenként

---

### 7.5. Sheet placements kivágása: teljes sparrow outputból csak a fit instance-ek

**Összefoglaló:**
A sparrow output minden remaining instance-et elhelyez valahol a stripen. A sheetre csak azokat visszük át, amik beleférnek a fix H-ba.

**Feladatlista:**
- [ ] `fits_ids` meghatározása (7.4)
- [ ] `sheet_placements = [p for p in placements if p.instance_id in fits_ids]`
- [ ] `unplaced_for_this_sheet = remaining - fits_ids`
- [ ] `used_height_mm` a sheetre:
  - max_y a sheet_placements transzformált bbox-aiból
- [ ] Mentés:
  - `sheet_XXX_placements.json` (saját, egyszerű lista)

**Kimenet:**
- sheet placements lista

---

### 7.6. Hard error szabályok (amikor meg kell állni)

**Összefoglaló:**
Az iteráció el tud akadni. Ezt gyorsan és érthetően kell kezelni.

**Hard error esetek:**
- egy sparrow run után `fits_ids` üres → nem sikerült egy darabot sem H-ba tenni
- a remaining-ben van olyan instance, ami soha nem fér be (bbox > bin)

**Feladatlista:**
- [ ] Ha `fits_ids` üres:
  - készíts diagnózist:
    - listázd a remaining top 10 legnagyobb bbox-át
    - írd ki a bin méretet (inset)
    - javaslat: növeld H-t vagy csökkents margin/spacing, engedj rotációt
  - állj meg `MULTISHEET_NO_PROGRESS` hibával
- [ ] Ha van „never fits” instance:
  - állj meg `PART_NEVER_FITS_BIN`

**Kimenet:**
- értelmes megállás, nem végtelen ciklus

---

### 7.7. Determinisztika és seed kezelés sheetenként

**Összefoglaló:**
Több futás lesz. Ha mindegyikben más seed van, akkor minden futás más lesz. MVP-ben legyen stabil.

**MVP szabály:**
- alap seed = project seed
- sheetenként származtatott seed:
  - `seed_sheet = seed_base + sheet_index` (egyszerű)

**Feladatlista:**
- [ ] Implementáld a seed deriválást
- [ ] Írd bele sheet reportba

**Kimenet:**
- reprodukálható multi-sheet run

---

### 7.8. Időlimit stratégia (time budget) multi-sheet esetén

**Összefoglaló:**
Ha 10 tábla kell, és mindegyik 60s, akkor 10 perc. MVP-ben kell kontroll.

**MVP opciók:**
- (A) fix `time_limit_s` per sheet
- (B) globális time budget, amit elosztasz (P1)

**Feladatlista:**
- [ ] MVP-ben válaszd (A): per sheet limit
- [ ] Logold a teljes futási időt és sheetek számát
- [ ] Opcionális `max_sheets` paraméter (védelem)

**Kimenet:**
- kontrollált futási idő

---

### 7.9. Wrapper report és metrikák (kihasználtság, sheet szám)

**Összefoglaló:**
A usernek látni kell: hány tábla lett, mennyire van kihasználva.

**MVP metrikák:**
- `sheet_count`
- `used_height_mm` sheetenként
- `area_utilization_estimate` (durva): sum(part_area) / (W_inset*H_inset*sheet_count)

**Feladatlista:**
- [ ] Számold a total part area-t (prepared geometry alapján)
- [ ] Számold a bin inset area-t
- [ ] Írd a reportba:
  - per-sheet: placements_count, used_height
  - összesen: sheet_count, total_instances

**Kimenet:**
- `report.json` multi-sheet résszel

---

## 🧪 Tesztállapot

### Minimum automata tesztek
- [ ] Kényszer több sheet:
  - kis H mellett 2+ sheet jön ki
- [ ] No progress:
  - olyan input, ahol egy part túl magas → `fits_ids` üres → hiba
- [ ] Fits check:
  - rotált shape pontokból számolt bbox alapján helyes döntés
- [ ] Seed deriválás:
  - ugyanaz a project seed → ugyanaz a sheet felosztás (nagyjából)

### Minimum manuális ellenőrzés
- [ ] 1 valós készlet (pl. 1500×3000) és mesterségesen 1500×800:
  - több sheet keletkezik
  - minden instance elhelyezve

---

## 🌍 Lokalizáció

Nem kell.

---

## 📎 Kapcsolódások

**Bemenet:**
- 4) PreparedBin + PreparedPart[]
- 5) instance generátor (sheetenként)
- 6) sparrow futás + placements

**Kimenet:**
- 8) DXF export sheetenként (placements listák)

Megjegyzés: a multi-sheet wrapper minősége nagyban függ a fit-ellenőrzéstől. Ha csak egyszerű bbox-ot használsz rotáció nélkül, fals pozitív/negatív jöhet. MVP-ben ezért javasolt a pontok transzformálása és abból bbox-olás.

