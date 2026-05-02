# Cavity v2 T07 — Result normalizer v2 tree flatten

## Cél

A `worker/result_normalizer.py` bővítése: a `_normalize_solver_output_projection_v2()` feldolgozza a `cavity_plan_v2` `placement_trees` struktúráját. A rekurzív fa flatten abszolút koordinátákat számít minden szintre, a `placement_transform_point()` helper segítségével. A v1 path teljesen változatlan.

---

## Miért szükséges

A T06 által gyártott `cavity_plan_v2` plan `placement_trees` rekurzív node-okat tartalmaz. A jelenlegi normalizer csak a `cavity_plan_v1` lapos `internal_placements` listát kezeli. A T07 nélkül a v2 prepack outputja nem kerülhet a final placement projektbe — a nested child alkatrészek pozíciói nem számítódnak ki.

---

## Érintett valós fájlok

### Módosítandó:
- `worker/result_normalizer.py` — `_load_enabled_cavity_plan()`, `_normalize_solver_output_projection_v2()`, új helper függvények

### Tesztek:
- `tests/worker/test_result_normalizer_cavity_plan.py` — v2 recursive tesztek

---

## Nem célok / scope határok

- **Nem** módosítja a v1 normalizer path-t (`cavity_plan_v1` ág).
- **Nem** implementálja az exact validátort (az T08).
- **Nem** érinti a `_normalize_solver_output_projection_v1()` (BLF engine) függvényt.
- A `placement_transform_point()` már létező helper — **nem módosítja**.

---

## Részletes implementációs lépések

### 1. `_compose_cavity_transform()` helper

```python
def _compose_cavity_transform(
    *,
    parent_abs_x: float,
    parent_abs_y: float,
    parent_abs_rotation_deg: float,
    child_local_x: float,
    child_local_y: float,
    child_local_rotation_deg: float,
) -> tuple[float, float, float]:
    """Computes child absolute transform from parent absolute + child local transform."""
    abs_x, abs_y = placement_transform_point(
        local_x=child_local_x,
        local_y=child_local_y,
        tx=parent_abs_x,
        ty=parent_abs_y,
        rotation_deg=parent_abs_rotation_deg,
        base_x=0.0,
        base_y=0.0,
    )
    abs_rotation = _normalize_rotation_deg(parent_abs_rotation_deg + child_local_rotation_deg)
    return (_round6(abs_x), _round6(abs_y), _round6(abs_rotation))
```

### 2. `_flatten_cavity_plan_v2_tree()` rekurzív flatten

