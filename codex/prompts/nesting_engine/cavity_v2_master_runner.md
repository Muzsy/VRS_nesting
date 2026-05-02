# Cavity v2 Master Runner — Engine v2 Cavity-Prepack v2 teljes fejlesztési lánc

## Cél

Ez a dokumentum leírja a T01–T10 fejlesztési lánc helyes futtatási sorrendjét, minden task kötelező tesztelési lépéseit, a checkpoint feltételeket és a végső auditot. Egy agent ezzel a dokumentummal önállóan végigviheti az egész `cavity_plan_v2` implementációt.

---

## Előfeltételek a teljes lánc indítása előtt

1. Olvasd el a `AGENTS.md`-t.
2. Ellenőrizd, hogy a v1 baseline tesztek zöldek:
   ```bash
   python3 -m pytest -q tests/worker/test_cavity_prepack.py
   python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py
   ```
3. Ha bármely v1 teszt piros: **NE INDÍTSD EL A LÁNCOT** — előbb fixeld a v1 hibákat.
4. Ellenőrizd, hogy a szükséges eszközök elérhetők:
   ```bash
   python3 --version
   python3 -c "import shapely; print('shapely OK')"
   python3 -c "import pytest; print('pytest OK')"
   ```

---

## Futtatási sorrend és függőségek

```
T01 (audit)   ──┐
                 ├── T03 (guard) ──────────────────────────────────────────────────────────┐
T02 (UI)    ───┘                                                                            │
                                                                                             │
                 T04 (v2 contract) ─── T05 (holed child) ─── T06 (recursive fill) ─────────┤
                                                                                             │
                                                             T07 (normalizer flatten) ───────┤
                                                                                             │
                                                             T08 (exact validator) ──────────┤
                                                                                             │
                                                             T09 (observability) ────────────┤
                                                                                             │
                                                             T10 (LV8 benchmark) ────────────┘
```

**Párhuzamosan futtatható:** T01 és T02 (egymástól független).
**Kötelező sorrend:** T04 → T05 → T06 → T07 → T08 → T09 → T10.
**T03** (guard) futtatható T01 után és T04 előtt, vagy párhuzamosan T04-gyel.

---

## Task-by-task végrehajtási utasítás

### CHECKPOINT-0: Baseline verify

```bash
python3 -m pytest -q tests/worker/test_cavity_prepack.py tests/worker/test_result_normalizer_cavity_plan.py
```
**Feltétel: 0 piros teszt. Ha van piros: STOP.**

---

### T01 — Cavity-prepack v1 audit és contract snapshot

**Runner prompt:** `codex/prompts/nesting_engine/cavity_v2_t01_audit_contract_snapshot/run.md`
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_cavity_v2_t01_audit_contract_snapshot.yaml`

**Kötelező lépések:**
```bash
python3 -m pytest -q tests/worker/test_cavity_prepack.py
python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py
./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t01_audit_contract_snapshot.md
```

**Elvárt output:** `docs/nesting_engine/cavity_prepack_v1_audit.md`

**CHECKPOINT-T01:**
- [ ] `docs/nesting_engine/cavity_prepack_v1_audit.md` létezik
- [ ] Baseline tesztek zöldek
- [ ] Nincs kódmódosítás

**Ha CHECKPOINT-T01 megbukik:** Ne folytasd T03/T04-gyel. Vizsgáld meg, miért nem teljesül a feltétel.

---

### T02 — quality_cavity_prepack UI/API elérhetővé tétele

**Runner prompt:** `codex/prompts/nesting_engine/cavity_v2_t02_ui_api_quality_prepack/run.md`
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_cavity_v2_t02_ui_api_quality_prepack.yaml`

**Kötelező lépések:**
```bash
cd frontend && npx tsc --noEmit
./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t02_ui_api_quality_prepack.md
```

**CHECKPOINT-T02:**
- [ ] TypeScript build hibátlan
- [ ] `QualityProfileName` tartalmazza `"quality_cavity_prepack"` literált

**Megjegyzés:** T02 nem blokkol más taskot. Ha a TypeScript build nem elérhető, rögzítsd és lépj tovább.

---

