# DXF nesting app – 6) Sparrow futtatás + output parse (részletes)

## 🎯 Funkció

**Cél ebben a fázisban:**
A 5) fázisban legenerált `instance.json` alapján a **sparrow** futtatása (CLI subprocess), majd a kimenetek begyűjtése és a placementek (x, y, rot) visszaolvasása a további lépésekhez (multi-sheet + DXF export).

**Kimenet:**
- `SparrowRunResult`:
  - `placements[]`: instance_id → (x_mm, y_mm, rotation_deg)
  - `bin_used_height_mm` (strip jelleghez)
  - `artifacts_paths`: final.svg, final.json, log
  - `run_stats`: runtime, exit_code, warnings

---

## 🧠 Fejlesztési részletek

### 6.1. Sparrow bináris elérhetőség és verzió rögzítése

**Összefoglaló:**
MVP-ben a leggyakoribb „nem működik” ok: nincs telepítve a sparrow, vagy más verzió van, ami mást vár/ír. Rögzítsd, hogyan találja meg a program.

**Ajánlott megoldás (MVP):**
- `SPARROW_BIN` environment variable (elsőbbség)
- ha nincs, akkor keresés PATH-on: `shutil.which("sparrow")`
- futás elején `sparrow --version` (ha támogatott) és logolás

**Feladatlista:**
- [ ] `core/sparrow_runner.py` modul létrehozása
- [ ] `resolve_sparrow_bin()` implementálása:
  - env → PATH → hiba
- [ ] Verifikáció:
  - futtasd `sparrow --help` vagy `--version` és ellenőrizd exit=0
- [ ] Írd bele a `report.json`-ba: bin path + verzió string

**Kimenet:**
- determinisztikus bináris feloldás

---

### 6.2. Futási parancs és argumentumok összeállítása

**Összefoglaló:**
A sparrow CLI-t paraméterezni kell: input instance, output hely, időlimit, seed, workers. Ezeket egységesen kezeljük.

**Feladatlista:**
- [ ] Definiáld a parancs buildert: `build_sparrow_cmd(instance_path, out_dir, run_cfg)`
- [ ] Paraméterek:
  - input: `instance.json`
  - output: `runs/.../artifacts/` (vagy alt mappa)
  - time limit: `time_limit_s`
  - seed
  - workers/threads
- [ ] (Ha a sparrow-nál nincs minden CLI arg):
  - amit nem tudsz CLI-ből, írd be az input JSON megfelelő részébe (vagy fordítva)
- [ ] Logold a teljes parancsot (shell-escaped formában) a debug logba

**Kimenet:**
- futtatható subprocess parancs

---

### 6.3. Subprocess futtatás (timeout, log capture, exit code)

**Összefoglaló:**
A sparrow futása lehet hosszú. A toolnak meg kell állnia time limitnél, és el kell mentenie a stdout/stderr-t.

**Feladatlista:**
- [ ] `subprocess.run(..., capture_output=True, text=True, timeout=...)`
- [ ] Timeout kezelése:
  - ha timeout: jelöld `status=TIMEOUT`, mentsd a partial logot
- [ ] stdout/stderr mentése:
  - `runs/.../artifacts/sparrow_stdout.log`
  - `runs/.../artifacts/sparrow_stderr.log`
- [ ] Exit code kezelése:
  - 0: OK
  - !=0: error → a kimenet fájlokat akkor is próbáld begyűjteni, ha léteznek

**Kimenet:**
- reprodukálható futás logokkal

---

### 6.4. Kimeneti fájlok felderítése és konvenció

**Összefoglaló:**
A sparrow tipikusan SVG-t és JSON-t ad. MVP-ben rögzíts egy elnevezést, és ha a sparrow más néven ír, keress rá.

**Feladatlista:**
- [ ] Output dir: `runs/.../artifacts/sparrow/`
- [ ] Várt fájlok:
  - `final.json` (placements)
  - `final.svg` (preview)
- [ ] Implementáld a „find output” logikát:
  - ha nincs `final.json`, akkor listázd az out dir fájljait és keress `.json`-t, ami megfelel
  - ugyanez `.svg`-re
- [ ] Ha nem találod:
  - error + sorold a mappa tartalmát a logban

**Kimenet:**
- `final_json_path`, `final_svg_path`

