# DXF nesting app (házon belüli) – komplett megvalósítási terv (sparrow/jagua-rs)

## 🎯 Funkció

**Cél:** egy kicsi, belső használatú alkalmazás, ami DXF alkatrészeket beolvas, darabszámokat kezel, majd megadott táblaméret(ek)re a lehető legjobb kihasználással kiosztja (nesting), figyelembe véve:
- tábla széltávolság (margin)
- alkatrészek közti min. távolság (spacing / kerf+biztonság)
- forgatási szabályok (0/90/… vagy tetszőleges fok felbontással)
- több tábla (multi-sheet) automatikus kezelése
- mentés DXF-be (táblánként külön DXF)

**Követelmények (a te esetedre optimalizálva):**
- konkáv, íves alkatrészek gyakoriak (DXF ARC/SPLINE → poligonizálás)
- part-in-part (alkatrész a másik alkatrész „lyukába” / kivágott terébe)
- akár finom szögfelbontás (pl. 1–5°)
- stabil, reprodukálható eredmény (seed + config mentés)

**Javasolt alap:**
- Nesting engine: **sparrow** (optimalizáló) + **jagua-rs** (geometria/collision, implicit a sparrow alatt)
- App köré: **Python** (gyors fejlesztés) + `ezdxf` (DXF olvas/ír) + saját konverzió a sparrow JSON formátumára

---

## 🧠 Fejlesztési részletek

### 1) Architektúra (minimál, de bővíthető)

**Három réteg:**
1. **UI/CLI réteg** – projekt konfiguráció, input fájlok, preview, futtatás
2. **Pipeline/Orchestrator** – DXF import → shape-ek → nesting → sheets → DXF export
3. **Core modulok** – DXF parser, poligonizálás, hole-detektálás, JSON generator, export

**Mappa-struktúra (ajánlott):**
- `app/`
  - `ui/` (GUI/CLI)
  - `core/`
    - `dxf_import.py`
    - `geometry.py` (poligonizálás, egyszerűsítés, clean)
    - `nesting.py` (sparrow futtatás, multi-sheet wrapper)
    - `dxf_export.py`
    - `project_model.py` (config + part list)
  - `schemas/` (sparrow input/output JSON schema leírás, saját validátor)
  - `assets/` (ikonok, demo)
- `projects/` (mentett munkák: config + log + output)

### 2) UI/GUI döntés

**Két szintű megoldás (praktikus):**

#### 2.1. MVP: CLI + minimál preview (gyors, stabil)
- Parancs: `nesttool run <project.json>`
- Input mappa: DXF-ek
- Output mappa: `out/sheet_001.dxf`, `out/sheet_002.dxf`, + `report.json`
- Preview: `out/sheet_001.svg` (sparrow natív), opcionálisan PNG konverzió

**Miért jó:** kevesebb hibalehetőség, gyors iteráció, belső használatnál sokszor elég.

#### 2.2. Kényelmes GUI: PySide6 (Qt) – 1 ablak, 3 panel
- **Bal panel:** Alkatrészlista (DXF fájlnév, darabszám, státusz, bounding box, hibák)
- **Közép panel:** Preview (tábla + elhelyezett alkatrészek SVG/Qt render)
- **Jobb panel:** Beállítások (tábla W×H, margin, spacing, rotációk, időlimit, seed)

**GUI funkciók:**
- Drag&drop DXF-ek
- Darabszám szerkesztés (spinner)
- „Run nesting” gomb
- Sheet lapozó (Sheet 1/2/3…)
- „Export DXF” gomb (mappába)
- Hibajelzés: „Nem zárt kontúr”, „Önmetszés”, „Túl kicsi ív-szegmentálás”, stb.

**Javaslat:** kezdj CLI-vel, és csak ha stabil, jöjjön a GUI.

---

## 3) Pipeline – end-to-end adatfolyam

### 3.1. Import (DXF → Part objektum)
**Bemenet:** több DXF fájl, mindegyik egy alkatrész (ideális konvenció), plusz darabszám.

