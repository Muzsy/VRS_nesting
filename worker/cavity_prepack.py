from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import math
from typing import Any

from shapely import affinity
from shapely.geometry import Polygon

_PLAN_VERSION = "cavity_plan_v1"
_PLAN_VERSION_V2 = "cavity_plan_v2"
_VIRTUAL_PART_PREFIX = "__cavity_composite__"
_EPS_AREA = 1e-7
_EPS_COORD = 1e-9


class CavityPrepackError(RuntimeError):
    pass


class CavityPrepackGuardError(CavityPrepackError):
    pass


@dataclass(frozen=True)
class _PartRecord:
    part_id: str
    part_code: str
    quantity: int
    allowed_rotations_deg: list[int]
    outer_points_mm: list[list[float]]
    holes_points_mm: list[list[list[float]]]
    area_mm2: float
    bbox_max_dim_mm: float
    source_geometry_revision_id: str
    selected_nesting_derivative_id: str


@dataclass(frozen=True)
class _CavityPlacement:
    child_part_revision_id: str
    child_instance: int
    cavity_index: int
    x_local_mm: float
    y_local_mm: float
    rotation_deg: int
    placement_origin_ref: str


@dataclass(frozen=True)
class _PlacementTreeNode:
    node_id: str
    part_revision_id: str
    instance: int
    kind: str
    parent_node_id: str | None
    parent_cavity_index: int | None
    x_local_mm: float
    y_local_mm: float
    rotation_deg: int
    placement_origin_ref: str
    children: tuple["_PlacementTreeNode", ...]


@dataclass(frozen=True)
class _CavityRecord:
    parent_part_id: str
    parent_instance: int
    cavity_index: int
    cavity_polygon: Polygon
    cavity_bounds: tuple[float, float, float, float]
    usable_area_mm2: float


