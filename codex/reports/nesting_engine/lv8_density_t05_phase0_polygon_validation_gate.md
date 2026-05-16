# Report — lv8_density_t05_phase0_polygon_validation_gate

**Státusz:** PASS

A `./scripts/verify.sh` (repo gate) zöld: minden T05 DoD pont teljesült. A polygon-aware
validator (Shapely-alapú) binding PASS gate-ként be van kötve a LV8 harness summaryba.
A unit tesztek 13+12 = 25/25 zöldek. A legacy AABB validator nem-binding diagnosztikává
minősül. Rust fájl nem módosult.

## 1) Meta

- **Task slug:** `lv8_density_t05_phase0_polygon_validation_gate`
- **Kapcsolódó canvas:** [canvases/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.md](../../../canvases/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.md)
- **Kapcsolódó goal YAML:** [codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t05_phase0_polygon_validation_gate.yaml](../../goals/canvases/nesting_engine/fill_canvas_lv8_density_t05_phase0_polygon_validation_gate.yaml)
- **T00 index:** [canvases/nesting_engine/lv8_density_task_index.md](../../../canvases/nesting_engine/lv8_density_task_index.md)
- **T00 master runner:** [codex/prompts/nesting_engine/lv8_density_master_runner.md](../../prompts/nesting_engine/lv8_density_master_runner.md)
- **T01 előzmény-report:** [codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md](lv8_density_t01_phase0_fixture_inventory.md) (PASS)
- **T02 előzmény-report:** [codex/reports/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md](lv8_density_t02_phase0_quality_profile_shadow_switch.md) (PASS)
- **T03 előzmény-report:** [codex/reports/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md](lv8_density_t03_phase0_nfp_diag_gate.md) (PASS)
- **T04 előzmény-report:** [codex/reports/nesting_engine/lv8_density_t04_phase0_engine_stats_export.md](lv8_density_t04_phase0_engine_stats_export.md) (PASS)
- **Forrásterv:** [codex/reports/nesting_engine/development_plan_packing_density_20260515.md](development_plan_packing_density_20260515.md)
- **Futás dátuma:** 2026-05-16
- **Branch / commit:** `main`
- **Fókusz terület:** Scripts (Python harness polygon-aware validation gate)

## 2) Scope

### 2.1 Cél

1. A meglévő validációs útvonalak auditálása (legacy AABB + cavity_validation.py).
2. Polygon-aware validator script (`lv8_polygon_validator.py`) létrehozása Shapely-alapon.
3. Koordináta-konvenció döntés: `cavity_validation.py` konvenciója (rotate → normalize → translate).
4. A validator bekötése a LV8 harness `run_one()` végén binding PASS gate-ként.
5. Unit tesztek hozzáadása (25 teszt, 2 fájlban).

### 2.2 Nem-cél (explicit)

1. Nem módosítja `rust/nesting_engine/src/**` (Rust scope tiltva).
2. Nem módosítja `worker/cavity_validation.py` (T05 scope tiltva).
3. Nem módosítja `vrs_nesting/config/nesting_quality_profiles.py`.
4. Nem futtat hosszú LV8 benchmark mátrixot.
5. A legacy AABB validator (`lv8_2sheet_claude_validate.py`) marad — csak nem-binding.

## 3) Változások összefoglalója (Change summary)

### 3.1 Érintett fájlok

- **Scripts (harness):**
  - [scripts/experiments/lv8_2sheet_claude_search.py](../../../scripts/experiments/lv8_2sheet_claude_search.py)
    — `_EXPERIMENTS_DIR` sys.path; `from lv8_polygon_validator import validate as _polygon_validate`;
    `completion_gate`/`quantity_gate` szétválasztás; `_polygon_validate()` hívás;
    `polygon_validation.json` kiírás; `valid_quantity_gate`, `valid_polygon_gate`,
    `polygon_validation` a summaryban; végső `valid` logika.
  - [scripts/experiments/lv8_polygon_validator.py](../../../scripts/experiments/lv8_polygon_validator.py)
    (új) — Shapely-alapú polygon validator; `_build_placed_polygon()`; `validate()` fn;
    CLI wrapper `main()`.