---

### 6.5. Final JSON parse: placements és transzformok kinyerése

**Összefoglaló:**
A multi-sheet és DXF export csak akkor működik, ha pontosan visszakapjuk:
- melyik instance hova került
- milyen rotációval

**Feladatlista:**
- [ ] JSON betöltés: `json.load(open(final_json_path))`
- [ ] Parse logika:
  - items/placements listában keresd az `id`-t (instance_id)
  - a transzformból szedd ki:
    - `translation`: x,y
    - `rotation`: deg (vagy rad → konvert)
- [ ] Egységek:
  - ha rad: `deg = rad * 180/pi`
  - ellenőrizd, hogy mm-ben van-e (MVP-ben feltételezzük igen)
- [ ] Eredmény struktúra:
  - `placements: Dict[str, Placement]`

**Kimenet:**
- placements map/list

---

### 6.6. Bin used height (strip packing) számítása

**Összefoglaló:**
A sparrow strip jelleg miatt fontos mérőszám, hogy a megoldás „mennyi magasságot használ”. Ez kell a 7) multi-sheet wrapper döntéséhez.

**MVP számítás:**
- használd az elhelyezett instance-ek bbox-át (a shape bbox + transzform), és vedd a max Y-t
- `used_height = max(y_max) - bin_min_y`

**Feladatlista:**
- [ ] Tárold minden instance alap bbox-át már a 4/5 fázisban (prepared stats)
- [ ] Placement után számold:
  - `placed_bbox = rotate_bbox_if_needed(...)` (MVP: egyszerű becslés)
  - vagy pontosabb: transzformáld a pontokat és bbox-olj
- [ ] `used_height_mm` számítás
- [ ] Logold: used_height vs board_H

**Kimenet:**
- `bin_used_height_mm`

---

### 6.7. Output sanity check (ütközés, bin-en belüliség) – gyors ellenőrzés

**Összefoglaló:**
MVP-ben is kell egy gyors check, hogy a sparrow nem adott-e hibás elhelyezést (ritka, de előfordulhat rossz inputnál).

**Feladatlista:**
- [ ] Bin-en belüliség:
  - ellenőrizd, hogy a placed bbox a bin bbox-on belül van (gyors)
- [ ] Ütközés:
  - MVP-ben hagyható, mert a motor ezt garantálja, de ha könnyű:
    - 5–10 random párra bbox overlap check (warning)
- [ ] Ha bármi gyanús:
  - warning a reportba

**Kimenet:**
- warningok listája

---

### 6.8. Eredmény csomagolása és report frissítése

**Összefoglaló:**
A runner a következő fázisnak egy tiszta objektumot adjon, és a run reportba írjon mindent.

**Feladatlista:**
- [ ] `SparrowRunResult` dataclass:
  - status (OK/TIMEOUT/ERROR)
  - runtime_s
  - exit_code
  - final_json_path, final_svg_path
  - placements
  - used_height_mm
- [ ] `report.json` bővítése:
  - sparrow bin path + version
  - cmd args
  - runtime
  - used_height
  - placements count
  - stdout/stderr log paths

**Kimenet:**
- tiszta eredmény a 7) multi-sheet wrapperhez

---

## 🧪 Tesztállapot

### Minimum automata tesztek
- [ ] `resolve_sparrow_bin()`:
  - env beállítva → azt használja
  - env nincs → PATH-on keresi
- [ ] Output finder:
  - ha final.json hiányzik, de van 1 json → megtalálja
- [ ] JSON parse:
  - sample final.json → placements map helyes
- [ ] used_height számítás:
  - 2 placement → max y számítás helyes

### Minimum manuális ellenőrzés
- [ ] 1 kicsi demo instance futtatása:
  - létrejön final.svg
  - placements szám megegyezik instance counttal

---

## 🌍 Lokalizáció

Nem kell.

---

## 📎 Kapcsolódások

**Bemenet:** 5) `instance.json`

**Kimenet:**
- 7) multi-sheet wrapper (used_height + placements)
- 8) DXF export (placements)

Megjegyzés: a 6) fázisnál fontos, hogy hiba esetén is megmaradjon minden artefakt (instance.json, stdout/stderr, rész-eredmények), különben a későbbi debug pokol.

