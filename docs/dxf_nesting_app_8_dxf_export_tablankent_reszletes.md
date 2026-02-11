# DXF nesting app – 8) DXF export táblánként (részletes)

## 🎯 Funkció

**Cél ebben a fázisban:**
A 7) fázis `sheets[]` placement listái alapján **táblánként DXF-et exportálni**, olyan formában, amit a lézervágó előtti CAM/vezérlő szoftver stabilan be tud olvasni.

**MVP export elv:**
- **1 sheet = 1 DXF**
- alkatrészek geometriája **változatlanul megőrzött** (az eredeti DXF entitásokból)
- elhelyezés csak **transzform** (translate + rotate)
- implementáció: **BLOCK + INSERT** (DXF best practice)

**Kimenet:**
- `out/sheet_001.dxf`, `out/sheet_002.dxf`, …
- opcionális: `out/sheet_001_map.json` (instance_id → block_name + transform)

---

## 🧠 Fejlesztési részletek

### 8.1. Export célformátum és konvenciók rögzítése

**Összefoglaló:**
MVP-ben egyszerű, következetes DXF kell. Ha túl sok „okoskodás” van (layer átnevezés, entitás átalakítás), a kompatibilitás romlik.

**MVP döntések:**
- DXF verzió: pl. `R2010` (általában jó kompatibilitás)
- Unit: mm (ha a DXF-ben állítható)
- Layer-ek:
  - tartsd meg az eredeti `CUT_OUTER` és `CUT_INNER` layer-eket a part blokkon belül
  - opcionális extra layer: `NEST_INFO` (szöveg/azonosítók)
- Sheet keret:
  - opcionális, alapból OFF (sok CAM nem szereti, ha „plusz vágás”)

**Feladatlista:**
- [ ] Rögzítsd az export konvenciót a doksiba (`docs/dxf_export_contract.md`)
- [ ] Döntsd el a DXF verziót és unit beállítást

**Kimenet:**
- stabil export szabályrendszer

---

### 8.2. Part forrásgeometria előkészítése exporthoz (BLOCK tartalom)

**Összefoglaló:**
A 2) fázisban elmentettük a part eredeti entitásait (outer+inner). Most ebből készítünk DXF BLOCK-ot.

**Kulcs elv:**
- a BLOCK *lokális koordinátában* legyen (part saját origója)
- a nesting placement csak INSERT transform (x,y,rot)

**Feladatlista:**
- [ ] Definiáld a `PartSource` adatszerkezetet (ha még nincs):
  - `part_id`, `name`
  - `entities_outer[]`, `entities_inner[]` (ezdxf entity másolat vagy serializable leírás)
  - `base_transform` (ha importkor normalizáltál)
- [ ] Döntsd el: importkor normalizáltad-e a part origót (bbox min → 0,0)
  - ha igen: a BLOCK is így épüljön
- [ ] Implementáld `build_part_block(doc, part_source) -> block_name`
  - add hozzá a part entitásait a block layoutba
  - tartsd meg a layer-eket

**Kimenet:**
- block-ok létrejönnek a kimeneti DXF-ben

---

### 8.3. Block név- és ID-stratégia (ütközésmentesen)

**Összefoglaló:**
Ha több part van, és több sheet, a block neveknek stabilnak és ütközésmentesnek kell lenniük.

**MVP javaslat:**
- block name: `P_<part_id_short>` (pl. fájlnév hash 8 karakter)

**Feladatlista:**
- [ ] Írj `make_block_name(part_id) -> str` függvényt
- [ ] Garantáld az egyediséget (set check)
- [ ] Logold a block mappinget debug módban

**Kimenet:**
- stabil block mapping

---

### 8.4. Sheet DXF létrehozása és beállításai

**Összefoglaló:**
Sheetenként új DXF dokumentumot hozunk létre, beállítjuk az alap layer-eket, majd beillesztjük (INSERT) a blockokat.

**Feladatlista:**
- [ ] `ezdxf.new(dxfversion="R2010")`
- [ ] Unit beállítás (ha elérhető API-val)
- [ ] Layer-ek létrehozása (ha nem léteznek):
  - `CUT_OUTER`, `CUT_INNER`, `NEST_INFO` (opcionális)
- [ ] `msp = doc.modelspace()`

**Kimenet:**
- üres, de jól konfigurált sheet DXF

---

### 8.5. Placement → INSERT transzform (x,y,rot) alkalmazása

**Összefoglaló:**
A placementek sheetenként instance szinten vannak: instance_id → (x, y, rot). Ezekből INSERT-ek lesznek.

**Fontos:**
- a (x,y) a nesting bin koordinátában van
- a rot a part lokális origója körül értendő

**Feladatlista:**
- [ ] Készíts `insert_part(msp, block_name, x_mm, y_mm, rot_deg)`:
  - `msp.add_blockref(block_name, insert=(x, y))`
  - `blockref.dxf.rotation = rot_deg`