**Lépések DXF-enként:**
1. Olvasás (`ezdxf`)
2. Geometria kinyerés (ajánlott szabály):
   - Outer kontúr layer: `CUT_OUTER`
   - Hole kontúr layer: `CUT_INNER`
   - Ha nincs layer konvenció: heur. (zárt görbék keresése, terület alapján outer=legnagyobb, holes=benne lévők)
3. Ívek/spline-ok poligonizálása toleranciával:
   - `arc_tolerance_mm` (pl. 0.1–0.3mm)
   - cél: zárt polyline pontlisták (outer + holes)
4. Geometria „clean”:
   - duplikált pontok
   - nagyon rövid szakaszok kiszűrése
   - önmetszés ellenőrzés (ha van: javítás/hiba)
5. Part objektum létrehozása:
   - `id`, `name`, `outer_points`, `holes_points[]`, `quantity`, `original_entities_ref`

**Output:** `Part[]`

### 3.2. Nesting input előállítás (Part → sparrow JSON instance)
**Alap paraméterek:**
- `bin` (tábla): W×H
- `margin` (táblaszél): mm
- `spacing` (min distance): mm
- `rotations`:
  - mód A: fix lista (0/90/180/270)
  - mód B: felbontás (pl. 5°) → generált lista 0..355
  - mód C: csak 0/180 (szálirány, mintázat, stb.)
- `time_limit_s` (pl. 30–300s)
- `seed` (reprodukálhatóság)

**Geometriai trükk:**
- A `margin` és `spacing` kombinálása legegyszerűbben:
  - partokat **offseteled** (buffer/outset) a `spacing/2` értékkel,
  - a táblát (bin) pedig **inseteled** `margin + spacing/2` értékkel.
- Így a nesting motor „nulla távolság” mellett is betartja a távolságokat.

**Part-in-part:**
- A holes listát **megtartod**, nem „kitöltöd” – a motor így tudja kihasználni a belső üregeket.

### 3.3. Sparrow futtatás (single sheet / strip)
**Alap:** sparrow strip packing: szélesség fix, „hossz” minimalizál.

**Táblára illesztés stratégia:**
- A strip szélesség = tábla W
- A megoldásból kapott `used_height` ≤ tábla H esetén: 1 tábla kész
- Ha `used_height` > H: multi-sheet wrapper lép életbe

### 3.4. Multi-sheet wrapper (több tábla automatikusan)
**Cél:** a teljes partkészletet több táblára ossza.

**Egyszerű, stabil megoldás (MVP):**
- `remaining_parts` listával dolgozol
- ciklus `sheet_index = 1..`:
  1) futtasd sparrow-t `remaining_parts`-ra
  2) az eredményből vedd ki azokat a part példányokat, amelyek **Y <= H** tartományban elférnek
  3) ezek kerülnek az adott sheet-re, a többiek maradnak `remaining_parts`
  4) stop, ha üres a remaining

**Finomítás (P1):**
- ha a sparrow output nem „sheet-aware”, akkor két mód:
  - (A) futtatás egy nagy H-val, majd szeletelés H-ként (gyors, de suboptimal)
  - (B) iteratív futtatás sheet-enként (jobb, de több futás)

**Stop feltételek:**
- ha egy futásban sem sikerül legalább 1 partot elhelyezni: hiba (valami túl nagy / margin túl nagy / rotáció tiltás)

### 3.5. Export (sheet placements → DXF)
**Elv:** minden input partot „blockként” tárolsz, és sheetenként INSERT-eket raksz be transzformmal.

**Export lépések sheetenként:**
1) új DXF létrehozása
2) tábla keret (opcionális layer `SHEET`)
3) minden part eredeti DXF entitásait add blockba (vagy importáld a már beolvasott entitásokat)
4) placement szerint INSERT:
   - translate (x, y)
   - rotate (deg)
5) layer mapping:
   - CUT_OUTER, CUT_INNER megtartása
   - opcionális: `NEST_INFO` layer szövegek (id, rotation, sheet)

