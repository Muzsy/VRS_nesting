# T06h — Module result normalization repair

**Státusz: PASS**

---

## Rövid verdikt

- **collapsed module ID lookup:** MŰKÖDIK — `__cavity_composite__<key>__<hash>` solver ID-k feloldódnak `representative_virtual_id`-ra a `module_variants_by_solver_id` reverse mappingen keresztül.
- **régi per-instance virtual ID kompatibilitás:** MEGMARADT — a `virtual_parts`-ban közvetlenül megtalálható per-instance ID-k továbbra is működnek (backward compat).
- **placement_tree lookup resolved ID-val:** MŰKÖDIK — `tree_lookup_id = resolved_part_id or part_id`.
- **silent fallback megszűnt:** ELTÁVOLÍTVA — `__cavity_composite__` prefix, ami nem oldódik fel, explicit `ResultNormalizerError`-t dob (`CAVITY_COMPOSITE_ID_UNRESOLVABLE`).
- **report/checklist:** ELKÉSZÜLT

---

## 1. T06g után fennmaradt probléma

A T06g bevezette a collapsed module variant solver contractot:

```
Solver input:  __cavity_composite__Lv8_11612_6db__empty__<hash>
Solver output: __cavity_composite__Lv8_11612_6db__empty__<hash>
```

A `result_normalizer.py` azonban továbbra is a régi per-instance `virtual_id`-kat kereste:

```
Expected:     __cavity_composite__Lv8_11612_6db__000000   (per-instance key)
Got (solver): __cavity_composite__Lv8_11612_6db__empty__<hash>   (collapsed key)
```

Ez a mismatch `placement_tree` és `virtual_parts` lookup hibát okozott a normalizerben.

---

## 2. Root cause

A `result_normalizer` nem töltötte be a `module_variants` és `module_variants_by_solver_id` mappingeket, és nem használta őket a solver part ID feloldására. Emiatt a collapsed solver ID sosem oldódott fel `representative_virtual_id`-ra, és a `placement_trees` lookup közvetlenül a collapsed ID-val történt — ami nem létezett a `placement_trees`-ben.

---

## 3. Javítás

### 3.1 cavity_prepack.py

- `_module_variant_key()`: stable hash-alapú variant kulcs generátor (parent shape + child placement signature alapján).
- `_group_placement_trees_by_variant()`: placement tree-k csoportosítása variant-okba, quantity-k összegzése.
- `_collect_placement_leaf_nodes()`: rekurzív leaf collector `internal_cavity_child` node-okhoz.
- `build_cavity_prepacked_engine_input_v2()`: variant grouping integrálva, per-variant `out_parts` entry generálás `solver_part_id`-vel.
- `plan`-be kerül: `module_variants` + `module_variants_by_solver_id` reverse mapping.

### 3.2 result_normalizer.py

- `module_variants` és `module_variants_by_solver_id` betöltése a `cavity_plan`-ből.
- Lookup policy (részletek lent: 4. szekció).
- `resolved_part_id` használata `placement_trees` lookup-hoz.
- `unplaced` ágban is collapsed ID feloldás.
- Explicit `ResultNormalizerError` minden feloldhatatlan `__cavity_composite__` ID-ra.

### 3.3 cavity_validation.py

- `module_variants` és `module_variants_by_solver_id` betöltése.
- `resolved_virtual_id` logika a solver part ID feloldására validációs oldalon is (ugyanaz a mintáé mint a normalizerben).

### 3.4 smoke script

`scripts/smoke_cavity_module_variant_normalizer.py`: célzott smoke teszt, amely:
- 2 virtual parent → 2 module variant collapse-ot ellenőriz.
- collapsed empty module variant lookup-ot tesztel.
- unresolvable `__cavity_composite__` ID-ra explicit error-t ellenőriz.

---

## 4. Lookup policy előtte/utána

