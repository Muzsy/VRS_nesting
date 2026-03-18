#!/usr/bin/env python3
"""Instance expansion and multi-sheet placement validation helpers."""

from __future__ import annotations

from collections import Counter, defaultdict
import math
from typing import Any

try:
    from shapely.affinity import rotate as shp_rotate
    from shapely.affinity import translate as shp_translate
    from shapely.geometry import Polygon
except ImportError:  # pragma: no cover
    Polygon = None
    shp_rotate = None
    shp_translate = None


EPS = 1e-9
AREA_EPS = 1e-9


def expand_part_instances(payload: dict[str, Any]) -> list[dict[str, Any]]:
    parts = payload.get("parts")
    if not isinstance(parts, list):
        raise ValueError("parts must be a list")

    instances: list[dict[str, Any]] = []
    for part in parts:
        if not isinstance(part, dict):
            raise ValueError("part must be object")
        part_id = str(part.get("id", "")).strip()
        qty = part.get("quantity")
        if not part_id:
            raise ValueError("part.id must be non-empty")
        if not isinstance(qty, int) or qty < 1:
            raise ValueError(f"part.quantity must be positive int for part {part_id}")

        for idx in range(1, qty + 1):
            instances.append({"instance_id": f"{part_id}__{idx:04d}", "part_id": part_id})

    return instances


def _require_shapely() -> None:
    if Polygon is None or shp_rotate is None or shp_translate is None:
        raise ValueError("shapely is required for geometry validation")


def _parse_point(raw: Any, where: str) -> tuple[float, float]:
    if isinstance(raw, (list, tuple)) and len(raw) == 2:
        x, y = raw
    elif isinstance(raw, dict) and "x" in raw and "y" in raw:
        x, y = raw["x"], raw["y"]
    else:
        raise ValueError(f"invalid point format at {where}")

    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        raise ValueError(f"point coordinates must be numeric at {where}")
    return float(x), float(y)


def _parse_polygon(raw: Any, where: str) -> list[tuple[float, float]]:
    if not isinstance(raw, list):
        raise ValueError(f"polygon must be list at {where}")
    pts = [_parse_point(pt, f"{where}[{idx}]") for idx, pt in enumerate(raw)]
    if len(pts) < 3:
        raise ValueError(f"polygon must have >=3 points at {where}")
    return pts


def _normalize_loops(outer: list[tuple[float, float]], holes: list[list[tuple[float, float]]]) -> tuple[list[tuple[float, float]], list[list[tuple[float, float]]]]:
    all_points = list(outer)
    for hole in holes:
        all_points.extend(hole)

    min_x = min(p[0] for p in all_points)
    min_y = min(p[1] for p in all_points)

    def _shift(loop: list[tuple[float, float]]) -> list[tuple[float, float]]:
        return [(float(x - min_x), float(y - min_y)) for x, y in loop]

    return _shift(outer), [_shift(hole) for hole in holes]


def _as_polygon(outer: list[tuple[float, float]], holes: list[list[tuple[float, float]]], where: str) -> Any:
    _require_shapely()
    poly = Polygon(outer, holes)
    if poly.is_empty or poly.area <= 0 or not poly.is_valid:
        raise ValueError(f"invalid polygon at {where}")
    return poly


def _stock_outer_and_holes(stock: dict[str, Any], where: str) -> tuple[list[tuple[float, float]], list[list[tuple[float, float]]], float, float]:
    width = stock.get("width")
    height = stock.get("height")

    if "outer_points" in stock and stock["outer_points"] is not None:
        outer = _parse_polygon(stock["outer_points"], f"{where}.outer_points")
    else:
        if not isinstance(width, (int, float)) or width <= 0:
            raise ValueError(f"{where}.width must be > 0 when outer_points is not provided")
        if not isinstance(height, (int, float)) or height <= 0:
            raise ValueError(f"{where}.height must be > 0 when outer_points is not provided")
        w = float(width)
        h = float(height)
        outer = [(0.0, 0.0), (w, 0.0), (w, h), (0.0, h)]

    holes_raw = stock.get("holes_points", [])
    holes: list[list[tuple[float, float]]] = []
    if holes_raw is not None:
        if not isinstance(holes_raw, list):
            raise ValueError(f"{where}.holes_points must be list")
        for hole_idx, hole in enumerate(holes_raw):
            holes.append(_parse_polygon(hole, f"{where}.holes_points[{hole_idx}]") )

    min_x = min(p[0] for p in outer)
    max_x = max(p[0] for p in outer)
    min_y = min(p[1] for p in outer)
    max_y = max(p[1] for p in outer)

    bbox_w = max_x - min_x
    bbox_h = max_y - min_y
    if bbox_w <= 0 or bbox_h <= 0:
        raise ValueError(f"{where} outer polygon has invalid bbox")

    return outer, holes, bbox_w, bbox_h


