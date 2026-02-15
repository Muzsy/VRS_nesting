PASS

## 1) Meta

- **Task slug:** `p1_python_dependency_management_reproducible_install`
- **Kapcsolodo canvas:** `canvases/egyedi_solver/p1_python_dependency_management_reproducible_install.md`
- **Kapcsolodo goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_p1_python_dependency_management_reproducible_install.yaml`
- **Futas datuma:** `2026-02-15`
- **Branch / commit:** `main@34d7695`
- **Fokusz terulet:** `QA | CI | Dependency management | Docs`

## 2) Scope

### 2.1 Cel

- Reprodukálható Python dependency management bevezetése pip-tools flow-val.
- Script/CI telepítések átállítása pinelt requirements használatára.
- Dokumentáció frissítése az új install/update folyamathoz.

### 2.2 Nem-cel (explicit)

- Pyproject/package management teljes migráció.
- Új quality gate lépések bevezetése.
- Nem-Python dependency kezelés átalakítása.

## 3) Valtozasok osszefoglalasa (Change summary)

### 3.1 Erintett fajlok

- `requirements.in`
- `requirements-dev.in`
- `requirements.txt`
- `requirements-dev.txt`
- `scripts/check.sh`
- `scripts/run_sparrow_smoketest.sh`
- `.github/workflows/repo-gate.yml`
- `.github/workflows/sparrow-smoketest.yml`
- `.github/workflows/nesttool-smoketest.yml`
- `docs/qa/testing_guidelines.md`
- `docs/qa/dry_run_checklist.md`
- `docs/codex/overview.md`
- `AGENTS.md`
- `codex/codex_checklist/egyedi_solver/p1_python_dependency_management_reproducible_install.md`
- `codex/reports/egyedi_solver/p1_python_dependency_management_reproducible_install.md`

### 3.2 Miert valtoztak?

- Az eddigi telepítés ad-hoc apt/pip kombináció volt workflow-nként eltérő módon.
- A pinelt requirements egységesíti és reprodukálhatóvá teszi a lokál + CI telepítést.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs

- `./scripts/verify.sh --report codex/reports/egyedi_solver/p1_python_dependency_management_reproducible_install.md` -> PASS

### 4.2 Opcionlis, feladatfuggo parancsok

- `python3 -m piptools compile requirements.in -o requirements.txt` -> PASS
- `python3 -m piptools compile requirements-dev.in -o requirements-dev.txt` -> PASS
- `./scripts/check.sh` -> PASS

### 4.3 Ha valami kimaradt

- Nincs.

### 4.4 Automatikus blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-15T18:13:22+01:00 → 2026-02-15T18:14:58+01:00 (96s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/p1_python_dependency_management_reproducible_install.verify.log`
- git: `main@34d7695`
- módosított fájlok (git status): 18

**git diff --stat**

```text
 .github/workflows/nesttool-smoketest.yml |  6 +++++-
 .github/workflows/repo-gate.yml          |  6 +++---
 .github/workflows/sparrow-smoketest.yml  |  8 ++++++--
 AGENTS.md                                |  6 +++---
 docs/codex/overview.md                   |  5 +++++
 docs/qa/dry_run_checklist.md             |  1 +
 docs/qa/testing_guidelines.md            | 16 ++++++++++------
 scripts/check.sh                         |  4 ++--
 scripts/run_sparrow_smoketest.sh         |  3 +--
 9 files changed, 36 insertions(+), 19 deletions(-)
```

**git status --porcelain (preview)**

```text
 M .github/workflows/nesttool-smoketest.yml
 M .github/workflows/repo-gate.yml
 M .github/workflows/sparrow-smoketest.yml
 M AGENTS.md
 M docs/codex/overview.md
 M docs/qa/dry_run_checklist.md
 M docs/qa/testing_guidelines.md
 M scripts/check.sh
 M scripts/run_sparrow_smoketest.sh
?? canvases/egyedi_solver/p1_python_dependency_management_reproducible_install.md
?? codex/codex_checklist/egyedi_solver/p1_python_dependency_management_reproducible_install.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_p1_python_dependency_management_reproducible_install.yaml
?? codex/reports/egyedi_solver/p1_python_dependency_management_reproducible_install.md
?? codex/reports/egyedi_solver/p1_python_dependency_management_reproducible_install.verify.log
?? requirements-dev.in
?? requirements-dev.txt
?? requirements.in
?? requirements.txt
```

<!-- AUTO_VERIFY_END -->

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| --- | ---: | --- | --- | --- |
| Requirements input + pinelt output fájlok létrejöttek | PASS | `requirements.in:1`, `requirements-dev.in:1`, `requirements.txt:1`, `requirements-dev.txt:1` | A dependency forrás és lock jellegű pinelt fájlok létrejöttek pip-tools compile-ból. | `python3 -m piptools compile ...` |
| Script tippek requirements-dev telepítésre mutatnak | PASS | `scripts/check.sh:31`, `scripts/run_sparrow_smoketest.sh:112` | Az install tippek már nem ad-hoc csomagra, hanem a pinelt dev requirements-re mutatnak. | `./scripts/check.sh` |
| CI workflow-k pinelt requirements alapján telepítenek | PASS | `.github/workflows/repo-gate.yml:22`, `.github/workflows/sparrow-smoketest.yml:22`, `.github/workflows/nesttool-smoketest.yml:22` | A workflow-k Python deps telepítése konzisztens és reprodukálható. | Workflow review |
| Doksikban hivatalos install/update folyamat szerepel | PASS | `docs/qa/testing_guidelines.md:70`, `docs/qa/dry_run_checklist.md:89`, `docs/codex/overview.md:72`, `AGENTS.md:78` | Rögzítve a `requirements-dev.txt` telepítés és `.in` + compile frissítési szabály. | Doksireview |
| Verify PASS + auto log/report frissítés | PASS | `codex/reports/egyedi_solver/p1_python_dependency_management_reproducible_install.verify.log:1` | Verify wrapper lefutott és frissítette az AUTO_VERIFY blokkot. | `./scripts/verify.sh --report ...` |

## 8) Advisory notes (nem blokkolo)

- A pip-tools futtatás lokál Python verzióhoz kötött, ezért lock frissítésnél ugyanazon főverzió ajánlott mint CI-ben.
