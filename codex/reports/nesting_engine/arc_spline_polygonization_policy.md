# Codex Report — arc_spline_polygonization_policy

**Status:** PASS

---

## 1) Meta

- **Task slug:** `arc_spline_polygonization_policy`
- **Kapcsolodo canvas:** `canvases/nesting_engine/arc_spline_polygonization_policy.md`
- **Kapcsolodo goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_arc_spline_polygonization_policy.yaml`
- **Futas datuma:** 2026-03-07
- **Branch / commit:** `main` / `9c48046` (implementacio kozben, uncommitted)
- **Fokusz terulet:** Mixed

## 2) Scope

### 2.1 Cel

1. ARC/SPLINE/ELLIPSE polygonization policy centralizalasa a Python geometry/importer retegen.
2. Arc-heavy valos DXF fixture kor bovitese repo-native pathon (`samples/dxf_demo/`).
3. Regresszios tesztek + smoke gate erosites self-intersection es hibakod bizonyitekkal.
4. F3-1 backlog es kapcsolodo tolerance/architecture dokumentacio szinkronizalasa.

### 2.2 Nem-cel (explicit)

1. Rust NFP / placement / SA algoritmus modositas.
2. Uj user-facing CLI/config mezo bevezetese.
3. Nominal/export contract ujratervezese.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok

- **Python geometry/importer policy:**
  - `vrs_nesting/geometry/polygonize.py`
  - `vrs_nesting/dxf/importer.py`
- **Tesztek:**
  - `tests/test_geometry_polygonize.py`
  - `tests/test_dxf_importer_json_fixture.py`
  - `tests/test_dxf_importer_error_handling.py`
- **Valos DXF fixture + smoke:**
  - `samples/dxf_demo/README.md`
  - `samples/dxf_demo/part_arc_heavy_ok.dxf`
  - `samples/dxf_demo/part_arc_heavy_self_intersect_fail.dxf`
  - `scripts/smoke_real_dxf_fixtures.py`
- **Docs + backlog:**
  - `canvases/nesting_engine/nesting_engine_backlog.md`
  - `docs/nesting_engine/tolerance_policy.md`
  - `docs/nesting_engine/architecture.md`
- **Codex workflow:**
  - `codex/codex_checklist/nesting_engine/arc_spline_polygonization_policy.md`
  - `codex/reports/nesting_engine/arc_spline_polygonization_policy.md`

### 3.2 Miert valtoztak?

- A curve tolerance policy eddig reszben implicit volt (`0.2` tobb helyen); most explicit source-of-truth konstansokra lett zarva.
- Az F3-1 regressziohoz repo-native valos DXF fixture-k kellettek, nem uj `poc/...` hierarchia.
- A smoke + tesztcsomag most mar expliciten bizonyitja a pozitiv non-self-intersection es negativ `DXF_INVALID_RING` viselkedest.

## 4) Verifikacio

### 4.1 Kotelezo parancs

- `./scripts/verify.sh --report codex/reports/nesting_engine/arc_spline_polygonization_policy.md` -> PASS

### 4.2 Opcionális, task-specifikus parancsok

- `python3 -m pytest -q tests/test_geometry_polygonize.py tests/test_dxf_importer_json_fixture.py tests/test_dxf_importer_error_handling.py` -> PASS (`18 passed`)
- `python3 scripts/smoke_real_dxf_fixtures.py` -> PASS

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
|---|---|---|---|---|
| `arc_tolerance_mm = 0.2` dokumentalva es tenylegesen alkalmazva van az importer curve polygonization policy-jeben | PASS | `vrs_nesting/geometry/polygonize.py:11`, `vrs_nesting/geometry/polygonize.py:73`, `vrs_nesting/dxf/importer.py:190`, `vrs_nesting/dxf/importer.py:623`, `docs/nesting_engine/tolerance_policy.md:144` | A tolerancia explicit konstans lett (`ARC_TOLERANCE_MM`/`CURVE_FLATTEN_TOLERANCE_MM`), es ARC valamint SPLINE/ELLIPSE utvonalon is ez van hasznalva. | pytest + verify gate |
| Van repo-native arc-heavy fixture keszlet a `samples/dxf_demo/` alatt, README-vel dokumentalva | PASS | `samples/dxf_demo/README.md:19`, `samples/dxf_demo/README.md:23`, `samples/dxf_demo/part_arc_heavy_ok.dxf`, `samples/dxf_demo/part_arc_heavy_self_intersect_fail.dxf`, `canvases/nesting_engine/nesting_engine_backlog.md:323` | Uj pozitiv/negativ valos DXF fixture kerult a canonical `samples/dxf_demo/` helyre, es backlog DoD path is ehhez lett igazítva. | `python3 scripts/smoke_real_dxf_fixtures.py` |
| A pozitiv arc-heavy fixture-ok polygonizalasa utan 0 self-intersection marad | PASS | `scripts/smoke_real_dxf_fixtures.py:28`, `scripts/smoke_real_dxf_fixtures.py:55`, `scripts/smoke_real_dxf_fixtures.py:66` | A smoke explicit `outer`+`holes` onmetszes-ellenorzest futtat a pozitiv fixture-okon. | `python3 scripts/smoke_real_dxf_fixtures.py` |
| A negativ arc-heavy fixture stabil, determinisztikus hibakoddal bukik (`DXF_INVALID_RING`) | PASS | `scripts/smoke_real_dxf_fixtures.py:81`, `scripts/smoke_real_dxf_fixtures.py:85`, `tests/test_dxf_importer_error_handling.py:44` | A valos DXF negativ fixture es egy importer-level curve kontur regresszio is `DXF_INVALID_RING` kodot var el. | pytest + smoke + verify gate |
| `python3 -m pytest -q` PASS a kapcsolodo importer/polygonize tesztekkel | PASS | `tests/test_geometry_polygonize.py:20`, `tests/test_dxf_importer_json_fixture.py:141`, `tests/test_dxf_importer_error_handling.py:44` | A policy-ra es regressziora celzott tesztek futnak es zolden mennek. | `python3 -m pytest -q tests/test_geometry_polygonize.py tests/test_dxf_importer_json_fixture.py tests/test_dxf_importer_error_handling.py` |
| `python3 scripts/smoke_real_dxf_fixtures.py` PASS a bovitett fixture-keszlettel | PASS | `scripts/smoke_real_dxf_fixtures.py:94`, `scripts/smoke_real_dxf_fixtures.py:105`, `scripts/smoke_real_dxf_fixtures.py:110` | A smoke mar kotelezoleg ellenorzi az uj arc-heavy pozitiv/negativ fixture-ket is. | `python3 scripts/smoke_real_dxf_fixtures.py` |
| `./scripts/verify.sh --report codex/reports/nesting_engine/arc_spline_polygonization_policy.md` PASS | PASS | `codex/reports/nesting_engine/arc_spline_polygonization_policy.verify.log` | A standard repo gate wrapper lefutott, es automatikusan frissiti az AUTO_VERIFY blokkot. | `./scripts/verify.sh --report codex/reports/nesting_engine/arc_spline_polygonization_policy.md` |

## 8) Advisory notes

- A curve flatten tolerance es endpoint chaining epsilon most expliciten kulon policy-kent van dokumentalva, akkor is, ha mindketto jelenleg `0.2`.
- Az arc-heavy negativ fixture SPLINE-alapu onmetszo contour, hogy importer oldalon stabil `DXF_INVALID_RING` hibat adjon.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-07T23:11:37+01:00 → 2026-03-07T23:14:48+01:00 (191s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/arc_spline_polygonization_policy.verify.log`
- git: `main@9c48046`
- módosított fájlok (git status): 18

