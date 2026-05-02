# Cavity v2 T06 — Rekurzív cavity fill algoritmus

## Cél

Implementálja a `worker/cavity_prepack.py`-ban a rekurzív cavity fill algoritmust, amely `cavity_plan_v2` outputot gyárt `placement_trees` struktúrával. A fő belépési pont: `build_cavity_prepacked_engine_input_v2()`. Az algoritmus lyukas child-okat outer proxyval kezel, és a lyukas child saját cavity-jeit rekurzívan tölti.

---

## Miért szükséges

A v1 lapos `internal_placements` modellje nem támogatja a matrjoska esetet (A parent → B child → C child a B cavityjében). A v2 rekurzív fa felépítése lehetővé teszi, hogy a solver input teljesen lyuk-mentes legyen még komplex, többszintű elhelyezések esetén is.

---

## Érintett valós fájlok

### Módosítandó:
- `worker/cavity_prepack.py` — új függvények, `build_cavity_prepacked_engine_input_v2()` belépési pont

### Tesztek:
- `tests/worker/test_cavity_prepack.py` — v2 recursive tesztesetek

---

## Nem célok / scope határok

- **Nem** módosítja a meglévő `build_cavity_prepacked_engine_input()` v1 függvényt.
- **Nem** implementálja a normalizer flatten logikát (az T07).
- **Nem** implementálja az exact nested validátort (az T08).
- Az algoritmus nem globálisan optimális — greedy + basic scoring.
- A mélységi limit paraméterezhető, alapértelmezés `max_cavity_depth=3`.

---

## Részletes implementációs lépések

### 1. Új segédfüggvények

#### `_build_usable_cavity_records()`

```python
@dataclass(frozen=True)
class _CavityRecord:
    parent_part_id: str
    parent_instance: int
    cavity_index: int
    cavity_polygon: Polygon
    cavity_bounds: tuple[float, float, float, float]
    usable_area_mm2: float

def _build_usable_cavity_records(
    *,
    parent: _PartRecord,
    parent_instance: int,
    min_usable_cavity_area_mm2: float,
    diagnostics: list[dict[str, Any]],
) -> list[_CavityRecord]:
    """Minden lyukhoz _CavityRecord-ot épít, kizárja az érvénytelen/túl kis lyukakat."""
    records: list[_CavityRecord] = []
    for cavity_index, cavity_ring in enumerate(parent.holes_points_mm):
        try:
            cavity_poly = _to_polygon(cavity_ring, [])
        except CavityPrepackError:
            diagnostics.append({
                "code": "invalid_cavity_polygon",
                "parent_part_id": parent.part_id,
                "cavity_index": cavity_index,
            })
            continue
        area = float(cavity_poly.area)
        if area < min_usable_cavity_area_mm2:
            diagnostics.append({
                "code": "cavity_too_small",
                "parent_part_id": parent.part_id,
                "cavity_index": cavity_index,
                "usable_area_mm2": round(area, 6),
            })
            continue
        records.append(_CavityRecord(
            parent_part_id=parent.part_id,
            parent_instance=parent_instance,
            cavity_index=cavity_index,
            cavity_polygon=cavity_poly,
            cavity_bounds=_ring_bbox(cavity_ring),
            usable_area_mm2=round(area, 6),
        ))
    return records
```

#### `_rank_cavity_child_candidates()`

```python
def _rank_cavity_child_candidates(
    *,
    cavity: _CavityRecord,
    part_records: list[_PartRecord],
    remaining_qty: dict[str, int],
    excluded_part_ids: set[str],
) -> list[_PartRecord]:
    """Szűri és rendezi a child jelölteket: nagyobb area > jobb fill ratio > part_code."""
    cav_area = cavity.usable_area_mm2
    cav_min_x, cav_min_y, cav_max_x, cav_max_y = cavity.cavity_bounds
    cav_w = cav_max_x - cav_min_x
    cav_h = cav_max_y - cav_min_y

    candidates: list[_PartRecord] = []
    for part in part_records:
        if part.part_id in excluded_part_ids:
            continue
        if int(remaining_qty.get(part.part_id, 0)) <= 0:
            continue
        if part.bbox_max_dim_mm > max(cav_w, cav_h):
            continue  # biztosan nem fér be
        candidates.append(part)

    candidates.sort(key=lambda p: (
        -float(p.area_mm2),
        float(p.area_mm2) / cav_area if cav_area > 0 else 0.0,
        p.part_code,
        p.part_id,
    ))
    return candidates
```

#### `_fill_cavity_recursive()`

