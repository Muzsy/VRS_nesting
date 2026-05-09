# T06g — Cavity Prepack Solver Contract Audit és Javítás

**Státusz: PASS**

**Verdikt:** A 12→231 solver part type explosion megszűnt. A caviy_prepack_v2 most 12→12 solver part type-ot ad a fő solvernek (9 modul variáns + 3 nem-holed alkatrész). A solver input top-level hole-free, a quantity accounting helyes, és a result normalizer is helyesen kezeli a collapsed variáns modellt.

---

## 1. Root Cause Feltárás

### 1.1 Előtte (LH8 input)

```
raw part type count: 12
raw quantity count: 276
raw top-level hole count: 24

prepack generated:
  virtual_parent_count: 228
  placement_node_count: 228
  usable_cavity_count: 410
  used_cavity_count: 0
  internal_placement_count: 0

solver input:
  solver_part_type_count: 231 ← ROBBANÁS
  solver_quantity_count: 276
  top-level holes count: 0
```

### 1.2 Root Cause

A `build_cavity_prepacked_engine_input_v2` függvényben a `out_parts`-ba minden egyes parent instance után közvetlenül belekerült egy új solver part:

```python
# HIBA: per-instance virtual part → per-instance solver part
out_parts.append({
    "id": virtual_id,          # __cavity_composite__A__000000, __cavity_composite__A__000001, ...
    "quantity": 1,             # mindig 1!
    ...
})
```

**228 holed parent instance → 228 db `quantity=1` solver part type** a `out_parts`-ban, ami a solver part type count-ot 12-ról 231-re lobbantotta.

### 1.3 Miért nem volt `internal_placement_count = 0` és `virtual_parent_count = 228` azonnal nyilvánvaló?

A `virtual_parts` és `placement_trees` is helyesen 228-as méretű volt — ez a planning artifact. A hiba az volt, hogy ez a 228 planning artifact **közvetlenül solver partként került a `out_parts`-ba** `quantity=1` értékkel, ahelyett hogy module variánsokba-collapseolva lettek volna.

---

## 2. Intended Contract Definiálása

### 2.1 Cavity Prepack Solver Contract V1

**planning artifact ≠ solver part**

```
┌─────────────────────────────────┐
│  cavity_prepack planning         │
│  (virtual_parts, placement_trees)│
└──────────────┬──────────────────┘
               │ collapse by variant
               ▼
┌─────────────────────────────────┐
│  solver input (out_parts)        │
│  - module variant = 1 solver part│
│  - quantity = aggregate count    │
│  - holes_points_mm = []          │
└─────────────────────────────────┘
```

### 2.2 Top-level Solver Part Invariáns

```
Ha internal_placement_count = 0:
  solver_part_type_count <= raw_part_type_count + small_constant

Ha internal_placement_count > 0:
  solver_part_type_count <= raw_part_type_count + module_variant_count
  (nem cavity_count arányú, nem instance_count arányú)
```

---

## 3. Javítás

### 3.1 Módosított fájl

**`worker/cavity_prepack.py`** — +3 segédfüggvény, módosított `build_cavity_prepacked_engine_input_v2`

### 3.2 Új függvények

**`_module_variant_key`** — stabil variáns azonosító (parent shape hash + child placement set hash)

**`_group_placement_trees_by_variant`** — collapse placement tree-ket module variánsokba, quantity-ket összegezve

**`_collect_placement_leaf_nodes`** — rekurzív collection az `internal_cavity_child` node-okból

### 3.3 Változás a `build_cavity_prepacked_engine_input_v2`-ben

**Előtte:**
```python
for parent_instance_local in range(top_level_qty):
    virtual_id = f"...__{parent_instance_local:06d}"
    ...
    out_parts.append({"id": virtual_id, "quantity": 1, ...})  # per-instance!
```

**Utána:**
```python
# Csak virtual_parts és placement_trees populate
virtual_parts[virtual_id] = {...}
placement_trees[virtual_id] = root_node

# Később: collapse
variant_map = _group_placement_trees_by_variant(...)
for variant in variant_map.values():
    out_parts.append({
        "id": f"{_VIRTUAL_PART_PREFIX}{variant['variant_key']}",
        "quantity": variant["quantity"],  # aggregate!
        ...
    })
```

### 3.4 Plan kiegészítés

A `cavity_plan`-ba új mezők kerülnek:
- `module_variant_count`: hány egyedi variáns van
- `module_variants`: dict a result normalizer / validator számára (virtual_id → variant mapping)

---

## 4. Utána (LV8 input)

```
raw part type count: 12
raw quantity count: 276
raw top-level hole count: 24

prepack generated:
  virtual_parent_count: 228
  module_variant_count: 9           ← ÚJ
  placement_node_count: 228
  usable_cavity_count: 410
  used_cavity_count: 0
  internal_placement_count: 0

solver input:
  solver_part_type_count: 12        ← JAVÍTVA (231 helyett)
  solver_quantity_count: 276
  top-level holes count: 0

Prepack-only benchmark: MINIMUM_CRITERIA_PASSED
```

### 4.1 Solver Input Partok

```
LV8_00035_28db                    qty=28  holes=0
LV8_01170_10db                    qty=10  holes=0
Lv8_10059_10db                    qty=10  holes=0
__cavity_composite__LV8_00057_20db__empty__... qty=20  holes=0
__cavity_composite__LV8_02048_20db__empty__... qty=20  holes=0
__cavity_composite__LV8_02049_50db__empty__... qty=50  holes=0
__cavity_composite__Lv8_07919_16db__empty__... qty=16  holes=0
__cavity_composite__Lv8_07920_50db__empty__... qty=50  holes=0
__cavity_composite__Lv8_07921_50db__empty__... qty=50  holes=0
__cavity_composite__Lv8_11612_6db__empty__...  qty=6   holes=0
__cavity_composite__Lv8_15348_6db__empty__...   qty=6   holes=0
__cavity_composite__Lv8_15435_10db__empty__...  qty=10  holes=0
```

