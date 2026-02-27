# DXF nesting app – 4) Spacing + margin implementáció offsettel (részletes)

## 🎯 Funkció

**Cél ebben a fázisban:**
A 3) lépésből kapott érvényes poligonokat úgy alakítani, hogy a nesting motor automatikusan betartsa:
- **tábla szélétől** a `margin_mm` távolságot,
- **alkatrészek egymástól** a `spacing_mm` távolságot.

**MVP stratégia:** geometriai offset (buffer/offset) – így a motor „0 clearance” elhelyezést végezhet, mégis garantált a távolság.

**Kimenet:**
- `PreparedBin`: a tabla hasznalhato terulete (`bin_offset` alapjan modositott bin outer + akadalyok)
- `PreparedPart`: offsetelt part poligon (outer+holes), nestingre kész

---

## 🧠 Fejlesztési részletek

### 4.1. Paraméterek és modellezés rögzítése

**Összefoglaló:**
A spacing és margin sokféleképpen értelmezhető. Itt egyértelműen rögzítjük:
- `margin_mm`: minimális távolság a part *vágandó kontúrja* és a tábla külső széle között
- `spacing_mm`: minimális távolság a két part *vágandó kontúrjai* között

**MVP képlet (ajanlott):**
- `inflate_delta = spacing_mm / 2`
- `bin_offset = spacing_mm / 2 - margin_mm`
- **Part**: `offset_out(part, inflate_delta)`
- **Bin outer**: `offset(bin_outer, bin_offset)` (negativ = deflate, pozitiv = inflate)
- **Stock hole/defect akadaly**: `offset_out(hole, inflate_delta)`

Ezzel ket part kozott legalabb `spacing_mm` marad, mikozben a part-bin edge tavolsag `margin_mm` marad.
Kotelezoen tamogatott eset: `margin_mm < spacing_mm/2` (ilyenkor a bin outer kifele no).

**Feladatlista:**
- [ ] Dokumentáld a képletet és jelentését (`docs/clearance_model.md`)
- [ ] Validáld: `spacing_mm >= 0`, `margin_mm >= 0`
- [ ] Definiáld az offset jellegét:
  - join style: round (íves sarkok), miter, bevel (MVP: round a legbiztosabb)

**Kimenet:**
- `ClearanceModel` (konfig + leírás)

---

### 4.2. Offset engine kiválasztása (Shapely vs PyClipper)

**Összefoglaló:**
A stabil offset a nesting egyik legkényesebb pontja. Két reális opció:

**A) Shapely**
- egyszerű `buffer(distance)`
- van `cap_style`/`join_style`
- jó validációs eszközök (`is_valid`)

**B) PyClipper**
- gyors és stabil integer alapú offset
- skálázni kell (mm → int)
- join típusok jól kontrollálhatók

**MVP ajánlás:**
- ha már használsz Shapely-t validációra: **Shapely buffer**
- ha sok edge case és stabilitás kell: **PyClipper**

**Feladatlista:**
- [ ] Döntsd el: Shapely vagy PyClipper legyen az MVP-ben
- [ ] Írj egy egységes API-t: `offset_polygon(polygon, dist_mm, mode=out/in)`
- [ ] Ha PyClipper:
  - válassz skálát (pl. 1000: 0.001mm felbontás)

**Kimenet:**
- `core/offset.py` (1 jól tesztelt függvény)

---

### 4.3. Tabla (bin) poligon letrehozasa es bin_offset alkalmazasa

**Osszefoglalo:**
A tabla alapbol egy teglalap. Ebbol keszitunk egy poligont, majd a `bin_offset` szerint modositjuk.

**Lépések:**
1) `bin_rect = [(0,0), (W,0), (W,H), (0,H)]`
2) `bin_offset = spacing/2 - margin`
3) `bin_usable_outer = offset(bin_rect, bin_offset)` (negativ = befele, pozitiv = kifele)
4) Validacio: ne legyen ures / tul kicsi

**Feladatlista:**
- [ ] Készíts bin téglalap poligont mm-ben
- [ ] Szamold: `inflate_delta = spacing/2`, `bin_offset = spacing/2 - margin`
- [ ] Alkalmazd a `bin_offset`-ot a bin outer konturra (pozitiv esetben is)
- [ ] Ellenőrzések:
  - ha tul nagy negativ `bin_offset` miatt invertalodna, determinisztikus clamp kell (`max >= min`)
  - minimális méret: pl. width/height > 0
- [ ] Add vissza a `PreparedBin`-t:
  - polygon pontlisták
  - bbox

**Kimenet:**
- `PreparedBin`

---

### 4.4. Part offset: outer kifelé, holes befelé (kritikus)

**Összefoglaló:**
Egy lyukas poligon offsetelése nem csak annyi, hogy „buffer”. A helyes clearance model:
- outer kontúr **kifelé** tolódik `d`-vel
- hole kontúrok **befelé** tolódnak `d`-vel (mert a vágandó anyag maradék része csökken)

A legtöbb geometriai könyvtár ezt automatikusan kezeli, ha a poligon outer+holes szerkezetben van és a ringek iránya helyes.