### T03 — Prepack guard: solver input top-level hole-free legyen

**Runner prompt:** `codex/prompts/nesting_engine/cavity_v2_t03_prepack_guard_hole_free/run.md`
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_cavity_v2_t03_prepack_guard_hole_free.yaml`

**Kötelező lépések:**
```bash
python3 -m pytest -q tests/worker/test_cavity_prepack.py
python3 -m pytest -q tests/worker/test_cavity_prepack.py -k "guard"
./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t03_prepack_guard_hole_free.md
```

**CHECKPOINT-T03:**
- [ ] `validate_prepack_solver_input_hole_free` importálható: `python3 -c "from worker.cavity_prepack import validate_prepack_solver_input_hole_free; print('OK')"`
- [ ] Guard tesztek zöldek
- [ ] Meglévő cavity tesztek zöldek

**Ha CHECKPOINT-T03 megbukik:** A guard kritikus biztonsági elem — ne lépj tovább T06-ra guard nélkül.

---

### T04 — Cavity plan v2 contract bevezetése

**Runner prompt:** `codex/prompts/nesting_engine/cavity_v2_t04_plan_v2_contract/run.md`
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_cavity_v2_t04_plan_v2_contract.yaml`

**Kötelező lépések:**
```bash
python3 -c "from worker.cavity_prepack import _PLAN_VERSION_V2; print('v2 constant OK')"
python3 -m pytest -q tests/worker/test_cavity_prepack.py
python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py
./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t04_plan_v2_contract.md
```

**CHECKPOINT-T04:**
- [ ] `_PLAN_VERSION_V2 = "cavity_plan_v2"` konstans megvan: `grep "cavity_plan_v2" worker/cavity_prepack.py`
- [ ] `_PlacementTreeNode` dataclass megvan: `grep "_PlacementTreeNode" worker/cavity_prepack.py`
- [ ] `docs/nesting_engine/cavity_prepack_contract_v2.md` létezik
- [ ] Minden v1 teszt zöld

---

### T05 — Lyukas child támogatása outer-only proxyval

**Runner prompt:** `codex/prompts/nesting_engine/cavity_v2_t05_holed_child_outer_proxy/run.md`
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_cavity_v2_t05_holed_child_outer_proxy.yaml`

**Kötelező lépések:**
```bash
python3 -m pytest -q tests/worker/test_cavity_prepack.py
python3 -m pytest -q tests/worker/test_cavity_prepack.py -k "holed_child"
./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t05_holed_child_outer_proxy.md
```

**CHECKPOINT-T05:**
- [ ] `child_has_holes_unsupported_v1` mellett nincs `continue` a `_candidate_children()`-ben: `grep -A 5 "child_has_holes_outer_proxy_used" worker/cavity_prepack.py`
- [ ] Holed child tesztek zöldek
- [ ] Meglévő solid child tesztek zöldek

---

### T06 — Rekurzív cavity fill algoritmus

**Runner prompt:** `codex/prompts/nesting_engine/cavity_v2_t06_recursive_cavity_fill/run.md`
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_cavity_v2_t06_recursive_cavity_fill.yaml`

**Kötelező lépések:**
```bash
python3 -c "from worker.cavity_prepack import build_cavity_prepacked_engine_input_v2; print('v2 entrypoint OK')"
python3 -m pytest -q tests/worker/test_cavity_prepack.py
python3 -m pytest -q tests/worker/test_cavity_prepack.py -k "v2"
./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t06_recursive_cavity_fill.md
```

**CHECKPOINT-T06 (KRITIKUS — NE LÉPJ TOVÁBB HA BÁRMELYIK MEGBUKIK):**
- [ ] `build_cavity_prepacked_engine_input_v2` importálható és exportálva
- [ ] Matrjoska teszt (A→B→C) zöld
- [ ] Ciklus védelem teszt zöld
- [ ] Quantity invariáns teszt zöld
- [ ] Top-level holes = 0 a v2 output-ban
- [ ] V1 `build_cavity_prepacked_engine_input` tesztek mind zöldek

**Ha CHECKPOINT-T06 megbukik:** T07, T08, T09, T10 nem futtatható. Javítsd a T06-ot.

