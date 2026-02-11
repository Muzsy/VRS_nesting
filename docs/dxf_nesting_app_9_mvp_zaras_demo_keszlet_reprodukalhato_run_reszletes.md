# DXF nesting app – 9) MVP zárás: demo készlet + reprodukálható run (részletes)

## 🎯 Funkció

**Cél ebben a fázisban:**
Az MVP-t „lezárhatóvá” tenni: legyen egy **demo/teszt készlet**, egy **egy-parancsos futás**, és egy **reprodukálható** (visszakereshető, auditálható) output struktúra.

**MVP akkor kész:**
- adott demo csomagból mindig előáll **DXF sheet output(ok)**
- a run mappában minden artefakt megvan (input, log, instance, final, report)
- legalább minimális automatizált tesztek zöldek
- dokumentált a használat és a tipikus hibahelyzetek

---

## 🧠 Fejlesztési részletek

### 9.1. Demo készlet összeállítása (samples/)

**Összefoglaló:**
Ha nincs fix bemenet, nincs fix regresszióteszt. MVP-hez kell egy kis csomag, ami lefedi a tipikus eseteket.

**Minimum demo tartalom (3–5 alkatrész + mennyiségek):**
- (A) Egyszerű konvex alkatrész (pl. téglalap lekerekítéssel)
- (B) Konkáv íves alkatrész (C alak / csatorna)
- (C) Hole-os alkatrész (outer + 2–5 belső kivágás)
- (D) Part-in-part jelleghez előkészítés:
  - egy nagy outer nagy lyukkal (belső „keret”)
  - egy kicsi alkatrész, ami belefér a lyukba
  - (MVP-ben a nesting motor majd úgyis be tudja tenni, ha a hole geometriát kezeli)
- (E) Darabszám teszt: legalább 1 elem quantity=10

**Feladatlista:**
- [ ] `samples/parts/` alá tedd be a DXF-eket a szerződés szerint (`CUT_OUTER`, `CUT_INNER`)
- [ ] Készíts `samples/project_demo.json`-t:
  - board méret (pl. 1500×3000)
  - margin/spacing
  - rotations (pl. step=5)
  - run seed/time_limit
  - parts list + quantity
- [ ] Adj hozzá `samples/README.md`-t:
  - mit tesztel az adott DXF

**Kimenet:**
- stabil demo input csomag

---

### 9.2. Reprodukálható run szabályok rögzítése

**Összefoglaló:**
Belső használatnál a legfontosabb: ha „ez tegnap jó volt”, ma is ugyanúgy vissza tudd nézni. Ehhez seed + input snapshot + hash kell.

**MVP szabályok:**
- minden run kap timestamp mappát
- a run mappába **kimásolod** a project.json-t (normalizált változatban)
- a run mappába **elmented** az instance.json-t (sheetenként)
- `instance_hash` bekerül a reportba
- a sparrow bináris útvonala és verziója bekerül a reportba

**Feladatlista:**
- [ ] `runner.py` végén mindig írd ki a run summary-t (console):
  - run dir
  - sheet count
  - output dxf-ek
- [ ] `report.json` mezők:
  - started_at, finished_at
  - app version (git commit hash, ha van)
  - sparrow bin path + version
  - project_config_hash
  - per sheet: instance_hash, final_json_path, final_svg_path, used_height
- [ ] Implementáld a hash-eket:
  - sha256 a JSON canonical formára (sorted keys)

**Kimenet:**
- teljesen auditálható run

---

### 9.3. „One command” futtatás (make target / bash script)

**Összefoglaló:**
Ha az indítás bonyolult, nem fogod használni. MVP-hez 1 parancs kell, ami végigmegy.

**Feladatlista:**
- [ ] Adj egy egyszerű scriptet:
  - `./run_demo.sh` vagy `make demo`
- [ ] A script:
  - aktiválja a venv-et (vagy kiírja, hogy aktiváld)
  - futtatja: `nesttool run samples/project_demo.json`
  - a végén kiírja az output könyvtárat

**Kimenet:**
- 1 parancsos demó

---

### 9.4. Minimális automatizált tesztcsomag (smoke + core)

**Összefoglaló:**
Nem kell full CI, de minimum legyen zöld:
- config validáció
- DXF import alap esetei
- poligonizálás zártság
- offset/inset működik
- instance.json generálható