**git diff --stat**

```text
 canvases/nesting_engine/nesting_engine_backlog.md |  2 +-
 docs/nesting_engine/architecture.md               | 36 +++++++++++++--
 docs/nesting_engine/tolerance_policy.md           | 32 +++++++++++++-
 samples/dxf_demo/README.md                        |  8 ++++
 scripts/smoke_real_dxf_fixtures.py                | 53 ++++++++++++++++++++---
 tests/test_dxf_importer_error_handling.py         | 25 +++++++++++
 tests/test_dxf_importer_json_fixture.py           | 35 +++++++++++++++
 vrs_nesting/dxf/importer.py                       | 14 +++---
 vrs_nesting/geometry/polygonize.py                |  8 +++-
 9 files changed, 196 insertions(+), 17 deletions(-)
```

**git status --porcelain (preview)**

```text
 M canvases/nesting_engine/nesting_engine_backlog.md
 M docs/nesting_engine/architecture.md
 M docs/nesting_engine/tolerance_policy.md
 M samples/dxf_demo/README.md
 M scripts/smoke_real_dxf_fixtures.py
 M tests/test_dxf_importer_error_handling.py
 M tests/test_dxf_importer_json_fixture.py
 M vrs_nesting/dxf/importer.py
 M vrs_nesting/geometry/polygonize.py
?? canvases/nesting_engine/arc_spline_polygonization_policy.md
?? codex/codex_checklist/nesting_engine/arc_spline_polygonization_policy.md
?? codex/goals/canvases/nesting_engine/fill_canvas_arc_spline_polygonization_policy.yaml
?? codex/prompts/nesting_engine/arc_spline_polygonization_policy/
?? codex/reports/nesting_engine/arc_spline_polygonization_policy.md
?? codex/reports/nesting_engine/arc_spline_polygonization_policy.verify.log
?? samples/dxf_demo/part_arc_heavy_ok.dxf
?? samples/dxf_demo/part_arc_heavy_self_intersect_fail.dxf
?? tests/test_geometry_polygonize.py
```

<!-- AUTO_VERIFY_END -->
