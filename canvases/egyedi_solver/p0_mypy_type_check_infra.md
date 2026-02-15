# canvases/egyedi_solver/p0_mypy_type_check_infra.md

# P0: Mypy type-check bevezetése (konfig + gate integráció)

## 🎯 Funkció

A repóban jelenleg nincs statikus típusellenőrzés. A cél:

1. **mypy konfiguráció** bevezetése (fókusz: `vrs_nesting/`),
2. **gate integráció** a repo standard ellenőrzésébe (`scripts/check.sh`), hogy **minden feladat után automatikusan lefusson** a `verify.sh`-n keresztül,
3. **CI gate integráció** a standard gate workflow-ba (`.github/workflows/repo-gate.yml`) úgy, hogy a check.sh-ban futó mypy ténylegesen lefusson (mypy telepítve legyen),
4. minimális **kódtisztítás**, hogy a mypy baseline **PASS** legyen,
5. dokumentáció frissítése: a „szokásos végfuttatás” része legyen a mypy is.

## 🧠 Fejlesztési részletek

### Scope

**Benne van**

* `mypy.ini` a repo rootban (scoped: csak `vrs_nesting/`).
* `scripts/check.sh` bővítése: mypy fusson le **fail-fast** módon, a pytest után, a Sparrow build / smoke előtt.
* CI bővítés: `.github/workflows/repo-gate.yml` telepítse a mypy-t (pip), mert a gate mostantól futtatja.
* Minimális javítások a mypy által jelzett valós hibákra (csak ami kell a baseline PASS-hoz).
* Dokumentáció frissítés:

  * `docs/qa/testing_guidelines.md`
  * `docs/qa/dry_run_checklist.md`
  * `docs/codex/overview.md`
  * `AGENTS.md`

**Nincs benne**

* “strict mypy” vagy teljes típusannotációs refaktor.
* dependency management (requirements/pyproject) rendbetétel.
* ruff/black/flake8 bevezetés.

### mypy policy (baseline)

* `files = vrs_nesting` (ne menjen végig a `scripts/`, `poc/`, `runs/` stb. fájlokon).
* `check_untyped_defs = True`, `no_implicit_optional = True`.
* Warnok: `warn_unused_ignores`, `warn_redundant_casts`, `warn_return_any`.
* 3rd-party/optional modulokra per-module ignore:

  * `ezdxf` (opcionális DXF backend)
  * `shapely` (telepített, de stubs/py.typed nem garantált)

### Szükséges kódjavítások (a baseline PASS-hoz)

A következő fájlokban a mypy valós hibákat jelez; ezeket minimálisan javítani kell:

* `vrs_nesting/nesting/instances.py`

  * `PART_NEVER_FITS_STOCK` ágban a `part_dims.get(..., None)` helyett explicit `if part_id not in part_dims: raise`, majd `part_dims[part_id]`.
* `vrs_nesting/geometry/polygonize.py`

  * `outer_points_mm` kötelező mező: ha `None`, dobjon ValueError-t (type narrowing + logikai korrektség).
* `vrs_nesting/dxf/importer.py`

  * `points` többszöri definíciója helyett egyedi változónevek (pl. `lw_points`, `poly_points`, `line_points`, `spline_points`).
  * az `import ezdxf` soron lévő felesleges `# type: ignore` eltávolítása (mypy.ini kezeli).
* `vrs_nesting/dxf/exporter.py`

  * a felesleges `# type: ignore` eltávolítása az `import ezdxf` soron.
* `vrs_nesting/runner/sparrow_runner.py`

  * `_read_json()` térjen vissza garantáltan `dict[str, Any]`-val (runtime check + `typing.cast`).

### Érintett fájlok (konkrét)

* Új:

  * `canvases/egyedi_solver/p0_mypy_type_check_infra.md`
  * `mypy.ini`
* Módosul:

  * `scripts/check.sh`
  * `.github/workflows/repo-gate.yml`
  * `vrs_nesting/nesting/instances.py`
  * `vrs_nesting/geometry/polygonize.py`
  * `vrs_nesting/dxf/importer.py`
  * `vrs_nesting/dxf/exporter.py`
  * `vrs_nesting/runner/sparrow_runner.py`
  * `docs/qa/testing_guidelines.md`
  * `docs/qa/dry_run_checklist.md`
  * `docs/codex/overview.md`
  * `AGENTS.md`

### DoD

* [ ] `python3 -m mypy --config-file mypy.ini vrs_nesting` PASS.
* [ ] `scripts/check.sh` futtatja a mypy-t (fail-fast), és hiba esetén ad konkrét install tippet.
* [ ] CI-ben a `repo-gate` workflow PASS (mypy telepítve, check.sh fut).
* [ ] Doksikban szerepel, hogy a mypy a standard futtatás része.
* [ ] Repo gate lefut:

  * `./scripts/verify.sh --report codex/reports/egyedi_solver/p0_mypy_type_check_infra.md` -> PASS

### Kockázat + mitigáció + rollback

* Kockázat: új “kötelező” tool (mypy) bejön a gate-be.
* Mitigáció: fail-fast, egyértelmű telepítési tipp + CI telepítés beemelve.
* Rollback: mypy step kivétele a `scripts/check.sh`-ból + `mypy.ini` törlése + CI install step revert.

## 🧪 Tesztállapot

* Kötelező repo gate:

  * `./scripts/verify.sh --report codex/reports/egyedi_solver/p0_mypy_type_check_infra.md`
* Közvetlen:

  * `python3 -m mypy --config-file mypy.ini vrs_nesting`
  * `./scripts/check.sh`

## 🌍 Lokalizáció

N/A

## 📎 Kapcsolódások

* Feltöltött audit megállapítás: “NINCS MYPY / TYPECHECK” (P0)
* Standard gate: `scripts/check.sh`, `scripts/verify.sh`
* CI gate: `.github/workflows/repo-gate.yml`
* Doksik: `docs/qa/testing_guidelines.md`, `docs/qa/dry_run_checklist.md`, `docs/codex/overview.md`, `AGENTS.md`