**Feladatlista:**
- [ ] `tests/test_cli_smoke.py`:
  - `--dry-run` lefut
- [ ] `tests/test_dxf_import.py`:
  - 1 sample DXF outer+inner → PartRaw ok
- [ ] `tests/test_discretization.py`:
  - arc/circle poligonizálás zárt
- [ ] `tests/test_offset.py`:
  - bin inset nem üres
  - part offset valid
- [ ] (Opcionális) `tests/test_instance_json.py`:
  - rotations count
  - instance count

**Kimenet:**
- `pytest` zöld, legalább alap szinten

---

### 9.5. Dokumentáció: használat, paraméterek, hibák

**Összefoglaló:**
A tool addig használható, amíg a dokumentáció a valóságot írja. MVP-hez rövid, konkrét leírás kell.

**Doksi minimum:**
- telepítés (venv + pip install)
- futtatás (run parancs példák)
- project.json magyarázata (mezők + példák)
- DXF input contract (layer, zárt kontúrok)
- tipikus hibák (error code-ok és megoldás)

**Feladatlista:**
- [ ] `README.md` frissítése:
  - Quickstart
  - Demo run
  - Output struktúra
- [ ] `docs/` minimum:
  - `mvp_input_contract.md`
  - `clearance_model.md`
  - `rotations.md`
  - `dxf_export_contract.md`
  - `troubleshooting.md`
- [ ] `troubleshooting.md` tartalom:
  - hiba kód → ok → javítás (konkrét)

**Kimenet:**
- használható belső tool dokumentáció

---

### 9.6. Kimenetek manuális QA checkliste (gyártási szemmel)

**Összefoglaló:**
A végén a DXF-eket valósan is meg kell nézni. MVP-hez kell egy rövid QA lista.

**Feladatlista:**
- [ ] Nyisd meg `out/sheet_001.dxf`-et QCAD/LibreCAD-ben:
  - layer-ek megvannak
  - geometriák a táblán belül
  - rotációk nem fordítottak
- [ ] Mérj meg 2–3 távolságot:
  - part-part spacing >= spacing_mm
  - part-edge >= margin_mm
- [ ] Nyisd meg a cél CAM szoftverben:
  - blockref elfogadott-e (ha nem: export_exploded)
- [ ] `final.svg` vizuális sanity check

**Kimenet:**
- kipipálható QA

---

### 9.7. Verziózás és release címke (belső használatra)

**Összefoglaló:**
Még ha házon belüli is, kell tudni: „melyik builddel készült ez a DXF?”

**Feladatlista:**
- [ ] `__version__` a csomagban (pl. `0.1.0`)
- [ ] Reportba írd bele:
  - app version
  - git commit hash (ha repo)
- [ ] (Opcionális) tag: `mvp-0.1.0`

**Kimenet:**
- visszakereshető verzió

---

### 9.8. MVP acceptance kritériumok (kőkemény lista)

**Összefoglaló:**
Itt húzod meg a vonalat: mi az, ami késznek számít.

**Feladatlista / kritériumok:**
- [ ] `./run_demo.sh` lefut hiba nélkül
- [ ] Kijön legalább 1 DXF sheet (ha kell, több)
- [ ] `runs/.../report.json` tartalmaz:
  - instance hash(ek)
  - sparrow verzió
  - sheet count + per-sheet used_height
- [ ] `out/sheet_XXX.dxf` megnyitható QCAD/LibreCAD-ben
- [ ] spacing és margin szemre és mérésre rendben
- [ ] `pytest` zöld (minimum tesztek)

**Kimenet:**
- lezárható MVP

---

## 🧪 Tesztállapot

Ebben a fázisban a cél nem új logika, hanem a stabilitás:
- demo futtatás mindig siker
- regressziók kiszűrhetők

---

## 🌍 Lokalizáció

Nem kell.

---

## 📎 Kapcsolódások

Ez a fázis lezárja az MVP-t, és előkészíti a következőket (ha később kell):
- P1: GUI (PySide6), drag&drop, vizuális preview
- P1: per-part rotáció tiltás, part priority
- P2: „true” part-in-part optimalizálás (hole-aware scoring, advanced placement)

Megjegyzés: ha a demo készlet nincs rendben (layer, zártság), az egész MVP folyamatosan false negatív hibákat fog dobni. A demo DXF-eket ezért érdemes „kézzel” rendbe rakni egyszer, és azt tekinteni arany standardnak.

