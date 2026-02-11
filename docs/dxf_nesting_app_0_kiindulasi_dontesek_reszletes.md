# DXF nesting app – 0) Kiindulási döntések (részletes)

## 🎯 Funkció

**Ennek a fázisnak a célja:** a projekt elején *kőbe vésni* azokat a döntéseket, amik nélkül a DXF-ek varianciája miatt a fejlesztés szétesik.

**Kimenet:** 1–2 rövid dokumentum + 1 minta project config + 1 minta DXF-csomag (2–3 alkatrész), amivel az MVP végig tesztelhető.

---

## 🧠 Fejlesztési részletek

### 0.1. Döntés: DXF input szerződés (kötelező konvenció MVP-ben)

**Összefoglaló:**
A DXF világban a legnagyobb kockázat, hogy nincs egységes jelölés a *külső kontúr*, *belső lyukak*, *gravírozás*, *segédvonalak* között. MVP-hez ezért kötelező egy input szerződés. Ha ezt nem rögzíted, a parser lesz a projekt 80%-a.

**Döntendők:**
- 1 fájl = 1 alkatrész **(MVP kötelező)**
- Layer konvenció:
  - `CUT_OUTER`: a vágandó külső kontúr (pontosan 1 db)
  - `CUT_INNER`: vágandó belső kontúrok (0..n)
  - opcionális később: `ETCH`, `MARK`, `IGNORE`
- Kontúr jelleg:
  - zárt görbe kell: LWPOLYLINE zárt vagy LINE/ARC lánc zárható
  - nincs önmetszés (ha van: hiba)
- Egység: mm

**Feladatlista:**
- [ ] Írd le 1 oldalban az input szerződést: `docs/mvp_input_contract.md`
- [ ] Adj példákat: mi számít outernek / holenek / mi kerül ignore-ba
- [ ] Rögzíts „tiltott” elemeket MVP-ben (pl. text, dimension, hatch) → ignore vagy hiba
- [ ] Definiáld a toleranciákat a láncoláshoz (endpoint merge tol, pl. 0.05–0.2 mm)

**Kimenet:**
- `docs/mvp_input_contract.md`

---

### 0.2. Döntés: Mértékegység, koordinátarendszer, alapértelmezett origó

**Összefoglaló:**
DXF-ben a koordináta abszolút, az egység néha nincs rendesen beállítva. Rögzíteni kell, hogy mit tekintünk mm-nek, és hogyan normalizáljuk a shape-eket (origó, irány, CW/CCW), különben exportnál elcsúszik.

**Döntendők:**
- Minden belső számítás **mm-ben**
- Importkor normalizálás:
  - part koordináták eltolása úgy, hogy a part bbox bal-alsó sarka (0,0) közelébe kerüljön
  - CW/CCW irány egységesítése (outer vs holes)
- Board koordináta:
  - board origó (0,0) bal-alsó
  - X jobbra, Y felfelé

**Feladatlista:**
- [ ] Rögzítsd a mm feltételezést és a fallback-et, ha DXF unit hiányzik
- [ ] Döntsd el: ha DXF unit inch → konvertálsz-e MVP-ben (ajánlott: igen, de minimum warning)
- [ ] Írd le a normalizálást (bbox shift, orientation)

**Kimenet:**
- `docs/coordinate_system.md` (rövid)

---

### 0.3. Döntés: Íves geometriák kezelése (poligonizálás szabályai)

**Összefoglaló:**
A sparrow/jagua poligonokat eszik. A DXF ARC/CIRCLE/SPLINE ezért *mintavételezve* pontlistává alakul. A mintavételezés túl durva → rossz kihasználtság / ütközési hibák. Túl finom → lassú és instabil offset.

**Döntendők (MVP default javaslat):**
- `arc_tolerance_mm` (chord error): 0.2 mm (gyártási igény szerint 0.1–0.3)
- max pontszám kontúronként: pl. 5000 (védelem)
- SPLINE/ELLIPSE:
  - MVP: approximáljuk, ha lehetséges
  - ha nem: hiba + listázás (ne csendben elrontsa)

**Feladatlista:**
- [ ] Válaszd ki a default toleranciát (0.2mm jó kiindulás)
- [ ] Rögzítsd a „min segment count” szabályt körre/ívre (pl. minimum 24 pont körön)
- [ ] Definiáld a „too complex” fallback-et (warning + simplify)

**Kimenet:**
- `docs/curve_discretization.md`

---

### 0.4. Döntés: Spacing + margin matematikai modell (hogyan garantáljuk a távolságot)

**Összefoglaló:**
A távolságtartást két helyen kell betartani:
- tábla szélétől (margin)
- alkatrészek egymástól (spacing)

A legstabilabb MVP-út: **geometriai offset**.
- partot kifelé offseteled `spacing/2`-vel
- a táblát befelé inseteled `margin + spacing/2`-vel

Ezzel a nesting motor már „0 clearance” mellett is betartja a távolságot.

**Döntendők:**
- Offset engine: Shapely buffer vagy PyClipper offset
- Mit csinálsz, ha offset után a shape érvénytelen (összeomlik):
  - hiba (MVP)
  - vagy automata tolerancia növelés (P1)

