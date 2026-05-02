# Cavity v2 T08 — Exact nested cavity validator

## Cél

Létrehoz egy `worker/cavity_validation.py` modult, amely exact Shapely alapú validációt végez a `cavity_plan_v2` `placement_trees` struktúráján. Minden szinten ellenőrzi: a child teljesen benn van a cavity polygonban, nincs child-child overlap, nincs boundary metszés, a transform helyes, nincs quantity mismatch.

---

## Miért szükséges

A T06 greedy fit check nem garantál teljes exactságot — gyors heurisztikára épül. A final placement előtt kötelező egy független, Shapely-alapú validátor futtatása, amely minden placement tree node-ra elvégzi az exact geometriai ellenőrzést. Ha a validáció megbukik, a run nem folytatódhat.

---

## Érintett valós fájlok

### Létrehozandó:
- `worker/cavity_validation.py` — új modul

### Módosítandó:
- `worker/cavity_prepack.py` — hívja a validátort `build_cavity_prepacked_engine_input_v2()` végén (opcionálisan, vagy a worker/main.py)

### Tesztek:
- `tests/worker/test_cavity_validation.py` — új tesztfájl

---

## Nem célok / scope határok

- **Nem** helyettesíti a result normalizer-t.
- **Nem** módosítja a v1 path-t.
- **Nem** végez teljesítmény-optimalizálást.
- A validátor **nem javít** — csak jelez és dob.

---

## Részletes implementációs lépések

### 1. Hibakód osztályok

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

class CavityValidationError(RuntimeError):
    """Hard fail: a cavity placement tree validáció megbukott."""
    pass

@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    context: dict[str, Any] = field(default_factory=dict)
```

### 2. Egyedi validáló függvények

```python
from shapely.geometry import Polygon
from shapely import affinity

_EPS_AREA = 1e-7

def _build_placed_polygon(
    *,
    outer_points_mm: list[list[float]],
    x_abs: float,
    y_abs: float,
    rotation_deg: float,
) -> Polygon:
    """Felépíti az exact Shapely polygont az abszolút pozícióból."""
    base = Polygon(outer_points_mm)
    rotated = affinity.rotate(base, rotation_deg, origin=(0.0, 0.0), use_radians=False)
    min_x, min_y, _, _ = rotated.bounds
    normalized = affinity.translate(rotated, xoff=-min_x, yoff=-min_y)
    return affinity.translate(normalized, xoff=x_abs, yoff=y_abs)

def validate_child_within_cavity(
    *,
    cavity_polygon: Polygon,
    child_polygon: Polygon,
    context: dict[str, Any],
) -> ValidationIssue | None:
    """CAVITY_CHILD_OUTSIDE_PARENT_CAVITY ha child nem fér bele teljesen."""
    if not cavity_polygon.covers(child_polygon):
        diff_area = float(child_polygon.difference(cavity_polygon).area)
        return ValidationIssue(
            code="CAVITY_CHILD_OUTSIDE_PARENT_CAVITY",
            message=f"Child polygon exceeds cavity boundary by {diff_area:.6f} mm2",
            context={**context, "diff_area_mm2": diff_area},
        )
    return None

def validate_no_child_child_overlap(
    *,
    placed_polygons: list[tuple[str, Polygon]],
    context: dict[str, Any],
) -> list[ValidationIssue]:
    """CAVITY_CHILD_CHILD_OVERLAP ha bármelyik két child polygon metszi egymást."""
    issues: list[ValidationIssue] = []
    for i in range(len(placed_polygons)):
        id_a, poly_a = placed_polygons[i]
        for j in range(i + 1, len(placed_polygons)):
            id_b, poly_b = placed_polygons[j]
            if not poly_a.intersects(poly_b):
                continue
            overlap_area = float(poly_a.intersection(poly_b).area)
            if overlap_area > _EPS_AREA:
                issues.append(ValidationIssue(
                    code="CAVITY_CHILD_CHILD_OVERLAP",
                    message=f"Overlap between {id_a} and {id_b}: {overlap_area:.6f} mm2",
                    context={**context, "part_a": id_a, "part_b": id_b, "overlap_area_mm2": overlap_area},
                ))
    return issues