```python
def _flatten_cavity_plan_v2_tree(
    *,
    node: dict[str, Any],
    parent_abs_x: float,
    parent_abs_y: float,
    parent_abs_rotation_deg: float,
    sheet_index: int,
    part_index: dict[str, dict[str, Any]],
    cavity_plan_version: str,
    per_sheet_counter: dict[int, int],
    per_sheet_placed_area: dict[int, float],
    placement_rows: list[dict[str, Any]],
    depth: int = 0,
) -> None:
    """Rekurzívan flatteneli a placement tree node-okat placement row-okká."""
    part_revision_id = _require_str(node.get("part_revision_id"), field="placement_tree_node.part_revision_id")
    instance = _parse_nonnegative_int(node.get("instance"), field="placement_tree_node.instance")
    kind = str(node.get("kind") or "")
    local_x = _parse_finite_float(node.get("x_local_mm", 0.0), field="placement_tree_node.x_local_mm")
    local_y = _parse_finite_float(node.get("y_local_mm", 0.0), field="placement_tree_node.y_local_mm")
    local_rotation = _parse_finite_float(node.get("rotation_deg", 0.0), field="placement_tree_node.rotation_deg")

    if kind == "top_level_virtual_parent":
        # A parent abszolút pozíciója a solver output-ból jön (caller adja)
        abs_x, abs_y, abs_rotation = parent_abs_x, parent_abs_y, parent_abs_rotation_deg
    else:
        abs_x, abs_y, abs_rotation = _compose_cavity_transform(
            parent_abs_x=parent_abs_x,
            parent_abs_y=parent_abs_y,
            parent_abs_rotation_deg=parent_abs_rotation_deg,
            child_local_x=local_x,
            child_local_y=local_y,
            child_local_rotation_deg=local_rotation,
        )

    part = part_index.get(part_revision_id)
    if part is None:
        raise ResultNormalizerError(f"unknown part in cavity_plan_v2 tree: {part_revision_id}")

    parent_node_id = str(node.get("parent_node_id") or "")
    parent_cavity_index = node.get("parent_cavity_index")
    metadata: dict[str, Any] = {
        "normalizer_scope": "cavity_v2_tree_flatten",
        "engine_backend": "nesting_engine_v2",
        "part_code": part["part_code"],
        "part_definition_id": part["part_definition_id"],
        "source_geometry_revision_id": part["source_geometry_revision_id"],
        "selected_nesting_derivative_id": part["selected_nesting_derivative_id"],
        "instance": int(instance),
        "placement_scope": "top_level_parent" if kind == "top_level_virtual_parent" else "internal_cavity",
        "cavity_plan_version": cavity_plan_version,
        "cavity_tree_depth": int(depth),
    }
    if kind != "top_level_virtual_parent" and parent_node_id:
        metadata["parent_node_id"] = parent_node_id
        if parent_cavity_index is not None:
            metadata["parent_cavity_index"] = int(parent_cavity_index)
        metadata["local_transform"] = {
            "x_local_mm": _round6(local_x),
            "y_local_mm": _round6(local_y),
            "rotation_deg": _round6(local_rotation),
        }

    placement_index = per_sheet_counter.get(sheet_index, 0)
    per_sheet_counter[sheet_index] = placement_index + 1
    per_sheet_placed_area[sheet_index] = per_sheet_placed_area.get(sheet_index, 0.0) + float(part["area_mm2"])
    transform_jsonb = {
        "x": _round6(abs_x),
        "y": _round6(abs_y),
        "rotation_deg": _round6(abs_rotation),
        "sheet_index": int(sheet_index),
        "instance_id": f"{part_revision_id}:{instance}",
    }
    placement_rows.append({
        "sheet_index": int(sheet_index),
        "placement_index": int(placement_index),
        "part_revision_id": part_revision_id,
        "quantity": 1,
        "transform_jsonb": transform_jsonb,
        "bbox_jsonb": _transform_bbox(bbox=part["bbox"], x=abs_x, y=abs_y, rotation_deg=abs_rotation),
        "metadata_jsonb": metadata,
    })

    # Rekurzív children
    children = node.get("children") or []
    if isinstance(children, list):
        for child_node in children:
            if isinstance(child_node, dict):
                _flatten_cavity_plan_v2_tree(
                    node=child_node,
                    parent_abs_x=abs_x,
                    parent_abs_y=abs_y,
                    parent_abs_rotation_deg=abs_rotation,
                    sheet_index=sheet_index,
                    part_index=part_index,
                    cavity_plan_version=cavity_plan_version,
                    per_sheet_counter=per_sheet_counter,
                    per_sheet_placed_area=per_sheet_placed_area,
                    placement_rows=placement_rows,
                    depth=depth + 1,
                )
```

### 3. `_normalize_solver_output_projection_v2()` v2 ág

A `_normalize_solver_output_projection_v2()` függvényben (sor ~561) a cavity plan betöltése után adjunk hozzá version check-et:

```python
cavity_plan_version = str(cavity_plan.get("version")) if cavity_enabled else None

# v2 placement_trees betöltése
placement_trees: dict[str, dict[str, Any]] = {}
if cavity_enabled and cavity_plan_version == "cavity_plan_v2":
    trees_raw = _require_dict(
        cavity_plan.get("placement_trees", {}),
        field="cavity_plan.placement_trees"
    )
    placement_trees = trees_raw
```

A solver output placements ciklusában, ha a `part_id` egy virtual part:

```python
virtual = virtual_parts.get(part_id) if cavity_enabled else None
if virtual is not None:
    if cavity_plan_version == "cavity_plan_v2":
        # v2 path: placement_trees recursive flatten
        tree_node = placement_trees.get(part_id)
        if tree_node is None:
            raise ResultNormalizerError(f"missing placement_tree for virtual part: {part_id}")
        # v2 top-level virtual parent nem kerül placement row-ba önállóan
        # → csak a real parent kerül be, majd gyermekei
        parent_part_id = str(virtual["parent_part_revision_id"])
        parent_part = part_index.get(parent_part_id)
        if parent_part is None:
            raise ResultNormalizerError(f"missing parent part for v2 virtual: {parent_part_id}")
        parent_instance = int(virtual["parent_instance"])
        parent_instance_id = f"{parent_part_id}:{parent_instance}"
        # Parent placement (x, y, rotation jön a solver output-ból)
        parent_meta = {
            "normalizer_scope": "cavity_v2_tree_flatten",
            "engine_backend": "nesting_engine_v2",
            "part_code": parent_part["part_code"],
            "part_definition_id": parent_part["part_definition_id"],
            "source_geometry_revision_id": parent_part["source_geometry_revision_id"],
            "selected_nesting_derivative_id": parent_part["selected_nesting_derivative_id"],
            "instance": int(parent_instance),
            "placement_scope": "top_level_parent",
            "cavity_plan_version": cavity_plan_version,
            "solver_instance": int(instance),
        }
        _append_placement_row(
            sheet_index=sheet_index,
            part_revision_id=parent_part_id,
            instance_id=parent_instance_id,
            x=x, y=y, rotation_deg=rotation_deg,
            part=parent_part,
            metadata_jsonb=parent_meta,
        )
        # Rekurzív flatten a children-ekre
        for child_node in (tree_node.get("children") or []):
            if isinstance(child_node, dict):
                _flatten_cavity_plan_v2_tree(
                    node=child_node,
                    parent_abs_x=x,
                    parent_abs_y=y,
                    parent_abs_rotation_deg=rotation_deg,
                    sheet_index=sheet_index,
                    part_index=part_index,
                    cavity_plan_version=cavity_plan_version,
                    per_sheet_counter=per_sheet_counter,
                    per_sheet_placed_area=per_sheet_placed_area,
                    placement_rows=placement_rows,
                    depth=1,
                )
        continue
    else:
        # v1 path: meglévő logika változatlan (internal_placements lapos lista)
        # ... meglévő v1 branch kód ...
```