**Feladatlista:**
- [ ] Válaszd ki az offset könyvtárat (MVP-ben 1 legyen)
- [ ] Rögzítsd a képletet margin/spacing-re
- [ ] Írd le a validációt: offset után is legyen érvényes poligon

**Kimenet:**
- `docs/clearance_model.md`

---

### 0.5. Döntés: Forgatási modell (diszkrét szögek, „tetszőleges” közelítése)

**Összefoglaló:**
A „tetszőleges” forgatás a gyakorlatban diszkrét mintavétel.
A túl sok szög értékelése drága, ezért MVP-ben kell egy ésszerű default.

**Döntendők:**
- Rotáció módok:
  - `fixed`: [0, 90, 180, 270]
  - `step`: pl. 5° (0..355)
  - `list`: kézzel megadott
- Default: `step=5°` (jó kompromisszum)
- Opcionális: „grain lock” mód (csak 0/180)

**Feladatlista:**
- [ ] Rögzítsd a defaultot (5°)
- [ ] Döntsd el a max szögszámot (pl. 360 fölé ne engedd)
- [ ] Dokumentáld a tradeoff-ot: több szög = jobb lehet, de lassabb

**Kimenet:**
- `docs/rotations.md`

---

### 0.6. Döntés: Multi-sheet stratégia (MVP-ben egyszerű wrapper)

**Összefoglaló:**
A sparrow strip packing jellegű. Táblázásra MVP-ben egy iteratív wrapper a legegyszerűbb:
- futtasd a remaining set-re
- vedd ki ami belefér H-ba
- ismételd, amíg elfogy

**Döntendők:**
- Elférés feltétel: bbox (gyors) vs pontos poligon (drágább)
  - MVP: bbox elég, ha clearance offset már megtörtént
- Stop szabály: ha 0 elem kerül sheetre → hiba

**Feladatlista:**
- [ ] Írd le az MVP multi-sheet algoritmust
- [ ] Rögzítsd a stop/hard error feltételeket
- [ ] Definiálj report metrikákat (sheet count, utilization becslés)

**Kimenet:**
- `docs/multisheet_mvp.md`

---

### 0.7. Döntés: Sparrow futtatási mód + reprodukálhatóság

**Összefoglaló:**
Ha belső termelésre kell, ugyanaz a bemenet ne adjon teljesen más eredményt „véletlenül”. Ehhez seed + config mentés kell.

**Döntendők:**
- sparrow futtatás: CLI subprocess (MVP)
- Paraméterek:
  - time limit (pl. 60s default)
  - workers/threads (pl. CPU cores)
  - seed (default fix, de állítható)
- Output: minden run mentése mappába (input instance.json + final.json + svg + log)

**Feladatlista:**
- [ ] Definiálj default time limitet (pl. 60s)
- [ ] Rögzítsd a seed kezelést (explicit a projectben)
- [ ] Mappaszerkezet: `runs/YYYYMMDD_HHMMSS/…`

**Kimenet:**
- `docs/run_reproducibility.md`

---

### 0.8. Döntés: DXF export forma (BLOCK+INSERT, layer mapping)

**Összefoglaló:**
Exportnál a legbiztosabb, ha a part eredeti geometriáját változatlanul megőrzöd, és csak transzformálod.
Erre a DXF-ben a BLOCK+INSERT a stabil út.

**Döntendők:**
- output: 1 sheet = 1 DXF
- layer mapping:
  - vágás layer-ek megtartása
  - opcionális info layer (id, rotation)
- tábla keret rajzolása: default off (opcionális)

**Feladatlista:**
- [ ] Rögzítsd a DXF export szabályt (BLOCK+INSERT)
- [ ] Definiálj layer mappinget
- [ ] Döntsd el: exportálunk-e tábla keretet (opcionális)

**Kimenet:**
- `docs/dxf_export_contract.md`

---

### 0.9. Döntés: MVP project config séma + minta

**Összefoglaló:**
MVP-ben a felhasználói felület egy `project.json`. Ha nincs jó séma, később fáj.

**Döntendők:**
- Kötelező mezők:
  - board: W/H/margin
  - spacing
  - rotations (mode + step/list)
  - parts: path + quantity
  - quality: arc_tolerance
  - run: time_limit + seed

**Feladatlista:**
- [ ] Írd meg a `project.schema.json`-t (vagy pydantic modelt)
- [ ] Adj `samples/project_example.json`-t
- [ ] Adj 2–3 DXF sample-t a szerződés szerint

**Kimenet:**
- `samples/project_example.json`
- `samples/parts/*.dxf`

---

## 🧪 Tesztállapot

Ebben a fázisban még nincs kód, de legyen **validációs csomag**:
- 1 konvex egyszerű
- 1 konkáv íves
- 1 part-in-part (outer + nagy hole)

És mindegyik megfelel a layer szerződésnek.

---

## 🌍 Lokalizáció

Nem kell.

---

## 📎 Kapcsolódások

A döntések közvetlenül befolyásolják:
- DXF import implementáció bonyolultsága
- poligonizálás pontossága
- offset stabilitás
- multi-sheet logika
- export reprodukálhatóság