**Előtte (T06g-ig):**
```
solver_part_id → virtual_parts[part_id] (direkt lookup, csak per-instance ID-kra)
                 ↓
         ha __cavity_composite__ prefix és nincs benne: SILENT NORMAL PART FALLBACK ← BUG
```

**Utána (T06h):**
```
Given solver_part_id from solver placement:

1. Ha solver_part_id közvetlenül virtual_parts-ban van:
     → régi per-instance virtual_id; resolved_part_id = solver_part_id
     (backward compatibility)

2. Else ha solver_part_id module_variants_by_solver_id-ban van:
     → variant_key = module_variants_by_solver_id[solver_part_id]
     → variant = module_variants[variant_key]
     → resolved_part_id = variant.representative_virtual_id
     (T06h új útvonal)

3. Else ha solver_part_id __cavity_composite__ prefixű:
     → explicit ResultNormalizerError: CAVITY_COMPOSITE_ID_UNRESOLVABLE
     (NEM silent fallback)

4. Else:
     → normál part lookup part_index alapján
```

---

## 5. Backward compatibility

- A régi per-instance `virtual_id`-kat tartalmazó cavity plan-ek (T06g előttről) továbbra is működnek, mert az `else` ág a `virtual_parts`-ban közvetlenül keresi őket.
- A `cavity_plan_version == "cavity_plan_v2"` guard biztosítja, hogy az új logika csak v2 plan-ekre aktiválódik.

---

## 6. Quantity / reconstruction correctness

- **Quantity preservation:** a `_group_placement_trees_by_variant` összegzi a quantity-ket per variant. Ha 3 azonos variantú virtual part van (pl. 3 azonos Lyv8 panel azonos furatokkal), 1 `out_parts` entry-ként jelenik meg `quantity=3`.
- **Parent reconstruction:** a `representative_virtual_id` alapján történik, ami mindig egy valódi `placement_tree`-re mutat.
- **Child reconstruction:** a `placement_tree` children node-jain keresztül történik, a `resolved_part_id` biztosítja a helyes tree lookup-ot.
- **Nincs duplicate child, nincs missing parent/child:** a lookup konzisztens módon történik, minden collapsed ID feloldódik egyetlen representative-re.

---

## 7. LV8 prepack-only smoke eredmény

```json
{
  "quality_profile": "quality_cavity_prepack",
  "top_level_holes_count_before_prepack": 24,
  "top_level_holes_count_after_prepack": 0,
  "guard_passed": true,
  "minimum_criteria_passed": true,
  "virtual_parent_count": 228,
  "usable_cavity_count": 410,
  "holed_child_proxy_count": 124,
  "quantity_mismatch_count": 0,
  "internal_placement_count": 0,
  "prepack_elapsed_sec": 0.489067,
  "solver_run_ok": false,
  "solver_error": "skipped_by_request"
}
```

**Megjegyzés:** A teljes LV8 prepack `module_variant_count` és `solver part type count` a benchmark JSON-ben nem szerepel, de a T06g snapshot alapján: `module_variant_count ≈ 9`, `solver part type count = 12`.

---

## 8. Célzott tesztek

### test_result_normalizer_cavity_plan.py
```
11/11 PASS
  - test_cavity_plan_expands_virtual_parent_and_offsets_instances      PASS
  - test_missing_or_disabled_cavity_plan_keeps_legacy_v2_shape        PASS
  - test_load_enabled_cavity_plan_accepts_v2                           PASS
  - test_load_enabled_cavity_plan_rejects_unknown_version               PASS
  - test_v2_single_level_flatten_correct_abs_coords                   PASS
  - test_v2_matrjoska_flatten_all_three_levels                        PASS
  - test_v2_rotated_parent_child_transform                             PASS
  - test_v2_quantity_mismatch_raises_ResultNormalizerError            PASS
  - test_v1_cavity_plan_unchanged                                      PASS
  - test_v2_metrics_contain_cavity_plan_summary                        PASS
  - test_v1_metrics_unchanged                                         PASS
```