```python
def _fill_cavity_recursive(
    *,
    cavity: _CavityRecord,
    part_records: list[_PartRecord],
    part_by_id: dict[str, _PartRecord],
    remaining_qty: dict[str, int],
    reserved_instance_ids: set[str],
    ancestor_part_ids: frozenset[str],
    next_instance: dict[str, int],
    depth: int,
    max_depth: int,
    min_usable_cavity_area_mm2: float,
    diagnostics: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Rekurzívan tölti a cavity-t, placement node listát ad vissza."""
    if depth > max_depth:
        diagnostics.append({"code": "max_cavity_depth_reached", "depth": depth})
        return []

    # Kizárt IDs: ancestor partok (ciklus védelem) + parent maga
    excluded = ancestor_part_ids | {cavity.parent_part_id}
    candidates = _rank_cavity_child_candidates(
        cavity=cavity,
        part_records=part_records,
        remaining_qty=remaining_qty,
        excluded_part_ids=excluded,
    )

    occupied: list[Polygon] = []
    placement_nodes: list[dict[str, Any]] = []

    for child in candidates:
        child_shapes = _rotation_shapes(child)
        while int(remaining_qty.get(child.part_id, 0)) > 0:
            placement = _try_place_child_in_cavity(
                cavity_polygon=cavity.cavity_polygon,
                cavity_bounds=cavity.cavity_bounds,
                child_shapes=child_shapes,
                occupied=occupied,
            )
            if placement is None:
                break
            x_local, y_local, rotation_deg, placed_poly = placement
            child_instance = int(next_instance.get(child.part_id, 0))
            next_instance[child.part_id] = child_instance + 1

            instance_key = f"{child.part_id}:{child_instance}"
            reserved_instance_ids.add(instance_key)
            remaining_qty[child.part_id] = int(remaining_qty[child.part_id]) - 1
            occupied.append(placed_poly)

            node_id = f"node:{child.part_id}:{child_instance}"
            node: dict[str, Any] = {
                "node_id": node_id,
                "part_revision_id": child.part_id,
                "instance": child_instance,
                "kind": "internal_cavity_child",
                "parent_node_id": f"node:{cavity.parent_part_id}:{cavity.parent_instance}",
                "parent_cavity_index": cavity.cavity_index,
                "x_local_mm": round(float(x_local), 6),
                "y_local_mm": round(float(y_local), 6),
                "rotation_deg": int(rotation_deg),
                "placement_origin_ref": "bbox_min_corner",
                "children": [],
            }

            # Rekurzív: ha child maga lyukas, fill its own cavities
            if child.holes_points_mm and depth < max_depth:
                new_ancestor_ids = ancestor_part_ids | {cavity.parent_part_id}
                child_cavity_records = _build_usable_cavity_records(
                    parent=child,
                    parent_instance=child_instance,
                    min_usable_cavity_area_mm2=min_usable_cavity_area_mm2,
                    diagnostics=diagnostics,
                )
                for child_cavity in child_cavity_records:
                    nested_nodes = _fill_cavity_recursive(
                        cavity=child_cavity,
                        part_records=part_records,
                        part_by_id=part_by_id,
                        remaining_qty=remaining_qty,
                        reserved_instance_ids=reserved_instance_ids,
                        ancestor_part_ids=new_ancestor_ids,
                        next_instance=next_instance,
                        depth=depth + 1,
                        max_depth=max_depth,
                        min_usable_cavity_area_mm2=min_usable_cavity_area_mm2,
                        diagnostics=diagnostics,
                    )
                    node["children"].extend(nested_nodes)

            placement_nodes.append(node)

    return placement_nodes
```

### 2. `build_cavity_prepacked_engine_input_v2()`

