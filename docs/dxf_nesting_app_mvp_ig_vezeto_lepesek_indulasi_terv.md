# DXF nesting app – hogyan induljunk neki (lépések MVP-ig)

## 🎯 Funkció

**MVP cél:** parancssoros (CLI) eszköz, ami:
1) beolvas több DXF alkatrészt + darabszámokat,
2) paraméterek alapján (táblaméret, margin, spacing, rotációk) nestinget futtat (sparrow),
3) 1 vagy több táblára szétosztja,
4) táblánként DXF-et exportál + SVG preview-t + reportot.

**Kizárások MVP-ben (szándékosan):**
- GUI, interaktív szerkesztés, drag&drop
- automata layer/contour felismerés mindenféle DXF-ből (MVP-ben konvenció kell)
- „tökéletes optimum” (MVP-ben stabilan működjön és gyártásra exportálható legyen)

---

## 🧠 Fejlesztési részletek

### 0) Kiindulási döntések (1 nap)
**Összefoglaló:** rögzítsük a szabályokat, különben a DXF-ek változatossága szétszedi a projektet.

**Döntések:**
- **Input konvenció (kötelező MVP-ben):**
  - 1 DXF = 1 alkatrész
  - outer kontúr layer: `CUT_OUTER`
  - hole kontúr layer: `CUT_INNER`
  - minden kontúr zárt (polyline vagy line/arc lánc, ami zárható)
- **Egység:** mm
- **Rotáció modell:**
  - mód A: step (pl. 5°) → 0..355
  - mód B: fix lista (0/90/180/270)
- **Spacing/margin kezelés:** geometriai offset (part outset + bin inset)
- **Futtatás:** sparrow CLI subprocessből (nem library link)

**Feladatlista:**
- [ ] Írd le és rögzítsd a DXF input szabályt (1 oldal README)
- [ ] Dönts: MVP rotáció alapértelmezés (pl. 5°)
- [ ] Dönts: MVP toleranciák (arc_tolerance 0.2mm, simplify 0.05–0.1mm)

Kimenet:
- `docs/mvp_input_contract.md`

---

### 1) Repo skeleton + futtatható „hello pipeline” (fél nap)
**Összefoglaló:** legyen egy projekt, ami fut, tud configot olvasni, és logol.

**Feladatlista:**
- [ ] Python venv + dependency management (uv/poetry/pip-tools – bármi, de rögzítve)
- [ ] CLI váz (argparse/typer): `nesttool run project.json`
- [ ] Project config modell (pydantic): board, spacing, rotations, parts[]
- [ ] Output dir kezelés: timestampelt run mappa
- [ ] Egységes log: console + `run.log`

Kimenet:
- `nesttool` fut, project.json validálva, üresen is lefut (még nem nestel)

---

### 2) DXF import: kontúrok kinyerése konvencióval (1–2 nap)
**Összefoglaló:** ez az egyik legkritikusabb rész. Először csak a konvenciót támogasd.

**Feladatlista:**
- [ ] `ezdxf` olvasás
- [ ] Entities filter layer alapján (`CUT_OUTER`, `CUT_INNER`)
- [ ] Kontúrok „láncolása”:
  - LINE + ARC elemekből zárt görbe összeállítás (endpoint illesztés toleranciával)
  - Ha LWPOLYLINE zárt: egyszerű
- [ ] Outer/hole kontúr azonosítás:
  - ha több outer: hibázz (MVP)
  - holes: minden zárt kontúr a `CUT_INNER` layerből
- [ ] BBox/terület számítás debughoz
- [ ] Validációk:
  - outer hiányzik → hiba
  - kontúr nem zárt → hiba

Kimenet:
- DXF → `Part{outer, holes}` pontlisták (még ívek nélkül vagy poligonizálva)
- `--debug-export-contours` opció: outer/holes SVG rajz ellenőrzéshez

---

### 3) Ívek/spline-ok poligonizálása + geometria clean (1–2 nap)
**Összefoglaló:** a sparrow/jagua poligonokat szeret. A DXF íveket stabilan poligonizálni kell.

**Feladatlista:**
- [ ] ARC → pontlista mintavétele:
  - tolerancia paraméter (pl. chord error)
  - garantált zárás
- [ ] CIRCLE → pontlista (N szegmens)
- [ ] SPLINE/ELLIPSE (ha előfordul):
  - MVP-ben: próbáld aproximálni; ha nem megy: hiba + file lista
- [ ] Clean:
  - duplikált pontok
  - túl rövid szakaszok (eps)
  - pontszám limit (ne legyen 50k pont / kontúr)
- [ ] (Opcionális MVP-ben) egyszerűsítés epsilon-nal

Kimenet:
- Stabil, zárt poligonok: outer + holes
- `geometry_report.json`: pontszámok, bbox, warnings

---

### 4) Spacing + margin implementáció offsettel (1 nap)
**Összefoglaló:** így lesz garantált a távolság a motor „0 clearance” világában is.

