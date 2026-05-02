#!/usr/bin/env python3
"""DXF import helper with strict CUT_OUTER / CUT_INNER layer conventions.

The module supports two input backends:
- `.json` fixture format used by deterministic repo smoke checks.
- `.dxf` files via optional `ezdxf` dependency when available.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vrs_nesting.geometry.clean import GeometryCleanError, clean_ring, rdp_tol_mm_from_env
from vrs_nesting.geometry.polygonize import (
    ARC_POLYGONIZE_MIN_SEGMENTS,
    CURVE_FLATTEN_TOLERANCE_MM,
    arc_to_points,
)


OUTER_LAYER_DEFAULT = "CUT_OUTER"
INNER_LAYER_DEFAULT = "CUT_INNER"
SUPPORTED_LAYER_ENTITY_TYPES = {"LWPOLYLINE", "POLYLINE", "LINE", "ARC", "CIRCLE", "SPLINE", "ELLIPSE"}
CHAIN_ENDPOINT_EPSILON_MM = 0.2
# Keep this separate from curve flatten tolerance: same numeric value, different policy purpose.
ELLIPSE_CLOSED_PARAM_EPSILON = 1e-6
MAX_INSERT_EXPANSION_DEPTH = 8
RING_INTERSECTION_EPS = 1e-9
POINT_CLOSE_EPSILON_MM = 1e-6
CURVE_FLATTEN_TOL_MIN_SOURCE_UNITS = 1e-6
CURVE_FLATTEN_TOL_MAX_SOURCE_UNITS = 1e3
MAX_CURVE_POINTS = 10000
MAX_SELF_INTERSECTION_SEGMENTS = 2000
INSUNITS_MM_SCALE = {
    0: 1.0,
    1: 25.4,
    2: 304.8,
    3: 1609344.0,
    4: 1.0,
    5: 10.0,
    6: 1000.0,
    7: 1000000.0,
    8: 0.0000254,
    9: 0.0254,
    10: 914.4,
    11: 0.0000001,
    12: 0.000001,
    13: 0.001,
    14: 100.0,
    15: 10000.0,
    16: 100000.0,
    17: 1000000000000.0,
    18: 149597870700000.0,
    19: 9460730472580800000.0,
    20: 30856775814913700000.0,
}


class DxfImportError(RuntimeError):
    """Deterministic DXF import error with stable code + message."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class PartRaw:
    """Normalized geometry payload for solver-preparation steps."""

    outer_points_mm: list[list[float]]
    holes_points_mm: list[list[list[float]]]
    source_path: str
    source_entities: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "outer_points_mm": self.outer_points_mm,
            "holes_points_mm": self.holes_points_mm,
            "source_path": self.source_path,
            "source_entities": self.source_entities,
        }


