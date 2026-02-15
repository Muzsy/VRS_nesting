# canvases/egyedi_solver/p1_python_dependency_management_reproducible_install.md
# P1: Python dependency management (reproducible install)

## 🎯 Funkció

A cél reprodukálható Python dependency menedzsment bevezetése a repóban:

1. pip-tools alapú `.in` -> pinelt `.txt` flow (`requirements.in`, `requirements-dev.in`, `requirements.txt`, `requirements-dev.txt`),
2. script és CI telepítési tippek/steps átállítása a `requirements-dev.txt` használatára,
3. dokumentáció szinkronizálása, hogy a standard út a pinelt requirements telepítés legyen.

## 🧠 Fejlesztési részletek

### Scope

**Benne van**

- Runtime + dev függőségek explicit listázása `.in` fájlokban.
- Pinelt lock jellegű `requirements.txt` és `requirements-dev.txt` generálása pip-tools-szal.
- `scripts/check.sh` és `scripts/run_sparrow_smoketest.sh` telepítési tippek átállítása requirements-dev alapra.
- `repo-gate`, `sparrow-smoketest`, `nesttool-smoketest` workflow-k Python deps telepítésének egységesítése.
- QA/Codex/AGENTS dokumentáció frissítése a reprodukálható install folyamathoz.

**Nincs benne**

- Packaging/pyproject alapú teljes átállás.
- Nem-Python dependency kezelés átalakítása.
- Új quality gate bevezetése.

### Dependency policy

- `requirements.in`: runtime third-party csomagok (`ezdxf`, `shapely`).
- `requirements-dev.in`: fejlesztői + gate tooling (`-r requirements.in`, `pytest`, `mypy`, `pip-tools`).
- A pinelt `.txt` fájlok pip-tools compile eredmények és commitolandók.

### DoD

- [ ] A `requirements.in` / `requirements-dev.in` létezik és csak valós használt csomagokat tartalmaz.
- [ ] A pinelt `requirements.txt` / `requirements-dev.txt` létrejött pip-tools compile-ból.
- [ ] `scripts/check.sh` és `scripts/run_sparrow_smoketest.sh` telepítési tippek `requirements-dev.txt`-re mutatnak.
- [ ] A három workflow konzisztensen `requirements-dev.txt`-ből telepít Python deps-et.
- [ ] A dokumentáció rögzíti a hivatalos install/update folyamatot (`.in` módosítás + compile).
- [ ] Repo gate PASS:
  - `./scripts/verify.sh --report codex/reports/egyedi_solver/p1_python_dependency_management_reproducible_install.md`

### Kockázat + mitigáció + rollback

- Kockázat: lock fájl frissítés platform-specifikus eltéréseket okozhat.
- Mitigáció: CI-ben is ugyanazt a `requirements-dev.txt` telepítést használjuk.
- Rollback: workflow install lépések + script tippek visszaállítása, requirements fájlok eltávolítása.

## 🧪 Tesztállapot

- `./scripts/verify.sh --report codex/reports/egyedi_solver/p1_python_dependency_management_reproducible_install.md`
- `./scripts/check.sh`

## 🌍 Lokalizáció

Nem releváns.

## 📎 Kapcsolódások

- `scripts/check.sh`
- `scripts/run_sparrow_smoketest.sh`
- `.github/workflows/repo-gate.yml`
- `.github/workflows/sparrow-smoketest.yml`
- `.github/workflows/nesttool-smoketest.yml`
- `docs/qa/testing_guidelines.md`
- `docs/qa/dry_run_checklist.md`
- `docs/codex/overview.md`
- `AGENTS.md`