**Feladatlista:**
- [ ] `spacing_mm` kezelése:
  - part outset = spacing/2
- [ ] `margin_mm` kezelése:
  - bin inset = margin + spacing/2
- [ ] Offset könyvtár választás:
  - Shapely buffer vagy PyClipper offset (MVP-ben elég az egyik)
- [ ] Validáció:
  - offset után is legyen érvényes poligon (nem omlik össze)

Kimenet:
- `PartPrepared` poligonok (offsetelve)
- `BinPrepared` (insetelt tábla poligon)

---

### 5) Sparrow input JSON generátor (0.5–1 nap)
**Összefoglaló:** össze kell rakni a sparrow által várt instance JSON-t.

**Feladatlista:**
- [ ] `parts[]` → példányosítás darabszám szerint (vagy quantity mező támogatás, ha a formátum engedi)
- [ ] allowed orientations generálás:
  - `step_deg` → lista
  - `list_deg` → közvetlen
- [ ] seed, time_limit, workers paraméterek
- [ ] input JSON mentése `run/instance.json`
- [ ] JSON validáció (schema vagy saját check)

Kimenet:
- `instance.json` és debug log, hogy hány part példány van

---

### 6) Sparrow futtatás + output parse (0.5–1 nap)
**Összefoglaló:** subprocessből futtatod, kimenetet begyűjtöd, parse-olod a placementeket.

**Feladatlista:**
- [ ] sparrow bináris beállítása (path / bundled)
- [ ] subprocess run:
  - stdout/stderr log mentés
  - time_limit enforced
- [ ] output fájlok kezelése:
  - final SVG
  - final JSON (placements)
- [ ] placements parse:
  - part id → (x, y, rot)
  - used_height számítás

Kimenet:
- `run/sparrow_final.json`, `run/sparrow_final.svg`
- `placements[]` a következő lépéshez

---

### 7) Multi-sheet wrapper (1–2 nap)
**Összefoglaló:** ha nem férnek el egy táblán, osszuk szét több táblára iteratívan.

**Feladatlista:**
- [ ] Loop sheetenként:
  - futtasd sparrow-t remaining set-re
  - válaszd ki azokat, amelyek y+height <= H (tényleges check bbox-alapon)
  - vedd ki őket a remainingből
- [ ] Stop: ha 0 part került sheet-re → hiba (paraméterek túl szigorúak vagy túl nagy elem)
- [ ] Sheet output struktúra:
  - `out/sheet_001/{placements, svg, dxf}`

Kimenet:
- több sheet placements listája
- `report.json`: sheet count, utilization becslés

---

### 8) DXF export táblánként (1–2 nap)
**Összefoglaló:** a gyártás szempontjából ez a másik kritikus rész. A legegyszerűbb stabil export: BLOCK + INSERT.

**Feladatlista:**
- [ ] Input entitások megőrzése partonként (importkor tárold)
- [ ] Part → BLOCK (outer+inner layer marad)
- [ ] Sheet DXF létrehozás:
  - tábla keret (opcionális)
  - INSERT-ek placements szerint (x,y,rot)
- [ ] Ellenőrzés:
  - bbox a binen belül
  - spacing/margin vizuális sanity check

Kimenet:
- `out/sheet_001.dxf`, `out/sheet_002.dxf`, …

---

### 9) MVP zárás: demo készlet + reprodukálható run (0.5–1 nap)
**Összefoglaló:** legyen 3–5 teszt DXF csomag, amivel mindig validálni tudod, hogy nem romlott el.

**Feladatlista:**
- [ ] Demo set:
  - egyszerű konvex
  - konkáv íves
  - part-in-part (outer + nagy hole)
  - több darabszám
- [ ] Dokumentáció:
  - 1 parancsos futtatás
  - paraméter magyarázat
  - tipikus hibák (nem zárt kontúr, túl durva poligonizálás)
- [ ] Reprodukció:
  - seed rögzítése a reportban
  - ugyanaz a config → hasonló eredmény

Kimenet:
- `docs/how_to_run.md`
- `samples/` mappa

---

## 🧪 Tesztállapot (MVP elvárás)

**Minimum automata tesztek:**
- kontúrláncolás zártság
- arc poligonizálás zártság + pontszám
- hole containment
- export transzform (rot/translate)
- multi-sheet: ha H kicsi, több sheet

**Minimum manual QA:**
- 1 DXF csomag valós gyártási előnézetben (pl. QCAD / LibreCAD) megnyitva
- távolságok mérővel ellenőrizve

---

## 🌍 Lokalizáció

MVP-ben nincs. GUI-nál majd.

---

## 📎 Kapcsolódások

**Külső függőségek (MVP):**
- `ezdxf`
- shapely vagy pyclipper
- sparrow bináris (külön telepítve vagy csomagolva)

**Később (P1/P2):**
- PySide6 GUI
- fejlettebb DXF felismerés layer nélkül