- [ ] Ha szükséges, kezelj scale-t (MVP: 1.0)
- [ ] Győződj meg róla, hogy a rotáció előjele helyes (CW/CCW) – ha fordítva: invert
- [ ] Minden INSERT-hez opcionális attribútum:
  - instance_id, part_name (NEST_INFO layer textként, nem BLOCK attribútumként MVP-ben)

**Kimenet:**
- modelspace tele INSERT-ekkel

---

### 8.6. Opcionális: NEST_INFO feliratok (debug/gyártási jelölés)

**Összefoglaló:**
Belső használatnál sokat segít, ha minden part mellé odaírjuk az ID-t. De ez néha zavarja a CAM-et. Ezért legyen kapcsolható.

**Feladatlista:**
- [ ] Config flag: `export_labels: true/false`
- [ ] Ha true:
  - `msp.add_text(f"{part_name}", dxfattribs={"layer":"NEST_INFO"}).set_pos((x, y))`
  - pozíció: a part bbox sarka mellé (bbox számításból)
- [ ] Font height mm-ben (pl. 5–10mm)

**Kimenet:**
- kapcsolható jelölések

---

### 8.7. Opcionális: Sheet keret rajzolása (külön layer, alapból OFF)

**Összefoglaló:**
A tábla keret vizuális debughoz jó, de gyártásnál problémás lehet, ha vágásként értelmeződik.

**Feladatlista:**
- [ ] Config flag: `export_sheet_frame: true/false`
- [ ] Ha true:
  - rajzolj téglalapot `SHEET_FRAME` layerre
  - külön szín/linetype (ha kell)
- [ ] Alapból OFF

**Kimenet:**
- opcionális keret

---

### 8.8. Validáció export után (gyors QA)

**Összefoglaló:**
MVP-ben minimum ellenőrizni kell, hogy semmi nem lóg ki a táblából. A spacing/margin elvileg az offset miatt garantált, de a transzform hibák mindent elronthatnak.

**Feladatlista:**
- [ ] Számold ki minden instance transzformált outer bbox-át (7.4 módszer)
- [ ] Ellenőrizd:
  - bbox min_x/min_y >= bin_min
  - bbox max_x/max_y <= bin_max
- [ ] Ha bármelyik kilóg:
  - jelöld `export_validation_failed` a reportban
  - írd ki a konkrét instance_id-t és mennyit lóg ki

**Kimenet:**
- export sanity check

---

### 8.9. Mentés és fájlnév konvenció (több sheet)

**Összefoglaló:**
A fájlnevek legyenek rendezhetők és egyértelműek.

**Feladatlista:**
- [ ] Fájlnév:
  - `sheet_001.dxf`, `sheet_002.dxf` … (zero padding)
- [ ] Mentsd:
  - `doc.saveas(path)`
- [ ] Írj mellé `sheet_001_map.json`-t:
  - instance_id → part_id, block_name, x,y,rot

**Kimenet:**
- rendezett outputok

---

### 8.10. Gyártási kompatibilitás „escape hatch” (ha valami CAM nem szereti a BLOCK-ot)

**Összefoglaló:**
Van olyan CAM, ami furcsán kezeli a blockref-et. B tervként legyen egy „explode blocks” export opció.

**Feladatlista:**
- [ ] Config flag: `export_exploded: true/false` (default false)
- [ ] Ha true:
  - blockref „feloldása” (transform + entitás másolás a modelspace-be)
  - blockref törlés
- [ ] Dokumentáld, hogy ez lassabb és nagyobb DXF-et ad

**Kimenet:**
- kompatibilitási mód

---

## 🧪 Tesztállapot

### Minimum automata tesztek
- [ ] BLOCK név egyediség
- [ ] INSERT rotáció beállítás
- [ ] Map.json tartalom helyes
- [ ] Export validáció: kilógó elem → jelzett hiba

### Minimum manuális ellenőrzés
- [ ] Nyisd meg LibreCAD/QCAD-ben:
  - layer-ek rendben
  - alkatrészek helyükön
  - rotáció helyes irányban
- [ ] Nyisd meg a cél CAM szoftverben (ha van): beolvassa-e a blockref-et

---

## 🌍 Lokalizáció

Nem kell.

---

## 📎 Kapcsolódások

**Bemenet:**
- 7) `SheetsResult` placements sheetenként
- 2) `PartSource` (eredeti entitások)

**Kimenet:**
- `out/sheet_XXX.dxf` fájlok

Megjegyzés: ha a part origó normalizálás nincs jól kezelve (import vs export), az egész layout elcsúszik. Ezért a part lokális koordináta és az INSERT transzform definícióját rögzítsd, és tartsd végig konzisztensen.

