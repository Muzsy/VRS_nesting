PASS

## 1) Meta
- Task slug: `cavity_v2_t07_result_normalizer_v2_flatten`
- Kapcsolodo canvas: `canvases/nesting_engine/cavity_v2_t07_result_normalizer_v2_flatten.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/nesting_engine/fill_canvas_cavity_v2_t07_result_normalizer_v2_flatten.yaml`
- Futas datuma: `2026-05-02`
- Branch / commit: `main@807157b`
- Fokusz terulet: `Result normalizer v2 recursive tree flatten`

## 2) Scope

### 2.1 Cel
- `cavity_plan_v2` esetben `placement_trees` rekurziv flatten implementalasa.
- Lokalis cavity transzformok abszolut koordinatava komponalasa.
- Quantity mismatch hard fail bevezetese.
- V1 branch backward compatibility megtartasa.

### 2.2 Nem-cel (explicit)
- V1 solver projection (`_normalize_solver_output_projection_v1`) nincs modositva.
- `placement_transform_point()` helper nincs modositva.
- Cavity exact validator nincs implementalva (T08 scope).

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `worker/result_normalizer.py`
- `tests/worker/test_result_normalizer_cavity_plan.py`
- `codex/codex_checklist/nesting_engine/cavity_v2_t07_result_normalizer_v2_flatten.md`
- `codex/reports/nesting_engine/cavity_v2_t07_result_normalizer_v2_flatten.md`

### 3.2 Mi valtozott es miert
- Uj helper kerult be:
  - `_compose_cavity_transform()` a parent abs + child local komponalasra,
  - `_count_diagnostics_by_code()` cavity diagnosztika aggregalashoz,
  - `_flatten_cavity_plan_v2_tree()` rekurziv node flattenhez.
- A `_normalize_solver_output_projection_v2()` most:
  - v2 eseten beolvassa a `placement_trees` strukturat,
  - virtual parent solver placement utan a tree child node-okat rekurzivan flatteneli,
  - v2 quantity delta alapjan hard-fail checket futtat (`CAVITY_QUANTITY_MISMATCH`).
- V2 metadata bovult (`cavity_tree_depth`, `parent_node_id`, `local_transform`) a flattenelt sorokon.
- V1 path valtozatlan logikaval maradt, csak a transform-szamitas helperre lett atkotve.

## 4) Verifikacio

### 4.1 Feladatfuggo ellenorzes
- `python3 -c "from worker.result_normalizer import placement_transform_point; print('normalizer OK')"` -> PASS
- `python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py -k "v2"` -> PASS (`6 passed, 3 deselected`)
- `python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py` -> PASS (`9 passed`)

### 4.2 Kotelezo repo gate
- `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t07_result_normalizer_v2_flatten.md` -> PASS (AUTO_VERIFY blokk frissul)

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| `_compose_cavity_transform()` letezik | PASS | `worker/result_normalizer.py:258` | Parent abs + child local transform komponalasa dedikalt helperbe kerult. | `pytest -k v2` |
| `_flatten_cavity_plan_v2_tree()` letezik es rekurziv | PASS | `worker/result_normalizer.py:292`, `worker/result_normalizer.py:394` | Node flatten + recursive child bejaras implementalva. | `pytest -k v2` |
| V2 plan eseten `placement_trees` feldolgozodik | PASS | `worker/result_normalizer.py:814`, `worker/result_normalizer.py:941` | V2 virtual part lookup utan tree child flatten fut. | `pytest -k v2` |
| Rotalt parent transform helyes | PASS | `tests/worker/test_result_normalizer_cavity_plan.py:689`, `tests/worker/test_result_normalizer_cavity_plan.py:774` | 90 fokos parent + child local transform eseten abs `(46, 62, 270)` igazolt. | `pytest -k v2` |
| Quantity mismatch `ResultNormalizerError`-t dob | PASS | `worker/result_normalizer.py:1057`, `tests/worker/test_result_normalizer_cavity_plan.py:779` | V2 internal darabszam elteresre hard fail tortenik `CAVITY_QUANTITY_MISMATCH` koddal. | `pytest -k v2` |
| V1 branch kompatibilis | PASS | `tests/worker/test_result_normalizer_cavity_plan.py:208`, `tests/worker/test_result_normalizer_cavity_plan.py:864` | V1 legacy teszt + explicit v1 kompatibilitas teszt zold. | `pytest tests/worker/test_result_normalizer_cavity_plan.py` |
| `metadata_jsonb.cavity_tree_depth` megvan | PASS | `worker/result_normalizer.py:356`, `worker/result_normalizer.py:927`, `tests/worker/test_result_normalizer_cavity_plan.py:568` | V2 flatten sorok metadatajaban a melyseg explicit kikerul. | `pytest -k v2` |

## 6) Advisory notes
- V2 cavity meta blokk mar tartalmaz `diagnostics_by_code` aggregaciot.
- V2 quantity check a flattenelt `internal_cavity` sorokat hasonlitja a `quantity_delta.internal_qty` ertekekhez.

## 7) Follow-up
- T08-ban az exact nested cavity validacio erre a flatten path-ra kell epuljon.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-02T23:35:52+02:00 → 2026-05-02T23:38:55+02:00 (183s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/cavity_v2_t07_result_normalizer_v2_flatten.verify.log`
- git: `main@807157b`
- módosított fájlok (git status): 30

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
?? docs/nesting_engine/cavity_prepack_contract_v2.md
?? docs/nesting_engine/cavity_prepack_v1_audit.md
```

<!-- AUTO_VERIFY_END -->
