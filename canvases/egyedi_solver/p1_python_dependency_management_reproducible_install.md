# canvases/egyedi_solver/p1_python_dependency_management_reproducible_install.md

# P1: Python dependency management (reprodukálható telepítés)

## 🎯 Funkció

A repó Python-függőségei jelenleg részben ad-hoc módon kerülnek telepítésre (CI-ben apt + pip, lokál gépen egyéni telepítés).  
A cél egy **reprodukálható, dokumentált** telepítési mód:

- legyen **verziózott, pinelt** Python dependency lista a repóban,
- a **CI workflow-k** ugyanazt a dependency készletet telepítsék,
- a lokál fejlesztői telepítés 1–2 paranccsal meglegyen,
- a gate (`scripts/check.sh` + `scripts/verify.sh`) változatlan elv mellett fusson.

Nem cél: packaging/kiadás (PyPI), modul publikálás, nagy átszervezés.

---

## 🧠 Fejlesztési részletek

### Jelenlegi állapot (repo tények)
- A gate belépési pont: `scripts/check.sh`
- CI-ben a “repo-gate” workflow futtatja: `.github/workflows/repo-gate.yml`
- A check.sh közvetlenül hívja:
  - `python3 -m pytest -q`
  - `python3 -m mypy --config-file mypy.ini vrs_nesting`
- A `mypy.ini` nem pinel konkrét Python minor verziót (`python_version` nincs megadva), ezért ezt a canvas sem tekinti fix 3.11 elvárásnak.

### Választott megoldás
**pip-tools alapú** dependency management:
- `requirements.in` (csak direkt függőségek)
- `requirements-dev.in` (dev + teszt + tooling, base-re támaszkodva)
- generált/pinelt:
  - `requirements.txt`
  - `requirements-dev.txt`

A CI és a lokál install **a pinelt** `requirements-dev.txt`-t használja.

### Érintett fájlok (elvárt)
Újak:
- `requirements.in`
- `requirements-dev.in`
- `requirements.txt`
- `requirements-dev.txt`

Módosul:
- `scripts/check.sh` (install tippek: requirements-dev.txt-re mutassanak)
- `.github/workflows/repo-gate.yml` (pip install requirements-dev.txt)
- opcionálisan (konszolidáció): `.github/workflows/sparrow-smoketest.yml`, `.github/workflows/nesttool-smoketest.yml`
- `docs/qa/testing_guidelines.md` (telepítés szekció frissítése)
- `docs/qa/dry_run_checklist.md` (telepítés / gate futtatás előfeltételek)
- `AGENTS.md` (munkaszabály: új dependency esetén .in + compile + commit)
- `docs/codex/overview.md` (minőségkapu + telepítés hivatkozás)

### Feladatlista
- [ ] `requirements.in` és `requirements-dev.in` létrehozása (repo jelenlegi csomagigényei alapján: pytest/mypy/ezdxf/shapely)
- [ ] `requirements.txt` + `requirements-dev.txt` előállítása pip-tools-szal (pinelt verziók)
- [ ] CI workflow(k) frissítése: pip install `-r requirements-dev.txt`
- [ ] `scripts/check.sh` install tipjeinek frissítése: requirements-dev.txt (ne csomagonkénti random telepítés)
- [ ] Doksik frissítése: `docs/qa/testing_guidelines.md`, `docs/qa/dry_run_checklist.md`, `docs/codex/overview.md`, `AGENTS.md`
- [ ] Repo gate futtatás: `./scripts/verify.sh --report codex/reports/egyedi_solver/p1_python_dependency_management_reproducible_install.md`

### DoD (késznek tekinthető, ha)
- Egy friss gépen (venv-ben vagy system pythonon) a `requirements-dev.txt` telepítése után
  - `./scripts/check.sh` lefut,
  - `./scripts/verify.sh --report ...` PASS.
- CI-ben a `repo-gate` workflow ugyanebből a requirements-ből telepít.
- A telepítési lépések dokumentálva vannak a fent jelzett doksikban.

### Kockázatok / rollback
- Kockázat: bizonyos csomagok platformfüggőek → első körben csak a ténylegesen használt csomagokat rögzítsük.
- Rollback: workflow-k és doksik visszaállítása a korábbi apt+pip egyedi telepítésre; requirements fájlok maradhatnak, de nem használtak.

---

## 🧪 Tesztállapot

Elvárt ellenőrzés:
- `./scripts/verify.sh --report codex/reports/egyedi_solver/p1_python_dependency_management_reproducible_install.md`

Megjegyzés:
- Ha a későbbiekben új teszt/gate lépés kerül a `check.sh`-ba, akkor azt **a standard gate listában** is rögzíteni kell (`docs/qa/testing_guidelines.md` + `docs/qa/dry_run_checklist.md`).

---

## 🌍 Lokalizáció

Nem releváns.

---

## 📎 Kapcsolódások

- `scripts/check.sh`
- `scripts/verify.sh`
- `.github/workflows/repo-gate.yml`
- `docs/qa/testing_guidelines.md`
- `docs/qa/dry_run_checklist.md`
- `AGENTS.md`
- `docs/codex/overview.md`
- `mypy.ini`
- `pytest.ini`