**Feladatlista:**
- [ ] Győződj meg róla, hogy a 3) lépésben a ringek iránya konzisztens (outer CCW, holes CW)
- [ ] Építs `Polygon(outer, holes)` objektumot (Shapely) vagy megfelelő struktúrát (PyClipper)
- [ ] Számold `d = spacing/2`
- [ ] `part_offset = buffer(+d)` (Shapely) vagy Clipper offset +d
- [ ] Hole összeomlás kezelése:
  - ha egy hole a befelé tolás miatt eltűnik (összezár), az OK lehet
  - de ha a hole „átfordul” vagy invalid lesz: hiba/warning (MVP-ben inkább hiba)

**Kimenet:**
- `PreparedPart` poligon (outer + holes) offsetelve

---

### 4.5. Érvényesség és degenerációk kezelése

**Összefoglaló:**
Offset után gyakori problémák:
- poligon invalid (self-intersection)
- poligon szétesik több komponensre (MultiPolygon)
- nagyon vékony részek eltűnnek

MVP-ben a cél: vagy stabilan kezeljük, vagy konkrét hibával megállunk.

**Feladatlista:**
- [ ] Validáld `part_offset.is_valid`
- [ ] Ha MultiPolygon:
  - MVP opció A: hiba (mert a part szétesett)
  - MVP opció B: válaszd a legnagyobb komponenst + warning (csak ha biztos)
- [ ] Minimum area threshold:
  - ha area túl kicsi → hiba
- [ ] Logold az offset előtti/utáni statokat:
  - point count, area, bbox

**Kimenet:**
- stabil `PreparedPart` vagy konkrét hiba

---

### 4.6. Bin containment sanity check (gyors előszűrés)

**Összefoglaló:**
Mielőtt nestinget futtatnál, érdemes gyorsan megmondani, ha valami soha nem fér be:
- part bbox nagyobb mint a bin bbox

Ez sok időt spórol és jobb hibát ad.

**Feladatlista:**
- [ ] Számold a part bbox-ot (offset után)
- [ ] Ha bbox_w > bin_w vagy bbox_h > bin_h:
  - hiba: „Part never fits”
  - javaslat: margin/spacing csökkentés, rotáció engedélyezés, nagyobb tábla
- [ ] (Opcionális) több rotáció esetén bbox rotációval változik – MVP-ben elég a 0° bbox check + warning

**Kimenet:**
- korai, érthető hiba

---

### 4.7. Debug export (offset előtte/utána) – kötelező eszköz

**Összefoglaló:**
Ha az offset rossz, a nesting „furcsán” fog viselkedni. Azonnal látni kell.

**Feladatlista:**
- [ ] Exportáld SVG-be:
  - eredeti part geometria (3) kimenet
  - offsetelt part geometria (4) kimenet
  - `bin_offset` alapjan modositott bin geometria
- [ ] Fájlok:
  - `runs/.../debug/bin_offset.svg`
  - `runs/.../debug/part_<id>_before_offset.svg`
  - `runs/.../debug/part_<id>_after_offset.svg`
- [ ] Jelöld a távolságot (opcionális): egyszerűen csak a két kontúr eltérése látszódjon

**Kimenet:**
- gyors vizuális ellenőrzés

---

### 4.8. API tervezés: mit ad vissza a modul a nestinghez?

**Összefoglaló:**
A nesting modulnak nem kell tudnia semmit a margin/spacing képletről – csak megkapja a kész poligonokat.

**Ajánlott adatszerkezetek:**
- `PreparedBin`:
  - `polygon_points` (outer ring)
  - `bbox`, `width`, `height`
- `PreparedPart`:
  - `id`, `name`
  - `outer_points`, `holes_points[]`
  - `quantity`
  - `stats` (area, bbox)

**Feladatlista:**
- [ ] Definiáld a `prepared_model.py`-t
- [ ] Írj konverziót shapely/pyclipper → pontlisták
- [ ] Garancia: minden ring zárt, nincs duplikált utolsó pont (vagy egységesen kezeld)

**Kimenet:**
- tiszta interface a 5) Sparrow JSON generátor felé

---

## 🧪 Tesztállapot

### Minimum automata tesztek
- [ ] Bin offset:
  - W=1500, H=3000, margin=10, spacing=2 -> `bin_offset=-9`, usable outer merete csokken
  - W=1500, H=3000, margin=0.5, spacing=2 -> `bin_offset=+0.5`, usable outer merete no
  - tul nagy negativ `bin_offset` eseten determiniztikus clamp (`max>=min`)
- [ ] Part offset:
  - egyszerű négyzet + d → bbox nő d*2-vel
  - lyukas négyzet: hole terület csökken
- [ ] Validáció:
  - offsetelt poligon `is_valid`
- [ ] MultiPolygon eset:
  - vékony „C” alak offset után széteshet → elvárt viselkedés (hiba vagy largest)

### Minimum manuális ellenőrzés
- [ ] 2–3 valós alkatrész (konkáv íves) offset előtte/utána SVG-n szemre helyes

---

## 🌍 Lokalizáció

Nem kell.

---

## 📎 Kapcsolódások

**Bemenet:** 3) `PartGeom`

**Kimenet:** 5) Sparrow input JSON generátor `PreparedBin` + `PreparedPart[]`

Megjegyzés: ha itt instabil az offset, a nesting eredmények értelmetlenek lesznek. Ezért a validáció + debug export nem opcionális.
