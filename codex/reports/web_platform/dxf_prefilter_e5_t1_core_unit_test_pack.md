PASS_WITH_NOTES

## 1) Meta
- Task slug: `dxf_prefilter_e5_t1_core_unit_test_pack`
- Kapcsolódó canvas: `canvases/web_platform/dxf_prefilter_e5_t1_core_unit_test_pack.md`
- Kapcsolódó goal YAML: `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e5_t1_core_unit_test_pack.yaml`
- Futás dátuma: `2026-04-22`
- Branch / commit: `main@be80160`
- Fókusz terület: `Tests`

## 2) Scope

### 2.1 Cél
- Uj, onallo `tests/test_dxf_preflight_core_unit_pack.py` cross-module pytest pack a T1->T6 core pipeline-ra.
- Valódi `_run_pipeline` T1->T6 chain helper, amelynek köztes rétegeredményei a cross-step invariánsok alapja.
- Minimum V1 scenario-k fixture-driven regressziója: 7 scenario, 10 test function.
- Strict vs lenient kimenet különbség explicit tesztelése külön `_lenient` / `_strict` párokban.
- Task-specifikus structural smoke a pack jelenlétének és scope-határainak determinisztikus bizonyítására.

### 2.2 Nem-cél (explicit)
- Termelési service kód módosítása (T1..T6 modulok érintetlenek maradnak).
- Meglévő E2 réteg-specifikus tesztfájlok újraírása vagy törlése.
- E3 runtime/persistence/route/artifact storage scope.
- E4 UI/intake/drawer/review flow scope.
- T7 diagnostics renderer / file-list projection scope.

## 3) Változások összefoglalója

### 3.1 Érintett fájlok
- Teszt:
  - `tests/test_dxf_preflight_core_unit_pack.py` (új)
- Smoke:
  - `scripts/smoke_dxf_prefilter_e5_t1_core_unit_test_pack.py` (új)
- Codex artefaktok:
  - `canvases/web_platform/dxf_prefilter_e5_t1_core_unit_test_pack.md`
  - `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e5_t1_core_unit_test_pack.yaml`
  - `codex/prompts/web_platform/dxf_prefilter_e5_t1_core_unit_test_pack/run.md`
  - `codex/codex_checklist/web_platform/dxf_prefilter_e5_t1_core_unit_test_pack.md`
  - `codex/reports/web_platform/dxf_prefilter_e5_t1_core_unit_test_pack.md`

### 3.2 Miért változtak?
- Teszt/smoke: az E5-T1 teljes taskja csak új tesztfájlok hozzáadásából áll; production kód nem módosult.
- Codex artefaktok: a canvas/YAML/prompt a tmp/task csomagból másolva, a checklist/report most jött létre.

## 4) Verifikáció

### 4.1 Kötelező parancs
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e5_t1_core_unit_test_pack.md` → lásd AUTO_VERIFY blokk

### 4.2 run.md szerinti célzott futtatások
- `python3 -m py_compile tests/test_dxf_preflight_core_unit_pack.py scripts/smoke_dxf_prefilter_e5_t1_core_unit_test_pack.py`
- `python3 -m pytest -q tests/test_dxf_preflight_core_unit_pack.py`
- `python3 scripts/smoke_dxf_prefilter_e5_t1_core_unit_test_pack.py`

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-04-22T00:37:12+02:00 → 2026-04-22T00:39:51+02:00 (159s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/dxf_prefilter_e5_t1_core_unit_test_pack.verify.log`
- git: `main@be80160`
- módosított fájlok (git status): 8

**git status --porcelain (preview)**

```text
?? canvases/web_platform/dxf_prefilter_e5_t1_core_unit_test_pack.md
?? codex/codex_checklist/web_platform/dxf_prefilter_e5_t1_core_unit_test_pack.md
?? codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e5_t1_core_unit_test_pack.yaml
?? codex/prompts/web_platform/dxf_prefilter_e5_t1_core_unit_test_pack/
?? codex/reports/web_platform/dxf_prefilter_e5_t1_core_unit_test_pack.md
?? codex/reports/web_platform/dxf_prefilter_e5_t1_core_unit_test_pack.verify.log
?? scripts/smoke_dxf_prefilter_e5_t1_core_unit_test_pack.py
?? tests/test_dxf_preflight_core_unit_pack.py
```

<!-- AUTO_VERIFY_END -->

## 5) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat |
|---|---|---|---|
| #1 Új dedikált core-pack pytest file | PASS | `tests/test_dxf_preflight_core_unit_pack.py` | Önálló fájl saját helper-rel, nem módosítja a meglévő E2 teszteket |
| #2 T1->T6 chain helper | PASS | `tests/test_dxf_preflight_core_unit_pack.py:L57-L90` `_run_pipeline` | Valódi T1->T6 sorrendet hív, köztes eredményeket adja vissza |
| #3 Minimum V1 scenario matrix | PASS | `tests/test_dxf_preflight_core_unit_pack.py:L96-L320` | 7 scenario, 10 test function (strict+lenient párok) |
| #4 Cross-step invariánsok | PASS | minden test function inspect/role/gap/dedupe/writer/gate szinten is állít | Nem csak a végső acceptance_outcome-ot nézi |
| #5 ezdxf dependency truth | PASS | `tests/test_dxf_preflight_core_unit_pack.py:L36` `pytest.importorskip("ezdxf")` | Explicit guard, nem rejtett dependency |
| #6 Task-specifikus structural smoke | PASS | `scripts/smoke_dxf_prefilter_e5_t1_core_unit_test_pack.py` | 6 ellenőrzési kategória, scope-határ védelem |
| #7 Meglévő tesztek érintetlenek | PASS | git diff: T1..T6 teszt fájlok nem módosultak | Additive pack, nem replacement |
| #8 Strict vs lenient truth | PASS | `_lenient` / `_strict` test párok d, f, g scenario-kban | Explicit outcome assertion mindkét módban |

## 6) Advisory notes (nem blokkoló)

- **Scenario c current-code truth:** A `test_small_gap_repaired` esetben a T3 repair sikeres (applied_gap_repairs >= 1, remaining = 0), de T2 `cut_like_open_path_on_canonical_layer` review_required jele megmarad a role_resolution-ban, így T6 `preflight_review_required`-et ad vissza — nem `accepted_for_import`-ot. Ez a jelenlegi T2 logika következménye (T2 inspect-time signal, T3 repair nem retroaktívan törli).
- **Scenario f fixture tervezés:** Az ambiguous gap partner teszthez egy valid closed outer ring szükséges ([-50,-50] to [200,150]), hogy T5/T6 importer probe sikerrel fusson. Enélkül T6 importer_failed miatt rejected-et adna vissza, nem az ambiguity signal miatt.
- **ezdxf guard szintje:** `pytest.importorskip("ezdxf")` module szinten van → egész pack skip-elődik ezdxf nélkül. Ez a helyes viselkedés (T5/T6 valódi DXF-et ír/olvas).

## 7) Follow-ups (opcionális)

- A T2 `cut_like_open_path_on_canonical_layer` signal és a T3 repair utáni "tisztítás" kérdése egy jövőbeli canvas-ban döntendő el (upstream signal retroaktív törlése vs jelenlegi megőrzés).
- Az E5-T1 pack alapként szolgálhat E5-T2+ fixture bővítéshez (pl. MARKING réteg, skipped entity, validator probe edge case-ek).