**Export kimenetek:**
- `sheet_001.dxf`, `sheet_002.dxf`, …
- `sheet_001.svg` (sparrow preview) – debug/ellenőrzés
- `report.json`:
  - kihasználtság (%), táblaszám, futási idő, paraméterek, seed

---

## 4) Konfigurációs modell (Project)

**Project JSON:**
- `board`: { `width_mm`, `height_mm`, `margin_mm` }
- `spacing_mm`
- `rotations`: { `mode`: `fixed|step|list`, `step_deg`, `list_deg[]` }
- `quality`: { `arc_tolerance_mm`, `simplify_epsilon_mm` }
- `run`: { `time_limit_s`, `threads`, `seed` }
- `parts`: [ { `path`, `quantity`, `name`, `layer_rules?` } ]
- `output_dir`

**Miért kell:** 1 kattintás/1 parancs újrafuttatni, és ugyanazt kapni.

---

## 5) Hibakezelés és validáció (kritikus)

### 5.1. DXF input ellenőrzések
- nincs zárt kontúr (outer missing) → hiba
- lyuk kontúr outeren kívül → hiba / warning
- önmetsző poligon → hiba + javaslat tolerancia növelés / kontúr javítás
- túl kevés pont ívnél (durva poligonizálás) → warning

### 5.2. Nesting run ellenőrzések
- 0 elhelyezett part → hiba (paraméter/rotáció túl szigorú, vagy part nagyobb mint a bin)
- used_height > H és multi-sheet sem halad → hiba

### 5.3. Export ellenőrzések
- DXF mentés után quick-validate: bounding boxok a táblán belül

---

## 6) Fejlesztési lépések (MVP → P1 → P2)

### MVP (működő, belsős tool)
1) CLI projekt modell + JSON config beolvasás
2) DXF import (outer+holes) layer konvencióval
3) ARC → pontlista poligonizálás toleranciával
4) sparrow input JSON generálás
5) sparrow futtatás (subprocess)
6) 1 sheet export DXF + SVG preview
7) report.json

**Kimenet:** 1 tábla esetén teljes flow.

### P1 (valós gyártási használhatóság)
8) Multi-sheet wrapper (iteratív sheet-képzés)
9) darabszámok UI/CLI támogatása (ugyanaz a part többször)
10) seed + reprodukció (ugyanaz az input → ugyanaz a run)
11) hibák részletes logja (melyik fájl, miért)

### P2 (kényelmi + minőség)
12) GUI (PySide6) + preview panel
13) beépített DXF ellenőrző nézet (outer/holes kiemelés)
14) automata „layer felismerés” fallback (ha nincs konvenció)
15) egyszerű „nest quality” presetek (Fast/Balanced/Best)

---

## 🧪 Tesztállapot

**Automata tesztek (minimum):**
- DXF parser: zárt kontúr felismerés (outer + holes)
- ARC poligonizálás: tolerancia szerint pontszám / zártság
- hole containment: lyuk a külsőben van
- export: transzformok helyesek (rotation + translation)
- multi-sheet: ha H kicsi, több sheet keletkezik, és minden part elhelyezve

**Manual QA checklist:**
- távolságok: margin/spacing betartva (mérhető)
- part-in-part: legalább 1 teszt, ahol lyukba kerül elem
- rotáció: 1–5° lépésnél láthatóan jobb kihasználtság

---

## 🌍 Lokalizáció

Belső tool → alapból EN/HU két nyelv (opcionális):
- paraméter nevek
- hibák/warningok
- report summary

CLI esetén elég angol.

---

## 📎 Kapcsolódások

**Külső engine:**
- sparrow (CLI futtatás) + jagua-rs (alatta)

**Python könyvtárak (javasolt):**
- `ezdxf` – DXF IO
- `shapely` vagy `pyclipper` – offset/validáció (spacing/margin implementáció)
- `numpy` – gyors pontfeldolgozás
- `pydantic` – config/model validáció
- (GUI): `PySide6`

**Kimenetek:**
- DXF sheet-ek
- SVG preview sheet-ek
- JSON report + log

