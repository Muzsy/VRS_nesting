# DXF nesting app – 2) DXF import: kontúrok kinyerése konvencióval (részletes)

## 🎯 Funkció

**Cél ebben a fázisban:** DXF fájlból stabilan kinyerni az alkatrész(ek) vágandó kontúrjait az MVP input szerződés szerint:
- outer kontúr layer: `CUT_OUTER` (pontosan 1 zárt kontúr)
- hole kontúrok layer: `CUT_INNER` (0..n zárt kontúr)

**Kimenet:** minden DXF-hez egy `PartRaw` objektum:
- `outer_path`: görbe szegmensek listája (LINE/ARC/POLYLINE normalizált formában)
- `holes_paths[]`: ugyanilyen lista
- `source_entities`: az eredeti DXF entitások referenciája/exporthoz
- `warnings/errors`

**MVP fókusz:** konvencióval működjön megbízhatóan. Automata felismerés (layer nélkül) később.

---

## 🧠 Fejlesztési részletek

### 2.1. DXF olvasás és dokument meta (units, rétegek, modelspace)

**Összefoglaló:**
A DXF-et be kell olvasni és ki kell szedni a modell térből (modelspace) azokat az entitásokat, amelyek a vágást adják. A későbbi hibakereséshez érdemes kiírni a DXF metaadatokat (unit, réteglista, entity count).

**Feladatlista:**
- [ ] `ezdxf.readfile(path)` beolvasás
- [ ] `msp = doc.modelspace()`
- [ ] Gyűjts metaadatokat:
  - file path, file size
  - doc units (ha elérhető)
  - layer nevek listája
  - entity type stat (LINE/ARC/LWPOLYLINE/… darabszám)
- [ ] Logold `--debug` módban a fenti összegzést

**Kimenet:**
- `DxfMeta` (debughoz) + tovább a 2.2-re

---

### 2.2. Entitások szűrése layer alapján (CUT_OUTER / CUT_INNER)

**Összefoglaló:**
MVP-ben nem találgatunk. Csak a megadott layer-ek érdekelnek. Minden más ignore.

**Feladatlista:**
- [ ] Szűrd az entitásokat:
  - `outer_entities = [e for e in msp if e.dxf.layer == "CUT_OUTER"]`
  - `inner_entities = [e for e in msp if e.dxf.layer == "CUT_INNER"]`
- [ ] Ismeretlen/tiltott típusok:
  - ha outer/inner layeren TEXT/DIMENSION/HATCH van → warning vagy error (MVP-ben inkább error)
- [ ] Ha `outer_entities` üres → hiba

**Kimenet:**
- két nyers lista: outer_entities, inner_entities

---

### 2.3. Normalizált „szegmens” reprezentáció kialakítása (LINE/ARC/POLYLINE → Segment)

**Összefoglaló:**
A későbbi láncoláshoz egységes belső formátum kell. Nem az ezdxf entitásokkal dolgozunk közvetlenül.

**Segment típusok (MVP):**
- `LineSeg(p0, p1)`
- `ArcSeg(center, radius, start_angle, end_angle, ccw=True)`
- `PolySeg(points[], closed_flag, bulge_support?)`

**Feladatlista:**
- [ ] LINE → LineSeg (start/end)
- [ ] ARC → ArcSeg (center/radius/start/end)
- [ ] CIRCLE → ArcSeg (0..360) vagy külön CircleSeg (de később úgyis poligon)
- [ ] LWPOLYLINE:
  - ha van bulge: döntés (MVP-ben vagy támogatod, vagy előírod, hogy nincs bulge)
  - points listát add vissza, zárt-e
- [ ] POLYLINE (régi): kezeld mint LWPOLYLINE

**Kimenet:**
- `outer_segments[]`, `inner_segments[]`

---

### 2.4. Kontúrok összeállítása (chaining): sok szegmens → zárt path(ok)

**Összefoglaló:**
DXF-ben gyakori, hogy a kontúr nem egy darab zárt polyline, hanem több LINE/ARC elem láncolata. Össze kell őket fűzni.

**Alap elv:**
- minden segmentnek van start/end pontja
- a szegmenseket úgy fűzöd össze, hogy az aktuális end ponthoz a legközelebbi start/end illeszkedjen (toleranciával)
- ha fordítva kell: a segmentet megfordítod (LINE-nál swap; ARC-nál start/end csere + ccw flip)

**Paraméterek:**
- `endpoint_tol_mm` (pl. 0.05–0.2mm)