### 4. Quantity check bővítése

A placement_rows generálása után validálni kell, hogy a v2 tree flatten minden instance-t megadott:

```python
if cavity_plan_version == "cavity_plan_v2":
    quantity_delta = _require_dict(
        cavity_plan.get("quantity_delta", {}), field="cavity_plan.quantity_delta"
    )
    for part_id_raw, delta in quantity_delta.items():
        expected_internal = int(delta.get("internal_qty", 0))
        actual_internal = sum(
            1 for row in placement_rows
            if row["part_revision_id"] == str(part_id_raw)
            and row.get("metadata_jsonb", {}).get("placement_scope") == "internal_cavity"
        )
        if actual_internal != expected_internal:
            raise ResultNormalizerError(
                f"CAVITY_QUANTITY_MISMATCH: {part_id_raw} "
                f"expected_internal={expected_internal} actual={actual_internal}"
            )
```

---

## Adatmodell / contract változások

- Új `_compose_cavity_transform()` helper a `result_normalizer.py`-ban
- Új `_flatten_cavity_plan_v2_tree()` rekurzív függvény
- `metadata_jsonb` bővítése: `cavity_tree_depth`, `parent_node_id`, `local_transform`
- `normalizer_scope` = `"cavity_v2_tree_flatten"` az v2 row-oknál

---

## Backward compatibility szempontok

- A v1 branch (`cavity_plan_v1`) kód érintetlen
- `placement_transform_point()` helper változatlan
- Az v1 `internal_placements` feldolgozás nem módosul

---

## Hibakódok / diagnosztikák

| Kód | Leírás |
|-----|--------|
| `CAVITY_QUANTITY_MISMATCH` | Flatten után a belső instance count eltér az elvárttól |
| `ResultNormalizerError("missing placement_tree for virtual part: ...")` | v2 plan tree hiányzik |
| `ResultNormalizerError("unknown part in cavity_plan_v2 tree: ...")` | Part nem found a part_index-ben |

---

## Tesztelési terv

```bash
python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py
python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py -k "v2"
./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t07_result_normalizer_v2_flatten.md
```

Tesztesetek:
- `test_v2_single_level_cavity_flatten`: 1 parent, 1 child → helyes abs koordináta
- `test_v2_matrjoska_flatten`: A→B→C → mindhárom placement row helyes abs koordinátával
- `test_v2_rotated_parent_child_transform`: rotált parent esetén child abs pozíció helyes
- `test_v2_quantity_mismatch_raises`: quantity delta eltérés → `ResultNormalizerError`
- `test_v1_cavity_plan_unchanged`: v1 plan feldolgozás változatlan

---

## Elfogadási feltételek

- `_compose_cavity_transform()` és `_flatten_cavity_plan_v2_tree()` léteznek
- v2 plan esetén a tree rekurzívan flatten-elve lesz
- Minden child node abszolút koordinátája helyes (transform compose)
- v1 tesztek változatlanul zöldek
- Quantity mismatch hard fail-t okoz

---

## Rollback / safety notes

- A version check alapú routing garantálja, hogy v1 plan nem kerül v2 ágba
- Ha a v2 flatten hibás, csak a v2 prepack run-ok érintettek
- A `_compose_cavity_transform()` pure function — unit tesztelhető elszigetelten

---

## Dependency

- T04 (v2 schema) — kötelező
- T06 (recursive fill, placement_trees gyártja) — kötelező
