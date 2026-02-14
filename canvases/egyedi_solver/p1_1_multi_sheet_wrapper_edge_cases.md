# canvases/egyedi_solver/p1_1_multi_sheet_wrapper_edge_cases.md

## 🎯 Funkció

A `vrs_nesting/sparrow/multi_sheet_wrapper.py` stabilizálása „éles” edge-case-ekre, hogy a DXF → Sparrow multi-sheet futás **ne legyen törékeny**, és az output **determinista + diagnosztikus** legyen.

Konkrét célok:
- `unplaced[].reason` **normalizálása** (konzisztens okokkal).
- **Determinista** iteráció + kimenet (azonos input + seed → azonos `solver_output.json`).
- **Globális time_limit_s + sheet-enkénti budget** kezelése (ne kapjon minden sheet „teljes” time_limit-et).
- „No progress” helyzetekben **ne hard-crash** legyen az alapértelmezés, hanem kontrollált `partial` + okok (kivéve tényleges futtatási/IO hiba).

## 🧠 Fejlesztési részletek

### 1) Kiinduló állapot (valós kód)
- Multi-sheet wrapper: `vrs_nesting/sparrow/multi_sheet_wrapper.py`
  - jelenleg:
    - sheet-enként `time_limit_s` teljesen ugyanaz (`time_limit_s` → minden sheet), globális budget nincs enforce-olva
    - ha egy sheet-en 0 elhelyezés → **break** (későbbi sheet-ek már nem próbálódnak)
    - `unplaced.reason` mindig `"NO_STOCK_LEFT"`
- Sparrow futtatás: `vrs_nesting/runner/sparrow_runner.py` (`run_sparrow_in_dir(...)`)
- DXF entrypoint: `vrs_nesting/cli.py` (`dxf-run` → `run_multi_sheet_wrapper(...)`)

Repo-aktualis megjegyzes:
- A wrapper jelenleg `source_geometry_map.json`-t is general.
- A `solver_output.status` jelenleg csak `ok|partial`, ezt megtartjuk.

### 2) `unplaced.reason` normalizálás (minimum készlet)
A wrapper a hátralévő példányokra egységesen állítson okot (string).

Javasolt okok:
- `too_large`  
  - a part (bbox) **semmilyen** stock sheet-en nem fér el (figyelem: csak axis-aligned check, a margin/spacing jelenleg nem része a solver_input-nak)
- `invalid_geometry`  
  - hiányzó/hibás shape (pl. nem `simple_polygon`, túl kevés pont, nem numerikus koordináták)
- `timeout`  
  - globális budget elfogyott (wrapper megszakította a további sheet próbákat)
- `no_feasible_position`  
  - minden más eset (fit-elhetne valahova, de a futások után is bent maradt)

**Követelmény:**  
- `unplaced` legyen stabilan rendezett (pl. `part_id`, `instance_id`).
- ne legyen többé fix `"NO_STOCK_LEFT"` mindenre.

### 3) Determinizmus (input-order, stable-sort, output-order)
Implementálandó stabilizálások:
- `remaining` példánylista determinisztikus rendezése (pl. `part_id`, `instance_id`).
- `placements` listát a wrapper a végén determinisztikusan rendezze (pl. `sheet_index`, `part_id`, `instance_id`).
- `unplaced` listát ugyanígy (pl. `part_id`, `instance_id`).
- sheet seed kezelés maradhat `seed + sheet_index`, de a sheet-ek megpróbálása legyen determinisztikus (ne függjön futási időtől/rángástól).

### 4) Időkeret-kezelés: globális + per-sheet budget
Jelenleg: minden sheet a teljes `time_limit_s`-t kapja.

Kívánt:
- A wrapper **előre** ossza ki a globális `time_limit_s`-t sheet-ekre determinisztikusan (pl. egyenletesen, minimum 1s/attempt), és:
  - per sheet a `run_sparrow_in_dir(... time_limit_s=<allocated>)` kapjon budgetet
  - opcionálisan: ha a wall-clock (monotonic) szerint már elfogyott a globális idő, álljon le `partial` + `timeout`

