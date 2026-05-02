from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from shapely import affinity
from shapely.geometry import Polygon

from worker.result_normalizer import placement_transform_point

_EPS_AREA = 1e-7


class CavityValidationError(RuntimeError):
    """Hard fail raised when cavity v2 validation detects issues."""


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class _PartGeom:
    part_id: str
    outer_points_mm: list[list[float]]
    holes_points_mm: list[list[list[float]]]


def _normalize_rotation_deg(value: float) -> float:
    normalized = float(value) % 360.0
    if normalized < 0.0:
        normalized += 360.0
    return normalized


def _as_list_of_points(raw: Any) -> list[list[float]]:
    if not isinstance(raw, list) or len(raw) < 3:
        raise ValueError("invalid ring")
    out: list[list[float]] = []
    for point in raw:
        if not isinstance(point, list) or len(point) != 2:
            raise ValueError("invalid point")
        out.append([float(point[0]), float(point[1])])
    return out


def _part_id_from_raw(part: Any) -> str:
    if isinstance(part, dict):
        part_id = str(part.get("part_id") or part.get("id") or "").strip()
    else:
        part_id = str(getattr(part, "part_id", "")).strip()
    if not part_id:
        raise ValueError("missing part_id")
    return part_id


def _part_outer_from_raw(part: Any) -> list[list[float]]:
    raw = part.get("outer_points_mm") if isinstance(part, dict) else getattr(part, "outer_points_mm", None)
    return _as_list_of_points(raw)


def _part_holes_from_raw(part: Any) -> list[list[list[float]]]:
    raw = part.get("holes_points_mm", []) if isinstance(part, dict) else getattr(part, "holes_points_mm", [])
    if not isinstance(raw, list):
        raise ValueError("invalid holes")
    return [_as_list_of_points(ring) for ring in raw]


def _build_part_index(part_records: list[Any]) -> dict[str, _PartGeom]:
    out: dict[str, _PartGeom] = {}
    for raw in part_records:
        part_id = _part_id_from_raw(raw)
        if part_id in out:
            raise ValueError(f"duplicate part_id: {part_id}")
        out[part_id] = _PartGeom(
            part_id=part_id,
            outer_points_mm=_part_outer_from_raw(raw),
            holes_points_mm=_part_holes_from_raw(raw),
        )
    return out


def _to_polygon(outer_points_mm: list[list[float]], holes_points_mm: list[list[list[float]]] | None = None) -> Polygon:
    polygon = Polygon(outer_points_mm, holes_points_mm or [])
    if polygon.is_empty:
        raise ValueError("empty polygon")
    if not polygon.is_valid:
        polygon = polygon.buffer(0)
    if polygon.is_empty or not polygon.is_valid:
        raise ValueError("invalid polygon")
    if float(polygon.area) <= _EPS_AREA:
        raise ValueError("non-positive polygon area")
    return polygon


def _build_placed_polygon(
    *,
    outer_points_mm: list[list[float]],
    x_abs: float,
    y_abs: float,
    rotation_deg: float,
) -> Polygon:
    base = _to_polygon(outer_points_mm)
    rotated = affinity.rotate(base, float(rotation_deg), origin=(0.0, 0.0), use_radians=False)
    min_x, min_y, _, _ = rotated.bounds
    normalized = affinity.translate(rotated, xoff=-min_x, yoff=-min_y)
    placed = affinity.translate(normalized, xoff=float(x_abs), yoff=float(y_abs))
    return _to_polygon([[float(x), float(y)] for x, y in list(placed.exterior.coords)[:-1]])


