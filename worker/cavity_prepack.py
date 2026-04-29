from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import math
from typing import Any

from shapely import affinity
from shapely.geometry import Polygon

_PLAN_VERSION = "cavity_plan_v1"
_VIRTUAL_PART_PREFIX = "__cavity_composite__"
_EPS_AREA = 1e-7
_EPS_COORD = 1e-9


class CavityPrepackError(RuntimeError):
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
    # v1 intentionally ignores child holes: unsupported and filtered before use.
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
                    "code": "child_has_holes_unsupported_v1",
                    "child_part_revision_id": part.part_id,
                }
            )
            continue
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


__all__ = ["CavityPrepackError", "build_cavity_prepacked_engine_input"]