- **Tesztek:**
  - [tests/test_lv8_density_polygon_validator.py](../../../tests/test_lv8_density_polygon_validator.py) (új, 13 teszt)
  - [tests/test_lv8_density_polygon_validation_summary.py](../../../tests/test_lv8_density_polygon_validation_summary.py) (új, 12 teszt)
- **Codex artefaktok:**
  - [codex/codex_checklist/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.md](../../codex_checklist/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.md) (új)
  - [codex/reports/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.md](lv8_density_t05_phase0_polygon_validation_gate.md) (új, ez a fájl)
  - `codex/reports/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.verify.log` (a `verify.sh` írja)

Nem módosult Rust fájl. `rust/nesting_engine/src/**`, `worker/cavity_validation.py`,
`vrs_nesting/` érintetlen.

### 3.2 Miért változtak?

- **Harness + validator:** A T04 előtt a LV8 summary `valid` kizárólag AABB-konzervatív
  számoláson alapult (`lv8_2sheet_claude_validate.py`, `validation_kind = "AABB-conservative"`).
  Ez nem detektál polygon szintű átfedéseket (konkáv részek) és nem köti be a cavity_plan_v2
  validációt. T05 cél: polygon-aware Shapely gate legyen a binding döntési pont.
- **Tesztek:** A polygon gate determinisztikus viselkedését célzott unit tesztek fedik le
  (13 validator + 12 summary gate test), hogy a binding gate helyes legyen a Phase 0 pipeline-ban.

## 4) Validációs útvonal audit

### 4.1 Legacy AABB validator (`lv8_2sheet_claude_validate.py`)

- `validation_kind = "AABB-conservative"` — nem binding döntési pont.
- Koordináta-konvenció: affinity.rotate → affinity.translate (normalizáció **nélkül**).
- T05 után: megmarad diagnosztikai célra, de `summary["valid"]` nem tőle függ.

### 4.2 Cavity validation (`worker/cavity_validation.py`)

- `validate_cavity_plan_v2(*, cavity_plan, part_records, solver_placements, strict=True/False)`
  szignatúra: `strict=False` a harness hívásból.
- `_build_placed_polygon(*, outer_points_mm, x_abs, y_abs, rotation_deg)`:
  - `affinity.rotate(origin=(0,0))` → `normalize (min_x→0, min_y→0)` → `affinity.translate`
  - Ez az **autoritatív konvenció** T05-ben is.

### 4.3 Koordináta-konvenció döntés

| Lépés | cavity_validation.py (választott) | legacy AABB validator |
|---|---|---|
| Rotate | `affinity.rotate(origin=(0,0))` | `affinity.rotate(origin=(0,0))` |
| Normalize | `shift min_x→0, min_y→0` | **nincs** |
| Translate | `affinity.translate(x_mm, y_mm)` | `affinity.translate(x_mm, y_mm)` |

**Döntés:** A `cavity_validation.py` konvenciót alkalmazzuk, mert ez az autoritatív CAM-grade
cavity gate konvenciója. A legacy AABB validator eltérése (normalizáció hiánya) csak a
nem-binding diagnosztikában marad.

## 5) Verifikáció (How tested)

### 5.1 Kötelező parancsok

- `python3 -m py_compile scripts/experiments/lv8_polygon_validator.py` → OK
- `python3 -m pytest tests/test_lv8_density_polygon_validator.py -q` → **13 passed**
- `python3 -m pytest tests/test_lv8_density_polygon_validation_summary.py -q` → **12 passed**
- `./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.md`
  → eredmény az AUTO_VERIFY blokkban (5.4 alatt).

### 5.2 Validator tesztek (13 teszt, `test_lv8_density_polygon_validator.py`)

| Teszt osztály | Fedett eset |
|---|---|
| `TestValidNonOverlap` (2) | Két nem-átfedő rect PASS; quantity_ok True |
| `TestPolygonOverlap` (3) | Teljes átfedés FAIL; részleges átfedés FAIL; issues_sample tartalmaz `POLYGON_OVERLAP` kódot |
| `TestBoundaryViolation` (3) | Margin sértés FAIL; margón belüli PASS; sheet határon túl FAIL |
| `TestClearanceViolation` (2) | Gap < spacing_mm FAIL; gap ≥ spacing_mm PASS |
| `TestMissingGeometry` (1) | Hiányzó part_id a prepacked-ben FAIL |
| `TestPolygonTransform` (2) | Zero rotáció koordinátái; 90° rotáció + normalizáció bounds |

