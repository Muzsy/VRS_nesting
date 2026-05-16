# LV8 Density T05 — Phase 0 polygon-aware validation gate

## 🎯 Funkció

A T05 feladat célja a Phase 0 mérési higiénia következő kritikus eleme: a benchmark eredmények **kötelező polygon-aware validációs gate** alá helyezése.

A jelenlegi `scripts/experiments/lv8_2sheet_claude_validate.py` script AABB-alapú, konzervatív diagnosztikai validátor. Ez továbbra is megmaradhat legacy diagnosztikai eszközként, de a T05 után **nem dönthet binding PASS/FAIL validitásról**. A `summary.json` `valid` mezője csak akkor lehet `true`, ha:

1. a quantity / completion gate igaz,
2. a solver nem timeoutolt és return code rendben van,
3. a sheet count gate igaz,
4. a polygon-aware validation gate igaz.

A feladat a végleges `development_plan_packing_density_20260515.md` v2.2 terv Phase 0.3 pontjára épül.

---

## Valós repo-kiindulópontok a friss snapshot alapján

A T05 előtt ellenőrzött releváns állapot:

- `scripts/experiments/lv8_2sheet_claude_validate.py`
  - Létezik.
  - Docstringje explicit kimondja, hogy AABB-alapú, konzervatív validátor.
  - `validation_kind = "AABB-conservative"`.
  - Nem CAM-grade verdict.
- `worker/cavity_validation.py`
  - Létezik.
  - Tartalmazza a `validate_cavity_plan_v2()` függvényt.
  - A cavity prepack belső gyermek-elhelyezéseire polygon-aware ellenőrzést ad: child-within-cavity, child-child overlap, quantity mismatch.
  - Nem önmagában teljes top-level sheet validator; a T05-ben auditálni kell, pontosan mire használható.
- `scripts/benchmark_cavity_v2_lv8.py`
  - Már mutat mintát a `validate_cavity_plan_v2()` hívására.
- `scripts/experiments/lv8_2sheet_claude_search.py`
  - T04 után `engine_stats` blokkot ír a `summary.json`-ba.
  - Jelenlegi `valid` logika még alapvetően solver completion + quantity + sheet count alapján dönt.
  - A T05-ben ezt ki kell egészíteni polygon-aware validation gate-tel.
- T01 szerint a Phase 0 shadow fixture-családok:
  - LV8 276: `tests/fixtures/nesting_engine/ne2_input_lv8jav.json`
  - LV8 179: T01 által dokumentált / helyreállított útvonal
  - small synthetic / SA guard: `poc/nesting_engine/f2_4_sa_quality_fixture_v2.json`
  - contract_freeze: T01 reportban rögzített konkrét lista

---

## T05 scope

### T05 feladata

1. Auditálni a meglévő validációs útvonalakat:
   - legacy AABB validator: `scripts/experiments/lv8_2sheet_claude_validate.py`,
   - cavity validator: `worker/cavity_validation.py::validate_cavity_plan_v2`,
   - lehetséges engine-side feasibility reuse: `rust/nesting_engine/src/feasibility/`.
2. Létrehozni egy kötelező polygon-aware benchmark validator scriptet:
   - javasolt útvonal: `scripts/experiments/lv8_polygon_validator.py`.
3. A validator olvassa legalább:
   - fixture input,
   - prepacked solver input,
   - solver stdout,
   - cavity plan, ha létezik.
4. A validator outputoljon stabil JSON-t:
   - `validation_kind = "polygon-aware"`,
   - `valid_polygon_gate`,
   - `quantity_ok`,
   - `overlap_count`,
   - `clearance_count`,
   - `boundary_count`,
   - `cavity_validation_issue_count`,
   - `issues_sample`,
   - `legacy_aabb_validator = false`.
5. A T04 harnessben a `summary.json` kapjon polygon validation blokkot:
   - `polygon_validation`,
   - `valid_quantity_gate`,
   - `valid_polygon_gate`,
   - végső `valid = previous_completion_gate AND valid_polygon_gate`.
6. A legacy AABB validator maradjon elérhető diagnosztikai eszköznek, de ne írja felül a binding `valid` mezőt.
7. Adj hozzá célzott unit teszteket a validatorra és a summary merge logikára.