```python
def build_cavity_prepacked_engine_input_v2(
    *,
    snapshot_row: dict[str, Any],
    base_engine_input: dict[str, Any],
    enabled: bool,
    max_cavity_depth: int = 3,
    min_usable_cavity_area_mm2: float = 100.0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """V2 belépési pont: cavity_plan_v2 placement_trees struktúrával."""
    base = _require_dict(base_engine_input, field="base_engine_input")
    _require_str(base.get("version"), field="base_engine_input.version")
    _require_dict(snapshot_row, field="snapshot_row")

    out_input = deepcopy(base_engine_input)
    if not enabled:
        plan = _empty_plan_v2(enabled=False, max_cavity_depth=max_cavity_depth)
        return out_input, plan

    part_records = _build_part_records(snapshot_row, base)
    part_by_id = {p.part_id: p for p in part_records}
    remaining_qty: dict[str, int] = {p.part_id: int(p.quantity) for p in part_records}
    next_instance: dict[str, int] = {p.part_id: 0 for p in part_records}
    reserved_instance_ids: set[str] = set()
    diagnostics: list[dict[str, Any]] = []
    virtual_parts: dict[str, dict[str, Any]] = {}
    placement_trees: dict[str, dict[str, Any]] = {}
    out_parts: list[dict[str, Any]] = []

    holed_parents = [p for p in part_records if p.holes_points_mm and p.quantity > 0]

    for parent in holed_parents:
        for parent_instance in range(parent.quantity):
            virtual_id = f"{_VIRTUAL_PART_PREFIX}{parent.part_id}__{parent_instance:06d}"
            cavity_records = _build_usable_cavity_records(
                parent=parent,
                parent_instance=parent_instance,
                min_usable_cavity_area_mm2=min_usable_cavity_area_mm2,
                diagnostics=diagnostics,
            )

            root_node: dict[str, Any] = {
                "node_id": f"node:{parent.part_id}:{parent_instance}",
                "part_revision_id": parent.part_id,
                "instance": parent_instance,
                "kind": "top_level_virtual_parent",
                "parent_node_id": None,
                "parent_cavity_index": None,
                "x_local_mm": 0.0,
                "y_local_mm": 0.0,
                "rotation_deg": 0,
                "placement_origin_ref": "bbox_min_corner",
                "children": [],
            }

            for cavity in cavity_records:
                child_nodes = _fill_cavity_recursive(
                    cavity=cavity,
                    part_records=part_records,
                    part_by_id=part_by_id,
                    remaining_qty=remaining_qty,
                    reserved_instance_ids=reserved_instance_ids,
                    ancestor_part_ids=frozenset({parent.part_id}),
                    next_instance=next_instance,
                    depth=1,
                    max_depth=max_cavity_depth,
                    min_usable_cavity_area_mm2=min_usable_cavity_area_mm2,
                    diagnostics=diagnostics,
                )
                root_node["children"].extend(child_nodes)

            virtual_parts[virtual_id] = {
                "kind": "parent_composite",
                "parent_part_revision_id": parent.part_id,
                "parent_instance": parent_instance,
                "source_geometry_revision_id": parent.source_geometry_revision_id,
                "selected_nesting_derivative_id": parent.selected_nesting_derivative_id,
            }
            placement_trees[virtual_id] = root_node
            out_parts.append({
                "id": virtual_id,
                "quantity": 1,
                "allowed_rotations_deg": list(parent.allowed_rotations_deg),
                "outer_points_mm": deepcopy(parent.outer_points_mm),
                "holes_points_mm": [],
            })

        remaining_qty[parent.part_id] = 0

    # Non-holed parts: maradék quantity
    for part in part_records:
        if part.holes_points_mm:
            continue
        qty = int(remaining_qty.get(part.part_id, 0))
        if qty <= 0:
            continue
        out_parts.append({
            "id": part.part_id,
            "quantity": qty,
            "allowed_rotations_deg": list(part.allowed_rotations_deg),
            "outer_points_mm": deepcopy(part.outer_points_mm),
            "holes_points_mm": [],
        })

    # Quantity delta számítás
    quantity_delta: dict[str, dict[str, int]] = {}
    instance_bases: dict[str, dict[str, int]] = {}
    for part in part_records:
        original = int(part.quantity)
        remaining = int(remaining_qty.get(part.part_id, 0))
        internal = original - remaining
        if internal > 0:
            quantity_delta[part.part_id] = {
                "original_required_qty": original,
                "internal_qty": internal,
                "top_level_qty": remaining,
            }
            instance_bases[part.part_id] = {
                "internal_reserved_count": internal,
                "top_level_instance_base": internal,
            }

    out_parts.sort(key=lambda item: str(item.get("id") or ""))
    out_input["parts"] = out_parts

    plan = _empty_plan_v2(enabled=True, max_cavity_depth=max_cavity_depth)
    plan["virtual_parts"] = virtual_parts
    plan["placement_trees"] = placement_trees
    plan["instance_bases"] = instance_bases
    plan["quantity_delta"] = quantity_delta
    plan["diagnostics"] = diagnostics
    plan["summary"] = {
        "virtual_parent_count": len(virtual_parts),
        "usable_cavity_count": sum(
            len(t.get("children", [])) for t in placement_trees.values()
        ),
    }
    return out_input, plan
```

### 3. Exportálás

`__all__` bővítése:
```python
"build_cavity_prepacked_engine_input_v2",
```

### 4. Tesztek