```

### 3. `validate_placement_tree_node()` rekurzív

```python
from worker.result_normalizer import placement_transform_point, _normalize_rotation_deg

def _abs_transform_from_local(
    *,
    parent_abs_x: float,
    parent_abs_y: float,
    parent_abs_rotation: float,
    local_x: float,
    local_y: float,
    local_rotation: float,
) -> tuple[float, float, float]:
    abs_x, abs_y = placement_transform_point(
        local_x=local_x, local_y=local_y,
        tx=parent_abs_x, ty=parent_abs_y,
        rotation_deg=parent_abs_rotation,
        base_x=0.0, base_y=0.0,
    )
    abs_rotation = _normalize_rotation_deg(parent_abs_rotation + local_rotation)
    return abs_x, abs_y, abs_rotation

def validate_placement_tree_node(
    *,
    node: dict[str, Any],
    parent_cavity_polygon: Polygon | None,
    parent_abs_x: float,
    parent_abs_y: float,
    parent_abs_rotation: float,
    part_records_by_id: dict[str, Any],
    depth: int,
    max_depth: int,
    issues: list[ValidationIssue],
) -> None:
    """Rekurzívan validálja a placement tree node-ot és gyermekeit."""
    if depth > max_depth:
        issues.append(ValidationIssue(
            code="CAVITY_TREE_DEPTH_EXCEEDED",
            message=f"Tree depth {depth} exceeds max {max_depth}",
            context={"node_id": str(node.get("node_id")), "depth": depth},
        ))
        return

    part_id = str(node.get("part_revision_id") or "")
    instance = int(node.get("instance", 0))
    kind = str(node.get("kind") or "")
    local_x = float(node.get("x_local_mm", 0.0))
    local_y = float(node.get("y_local_mm", 0.0))
    local_rotation = float(node.get("rotation_deg", 0.0))

    if kind == "top_level_virtual_parent":
        abs_x, abs_y, abs_rotation = parent_abs_x, parent_abs_y, parent_abs_rotation
    else:
        abs_x, abs_y, abs_rotation = _abs_transform_from_local(
            parent_abs_x=parent_abs_x, parent_abs_y=parent_abs_y,
            parent_abs_rotation=parent_abs_rotation,
            local_x=local_x, local_y=local_y, local_rotation=local_rotation,
        )

    part_rec = part_records_by_id.get(part_id)
    if part_rec is None:
        issues.append(ValidationIssue(
            code="CAVITY_TRANSFORM_INVALID",
            message=f"Unknown part in placement tree: {part_id}",
            context={"part_id": part_id, "instance": instance},
        ))
        return

    child_poly = _build_placed_polygon(
        outer_points_mm=part_rec["outer_points_mm"],
        x_abs=abs_x, y_abs=abs_y, rotation_deg=abs_rotation,
    )

    if parent_cavity_polygon is not None:
        issue = validate_child_within_cavity(
            cavity_polygon=parent_cavity_polygon,
            child_polygon=child_poly,
            context={"part_id": part_id, "instance": instance, "depth": depth},
        )
        if issue:
            issues.append(issue)

    children = node.get("children") or []
    placed_children: list[tuple[str, Polygon]] = []
    for child_node in children:
        if not isinstance(child_node, dict):
            continue
        child_part_id = str(child_node.get("part_revision_id") or "")
        child_instance = int(child_node.get("instance", 0))
        child_local_x = float(child_node.get("x_local_mm", 0.0))
        child_local_y = float(child_node.get("y_local_mm", 0.0))
        child_local_rotation = float(child_node.get("rotation_deg", 0.0))
        child_abs_x, child_abs_y, child_abs_rotation = _abs_transform_from_local(
            parent_abs_x=abs_x, parent_abs_y=abs_y, parent_abs_rotation=abs_rotation,
            local_x=child_local_x, local_y=child_local_y, local_rotation=child_local_rotation,
        )
        child_rec = part_records_by_id.get(child_part_id)
        if child_rec:
            c_poly = _build_placed_polygon(
                outer_points_mm=child_rec["outer_points_mm"],
                x_abs=child_abs_x, y_abs=child_abs_y, rotation_deg=child_abs_rotation,
            )
            placed_children.append((f"{child_part_id}:{child_instance}", c_poly))

    if len(placed_children) > 1:
        overlap_issues = validate_no_child_child_overlap(
            placed_polygons=placed_children,
            context={"parent_part_id": part_id, "parent_instance": instance, "depth": depth},
        )
        issues.extend(overlap_issues)

    # Recursive: ha a part maga lyukas, a children a lyukakon belül vannak-e
    if part_rec.get("holes_points_mm"):
        for cavity_idx, hole_ring in enumerate(part_rec["holes_points_mm"]):
            try:
                from shapely.geometry import Polygon as ShapelyPolygon
                cavity_poly = ShapelyPolygon(hole_ring)
                # Transzformáljuk a cavity polygont is (a parent elhelyezési pozíciójában)
                rotated_cavity = affinity.rotate(
                    cavity_poly, abs_rotation, origin=(0.0, 0.0), use_radians=False
                )
                min_x, min_y, _, _ = rotated_cavity.bounds
                cavity_abs = affinity.translate(rotated_cavity, xoff=abs_x - min_x, yoff=abs_y - min_y)
            except Exception:
                continue
            # Ellenőrzés: cavity_idx-hez tartozó children
            cavity_children_nodes = [
                c for c in children
                if isinstance(c, dict) and int(c.get("parent_cavity_index", -1)) == cavity_idx
            ]
            for child_node in cavity_children_nodes:
                validate_placement_tree_node(
                    node=child_node,
                    parent_cavity_polygon=cavity_abs,
                    parent_abs_x=abs_x, parent_abs_y=abs_y, parent_abs_rotation=abs_rotation,
                    part_records_by_id=part_records_by_id,
                    depth=depth + 1, max_depth=max_depth,
                    issues=issues,
                )
    else:
        for child_node in children:
            if isinstance(child_node, dict):
                validate_placement_tree_node(
                    node=child_node,
                    parent_cavity_polygon=None,
                    parent_abs_x=abs_x, parent_abs_y=abs_y, parent_abs_rotation=abs_rotation,
                    part_records_by_id=part_records_by_id,
                    depth=depth + 1, max_depth=max_depth,
                    issues=issues,
                )