### 5.3 Summary gate tesztek (12 teszt, `test_lv8_density_polygon_validation_summary.py`)

| Teszt osztály | Fedett eset |
|---|---|
| `TestSummaryValidGate` (5) | Polygon gate True/False; `valid=False` ha polygon gate False; `valid=True` csak ha mind True; `valid=False` ha completion_gate False; `valid=False` ha quantity_gate False |
| `TestSummaryStructure` (4) | Kötelező kulcsok jelen; `validation_kind = "polygon-aware"`; `legacy_aabb_validator = False`; cavity_validation_available = False ha nincs plan |
| `TestPolygonGateIsBinding` (2) | `valid_polygon_gate` bool típusú; harness gate expression igazolja a polygon gate binding voltát |

### 5.4 Automatikus blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-16T23:01:58+02:00 → 2026-05-16T23:04:45+02:00 (167s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.verify.log`
- git: `main@abd4dbd`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 scripts/experiments/lv8_2sheet_claude_search.py | 31 +++++++++++++++++++++----
 1 file changed, 27 insertions(+), 4 deletions(-)
```

**git status --porcelain (preview)**

```text
 M scripts/experiments/lv8_2sheet_claude_search.py
?? canvases/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.md
?? codex/codex_checklist/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.md
?? codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t05_phase0_polygon_validation_gate.yaml
?? codex/prompts/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate/
?? codex/reports/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.md
?? codex/reports/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.verify.log
?? scripts/experiments/lv8_polygon_validator.py
?? tests/test_lv8_density_polygon_validation_summary.py
?? tests/test_lv8_density_polygon_validator.py
```

<!-- AUTO_VERIFY_END -->

## 6) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték | Magyarázat |
|---|---|---|---|
| #1 T04 PASS előfeltétel ellenőrizve | PASS | [lv8_density_t04_phase0_engine_stats_export.md](lv8_density_t04_phase0_engine_stats_export.md) státusz: PASS | T04 report elolvasva; minden T04 DoD pont PASS. |
| #2 Meglévő validációs útvonalak auditálva | PASS | [lv8_2sheet_claude_validate.py](../../../scripts/experiments/lv8_2sheet_claude_validate.py); [cavity_validation.py](../../../worker/cavity_validation.py); [benchmark_cavity_v2_lv8.py](../../../scripts/benchmark_cavity_v2_lv8.py) | Legacy AABB = non-binding; cavity_validation.py konvenció = autoritatív. Audit eredmény: 4) szekció. |
| #3 Koordináta-konvenció döntés rögzítve | PASS | 4.3 táblázat ebben a reportban | rotate → normalize → translate (cavity_validation.py); nem a legacy AABB konvenció. |
| #4 `lv8_polygon_validator.py` létrehozva Shapely-alapon | PASS | [scripts/experiments/lv8_polygon_validator.py](../../../scripts/experiments/lv8_polygon_validator.py) | `_build_placed_polygon()` + `validate()` + CLI `main()`; összes ellenőrzési típus implementálva. |
| #5 `valid_polygon_gate` binding gate a summaryban | PASS | [scripts/experiments/lv8_2sheet_claude_search.py](../../../scripts/experiments/lv8_2sheet_claude_search.py) — `valid = completion_gate and quantity_gate and polygon_validation.get("valid_polygon_gate") is True` | A `valid` csak akkor True, ha mindhárom gate True. |
| #6 Legacy AABB validator nem binding gate | PASS | A `lv8_2sheet_claude_validate.py` híváslánc nincs a binding `valid` logikában; `legacy_aabb_validator: False` a polygon validator outputban | T05 után a summary valid kizárólag polygon gate-en alapul. |
| #7 `polygon_validation.json` kiírva az out_dir-be | PASS | [scripts/experiments/lv8_2sheet_claude_search.py](../../../scripts/experiments/lv8_2sheet_claude_search.py) — `(out_dir / "polygon_validation.json").write_text(...)` | Minden `run_one()` hívás kiírja a polygon validation eredményt. |
| #8 Summary tartalmaz `valid_quantity_gate`, `valid_polygon_gate`, `polygon_validation` mezőket | PASS | [scripts/experiments/lv8_2sheet_claude_search.py](../../../scripts/experiments/lv8_2sheet_claude_search.py) summary dict | Mindhárom mező jelen a return dict-ben. |
| #9 Unit tesztek zöldek | PASS | `python3 -m pytest tests/test_lv8_density_polygon_validator.py -q` → 13 passed; `python3 -m pytest tests/test_lv8_density_polygon_validation_summary.py -q` → 12 passed | 25/25 teszt zöld. |
| #10 Hosszú LV8 benchmark nem futott; Rust fájl nem módosult | PASS | `git diff HEAD -- 'rust/**'` → üres; tesztek nem futtatnak engine-t | T05 kizárólag Python validator + teszt módosítás; Rust build nem szükséges. |
| #11 Output JSON séma stabil | PASS | [lv8_polygon_validator.py](../../../scripts/experiments/lv8_polygon_validator.py) `validate()` return dict | 17 mező, `validation_kind`, `valid_polygon_gate`, `legacy_aabb_validator: False` minden esetben. |
| #12 `./scripts/verify.sh --report …` zöld | PASS | AUTO_VERIFY blokk a 5.4 alatt | A repo gate lefutott. |
| #13 Checklist és report Report Standard v2 szerint | PASS | [Checklist](../../codex_checklist/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.md) + ez a fájl | Checklist pipálható DoD listával; report struktúra teljes. |

## 7) IO contract / minták

A `polygon_validation.json` minimális stabil séma (visszafelé kompatibilis bővítés):

```json
{
  "validation_kind": "polygon-aware",
  "valid_polygon_gate": true,
  "quantity_ok": true,
  "placed_instances": 276,
  "required_instances": 276,
  "unplaced_count": 0,
  "sheets_used": 2,
  "boundary_count": 0,
  "overlap_count": 0,
  "clearance_count": 0,
  "missing_geometry_count": 0,
  "cavity_validation_available": true,
  "cavity_validation_issue_count": 0,
  "cavity_validation_issues_sample": [],
  "issues_sample": [],
  "legacy_aabb_validator": false
}
```

## 8) Advisory notes (max 5)

1. A `_EPS = 1e-3` (0.001 mm) overlap tolerancia a Shapely numerikus stabilitásához szükséges;
   ennél kisebb területű metszet (`area ≤ _EPS`) nem számít overlappnek — ez floating point
   artefaktot szűr, nem valódi fizikai átfedést.
2. A clearance check (`poly_a.distance(poly_b)`) csak non-overlapping párokon fut (overlap esetén
   a clearance ellenőrzés kihagyva); ez szándékos — az overlap önmagában súlyosabb hiba.
3. `cavity_validation_available` csak `cavity_plan_v2` verzió esetén True; ha a fixture nincs
   cavity plan-nel párosítva (pl. 2-sheet solver outputok), a cavity gate 0 issue-t ad vissza
   és nem befolyásolja `valid_polygon_gate`-et.
4. A `issues_sample` legfeljebb 100 issue-t gyűjt belül, de csak 50-et exportál — longrun esetén
   a legfontosabb hibák elöl lesznek (boundary+overlap prioritású).
5. A `lv8_2sheet_claude_search.py` `_polygon_validate()` hívása `prepacked_input`-ot vár
   a polygon geometriákhoz (nem a fixture `parts`-t); ez egyezik a solver input konvencióval
   (virtuális alkatrészek a packer inputban).

## 9) Follow-ups

1. **T06** — Phase 0 baseline aggregálás (shadow run); a `valid_polygon_gate` és `polygon_validation`
   blokk T06 számára stabil forrás a quality scoring-hoz.
2. **T07 / cavity gate hardening** — ha cavity_plan_v2 rendszeresen elérhető, a `strict=False`
   paraméter felülvizsgálható.
3. **`_EPS` kalibráció** — ha a LV8 benchmark tényleges futáson sok hamis negativo clearance
   violation-t jelez, az `_EPS` értéke finomítható (1e-2 mm-re); jelenleg konzervatív.
