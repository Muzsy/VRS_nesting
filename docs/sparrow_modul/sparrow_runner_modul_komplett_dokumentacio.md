# Sparrow runner modul – komplett dokumentáció

> Cél: a Sparrow (Rust CLI) determinisztikus, reprodukálható futtatása, az összes futási artifact (input snapshot, logok, outputok) rögzítése, és a kimenet minimál (de szigorú) ellenőrzése, hogy a pipeline következő lépései stabilan tudjanak rá építeni.

---

## 🎯 Funkció

### Mit csinál a modul?
A **Sparrow runner** egy “thin orchestration” réteg a Sparrow CLI köré.

**Feladatai (IN-scope):**
- Sparrow futtatása **subprocess**-ből, fix **seed** + **time limit** paraméterekkel.
- **Run directory** létrehozása és karbantartása (reprodukálhatóság).
- Input instance JSON **snapshotolása** a run mappába.
- Sparrow stdout/stderr **naplózása fájlba**.
- Sparrow output fájlok (final JSON + final SVG) **megtalálása** és rögzítése.
- Output **minimál parse** (strip_width, density, placed_items count) és visszaadása.
- Opcionálisan a kimenet **validálása** (pl. a `scripts/validate_sparrow_io.py` meghívásával).

**Nem feladata (OUT-scope):**
- DXF import, geometriakinyerés, poligonizálás
- kerf/spacing/margin offset (kompenzáció)
- Sparrow input JSON generálás (generator modul dolga)
- multi-sheet wrapper stratégia (külön modul)
- DXF export táblánként

### Bemenetek
- **instance JSON path**: Sparrow/Jagua kompatibilis input (`name`, `items[]`, `strip_height`, stb.)
- Runner paraméterek:
  - `sparrow_bin` (útvonal, vagy PATH-ban lévő parancs)
  - `seed` (int)
  - `time_limit_s` (int)
  - `run_root` vagy `run_dir` (artifactok tárolásához)
  - `validate` (bool)

### Kimenetek
- **RunResult** (struktúrált objektum / dict):
  - `run_dir`
  - `instance_snapshot_path`
  - `stdout_log_path`, `stderr_log_path`
  - `final_json_path`, `final_svg_path` (ha elérhető)
  - `return_code`, `duration_sec`
  - `strip_width`, `density`, `placed_count`
  - `warnings` (pl. “final svg nem található”, “fallback final_*.json alapján azonosítva”)

---

## 🧠 Fejlesztési részletek

## 1) Könyvtár- és fájlszerkezet (best practice)

### Javasolt modul elhelyezés
- `vrs_nesting/runner/sparrow_runner.py`
- `vrs_nesting/runner/__init__.py`

### Javasolt run artifact struktúra
Minden futás egyedi run mappába kerül:

- `runs/<run_id>/`
  - `instance.json` *(snapshot; az a pontos input, amit lefuttattunk)*
  - `sparrow_stdout.log`
  - `sparrow_stderr.log`
  - `runner_meta.json` *(runner által írt meta; seed, timelimit, sparrow_bin, commit/verzió, timestamps)*
  - `output/`
    - `final_<name>.json`
    - `final_<name>.svg`

**Miért így?**
- Reprodukció: minden futás önálló, később is újrafuttatható ugyanazzal az inputtal.
- Debug: output és logok egy helyen.
- CI: artifactként feltölthető.


## 2) Determinizmus és reprodukálhatóság

### Determinisztikus futás feltételei
- `seed` explicit megadása (pl. `-s 0`).
- `time_limit_s` explicit megadása (pl. `-t 60`).
- Sparrow verzió/commit **rögzítése** (CI-ben különösen fontos).

### Kötelező meta a `runner_meta.json`-ban
- `timestamp_utc` (ISO-8601)
- `seed`, `time_limit_s`
- `sparrow_bin` (abs path)
- `sparrow_version` vagy `sparrow_commit` (ha elérhető)
- `input_sha256` (a snapshotolt instance.json hash-e)