```python
def test_v2_matrjoska_three_level():
    """A → B (B lyukas) → C matrjoska elhelyezés."""
    parts = [
        {"id": "A", "quantity": 1, "allowed_rotations_deg": [0],
         "outer_points_mm": _rect(0, 0, 200, 200),
         "holes_points_mm": [_rect(10, 10, 190, 190)]},
        {"id": "B", "quantity": 1, "allowed_rotations_deg": [0],
         "outer_points_mm": _rect(0, 0, 80, 80),
         "holes_points_mm": [_rect(10, 10, 70, 70)]},  # B maga is lyukas
        {"id": "C", "quantity": 1, "allowed_rotations_deg": [0],
         "outer_points_mm": _rect(0, 0, 30, 30),
         "holes_points_mm": []},
    ]
    snapshot = _snapshot_for_parts(parts)
    base = _base_input(parts)
    from worker.cavity_prepack import build_cavity_prepacked_engine_input_v2
    out_input, plan = build_cavity_prepacked_engine_input_v2(
        snapshot_row=snapshot, base_engine_input=base, enabled=True
    )
    assert plan["version"] == "cavity_plan_v2"
    # A top-level inputban nincs lyuk
    for part in out_input["parts"]:
        assert part["holes_points_mm"] == []
    # C eltűnt a top-level-ből (belső elhelyezés)
    top_level_ids = {p["id"] for p in out_input["parts"]}
    assert "C" not in top_level_ids

def test_v2_cycle_protection():
    """Ciklus védelme: A parent nem kerülhet saját cavityjébe."""
    parts = [
        {"id": "A", "quantity": 2, "allowed_rotations_deg": [0],
         "outer_points_mm": _rect(0, 0, 100, 100),
         "holes_points_mm": [_rect(10, 10, 90, 90)]},
    ]
    snapshot = _snapshot_for_parts(parts)
    base = _base_input(parts)
    from worker.cavity_prepack import build_cavity_prepacked_engine_input_v2
    out_input, plan = build_cavity_prepacked_engine_input_v2(
        snapshot_row=snapshot, base_engine_input=base, enabled=True
    )
    # Az A nem kerülhet saját cavityjébe
    for tree in plan["placement_trees"].values():
        for child in tree.get("children", []):
            assert child["part_revision_id"] != "A"

def test_v2_quantity_invariant():
    """internal_qty + top_level_qty == original_required_qty minden partra."""
    # ... teszteset ...
```

---

## Adatmodell / contract változások

- `placement_trees` mező a `cavity_plan_v2`-ben (T04-ben definiált schema szerint)
- `build_cavity_prepacked_engine_input_v2()` publikus függvény
- Új helper függvények (belső): `_build_usable_cavity_records`, `_rank_cavity_child_candidates`, `_fill_cavity_recursive`

---

## Backward compatibility szempontok

- A meglévő `build_cavity_prepacked_engine_input()` (v1) **változatlan** marad
- A v2 belépési pont egy **új** funkció, nem módosítja a v1-et
- A v1 tesztek mind zöldek maradnak

---

## Hibakódok / diagnosztikák

| Kód | Leírás |
|-----|--------|
| `invalid_cavity_polygon` | Érvénytelen cavity polygon |
| `cavity_too_small` | Cavity area < min_usable_cavity_area_mm2 |
| `max_cavity_depth_reached` | Mélységi limit elérve |
| `child_has_holes_outer_proxy_used` | Lyukas child outer proxyval (T05 alapján) |

---

## Tesztelési terv

```bash
python3 -m pytest -q tests/worker/test_cavity_prepack.py
python3 -m pytest -q tests/worker/test_cavity_prepack.py -k "v2"
./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t06_recursive_cavity_fill.md
```

---

## Elfogadási feltételek

- `build_cavity_prepacked_engine_input_v2()` létezik és exportálva van
- A v2 output tartalmaz `placement_trees` mezőt
- Matrjoska teszteset (A→B→C) lefut
- Ciklus védelem tesztelt: parent nem kerülhet saját cavityjébe
- Quantity invariáns tesztelt
- Minden top-level part `holes_points_mm == []`
- A v1 függvény és tesztek változatlanok

---

## Rollback / safety notes

- A v2 függvény új belépési pont — a v1 érintetlen
- Ha a rekurzív fill hibás eredményt ad, a worker/main.py választhatja a v1 entry pointot
- A `max_cavity_depth=3` alapértelmezés korlátozza a számítási időt

---

## Dependency

- T04 (v2 schema konstansok és `_PlacementTreeNode` dataclass) — kötelező
- T05 (lyukas child outer proxy) — kötelező (nélküle a lyukas child nem kerülhet candidate-be)
- T03 (guard) — ajánlott, hogy a v2 output is guard-olva legyen
