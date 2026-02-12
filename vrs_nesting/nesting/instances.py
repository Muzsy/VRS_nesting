#!/usr/bin/env python3
"""Instance expansion and multi-sheet placement validation helpers."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


EPS = 1e-9


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
            holes.append(_parse_polygon(hole, f"{where}.holes_points[{hole_idx}]"))

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

        for _ in range(qty):
            sheet_shapes[sheet_index] = {
                "stock_id": stock_id,
                "outer": outer,
                "holes": holes,
                "bbox_w": bbox_w,
                "bbox_h": bbox_h,
            }
            sheet_index += 1

    return sheet_shapes


def _part_dims(payload: dict[str, Any]) -> dict[str, tuple[float, float, bool]]:
    parts = payload.get("parts")
    if not isinstance(parts, list):
        raise ValueError("parts must be list")

    out: dict[str, tuple[float, float, bool]] = {}
    for part in parts:
        if not isinstance(part, dict):
            raise ValueError("part must be object")
        part_id = str(part.get("id", "")).strip()
        width = part.get("width")
        height = part.get("height")
        allow_rotation = bool(part.get("allow_rotation", False))
        if not part_id:
            raise ValueError("part.id must be non-empty")
        if not isinstance(width, (int, float)) or width <= 0:
            raise ValueError(f"part.width invalid for {part_id}")
        if not isinstance(height, (int, float)) or height <= 0:
            raise ValueError(f"part.height invalid for {part_id}")
        out[part_id] = (float(width), float(height), allow_rotation)

    return out


def _rect_overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return ax1 < bx2 - EPS and bx1 < ax2 - EPS and ay1 < by2 - EPS and by1 < ay2 - EPS


def _point_on_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> bool:
    cross = (py - ay) * (bx - ax) - (px - ax) * (by - ay)
    if abs(cross) > EPS:
        return False
    dot = (px - ax) * (px - bx) + (py - ay) * (py - by)
    return dot <= EPS


def _point_in_polygon(pt: tuple[float, float], poly: list[tuple[float, float]]) -> bool:
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if _point_on_segment(x, y, x1, y1, x2, y2):
            return True
        intersects = ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / ((y2 - y1) + EPS) + x1)
        if intersects:
            inside = not inside
    return inside


def _orientation(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _segments_intersect(a1: tuple[float, float], a2: tuple[float, float], b1: tuple[float, float], b2: tuple[float, float]) -> bool:
    o1 = _orientation(a1, a2, b1)
    o2 = _orientation(a1, a2, b2)
    o3 = _orientation(b1, b2, a1)
    o4 = _orientation(b1, b2, a2)

    if (o1 > EPS and o2 < -EPS or o1 < -EPS and o2 > EPS) and (o3 > EPS and o4 < -EPS or o3 < -EPS and o4 > EPS):
        return True

    if abs(o1) <= EPS and _point_on_segment(b1[0], b1[1], a1[0], a1[1], a2[0], a2[1]):
        return True
    if abs(o2) <= EPS and _point_on_segment(b2[0], b2[1], a1[0], a1[1], a2[0], a2[1]):
        return True
    if abs(o3) <= EPS and _point_on_segment(a1[0], a1[1], b1[0], b1[1], b2[0], b2[1]):
        return True
    if abs(o4) <= EPS and _point_on_segment(a2[0], a2[1], b1[0], b1[1], b2[0], b2[1]):
        return True

    return False


def _polygon_edges(poly: list[tuple[float, float]]) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    return [(poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly))]


def _rect_edges(rect: tuple[float, float, float, float]) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    x1, y1, x2, y2 = rect
    return [
        ((x1, y1), (x2, y1)),
        ((x2, y1), (x2, y2)),
        ((x2, y2), (x1, y2)),
        ((x1, y2), (x1, y1)),
    ]


def _rect_shape_feasible(rect: tuple[float, float, float, float], outer: list[tuple[float, float]], holes: list[list[tuple[float, float]]]) -> bool:
    x1, y1, x2, y2 = rect
    corners = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]

    for c in corners:
        if not _point_in_polygon(c, outer):
            return False

    rect_edges = _rect_edges(rect)
    for hole in holes:
        for c in corners:
            if _point_in_polygon(c, hole):
                return False
        for re in rect_edges:
            for he in _polygon_edges(hole):
                if _segments_intersect(re[0], re[1], he[0], he[1]):
                    return False

    return True


def validate_multi_sheet_output(input_payload: dict[str, Any], output_payload: dict[str, Any]) -> None:
    if output_payload.get("contract_version") != "v1":
        raise ValueError("output.contract_version must be v1")

    placements = output_payload.get("placements")
    unplaced = output_payload.get("unplaced")
    if not isinstance(placements, list):
        raise ValueError("output.placements must be list")
    if not isinstance(unplaced, list):
        raise ValueError("output.unplaced must be list")

    sheet_shapes = _build_sheet_shapes(input_payload)
    part_dims = _part_dims(input_payload)

    expected_counts: Counter[str] = Counter()
    for part in input_payload.get("parts", []):
        expected_counts[str(part["id"])] += int(part["quantity"])

    seen_instance_ids: set[str] = set()
    seen_counts: Counter[str] = Counter()
    sheet_rects: dict[int, list[tuple[float, float, float, float]]] = defaultdict(list)

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

        if part_id not in part_dims:
            raise ValueError(f"unknown part_id in placement: {part_id}")
        if not isinstance(sheet_index, int) or sheet_index not in sheet_shapes:
            raise ValueError(f"invalid sheet_index: {sheet_index}")
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise ValueError("placement x/y must be number")
        if not isinstance(rot, (int, float)):
            raise ValueError("placement.rotation_deg must be number")

        base_w, base_h, allow_rotation = part_dims[part_id]
        rot_norm = int(rot) % 360
        if rot_norm in (0, 180):
            w, h = base_w, base_h
        elif rot_norm in (90, 270):
            if not allow_rotation:
                raise ValueError(f"rotation not allowed for part {part_id}")
            w, h = base_h, base_w
        else:
            raise ValueError(f"unsupported rotation_deg: {rot}")

        x1 = float(x)
        y1 = float(y)
        x2 = x1 + w
        y2 = y1 + h
        rect = (x1, y1, x2, y2)

        sheet = sheet_shapes[sheet_index]
        if not _rect_shape_feasible(rect, sheet["outer"], sheet["holes"]):
            raise ValueError(f"placement out of stock shape or intersects hole: {instance_id}")

        for prev in sheet_rects[sheet_index]:
            if _rect_overlap(prev, rect):
                raise ValueError(f"overlap detected on sheet {sheet_index} for {instance_id}")
        sheet_rects[sheet_index].append(rect)

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
            bw, bh, allow_rot = part_dims.get(part_id, (None, None, None))
            if bw is None:
                raise ValueError(f"unknown part in unplaced: {part_id}")
            fits_any = False
            for sheet in sheet_shapes.values():
                if bw <= sheet["bbox_w"] and bh <= sheet["bbox_h"]:
                    fits_any = True
                if allow_rot and bh <= sheet["bbox_w"] and bw <= sheet["bbox_h"]:
                    fits_any = True
            if fits_any:
                raise ValueError(f"invalid PART_NEVER_FITS_STOCK reason for part {part_id}")

    for part_id, expected in expected_counts.items():
        if seen_counts[part_id] != expected:
            raise ValueError(
                f"coverage mismatch for part {part_id}: expected {expected}, got {seen_counts[part_id]}"
            )