**Minimum DoD**:
- a `sparrow_output.json`-ba bekerülő `runner_meta.time_limit_s` sheet-enként legyen **<= global time_limit_s**
- az összes sheet-re kiosztott budget összege legyen **<= global time_limit_s**
- ne kapjon 0 másodpercet futtatott sheet (ha budget nincs, az adott sheet ne próbálódjon)

Determinista budget policy:
- `time_limit_s` egész másodperces keretből történik kiosztás,
- a futtatott sheet-ek egymás után, stabil sorrendben kapnak budgetet,
- kiosztás: közel egyenletes, maradék az első sheet-ekre.

### 5) „0 placement” / „no progress” kezelése
- Ha egy sheet futás 0 placement-et ad:
  - **ne törje el** automatikusan a teljes folyamatot (ne `break` azonnal),
  - próbálja tovább a következő sheet-et (amíg van budget/sheet),
  - a végén, ha nem lett placement egyáltalán: `status=partial`, minden item `unplaced`, reason alapján.
- A `MultiSheetWrapperError("MULTISHEET_NO_PROGRESS")` csak akkor maradjon hard error, ha:
  - valós IO/protokoll hiba van (pl. hiányzó Sparrow output JSON, parse error, NonZeroExit),
  - nem „normál” no-solution szituáció.

### 6) DXF report.json (opcionális, de hasznos)
`vrs_nesting/cli.py` (`_cmd_dxf_run`) report-jába opcionálisan tegyünk:
- `metrics.unplaced_reasons` (ok → darabszám), a `solver_output.unplaced` alapján

Ez backward compatible (új optional mező).

## 🧪 Tesztállapot

### Új smoke (kötelező)
Hozz létre: `scripts/smoke_multisheet_wrapper_edge_cases.py`, ami:
- minimális, programból épített `sparrow_instance` + `solver_input` alapján meghívja a `run_multi_sheet_wrapper(...)`-t
- ellenőrzi:
  - nem dob kivételt, ha van `invalid_geometry` és `too_large` item
  - `solver_output.status == "partial"`
  - `unplaced` tartalmazza a várt okokat (`invalid_geometry`, `too_large`) legalább 1-1 példánnyal
  - a sheet-enkénti `runner_meta.time_limit_s` (a `sparrow_output.json` raw_outputs-ben) **nem lépi túl** a globális limitet
  - determinisztika: ugyanazzal a seed-del két futás solver_output-ja byte-szinten egyezik (rendezett dump)

### Gate bekötés
- `scripts/check.sh` DXF blokkja alá vedd fel:
  - `python3 scripts/smoke_multisheet_wrapper_edge_cases.py`

### Verify
- `./scripts/verify.sh --report codex/reports/egyedi_solver/p1_1_multi_sheet_wrapper_edge_cases.md` legyen PASS, és generálja a `.verify.log`-ot.

## 🌍 Lokalizáció

N/A (nincs UI-szöveg).  
Ha új reason stringek megjelennek logban/reportban, maradjanak angol snake-case formában (stabil gépi feldolgozáshoz).

## 📎 Kapcsolódások

- Multi-sheet wrapper: `vrs_nesting/sparrow/multi_sheet_wrapper.py`
- Sparrow runner: `vrs_nesting/runner/sparrow_runner.py`
- DXF pipeline entry: `vrs_nesting/cli.py` (`dxf-run`)
- Multi-sheet doksi: `docs/dxf_nesting_app_7_multi_sheet_wrapper_reszletes.md`
- Gate: `scripts/check.sh`, verify wrapper: `scripts/verify.sh`
- Külső tervdoksi (repo-n kívül): `vrs_nesting_mvp_ig_kovetkezo_lepesek_prioritas_szerint.md`
