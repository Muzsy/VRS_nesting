#!/usr/bin/env python3
"""DXF import helper with strict CUT_OUTER / CUT_INNER layer conventions.

The module supports two input backends:
- `.json` fixture format used by deterministic repo smoke checks.
- `.dxf` files via optional `ezdxf` dependency when available.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


OUTER_LAYER_DEFAULT = "CUT_OUTER"
INNER_LAYER_DEFAULT = "CUT_INNER"
SUPPORTED_LAYER_ENTITY_TYPES = {"LWPOLYLINE", "POLYLINE"}


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "outer_points_mm": self.outer_points_mm,
            "holes_points_mm": self.holes_points_mm,
            "source_path": self.source_path,
        }


def _normalize_points(raw: Any, where: str) -> list[list[float]]:
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

    if len(points) < 3:
        raise DxfImportError("DXF_INVALID_RING", f"{where} must contain at least 3 points")

    if points[0] == points[-1]:
        points = points[:-1]

    if len(points) < 3:
        raise DxfImportError("DXF_INVALID_RING", f"{where} must contain at least 3 unique points")

    return points


def _is_closed_entity(entity: dict[str, Any], where: str) -> bool:
    closed = entity.get("closed")
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
        layer = entity.get("layer")
        etype = entity.get("type", "LWPOLYLINE")
        if not isinstance(layer, str) or not layer.strip():
            raise DxfImportError("DXF_ENTITY_INVALID", f"entities[{idx}].layer must be non-empty string")
        if not isinstance(etype, str) or not etype.strip():
            raise DxfImportError("DXF_ENTITY_INVALID", f"entities[{idx}].type must be non-empty string")

        out.append(
            {
                "layer": layer.strip(),
                "type": etype.strip().upper(),
                "closed": _is_closed_entity(entity, f"entities[{idx}]"),
                "points": _normalize_points(entity.get("points"), f"entities[{idx}].points"),
            }
        )

    return out


def _extract_entities_from_dxf(path: Path) -> list[dict[str, Any]]:
    try:
        import ezdxf  # type: ignore
    except ImportError as exc:
        raise DxfImportError("DXF_BACKEND_MISSING", "ezdxf not installed; use JSON fixture backend or install ezdxf") from exc

    try:
        doc = ezdxf.readfile(path)
    except Exception as exc:  # noqa: BLE001
        raise DxfImportError("DXF_READ_FAILED", f"could not read dxf: {path}: {exc}") from exc

    msp = doc.modelspace()
    out: list[dict[str, Any]] = []
    for idx, entity in enumerate(msp):
        etype = entity.dxftype().upper()
        layer = str(entity.dxf.layer)

        if etype not in SUPPORTED_LAYER_ENTITY_TYPES:
            out.append(
                {
                    "layer": layer,
                    "type": etype,
                    "closed": False,
                    "points": [],
                    "_unsupported": True,
                    "_where": f"modelspace[{idx}]",
                }
            )
            continue

        if etype == "LWPOLYLINE":
            points = [[float(x), float(y)] for x, y, *_ in entity.get_points("xy")]
            closed = bool(entity.closed)
        else:  # POLYLINE
            points = [[float(v.dxf.location.x), float(v.dxf.location.y)] for v in entity.vertices]
            closed = bool(entity.is_closed)

        out.append(
            {
                "layer": layer,
                "type": etype,
                "closed": closed,
                "points": _normalize_points(points, f"modelspace[{idx}].points"),
            }
        )

    return out


def _normalize_entities(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".json":
        return _extract_entities_from_json(path)
    if path.suffix.lower() == ".dxf":
        return _extract_entities_from_dxf(path)
    raise DxfImportError("DXF_UNSUPPORTED_INPUT", f"unsupported file type: {path.suffix or '<none>'}")


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
    outer: list[list[list[float]]] = []
    holes: list[list[list[float]]] = []

    for idx, entity in enumerate(entities):
        layer = entity.get("layer")
        etype = entity.get("type")
        where = f"entities[{idx}]"

        if layer not in {outer_layer, inner_layer}:
            continue

        if entity.get("_unsupported") or etype not in SUPPORTED_LAYER_ENTITY_TYPES:
            raise DxfImportError(
                "DXF_UNSUPPORTED_ENTITY_TYPE",
                f"{where} on layer {layer} uses unsupported type {etype}",
            )

        if not bool(entity.get("closed")):
            if layer == outer_layer:
                raise DxfImportError("DXF_OPEN_OUTER_PATH", f"open contour on {outer_layer} at {where}")
            raise DxfImportError("DXF_OPEN_INNER_PATH", f"open contour on {inner_layer} at {where}")

        points = _normalize_points(entity.get("points"), f"{where}.points")
        if layer == outer_layer:
            outer.append(points)
        else:
            holes.append(points)

    if not outer:
        raise DxfImportError("DXF_NO_OUTER_LAYER", f"no closed contour found on layer {outer_layer}")
    if len(outer) > 1:
        raise DxfImportError("DXF_MULTIPLE_OUTERS", f"multiple closed contours found on layer {outer_layer}")

    return PartRaw(
        outer_points_mm=outer[0],
        holes_points_mm=holes,
        source_path=str(path.resolve()),
    )