### T05 nem célja

- Nem ír új placement / nesting algoritmust.
- Nem módosítja az NFP cache-t.
- Nem módosítja a Phase 2+ scoring, lookahead, beam vagy LNS logikát.
- Nem hard-cutolja az SA→none váltást; az T06 shadow evidence után történik.
- Nem törli a legacy AABB validátort.
- Nem futtat hosszú LV8 benchmark mátrixot; az T06 scope.
- Nem módosítja a `PlacementResult` vagy `NestSheet` szerződést.

---

## Implementációs útmutató

### 1) Validator script

Javasolt új fájl:

```text
scripts/experiments/lv8_polygon_validator.py
```

Javasolt CLI:

```bash
python3 scripts/experiments/lv8_polygon_validator.py \
  --fixture tests/fixtures/nesting_engine/ne2_input_lv8jav.json \
  --prepacked-input <run_dir>/prepacked_solver_input.json \
  --solver-stdout <run_dir>/solver_stdout.json \
  --cavity-plan <run_dir>/cavity_plan.json \
  --required-instances 276 \
  --spacing-mm 10 \
  --margin-mm 10 \
  --out <run_dir>/polygon_validation.json
```

A script **ne függjön hosszú benchmark futástól**; meglévő solver output JSON-nal is futtatható legyen.

### 2) Top-level sheet polygon validation

A validatornak a solver top-level placements szintjén legalább ezt kell ellenőriznie:

- minden placement part_id-ja létezik a `prepacked_solver_input.json` `parts` blokkjában,
- a placement polygon előállítható `outer_points_mm` + `holes_points_mm` alapján,
- sheet boundary + margin,
- polygon-polygon overlap ugyanazon sheeten,
- polygon clearance / spacing ugyanazon sheeten,
- `sheets_used <= max_sheets`, ahol a harness vagy CLI megadja a limitet,
- quantity gate: `placed_instances == required_instances` és `unplaced` üres.

Használható Shapely, mert a repo worker validátora is Shapelyre épít.

**Fontos koordináta-konvenció:** ne találj ki új transzformációt. Auditáld a jelenlegi solver output és legacy validator konvencióját. A reportban rögzítsd, hogy a `x_mm`, `y_mm`, `rotation_deg` hogyan kerül polygon transzformációra. Ha a legacy AABB validator és a worker cavity validator eltérően normalizál rotáció után, a T05 reportban legyen explicit döntés és teszt.

### 3) Cavity validation reuse

Ha `cavity_plan.json` létezik és `version == "cavity_plan_v2"`, a validator hívja:

```python
from worker.cavity_validation import validate_cavity_plan_v2
```

A hívás mintája megtalálható:

```text
scripts/benchmark_cavity_v2_lv8.py
```

A `validate_cavity_plan_v2()` issue-k ne vesszenek el. A polygon validation output tartalmazza:

```json
{
  "cavity_validation_issue_count": 0,
  "cavity_validation_issues_sample": []
}
```

Ha nincs cavity plan vagy nem cavity v2, akkor:

- `cavity_validation_available = false`,
- ez önmagában ne legyen hard fail nem-prepack fixture esetén,
- prepack run esetén hiányzó cavity plan legyen issue.

### 4) Harness integration

Módosítandó:

```text
scripts/experiments/lv8_2sheet_claude_search.py
```

A `run_one()` végén, a `solver_stdout.json`, `prepacked_solver_input.json`, `cavity_plan.json` és `summary.json` írása környékén:

1. Hívd meg a polygon validator helperét vagy script-függvényét.
2. Írd ki:

```text
<out_dir>/polygon_validation.json
```

3. A `summary` tartalmazza:

```python
"polygon_validation": polygon_validation,
"valid_quantity_gate": quantity_ok,
"valid_polygon_gate": polygon_validation.get("valid_polygon_gate"),
"valid": completion_gate and quantity_ok and polygon_validation.get("valid_polygon_gate") is True,
```

A korábbi `valid` logika legyen külön változó, például:

```python
completion_gate = not timed_out and return_code == 0 and sheets_used > 0 and sheets_used <= 2
quantity_gate = len(unplaced) == 0 and placed_instances == required_instances
```

### 5) Legacy AABB validator státusz

A `scripts/experiments/lv8_2sheet_claude_validate.py` maradhat változatlanul. Ha a T05 implementáció mégis hozzáér, csak additive módosítás engedett:

- docstring vagy output mező pontosítása,
- `legacy_aabb_validator = true`.

A binding gate nem hivatkozhat erre mint végső validitásra.

---

## Engedélyezett módosítások

A T05 futása legfeljebb ezeket a fájlokat hozhatja létre vagy módosíthatja:

- `scripts/experiments/lv8_polygon_validator.py`
- `scripts/experiments/lv8_2sheet_claude_search.py`
- `tests/test_lv8_density_polygon_validator.py`
- `tests/test_lv8_density_polygon_validation_summary.py`
- `codex/codex_checklist/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.md`
- `codex/reports/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.md`
- `codex/reports/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.verify.log`

Opcionális, csak indokolt esetben:

- `scripts/experiments/lv8_2sheet_claude_validate.py` — csak legacy metadata/docstring additive módosítás.

Tilos módosítani:

- `rust/nesting_engine/src/**`
- `vrs_nesting/config/nesting_quality_profiles.py`
- `worker/cavity_validation.py`, kivéve ha egyértelmű bugot találsz; ilyen esetben STOP + report, ne javítsd T05-ben automatikusan.

---

## Definition of Done

- [ ] T04 report létezik és PASS vagy PASS_WITH_NOTES.
- [ ] A legacy AABB validator auditálva és reportban nem-binding státuszként jelölve.
- [ ] Új polygon-aware validator script létezik vagy a report egyértelműen indokolja, miért választott más drop-in implementációt.
- [ ] A polygon validator képes meglévő `solver_stdout.json` + `prepacked_solver_input.json` alapján futni.
- [ ] A polygon validator stabil JSON outputot ír `polygon_validation.json` néven.
- [ ] A `summary.json` tartalmazza a `polygon_validation`, `valid_quantity_gate`, `valid_polygon_gate` mezőket.
- [ ] A végső `summary["valid"]` nem lehet true, ha `valid_polygon_gate` false.
- [ ] Cavity plan v2 esetén `validate_cavity_plan_v2()` issue-k bekerülnek a polygon validation outputba.
- [ ] Nincs hosszú LV8 benchmark futtatás T05 alatt.
- [ ] Unit tesztek fedik legalább: valid non-overlap, polygon overlap, boundary violation, clearance violation, summary valid gating.
- [ ] Python syntax és célzott pytest zöld.
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.md` zöld.
- [ ] Report Standard v2 szerinti report és checklist elkészült.

---

## Kötelező ellenőrzések

Minimum célzott ellenőrzések:

```bash
python3 -m py_compile scripts/experiments/lv8_polygon_validator.py
python3 -m pytest tests/test_lv8_density_polygon_validator.py -q
python3 -m pytest tests/test_lv8_density_polygon_validation_summary.py -q
```

Ha a két tesztfájlt egyben implementálod, akkor egyetlen pytest parancs is elfogadható:

```bash
python3 -m pytest tests/test_lv8_density_polygon_validator.py tests/test_lv8_density_polygon_validation_summary.py -q
```

Full repo gate:

```bash
./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.md
```

Rust check nem kötelező, mert T05 nem módosíthat Rust fájlt. Ha mégis Rust módosításra lenne szükség, az T05 scope break; állj meg és reportold.

---

## Report követelmény

A T05 report elején státusz:

- `PASS`, ha minden DoD teljesült,
- `PASS_WITH_NOTES`, ha a gate működik, de van nem blokkoló advisory,
- `FAIL/BLOCKED`, ha nincs kötelező polygon-aware gate.

A report tartalmazza:

- validációs útvonal audit,
- választott implementáció indoklása,
- output JSON séma,
- T04 summary integration diff,
- célzott tesztek eredménye,
- DoD → Evidence Matrix,
- advisory notes legfeljebb 5 pontban,
- follow-up T06 számára.