def _build_sheet_shapes(payload: dict[str, Any]) -> dict[int, dict[str, Any]]:
    stocks = payload.get("stocks")
    if not isinstance(stocks, list):
        raise ValueError("stocks must be a list")

    sheet_shapes: dict[int, dict[str, Any]] = {}
    sheet_index = 0
    for idx, stock in enumerate(stocks):
        if not isinstance(stock, dict):
            raise ValueError("stock must be object")
        qty = stock.get("quantity")
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError("stock.quantity must be > 0")

        outer, holes, bbox_w, bbox_h = _stock_outer_and_holes(stock, f"stocks[{idx}]")
        stock_id = str(stock.get("id", "")).strip() or f"stock_{idx}"
        stock_poly = _as_polygon(outer, holes, f"stocks[{idx}]")

        for _ in range(qty):
            sheet_shapes[sheet_index] = {
                "stock_id": stock_id,
                "polygon": stock_poly,
                "bbox_w": float(bbox_w),
                "bbox_h": float(bbox_h),
            }
            sheet_index += 1

    return sheet_shapes


def _normalize_allowed_rotations(part: dict[str, Any], where: str) -> list[int]:
    raw = part.get("allowed_rotations_deg", [0])
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"{where}.allowed_rotations_deg must be non-empty list")

    out: list[int] = []
    seen: set[int] = set()
    for idx, value in enumerate(raw):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{where}.allowed_rotations_deg[{idx}] must be integer")
        rot = value % 360
        if rot not in (0, 90, 180, 270):
            raise ValueError(f"{where}.allowed_rotations_deg[{idx}] must be one of 0,90,180,270")
        if rot not in seen:
            seen.add(rot)
            out.append(rot)
    return out