**Feladatlista:**
- [ ] Írj `segment_endpoints(seg)` függvényt
- [ ] Írj `reverse_segment(seg)` függvényt (LINE/ARC)
- [ ] Írj `chain_segments(segments, tol) -> list[Path]`:
  - válassz egy kezdő szegmenst
  - iterálj: keress következőt, ami illeszkedik
  - ha nincs: path vége
  - ha end ≈ start (tol) és path hossza >=2 → zárt
  - jelöld a path állapotát (closed/open)
- [ ] Sebesség:
  - MVP-ben elég O(n^2), de implementálj pont-indexet (grid/hash) ha kell

**Kimenet:**
- `outer_paths[]` és `inner_paths[]` ahol Path = szegmensek listája + closed flag

---

### 2.5. Outer/hole validáció (MVP szigor)

**Összefoglaló:**
Az MVP-ben inkább álljunk meg hibával, mint hogy csendben rosszat vágjunk.

**Szabályok:**
- outer_paths: **pontosan 1 db**
- outer path: **zárt**
- inner_paths: mind zárt (különben hiba)
- inner path-oknak az outer-en belül kell lenniük (containment check később poligon szinten; ebben a fázisban elég bbox check + warning)

**Feladatlista:**
- [ ] Ha outer_paths != 1 → hiba (listázd a talált pathok számát)
- [ ] Ha outer open → hiba
- [ ] Ha bármely inner open → hiba
- [ ] BBox számítás pathokra (gyors)
- [ ] Inner bbox containment: ha inner bbox nincs outer bbox-on belül → warning/error

**Kimenet:**
- validált `PartRaw` (még nem poligon)

---

### 2.6. Eredeti entitások megőrzése exporthoz (source capture)

**Összefoglaló:**
DXF exportnál a cél az, hogy az alkatrész eredeti entitásai megmaradjanak (outer+inner). Ehhez importkor el kell tenni a referenciákat/rekonstrukcióhoz szükséges adatot.

**Feladatlista:**
- [ ] Tárold el az outer+inner entitásokat „nyersen” (deep copy vagy serializable leírás)
- [ ] Rögzítsd a layer neveket (hogy exportnál ugyanoda kerüljön)
- [ ] Adj minden partnak stabil `part_id`-t (pl. fájlnév hash)

**Kimenet:**
- `PartSource` struktúra exporthoz

---

### 2.7. Debug eszközök: kontúr export SVG/JSON (erősen ajánlott)

**Összefoglaló:**
A kontúr-kivonás hibái vizuálisan derülnek ki a leggyorsabban. MVP-ben kell egy debug export.

**Feladatlista:**
- [ ] `--debug-export-contours` flag
- [ ] Export:
  - `runs/.../debug/part_<id>_outer.svg`
  - `runs/.../debug/part_<id>_holes.svg`
  - `runs/.../debug/part_<id>.json` (pontok/szegmensek)
- [ ] SVG-ben jelöld:
  - outer vastag
  - holes vékony
  - start pont marker (piros pont)

**Kimenet:**
- gyors vizuális verifikáció minden DXF-re

---

### 2.8. Hibakatalógus (standard üzenetek)

**Összefoglaló:**
A felhasználó (te) akkor tud gyorsan javítani a DXF-en, ha a hiba üzenet konkrét.

**Feladatlista:**
- [ ] Standard error codes (MVP):
  - `DXF_NO_OUTER_LAYER`
  - `DXF_MULTIPLE_OUTERS`
  - `DXF_OPEN_OUTER_PATH`
  - `DXF_OPEN_INNER_PATH`
  - `DXF_UNSUPPORTED_ENTITY_TYPE`
  - `DXF_CHAINING_GAP_TOO_LARGE`
- [ ] Minden hibához add meg:
  - file path
  - layer
  - entity type
  - javaslat (pl. „zárd le a polyline-t”, „tedd outer-t CUT_OUTER layerre”)

**Kimenet:**
- értelmes, reprodukálható hibák

---

## 🧪 Tesztállapot

### Minimum automata tesztek
- [ ] 1 egyszerű DXF: 1 zárt LWPOLYLINE outer, 1 zárt inner → 1 PartRaw, 1 hole
- [ ] DXF: outer LINE láncból → chaining zár
- [ ] DXF: open outer → hiba
- [ ] DXF: inner open → hiba

### Minimum manuális ellenőrzés
- [ ] 2–3 valós DXF a te készletedből lefut, debug SVG-n kontúrok helyesek

---

## 🌍 Lokalizáció

Nem kell.

---

## 📎 Kapcsolódások

Ez a modul közvetlen inputja a következő fázisnak:
- 3) poligonizálás és geometria clean

Fontos: a 2) fázis *még nem* poligonizál. Csak biztosítja, hogy a kontúrok helyesen ki vannak szedve és zártak.

