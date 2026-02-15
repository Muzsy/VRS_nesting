# canvases/egyedi_solver/ci_gate_check_sh.md

# CI gate: `check.sh` futtatása + docs szinkron (bővített smoke suite)

## 🎯 Funkció

A cél, hogy a repo **egyetlen, közös quality gate-je** (`./scripts/check.sh`) legyen a **lokál + Codex verify + CI** közös igazsága, és a **bővített smoke suite** (valódi DXF fixture, BLOCK/INSERT export smoke, multisheet edge-case smoke, stb.)

1. **dokumentálva** legyen az „általános tesztfuttatás” részeként, és
2. **CI-ben is lefusson** minden PR/push esetén.

Ezzel megszűnik az a csúszás, hogy lokál/verify alatt lefutnak extra smoke-ok, de CI-ben nem.

## 🧠 Fejlesztési részletek

### Jelenlegi állapot (evidence)

* A standard gate bővített smoke lépései a `scripts/check.sh`-ban vannak (több `scripts/smoke_*.py` hívás).
* A feladat-specifikus report jelzi, hogy a valódi DXF smoke **`ezdxf`** függőségű.
* A CI jelenleg két külön workflow-t futtat, de **nem** futtatja a `scripts/check.sh`-t, így a bővített smoke suite nem része a CI gate-nek.

### Scope

**Benne van:**

* `docs/qa/testing_guidelines.md` frissítése:

  * az „általános tesztfuttatás” szekció sorolja fel a `./scripts/check.sh` fő lépéseit (pytest + smoke-ok), és a szükséges függőségeket (különösen: `ezdxf`).
* `docs/codex/overview.md` frissítése:

  * a „standard gate” leírás szinkronba kerül a `scripts/check.sh` aktuális valós tartalmával.
* Új CI workflow bevezetése, ami **egyetlen parancsként** futtatja a `./scripts/check.sh`-t:

  * `.github/workflows/repo-gate.yml`
  * telepíti a minimum csomagokat (python3, pytest, pip, shapely) és pip-pel az `ezdxf`-et.
  * failure esetén artifact upload (legalább `runs/**` és `.cache/sparrow/**`).

**Nincs benne:**

* A két meglévő workflow (nesttool/sparrow) átszabása vagy kiváltása (most csak új „össz-gate” workflow-t adunk hozzá).
* Dependency management rendszer (requirements/pyproject) bevezetése (külön task).

### DoD

* [ ] `docs/qa/testing_guidelines.md` tartalmazza a **„Szokásos végfuttatás”** parancsot és a `check.sh` fő lépéseinek felsorolását, plusz a szükséges dependency-ket.

  * [ ] külön megjegyzés: a valódi DXF smoke-okhoz kell `ezdxf`.
* [ ] `docs/codex/overview.md` gate leírása a `scripts/check.sh` aktuális tartalmával összhangban van.
* [ ] Új workflow: `.github/workflows/repo-gate.yml`

  * [ ] `on: [push, pull_request, workflow_dispatch]`
  * [ ] `./scripts/check.sh` fut
  * [ ] telepíti a szükséges csomagokat (python3, pytest, pip, shapely, git) és `pip install ezdxf`
  * [ ] failure esetén feltölti a futási artefaktokat
* [ ] Verify PASS (Codex):

  * `./scripts/verify.sh --report codex/reports/egyedi_solver/ci_gate_check_sh.md`
* [ ] A report DoD -> Evidence mátrixa kitöltve (fájl + line hivatkozásokkal), és a verify log generálódik.

### Kockázat + mitigáció + rollback

* Kockázat: a `check.sh` futásidő CI-ben nő (Sparrow clone+build + smoke suite).

  * Mitigáció: workflow timeout emelése (pl. 25 perc), artifact upload failure esetén.
* Kockázat: `ezdxf` pip install eltérő környezetekben.

  * Mitigáció: CI-ben pip install; lokál doksiban rövid install tipp.
* Rollback: a `.github/workflows/repo-gate.yml` törölhető, a docs módosítás visszagörgethető.

## 🧪 Tesztállapot

* Közös gate parancs:

  * `./scripts/check.sh`
* Codex kötelező verify:

  * `./scripts/verify.sh --report codex/reports/egyedi_solver/ci_gate_check_sh.md`

## 🌍 Lokalizáció

Nem releváns.

## 📎 Kapcsolódások

* `scripts/check.sh`
* `scripts/verify.sh`
* `docs/qa/testing_guidelines.md`
* `docs/codex/overview.md`
* `.github/workflows/nesttool-smoketest.yml`
* `.github/workflows/sparrow-smoketest.yml`
* `codex/reports/egyedi_solver/real_dxf_fixture_smoke_arc_spline_chaining_impl.md` (ezdxf dependency note)