def _build_transformed_cavity_polygon(
    *,
    parent_outer_points_mm: list[list[float]],
    parent_cavity_ring_mm: list[list[float]],
    parent_abs_x: float,
    parent_abs_y: float,
    parent_abs_rotation_deg: float,
) -> Polygon:
    parent_outer = _to_polygon(parent_outer_points_mm)
    rotated_outer = affinity.rotate(parent_outer, float(parent_abs_rotation_deg), origin=(0.0, 0.0), use_radians=False)
    outer_min_x, outer_min_y, _, _ = rotated_outer.bounds

    cavity_poly = _to_polygon(parent_cavity_ring_mm)
    rotated_cavity = affinity.rotate(cavity_poly, float(parent_abs_rotation_deg), origin=(0.0, 0.0), use_radians=False)
    normalized = affinity.translate(rotated_cavity, xoff=-outer_min_x, yoff=-outer_min_y)
    placed = affinity.translate(normalized, xoff=float(parent_abs_x), yoff=float(parent_abs_y))
    return _to_polygon([[float(x), float(y)] for x, y in list(placed.exterior.coords)[:-1]])


def _compose_cavity_transform(
    *,
    parent_abs_x: float,
    parent_abs_y: float,
    parent_abs_rotation_deg: float,
    child_local_x: float,
    child_local_y: float,
    child_local_rotation_deg: float,
) -> tuple[float, float, float]:
    abs_x, abs_y = placement_transform_point(
        local_x=float(child_local_x),
        local_y=float(child_local_y),
        tx=float(parent_abs_x),
        ty=float(parent_abs_y),
        rotation_deg=float(parent_abs_rotation_deg),
        base_x=0.0,
        base_y=0.0,
    )
    abs_rotation = _normalize_rotation_deg(float(parent_abs_rotation_deg) + float(child_local_rotation_deg))
    return (float(abs_x), float(abs_y), float(abs_rotation))


def validate_child_within_cavity(
    *,
    cavity_polygon: Polygon,
    child_polygon: Polygon,
    context: dict[str, Any],
) -> ValidationIssue | None:
    if cavity_polygon.covers(child_polygon):
        return None
    diff_area = float(child_polygon.difference(cavity_polygon).area)
    return ValidationIssue(
        code="CAVITY_CHILD_OUTSIDE_PARENT_CAVITY",
        message=f"Child polygon exceeds cavity boundary by {diff_area:.6f} mm2",
        context={**context, "outside_area_mm2": round(diff_area, 6)},
    )