def _require_dict(raw: Any, *, field: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise CavityPrepackError(f"invalid {field}")
    return raw


def _require_list(raw: Any, *, field: str) -> list[Any]:
    if not isinstance(raw, list):
        raise CavityPrepackError(f"invalid {field}")
    return raw


def _require_str(raw: Any, *, field: str) -> str:
    value = str(raw or "").strip()
    if not value:
        raise CavityPrepackError(f"invalid {field}")
    return value


def _parse_positive_int(raw: Any, *, field: str) -> int:
    if isinstance(raw, bool):
        raise CavityPrepackError(f"invalid {field}")
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise CavityPrepackError(f"invalid {field}") from exc
    if value <= 0:
        raise CavityPrepackError(f"invalid {field}")
    return value


def _parse_ring(raw: Any, *, field: str) -> list[list[float]]:
    points = _require_list(raw, field=field)
    if len(points) < 3:
        raise CavityPrepackError(f"invalid {field}")
    out: list[list[float]] = []
    for idx, point_raw in enumerate(points):
        if not isinstance(point_raw, list) or len(point_raw) != 2:
            raise CavityPrepackError(f"invalid {field}[{idx}]")
        try:
            x = float(point_raw[0])
            y = float(point_raw[1])
        except (TypeError, ValueError) as exc:
            raise CavityPrepackError(f"invalid {field}[{idx}]") from exc
        if not math.isfinite(x) or not math.isfinite(y):
            raise CavityPrepackError(f"invalid {field}[{idx}]")
        out.append([x, y])
    return out


def _canonical_policy(enabled: bool) -> dict[str, Any]:
    return {
        "mode": "auto_prepack" if enabled else "disabled",
        "top_level_hole_policy": "solidify_parent_outer",
        "usable_cavity_source": "inflated_or_deflated_hole_from_pipeline",
        "quantity_allocation": "internal_first_deterministic",
    }


def _empty_plan(*, enabled: bool) -> dict[str, Any]:
    return {
        "version": _PLAN_VERSION,
        "enabled": bool(enabled),
        "policy": _canonical_policy(enabled),
        "virtual_parts": {},
        "instance_bases": {},
        "quantity_delta": {},
        "diagnostics": [],
    }


def _empty_plan_v2(*, enabled: bool, max_cavity_depth: int = 3) -> dict[str, Any]:
    return {
        "version": _PLAN_VERSION_V2,
        "enabled": bool(enabled),
        "policy": {
            "mode": "recursive_cavity_prepack" if enabled else "disabled",
            "top_level_hole_policy": "solidify_parent_outer",
            "child_hole_policy": "recursive_outer_proxy_with_exact_export",
            "quantity_allocation": "internal_first_scored",
            "max_cavity_depth": int(max_cavity_depth),
        },
        "virtual_parts": {},
        "placement_trees": {},
        "instance_bases": {},
        "quantity_delta": {},
        "diagnostics": [],
        "summary": {},
    }


def _to_polygon(outer_points_mm: list[list[float]], holes_points_mm: list[list[list[float]]]) -> Polygon:
    polygon = Polygon(outer_points_mm, holes_points_mm)
    if polygon.is_empty:
        raise CavityPrepackError("invalid polygon: empty")
    if not polygon.is_valid:
        polygon = polygon.buffer(0)
    if polygon.is_empty or not polygon.is_valid:
        raise CavityPrepackError("invalid polygon")
    if float(polygon.area) <= _EPS_AREA:
        raise CavityPrepackError("invalid polygon area")
    return polygon


def _build_snapshot_part_index(snapshot_row: dict[str, Any]) -> dict[str, dict[str, str]]:
    parts_manifest_raw = _require_list(snapshot_row.get("parts_manifest_jsonb"), field="parts_manifest_jsonb")
    out: dict[str, dict[str, str]] = {}
    for idx, raw_part in enumerate(parts_manifest_raw):
        if not isinstance(raw_part, dict):
            continue
        part_revision_id = _require_str(raw_part.get("part_revision_id"), field=f"parts_manifest_jsonb[{idx}].part_revision_id")
        out[part_revision_id] = {
            "part_code": _require_str(raw_part.get("part_code"), field=f"parts_manifest_jsonb[{idx}].part_code"),
            "source_geometry_revision_id": _require_str(
                raw_part.get("source_geometry_revision_id"),
                field=f"parts_manifest_jsonb[{idx}].source_geometry_revision_id",
            ),
            "selected_nesting_derivative_id": _require_str(
                raw_part.get("selected_nesting_derivative_id"),
                field=f"parts_manifest_jsonb[{idx}].selected_nesting_derivative_id",
            ),
        }
    return out


def _build_part_records(snapshot_row: dict[str, Any], base_engine_input: dict[str, Any]) -> list[_PartRecord]:
    base_parts_raw = _require_list(base_engine_input.get("parts"), field="base_engine_input.parts")
    snapshot_index = _build_snapshot_part_index(snapshot_row)
    out: list[_PartRecord] = []
    for idx, raw_part in enumerate(base_parts_raw):
        part = _require_dict(raw_part, field=f"base_engine_input.parts[{idx}]")
        part_id = _require_str(part.get("id"), field=f"base_engine_input.parts[{idx}].id")
        quantity = _parse_positive_int(part.get("quantity"), field=f"base_engine_input.parts[{idx}].quantity")
        rotations_raw = _require_list(
            part.get("allowed_rotations_deg"),
            field=f"base_engine_input.parts[{idx}].allowed_rotations_deg",
        )
        rotations: list[int] = []
        for rot_idx, rotation_raw in enumerate(rotations_raw):
            if isinstance(rotation_raw, bool):
                raise CavityPrepackError(
                    f"invalid base_engine_input.parts[{idx}].allowed_rotations_deg[{rot_idx}]"
                )
            try:
                rotation = int(rotation_raw) % 360
            except (TypeError, ValueError) as exc:
                raise CavityPrepackError(
                    f"invalid base_engine_input.parts[{idx}].allowed_rotations_deg[{rot_idx}]"
                ) from exc
            rotations.append(rotation)
        if not rotations:
            raise CavityPrepackError(f"invalid base_engine_input.parts[{idx}].allowed_rotations_deg")

        outer_points_mm = _parse_ring(
            part.get("outer_points_mm"),
            field=f"base_engine_input.parts[{idx}].outer_points_mm",
        )
        holes_points_raw = _require_list(
            part.get("holes_points_mm", []),
            field=f"base_engine_input.parts[{idx}].holes_points_mm",
        )
        holes_points_mm = [
            _parse_ring(ring, field=f"base_engine_input.parts[{idx}].holes_points_mm[{ring_idx}]")
            for ring_idx, ring in enumerate(holes_points_raw)
        ]

        polygon = _to_polygon(outer_points_mm, holes_points_mm)
        min_x, min_y, max_x, max_y = polygon.bounds
        max_dim = max(float(max_x - min_x), float(max_y - min_y))

        snapshot_meta = snapshot_index.get(part_id)
        if snapshot_meta is None:
            raise CavityPrepackError(f"snapshot part metadata missing: {part_id}")

        out.append(
            _PartRecord(
                part_id=part_id,
                part_code=snapshot_meta["part_code"],
                quantity=quantity,
                allowed_rotations_deg=sorted(set(rotations)),
                outer_points_mm=outer_points_mm,
                holes_points_mm=holes_points_mm,
                area_mm2=float(polygon.area),
                bbox_max_dim_mm=max_dim,
                source_geometry_revision_id=snapshot_meta["source_geometry_revision_id"],
                selected_nesting_derivative_id=snapshot_meta["selected_nesting_derivative_id"],
            )
        )
    return out


def _ring_bbox(ring: list[list[float]]) -> tuple[float, float, float, float]:
    xs = [float(point[0]) for point in ring]
    ys = [float(point[1]) for point in ring]
    return (min(xs), min(ys), max(xs), max(ys))


def _rotation_shapes(part: _PartRecord) -> list[tuple[int, Polygon, float, float]]:
    # outer-only proxy: holes excluded from fit geometry; exact holes preserved in part record for export.
    base_poly = _to_polygon(part.outer_points_mm, [])
    out: list[tuple[int, Polygon, float, float]] = []
    for rotation_deg in part.allowed_rotations_deg:
        rotated = affinity.rotate(base_poly, rotation_deg, origin=(0.0, 0.0), use_radians=False)
        min_x, min_y, max_x, max_y = rotated.bounds
        normalized = affinity.translate(rotated, xoff=-min_x, yoff=-min_y)
        out.append((int(rotation_deg), normalized, float(max_x - min_x), float(max_y - min_y)))
    return out


def _candidate_children(
    *,
    part_records: list[_PartRecord],
    parent_part_id: str,
    remaining_qty: dict[str, int],
    diagnostics: list[dict[str, Any]],
) -> list[_PartRecord]:
    out: list[_PartRecord] = []
    for part in part_records:
        if part.part_id == parent_part_id:
            continue
        if int(remaining_qty.get(part.part_id, 0)) <= 0:
            continue
        if part.holes_points_mm:
            diagnostics.append(
                {
                    "code": "child_has_holes_outer_proxy_used",
                    "child_part_revision_id": part.part_id,
                    "hole_count": len(part.holes_points_mm),
                }
            )
        out.append(part)
    out.sort(
        key=lambda item: (
            -float(item.area_mm2),
            float(item.bbox_max_dim_mm),
            item.part_code,
            item.part_id,
        )
    )
    return out


def _build_usable_cavity_records(
    *,
    parent: _PartRecord,
    parent_instance: int,
    min_usable_cavity_area_mm2: float,
    diagnostics: list[dict[str, Any]],
) -> list[_CavityRecord]:
    records: list[_CavityRecord] = []
    for cavity_index, cavity_ring in enumerate(parent.holes_points_mm):
        try:
            cavity_poly = _to_polygon(cavity_ring, [])
        except CavityPrepackError:
            diagnostics.append(
                {
                    "code": "invalid_cavity_polygon",
                    "parent_part_id": parent.part_id,
                    "cavity_index": cavity_index,
                }
            )
            continue
        area = float(cavity_poly.area)
        if area < float(min_usable_cavity_area_mm2):
            diagnostics.append(
                {
                    "code": "cavity_too_small",
                    "parent_part_id": parent.part_id,
                    "cavity_index": cavity_index,
                    "usable_area_mm2": round(area, 6),
                }
            )
            continue
        records.append(
            _CavityRecord(
                parent_part_id=parent.part_id,
                parent_instance=int(parent_instance),
                cavity_index=int(cavity_index),
                cavity_polygon=cavity_poly,
                cavity_bounds=_ring_bbox(cavity_ring),
                usable_area_mm2=round(area, 6),
            )
        )
    return records


def _rank_cavity_child_candidates(
    *,
    cavity: _CavityRecord,
    part_records: list[_PartRecord],
    remaining_qty: dict[str, int],
    excluded_part_ids: set[str],
    diagnostics: list[dict[str, Any]],
) -> list[_PartRecord]:
    cav_min_x, cav_min_y, cav_max_x, cav_max_y = cavity.cavity_bounds
    cav_w = float(cav_max_x - cav_min_x)
    cav_h = float(cav_max_y - cav_min_y)
    cav_area = float(cavity.usable_area_mm2)
    max_cavity_dim = max(cav_w, cav_h)

    out: list[_PartRecord] = []
    for part in part_records:
        if part.part_id in excluded_part_ids:
            continue
        if int(remaining_qty.get(part.part_id, 0)) <= 0:
            continue
        if float(part.bbox_max_dim_mm) > max_cavity_dim + _EPS_COORD:
            continue
        if part.holes_points_mm:
            diagnostics.append(
                {
                    "code": "child_has_holes_outer_proxy_used",
                    "child_part_revision_id": part.part_id,
                    "hole_count": len(part.holes_points_mm),
                }
            )
        out.append(part)

    out.sort(
        key=lambda part: (
            -float(part.area_mm2),
            -(float(part.area_mm2) / cav_area if cav_area > _EPS_AREA else 0.0),
            float(part.bbox_max_dim_mm),
            part.part_code,
            part.part_id,
        )
    )
    return out


def _transform_child_ring_for_placement(
    *,
    child: _PartRecord,
    ring: list[list[float]],
    rotation_deg: int,
    x_local_mm: float,
    y_local_mm: float,
) -> list[list[float]]:
    rotated_outer = affinity.rotate(
        _to_polygon(child.outer_points_mm, []),
        int(rotation_deg),
        origin=(0.0, 0.0),
        use_radians=False,
    )
    min_x, min_y, _, _ = rotated_outer.bounds

    ring_poly = affinity.rotate(
        _to_polygon(ring, []),
        int(rotation_deg),
        origin=(0.0, 0.0),
        use_radians=False,
    )
    normalized = affinity.translate(ring_poly, xoff=-min_x, yoff=-min_y)
    placed = affinity.translate(normalized, xoff=float(x_local_mm), yoff=float(y_local_mm))

    coords = list(placed.exterior.coords)
    if len(coords) >= 2 and coords[0] == coords[-1]:
        coords = coords[:-1]
    return [[float(x), float(y)] for x, y in coords]


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
    if depth > max_depth:
        diagnostics.append(
            {
                "code": "max_cavity_depth_reached",
                "depth": int(depth),
                "max_cavity_depth": int(max_depth),
                "parent_part_id": cavity.parent_part_id,
            }
        )
        return []

    excluded_part_ids = set(ancestor_part_ids) | {cavity.parent_part_id}
    candidates = _rank_cavity_child_candidates(
        cavity=cavity,
        part_records=part_records,
        remaining_qty=remaining_qty,
        excluded_part_ids=excluded_part_ids,
        diagnostics=diagnostics,
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
            instance_key = f"{child.part_id}:{child_instance}"
            if instance_key in reserved_instance_ids:
                diagnostics.append(
                    {
                        "code": "instance_id_reused",
                        "instance_key": instance_key,
                    }
                )
                child_instance += 1
                instance_key = f"{child.part_id}:{child_instance}"

            next_instance[child.part_id] = child_instance + 1
            reserved_instance_ids.add(instance_key)
            remaining_qty[child.part_id] = int(remaining_qty[child.part_id]) - 1
            occupied.append(placed_poly)

            node: dict[str, Any] = {
                "node_id": f"node:{child.part_id}:{child_instance}",
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

            if child.holes_points_mm and depth < max_depth:
                child_cavity_records = _build_usable_cavity_records(
                    parent=part_by_id[child.part_id],
                    parent_instance=child_instance,
                    min_usable_cavity_area_mm2=min_usable_cavity_area_mm2,
                    diagnostics=diagnostics,
                )
                for child_cavity in child_cavity_records:
                    transformed_ring = _transform_child_ring_for_placement(
                        child=child,
                        ring=child.holes_points_mm[child_cavity.cavity_index],
                        rotation_deg=int(rotation_deg),
                        x_local_mm=float(x_local),
                        y_local_mm=float(y_local),
                    )
                    transformed_poly = _to_polygon(transformed_ring, [])
                    nested_cavity = _CavityRecord(
                        parent_part_id=child.part_id,
                        parent_instance=child_instance,
                        cavity_index=child_cavity.cavity_index,
                        cavity_polygon=transformed_poly,
                        cavity_bounds=_ring_bbox(transformed_ring),
                        usable_area_mm2=float(child_cavity.usable_area_mm2),
                    )
                    nested_nodes = _fill_cavity_recursive(
                        cavity=nested_cavity,
                        part_records=part_records,
                        part_by_id=part_by_id,
                        remaining_qty=remaining_qty,
                        reserved_instance_ids=reserved_instance_ids,
                        ancestor_part_ids=frozenset(set(ancestor_part_ids) | {cavity.parent_part_id}),
                        next_instance=next_instance,
                        depth=depth + 1,
                        max_depth=max_depth,
                        min_usable_cavity_area_mm2=min_usable_cavity_area_mm2,
                        diagnostics=diagnostics,
                    )
                    node["children"].extend(nested_nodes)
            placement_nodes.append(node)
    return placement_nodes


def _dedupe_anchors(anchors: list[tuple[float, float]]) -> list[tuple[float, float]]:
    seen: set[tuple[int, int]] = set()
    out: list[tuple[float, float]] = []
    for x, y in anchors:
        key = (int(round(x * 1000.0)), int(round(y * 1000.0)))
        if key in seen:
            continue
        seen.add(key)
        out.append((x, y))
    out.sort(key=lambda item: (item[1], item[0]))
    return out


def _bbox_prefilter(
    *,
    cavity_bounds: tuple[float, float, float, float],
    anchor_x: float,
    anchor_y: float,
    width: float,
    height: float,
) -> bool:
    min_x, min_y, max_x, max_y = cavity_bounds
    if anchor_x < min_x - _EPS_COORD or anchor_y < min_y - _EPS_COORD:
        return False
    if anchor_x + width > max_x + _EPS_COORD:
        return False
    if anchor_y + height > max_y + _EPS_COORD:
        return False
    return True


def _fits_exactly(
    *,
    cavity_polygon: Polygon,
    candidate_polygon: Polygon,
    occupied: list[Polygon],
) -> bool:
    if not cavity_polygon.covers(candidate_polygon):
        return False
    for placed in occupied:
        if not candidate_polygon.intersects(placed):
            continue
        if float(candidate_polygon.intersection(placed).area) > _EPS_AREA:
            return False
    return True


def _try_place_child_in_cavity(
    *,
    cavity_polygon: Polygon,
    cavity_bounds: tuple[float, float, float, float],
    child_shapes: list[tuple[int, Polygon, float, float]],
    occupied: list[Polygon],
) -> tuple[float, float, int, Polygon] | None:
    anchors: list[tuple[float, float]] = [(cavity_bounds[0], cavity_bounds[1])]
    for placed in sorted(occupied, key=lambda poly: (poly.bounds[1], poly.bounds[0], poly.bounds[3], poly.bounds[2])):
        min_x, min_y, max_x, max_y = placed.bounds
        anchors.append((max_x, min_y))
        anchors.append((min_x, max_y))
        anchors.append((max_x, max_y))

    for rotation_deg, normalized_poly, width, height in child_shapes:
        for anchor_x, anchor_y in _dedupe_anchors(anchors):
            if not _bbox_prefilter(
                cavity_bounds=cavity_bounds,
                anchor_x=anchor_x,
                anchor_y=anchor_y,
                width=width,
                height=height,
            ):
                continue
            candidate = affinity.translate(normalized_poly, xoff=anchor_x, yoff=anchor_y)
            if _fits_exactly(cavity_polygon=cavity_polygon, candidate_polygon=candidate, occupied=occupied):
                return (anchor_x, anchor_y, rotation_deg, candidate)
    return None


def validate_prepack_solver_input_hole_free(engine_input: dict[str, Any]) -> None:
    parts_raw = engine_input.get("parts")
    if not isinstance(parts_raw, list):
        raise CavityPrepackGuardError("CAVITY_PREPACK_TOP_LEVEL_HOLES_REMAIN: invalid parts field")

    violations: list[str] = []
    for idx, part_raw in enumerate(parts_raw):
        if not isinstance(part_raw, dict):
            continue
        holes_points = part_raw.get("holes_points_mm")
        if isinstance(holes_points, list) and len(holes_points) > 0:
            part_id = str(part_raw.get("id") or f"idx:{idx}").strip() or f"idx:{idx}"
            violations.append(part_id)

    if violations:
        ordered_ids = ", ".join(sorted(set(violations)))
        raise CavityPrepackGuardError(
            f"CAVITY_PREPACK_TOP_LEVEL_HOLES_REMAIN: {len(violations)} part(s) still have holes after prepack: {ordered_ids}"
        )


def build_cavity_prepacked_engine_input(
    *,
    snapshot_row: dict[str, Any],
    base_engine_input: dict[str, Any],
    enabled: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    base = _require_dict(base_engine_input, field="base_engine_input")
    _require_str(base.get("version"), field="base_engine_input.version")
    _require_dict(snapshot_row, field="snapshot_row")

    out_input = deepcopy(base_engine_input)
    if not enabled:
        return out_input, _empty_plan(enabled=False)

    part_records = _build_part_records(snapshot_row, base)
    part_by_id = {part.part_id: part for part in part_records}
    remaining_qty: dict[str, int] = {part.part_id: int(part.quantity) for part in part_records}
    reserved_internal: dict[str, int] = {part.part_id: 0 for part in part_records}
    next_child_instance: dict[str, int] = {part.part_id: 0 for part in part_records}
    diagnostics: list[dict[str, Any]] = []
    virtual_parts: dict[str, dict[str, Any]] = {}
    out_parts: list[dict[str, Any]] = []

    holed_parents = [part for part in part_records if part.holes_points_mm and part.quantity > 0]
    non_holed = [part for part in part_records if not part.holes_points_mm and part.quantity > 0]

    for parent in holed_parents:
        for parent_instance in range(parent.quantity):
            virtual_id = f"{_VIRTUAL_PART_PREFIX}{parent.part_id}__{parent_instance:06d}"
            internal_placements: list[dict[str, Any]] = []
            cavity_diagnostics: list[dict[str, Any]] = []

            for cavity_index, cavity_ring in enumerate(parent.holes_points_mm):
                try:
                    cavity_poly = _to_polygon(cavity_ring, [])
                except CavityPrepackError:
                    cavity_diagnostics.append(
                        {
                            "cavity_index": cavity_index,
                            "status": "invalid_cavity_polygon",
                            "usable_area_mm2": 0.0,
                            "placements_count": 0,
                        }
                    )
                    continue

                cavity_bounds = _ring_bbox(cavity_ring)
                candidates = _candidate_children(
                    part_records=part_records,
                    parent_part_id=parent.part_id,
                    remaining_qty=remaining_qty,
                    diagnostics=diagnostics,
                )
                occupied: list[Polygon] = []
                cavity_placements = 0
                for child in candidates:
                    child_shapes = _rotation_shapes(child)
                    while int(remaining_qty.get(child.part_id, 0)) > 0:
                        placement = _try_place_child_in_cavity(
                            cavity_polygon=cavity_poly,
                            cavity_bounds=cavity_bounds,
                            child_shapes=child_shapes,
                            occupied=occupied,
                        )
                        if placement is None:
                            break
                        x_local, y_local, rotation_deg, placed_poly = placement
                        child_instance = int(next_child_instance[child.part_id])
                        next_child_instance[child.part_id] = child_instance + 1
                        remaining_qty[child.part_id] = int(remaining_qty[child.part_id]) - 1
                        reserved_internal[child.part_id] = int(reserved_internal[child.part_id]) + 1
                        occupied.append(placed_poly)
                        cavity_placements += 1
                        internal_placements.append(
                            {
                                "child_part_revision_id": child.part_id,
                                "child_instance": child_instance,
                                "cavity_index": cavity_index,
                                "x_local_mm": round(float(x_local), 6),
                                "y_local_mm": round(float(y_local), 6),
                                "rotation_deg": int(rotation_deg),
                                "placement_origin_ref": "bbox_min_corner",
                            }
                        )

                cavity_status = "used" if cavity_placements > 0 else "not_used_no_child_fit"
                cavity_diagnostics.append(
                    {
                        "cavity_index": cavity_index,
                        "status": cavity_status,
                        "usable_area_mm2": round(float(cavity_poly.area), 6),
                        "placements_count": int(cavity_placements),
                    }
                )

            virtual_parts[virtual_id] = {
                "kind": "parent_composite",
                "parent_part_revision_id": parent.part_id,
                "parent_instance": parent_instance,
                "source_geometry_revision_id": parent.source_geometry_revision_id,
                "selected_nesting_derivative_id": parent.selected_nesting_derivative_id,
                "internal_placements": internal_placements,
                "cavity_diagnostics": cavity_diagnostics,
            }
            out_parts.append(
                {
                    "id": virtual_id,
                    "quantity": 1,
                    "allowed_rotations_deg": list(parent.allowed_rotations_deg),
                    "outer_points_mm": deepcopy(parent.outer_points_mm),
                    "holes_points_mm": [],
                }
            )

        remaining_qty[parent.part_id] = 0

    for part in non_holed:
        qty = int(remaining_qty.get(part.part_id, 0))
        if qty <= 0:
            continue
        out_parts.append(
            {
                "id": part.part_id,
                "quantity": qty,
                "allowed_rotations_deg": list(part.allowed_rotations_deg),
                "outer_points_mm": deepcopy(part.outer_points_mm),
                "holes_points_mm": deepcopy(part.holes_points_mm),
            }
        )

    referenced_child_ids: set[str] = set()
    for virtual in virtual_parts.values():
        internal_placements = virtual.get("internal_placements")
        if not isinstance(internal_placements, list):
            continue
        for placement_raw in internal_placements:
            if not isinstance(placement_raw, dict):
                continue
            child_id = str(placement_raw.get("child_part_revision_id") or "").strip()
            if child_id:
                referenced_child_ids.add(child_id)

    instance_bases: dict[str, dict[str, int]] = {}
    quantity_delta: dict[str, dict[str, int]] = {}
    for child_id in sorted(referenced_child_ids):
        part = part_by_id.get(child_id)
        if part is None:
            continue
        internal_qty = int(reserved_internal.get(child_id, 0))
        top_level_qty = int(remaining_qty.get(child_id, 0))
        quantity_delta[child_id] = {
            "original_required_qty": int(part.quantity),
            "internal_qty": internal_qty,
            "top_level_qty": top_level_qty,
        }
        instance_bases[child_id] = {
            "internal_reserved_count": internal_qty,
            "top_level_instance_base": internal_qty,
        }

    out_parts.sort(key=lambda item: str(item.get("id") or ""))
    out_input["parts"] = out_parts

    plan = _empty_plan(enabled=True)
    plan["virtual_parts"] = virtual_parts
    plan["instance_bases"] = instance_bases
    plan["quantity_delta"] = quantity_delta
    plan["diagnostics"] = diagnostics
    return out_input, plan


def _module_variant_key(
    *,
    parent_part_id: str,
    parent_outer_points_mm: list[list[float]],
    child_placements: list[dict[str, Any]],
) -> str:
    """Stable variant id based on parent shape and child placement set."""
    import hashlib, json
    outer_hash = hashlib.sha256(
        json.dumps(parent_outer_points_mm, separators=(",", ":")).encode()
    ).hexdigest()[:16]
    if not child_placements:
        return f"{parent_part_id}__empty__{outer_hash}"
    child_sig = []
    for cp in sorted(child_placements, key=lambda c: (str(c.get("child_part_revision_id","")), c.get("child_instance",0))):
        child_sig.append(f"{cp.get('child_part_revision_id')}:{cp.get('child_instance')}:{cp.get('x_local_mm')}:{cp.get('y_local_mm')}:{cp.get('rotation_deg')}")
    child_hash = hashlib.sha256("|".join(child_sig).encode()).hexdigest()[:16]
    return f"{parent_part_id}__{child_hash}__{outer_hash}"


def _group_placement_trees_by_variant(
    *,
    placement_trees: dict[str, dict[str, Any]],
    virtual_parts: dict[str, dict[str, Any]],
    part_by_id: dict[str, _PartRecord],
) -> dict[str, dict[str, Any]]:
    """Collapse placement trees into module variants, summing quantities."""
    variant_map: dict[str, dict[str, Any]] = {}
    for virtual_id, tree in placement_trees.items():
        vp = virtual_parts.get(virtual_id, {})
        parent_id = vp.get("parent_part_revision_id", "")
        parent = part_by_id.get(parent_id)
        if parent is None:
            continue
        internal_placements = _collect_placement_leaf_nodes(tree)
        variant_key = _module_variant_key(
            parent_part_id=parent_id,
            parent_outer_points_mm=parent.outer_points_mm,
            child_placements=internal_placements,
        )
        if variant_key not in variant_map:
            solver_part_id = f"{_VIRTUAL_PART_PREFIX}{variant_key}"
            variant_map[variant_key] = {
                "variant_key": variant_key,
                "solver_part_id": solver_part_id,
                "parent_part_id": parent_id,
                "parent_outer_points_mm": deepcopy(parent.outer_points_mm),
                "allowed_rotations_deg": list(parent.allowed_rotations_deg),
                "source_geometry_revision_id": parent.source_geometry_revision_id,
                "selected_nesting_derivative_id": parent.selected_nesting_derivative_id,
                "quantity": 0,
                "representative_virtual_id": virtual_id,
                "member_virtual_ids": [],
                "placement_trees": [],
            }
        variant_map[variant_key]["quantity"] += 1
        variant_map[variant_key]["member_virtual_ids"].append(virtual_id)
        variant_map[variant_key]["placement_trees"].append(tree)
    return variant_map


def _collect_placement_leaf_nodes(tree: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect all internal_cavity_child nodes from a placement tree."""
    result: list[dict[str, Any]] = []
    children = tree.get("children", [])
    if not isinstance(children, list):
        return result
    for child in children:
        if not isinstance(child, dict):
            continue
        kind = str(child.get("kind") or "")
        if kind == "internal_cavity_child":
            result.append({
                "child_part_revision_id": child.get("part_revision_id", ""),
                "child_instance": child.get("instance", 0),
                "x_local_mm": child.get("x_local_mm", 0.0),
                "y_local_mm": child.get("y_local_mm", 0.0),
                "rotation_deg": child.get("rotation_deg", 0),
                "parent_cavity_index": child.get("parent_cavity_index"),
            })
        result.extend(_collect_placement_leaf_nodes(child))
    return result


def build_cavity_prepacked_engine_input_v2(
    *,
    snapshot_row: dict[str, Any],
    base_engine_input: dict[str, Any],
    enabled: bool,
    max_cavity_depth: int = 3,
    min_usable_cavity_area_mm2: float = 100.0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    base = _require_dict(base_engine_input, field="base_engine_input")
    _require_str(base.get("version"), field="base_engine_input.version")
    _require_dict(snapshot_row, field="snapshot_row")

    out_input = deepcopy(base_engine_input)
    if not enabled:
        return out_input, _empty_plan_v2(enabled=False, max_cavity_depth=max_cavity_depth)

    part_records = _build_part_records(snapshot_row, base)
    part_by_id = {part.part_id: part for part in part_records}
    remaining_qty: dict[str, int] = {part.part_id: int(part.quantity) for part in part_records}
    next_instance: dict[str, int] = {part.part_id: 0 for part in part_records}
    reserved_instance_ids: set[str] = set()
    diagnostics: list[dict[str, Any]] = []
    virtual_parts: dict[str, dict[str, Any]] = {}
    placement_trees: dict[str, dict[str, Any]] = {}
    variant_map: dict[str, dict[str, Any]] = {}
    top_level_qty_by_part: dict[str, int] = {part.part_id: 0 for part in part_records}
    out_parts: list[dict[str, Any]] = []
    usable_cavity_count = 0
    used_cavity_count = 0

    holed_parents = [part for part in part_records if part.holes_points_mm and part.quantity > 0]
    holed_parents.sort(
        key=lambda part: (
            -float(part.area_mm2),
            -float(part.bbox_max_dim_mm),
            str(part.part_code),
            str(part.part_id),
        )
    )
    for parent in holed_parents:
        top_level_qty = int(remaining_qty.get(parent.part_id, 0))
        if top_level_qty <= 0:
            continue
        top_level_qty_by_part[parent.part_id] = top_level_qty
        for parent_instance_local in range(top_level_qty):
            parent_instance = int(next_instance.get(parent.part_id, 0)) + parent_instance_local
            virtual_id = f"{_VIRTUAL_PART_PREFIX}{parent.part_id}__{parent_instance_local:06d}"
            cavity_records = _build_usable_cavity_records(
                parent=parent,
                parent_instance=parent_instance,
                min_usable_cavity_area_mm2=min_usable_cavity_area_mm2,
                diagnostics=diagnostics,
            )
            usable_cavity_count += len(cavity_records)

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
                if child_nodes:
                    used_cavity_count += 1
                root_node["children"].extend(child_nodes)

            virtual_parts[virtual_id] = {
                "kind": "parent_composite",
                "parent_part_revision_id": parent.part_id,
                "parent_instance": parent_instance,
                "source_geometry_revision_id": parent.source_geometry_revision_id,
                "selected_nesting_derivative_id": parent.selected_nesting_derivative_id,
            }
            placement_trees[virtual_id] = root_node
        next_instance[parent.part_id] = int(next_instance.get(parent.part_id, 0)) + top_level_qty
        remaining_qty[parent.part_id] = 0

    # Group identical module variants (same parent + same child placement set) → collapse per-instance to per-variant
    if virtual_parts or placement_trees:
        variant_map = _group_placement_trees_by_variant(
            placement_trees=placement_trees,
            virtual_parts=virtual_parts,
            part_by_id=part_by_id,
        )
        for variant in variant_map.values():
            out_parts.append(
                {
                    "id": f"{_VIRTUAL_PART_PREFIX}{variant['variant_key']}",
                    "quantity": variant["quantity"],
                    "allowed_rotations_deg": variant["allowed_rotations_deg"],
                    "outer_points_mm": deepcopy(variant["parent_outer_points_mm"]),
                    "holes_points_mm": [],
                }
            )

    for part in part_records:
        if part.holes_points_mm:
            continue
        qty = int(remaining_qty.get(part.part_id, 0))
        if qty <= 0:
            continue
        top_level_qty_by_part[part.part_id] = qty
        out_parts.append(
            {
                "id": part.part_id,
                "quantity": qty,
                "allowed_rotations_deg": list(part.allowed_rotations_deg),
                "outer_points_mm": deepcopy(part.outer_points_mm),
                "holes_points_mm": [],
            }
        )

    quantity_delta: dict[str, dict[str, int]] = {}
    instance_bases: dict[str, dict[str, int]] = {}
    for part in part_records:
        original_qty = int(part.quantity)
        top_level_qty = int(top_level_qty_by_part.get(part.part_id, 0))
        internal_qty = int(original_qty - top_level_qty)
        quantity_delta[part.part_id] = {
            "original_required_qty": original_qty,
            "internal_qty": internal_qty,
            "top_level_qty": top_level_qty,
        }
        instance_bases[part.part_id] = {
            "internal_reserved_count": internal_qty,
            "top_level_instance_base": internal_qty,
        }

    def _count_tree_nodes(node: dict[str, Any]) -> int:
        children_raw = node.get("children")
        if not isinstance(children_raw, list):
            return 1
        return 1 + sum(
            _count_tree_nodes(child)
            for child in children_raw
            if isinstance(child, dict)
        )

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
        "module_variant_count": len(variant_map),
        "placement_node_count": sum(_count_tree_nodes(tree) for tree in placement_trees.values()),
        "internal_placement_count": sum(
            int(metrics.get("internal_qty", 0))
            for metrics in quantity_delta.values()
            if isinstance(metrics, dict)
        ),
        "usable_cavity_count": int(usable_cavity_count),
        "used_cavity_count": int(used_cavity_count),
    }
    # Include collapsed module variants for result normalizer / validator reference
    if variant_map:
        plan["module_variants"] = {
            vk: {
                "variant_key": v["variant_key"],
                "solver_part_id": v["solver_part_id"],
                "quantity": v["quantity"],
                "parent_part_revision_id": v["parent_part_id"],
                "source_geometry_revision_id": v["source_geometry_revision_id"],
                "selected_nesting_derivative_id": v["selected_nesting_derivative_id"],
                "representative_virtual_id": v["representative_virtual_id"],
                "member_virtual_ids": list(v["member_virtual_ids"]),
            }
            for vk, v in variant_map.items()
        }
        # Reverse mapping: solver_part_id → variant_key (for O(1) lookup in normalizer)
        plan["module_variants_by_solver_id"] = {
            v["solver_part_id"]: vk for vk, v in variant_map.items()
        }
    return out_input, plan


__all__ = [
    "CavityPrepackError",
    "CavityPrepackGuardError",
    "build_cavity_prepacked_engine_input",
    "build_cavity_prepacked_engine_input_v2",
    "validate_prepack_solver_input_hole_free",
]
