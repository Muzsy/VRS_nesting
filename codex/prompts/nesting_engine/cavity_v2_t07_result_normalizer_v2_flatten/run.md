# Cavity v2 T07 — Result normalizer v2 tree flatten
TASK_SLUG: cavity_v2_t07_result_normalizer_v2_flatten

## Szerep
Senior Python coding agent vagy. A result normalizer v2 path-ját implementálod: rekurzív cavity tree flatten abszolút koordinátákkal.

## Cél
`_compose_cavity_transform()` és `_flatten_cavity_plan_v2_tree()` helper függvények implementálása. A `_normalize_solver_output_projection_v2()` v2 ága a `placement_trees`-t rekurzívan flatten-eli placement row-okká. Quantity mismatch hard fail.

## Olvasd el először
- `AGENTS.md`
- `canvases/nesting_engine/cavity_v2_t07_result_normalizer_v2_flatten.md`
- `codex/goals/canvases/nesting_engine/fill_canvas_cavity_v2_t07_result_normalizer_v2_flatten.yaml`
- `worker/result_normalizer.py` (TELJES fájl — különösen: placement_transform_point ~sor 137-152, _normalize_rotation_deg ~sor 251, _normalize_solver_output_projection_v2 ~sor 561, _append_placement_row belső függvény ~sor 673, _load_enabled_cavity_plan ~sor 233)
- `worker/cavity_prepack.py` (build_cavity_prepacked_engine_input_v2 output struktura)
- `tests/worker/test_result_normalizer_cavity_plan.py`
- T04 és T06 artefaktumok

## Engedélyezett módosítás
- `worker/result_normalizer.py`
- `tests/worker/test_result_normalizer_cavity_plan.py`

## Szigorú tiltások
- **Tilos a v1 branch-et (`cavity_plan_v1` ág) módosítani.**
- Tilos a `placement_transform_point()` helperét módosítani.
- Tilos a `_normalize_solver_output_projection_v1()` (BLF engine path) érinteni.
- Tilos a gyártási geometriából a lyukakat elveszíteni.
- Tilos quantity mismatch-t silent warning-gal elfogadni — hard fail kell.

## Végrehajtandó lépések (YAML steps sorrendben)

### Step 1: Kontextus olvasás
Olvasd el a teljes result_normalizer.py-t. Azonosítsd: `_load_enabled_cavity_plan()` hol van, a virtual_parts betöltési ciklus, az `_append_placement_row` belső függvény, a metrics_jsonb cavity_plan blokk.

### Step 2: _compose_cavity_transform() helper
A canvas spec alapján — `placement_transform_point()` és `_normalize_rotation_deg()` segítségével:
```python
def _compose_cavity_transform(*, parent_abs_x, parent_abs_y, parent_abs_rotation_deg,
                               child_local_x, child_local_y, child_local_rotation_deg
                               ) -> tuple[float, float, float]:
```

### Step 3: _flatten_cavity_plan_v2_tree() rekurzív flatten
A canvas spec alapján. Minden node-hoz:
- Ha `kind == "top_level_virtual_parent"`: abs = caller által adott
- Egyébként: `_compose_cavity_transform()` számolja
- `_append_placement_row()` hívása
- Rekurzív: `node.get("children")` iterálása

### Step 4: _normalize_solver_output_projection_v2() v2 ág
- `placement_trees` betöltése ha `cavity_plan_version == "cavity_plan_v2"`
- Virtual part lookup: ha v2, hívd a `_flatten_cavity_plan_v2_tree()`-t az összes children-re
- Quantity mismatch check (canvas spec szerinti ellenőrzés)
- V1 branch érintetlen

### Step 5: V2 normalizer tesztek
5 teszt a canvas spec szerint. Kritikus: `test_v2_rotated_parent_child_transform` — rotált parent esetén a child abs koordinátájának helyesnek kell lennie (compose transform teszt).

```bash
python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py
```

### Step 6: Checklist és report
### Step 7: Repo gate
```bash
./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t07_result_normalizer_v2_flatten.md
```

## Tesztelési parancsok
```bash
python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py
python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py -k "v2"
```

## Ellenőrzési pontok
- [ ] _compose_cavity_transform() létezik
- [ ] _flatten_cavity_plan_v2_tree() létezik és rekurzív
- [ ] V2 plan esetén placement_trees feldolgozódik
- [ ] Rotált parent esetén child abs koordináta helyes (transform compose)
- [ ] Quantity mismatch ResultNormalizerError-t dob
- [ ] V1 branch érintetlen, v1 tesztek zöldek
- [ ] metadata_jsonb-ben cavity_tree_depth mező megvan

## Elvárt végső jelentés
Magyar nyelvű report. DoD→Evidence. Rotált transform teszt kimenetének bizonyítéka (a várt abs koordinátákkal).

## Hiba esetén
Ha a transform pontossága eltér a vártól: ellenőrizd, hogy a `base_x=0.0, base_y=0.0` argumentumokat helyesen adod-e át a `placement_transform_point()`-nak. Ha a normalizer nem találja a `placement_trees`-t a cavity_plan-ban, ellenőrizd, hogy T06 az `_empty_plan_v2()` struktúrájában valóban a `placement_trees` kulcsot használja-e.
