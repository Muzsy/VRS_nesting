PASS

## 1) Meta
- Task slug: `cavity_v2_t03_prepack_guard_hole_free`
- Kapcsolodo canvas: `canvases/nesting_engine/cavity_v2_t03_prepack_guard_hole_free.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/nesting_engine/fill_canvas_cavity_v2_t03_prepack_guard_hole_free.yaml`
- Futas datuma: `2026-05-02`
- Branch / commit: `main@807157b`
- Fokusz terulet: `Worker guard + unit tesztek`

## 2) Scope

### 2.1 Cel
- Hard-fail guard bevezetese prepack modra, hogy top-level lyukas part ne mehessen solver inputba.
- Guard futtatasa `worker/main.py`-ban csak `part_in_part=prepack` policy mellett.
- Celfuggveny unit teszt lefedes (pass/fail/multi-violator).

### 2.2 Nem-cel (explicit)
- Nem valtozott a prepack elhelyezesi logika.
- Nincs backend API vagy rust engine mod.
- Nincs uj fajl a kodban, csak meglevok bovultek.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `worker/cavity_prepack.py`
- `worker/main.py`
- `tests/worker/test_cavity_prepack.py`
- `codex/codex_checklist/nesting_engine/cavity_v2_t03_prepack_guard_hole_free.md`
- `codex/reports/nesting_engine/cavity_v2_t03_prepack_guard_hole_free.md`

### 3.2 Mi valtozott es miert
- Uj guard hibaosztaly: `CavityPrepackGuardError`.
- Uj guard fuggveny: `validate_prepack_solver_input_hole_free(...)`, amely `CAVITY_PREPACK_TOP_LEVEL_HOLES_REMAIN` koddal hard fail-t dob lyukas top-level part eseten.
- `worker/main.py` prepack agaban lokalis importtal guard fut a prepackelt solver inputon.
- Harom uj unit teszt kerult be a guard viselkedes igazolasara.

## 4) Verifikacio

### 4.1 Feladatfuggo ellenorzes
- `python3 -c "from worker.cavity_prepack import validate_prepack_solver_input_hole_free; print('OK')"` -> PASS
- `python3 -m pytest -q tests/worker/test_cavity_prepack.py` -> PASS (`10 passed`)
- `python3 -m pytest -q tests/worker/test_cavity_prepack.py -k "guard"` -> PASS (`3 passed, 7 deselected`)

### 4.2 Kotelezo repo gate
- `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t03_prepack_guard_hole_free.md` -> PASS (AUTO_VERIFY blokk frissul)

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| `CavityPrepackGuardError` letezik es `__all__`-ban van | PASS | `worker/cavity_prepack.py:21`, `worker/cavity_prepack.py:541` | A guard dedikalt hibaosztallyal rendelkezik es publikus exportkent elerheto. | import check |
| `validate_prepack_solver_input_hole_free` letezik es `__all__`-ban van | PASS | `worker/cavity_prepack.py:349`, `worker/cavity_prepack.py:545` | A validator implementalt es publikus API-kent exportalt. | import check |
| `CAVITY_PREPACK_TOP_LEVEL_HOLES_REMAIN` szerepel az exception message-ben | PASS | `worker/cavity_prepack.py:352`, `worker/cavity_prepack.py:366` | A message prefix mind invalid parts, mind holes violation eseten egyezo kodot hasznal. | guard unit tests |
| Violalo part ID-k az uzenetben | PASS | `worker/cavity_prepack.py:360`, `worker/cavity_prepack.py:364`, `tests/worker/test_cavity_prepack.py:297` | A validator gyujti es listazza a violalo part id-kat, tesztelve multi-violator esetre is. | `pytest -k "guard"` |
| `main.py` bekotes megvan | PASS | `worker/main.py:1604`, `worker/main.py:1609` | A guard a prepackelt input eloallitas utan, solver hivas elott fut. | source review |
| Guard csak `part_in_part=="prepack"` eseten fut | PASS | `worker/main.py:1609` | Feltetel explicit a `requested_part_in_part_policy == "prepack"` check. | source review |
| Meglevo cavity tesztek zoldek | PASS | `tests/worker/test_cavity_prepack.py:61` | A korabbi testcsomag a guard bovites utan is teljesen zold. | `python3 -m pytest -q tests/worker/test_cavity_prepack.py` |

## 6) Advisory notes
- A guard hiba a `CavityPrepackError` alosztalya, igy a meglvo hibaagak kompatibilisek maradtak.
- A validacio csak top-level `parts[].holes_points_mm` ellenorzes, nem geometry szemantikai validator.

## 7) Follow-up
- T06 elott ez a guard biztos gatat ad regresszio ellen, ha lyuk top-levelen maradna prepack modban.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-02T22:47:30+02:00 → 2026-05-02T22:50:32+02:00 (182s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/cavity_v2_t03_prepack_guard_hole_free.verify.log`
- git: `main@807157b`
- módosított fájlok (git status): 15

**git diff --stat**

```text
 frontend/src/lib/types.ts           | 18 ++++++++++++-
 frontend/src/pages/NewRunPage.tsx   |  1 +
 tests/worker/test_cavity_prepack.py | 51 ++++++++++++++++++++++++++++++++++++-
 worker/cavity_prepack.py            | 32 ++++++++++++++++++++++-
 worker/main.py                      |  4 +++
 5 files changed, 103 insertions(+), 3 deletions(-)
```

**git status --porcelain (preview)**

```text
 M frontend/src/lib/types.ts
 M frontend/src/pages/NewRunPage.tsx
 M tests/worker/test_cavity_prepack.py
 M worker/cavity_prepack.py
 M worker/main.py
?? codex/codex_checklist/nesting_engine/cavity_v2_t01_audit_contract_snapshot.md
?? codex/codex_checklist/nesting_engine/cavity_v2_t02_ui_api_quality_prepack.md
?? codex/codex_checklist/nesting_engine/cavity_v2_t03_prepack_guard_hole_free.md
?? codex/reports/nesting_engine/cavity_v2_t01_audit_contract_snapshot.md
?? codex/reports/nesting_engine/cavity_v2_t01_audit_contract_snapshot.verify.log
?? codex/reports/nesting_engine/cavity_v2_t02_ui_api_quality_prepack.md
?? codex/reports/nesting_engine/cavity_v2_t02_ui_api_quality_prepack.verify.log
?? codex/reports/nesting_engine/cavity_v2_t03_prepack_guard_hole_free.md
?? codex/reports/nesting_engine/cavity_v2_t03_prepack_guard_hole_free.verify.log
?? docs/nesting_engine/cavity_prepack_v1_audit.md
```

<!-- AUTO_VERIFY_END -->