def validate_no_child_child_overlap(
    *,
    placed_polygons: list[tuple[str, Polygon]],
    context: dict[str, Any],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for idx_a in range(len(placed_polygons)):
        id_a, poly_a = placed_polygons[idx_a]
        for idx_b in range(idx_a + 1, len(placed_polygons)):
            id_b, poly_b = placed_polygons[idx_b]
            if not poly_a.intersects(poly_b):
                continue
            overlap_area = float(poly_a.intersection(poly_b).area)
            if overlap_area <= _EPS_AREA:
                continue
            issues.append(
                ValidationIssue(
                    code="CAVITY_CHILD_CHILD_OVERLAP",
                    message=f"Overlap between {id_a} and {id_b}: {overlap_area:.6f} mm2",
                    context={
                        **context,
                        "part_a": id_a,
                        "part_b": id_b,
                        "overlap_area_mm2": round(overlap_area, 6),
                    },
                )
            )
    return issues


def _parse_node_value(node: dict[str, Any], key: str, *, default: Any = None) -> Any:
    if key in node:
        return node.get(key)
    return default


def validate_placement_tree_node(
    *,
    node: dict[str, Any],
    parent_part: _PartGeom,
    parent_abs_x: float,
    parent_abs_y: float,
    parent_abs_rotation_deg: float,
    part_index: dict[str, _PartGeom],
    depth: int,
    max_depth: int,
    issues: list[ValidationIssue],
    internal_count_by_part: dict[str, int],
) -> None:
    if depth > max_depth:
        issues.append(
            ValidationIssue(
                code="CAVITY_TREE_DEPTH_EXCEEDED",
                message=f"Tree depth {depth} exceeds max {max_depth}",
                context={
                    "node_id": str(node.get("node_id") or ""),
                    "depth": int(depth),
                    "max_depth": int(max_depth),
                },
            )
        )
        return

    try:
        node_part_id = str(_parse_node_value(node, "part_revision_id") or "").strip()
        if not node_part_id:
            raise ValueError("missing part_revision_id")
        node_instance = int(_parse_node_value(node, "instance", default=0))
        local_x = float(_parse_node_value(node, "x_local_mm", default=0.0))
        local_y = float(_parse_node_value(node, "y_local_mm", default=0.0))
        local_rotation = float(_parse_node_value(node, "rotation_deg", default=0.0))
        parent_cavity_index_raw = _parse_node_value(node, "parent_cavity_index", default=None)
        parent_cavity_index = int(parent_cavity_index_raw) if parent_cavity_index_raw is not None else None
    except Exception as exc:  # noqa: BLE001
        issues.append(
            ValidationIssue(
                code="CAVITY_TRANSFORM_INVALID",
                message=f"Invalid placement tree node payload: {exc}",
                context={"node": node},
            )
        )
        return

    node_part = part_index.get(node_part_id)
    if node_part is None:
        issues.append(
            ValidationIssue(
                code="CAVITY_TRANSFORM_INVALID",
                message=f"Unknown part in placement tree: {node_part_id}",
                context={"part_id": node_part_id},
            )
        )
        return

    abs_x, abs_y, abs_rotation = _compose_cavity_transform(
        parent_abs_x=parent_abs_x,
        parent_abs_y=parent_abs_y,
        parent_abs_rotation_deg=parent_abs_rotation_deg,
        child_local_x=local_x,
        child_local_y=local_y,
        child_local_rotation_deg=local_rotation,
    )
    try:
        node_polygon = _build_placed_polygon(
            outer_points_mm=node_part.outer_points_mm,
            x_abs=abs_x,
            y_abs=abs_y,
            rotation_deg=abs_rotation,
        )
    except Exception as exc:  # noqa: BLE001
        issues.append(
            ValidationIssue(
                code="CAVITY_TRANSFORM_INVALID",
                message=f"Cannot build placed polygon for {node_part_id}:{node_instance}: {exc}",
                context={"part_id": node_part_id, "instance": int(node_instance)},
            )
        )
        return

    if parent_cavity_index is None:
        issues.append(
            ValidationIssue(
                code="CAVITY_TRANSFORM_INVALID",
                message="Missing parent_cavity_index for internal cavity child",
                context={"part_id": node_part_id, "instance": int(node_instance)},
            )
        )
        return

    if parent_cavity_index < 0 or parent_cavity_index >= len(parent_part.holes_points_mm):
        issues.append(
            ValidationIssue(
                code="CAVITY_TRANSFORM_INVALID",
                message=f"Invalid parent_cavity_index={parent_cavity_index}",
                context={
                    "part_id": node_part_id,
                    "instance": int(node_instance),
                    "parent_part_id": parent_part.part_id,
                },
            )
        )
        return

    try:
        parent_cavity_polygon = _build_transformed_cavity_polygon(
            parent_outer_points_mm=parent_part.outer_points_mm,
            parent_cavity_ring_mm=parent_part.holes_points_mm[parent_cavity_index],
            parent_abs_x=parent_abs_x,
            parent_abs_y=parent_abs_y,
            parent_abs_rotation_deg=parent_abs_rotation_deg,
        )
    except Exception as exc:  # noqa: BLE001
        issues.append(
            ValidationIssue(
                code="CAVITY_TRANSFORM_INVALID",
                message=f"Cannot build parent cavity polygon: {exc}",
                context={"parent_part_id": parent_part.part_id, "cavity_index": int(parent_cavity_index)},
            )
        )
        return

    containment_issue = validate_child_within_cavity(
        cavity_polygon=parent_cavity_polygon,
        child_polygon=node_polygon,
        context={
            "part_id": node_part_id,
            "instance": int(node_instance),
            "parent_part_id": parent_part.part_id,
            "parent_cavity_index": int(parent_cavity_index),
            "depth": int(depth),
        },
    )
    if containment_issue is not None:
        issues.append(containment_issue)

    internal_count_by_part[node_part_id] = int(internal_count_by_part.get(node_part_id, 0)) + 1

    children_raw = node.get("children", [])
    if not isinstance(children_raw, list):
        issues.append(
            ValidationIssue(
                code="CAVITY_TRANSFORM_INVALID",
                message="children field must be list",
                context={"part_id": node_part_id, "instance": int(node_instance)},
            )
        )
        return

    cavity_child_polygons: dict[int, list[tuple[str, Polygon]]] = {}
    child_nodes_for_recursion: list[dict[str, Any]] = []
    for child_raw in children_raw:
        if not isinstance(child_raw, dict):
            continue
        try:
            child_part_id = str(child_raw.get("part_revision_id") or "").strip()
            child_instance = int(child_raw.get("instance", 0))
            child_local_x = float(child_raw.get("x_local_mm", 0.0))
            child_local_y = float(child_raw.get("y_local_mm", 0.0))
            child_local_rotation = float(child_raw.get("rotation_deg", 0.0))
            child_parent_cavity_idx = int(child_raw.get("parent_cavity_index"))
        except Exception:
            continue

        child_part = part_index.get(child_part_id)
        if child_part is None:
            continue
        child_abs_x, child_abs_y, child_abs_rotation = _compose_cavity_transform(
            parent_abs_x=abs_x,
            parent_abs_y=abs_y,
            parent_abs_rotation_deg=abs_rotation,
            child_local_x=child_local_x,
            child_local_y=child_local_y,
            child_local_rotation_deg=child_local_rotation,
        )
        try:
            child_polygon = _build_placed_polygon(
                outer_points_mm=child_part.outer_points_mm,
                x_abs=child_abs_x,
                y_abs=child_abs_y,
                rotation_deg=child_abs_rotation,
            )
        except Exception:
            continue
        cavity_child_polygons.setdefault(child_parent_cavity_idx, []).append(
            (f"{child_part_id}:{child_instance}", child_polygon)
        )
        child_nodes_for_recursion.append(child_raw)

    for cavity_index, placed_polygons in cavity_child_polygons.items():
        issues.extend(
            validate_no_child_child_overlap(
                placed_polygons=placed_polygons,
                context={
                    "parent_part_id": node_part_id,
                    "parent_instance": int(node_instance),
                    "parent_cavity_index": int(cavity_index),
                    "depth": int(depth + 1),
                },
            )
        )

    for child_node in child_nodes_for_recursion:
        validate_placement_tree_node(
            node=child_node,
            parent_part=node_part,
            parent_abs_x=abs_x,
            parent_abs_y=abs_y,
            parent_abs_rotation_deg=abs_rotation,
            part_index=part_index,
            depth=depth + 1,
            max_depth=max_depth,
            issues=issues,
            internal_count_by_part=internal_count_by_part,
        )


def validate_cavity_plan_v2(
    *,
    cavity_plan: dict[str, Any],
    part_records: list[Any],
    solver_placements: list[dict[str, Any]],
    max_depth: int = 3,
    strict: bool = True,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if str(cavity_plan.get("version") or "") != "cavity_plan_v2":
        issues.append(
            ValidationIssue(
                code="CAVITY_TRANSFORM_INVALID",
                message="cavity plan version is not cavity_plan_v2",
                context={"version": cavity_plan.get("version")},
            )
        )
        if strict:
            raise CavityValidationError("cavity_plan_v2 validation failed: invalid plan version")
        return issues

    try:
        part_index = _build_part_index(part_records)
    except Exception as exc:  # noqa: BLE001
        issues.append(
            ValidationIssue(
                code="CAVITY_TRANSFORM_INVALID",
                message=f"invalid part_records payload: {exc}",
                context={},
            )
        )
        if strict:
            raise CavityValidationError(f"cavity_plan_v2 validation failed: invalid part_records: {exc}")
        return issues

    virtual_parts_raw = cavity_plan.get("virtual_parts")
    placement_trees_raw = cavity_plan.get("placement_trees")
    quantity_delta_raw = cavity_plan.get("quantity_delta")
    if not isinstance(virtual_parts_raw, dict) or not isinstance(placement_trees_raw, dict) or not isinstance(quantity_delta_raw, dict):
        issues.append(
            ValidationIssue(
                code="CAVITY_TRANSFORM_INVALID",
                message="cavity plan missing required dict blocks",
                context={},
            )
        )
        if strict:
            raise CavityValidationError("cavity_plan_v2 validation failed: missing required dict blocks")
        return issues

    internal_count_by_part: dict[str, int] = {}

    for solver_item in solver_placements:
        if not isinstance(solver_item, dict):
            continue
        virtual_part_id = str(solver_item.get("part_id") or "").strip()
        if virtual_part_id not in virtual_parts_raw:
            continue

        virtual_item = virtual_parts_raw.get(virtual_part_id)
        if not isinstance(virtual_item, dict):
            issues.append(
                ValidationIssue(
                    code="CAVITY_TRANSFORM_INVALID",
                    message=f"invalid virtual_parts entry: {virtual_part_id}",
                    context={},
                )
            )
            continue

        parent_part_id = str(virtual_item.get("parent_part_revision_id") or "").strip()
        parent_part = part_index.get(parent_part_id)
        if parent_part is None:
            issues.append(
                ValidationIssue(
                    code="CAVITY_TRANSFORM_INVALID",
                    message=f"unknown parent part for virtual id: {virtual_part_id}",
                    context={"parent_part_id": parent_part_id},
                )
            )
            continue

        tree_root = placement_trees_raw.get(virtual_part_id)
        if not isinstance(tree_root, dict):
            issues.append(
                ValidationIssue(
                    code="CAVITY_TRANSFORM_INVALID",
                    message=f"missing placement tree for virtual id: {virtual_part_id}",
                    context={"virtual_part_id": virtual_part_id},
                )
            )
            continue

        try:
            parent_abs_x = float(solver_item.get("x_mm", 0.0))
            parent_abs_y = float(solver_item.get("y_mm", 0.0))
            parent_abs_rotation = float(solver_item.get("rotation_deg", 0.0))
        except Exception as exc:  # noqa: BLE001
            issues.append(
                ValidationIssue(
                    code="CAVITY_TRANSFORM_INVALID",
                    message=f"invalid solver transform for virtual id {virtual_part_id}: {exc}",
                    context={"virtual_part_id": virtual_part_id},
                )
            )
            continue

        root_part_id = str(tree_root.get("part_revision_id") or "").strip()
        if root_part_id and root_part_id != parent_part_id:
            issues.append(
                ValidationIssue(
                    code="CAVITY_TRANSFORM_INVALID",
                    message="placement tree root part differs from virtual parent",
                    context={
                        "virtual_part_id": virtual_part_id,
                        "root_part_id": root_part_id,
                        "parent_part_id": parent_part_id,
                    },
                )
            )

        children_raw = tree_root.get("children", [])
        if not isinstance(children_raw, list):
            issues.append(
                ValidationIssue(
                    code="CAVITY_TRANSFORM_INVALID",
                    message=f"placement tree children must be list for {virtual_part_id}",
                    context={"virtual_part_id": virtual_part_id},
                )
            )
            continue

        root_child_groups: dict[int, list[tuple[str, Polygon]]] = {}
        for child_raw in children_raw:
            if not isinstance(child_raw, dict):
                continue
            try:
                child_part_id = str(child_raw.get("part_revision_id") or "").strip()
                child_instance = int(child_raw.get("instance", 0))
                child_local_x = float(child_raw.get("x_local_mm", 0.0))
                child_local_y = float(child_raw.get("y_local_mm", 0.0))
                child_local_rotation = float(child_raw.get("rotation_deg", 0.0))
                child_parent_cavity_idx = int(child_raw.get("parent_cavity_index"))
            except Exception:
                continue
            child_part = part_index.get(child_part_id)
            if child_part is None:
                continue
            child_abs_x, child_abs_y, child_abs_rotation = _compose_cavity_transform(
                parent_abs_x=parent_abs_x,
                parent_abs_y=parent_abs_y,
                parent_abs_rotation_deg=parent_abs_rotation,
                child_local_x=child_local_x,
                child_local_y=child_local_y,
                child_local_rotation_deg=child_local_rotation,
            )
            try:
                child_polygon = _build_placed_polygon(
                    outer_points_mm=child_part.outer_points_mm,
                    x_abs=child_abs_x,
                    y_abs=child_abs_y,
                    rotation_deg=child_abs_rotation,
                )
            except Exception:
                continue
            root_child_groups.setdefault(child_parent_cavity_idx, []).append(
                (f"{child_part_id}:{child_instance}", child_polygon)
            )
        for cavity_index, placed_polygons in root_child_groups.items():
            issues.extend(
                validate_no_child_child_overlap(
                    placed_polygons=placed_polygons,
                    context={
                        "parent_part_id": parent_part_id,
                        "parent_instance": int(virtual_item.get("parent_instance", 0)),
                        "parent_cavity_index": int(cavity_index),
                        "depth": 1,
                    },
                )
            )

        for child_node in children_raw:
            if not isinstance(child_node, dict):
                continue
            validate_placement_tree_node(
                node=child_node,
                parent_part=parent_part,
                parent_abs_x=parent_abs_x,
                parent_abs_y=parent_abs_y,
                parent_abs_rotation_deg=parent_abs_rotation,
                part_index=part_index,
                depth=1,
                max_depth=int(max_depth),
                issues=issues,
                internal_count_by_part=internal_count_by_part,
            )

    for part_id_raw, delta_raw in quantity_delta_raw.items():
        if not isinstance(delta_raw, dict):
            issues.append(
                ValidationIssue(
                    code="CAVITY_QUANTITY_MISMATCH",
                    message=f"invalid quantity_delta entry for {part_id_raw}",
                    context={"part_id": str(part_id_raw)},
                )
            )
            continue

        part_id = str(part_id_raw)
        try:
            original_qty = int(delta_raw.get("original_required_qty", 0))
            internal_qty = int(delta_raw.get("internal_qty", 0))
            top_level_qty = int(delta_raw.get("top_level_qty", 0))
        except Exception as exc:  # noqa: BLE001
            issues.append(
                ValidationIssue(
                    code="CAVITY_QUANTITY_MISMATCH",
                    message=f"invalid quantity numbers for {part_id}: {exc}",
                    context={"part_id": part_id},
                )
            )
            continue

        if internal_qty + top_level_qty != original_qty:
            issues.append(
                ValidationIssue(
                    code="CAVITY_QUANTITY_MISMATCH",
                    message=(
                        f"{part_id}: internal({internal_qty}) + top_level({top_level_qty}) "
                        f"!= original({original_qty})"
                    ),
                    context={
                        "part_id": part_id,
                        "original_required_qty": int(original_qty),
                        "internal_qty": int(internal_qty),
                        "top_level_qty": int(top_level_qty),
                    },
                )
            )

        actual_internal = int(internal_count_by_part.get(part_id, 0))
        if actual_internal != internal_qty:
            issues.append(
                ValidationIssue(
                    code="CAVITY_QUANTITY_MISMATCH",
                    message=f"{part_id}: expected_internal={internal_qty} actual_internal={actual_internal}",
                    context={
                        "part_id": part_id,
                        "expected_internal_qty": int(internal_qty),
                        "actual_internal_qty": int(actual_internal),
                    },
                )
            )

    if strict and issues:
        codes = ", ".join(sorted({issue.code for issue in issues}))
        raise CavityValidationError(
            f"cavity_plan_v2 validation failed with {len(issues)} issue(s): {codes}"
        )
    return issues


__all__ = [
    "CavityValidationError",
    "ValidationIssue",
    "validate_child_within_cavity",
    "validate_no_child_child_overlap",
    "validate_cavity_plan_v2",
]