## 3) Sparrow futtatás (subprocess best practice)

### Parancs összeállítása
- `sparrow -i <instance.json> -t <time_limit_s> -s <seed>`

### `cwd` kezelés
**Best practice:** a Sparrow-t **a run_dir-ben** futtasd (`cwd=run_dir`).
- Így a Sparrow által írt relatív `output/…` mappa a futáshoz kötődik.
- Elkerülöd, hogy több párhuzamos futás összekeverje az outputokat.

### Timeout stratégia
- Runner oldali timeout: `time_limit_s + grace` (pl. +10s)
- Grace célja: ha Sparrow befejezésnél flushol vagy fájlt ír, ne vágd le túl korán.

### Exit code és hibatípusok
- `return_code != 0`: hiba → logok kötelezően csatolva legyenek (stdout/stderr).
- Timeout: külön error (pl. `SparrowTimeoutError`).


## 4) Output felderítés (robosztus mód)

### Elsődleges
- Input `name` mező alapján: `output/final_<name>.json` és `.svg`

### Fallback
Ha a név eltér vagy a Sparrow más néven írja:
- keress `output/final_*.json`
- válaszd a **legfrissebb** fájlt (mtime alapján)

### Kötelező ellenőrzések
- `final_json_path` létezzen
- JSON parse-olható legyen
- `solution.layout.placed_items` létezzen (ha nem, akkor rossz output formátum)


## 5) Output minimál parse (stabil “contract”)

A runner nem “értelmez” mélyen, de kiszedi a legfontosabb metrikákat:
- `strip_width`
- `density`
- `placed_count = len(placed_items)`

**Miért hasznos?**
- gyors sanity check
- riportolás
- multi-sheet wrapper későbbi döntéseihez (pl. “elfér-e a fix táblán?”)


## 6) Opcionális validáció (best practice)

### Mikor validáljunk?
- POC/CI esetén **mindig** (hard fail)
- Lokális gyors iterálásnál kapcsolható

### Hogyan validáljunk?
- Két opció:
  1) Runner meghívja a meglévő `scripts/validate_sparrow_io.py` scriptet (subprocess).
  2) Runnerbe beépíted a validátort (később).

**Követelmény:** validáció failure esetén a runner **nem ad PASS-t**, és a logok/artefaktok maradjanak a run_dir-ben.


## 7) Logging és diagnosztika

### Kötelező logok
- `sparrow_stdout.log`
- `sparrow_stderr.log`

### Javasolt runner log üzenetek (console)
- run_dir
- sparrow_bin
- seed, time_limit_s
- final_json_path
- strip_width, density, placed_count

### Hibák esetén minimum információ
- visszatérési kód / timeout
- final output hiányzik-e
- log fájlok helye


## 8) Biztonság és “hardening”

### Input biztonság
- A runner **nem** futtasson ismeretlen binárist automatikusan.
- `sparrow_bin` legyen explicit paraméter vagy config.
- Tilos a shell string futtatás (ne `shell=True`).

### Fájlírás
- A run_dir létrehozása legyen atomikus, és ne írjon felül meglévő futást.
- Ha már létezik run_id, generáljon új run_id-t.

### Párhuzamos futások
- CWD-vel run_dir-re izolált futtatás.
- Ne használj globális `output/` könyvtárat repo gyökérben.


## 9) Konfiguráció (best practice)

### Környezeti változók (opcionális)
- `SPARROW_BIN`: Sparrow bin abs path
- `SPARROW_TIME_LIMIT_S`: default timelimit
- `SPARROW_SEED`: default seed

### CLI interface (ajánlott)
A runner modulnak legyen egy kicsi CLI-ja, hogy CI-ben és lokálisan is egységesen hívd:
- `python -m vrs_nesting.runner.sparrow_runner --input <instance.json> --run-root runs --seed 0 --time-limit 60 --validate`


## 10) Hibakezelési szerződés

