# canvases/egyedi_solver/p0_pytest_unit_test_infra.md
# P0: Pytest unit teszt infrastruktúra + gate/CI integráció

## 🎯 Funkció
A repóban jelenleg nincs unit teszt coverage (csak smoke script-ek vannak). Ennek a tasknak a célja:
1) pytest alapú unit teszt scaffold bevezetése (minimál, de érdemi tesztekkel),
2) futtatás integrálása a repo standard gate-be (`scripts/check.sh`), hogy **minden feladat után automatikusan lefusson** a `verify.sh`-n keresztül,
3) futtatás integrálása a CI workflow-kba,
4) dokumentáció frissítése: a “szokásos végfuttatás” és “általános tesztfuttatás” része legyen a pytest, és ha később új teszt típus kerül be, azt a docs+gate együtt kövesse.

## 🧠 Fejlesztési részletek

### Scope
**Benne van**
- `pytest.ini` + `tests/` könyvtár.
- 3 darab gyors, determinisztikus unit teszt (külső dep nélkül, ezdxf nélkül):
  - DXF importer JSON fixture backend validálás (outer/inner, open contour hibák).
  - Project schema model validáció (allowed_rotations normalizálás + invalid érték hibakód).
  - Run artifacts run_dir helper (dir struktúra + snapshot + log append).
- `scripts/check.sh` bővítése: `python3 -m pytest -q` fusson le **a gate elején** (fail-fast).
- CI bővítés:
  - `.github/workflows/nesttool-smoketest.yml`
  - `.github/workflows/sparrow-smoketest.yml`
  - Mindkettő futtassa a pytest-et (ubuntu apt: `python3-pytest`).
- Dokumentáció frissítés:
  - `docs/qa/testing_guidelines.md` (standard parancsok + pytest beemelése + “új tesztek => docs+gate frissítendő” szabály)
  - `docs/qa/dry_run_checklist.md` (ellenőrzési pont: pytest is része a gate-nek)
  - `docs/codex/overview.md` (standard gate leírásban szerepeljen a pytest)
  - `AGENTS.md` (tooling elvárások: pytest szükséges a check.sh-hoz)

**Nincs benne**
- Dependency management rendbetétele (requirements/pyproject) – ez külön P0 pont.
- mypy/ruff/black bevezetés – külön feladat.
- Nagy unit teszt coverage – most csak infrastruktúra + 3 kritikus unit teszt “mintának”.

### Érintett fájlok (konkrét)
- Új:
  - `pytest.ini`
  - `tests/test_dxf_importer_json_fixture.py`
  - `tests/test_project_model_validation.py`
  - `tests/test_run_dir.py`
- Módosul:
  - `scripts/check.sh`
  - `.github/workflows/nesttool-smoketest.yml`
  - `.github/workflows/sparrow-smoketest.yml`
  - `docs/qa/testing_guidelines.md`
  - `docs/qa/dry_run_checklist.md`
  - `docs/codex/overview.md`
  - `AGENTS.md`

### Elvárások / szabályok
- A unit tesztek legyenek **gyorsak**, és ne igényeljenek:
  - `ezdxf` telepítést,
  - Sparrow build-et,
  - shapely-t (ne importáljanak shapely-függő modulokat).
- A DXF importer teszt **JSON fixture** bemenetet használjon (top-level `{ "entities": [...] }`), mert ezt a kód natívan támogatja (`vrs_nesting/dxf/importer.py`).
- A `scripts/check.sh` új részének hibája legyen egyértelmű: ha nincs pytest, adjon **konkrét telepítési tippet** (pl. `sudo apt-get install -y python3-pytest`).

### DoD
- [ ] `python3 -m pytest -q` PASS lokálisan a repo rootból.
- [ ] `scripts/check.sh` a futás elején lefuttatja a pytest-et (fail-fast), és nem töri a meglévő gate működést.
- [ ] CI-ben mindkét workflow futtatja a pytest-et (python3-pytest telepítve).
- [ ] `docs/qa/testing_guidelines.md` és `docs/codex/overview.md` egyértelműen tartalmazza, hogy a pytest a standard futtatás része.
- [ ] `docs/qa/testing_guidelines.md` tartalmazza a szabályt: ha új teszt típust adunk hozzá, azt a standard gate-be és a doksiba is be kell emelni.
- [ ] `AGENTS.md` tooling elvárások közt szerepel a pytest.
- [ ] Repo gate kötelezően lefut: `./scripts/verify.sh --report codex/reports/egyedi_solver/p0_pytest_unit_test_infra.md` -> PASS

### Kockázat + mitigáció + rollback
- Kockázat: a gate (check.sh) újonnan pytest-függő lesz.
- Mitigáció: fail-fast, és hiba esetén egyértelmű install tipp; docs/AGENTS frissítve.
- Rollback: pytest futtatás kivétele `scripts/check.sh`-ból + CI step kivétele + `tests/` és `pytest.ini` eltávolítása (izolált).

## 🧪 Tesztállapot
- Kötelező repo gate:
  - `./scripts/verify.sh --report codex/reports/egyedi_solver/p0_pytest_unit_test_infra.md`
- Közvetlen:
  - `python3 -m pytest -q`
  - `./scripts/check.sh`

## 🌍 Lokalizáció
N/A

## 📎 Kapcsolódások
- Audit: `VRS_nesting_audit_report.md` (P0: “HIÁNYZÓ UNIT TESZT COVERAGE”)
- Gate: `scripts/check.sh`, `scripts/verify.sh`
- CI: `.github/workflows/nesttool-smoketest.yml`, `.github/workflows/sparrow-smoketest.yml`
- DXF importer: `vrs_nesting/dxf/importer.py`
- Project model: `vrs_nesting/project/model.py`
- Run artifacts: `vrs_nesting/run_artifacts/run_dir.py`
- Doksik: `docs/qa/testing_guidelines.md`, `docs/qa/dry_run_checklist.md`, `docs/codex/overview.md`, `AGENTS.md`