---

### T07 — Result normalizer v2 tree flatten

**Runner prompt:** `codex/prompts/nesting_engine/cavity_v2_t07_result_normalizer_v2_flatten/run.md`
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_cavity_v2_t07_result_normalizer_v2_flatten.yaml`

**Kötelező lépések:**
```bash
python3 -c "from worker.result_normalizer import placement_transform_point; print('normalizer OK')"
python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py
python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py -k "v2"
./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t07_result_normalizer_v2_flatten.md
```

**CHECKPOINT-T07:**
- [ ] `_compose_cavity_transform` megvan: `grep "_compose_cavity_transform" worker/result_normalizer.py`
- [ ] `_flatten_cavity_plan_v2_tree` megvan: `grep "_flatten_cavity_plan_v2_tree" worker/result_normalizer.py`
- [ ] Rotált parent transform teszt zöld
- [ ] Quantity mismatch hard fail tesztelt
- [ ] V1 normalizer tesztek zöldek

---

### T08 — Exact nested cavity validator

**Runner prompt:** `codex/prompts/nesting_engine/cavity_v2_t08_exact_nested_validator/run.md`
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_cavity_v2_t08_exact_nested_validator.yaml`

**Kötelező lépések:**
```bash
python3 -c "from worker.cavity_validation import validate_cavity_plan_v2, CavityValidationError; print('validator OK')"
python3 -m pytest -q tests/worker/test_cavity_validation.py
./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t08_exact_nested_validator.md
```

**CHECKPOINT-T08:**
- [ ] `worker/cavity_validation.py` létezik
- [ ] `tests/worker/test_cavity_validation.py` létezik
- [ ] Minden hibakód tesztelt és zöld
- [ ] Strict mód `CavityValidationError`-t dob

---

### T09 — Report és observability bővítés

**Runner prompt:** `codex/prompts/nesting_engine/cavity_v2_t09_report_observability/run.md`
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_cavity_v2_t09_report_observability.yaml`

**Kötelező lépések:**
```bash
python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py
cd frontend && npx tsc --noEmit
./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t09_report_observability.md
```

**CHECKPOINT-T09:**
- [ ] `metrics_jsonb.cavity_plan` v2 mezők: `grep "internal_placement_count" worker/result_normalizer.py`
- [ ] TypeScript build hibátlan
- [ ] V1 metrics formátum változatlan

---

### T10 — LV8 benchmark run

**Runner prompt:** `codex/prompts/nesting_engine/cavity_v2_t10_lv8_benchmark/run.md`
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_cavity_v2_t10_lv8_benchmark.yaml`

**Kötelező lépések:**
```bash
python3 scripts/benchmark_cavity_v2_lv8.py --help
python3 -c "import ast; ast.parse(open('scripts/benchmark_cavity_v2_lv8.py').read()); print('syntax OK')"
# Ha fixture elérhető:
python3 scripts/benchmark_cavity_v2_lv8.py
./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t10_lv8_benchmark.md
```

**CHECKPOINT-T10 (minimum feltételek):**
- [ ] `scripts/benchmark_cavity_v2_lv8.py` szintaktikailag helyes
- [ ] Ha futott: `top_level_holes_after_prepack = 0`
- [ ] Ha futott: `quantity_mismatch_count = 0`
- [ ] Ha futott: `guard_passed = True`
- [ ] Ha futott: JSON artefaktum megvan `tmp/benchmark_results/`-ben

---

## Végső teljes lánc audit

Miután T01–T10 mind teljesített:

### 1. Teljes teszt suite futtatás
```bash
python3 -m pytest -q tests/worker/
```
Minden tesztnek zöldnek kell lennie.

### 2. Import ellenőrzés
```bash
python3 -c "
from worker.cavity_prepack import (
    build_cavity_prepacked_engine_input,
    build_cavity_prepacked_engine_input_v2,
    validate_prepack_solver_input_hole_free,
    CavityPrepackError,
    CavityPrepackGuardError,
)
from worker.result_normalizer import normalize_solver_output_projection
from worker.cavity_validation import validate_cavity_plan_v2, CavityValidationError
from vrs_nesting.config.nesting_quality_profiles import runtime_policy_for_quality_profile
print('All imports OK')
runtime_policy_for_quality_profile('quality_cavity_prepack')
print('quality_cavity_prepack profile OK')
"
```

