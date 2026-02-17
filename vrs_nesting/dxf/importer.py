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

from vrs_nesting.geometry.clean import GeometryCleanError, clean_ring
from vrs_nesting.geometry.polygonize import arc_to_points


OUTER_LAYER_DEFAULT = "CUT_OUTER"
INNER_LAYER_DEFAULT = "CUT_INNER"
SUPPORTED_LAYER_ENTITY_TYPES = {"LWPOLYLINE", "POLYLINE", "LINE", "ARC", "CIRCLE", "SPLINE", "ELLIPSE"}
CHAIN_ENDPOINT_EPSILON_MM = 0.2
ARC_CHORD_ERROR_MM = 0.2
ELLIPSE_CLOSED_PARAM_EPSILON = 1e-6
MAX_INSERT_EXPANSION_DEPTH = 8
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


def _normalize_points(raw: Any, where: str, *, min_points: int = 3) -> list[list[float]]:
    if not isinstance(raw, list):
        raise DxfImportError("DXF_INVALID_POINTS", f"{where} must be list")

    points: list[list[float]] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise DxfImportError("DXF_INVALID_POINTS", f"{where}[{idx}] must be [x, y]")
        x, y = item
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise DxfImportError("DXF_INVALID_POINTS", f"{where}[{idx}] coordinates must be numeric")
        points.append([float(x), float(y)])

    if len(points) < min_points:
        raise DxfImportError("DXF_INVALID_RING", f"{where} must contain at least {min_points} points")

    return points


