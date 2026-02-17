#!/usr/bin/env python3
"""Per-sheet DXF exporter using approx polygons or source geometry BLOCK+INSERT."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vrs_nesting.dxf.importer import import_part_raw


class DxfExportError(RuntimeError):
    """Raised when export input is invalid."""


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise DxfExportError(f"missing json file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DxfExportError(f"invalid json {path}: line={exc.lineno} col={exc.colno}") from exc
    if not isinstance(payload, dict):
        raise DxfExportError(f"top-level object required: {path}")
    return payload


def _parse_point(raw: Any, where: str) -> tuple[float, float]:
    if isinstance(raw, (list, tuple)) and len(raw) == 2:
        x, y = raw
    elif isinstance(raw, dict) and "x" in raw and "y" in raw:
        x, y = raw["x"], raw["y"]
    else:
        raise DxfExportError(f"invalid point format at {where}")

    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        raise DxfExportError(f"point coordinates must be numeric at {where}")
    return float(x), float(y)


def _parse_polygon(raw: Any, where: str) -> list[tuple[float, float]]:
    if not isinstance(raw, list):
        raise DxfExportError(f"polygon must be list at {where}")
    pts = [_parse_point(point, f"{where}[{idx}]") for idx, point in enumerate(raw)]
    if len(pts) < 3:
        raise DxfExportError(f"polygon must have >=3 points at {where}")
    return pts


def _normalize_allowed_rotations(part: dict[str, Any], where: str) -> list[int]:
    raw = part.get("allowed_rotations_deg", [0])
    if not isinstance(raw, list) or not raw:
        raise DxfExportError(f"{where}.allowed_rotations_deg must be non-empty list")

    out: list[int] = []
    seen: set[int] = set()
    for idx, value in enumerate(raw):
        if not isinstance(value, int) or isinstance(value, bool):
            raise DxfExportError(f"{where}.allowed_rotations_deg[{idx}] must be integer")
        rot = value % 360
        if rot not in (0, 90, 180, 270):
            raise DxfExportError(f"{where}.allowed_rotations_deg[{idx}] must be one of 0,90,180,270")
        if rot not in seen:
            seen.add(rot)
            out.append(rot)
    return out


def _normalize_loops(
    outer: list[tuple[float, float]],
    holes: list[list[tuple[float, float]]],
) -> tuple[list[tuple[float, float]], list[list[tuple[float, float]]]]:
    all_points = list(outer)
    for hole in holes:
        all_points.extend(hole)

    min_x = min(p[0] for p in all_points)
    min_y = min(p[1] for p in all_points)

    def shift_loop(loop: list[tuple[float, float]]) -> list[tuple[float, float]]:
        return [(x - min_x, y - min_y) for (x, y) in loop]

    return shift_loop(outer), [shift_loop(hole) for hole in holes]


def _part_defs(input_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    parts = input_payload.get("parts")
    if not isinstance(parts, list):
        raise DxfExportError("input.parts must be a list")

    out: dict[str, dict[str, Any]] = {}
    for idx, part in enumerate(parts):
        if not isinstance(part, dict):
            raise DxfExportError("part entry must be object")

        part_id = str(part.get("id", "")).strip()
        width = part.get("width")
        height = part.get("height")
        if not part_id:
            raise DxfExportError("part.id must be non-empty")
        if not isinstance(width, (int, float)) or width <= 0:
            raise DxfExportError(f"invalid width for part {part_id}")
        if not isinstance(height, (int, float)) or height <= 0:
            raise DxfExportError(f"invalid height for part {part_id}")

        allowed_rotations = _normalize_allowed_rotations(part, f"parts[{idx}]")

        outer_raw = part.get("source_outer_points", part.get("outer_points"))
        holes_raw = part.get("source_holes_points", part.get("holes_points", []))
        if outer_raw is None:
            outer = [(0.0, 0.0), (float(width), 0.0), (float(width), float(height)), (0.0, float(height))]
            holes: list[list[tuple[float, float]]] = []
        else:
            outer = _parse_polygon(outer_raw, f"parts[{idx}].outer_points")
            if holes_raw is None:
                holes = []
            elif isinstance(holes_raw, list):
                holes = [_parse_polygon(hole, f"parts[{idx}].holes_points[{hidx}]") for hidx, hole in enumerate(holes_raw)]
            else:
                raise DxfExportError(f"parts[{idx}].holes_points must be list")

        outer, holes = _normalize_loops(outer, holes)
        source_entities = part.get("source_entities", [])
        if not isinstance(source_entities, list):
            source_entities = []
        out[part_id] = {
            "width": float(width),
            "height": float(height),
            "allowed_rotations": allowed_rotations,
            "outer": outer,
            "holes": holes,
            "source_entities": source_entities,
        }

    return out


def _sheet_sizes(input_payload: dict[str, Any]) -> dict[int, tuple[float, float]]:
    stocks = input_payload.get("stocks")
    if not isinstance(stocks, list):
        raise DxfExportError("input.stocks must be a list")

    out: dict[int, tuple[float, float]] = {}
    idx = 0
    for stock in stocks:
        if not isinstance(stock, dict):
            raise DxfExportError("stock entry must be object")

        width = stock.get("width")
        height = stock.get("height")
        quantity = stock.get("quantity")

        if not isinstance(width, (int, float)) or width <= 0:
            raise DxfExportError("stock.width must be positive number")
        if not isinstance(height, (int, float)) or height <= 0:
            raise DxfExportError("stock.height must be positive number")
        if not isinstance(quantity, int) or quantity <= 0:
            raise DxfExportError("stock.quantity must be positive integer")

        for _ in range(quantity):
            out[idx] = (float(width), float(height))
            idx += 1

    return out


def _approx_block_name(part_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_]", "_", part_id)
    if not safe:
        safe = "PART"
    digest = hashlib.sha1(part_id.encode("utf-8")).hexdigest()[:10].upper()
    return f"PART_{safe.upper()}_{digest}"


def _source_block_name(part_id: str, source_meta: dict[str, Any]) -> str:
    safe = re.sub(r"[^A-Za-z0-9_]", "_", part_id)
    if not safe:
        safe = "PART"

    stable_source = {
        "part_id": part_id,
        "source_dxf_path": str(Path(source_meta["source_dxf_path"]).resolve()),
        "source_layers": source_meta["source_layers"],
        "source_base_offset_mm": source_meta["source_base_offset_mm"],
    }
    digest = hashlib.sha1(json.dumps(stable_source, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:10]
    return f"P_{safe.upper()}_{digest.upper()}"


def _add_line_entity(lines: list[str], x1: float, y1: float, x2: float, y2: float, layer: str) -> None:
    lines.extend(
        [
            "0",
            "LINE",
            "8",
            layer,
            "10",
            f"{x1:.6f}",
            "20",
            f"{y1:.6f}",
            "30",
            "0.0",
            "11",
            f"{x2:.6f}",
            "21",
            f"{y2:.6f}",
            "31",
            "0.0",
        ]
    )


def _loop_to_lines(lines: list[str], loop: list[tuple[float, float]], layer: str) -> None:
    for idx in range(len(loop)):
        x1, y1 = loop[idx]
        x2, y2 = loop[(idx + 1) % len(loop)]
        _add_line_entity(lines, x1, y1, x2, y2, layer)


def _write_dxf_approx(
    path: Path,
    sheet_w: float,
    sheet_h: float,
    part_defs: dict[str, dict[str, Any]],
    sheet_placements: list[dict[str, Any]],
) -> dict[str, Any]:
    ezdxf = _require_ezdxf()
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    used_parts = sorted({str(p["part_id"]) for p in sheet_placements})
    for part_id in used_parts:
        pdef = part_defs[part_id]
        block = _approx_block_name(part_id)
        if block not in doc.blocks:
            block_rec = doc.blocks.new(name=block, base_point=(0.0, 0.0, 0.0))
            source_entities = pdef.get("source_entities", [])
            if isinstance(source_entities, list) and source_entities:
                base_x, base_y = _source_entities_base_offset(source_entities)
                _add_source_entities_to_block(block_rec, source_entities, base_x, base_y)
            else:
                block_rec.add_lwpolyline(pdef["outer"], close=True, dxfattribs={"layer": "PART_OUTER"})
                for hole in pdef["holes"]:
                    block_rec.add_lwpolyline(hole, close=True, dxfattribs={"layer": "PART_HOLE"})

    msp.add_line((0.0, 0.0, 0.0), (sheet_w, 0.0, 0.0), dxfattribs={"layer": "SHEET"})
    msp.add_line((sheet_w, 0.0, 0.0), (sheet_w, sheet_h, 0.0), dxfattribs={"layer": "SHEET"})
    msp.add_line((sheet_w, sheet_h, 0.0), (0.0, sheet_h, 0.0), dxfattribs={"layer": "SHEET"})
    msp.add_line((0.0, sheet_h, 0.0), (0.0, 0.0, 0.0), dxfattribs={"layer": "SHEET"})

    for placement in sheet_placements:
        part_id = str(placement["part_id"])
        block = _approx_block_name(part_id)
        msp.add_blockref(
            block,
            (float(placement["x"]), float(placement["y"]), 0.0),
            dxfattribs={
                "layer": "PART_INSERT",
                "rotation": float(placement["rotation_deg"]),
            },
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(path)
    return {
        "export_mode": "block_insert",
        "used_part_blocks": sorted({_approx_block_name(str(p["part_id"])) for p in sheet_placements}),
    }


def _source_entities_base_offset(source_entities: list[dict[str, Any]]) -> tuple[float, float]:
    min_x: float | None = None
    min_y: float | None = None

    def _push(x: float, y: float) -> None:
        nonlocal min_x, min_y
        if min_x is None or x < min_x:
            min_x = x
        if min_y is None or y < min_y:
            min_y = y

    for entity in source_entities:
        if not isinstance(entity, dict):
            continue
        etype = str(entity.get("type", "")).upper().strip()
        if etype in {"LINE", "LWPOLYLINE", "POLYLINE", "SPLINE", "ELLIPSE"}:
            points = entity.get("points")
            if isinstance(points, list):
                for point in points:
                    if isinstance(point, (list, tuple)) and len(point) == 2:
                        x = point[0]
                        y = point[1]
                        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                            _push(float(x), float(y))
            continue
        if etype in {"ARC", "CIRCLE"}:
            center = entity.get("center")
            radius = entity.get("radius")
            if (
                isinstance(center, (list, tuple))
                and len(center) == 2
                and isinstance(center[0], (int, float))
                and isinstance(center[1], (int, float))
                and isinstance(radius, (int, float))
            ):
                cx = float(center[0])
                cy = float(center[1])
                r = float(radius)
                _push(cx - r, cy - r)
                _push(cx + r, cy + r)
            continue

    if min_x is None or min_y is None:
        return 0.0, 0.0
    return float(min_x), float(min_y)


def _validate_source_meta(part_id: str, entry: dict[str, Any], *, where: str) -> dict[str, Any]:
    source_dxf_path = str(entry.get("source_dxf_path", entry.get("source_path", ""))).strip()
    if not source_dxf_path:
        raise DxfExportError(f"missing source_dxf_path for part {part_id} at {where}")

    source_layers = entry.get("source_layers")
    if not isinstance(source_layers, dict):
        raise DxfExportError(f"missing source_layers for part {part_id} at {where}")
    outer = str(source_layers.get("outer", "")).strip()
    inner = str(source_layers.get("inner", "")).strip()
    if not outer or not inner:
        raise DxfExportError(f"invalid source_layers for part {part_id} at {where}")

    source_base_offset = entry.get("source_base_offset_mm", {"x": 0.0, "y": 0.0})
    if not isinstance(source_base_offset, dict):
        raise DxfExportError(f"invalid source_base_offset_mm for part {part_id} at {where}")
    base_x = source_base_offset.get("x", 0.0)
    base_y = source_base_offset.get("y", 0.0)
    if not isinstance(base_x, (int, float)) or not isinstance(base_y, (int, float)):
        raise DxfExportError(f"invalid source_base_offset_mm.x/y for part {part_id} at {where}")

    return {
        "part_id": part_id,
        "source_dxf_path": str(Path(source_dxf_path).resolve()),
        "source_layers": {"outer": outer, "inner": inner},
        "source_base_offset_mm": {"x": float(base_x), "y": float(base_y)},
    }


def _source_meta_from_input(input_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    parts = input_payload.get("parts")
    if not isinstance(parts, list):
        raise DxfExportError("input.parts must be list")

    out: dict[str, dict[str, Any]] = {}
    for idx, part in enumerate(parts):
        if not isinstance(part, dict):
            raise DxfExportError(f"input.parts[{idx}] must be object")
        part_id = str(part.get("id", "")).strip()
        if not part_id:
            continue

        source_dxf_path = str(part.get("source_dxf_path", part.get("source_path", ""))).strip()
        if not source_dxf_path:
            continue

        source_layers = part.get("source_layers")
        if not isinstance(source_layers, dict):
            raise DxfExportError(f"input.parts[{idx}].source_layers must be object for source geometry export")
        out[part_id] = _validate_source_meta(part_id, part, where=f"input.parts[{idx}]")

    return out


def _source_meta_from_map_file(source_map_path: Path) -> dict[str, dict[str, Any]]:
    payload = _read_json(source_map_path)
    parts = payload.get("parts")
    if not isinstance(parts, list):
        raise DxfExportError(f"source map must contain parts list: {source_map_path}")

    out: dict[str, dict[str, Any]] = {}
    for idx, part in enumerate(parts):
        if not isinstance(part, dict):
            raise DxfExportError(f"source map part entry must be object at parts[{idx}]")
        part_id = str(part.get("part_id", part.get("id", ""))).strip()
        if not part_id:
            raise DxfExportError(f"source map missing part_id at parts[{idx}]")
        out[part_id] = _validate_source_meta(part_id, part, where=f"source_geometry_map.parts[{idx}]")
    return out


def _load_source_geometry_map(run_dir: Path | None, input_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    fallback = _source_meta_from_input(input_payload)
    if run_dir is None:
        return fallback

    source_map_path = run_dir / "source_geometry_map.json"
    if not source_map_path.is_file():
        return fallback

    explicit = _source_meta_from_map_file(source_map_path)
    merged = dict(fallback)
    merged.update(explicit)
    return merged


def _entity_points(entity: dict[str, Any], *, where: str) -> list[tuple[float, float]]:
    points = entity.get("points")
    if not isinstance(points, list):
        raise DxfExportError(f"{where}.points must be list")

    out: list[tuple[float, float]] = []
    for idx, point in enumerate(points):
        out.append(_parse_point(point, f"{where}.points[{idx}]"))
    return out


def _require_ezdxf() -> Any:
    try:
        import ezdxf
    except ImportError as exc:
        raise DxfExportError("source geometry export requires 'ezdxf' dependency") from exc
    return ezdxf


def _add_source_entities_to_block(block: Any, source_entities: list[dict[str, Any]], base_x: float, base_y: float) -> None:
    unsupported_types: set[str] = set()

    for idx, entity in enumerate(source_entities):
        if not isinstance(entity, dict):
            raise DxfExportError(f"source_entities[{idx}] must be object")

        etype = str(entity.get("type", "")).upper().strip()
        layer = str(entity.get("layer", "PART_SRC")).strip() or "PART_SRC"
        where = f"source_entities[{idx}]"

        if etype == "LINE":
            points = _entity_points(entity, where=where)
            if len(points) < 2:
                continue
            for pidx in range(len(points) - 1):
                x1, y1 = points[pidx]
                x2, y2 = points[pidx + 1]
                block.add_line((x1 - base_x, y1 - base_y, 0.0), (x2 - base_x, y2 - base_y, 0.0), dxfattribs={"layer": layer})
            continue

        if etype in {"LWPOLYLINE", "POLYLINE"}:
            points = _entity_points(entity, where=where)
            if len(points) < 2:
                continue
            block.add_lwpolyline(
                [(x - base_x, y - base_y) for x, y in points],
                close=bool(entity.get("closed", False)),
                dxfattribs={"layer": layer},
            )
            continue

        if etype == "ARC":
            center_raw = entity.get("center")
            if not isinstance(center_raw, (list, tuple)) or len(center_raw) != 2:
                raise DxfExportError(f"{where}.center must be [x, y]")
            cx = float(center_raw[0]) - base_x
            cy = float(center_raw[1]) - base_y
            radius = entity.get("radius")
            start = entity.get("start_angle")
            end = entity.get("end_angle")
            if not isinstance(radius, (int, float)):
                raise DxfExportError(f"{where}.radius must be numeric")
            if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
                raise DxfExportError(f"{where}.start_angle/end_angle must be numeric")
            block.add_arc((cx, cy, 0.0), float(radius), float(start), float(end), dxfattribs={"layer": layer})
            continue

        if etype == "CIRCLE":
            center_raw = entity.get("center")
            if not isinstance(center_raw, (list, tuple)) or len(center_raw) != 2:
                raise DxfExportError(f"{where}.center must be [x, y]")
            cx = float(center_raw[0]) - base_x
            cy = float(center_raw[1]) - base_y
            radius = entity.get("radius")
            if not isinstance(radius, (int, float)):
                raise DxfExportError(f"{where}.radius must be numeric")
            block.add_circle((cx, cy, 0.0), float(radius), dxfattribs={"layer": layer})
            continue

        if etype == "SPLINE":
            points = _entity_points(entity, where=where)
            if len(points) < 2:
                continue
            spline = block.add_spline(
                fit_points=[(x - base_x, y - base_y, 0.0) for x, y in points],
                dxfattribs={"layer": layer},
            )
            if bool(entity.get("closed", False)):
                spline.dxf.flags = int(getattr(spline.dxf, "flags", 0)) | 1
            continue

        if etype == "ELLIPSE":
            center = entity.get("center")
            major_axis = entity.get("major_axis")
            ratio = entity.get("ratio")
            start_param = entity.get("start_param", 0.0)
            end_param = entity.get("end_param", math.tau)
            if (
                isinstance(center, (list, tuple))
                and len(center) == 2
                and isinstance(center[0], (int, float))
                and isinstance(center[1], (int, float))
                and isinstance(major_axis, (list, tuple))
                and len(major_axis) == 2
                and isinstance(major_axis[0], (int, float))
                and isinstance(major_axis[1], (int, float))
                and isinstance(ratio, (int, float))
                and float(ratio) > 0.0
                and isinstance(start_param, (int, float))
                and isinstance(end_param, (int, float))
            ):
                block.add_ellipse(
                    center=(float(center[0]) - base_x, float(center[1]) - base_y, 0.0),
                    major_axis=(float(major_axis[0]), float(major_axis[1]), 0.0),
                    ratio=float(ratio),
                    start_param=float(start_param),
                    end_param=float(end_param),
                    dxfattribs={"layer": layer},
                )
                continue

            points = _entity_points(entity, where=where)
            if len(points) < 2:
                continue
            block.add_lwpolyline(
                [(x - base_x, y - base_y) for x, y in points],
                close=bool(entity.get("closed", True)),
                dxfattribs={"layer": layer},
            )
            continue

        if etype:
            unsupported_types.add(etype)

    if unsupported_types:
        unsupported_sorted = ",".join(sorted(unsupported_types))
        print(f"WARN: skipped unsupported source entity types: {unsupported_sorted}", file=sys.stderr)


def _write_dxf_source(
    path: Path,
    sheet_w: float,
    sheet_h: float,
    source_meta_by_part: dict[str, dict[str, Any]],
    sheet_placements: list[dict[str, Any]],
    source_entity_cache: dict[tuple[str, str, str], list[dict[str, Any]]],
) -> dict[str, Any]:
    ezdxf = _require_ezdxf()
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    msp.add_line((0.0, 0.0, 0.0), (sheet_w, 0.0, 0.0), dxfattribs={"layer": "SHEET"})
    msp.add_line((sheet_w, 0.0, 0.0), (sheet_w, sheet_h, 0.0), dxfattribs={"layer": "SHEET"})
    msp.add_line((sheet_w, sheet_h, 0.0), (0.0, sheet_h, 0.0), dxfattribs={"layer": "SHEET"})
    msp.add_line((0.0, sheet_h, 0.0), (0.0, 0.0, 0.0), dxfattribs={"layer": "SHEET"})

    block_names: dict[str, str] = {}
    used_parts = sorted({str(p["part_id"]) for p in sheet_placements})
    for part_id in used_parts:
        if part_id not in source_meta_by_part:
            raise DxfExportError(f"missing source geometry mapping for part_id={part_id}")

        source_meta = source_meta_by_part[part_id]
        block_name = _source_block_name(part_id, source_meta)
        block_names[part_id] = block_name

        if block_name in doc.blocks:
            continue

        outer_layer = source_meta["source_layers"]["outer"]
        inner_layer = source_meta["source_layers"]["inner"]
        source_path = source_meta["source_dxf_path"]
        cache_key = (source_path, outer_layer, inner_layer)
        if cache_key not in source_entity_cache:
            part_raw = import_part_raw(source_path, outer_layer=outer_layer, inner_layer=inner_layer)
            source_entity_cache[cache_key] = list(part_raw.source_entities)

        block = doc.blocks.new(name=block_name, base_point=(0.0, 0.0, 0.0))
        base_x = float(source_meta["source_base_offset_mm"]["x"])
        base_y = float(source_meta["source_base_offset_mm"]["y"])
        _add_source_entities_to_block(block, source_entity_cache[cache_key], base_x, base_y)

    for placement in sheet_placements:
        part_id = str(placement["part_id"])
        msp.add_blockref(
            block_names[part_id],
            (float(placement["x"]), float(placement["y"]), 0.0),
            dxfattribs={
                "layer": "PART_INSERT",
                "rotation": float(placement["rotation_deg"]),
            },
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(path)
    return {
        "export_mode": "source_block_insert",
        "used_part_blocks": [block_names[part_id] for part_id in used_parts],
    }


def _looks_like_dxf_flow(input_payload: dict[str, Any], run_dir: Path | None) -> bool:
    if run_dir is not None and (run_dir / "source_geometry_map.json").is_file():
        return True

    parts = input_payload.get("parts")
    if not isinstance(parts, list):
        return False

    for part in parts:
        if not isinstance(part, dict):
            continue
        source_path = str(part.get("source_dxf_path", part.get("source_path", ""))).strip()
        source_layers = part.get("source_layers")
        if source_path and isinstance(source_layers, dict):
            return True
    return False


def _resolve_geometry_mode(
    requested_mode: str,
    *,
    run_dir: Path | None,
    input_payload: dict[str, Any],
    output_payload: dict[str, Any],
) -> str:
    mode = requested_mode.strip().lower()
    if mode not in {"approx", "source"}:
        raise DxfExportError(f"unsupported geometry mode: {requested_mode}")

    if run_dir is not None and mode == "approx":
        output_mode = str(output_payload.get("geometry_mode", "")).strip().lower()
        if output_mode in {"approx", "source"}:
            return output_mode
        if _looks_like_dxf_flow(input_payload, run_dir):
            return "source"

    return mode


def export_per_sheet(
    input_payload: dict[str, Any],
    output_payload: dict[str, Any],
    out_dir: str | Path,
    *,
    geometry_mode: str = "approx",
    run_dir: str | Path | None = None,
) -> dict[str, Any]:
    if output_payload.get("contract_version") != "v1":
        raise DxfExportError("output.contract_version must be v1")

    placements = output_payload.get("placements")
    if not isinstance(placements, list):
        raise DxfExportError("output.placements must be list")

    part_defs = _part_defs(input_payload)
    sheet_sizes = _sheet_sizes(input_payload)

    run_root = Path(run_dir).resolve() if run_dir else None
    effective_mode = _resolve_geometry_mode(
        geometry_mode,
        run_dir=run_root,
        input_payload=input_payload,
        output_payload=output_payload,
    )

    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for pidx, placement in enumerate(placements):
        if not isinstance(placement, dict):
            raise DxfExportError("placement entry must be object")

        part_id = str(placement.get("part_id", "")).strip()
        if part_id not in part_defs:
            raise DxfExportError(f"unknown part_id in placement: {part_id}")

        sheet_index = placement.get("sheet_index")
        if not isinstance(sheet_index, int) or sheet_index not in sheet_sizes:
            raise DxfExportError(f"invalid sheet_index: {sheet_index}")

        x = placement.get("x")
        y = placement.get("y")
        rot = placement.get("rotation_deg")
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise DxfExportError(f"placement[{pidx}] x/y must be numeric")
        if not isinstance(rot, (int, float)):
            raise DxfExportError(f"placement[{pidx}].rotation_deg must be numeric")

        rot_norm = int(rot) % 360
        if rot_norm not in part_defs[part_id]["allowed_rotations"]:
            raise DxfExportError(f"rotation {rot_norm} not allowed for part {part_id}")

        grouped[sheet_index].append(
            {
                "part_id": part_id,
                "x": float(x),
                "y": float(y),
                "rotation_deg": float(rot_norm),
            }
        )

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    source_meta_by_part = _load_source_geometry_map(run_root, input_payload) if effective_mode == "source" else {}
    source_entity_cache: dict[tuple[str, str, str], list[dict[str, Any]]] = {}

    exported_files: list[str] = []
    sheet_metrics: list[dict[str, Any]] = []

    for sheet_index in sorted(grouped):
        sheet_placements = grouped[sheet_index]
        if not sheet_placements:
            continue

        sheet_w, sheet_h = sheet_sizes[sheet_index]
        file_name = f"sheet_{sheet_index + 1:03d}.dxf"
        file_path = out_path / file_name

        if effective_mode == "source":
            source_metric = _write_dxf_source(
                file_path,
                sheet_w,
                sheet_h,
                source_meta_by_part,
                sheet_placements,
                source_entity_cache,
            )
            export_mode = source_metric["export_mode"]
            used_part_blocks = source_metric["used_part_blocks"]
        else:
            approx_metric = _write_dxf_approx(file_path, sheet_w, sheet_h, part_defs, sheet_placements)
            export_mode = approx_metric["export_mode"]
            used_part_blocks = approx_metric["used_part_blocks"]

        exported_files.append(str(file_path.resolve()))
        sheet_metrics.append(
            {
                "sheet_index": sheet_index,
                "file": str(file_path.resolve()),
                "stock_width": sheet_w,
                "stock_height": sheet_h,
                "placed_count": len(sheet_placements),
                "export_mode": export_mode,
                "used_part_blocks": used_part_blocks,
            }
        )

    summary = {
        "geometry_mode": effective_mode,
        "exported_count": len(exported_files),
        "exported_files": exported_files,
        "sheet_metrics": sheet_metrics,
    }
    return summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export table-solver placements into per-sheet DXF files")
    parser.add_argument("--run-dir", default="", help="Run directory containing solver_input.json/solver_output.json/out/")
    parser.add_argument("--input", default="", help="Path to solver_input.json")
    parser.add_argument("--output", default="", help="Path to solver_output.json")
    parser.add_argument("--out-dir", default="", help="Directory for generated sheet_XXX.dxf files")
    parser.add_argument("--summary-json", default="", help="Optional path to write export summary json")
    parser.add_argument("--geometry-mode", choices=["approx", "source"], default="approx", help="Geometry export mode (default: approx)")
    return parser


def _resolve_cli_paths(args: argparse.Namespace, parser: argparse.ArgumentParser) -> tuple[Path, Path, Path, Path | None]:
    run_dir_raw = str(args.run_dir or "").strip()
    input_raw = str(args.input or "").strip()
    output_raw = str(args.output or "").strip()
    out_dir_raw = str(args.out_dir or "").strip()

    if run_dir_raw:
        if input_raw or output_raw or out_dir_raw:
            parser.error("--run-dir cannot be used with --input/--output/--out-dir")
        run_dir = Path(run_dir_raw).resolve()
        return run_dir / "solver_input.json", run_dir / "solver_output.json", run_dir / "out", run_dir

    if not input_raw or not output_raw or not out_dir_raw:
        parser.error("either --run-dir or all of --input/--output/--out-dir must be provided")

    return Path(input_raw).resolve(), Path(output_raw).resolve(), Path(out_dir_raw).resolve(), None


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    input_path, output_path, out_dir, run_dir = _resolve_cli_paths(args, parser)

    try:
        input_payload = _read_json(input_path)
        output_payload = _read_json(output_path)
        summary = export_per_sheet(
            input_payload,
            output_payload,
            out_dir,
            geometry_mode=args.geometry_mode,
            run_dir=run_dir,
        )
    except DxfExportError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: unexpected exporter error: {exc}", file=sys.stderr)
        return 2

    if args.summary_json:
        summary_path = Path(args.summary_json).resolve()
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
