PASS

# Report — SGH-Q15 `sgh_q15_cavity_prepack_v2_solver_hole_free_contract`

## Status

PASS. MAIN_SOLVER_MUST_BE_HOLE_FREE invariant proven and hardened. 376 tests pass.

## Dependency gate

- `codex/reports/egyedi_solver/sgh_q14_cde_touching_semantics_parity_fix.md`: first line `PASS`
- `SGH-Q15_STATUS: READY`: present in Q14 report

## 1) Meta

- **Task slug:** `sgh_q15_cavity_prepack_v2_solver_hole_free_contract`
- **Canvas:** `canvases/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract.md`
- **Goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q15_cavity_prepack_v2_solver_hole_free_contract.yaml`
- **Futás dátuma:** 2026-05-27
- **Branch / commit:** main
- **Fókusz terület:** Cavity Prepack v2 | Solver Hole-Free Invariant | Cavity Plan v2 | Result Normalizer

## 2) Scope

### 2.1 Cél

1. Bizonyítani és dokumentálni, hogy `build_cavity_prepacked_engine_input_v2(enabled=True)` után a solver input minden partján `holes_points_mm == []`.
2. Keményíteni a production boundary gate-t (`validate_prepack_solver_input_hole_free`).
3. 10 kötelező Q15 tesztet megírni és zöldre hozni.
4. Dokumentálni, hogy a `cavity_plan_v2` összes szükséges metaadatot megőrzi.
5. Igazolni, hogy `validate_cavity_plan_v2` futása kötelező a post-solve fázisban.

### 2.2 Nem-cél

- Main solver CDE hole-aware collision
- Part holes átadása a Rust/main solvernek
- cavity_prepack_v2 kiváltása
- Új optimizer/search stratégia
- DXF/preflight refaktor
- CDE production default bekapcsolása

## 3) Audit

### 3.1 Kötelező audit parancs eredménye

```
rg -n "build_cavity_prepacked_engine_input_v2|validate_prepack_solver_input_hole_free|..."
```

Találatok összefoglalója:
- `worker/cavity_prepack.py`: `validate_prepack_solver_input_hole_free` (line 1065), `build_cavity_prepacked_engine_input_v2` (line 900), `"holes_points_mm": []` explicit set (lines 1024, 1041)
- `worker/main.py`: prepack call (line 1716), gate call (line 1722), `validate_cavity_plan_v2` call (line 2002)
- `worker/result_normalizer.py`: `_flatten_cavity_plan_v2_tree` (line 292), `placement_trees` lookup (line 817), `internal_cavity` scope (line 339)
- `worker/cavity_validation.py`: `validate_cavity_plan_v2` (line 427), all error codes present

### 3.2 Prepack v2 architektúra

```text
base input:  holes_points_mm lehet nem üres (DXF/geometry manifest)
prepack:     virtual solver parts → holes_points_mm=[]  (line 1024)
             remaining top-level parts → holes_points_mm=[]  (line 1041)
gate:        validate_prepack_solver_input_hole_free (main.py line 1722)
solver:      outer-only input — nem hole-aware
post-solve:  validate_cavity_plan_v2 (main.py line 2002)
normalizer:  _flatten_cavity_plan_v2_tree → placement_scope: top_level_parent / internal_cavity
```

## 4) Implementáció

### 4.1 Production code változások

**Nincs szükség production code módosításra.** A MAIN_SOLVER_MUST_BE_HOLE_FREE invariant már implementálva volt:
- Virtual parts `holes_points_mm=[]` beállítva (`cavity_prepack.py` line 1024)
- Remaining top-level parts `holes_points_mm=[]` beállítva (`cavity_prepack.py` line 1041)
- `validate_prepack_solver_input_hole_free` gate megvan (`cavity_prepack.py` line 1065)
- Production wiring megvan (`main.py` lines 1716, 1722, 2002)
- `_flatten_cavity_plan_v2_tree` expansion megvan (`result_normalizer.py` line 292)

Q15 kizárólag tesztek és dokumentáció.

### 4.2 Cavity plan v2 metadata

```text
version         = "cavity_plan_v2"
virtual_parts   — solver ID → parent_part_revision_id, parent_instance, geom refs
placement_trees — solver ID → rekurzív node fa (parent + internal_cavity children)
instance_bases  — per part: internal_reserved_count, top_level_instance_base
quantity_delta  — per part: original_required_qty, internal_qty, top_level_qty
diagnostics     — per-cavity prepack döntés log
summary         — összesítő statisztikák
```

Invariant (bizonyítva): `internal_qty + top_level_qty == original_required_qty` minden partra.

### 4.3 Expansion

```text
_flatten_cavity_plan_v2_tree(node, parent_abs_x, parent_abs_y, parent_abs_rotation_deg, ...)
  root node (top_level_virtual_parent):
    placement_scope = "top_level_parent"
    abs_x = solver_placement.x_mm
    abs_y = solver_placement.y_mm
  child node (internal_cavity_child):
    placement_scope = "internal_cavity"
    abs_x = parent_abs_x + rotated(local_x, local_y).x
    abs_y = parent_abs_y + rotated(local_x, local_y).y
    metadata: parent_part_revision_id, parent_instance, cavity_tree_depth