### 3. V1 backward compat ellenőrzés
```bash
python3 -m pytest -q tests/worker/test_cavity_prepack.py -k "not v2"
python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py -k "not v2"
```

### 4. Dokumentáció ellenőrzés
```bash
ls docs/nesting_engine/cavity_prepack_contract_v1.md
ls docs/nesting_engine/cavity_prepack_contract_v2.md
ls docs/nesting_engine/cavity_prepack_v1_audit.md
```

### 5. Artefaktum lista ellenőrzés
```bash
ls codex/reports/nesting_engine/cavity_v2_t0*.md 2>/dev/null | sort
ls codex/reports/nesting_engine/cavity_v2_t10_*.md 2>/dev/null
ls codex/reports/nesting_engine/cavity_v2_t0*.verify.log 2>/dev/null | sort
```

### 6. Hibakód teljesség ellenőrzés
```bash
grep -rn "CAVITY_PREPACK_TOP_LEVEL_HOLES_REMAIN" worker/
grep -rn "CAVITY_CHILD_OUTSIDE_PARENT_CAVITY" worker/
grep -rn "CAVITY_CHILD_CHILD_OVERLAP" worker/
grep -rn "CAVITY_QUANTITY_MISMATCH" worker/
grep -rn "CAVITY_TRANSFORM_INVALID" worker/
```

---

## Kritikus nem-célok (amit soha nem szabad csinálni)

- **TILOS** a lyukakat végleg törölni a gyártási geometriából.
- **TILOS** silent NFP→BLF fallbacket elfogadni prepack módban.
- **TILOS** bbox-only fit alapján cavity elhelyezést elfogadni (Shapely exact kell).
- **TILOS** quantity mismatch-t warning-gal elfogadni — hard fail kell.
- **TILOS** a v1 `build_cavity_prepacked_engine_input()` logikáját módosítani.
- **TILOS** recursive tree-t validáció nélkül flatten-elni.
- **TILOS** `report.status=ok`-t adni ha top-level holes maradtak prepack módban.

---

## Gyors referencia táblázat

| Task | Fő output | Kötelező test parancs | Blokkol |
|------|-----------|----------------------|---------|
| T01 | cavity_prepack_v1_audit.md | pytest test_cavity_prepack.py | - |
| T02 | types.ts + NewRunPage.tsx | tsc --noEmit | - |
| T03 | cavity_prepack.py guard | pytest -k guard | T06+ |
| T04 | _PLAN_VERSION_V2, contract_v2.md | pytest test_cavity_prepack.py | T05, T06 |
| T05 | cavity_prepack.py outer proxy | pytest -k holed_child | T06 |
| T06 | build_cavity_prepacked_engine_input_v2 | pytest -k v2 | T07-T10 |
| T07 | result_normalizer.py v2 flatten | pytest test_result_normalizer | T08-T10 |
| T08 | cavity_validation.py | pytest test_cavity_validation | T10 |
| T09 | metrics_jsonb + UI panel | pytest + tsc | T10 |
| T10 | benchmark_cavity_v2_lv8.py | benchmark futtatás | - |

---

## Teljes lánc elfogadási feltételek

- T01–T10 minden task CHECKPOINT-ja teljesült
- `python3 -m pytest -q tests/worker/` = 0 piros teszt
- `from worker.cavity_prepack import build_cavity_prepacked_engine_input_v2` importálható
- `from worker.cavity_validation import validate_cavity_plan_v2` importálható
- `quality_cavity_prepack` kiválasztható a frontenden
- T10 benchmark (ha futott): top-level holes = 0, qty mismatch = 0

---

## Ha a lánc megszakad

Állj meg az első megbukott CHECKPOINT-nál. Ne lépj tovább egy megbukott feltétellel — a downstream task-ok hamis eredményt adhatnak.

Rögzítsd a pontos megbukott feltételt és a hibaüzenetet a task reportjában. Javítsd a problémát, majd futtasd újra a CHECKPOINT-ot.
