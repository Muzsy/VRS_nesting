# DXF nesting app – 1) Repo skeleton + futtatható „hello pipeline” (részletes)

## 🎯 Funkció

**Ennek a fázisnak a célja:**
- legyen egy *futtatható* projekt (Python CLI tool),
- tudjon **project.json**-t beolvasni és validálni,
- hozzon létre egy **run mappát**, logoljon, és hozzon létre üres (placeholder) outputokat,
- készen álljon arra, hogy a következő lépésekben beépítsük a DXF importot és a sparrow futtatást.

**MVP szempont:** itt még nincs nesting. A cél a stabil „csővezeték váz”, amire rá lehet építeni.

---

## 🧠 Fejlesztési részletek

### 1.1. Döntés: Python tooling és dependency kezelés

**Összefoglaló:**
Ha a környezet nincs rögzítve, minden gépen másképp fog viselkedni. MVP-hez elég egy egyszerű, de determinisztikus megoldás.

**Ajánlott választás (egyszerű és stabil):**
- `python >= 3.11`
- `venv` + `pip-tools` (requirements.in → requirements.txt)

Alternatíva:
- `poetry` (kényelmes, de több „szabály”)
- `uv` (nagyon gyors, de csapatfüggő)

**Feladatlista:**
- [ ] Rögzítsd a Python verziót (README + `pyproject.toml` vagy `.python-version`)
- [ ] Hozz létre venv-et és alap csomaglistát
- [ ] Hozz létre `requirements.in`-t (csak a direkt függőségek)
- [ ] Generáld `requirements.txt`-t (pinelt verziókkal)

**Kimenet:**
- `requirements.in`
- `requirements.txt`
- `README.md` (telepítés 6 sorban)

---

### 1.2. Repo struktúra (minimal, de rendezett)

**Összefoglaló:**
Kezdettől legyenek külön a CLI, a core, a sémák és a docs. Így nem kell később szétverni.

**Javasolt struktúra:**
- `app/`
  - `__init__.py`
  - `cli.py` (entry)
  - `project_model.py` (pydantic model)
  - `runner.py` (orchestrator: load → run folder → placeholder steps)
  - `utils/`
    - `fs.py` (paths, safe mkdir)
    - `logging.py` (log setup)
- `docs/`
- `samples/`
  - `project_example.json`
- `runs/` (gitignore)
- `tests/` (üresen is ok)

**Feladatlista:**
- [ ] Hozd létre a mappákat és üres `__init__.py`
- [ ] Készíts `.gitignore`-t (venv, runs, __pycache__)
- [ ] Készíts egy minimál `README.md`-t

**Kimenet:**
- működő repo layout

---

### 1.3. CLI belépési pont (nesttool) + parancsok

**Összefoglaló:**
MVP-hez 1 parancs kell: `run`. Ezzel minden későbbi automatizmus kezelhető.

**Ajánlott CLI keretrendszer:**
- `typer` (szép help, gyors fejlesztés) vagy `argparse` (0 függőség)

**MVP parancsok:**
- `nesttool run <project.json> [--out <dir>] [--dry-run] [--debug]`
- opcionális: `nesttool validate <project.json>` (csak validál)

**Feladatlista:**
- [ ] `app/cli.py` létrehozása
- [ ] `run` parancs argumentumokkal
- [ ] exit code szabály:
  - 0 siker
  - 2 validációs hiba
  - 3 runtime hiba
- [ ] `--dry-run`: csak run mappát + logot csinál, nesting nélkül

**Kimenet:**
- `python -m app.cli run samples/project_example.json` lefut

---

### 1.4. Project config modell (pydantic) + séma

**Összefoglaló:**
A project.json lesz az egyetlen „UI” MVP-ben, ezért ezt nagyon stabilra kell tenni: típusok, defaultok, validáció.

**Javasolt mezők (MVP):**
- `board`: { `width_mm`, `height_mm`, `margin_mm` }
- `spacing_mm`
- `rotations`: { `mode`: "fixed"|"step"|"list", `step_deg`?, `list_deg`? }
- `quality`: { `arc_tolerance_mm`, `simplify_epsilon_mm`? }
- `run`: { `time_limit_s`, `seed`, `workers`? }
- `parts`: [ { `path`, `quantity`, `name`? } ]
- `output_dir`? (ha nincs: runs alatt generált)