```

### 4.4 Módosított fájlok

```
tests/worker/test_cavity_prepack.py                — 7 Q15 teszt hozzáadva
tests/worker/test_cavity_validation.py             — 2 Q15 teszt hozzáadva
tests/worker/test_result_normalizer_cavity_plan.py — 1 Q15 teszt hozzáadva
```

## 5) Tesztek

### Q15 kötelező tesztek (10/10 passing)

```
test_cavity_prepack_v2_outputs_hole_free_solver_input               ... ok
test_cavity_prepack_v2_virtual_parent_has_empty_holes_points        ... ok
test_cavity_prepack_v2_remaining_top_level_parts_have_empty_holes_points ... ok
test_validate_prepack_solver_input_hole_free_rejects_any_holes      ... ok
test_cavity_prepack_v2_preserves_placement_tree_metadata            ... ok
test_cavity_prepack_v2_quantity_delta_matches_internal_and_top_level ... ok
test_result_normalizer_expands_virtual_parent_to_internal_cavity_rows ... ok
test_validate_cavity_plan_v2_rejects_child_outside_cavity           ... ok
test_validate_cavity_plan_v2_rejects_child_child_overlap            ... ok
test_production_worker_rejects_or_blocks_hole_passthrough_without_prepack ... ok
```

### Összes teszt

```
python3 -m pytest tests worker -q -k "cavity or prepack or normalizer"
→ 45 passed in 0.52s

python3 -m pytest -q
→ 376 passed in 17.77s
```

## 6) Policy döntések összefoglalója

### PASS feltételek teljesítése

| Feltétel | Teljesítve |
|---|---|
| cavity_prepack_v2 után solver input hole-free | Igen — holes_points_mm=[] minden generated parton |
| Main solver hole-aware CDE NEM lett bevezetve | Igen — Q15 nem ad CDE hole collision support-ot |
| Cavity metadata megmarad a planben | Igen — virtual_parts, placement_trees, quantity_delta, stb. |
| Result normalizer visszaállítja internal placements-t | Igen — _flatten_cavity_plan_v2_tree |
| validate_cavity_plan_v2 fut és fail → no success | Igen — main.py line 2002, strict=True |
| Nincs silent hole passthrough | Igen — validate_prepack_solver_input_hole_free gate |
| verify zöld | Igen — lásd AUTO_VERIFY_START blokk |

### Explicit contract statement

```text
The main solver remains outer-only after cavity_prepack_v2.
Q15 does not implement CDE hole-aware item collision in the main solver.
Cavity semantics live in prepack + cavity_plan_v2 + validation + expansion.
```

## 7) Nem-blokkoló megjegyzések

1. **Cavity prepack disabled path**: Ha `cavity_prepack_enabled=False`, a `validate_prepack_solver_input_hole_free` gate nem fut. Ez dokumentált — a gate csak a prepack policy esetén kötelező.
2. **Module variant collapsing**: A v2 prepack összevonja az azonos parent+child kombinációkat egy solver partba (quantity>1). A `module_variants_by_solver_id` lookup ezt visszafordítja a normalizáló fázisban.

SGH-Q16_STATUS: READY

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-27T21:49:46+02:00 → 2026-05-27T21:52:41+02:00 (175s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract.verify.log`
- git: `main@1afe6dd`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 tests/worker/test_cavity_prepack.py                | 193 +++++++++++++++++++++
 tests/worker/test_cavity_validation.py             |  98 +++++++++++
 tests/worker/test_result_normalizer_cavity_plan.py | 103 +++++++++++
 3 files changed, 394 insertions(+)
```

**git status --porcelain (preview)**

```text
 M tests/worker/test_cavity_prepack.py
 M tests/worker/test_cavity_validation.py
 M tests/worker/test_result_normalizer_cavity_plan.py
?? canvases/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract.md
?? codex/codex_checklist/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q15_cavity_prepack_v2_solver_hole_free_contract.yaml
?? codex/prompts/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract/
?? codex/reports/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract.md
?? codex/reports/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract.verify.log
?? docs/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract.md
```

<!-- AUTO_VERIFY_END -->