def _is_finite_number(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    return math.isfinite(float(value))


def _as_finite_float(value: Any, *, where: str) -> float:
    if not _is_finite_number(value):
        raise DxfImportError("DXF_INVALID_POINTS", f"{where} must be finite numeric value")
    return float(value)


def _as_finite_float_entity(value: Any, *, where: str) -> float:
    if not _is_finite_number(value):
        raise DxfImportError("DXF_ENTITY_INVALID", f"{where} must be finite numeric value")
    return float(value)


def _clamp_curve_flatten_tolerance(tolerance_source_units: float) -> float:
    if not math.isfinite(tolerance_source_units) or tolerance_source_units <= 0:
        return CURVE_FLATTEN_TOL_MIN_SOURCE_UNITS
    return min(
        CURVE_FLATTEN_TOL_MAX_SOURCE_UNITS,
        max(CURVE_FLATTEN_TOL_MIN_SOURCE_UNITS, float(tolerance_source_units)),
    )


def _normalize_points(raw: Any, where: str, *, min_points: int = 3) -> list[list[float]]:
    if not isinstance(raw, list):
        raise DxfImportError("DXF_INVALID_POINTS", f"{where} must be list")

    points: list[list[float]] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise DxfImportError("DXF_INVALID_POINTS", f"{where}[{idx}] must be [x, y]")
        x, y = item
        if not _is_finite_number(x) or not _is_finite_number(y):
            raise DxfImportError("DXF_INVALID_POINTS", f"{where}[{idx}] coordinates must be finite numbers")
        points.append([float(x), float(y)])

    if len(points) < min_points:
        raise DxfImportError("DXF_INVALID_RING", f"{where} must contain at least {min_points} points")

    return points


def _is_closed_entity(entity: dict[str, Any], where: str, default: bool = False) -> bool:
    closed = entity.get("closed", default)
    if not isinstance(closed, bool):
        raise DxfImportError("DXF_ENTITY_INVALID", f"{where}.closed must be boolean")
    return closed


def _extract_preflight_color_index_from_json(entity: dict[str, Any], where: str) -> int | None:
    """Return raw ACI-style color index if the JSON fixture supplies one."""

    value: Any = entity.get("color_index", None)
    if value is None:
        value = entity.get("color", None)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise DxfImportError(
            "DXF_ENTITY_INVALID",
            f"{where}.color_index must be integer when provided",
        )
    return int(value)


def _extract_preflight_linetype_from_json(entity: dict[str, Any], where: str) -> str | None:
    """Return raw linetype name if the JSON fixture supplies one."""

    value: Any = entity.get("linetype_name", None)
    if value is None:
        value = entity.get("linetype", None)
    if value is None:
        return None
    if not isinstance(value, str):
        raise DxfImportError(
            "DXF_ENTITY_INVALID",
            f"{where}.linetype_name must be string when provided",
        )
    stripped = value.strip()
    return stripped or None


def _extract_preflight_raw_signals_from_dxf(entity_any: Any) -> dict[str, Any]:
    """Read raw ACI color + linetype from an ezdxf entity without raising."""

    dxf_attr = getattr(entity_any, "dxf", None)
    color_raw = getattr(dxf_attr, "color", None) if dxf_attr is not None else None
    linetype_raw = getattr(dxf_attr, "linetype", None) if dxf_attr is not None else None

    color_index: int | None
    if color_raw is None or isinstance(color_raw, bool):
        color_index = None
    else:
        try:
            color_index = int(color_raw)
        except (TypeError, ValueError):
            color_index = None

    linetype_name: str | None
    if linetype_raw is None:
        linetype_name = None
    else:
        try:
            text = str(linetype_raw).strip()
        except Exception:
            text = ""
        linetype_name = text or None

    return {"color_index": color_index, "linetype_name": linetype_name}


def _extract_entities_from_json(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DxfImportError("DXF_JSON_PARSE", f"invalid json at line {exc.lineno} column {exc.colno}") from exc

    if not isinstance(payload, dict):
        raise DxfImportError("DXF_JSON_SCHEMA", "top-level object required")

    entities = payload.get("entities")
    if not isinstance(entities, list):
        raise DxfImportError("DXF_JSON_SCHEMA", "entities must be list")

    out: list[dict[str, Any]] = []
    for idx, entity in enumerate(entities):
        if not isinstance(entity, dict):
            raise DxfImportError("DXF_ENTITY_INVALID", f"entities[{idx}] must be object")
        where = f"entities[{idx}]"
        layer = entity.get("layer")
        etype_raw = entity.get("type", "LWPOLYLINE")
        if not isinstance(layer, str) or not layer.strip():
            raise DxfImportError("DXF_ENTITY_INVALID", f"{where}.layer must be non-empty string")
        if not isinstance(etype_raw, str) or not etype_raw.strip():
            raise DxfImportError("DXF_ENTITY_INVALID", f"{where}.type must be non-empty string")

        etype = etype_raw.strip().upper()
        out_entity: dict[str, Any] = {
            "layer": layer.strip(),
            "type": etype,
            "closed": _is_closed_entity(entity, where, default=False),
            "color_index": _extract_preflight_color_index_from_json(entity, where),
            "linetype_name": _extract_preflight_linetype_from_json(entity, where),
        }

        if etype in {"LWPOLYLINE", "POLYLINE"}:
            out_entity["points"] = _normalize_points(entity.get("points"), f"{where}.points", min_points=3)
        elif etype == "LINE":
            out_entity["points"] = _normalize_points(entity.get("points"), f"{where}.points", min_points=2)
        elif etype in {"ARC", "CIRCLE"}:
            center = entity.get("center")
            if not isinstance(center, (list, tuple)) or len(center) != 2:
                raise DxfImportError("DXF_ENTITY_INVALID", f"{where}.center must be [x, y]")
            cx, cy = center
            radius = entity.get("radius")
            cx_f = _as_finite_float_entity(cx, where=f"{where}.center[0]")
            cy_f = _as_finite_float_entity(cy, where=f"{where}.center[1]")
            radius_f = _as_finite_float_entity(radius, where=f"{where}.radius")
            start = _as_finite_float_entity(entity.get("start_angle", 0.0), where=f"{where}.start_angle")
            end = _as_finite_float_entity(entity.get("end_angle", 360.0 if etype == "CIRCLE" else 0.0), where=f"{where}.end_angle")
            if radius_f <= 0:
                raise DxfImportError("DXF_ENTITY_INVALID", f"{where}.radius must be positive number")
            out_entity.update(
                {
                    "center": [cx_f, cy_f],
                    "radius": radius_f,
                    "start_angle": start,
                    "end_angle": end,
                }
            )
        elif etype == "SPLINE":
            points = entity.get("points") or entity.get("fit_points") or entity.get("control_points")
            out_entity["points"] = _normalize_points(points, f"{where}.points", min_points=2)
        else:
            out_entity["_unsupported"] = True

        out.append(out_entity)

    return out


def _extract_entities_from_dxf(path: Path) -> list[dict[str, Any]]:
    try:
        import ezdxf
    except ImportError as exc:
        raise DxfImportError("DXF_BACKEND_MISSING", "ezdxf not installed; use JSON fixture backend or install ezdxf") from exc

    try:
        doc = ezdxf.readfile(path)
    except Exception as exc:
        raise DxfImportError("DXF_READ_FAILED", f"could not read dxf: {path}: {exc}") from exc

    unit_scale_to_mm = _resolve_insunits_scale_to_mm(doc)
    flatten_tol_in_source_units = _clamp_curve_flatten_tolerance(CURVE_FLATTEN_TOLERANCE_MM / unit_scale_to_mm)
    msp = doc.modelspace()
    out: list[dict[str, Any]] = []
    for idx, entity in enumerate(msp):
        entity_any: Any = entity
        etype = entity_any.dxftype().upper()
        where = f"modelspace[{idx}]"
        expanded_entities = _expand_insert_entities(entity_any, where=where)
        for expanded_idx, expanded in enumerate(expanded_entities):
            expanded_any = expanded["entity"]
            expanded_type = str(expanded["type"]).upper()
            expanded_layer = str(expanded["layer"])
            expanded_where = f"{where}.expanded[{expanded_idx}]"
            raw_signals = _extract_preflight_raw_signals_from_dxf(expanded_any)

            if expanded_type not in SUPPORTED_LAYER_ENTITY_TYPES:
                out.append(
                    {
                        "layer": expanded_layer,
                        "type": expanded_type,
                        "_unsupported": True,
                        **raw_signals,
                    }
                )
                continue

            if expanded_type == "LWPOLYLINE":
                lw_points = [[float(x), float(y)] for x, y, *_ in expanded_any.get_points("xy")]
                out.append(
                    {
                        "layer": expanded_layer,
                        "type": expanded_type,
                        "closed": bool(expanded_any.closed),
                        "points": _normalize_points(lw_points, f"{expanded_where}.points"),
                        **raw_signals,
                    }
                )
                continue

            if expanded_type == "POLYLINE":
                poly_points = [[float(v.dxf.location.x), float(v.dxf.location.y)] for v in expanded_any.vertices]
                out.append(
                    {
                        "layer": expanded_layer,
                        "type": expanded_type,
                        "closed": bool(expanded_any.is_closed),
                        "points": _normalize_points(poly_points, f"{expanded_where}.points"),
                        **raw_signals,
                    }
                )
                continue

            if expanded_type == "LINE":
                line_points = [
                    [float(expanded_any.dxf.start.x), float(expanded_any.dxf.start.y)],
                    [float(expanded_any.dxf.end.x), float(expanded_any.dxf.end.y)],
                ]
                out.append(
                    {
                        "layer": expanded_layer,
                        "type": expanded_type,
                        "closed": False,
                        "points": _normalize_points(line_points, f"{expanded_where}.points", min_points=2),
                        **raw_signals,
                    }
                )
                continue

            if expanded_type == "ARC":
                out.append(
                    {
                        "layer": expanded_layer,
                        "type": expanded_type,
                        "closed": False,
                        "center": [float(expanded_any.dxf.center.x), float(expanded_any.dxf.center.y)],
                        "radius": float(expanded_any.dxf.radius),
                        "start_angle": float(expanded_any.dxf.start_angle),
                        "end_angle": float(expanded_any.dxf.end_angle),
                        **raw_signals,
                    }
                )
                continue

            if expanded_type == "CIRCLE":
                out.append(
                    {
                        "layer": expanded_layer,
                        "type": expanded_type,
                        "closed": True,
                        "center": [float(expanded_any.dxf.center.x), float(expanded_any.dxf.center.y)],
                        "radius": float(expanded_any.dxf.radius),
                        "start_angle": 0.0,
                        "end_angle": 360.0,
                        **raw_signals,
                    }
                )
                continue

            if expanded_type == "ELLIPSE":
                ellipse_points = _flatten_curve_points(
                    expanded_any,
                    where=f"{expanded_where}.ellipse",
                    flatten_tol=flatten_tol_in_source_units,
                    ezdxf_module=ezdxf,
                )
                out.append(
                    {
                        "layer": expanded_layer,
                        "type": expanded_type,
                        "closed": _is_ellipse_closed(expanded_any),
                        "points": _normalize_points(ellipse_points, f"{expanded_where}.points", min_points=2),
                        **raw_signals,
                    }
                )
                continue

            # SPLINE
            spline_points = _flatten_curve_points(
                expanded_any,
                where=f"{expanded_where}.spline",
                flatten_tol=flatten_tol_in_source_units,
                ezdxf_module=ezdxf,
            )
            out.append(
                {
                    "layer": expanded_layer,
                    "type": expanded_type,
                    "closed": bool(getattr(expanded_any, "closed", False)),
                    "points": _normalize_points(spline_points, f"{expanded_where}.points", min_points=2),
                    **raw_signals,
                }
            )

    return [_scale_entity_to_mm(entity, scale_to_mm=unit_scale_to_mm) for entity in out]


def _resolve_insunits_scale_to_mm(doc: Any) -> float:
    raw = doc.header.get("$INSUNITS", 0)
    try:
        code = int(raw)
    except (TypeError, ValueError) as exc:
        raise DxfImportError("DXF_UNSUPPORTED_UNITS", f"invalid DXF INSUNITS value: {raw!r}") from exc

    scale = INSUNITS_MM_SCALE.get(code)
    if scale is None or scale <= 0:
        raise DxfImportError("DXF_UNSUPPORTED_UNITS", f"unsupported DXF INSUNITS value: {code}")
    return float(scale)


def _scale_entity_to_mm(entity: dict[str, Any], *, scale_to_mm: float) -> dict[str, Any]:
    if scale_to_mm == 1.0:
        return entity

    scaled = dict(entity)
    points = scaled.get("points")
    if isinstance(points, list):
        scaled["points"] = [[float(pt[0]) * scale_to_mm, float(pt[1]) * scale_to_mm] for pt in points]

    center = scaled.get("center")
    if isinstance(center, list) and len(center) == 2:
        scaled["center"] = [float(center[0]) * scale_to_mm, float(center[1]) * scale_to_mm]

    radius = scaled.get("radius")
    if isinstance(radius, (int, float)):
        scaled["radius"] = float(radius) * scale_to_mm

    return scaled


def _points_from_curve_vertices(vertices: Any, *, where: str) -> list[list[float]]:
    points: list[list[float]] = []
    for idx, vertex in enumerate(vertices):
        x = _as_finite_float(getattr(vertex, "x", None), where=f"{where}[{idx}].x")
        y = _as_finite_float(getattr(vertex, "y", None), where=f"{where}[{idx}].y")
        points.append([x, y])
        if len(points) > MAX_CURVE_POINTS:
            raise DxfImportError(
                "DXF_CURVE_TOO_COMPLEX",
                f"{where} produced more than {MAX_CURVE_POINTS} points",
            )
    return points


def _flatten_curve_points(curve_entity: Any, *, where: str, flatten_tol: float, ezdxf_module: Any) -> list[list[float]]:
    try:
        points = _points_from_curve_vertices(curve_entity.flattening(flatten_tol), where=f"{where}.flattening")
        if points:
            return points
    except (AttributeError, TypeError, ValueError, ezdxf_module.DXFError):
        pass

    fit_points = list(getattr(curve_entity, "fit_points", []) or [])
    if fit_points:
        return _points_from_curve_vertices(fit_points, where=f"{where}.fit_points")
    control_points = list(getattr(curve_entity, "control_points", []) or [])
    if control_points:
        return _points_from_curve_vertices(control_points, where=f"{where}.control_points")
    raise DxfImportError("DXF_ENTITY_INVALID", f"{where} has no usable points")


def _is_ellipse_closed(entity: Any) -> bool:
    start = float(getattr(entity.dxf, "start_param", 0.0))
    end = float(getattr(entity.dxf, "end_param", math.tau))
    span = (end - start) % math.tau
    return math.isclose(span, 0.0, abs_tol=ELLIPSE_CLOSED_PARAM_EPSILON) or math.isclose(
        span, math.tau, abs_tol=ELLIPSE_CLOSED_PARAM_EPSILON
    )


def _expand_insert_entities(entity: Any, *, where: str, depth: int = 0) -> list[dict[str, Any]]:
    etype = str(entity.dxftype()).upper()
    if etype != "INSERT":
        return [{"entity": entity, "type": etype, "layer": str(entity.dxf.layer)}]

    if depth >= MAX_INSERT_EXPANSION_DEPTH:
        raise DxfImportError("DXF_INSERT_EXPANSION_FAILED", f"{where} exceeded insert expansion depth {MAX_INSERT_EXPANSION_DEPTH}")

    try:
        virtual_entities = list(entity.virtual_entities())
    except Exception as exc:
        raise DxfImportError("DXF_INSERT_EXPANSION_FAILED", f"{where} could not expand INSERT: {exc}") from exc

    expanded: list[dict[str, Any]] = []
    for idx, virtual_entity in enumerate(virtual_entities):
        virtual_where = f"{where}.insert[{idx}]"
        expanded.extend(_expand_insert_entities(virtual_entity, where=virtual_where, depth=depth + 1))
    return expanded


def _normalize_entities(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".json":
        return _extract_entities_from_json(path)
    if path.suffix.lower() == ".dxf":
        return _extract_entities_from_dxf(path)
    raise DxfImportError("DXF_UNSUPPORTED_INPUT", f"unsupported file type: {path.suffix or '<none>'}")


def _distance(a: list[float], b: list[float]) -> float:
    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))


def _orientation(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _point_on_segment(p: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> bool:
    cross = _orientation(a, b, p)
    if abs(cross) > RING_INTERSECTION_EPS:
        return False
    dot = (p[0] - a[0]) * (p[0] - b[0]) + (p[1] - a[1]) * (p[1] - b[1])
    return dot <= RING_INTERSECTION_EPS


def _segments_intersect(a1: tuple[float, float], a2: tuple[float, float], b1: tuple[float, float], b2: tuple[float, float]) -> bool:
    o1 = _orientation(a1, a2, b1)
    o2 = _orientation(a1, a2, b2)
    o3 = _orientation(b1, b2, a1)
    o4 = _orientation(b1, b2, a2)

    if (o1 > RING_INTERSECTION_EPS and o2 < -RING_INTERSECTION_EPS or o1 < -RING_INTERSECTION_EPS and o2 > RING_INTERSECTION_EPS) and (
        o3 > RING_INTERSECTION_EPS and o4 < -RING_INTERSECTION_EPS or o3 < -RING_INTERSECTION_EPS and o4 > RING_INTERSECTION_EPS
    ):
        return True

    if abs(o1) <= RING_INTERSECTION_EPS and _point_on_segment(b1, a1, a2):
        return True
    if abs(o2) <= RING_INTERSECTION_EPS and _point_on_segment(b2, a1, a2):
        return True
    if abs(o3) <= RING_INTERSECTION_EPS and _point_on_segment(a1, b1, b2):
        return True
    if abs(o4) <= RING_INTERSECTION_EPS and _point_on_segment(a2, b1, b2):
        return True
    return False


def _ring_has_self_intersection(ring: list[list[float]]) -> bool:
    points = [(float(p[0]), float(p[1])) for p in ring]
    n = len(points)
    if n < 3:
        return True

    for i in range(n):
        a1 = points[i]
        a2 = points[(i + 1) % n]
        for j in range(i + 1, n):
            if abs(i - j) <= 1:
                continue
            if i == 0 and j == n - 1:
                continue
            b1 = points[j]
            b2 = points[(j + 1) % n]
            if _segments_intersect(a1, a2, b1, b2):
                return True
    return False


def _assert_non_self_intersecting(ring: list[list[float]], *, where: str) -> None:
    if len(ring) > MAX_SELF_INTERSECTION_SEGMENTS:
        raise DxfImportError(
            "DXF_RING_TOO_COMPLEX",
            f"{where} has too many segments ({len(ring)} > {MAX_SELF_INTERSECTION_SEGMENTS})",
        )
    if _ring_has_self_intersection(ring):
        raise DxfImportError("DXF_INVALID_RING", f"self-intersecting contour at {where}")


def _reverse_path(points: list[list[float]]) -> list[list[float]]:
    rev = list(reversed(points))
    return [[float(x), float(y)] for x, y in rev]


def _append_path(dst: list[list[float]], src: list[list[float]]) -> None:
    if not src:
        return
    if not dst:
        dst.extend(src)
        return

    if _distance(dst[-1], src[0]) <= CHAIN_ENDPOINT_EPSILON_MM:
        dst.extend(src[1:])
        return

    dst.extend(src)


def _prepend_path(dst: list[list[float]], src: list[list[float]]) -> None:
    if not src:
        return
    if not dst:
        dst.extend(src)
        return

    if _distance(src[-1], dst[0]) <= CHAIN_ENDPOINT_EPSILON_MM:
        dst[:0] = src[:-1]
        return

    dst[:0] = src


def _chain_segments_to_rings(segments: list[list[list[float]]], *, layer: str) -> tuple[list[list[list[float]]], list[list[list[float]]]]:
    simplify_tol_mm = rdp_tol_mm_from_env()
    epsilon = CHAIN_ENDPOINT_EPSILON_MM
    scale = 1.0 / epsilon if epsilon > 0 else 1.0

    def _endpoint_key(point: list[float]) -> tuple[int, int]:
        return (int(round(float(point[0]) * scale)), int(round(float(point[1]) * scale)))

    def _segment_signature(segment: list[list[float]]) -> tuple[tuple[int, int], ...]:
        forward = tuple(_endpoint_key(point) for point in segment)
        reverse = tuple(reversed(forward))
        return forward if forward <= reverse else reverse

    remaining: list[list[list[float]]] = []
    seen_segments: set[tuple[tuple[int, int], ...]] = set()
    for segment in segments:
        if len(segment) < 2:
            continue
        normalized_segment = [[float(point[0]), float(point[1])] for point in segment]
        signature = _segment_signature(normalized_segment)
        if signature in seen_segments:
            continue
        seen_segments.add(signature)
        remaining.append(normalized_segment)

    rings: list[list[list[float]]] = []
    open_paths: list[list[list[float]]] = []

    if not remaining:
        return rings, open_paths

    alive: set[int] = set(range(len(remaining)))
    start_index: dict[tuple[int, int], set[int]] = {}
    end_index: dict[tuple[int, int], set[int]] = {}

    def _index_add(seg_idx: int) -> None:
        seg = remaining[seg_idx]
        skey = _endpoint_key(seg[0])
        ekey = _endpoint_key(seg[-1])
        start_index.setdefault(skey, set()).add(seg_idx)
        end_index.setdefault(ekey, set()).add(seg_idx)

    def _index_remove(seg_idx: int) -> None:
        seg = remaining[seg_idx]
        skey = _endpoint_key(seg[0])
        ekey = _endpoint_key(seg[-1])
        start_set = start_index.get(skey)
        if start_set is not None:
            start_set.discard(seg_idx)
            if not start_set:
                start_index.pop(skey, None)
        end_set = end_index.get(ekey)
        if end_set is not None:
            end_set.discard(seg_idx)
            if not end_set:
                end_index.pop(ekey, None)

    for seg_idx in sorted(alive):
        _index_add(seg_idx)

    def _consume_segment(seg_idx: int) -> list[list[float]]:
        _index_remove(seg_idx)
        alive.discard(seg_idx)
        return [list(p) for p in remaining[seg_idx]]

    while alive:
        current_idx = min(alive)
        chain = _consume_segment(current_idx)
        progressed = True
        while progressed and alive:
            progressed = False
            start = chain[0]
            end = chain[-1]

            candidate_idx_pool: set[int] = set()
            candidate_idx_pool.update(start_index.get(_endpoint_key(end), set()))
            candidate_idx_pool.update(end_index.get(_endpoint_key(end), set()))
            candidate_idx_pool.update(start_index.get(_endpoint_key(start), set()))
            candidate_idx_pool.update(end_index.get(_endpoint_key(start), set()))

            for idx in sorted(candidate_idx_pool):
                if idx not in alive:
                    continue
                candidate = remaining[idx]
                cand_forward = candidate
                cand_reverse = _reverse_path(candidate)

                if _distance(end, cand_forward[0]) <= CHAIN_ENDPOINT_EPSILON_MM:
                    _append_path(chain, cand_forward)
                    _consume_segment(idx)
                    progressed = True
                    break
                if _distance(end, cand_reverse[0]) <= CHAIN_ENDPOINT_EPSILON_MM:
                    _append_path(chain, cand_reverse)
                    _consume_segment(idx)
                    progressed = True
                    break
                if _distance(start, cand_forward[-1]) <= CHAIN_ENDPOINT_EPSILON_MM:
                    _prepend_path(chain, cand_forward)
                    _consume_segment(idx)
                    progressed = True
                    break
                if _distance(start, cand_reverse[-1]) <= CHAIN_ENDPOINT_EPSILON_MM:
                    _prepend_path(chain, cand_reverse)
                    _consume_segment(idx)
                    progressed = True
                    break

        if len(chain) >= 3 and _distance(chain[0], chain[-1]) <= CHAIN_ENDPOINT_EPSILON_MM:
            chain[-1] = [float(chain[0][0]), float(chain[0][1])]
            try:
                ring = clean_ring(
                    chain,
                    min_edge_len=1e-6,
                    ccw=True,
                    simplify_tol_mm=simplify_tol_mm,
                    where=f"{layer}.chain",
                )
                _assert_non_self_intersecting(ring, where=f"{layer}.chain")
                rings.append(ring)
            except GeometryCleanError as exc:
                raise DxfImportError("DXF_INVALID_RING", f"failed to normalize chained contour on {layer}: {exc}") from exc
        else:
            open_paths.append(chain)

    return rings, open_paths


def _entity_to_path(entity: dict[str, Any], where: str) -> list[list[float]]:
    etype = str(entity.get("type", "")).upper()

    if etype in {"LWPOLYLINE", "POLYLINE", "LINE", "SPLINE", "ELLIPSE"}:
        points = entity.get("points")
        if not isinstance(points, list):
            raise DxfImportError("DXF_ENTITY_INVALID", f"{where}.points must be list")
        out = _normalize_points(points, f"{where}.points", min_points=2)
        entity_closed = bool(entity.get("closed", False))
        should_strip_closing_point = etype != "LINE" and entity_closed
        if should_strip_closing_point and len(out) >= 2 and _distance(out[0], out[-1]) <= POINT_CLOSE_EPSILON_MM:
            out = out[:-1]
        return out

    if etype in {"ARC", "CIRCLE"}:
        center = entity.get("center")
        radius = entity.get("radius")
        start = entity.get("start_angle", 0.0)
        end = entity.get("end_angle", 360.0)
        if not isinstance(center, list) or len(center) != 2:
            raise DxfImportError("DXF_ENTITY_INVALID", f"{where}.center must be [x, y]")
        center_x = _as_finite_float_entity(center[0], where=f"{where}.center[0]")
        center_y = _as_finite_float_entity(center[1], where=f"{where}.center[1]")
        radius_f = _as_finite_float_entity(radius, where=f"{where}.radius")
        start_f = _as_finite_float_entity(start, where=f"{where}.start_angle")
        end_f = _as_finite_float_entity(end, where=f"{where}.end_angle")
        if radius_f <= 0:
            raise DxfImportError("DXF_ENTITY_INVALID", f"{where}.radius must be positive number")
        points = arc_to_points(
            center_x=center_x,
            center_y=center_y,
            radius=radius_f,
            start_angle_deg=start_f,
            end_angle_deg=end_f,
            max_chord_error_mm=CURVE_FLATTEN_TOLERANCE_MM,
            min_segments=ARC_POLYGONIZE_MIN_SEGMENTS,
            wrap_ccw=True,
        )
        points = _normalize_points(points, f"{where}.arc_points", min_points=2)
        if etype == "CIRCLE" and len(points) >= 2 and _distance(points[0], points[-1]) <= POINT_CLOSE_EPSILON_MM:
            points = points[:-1]
        return points

    raise DxfImportError("DXF_UNSUPPORTED_ENTITY_TYPE", f"{where} has unsupported type {etype}")


def _collect_layer_rings(
    entities: list[dict[str, Any]], *, layer: str
) -> tuple[list[list[list[float]]], list[list[list[float]]]]:
    """Return ``(rings, open_paths)`` where ``open_paths`` is the list of residual chains."""
    simplify_tol_mm = rdp_tol_mm_from_env()
    direct_rings: list[list[list[float]]] = []
    segment_paths: list[list[list[float]]] = []

    for idx, entity in enumerate(entities):
        etype = str(entity.get("type", "")).upper()
        where = f"{layer}[{idx}]"

        if entity.get("_unsupported") or etype not in SUPPORTED_LAYER_ENTITY_TYPES:
            raise DxfImportError("DXF_UNSUPPORTED_ENTITY_TYPE", f"{where} uses unsupported type {etype}")

        closed = bool(entity.get("closed", False))
        path = _entity_to_path(entity, where)
        if len(path) < 2:
            continue

        if etype in {"LWPOLYLINE", "POLYLINE"} and closed:
            ring_points = path + [path[0]]
            try:
                ring = clean_ring(
                    ring_points,
                    min_edge_len=1e-6,
                    ccw=True,
                    simplify_tol_mm=simplify_tol_mm,
                    where=f"{where}.closed",
                )
                _assert_non_self_intersecting(ring, where=f"{where}.closed")
                direct_rings.append(ring)
            except GeometryCleanError as exc:
                raise DxfImportError("DXF_INVALID_RING", f"invalid closed contour at {where}: {exc}") from exc
            continue

        if etype == "CIRCLE":
            ring_points = path + [path[0]]
            try:
                ring = clean_ring(
                    ring_points,
                    min_edge_len=1e-6,
                    ccw=True,
                    simplify_tol_mm=simplify_tol_mm,
                    where=f"{where}.circle",
                )
                _assert_non_self_intersecting(ring, where=f"{where}.circle")
                direct_rings.append(ring)
            except GeometryCleanError as exc:
                raise DxfImportError("DXF_INVALID_RING", f"invalid circle contour at {where}: {exc}") from exc
            continue

        if etype in {"SPLINE", "ELLIPSE"} and closed:
            ring_points = list(path)
            if _distance(ring_points[0], ring_points[-1]) <= CHAIN_ENDPOINT_EPSILON_MM:
                ring_points[-1] = list(ring_points[0])
            else:
                ring_points.append(list(ring_points[0]))
            try:
                ring = clean_ring(
                    ring_points,
                    min_edge_len=1e-6,
                    ccw=True,
                    simplify_tol_mm=simplify_tol_mm,
                    where=f"{where}.spline",
                )
                _assert_non_self_intersecting(ring, where=f"{where}.spline")
                direct_rings.append(ring)
            except GeometryCleanError as exc:
                raise DxfImportError("DXF_INVALID_RING", f"invalid spline contour at {where}: {exc}") from exc
            continue

        segment_paths.append(path)

    chained_rings, open_paths = _chain_segments_to_rings(segment_paths, layer=layer)
    return direct_rings + chained_rings, open_paths


def import_part_raw(
    source_path: str | Path,
    *,
    outer_layer: str = OUTER_LAYER_DEFAULT,
    inner_layer: str = INNER_LAYER_DEFAULT,
) -> PartRaw:
    """Import and normalize one part geometry from a DXF/fixture source."""

    path = Path(source_path)
    if not path.is_file():
        raise DxfImportError("DXF_PATH_NOT_FOUND", f"input file not found: {path}")

    entities = _normalize_entities(path)
    layer_entities = [entity for entity in entities if entity.get("layer") in {outer_layer, inner_layer}]

    outer_entities = [entity for entity in layer_entities if entity.get("layer") == outer_layer]
    inner_entities = [entity for entity in layer_entities if entity.get("layer") == inner_layer]

    outer_rings, outer_open_paths = _collect_layer_rings(outer_entities, layer=outer_layer)
    inner_rings, inner_open_paths = _collect_layer_rings(inner_entities, layer=inner_layer)
    outer_open = len(outer_open_paths)
    inner_open = len(inner_open_paths)

    if not outer_rings:
        if outer_open > 0:
            raise DxfImportError("DXF_OPEN_OUTER_PATH", f"open contour on {outer_layer}")
        raise DxfImportError("DXF_NO_OUTER_LAYER", f"no closed contour found on layer {outer_layer}")
    if len(outer_rings) > 1:
        raise DxfImportError("DXF_MULTIPLE_OUTERS", f"multiple closed contours found on layer {outer_layer}")
    if outer_open > 0:
        raise DxfImportError("DXF_OPEN_OUTER_PATH", f"open contour on {outer_layer}")
    if inner_open > 0:
        raise DxfImportError("DXF_OPEN_INNER_PATH", f"open contour on {inner_layer}")

    return PartRaw(
        outer_points_mm=outer_rings[0],
        holes_points_mm=inner_rings,
        source_path=str(path.resolve()),
        source_entities=layer_entities,
    )


def normalize_source_entities(source_path: str | Path) -> list[dict[str, Any]]:
    """Public, read-only normalization for DXF preflight inspect (E2-T1).

    This is the single surface that preflight inspect services (e.g.
    ``api/services/dxf_preflight_inspect.py``) should use to read raw,
    non-role-assigned source entities. It intentionally does NOT run any
    repair, role resolution or acceptance gate: that scope is reserved for
    later prefilter tasks (E2-T2 / E2-T3 / E2-T6).

    Each returned entity preserves the preflight raw signals that the later
    lane will depend on:

    * ``layer`` (str)
    * ``type`` (str, upper-cased)
    * ``closed`` (bool, when applicable)
    * ``color_index`` (int | None) -- raw ACI-style color index if available
    * ``linetype_name`` (str | None) -- raw linetype name if available
    * geometry payload fields (``points`` / ``center`` / ``radius`` / ...)

    When the source backend cannot supply an explicit color/linetype value,
    the field is set to ``None`` deterministically; no RGB or BYLAYER policy
    is invented here.
    """

    path = Path(source_path)
    if not path.is_file():
        raise DxfImportError("DXF_PATH_NOT_FOUND", f"input file not found: {path}")
    return _normalize_entities(path)


def probe_layer_rings(
    entities: list[dict[str, Any]], *, layer: str
) -> dict[str, Any]:
    """Soft, non-raising ring-candidate probe for a single layer (E2-T1).

    Wraps the existing internal ``_collect_layer_rings`` chainer so the
    caller always gets a deterministic dict back, even when the layer's
    geometry is not clean enough to produce rings. A hard importer error on
    this layer is surfaced as a structured diagnostic (``hard_error``)
    instead of being raised, so the preflight inspect service can report
    multiple layers in one pass without short-circuiting.

    Returned shape::

        {
            "layer": str,
            "entity_count": int,
            "rings": list[list[list[float]]],
            "open_path_count": int,
            "hard_error": {"code": str, "message": str} | None,
        }

    The function is intentionally inspect-only: no role assignment, no gap
    repair, no acceptance outcome.
    """

    layer_entities = [entity for entity in entities if entity.get("layer") == layer]
    # Unsupported entity types (TEXT, MTEXT, …) are annotation-only; skip them
    # in the probe so they don't abort ring detection on geometry layers.
    supported_entities = [e for e in layer_entities if not e.get("_unsupported")]
    try:
        rings, open_path_list = _collect_layer_rings(supported_entities, layer=layer)
    except DxfImportError as exc:
        return {
            "layer": layer,
            "entity_count": len(layer_entities),
            "rings": [],
            "open_path_count": 0,
            "hard_error": {"code": exc.code, "message": exc.message},
        }
    return {
        "layer": layer,
        "entity_count": len(layer_entities),
        "rings": rings,
        "open_path_count": len(open_path_list),
        "hard_error": None,
    }


def probe_layer_open_paths(
    entities: list[dict[str, Any]], *, layer: str
) -> dict[str, Any]:
    """Return structured endpoint evidence for residual open path chains (E2-T3).

    Extends ``probe_layer_rings`` with per-chain endpoint geometry so the T3
    gap repair service can determine whether a gap is repairable without
    re-implementing chaining logic.

    The open paths returned here are the *residual* chains that the importer's
    own ``_chain_segments_to_rings`` could not close within
    ``CHAIN_ENDPOINT_EPSILON_MM`` (0.2 mm). These are the starting point for
    the T3 gap repair layer.

    Returned shape::

        {
            "layer": str,
            "entity_count": int,
            "open_paths": [
                {
                    "path_index": int,
                    "point_count": int,
                    "start_point": [float, float],
                    "end_point": [float, float],
                    "points": list[list[float]],
                }
            ],
            "hard_error": {"code": str, "message": str} | None,
        }

    The ``points`` list carries the full chain geometry so the T3 service can
    produce a repaired ring without re-reading the source file. The function
    is intentionally inspect/repair-safe: no role assignment, no acceptance
    outcome.
    """
    layer_entities = [entity for entity in entities if entity.get("layer") == layer]
    supported_entities = [e for e in layer_entities if not e.get("_unsupported")]
    try:
        _rings, open_path_chains = _collect_layer_rings(supported_entities, layer=layer)
    except DxfImportError as exc:
        return {
            "layer": layer,
            "entity_count": len(layer_entities),
            "open_paths": [],
            "hard_error": {"code": exc.code, "message": exc.message},
        }

    structured: list[dict[str, Any]] = []
    for idx, chain in enumerate(open_path_chains):
        if len(chain) < 2:
            continue
        structured.append(
            {
                "path_index": idx,
                "point_count": len(chain),
                "start_point": [float(chain[0][0]), float(chain[0][1])],
                "end_point": [float(chain[-1][0]), float(chain[-1][1])],
                "points": [[float(p[0]), float(p[1])] for p in chain],
            }
        )
    return {
        "layer": layer,
        "entity_count": len(layer_entities),
        "open_paths": structured,
        "hard_error": None,
    }