**Validációk (MVP minimum):**
- width/height > 0
- margin >= 0
- spacing >= 0
- rotations:
  - fixed → implicit [0,90,180,270]
  - step → step_deg > 0 és 360 osztás logikus (1..180)
  - list → minden 0..359
- parts:
  - path létezik
  - quantity >= 1

**Feladatlista:**
- [ ] `app/project_model.py`: pydantic model + custom validators
- [ ] Defaultok rögzítése (pl. step=5°, arc_tol=0.2mm, time_limit=60s)
- [ ] `samples/project_example.json` elkészítése (DXF-ek nélkül is ok, csak útvonalak placeholder)
- [ ] (Opcionális) JSON schema export pydanticből

**Kimenet:**
- project.json hibáira értelmes hibaüzenet

---

### 1.5. Run mappa létrehozás + artefakt struktúra

**Összefoglaló:**
Minden futásnak külön mappában kell landolnia, hogy visszanézhető legyen (reproducibility).

**MVP run mappa struktúra:**
- `runs/YYYYMMDD_HHMMSS/`
  - `project.json` (bemásolt / normalizált)
  - `run.log`
  - `artifacts/`
    - `instance.json` (MVP-ben placeholder)
    - `final.json` (MVP-ben placeholder)
    - `sheet_001.svg` (MVP-ben placeholder)
  - `out/`
    - `sheet_001.dxf` (MVP-ben placeholder – üres DXF)
  - `report.json`

**Feladatlista:**
- [ ] `app/utils/fs.py`: safe mkdir, timestamp, path resolve
- [ ] `runner.py`: run folder create + subfolders
- [ ] project config másolása a run mappába
- [ ] placeholder fájlok generálása (üres JSON + üres DXF)

**Kimenet:**
- minden run determinisztikusan létrejön

---

### 1.6. Logging – konzol + file, egységes formátum

**Összefoglaló:**
Később DXF import és sparrow futtatásnál a log lesz az első számú debug eszköz.

**MVP logging szabályok:**
- INFO szint konzolra
- DEBUG opcionálisan `--debug`
- file log mindig mentésre kerül
- minden futás elején kiírod:
  - config összefoglaló
  - parts count + total quantity
  - board params

**Feladatlista:**
- [ ] `app/utils/logging.py`: logger setup
- [ ] CLI `--debug` kapcsoló
- [ ] minden exception stacktrace a file logba

**Kimenet:**
- `run.log` olvasható és hasznos

---

### 1.7. „Hello pipeline” futás – placeholder lépések

**Összefoglaló:**
A runnerben már most legyenek meg a pipeline „hook”-ok, de még üresen:
- load_project
- prepare_run_dir
- prepare_instance_json (placeholder)
- execute_engine (placeholder)
- export_outputs (placeholder)
- write_report

**Feladatlista:**
- [ ] `runner.py` lépésfüggvények skeleton
- [ ] `report.json` generálás MVP-ben:
  - timestamp
  - input parts list
  - params
  - status: OK (dry) / OK
- [ ] `--dry-run`: engine lépést átugorja

**Kimenet:**
- futtatás végén van `report.json` és placeholder output

---

### 1.8. Minőségkapuk (minimum)

**Összefoglaló:**
Ne engedd, hogy a repo már az elején „szemeteljen”.

**Feladatlista:**
- [ ] `ruff` (lint) + `black` (format) vagy csak ruff format
- [ ] `pytest` skeleton (1 db smoke test: CLI validate)
- [ ] pre-commit (opcionális, de ajánlott)

**Kimenet:**
- 1 parancs: `pytest` zöld
- 1 parancs: `ruff check .` zöld

---

## 🧪 Tesztállapot

**Ebben a fázisban elvárt:**
- Smoke test: `nesttool run samples/project_example.json --dry-run` exit 0
- Validation test: hibás config exit 2

---

## 🌍 Lokalizáció

Nincs.

---

## 📎 Kapcsolódások

Ez a fázis közvetlenül előkészíti:
- a DXF import modul bekötését (2. fázis)
- a sparrow futtatást (6. fázis)
- a multi-sheet export struktúrát (7–8. fázis)

