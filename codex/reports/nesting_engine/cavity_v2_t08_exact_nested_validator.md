PASS

## 1) Meta
- Task slug: `cavity_v2_t08_exact_nested_validator`
- Kapcsolodo canvas: `canvases/nesting_engine/cavity_v2_t08_exact_nested_validator.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/nesting_engine/fill_canvas_cavity_v2_t08_exact_nested_validator.yaml`
- Futas datuma: `2026-05-02`
- Branch / commit: `main@807157b`
- Fokusz terulet: `Exact nested cavity validation modul`

## 2) Scope

### 2.1 Cel
- Uj, fuggetlen Shapely-alapu validátor modul keszitese `cavity_plan_v2` placement tree-khez.
- Rekurziv containment + sibling overlap + quantity mismatch ellenorzes.
- Strict es non-strict uzemmod tamogatas.

### 2.2 Nem-cel (explicit)
- Nem tortent modositas `worker/cavity_prepack.py` vagy `worker/result_normalizer.py` allomanyokban.
- Nincs DB/file IO side-effect a validatorban.
- Nem tortent auto-javitas, csak issue detektalas.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `worker/cavity_validation.py` (uj)
- `tests/worker/test_cavity_validation.py` (uj)
- `codex/codex_checklist/nesting_engine/cavity_v2_t08_exact_nested_validator.md`
- `codex/reports/nesting_engine/cavity_v2_t08_exact_nested_validator.md`

### 3.2 Mi valtozott es miert
- Uj validacios modul:
  - `CavityValidationError`, `ValidationIssue`,
  - `validate_child_within_cavity()` (`covers()` alapu),
  - `validate_no_child_child_overlap()` (intersections area),
  - `validate_placement_tree_node()` (rekurziv tree validacio),
  - `validate_cavity_plan_v2()` (top-level validacio, strict/non-strict).
- A transform logika kulon helperben:
  - `_build_placed_polygon()` outer polygon elhelyezeshez,
  - `_build_transformed_cavity_polygon()` cavity gyuru transzformalashoz.
- Unit tesztek lefedik a 6 elvart scenariot, beleertve a matrjoska valid esetet is.

## 4) Verifikacio

### 4.1 Feladatfuggo ellenorzes
- `python3 -c "from worker.cavity_validation import CavityValidationError, ValidationIssue, validate_cavity_plan_v2; print('validator OK')"` -> PASS
- `python3 -m pytest -q tests/worker/test_cavity_validation.py` -> PASS (`6 passed`)
- `python3 -c "from shapely.geometry import Polygon; from shapely import affinity; print('shapely import OK')"` -> PASS
- `rg -n "^shapely" requirements-dev.txt requirements.txt` -> `shapely==2.1.2`

### 4.2 Kotelezo repo gate
- `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t08_exact_nested_validator.md` -> PASS (AUTO_VERIFY blokk frissul)

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| `worker/cavity_validation.py` letezik | PASS | `worker/cavity_validation.py:1` | Uj validator modul letrehozva. | import smoke |
| `CavityValidationError`, `ValidationIssue`, `validate_cavity_plan_v2` exportalt | PASS | `worker/cavity_validation.py:14`, `worker/cavity_validation.py:18`, `worker/cavity_validation.py:743` | Kotelezo publikus szimbolumok `__all__`-ban szerepelnek. | import smoke |
| `CAVITY_CHILD_OUTSIDE_PARENT_CAVITY` tesztelve | PASS | `worker/cavity_validation.py:165`, `tests/worker/test_cavity_validation.py:104` | Outside containment eset hard-fail/reported issue. | `pytest test_cavity_validation.py` |
| `CAVITY_CHILD_CHILD_OVERLAP` tesztelve | PASS | `worker/cavity_validation.py:188`, `tests/worker/test_cavity_validation.py:145` | Sibling overlap detektalas Shapely intersection area alapon. | `pytest test_cavity_validation.py` |
| `CAVITY_QUANTITY_MISMATCH` tesztelve | PASS | `worker/cavity_validation.py:654`, `tests/worker/test_cavity_validation.py:201` | Quantity delta invarians es actual internal count check. | `pytest test_cavity_validation.py` |
| `strict=True` -> exception | PASS | `worker/cavity_validation.py:735`, `tests/worker/test_cavity_validation.py:135` | Strict modban `CavityValidationError` dobodik. | `pytest test_cavity_validation.py` |
| `strict=False` -> issue lista | PASS | `worker/cavity_validation.py:736`, `tests/worker/test_cavity_validation.py:297` | Nem-strict mod visszaadja a problemakat. | `pytest test_cavity_validation.py` |
| Shapely `covers()` alapu containment | PASS | `worker/cavity_validation.py:161` | Nem bbox-only check, hanem exact polygon coverage. | code review + tests |
| Modul nem ir fajlt / nem hiv DB-t | PASS | `worker/cavity_validation.py:1` | Csak in-memory geometria/validacio, nincs IO/DB import. | code review |