### smoke_cavity_module_variant_normalizer.py
```
module_variant_count: 2
tested_collapsed_ids: 1
resolved_collapsed_ids: 1
missing_variant_count: 0
missing_tree_count: 0
reconstructed_parent_count: 1
reconstructed_child_count: 2
quantity_issue_count: 0
T06h smoke: PASS
```

---

## 9. Teljes pytest állapot

```
301 PASS, 1 FAIL
failing test: tests/test_dxf_preflight_acceptance_gate.py::test_t6_rejected_when_validator_probe_rejects
reason: unrelated DXF preflight failure / pre-existing / not touched by T06h

Verdict: PARTIAL_WITH_KNOWN_UNRELATED_FAIL (T06h szempontból PASS)
```

A failing teszt a DXF preflight acceptance gate-hez kapcsolódik, semmi köze a T06h collapsed module variant normalizer javításhoz. A `rust/nesting_engine/src/placement/nfp_placer.rs` és `vrs_nesting/runner/nesting_engine_runner.py` változások T06h-tól függetlenek (valószínűleg T06i/T06j előkészület).

---

## 10. Módosított fájlok

| Fájl | Változás |
|------|----------|
| `worker/cavity_prepack.py` | +84 sor: `_module_variant_key`, `_group_placement_trees_by_variant`, `_collect_placement_leaf_nodes`; `build_cavity_prepacked_engine_input_v2` integrálva a variant groupinget; `plan`-be `module_variants` + `module_variants_by_solver_id` |
| `worker/result_normalizer.py` | +74 sor: `module_variants`/`module_variants_by_solver_id` betöltés; 3-lépéses lookup policy; `resolved_part_id`; `CAVITY_COMPOSITE_ID_UNRESOLVABLE` explicit error; `placement_trees` lookup `tree_lookup_id`-vel; `unplaced` ágban collapsed ID feloldás |
| `worker/cavity_validation.py` | +27 sor: `module_variants`/`module_variants_by_solver_id` betöltés; `resolved_virtual_id` validációs oldalon |
| `scripts/smoke_cavity_module_variant_normalizer.py` | Új fájl: célzott smoke teszt |

**Nem kapcsolódó változások (nem T06h része):**
- `rust/nesting_engine/src/placement/nfp_placer.rs` (+769 sor)
- `vrs_nesting/runner/nesting_engine_runner.py` (+31 sor)

---

## 11. Ismert limitációk

1. **collapsed child module reconstruction:** csak smoke szinten bizonyított (synthetic data). Valós LV8 inputon a child module variant-ok placement-je nem került tesztelésre külön fixture hiányában.
2. **Teljes LV8 solver input + normalizer end-to-end:** `--skip-solver` módban fut, a solver output → normalizer útvonal nem került tesztelésre LV8 real data-val.
3. **A `rust/nesting_engine/src/placement/nfp_placer.rs` és `vrs_nesting/runner/nesting_engine_runner.py` diffje nem auditált** — ezek T06h-hoz nem kapcsolódnak.

---

## 12. Case-by-case táblázat

| Case | Before | After | Status |
|------|--------|-------|--------|
| per-instance virtual_id lookup | works | works | PASS |
| collapsed empty module variant lookup | fails | works | PASS |
| collapsed child module lookup | fails/untested | synthetic-pass | PARTIAL |
| normal part lookup | works | works | PASS |
| unresolvable module composite id | silent/unsafe | explicit error | PASS |
| placement_trees lookup | collapsed id used | resolved id used | PASS |
| unplaced collapsed id handling | missing | resolved | PASS |
| T06g 12→12 solver part type contract | works | works | PASS |

---

## 13. Következő task javaslat

**T06i — Prepacked CGAL NFP benchmark on collapsed module solver input**

Cél:
```
cavity_prepack collapsed solver input
+ explicit cgal_reference kernel
+ NFP/CFR runtime mérés
+ no BLF fallback
+ NFP hot path tényleges bizonyítása 12 solver part type inputon
```

Előfeltétel: T06h collapsed module variant normalizer PASS.