def _is_closed_entity(entity: dict[str, Any], where: str, default: bool = False) -> bool:
    closed = entity.get("closed", default)
    if not isinstance(closed, bool):
        raise DxfImportError("DXF_ENTITY_INVALID", f"{where}.closed must be boolean")
    return closed


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
            start = float(entity.get("start_angle", 0.0))
            end = float(entity.get("end_angle", 360.0 if etype == "CIRCLE" else 0.0))
            if not isinstance(cx, (int, float)) or not isinstance(cy, (int, float)):
                raise DxfImportError("DXF_ENTITY_INVALID", f"{where}.center coordinates must be numeric")
            if not isinstance(radius, (int, float)) or float(radius) <= 0:
                raise DxfImportError("DXF_ENTITY_INVALID", f"{where}.radius must be positive number")
            out_entity.update(
                {
                    "center": [float(cx), float(cy)],
                    "radius": float(radius),
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
    flatten_tol_in_source_units = ARC_CHORD_ERROR_MM / unit_scale_to_mm
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

            if expanded_type not in SUPPORTED_LAYER_ENTITY_TYPES:
                out.append({"layer": expanded_layer, "type": expanded_type, "_unsupported": True})
                continue

            if expanded_type == "LWPOLYLINE":
                lw_points = [[float(x), float(y)] for x, y, *_ in expanded_any.get_points("xy")]
                out.append(
                    {
                        "layer": expanded_layer,
                        "type": expanded_type,
                        "closed": bool(expanded_any.closed),
                        "points": _normalize_points(lw_points, f"{expanded_where}.points"),
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


def _flatten_curve_points(curve_entity: Any, *, where: str, flatten_tol: float, ezdxf_module: Any) -> list[list[float]]:
    try:
        return [[float(v.x), float(v.y)] for v in curve_entity.flattening(flatten_tol)]
    except (AttributeError, TypeError, ValueError, ezdxf_module.DXFError):
        fit_points = list(getattr(curve_entity, "fit_points", []) or [])
        if fit_points:
            return [[float(v.x), float(v.y)] for v in fit_points]
        control_points = list(getattr(curve_entity, "control_points", []) or [])
        if control_points:
            return [[float(v.x), float(v.y)] for v in control_points]
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


def _chain_segments_to_rings(segments: list[list[list[float]]], *, layer: str) -> tuple[list[list[list[float]]], list[list[list[float]]]]:
    remaining = [seg for seg in segments if len(seg) >= 2]
    rings: list[list[list[float]]] = []
    open_paths: list[list[list[float]]] = []

    while remaining:
        chain = [list(p) for p in remaining.pop(0)]
        progressed = True
        while progressed and remaining:
            progressed = False
            for idx, candidate in enumerate(remaining):
                cand_forward = candidate
                cand_reverse = _reverse_path(candidate)

                end = chain[-1]
                if _distance(end, cand_forward[0]) <= CHAIN_ENDPOINT_EPSILON_MM:
                    _append_path(chain, cand_forward)
                    remaining.pop(idx)
                    progressed = True
                    break
                if _distance(end, cand_reverse[0]) <= CHAIN_ENDPOINT_EPSILON_MM:
                    _append_path(chain, cand_reverse)
                    remaining.pop(idx)
                    progressed = True
                    break

        if len(chain) >= 3 and _distance(chain[0], chain[-1]) <= CHAIN_ENDPOINT_EPSILON_MM:
            chain[-1] = [float(chain[0][0]), float(chain[0][1])]
            try:
                ring = clean_ring(chain, min_edge_len=1e-6, ccw=True, where=f"{layer}.chain")
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
        out = [[float(p[0]), float(p[1])] for p in points]
        if etype != "LINE" and len(out) >= 2 and out[0] == out[-1]:
            out = out[:-1]
        return out

    if etype in {"ARC", "CIRCLE"}:
        center = entity.get("center")
        radius = entity.get("radius")
        start = entity.get("start_angle", 0.0)
        end = entity.get("end_angle", 360.0)
        if not isinstance(center, list) or len(center) != 2:
            raise DxfImportError("DXF_ENTITY_INVALID", f"{where}.center must be [x, y]")
        if not isinstance(radius, (int, float)):
            raise DxfImportError("DXF_ENTITY_INVALID", f"{where}.radius must be numeric")
        points = arc_to_points(
            center_x=float(center[0]),
            center_y=float(center[1]),
            radius=float(radius),
            start_angle_deg=float(start),
            end_angle_deg=float(end),
            max_chord_error_mm=ARC_CHORD_ERROR_MM,
            min_segments=12,
        )
        if len(points) >= 2 and points[0] == points[-1]:
            points = points[:-1]
        return points

    raise DxfImportError("DXF_UNSUPPORTED_ENTITY_TYPE", f"{where} has unsupported type {etype}")


def _collect_layer_rings(entities: list[dict[str, Any]], *, layer: str) -> tuple[list[list[list[float]]], int]:
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
                direct_rings.append(clean_ring(ring_points, min_edge_len=1e-6, ccw=True, where=f"{where}.closed"))
            except GeometryCleanError as exc:
                raise DxfImportError("DXF_INVALID_RING", f"invalid closed contour at {where}: {exc}") from exc
            continue

        if etype == "CIRCLE":
            ring_points = path + [path[0]]
            try:
                direct_rings.append(clean_ring(ring_points, min_edge_len=1e-6, ccw=True, where=f"{where}.circle"))
            except GeometryCleanError as exc:
                raise DxfImportError("DXF_INVALID_RING", f"invalid circle contour at {where}: {exc}") from exc
            continue

        if etype in {"SPLINE", "ELLIPSE"} and closed and _distance(path[0], path[-1]) <= CHAIN_ENDPOINT_EPSILON_MM:
            ring_points = list(path)
            ring_points[-1] = list(ring_points[0])
            try:
                direct_rings.append(clean_ring(ring_points, min_edge_len=1e-6, ccw=True, where=f"{where}.spline"))
            except GeometryCleanError as exc:
                raise DxfImportError("DXF_INVALID_RING", f"invalid spline contour at {where}: {exc}") from exc
            continue

        segment_paths.append(path)

    chained_rings, open_paths = _chain_segments_to_rings(segment_paths, layer=layer)
    return direct_rings + chained_rings, len(open_paths)


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

    outer_rings, outer_open = _collect_layer_rings(outer_entities, layer=outer_layer)
    inner_rings, inner_open = _collect_layer_rings(inner_entities, layer=inner_layer)

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