## 6) Transform logika
- `_build_placed_polygon()` lepesei:
  1. Outer ringbol Shapely polygon epitese.
  2. Forgatas `rotation_deg` szerint origora.
  3. Rotalt bbox min sarokra normalizalas.
  4. Eltolas abszolut (`x_abs`, `y_abs`) poziciora.
- `_build_transformed_cavity_polygon()` ugyanezt a normalizalas/eltolas referenciat hasznalja a parent hole gyurukre, hogy containment check ugyanabban a koordinatarendszerben tortenjen.

## 7) Advisory notes
- A validator jelenleg a cavity plan tree-bol szamolt internal darabszamot hasonlitja a `quantity_delta.internal_qty` ertekekhez.
- `CAVITY_TREE_DEPTH_EXCEEDED` es `CAVITY_TRANSFORM_INVALID` kodok implementalva vannak, bar explicit T08 tesztben nincs dedikalt fail fixture rajuk.

## 8) Follow-up
- T09/T10 integracios riportokban javasolt a validator issue code aggregaciojának publikálása.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-02T23:47:32+02:00 → 2026-05-02T23:50:34+02:00 (182s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/cavity_v2_t08_exact_nested_validator.verify.log`
- git: `main@807157b`
- módosított fájlok (git status): 35

**git diff --stat**

```text
 frontend/src/lib/types.ts                          |  18 +-
 frontend/src/pages/NewRunPage.tsx                  |   1 +
 tests/worker/test_cavity_prepack.py                | 342 +++++++++++-
 tests/worker/test_result_normalizer_cavity_plan.py | 577 ++++++++++++++++++++-
 worker/cavity_prepack.py                           | 483 ++++++++++++++++-
 worker/main.py                                     |   4 +
 worker/result_normalizer.py                        | 417 +++++++++++----
 7 files changed, 1743 insertions(+), 99 deletions(-)
```

**git status --porcelain (preview)**

```text
 M frontend/src/lib/types.ts
 M frontend/src/pages/NewRunPage.tsx
 M tests/worker/test_cavity_prepack.py
 M tests/worker/test_result_normalizer_cavity_plan.py
 M worker/cavity_prepack.py
 M worker/main.py
 M worker/result_normalizer.py
?? codex/codex_checklist/nesting_engine/cavity_v2_t01_audit_contract_snapshot.md
?? codex/codex_checklist/nesting_engine/cavity_v2_t02_ui_api_quality_prepack.md
?? codex/codex_checklist/nesting_engine/cavity_v2_t03_prepack_guard_hole_free.md
?? codex/codex_checklist/nesting_engine/cavity_v2_t04_plan_v2_contract.md
?? codex/codex_checklist/nesting_engine/cavity_v2_t05_holed_child_outer_proxy.md
?? codex/codex_checklist/nesting_engine/cavity_v2_t06_recursive_cavity_fill.md
?? codex/codex_checklist/nesting_engine/cavity_v2_t07_result_normalizer_v2_flatten.md
?? codex/codex_checklist/nesting_engine/cavity_v2_t08_exact_nested_validator.md
?? codex/reports/nesting_engine/cavity_v2_t01_audit_contract_snapshot.md
?? codex/reports/nesting_engine/cavity_v2_t01_audit_contract_snapshot.verify.log
?? codex/reports/nesting_engine/cavity_v2_t02_ui_api_quality_prepack.md
?? codex/reports/nesting_engine/cavity_v2_t02_ui_api_quality_prepack.verify.log
?? codex/reports/nesting_engine/cavity_v2_t03_prepack_guard_hole_free.md
?? codex/reports/nesting_engine/cavity_v2_t03_prepack_guard_hole_free.verify.log
?? codex/reports/nesting_engine/cavity_v2_t04_plan_v2_contract.md
?? codex/reports/nesting_engine/cavity_v2_t04_plan_v2_contract.verify.log
?? codex/reports/nesting_engine/cavity_v2_t05_holed_child_outer_proxy.md
?? codex/reports/nesting_engine/cavity_v2_t05_holed_child_outer_proxy.verify.log
?? codex/reports/nesting_engine/cavity_v2_t06_recursive_cavity_fill.md
?? codex/reports/nesting_engine/cavity_v2_t06_recursive_cavity_fill.verify.log
?? codex/reports/nesting_engine/cavity_v2_t07_result_normalizer_v2_flatten.md
?? codex/reports/nesting_engine/cavity_v2_t07_result_normalizer_v2_flatten.verify.log
?? codex/reports/nesting_engine/cavity_v2_t08_exact_nested_validator.md
?? codex/reports/nesting_engine/cavity_v2_t08_exact_nested_validator.verify.log
?? docs/nesting_engine/cavity_prepack_contract_v2.md
?? docs/nesting_engine/cavity_prepack_v1_audit.md
?? tests/worker/test_cavity_validation.py
?? worker/cavity_validation.py
```

<!-- AUTO_VERIFY_END -->