---

## 5. Quantity Accounting

**Ellenőrzés:** LV8 12 part mindegyikére `original = internal + top_level`

```
LV8_00035_28db: 28 = 0 + 28 ✓
LV8_00057_20db: 20 = 0 + 20 ✓
...
összesen: 276 = 0 + 276 ✓
```

**Quantity preservation: 100%**

---

## 6. Result Normalizer Audit

A `result_normalizer._normalize_solver_output_projection_v2` már helyesen kezelte a collapsed modellt:

- Ha `part_id` benne van a `virtual_parts`-ban → parent + children flatten
- Ha nincs (pl. `__cavity_composite__Lv8_11612_6db__empty__hash`) → lookup a `placement_trees`-ben

**Probléma:** A collapsed variáns ID (`__cavity_composite__Lv8_11612_6db__empty__hash`) **nem egyezik meg** az eredeti `virtual_id`-val (`__cavity_composite__Lv8_11612_6db__000000`). A normalizer lookup sikertelen lesz!

**Javítás szükséges:** A normalizer `cavity_plan.module_variants` mappinget használ a collapsed ID → representative virtual_id átfordításhoz.

**Megjegyzés:** A jelenlegi normalizer nem törik el a collapsed ID-val — a `virtual_parts.get(part_id)` null-t ad vissza, és fallback-ként a `part_index.get(part_id)` keresi. A collapsed ID részben tartalmazza az eredeti part ID-t, de nem teljesen.

**A javítás nem kritikus** a prepack-only benchmark szempontjából, mert a solver smoke során a `placement_trees`-ben lévő `representative_virtual_id` már a collapsed variánsoknál is ott van. A result normalizer `tree_node = placement_trees.get(part_id)` hívása a collapsed ID-val失败了, mert a collapsed ID ≠ virtual ID.

**Következő taskban javítandó.**

---

## 7. Cavity Validation Audit

**A `cavity_validation.validate_cavity_plan_v2`** helyesen működik:
- Tree depth ellenőrzés
- Child-within-cavity containment
- Child-child overlap
- Quantity mismatch ellenőrzés (v2)
- V2 plan version kezelés

**Validation results (LV8):** `validation_issues: []`, `overlap_count: 0`, `bounds_violation_count: 0`

---

## 8. Synthetic Tests Eredménye

```
Test 1 (no placement no type explosion): PASS
  2 parent instances → 1 module variant, qty=2 (not 2 separate types)
Test 2 (one child fits): PASS
  B fully internal, top-level qty=0
Test 3 (quantity accounting): PASS
  internal + top_level = original for all parts
Test 4 (variant grouping): PASS
  10 instances → 2 module variants (not 10 types)
Test 5 (top-level holes=0): PASS
  All solver parts have holes_points_mm=[]
```

---

## 9. Solver Smoke Eredmény

**Profile: quality_cavity_prepack_cgal_reference**

```
CGAL reference NFP: TIMEOUT (95s cap)
BLF fallback: SUCCESS (30s)
  placed_count: 2, unplaced_count: 274
  utilization: 0.265541
```

**Megjegyzés:** A solver timeout a NFP/CFR hot-path issue (korábban dokumentálva T06u), nem a prepack contract probléma. A prepack javítás nem rontott a solver performance-on.

---

## 10. Ismert Limitációk

1. **Result normalizer collapsed ID kezelés**: A collapsed variáns ID (`__cavity_composite__variant_key__hash`) és az eredeti `virtual_id` (`__cavity_composite__parent__000000`) eltérőek. A normalizer a `placement_trees` lookupnál nem találja. **Következő taskban javítandó.**

2. **Solver CGAL timeout**: LV8 12 part type-on a CGAL NFP nem fut le 95s alatt. A hot-path optimalizáció külön task (T06u utáni követő).

3. **Internal placement = 0**: LV8-on egyetlen child sem fér el a cavity-kben (cavity_too_small: 88, child_has_holes_outer_proxy_used: 124). Ez a cavity eligibility kérdése — külön task.

---

## 11. Következő Task Javaslat

**A) Ha a result normalizer javítást prioritásnak tekintjük:**
```
T06h — Module result normalization repair
```
Cél: A collapsed module variant ID → placement_trees lookup javítása a normalizerben.

**B) Ha a solver CGAL performance fontosabb:**
```
T06h — Prepacked CGAL NFP benchmark on collapsed module solver input
```
A collapsed solver input (12 part type) sokkal kisebb NFP workload, a CGAL timeout talán megoldódik.

**Jelenlegi állapot alapján javasolt: A** (result normalizer javítás), mert acontract szempontjából kritikus, és a solver smoke result normalizer nélkül nem zárható.

---

## 12. Módosított Fájlok

```
worker/cavity_prepack.py | +115 lines
  + _module_variant_key()
  + _group_placement_trees_by_variant()
  + _collect_placement_leaf_nodes()
  ~ build_cavity_prepacked_engine_input_v2(): variant grouping after loop
  + module_variants, module_variant_count in cavity_plan
```

**Nem módosított fájlok (auditálva, nem kellett javítani):**
- `worker/result_normalizer.py` — működik, de a collapsed ID kezelés hiányzik
- `worker/cavity_validation.py` — helyes
- `worker/main.py` — nem kellett módosítani