def _part_geometries(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    parts = payload.get("parts")
    if not isinstance(parts, list):
        raise ValueError("parts must be list")

    out: dict[str, dict[str, Any]] = {}
    for idx, part in enumerate(parts):
        if not isinstance(part, dict):
            raise ValueError("part must be object")

        part_id = str(part.get("id", "")).strip()
        if not part_id:
            raise ValueError("part.id must be non-empty")

        width = part.get("width")
        height = part.get("height")
        if not isinstance(width, (int, float)) or width <= 0:
            raise ValueError(f"part.width invalid for {part_id}")
        if not isinstance(height, (int, float)) or height <= 0:
            raise ValueError(f"part.height invalid for {part_id}")

        allowed_rotations = _normalize_allowed_rotations(part, f"parts[{idx}]")

        outer_raw = part.get("prepared_outer_points", part.get("outer_points"))
        holes_raw = part.get("prepared_holes_points", part.get("holes_points", []))

        if outer_raw is None:
            outer = [(0.0, 0.0), (float(width), 0.0), (float(width), float(height)), (0.0, float(height))]
            holes: list[list[tuple[float, float]]] = []
        else:
            outer = _parse_polygon(outer_raw, f"parts[{idx}].outer_points")
            holes = []
            if holes_raw is not None:
                if not isinstance(holes_raw, list):
                    raise ValueError(f"parts[{idx}].holes_points must be list")
                for hidx, hole in enumerate(holes_raw):
                    holes.append(_parse_polygon(hole, f"parts[{idx}].holes_points[{hidx}]"))

        outer, holes = _normalize_loops(outer, holes)
        poly = _as_polygon(outer, holes, f"parts[{idx}]")
        min_x, min_y, max_x, max_y = poly.bounds

        out[part_id] = {
            "allowed_rotations": allowed_rotations,
            "polygon": poly,
            "bbox_w": float(max_x - min_x),
            "bbox_h": float(max_y - min_y),
        }

    return out


def _parse_clearance(payload: dict[str, Any], key: str) -> float:
    value = payload.get(key, 0.0)
    if not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be number")
    if float(value) < 0:
        raise ValueError(f"{key} must be >= 0")
    return float(value)


def _placement_polygon(base_poly: Any, *, x: float, y: float, rotation_deg: int) -> Any:
    _require_shapely()
    rotated = shp_rotate(base_poly, float(rotation_deg), origin=(0.0, 0.0), use_radians=False)
    return shp_translate(rotated, xoff=float(x), yoff=float(y))


def validate_multi_sheet_output(input_payload: dict[str, Any], output_payload: dict[str, Any]) -> None:
    if output_payload.get("contract_version") != "v1":
        raise ValueError("output.contract_version must be v1")

    status = output_payload.get("status")
    if not isinstance(status, str) or status not in {"ok", "partial"}:
        raise ValueError("output.status must be ok or partial")

    placements = output_payload.get("placements")
    unplaced = output_payload.get("unplaced")
    if not isinstance(placements, list):
        raise ValueError("output.placements must be list")
    if not isinstance(unplaced, list):
        raise ValueError("output.unplaced must be list")

    spacing_mm = _parse_clearance(input_payload, "spacing_mm")
    margin_mm = _parse_clearance(input_payload, "margin_mm")

    sheet_shapes = _build_sheet_shapes(input_payload)
    part_geoms = _part_geometries(input_payload)

    sheet_margin_usable: dict[int, Any] = {}
    if margin_mm > 0:
        for sidx, sheet in sheet_shapes.items():
            usable = sheet["polygon"].buffer(-margin_mm, join_style=2)
            sheet_margin_usable[sidx] = usable

    expected_counts: Counter[str] = Counter()
    for part in input_payload.get("parts", []):
        expected_counts[str(part["id"])] += int(part["quantity"])

    seen_instance_ids: set[str] = set()
    seen_counts: Counter[str] = Counter()
    sheet_polys: dict[int, list[Any]] = defaultdict(list)

    for placement in placements:
        if not isinstance(placement, dict):
            raise ValueError("placement must be object")
        instance_id = str(placement.get("instance_id", "")).strip()
        part_id = str(placement.get("part_id", "")).strip()
        sheet_index = placement.get("sheet_index")
        x = placement.get("x")
        y = placement.get("y")
        rot = placement.get("rotation_deg")

        if not instance_id or not part_id:
            raise ValueError("placement.instance_id and placement.part_id are required")
        if instance_id in seen_instance_ids:
            raise ValueError(f"duplicate instance_id: {instance_id}")
        seen_instance_ids.add(instance_id)

        if part_id not in part_geoms:
            raise ValueError(f"unknown part_id in placement: {part_id}")
        if not isinstance(sheet_index, int) or sheet_index not in sheet_shapes:
            raise ValueError(f"invalid sheet_index: {sheet_index}")
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise ValueError("placement x/y must be number")
        if not isinstance(rot, (int, float)):
            raise ValueError("placement.rotation_deg must be number")
        if not math.isfinite(float(rot)):
            raise ValueError("placement.rotation_deg must be finite")

        rot_norm = int(round(float(rot))) % 360
        allowed_rotations = part_geoms[part_id]["allowed_rotations"]
        if rot_norm not in allowed_rotations:
            raise ValueError(f"rotation {rot_norm} not allowed for part {part_id}")

        poly = _placement_polygon(part_geoms[part_id]["polygon"], x=float(x), y=float(y), rotation_deg=rot_norm)
        sheet_poly = sheet_shapes[sheet_index]["polygon"]

        if not sheet_poly.covers(poly):
            raise ValueError(f"placement out of stock shape or intersects hole: {instance_id}")

        if margin_mm > 0:
            usable = sheet_margin_usable[sheet_index]
            if usable.is_empty or not usable.covers(poly):
                raise ValueError(f"margin violation on sheet {sheet_index} for {instance_id}")

        for prev in sheet_polys[sheet_index]:
            if prev.intersection(poly).area > AREA_EPS:
                raise ValueError(f"overlap detected on sheet {sheet_index} for {instance_id}")
            if spacing_mm > 0 and prev.distance(poly) < spacing_mm - EPS:
                raise ValueError(f"spacing violation on sheet {sheet_index} for {instance_id}")
        sheet_polys[sheet_index].append(poly)

        seen_counts[part_id] += 1

    for item in unplaced:
        if not isinstance(item, dict):
            raise ValueError("unplaced item must be object")
        instance_id = str(item.get("instance_id", "")).strip()
        part_id = str(item.get("part_id", "")).strip()
        reason = str(item.get("reason", "")).strip()
        if not instance_id or not part_id or not reason:
            raise ValueError("unplaced requires instance_id, part_id, reason")
        if instance_id in seen_instance_ids:
            raise ValueError(f"duplicate instance_id across placed/unplaced: {instance_id}")
        seen_instance_ids.add(instance_id)
        seen_counts[part_id] += 1

        if reason == "PART_NEVER_FITS_STOCK":
            if part_id not in part_geoms:
                raise ValueError(f"unknown part in unplaced: {part_id}")
            part_w = part_geoms[part_id]["bbox_w"]
            part_h = part_geoms[part_id]["bbox_h"]
            allowed_rot = part_geoms[part_id]["allowed_rotations"]
            fits_any = False
            for sheet in sheet_shapes.values():
                usable_w = sheet["bbox_w"] - (2.0 * margin_mm)
                usable_h = sheet["bbox_h"] - (2.0 * margin_mm)
                if usable_w <= 0 or usable_h <= 0:
                    continue
                for rotation in allowed_rot:
                    if rotation in (90, 270):
                        rw, rh = part_h, part_w
                    else:
                        rw, rh = part_w, part_h
                    if rw <= usable_w + EPS and rh <= usable_h + EPS:
                        fits_any = True
            if fits_any:
                raise ValueError(f"invalid PART_NEVER_FITS_STOCK reason for part {part_id}")

    for part_id, expected in expected_counts.items():
        if seen_counts[part_id] != expected:
            raise ValueError(
                f"coverage mismatch for part {part_id}: expected {expected}, got {seen_counts[part_id]}"
            )