### Javasolt kivétel típusok
- `SparrowRunnerError` (base)
- `SparrowBinaryNotFoundError`
- `SparrowTimeoutError`
- `SparrowNonZeroExitError`
- `SparrowOutputNotFoundError`
- `SparrowOutputParseError`

### Elv
- Hibánál **ne** töröld a run_dir-t. Pont az kell debughoz.


## 11) Platform kompatibilitás

- Linux (CI + dev) az elsődleges.
- Sparrow bináris elérhetőség:
  - CI-ben buildeld (`cargo build --release`) és használd abs path-tal.
  - Lokálisan: PATH vagy `SPARROW_BIN`.


## 12) Teljesítmény (best practice)

- `time_limit_s` legyen kontrollált (CI-ben rövid, lokálisan nagyobb lehet).
- A runner ne végezzen “nehéz geometriát”; csak futtat + parse.


---

## 🧪 Tesztállapot

### Kötelező smoke tesztek
1) **Golden IO smoke test** (már kész):
- input: `poc/sparrow_io/swim.json`
- futtatás + validálás: PASS

2) **Runner unit/integration test javaslatok**
- **Unit**: output JSON parse (strip_width, density, placed_count) a `poc/sparrow_io/final_swim.json` fixture-ből.
- **Integration**: CI-ben Sparrow build + runner futtatás + validáció.

### CI best practice
- Failure esetén töltsd fel artifactként:
  - `runs/<run_id>/**`
  - különösen: `output/final_*.json`, `output/final_*.svg`, `sparrow_*.log`


---

## 🌍 Lokalizáció

- A runner modul **belső eszköz**: alapértelmezett log/hibaüzenetek lehetnek **angolul** (dev/CI kompatibilitás) vagy magyarul (csapat preferencia).
- Best practice: hibaüzenetek rövidek, konkrétak; a részletek a logfájlokban.


---

## 📎 Kapcsolódások

### Kapcsolódó komponensek a pipeline-ban
- **Sparrow input generator**: előállítja az instance JSON-t (runner ezt kapja).
- **Output parser**: a final JSON-t mélyebben értelmezi (placed_items → placement model).
- **Multi-sheet wrapper**: több futást orchestrál, runner-t hívja iteratívan.
- **DXF export**: placements alapján DXF-et épít táblánként.

### Kapcsolódó fájlok a repóban
- `scripts/run_sparrow_smoketest.sh` (shell alapú futtatás)
- `scripts/validate_sparrow_io.py` (IO-contract validátor)
- `poc/sparrow_io/swim.json` (golden input)
- `poc/sparrow_io/final_swim.json` (golden output)


---

## Appendix A – “Definition of Done” (runner modul)

A runner modul akkor tekinthető késznek, ha:
1) Tud Sparrow-t futtatni abs bin path-tal és PATH-ról is.
2) Létrehoz run_dir-t, bemásolja az instance.json-t, és logol.
3) Megtalálja a `final_*.json`-t és parse-olja a metrikákat.
4) Opcionálisan validál (és fail esetén hibával kilép).
5) CI-ben fut és zöld a `poc/sparrow_io/swim.json` smoketest.
6) Failure esetén az artifactok visszakereshetők (log + output + instance snapshot).


## Appendix B – Tipikus hibák és gyors diagnózis

- **`sparrow` nem található** → `SPARROW_BIN`/PATH rossz. Ellenőrizd: `which sparrow`.
- **Üres pinned commit** → CI checkout fail. Kezeld: üres fájl esetén skip checkout.
- **Nincs `final_*.json`** → Sparrow crash vagy rossz cwd/output path. Nézd: `sparrow_stderr.log`.
- **Parse error** → Sparrow verzió változott, schema drift. Ilyenkor a golden input/output alapján frissítsd a parser/validator-t.
- **Átfedés fail** → input poligon topológia hibás vagy kompenzációs offset rossz (nem runner hiba, de itt derül ki).