```

### 4. `validate_cavity_plan_v2()` top-level

```python
def validate_cavity_plan_v2(
    *,
    cavity_plan: dict[str, Any],
    part_records: list[Any],
    solver_placements: list[dict[str, Any]],
    max_depth: int = 3,
    strict: bool = True,
) -> list[ValidationIssue]:
    """Futtatja a teljes cavity plan v2 validációt.
    Ha strict=True és van issue, CavityValidationError-t dob.
    """
    part_records_by_id = {str(p.part_id): {"outer_points_mm": p.outer_points_mm, "holes_points_mm": p.holes_points_mm} for p in part_records}
    placement_trees = cavity_plan.get("placement_trees") or {}
    virtual_parts = cavity_plan.get("virtual_parts") or {}

    issues: list[ValidationIssue] = []

    # Solver placement-ek iterálása
    for solver_placement in solver_placements:
        part_id = str(solver_placement.get("part_id") or "")
        if part_id not in virtual_parts:
            continue
        x_abs = float(solver_placement.get("x_mm", 0.0))
        y_abs = float(solver_placement.get("y_mm", 0.0))
        rotation_abs = float(solver_placement.get("rotation_deg", 0.0))

        tree_node = placement_trees.get(part_id)
        if tree_node is None:
            issues.append(ValidationIssue(
                code="CAVITY_TRANSFORM_INVALID",
                message=f"Missing placement_tree for virtual part: {part_id}",
                context={"part_id": part_id},
            ))
            continue

        for child_node in (tree_node.get("children") or []):
            if isinstance(child_node, dict):
                validate_placement_tree_node(
                    node=child_node,
                    parent_cavity_polygon=None,
                    parent_abs_x=x_abs, parent_abs_y=y_abs, parent_abs_rotation=rotation_abs,
                    part_records_by_id=part_records_by_id,
                    depth=1, max_depth=max_depth,
                    issues=issues,
                )

    # Quantity mismatch check
    quantity_delta = cavity_plan.get("quantity_delta") or {}
    for part_id_raw, delta in quantity_delta.items():
        expected = int(delta.get("original_required_qty", 0))
        internal = int(delta.get("internal_qty", 0))
        top_level = int(delta.get("top_level_qty", 0))
        if internal + top_level != expected:
            issues.append(ValidationIssue(
                code="CAVITY_QUANTITY_MISMATCH",
                message=f"{part_id_raw}: internal({internal}) + top_level({top_level}) != expected({expected})",
                context={"part_id": str(part_id_raw), "expected": expected, "internal": internal, "top_level": top_level},
            ))

    if strict and issues:
        codes = ", ".join(sorted({i.code for i in issues}))
        raise CavityValidationError(
            f"cavity_plan_v2 validation failed with {len(issues)} issue(s): {codes}"
        )
    return issues

__all__ = [
    "CavityValidationError",
    "ValidationIssue",
    "validate_cavity_plan_v2",
    "validate_child_within_cavity",
    "validate_no_child_child_overlap",
]
```

---

## Hibakódok / diagnosztikák

| Kód | Leírás |
|-----|--------|
| `CAVITY_CHILD_OUTSIDE_PARENT_CAVITY` | Child polygon nem fér bele a cavity-be |
| `CAVITY_CHILD_CHILD_OVERLAP` | Két child ütközik ugyanazon cavityn belül |
| `CAVITY_TREE_DEPTH_EXCEEDED` | Rekurzív mélység túllépve |
| `CAVITY_QUANTITY_MISMATCH` | Quantity invariáns sérül |
| `CAVITY_TRANSFORM_INVALID` | Transform nem számítható / part nem ismert |

---

## Tesztelési terv

```bash
python3 -m pytest -q tests/worker/test_cavity_validation.py
./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t08_exact_nested_validator.md
```

Tesztesetek:
- `test_valid_single_level_passes`
- `test_child_outside_cavity_fails` → `CAVITY_CHILD_OUTSIDE_PARENT_CAVITY`
- `test_child_child_overlap_fails` → `CAVITY_CHILD_CHILD_OVERLAP`
- `test_quantity_mismatch_fails` → `CAVITY_QUANTITY_MISMATCH`
- `test_matrjoska_valid_three_level`
- `test_strict_false_returns_issues_not_raises`

---

## Elfogadási feltételek

- `worker/cavity_validation.py` létezik és a fenti `__all__` exportokat tartalmazza
- Minden hibakód tesztelt
- Strict mód `CavityValidationError`-t dob
- Nem-strict mód listát ad vissza
- A modul nem ír fájlt, nem hív DB-t

---

## Rollback / safety notes

- Teljesen új modul — rollback: fájl törlése
- A `worker/cavity_prepack.py` hívása opcionális, a modul önállóan is tesztelhető

---

## Dependency

- T06 (rekurzív fill, placement_trees gyártja) — kötelező
- T07 (normalizer flatten) — ajánlott (koordináta számítás refbase)
