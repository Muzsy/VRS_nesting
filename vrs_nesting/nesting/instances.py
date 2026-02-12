#!/usr/bin/env python3
"""Instance expansion and multi-sheet placement validation helpers."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


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


def _build_sheet_sizes(payload: dict[str, Any]) -> dict[int, tuple[float, float]]:
    stocks = payload.get("stocks")
    if not isinstance(stocks, list):
        raise ValueError("stocks must be a list")

    sheet_sizes: dict[int, tuple[float, float]] = {}
    sheet_index = 0
    for stock in stocks:
        if not isinstance(stock, dict):
            raise ValueError("stock must be object")
        width = stock.get("width")
        height = stock.get("height")
        qty = stock.get("quantity")
        if not isinstance(width, (int, float)) or width <= 0:
            raise ValueError("stock.width must be > 0")
        if not isinstance(height, (int, float)) or height <= 0:
            raise ValueError("stock.height must be > 0")
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError("stock.quantity must be > 0")

        for _ in range(qty):
            sheet_sizes[sheet_index] = (float(width), float(height))
            sheet_index += 1

    return sheet_sizes


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
    return ax1 < bx2 and bx1 < ax2 and ay1 < by2 and by1 < ay2


def validate_multi_sheet_output(input_payload: dict[str, Any], output_payload: dict[str, Any]) -> None:
    if output_payload.get("contract_version") != "v1":
        raise ValueError("output.contract_version must be v1")

    placements = output_payload.get("placements")
    unplaced = output_payload.get("unplaced")
    if not isinstance(placements, list):
        raise ValueError("output.placements must be list")
    if not isinstance(unplaced, list):
        raise ValueError("output.unplaced must be list")

    sheet_sizes = _build_sheet_sizes(input_payload)
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
        if not isinstance(sheet_index, int) or sheet_index not in sheet_sizes:
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

        sw, sh = sheet_sizes[sheet_index]
        x1 = float(x)
        y1 = float(y)
        x2 = x1 + w
        y2 = y1 + h

        if x1 < 0 or y1 < 0 or x2 > sw or y2 > sh:
            raise ValueError(f"placement out of bounds: {instance_id}")

        rect = (x1, y1, x2, y2)
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
            for sw, sh in sheet_sizes.values():
                if bw <= sw and bh <= sh:
                    fits_any = True
                if allow_rot and bh <= sw and bw <= sh:
                    fits_any = True
            if fits_any:
                raise ValueError(f"invalid PART_NEVER_FITS_STOCK reason for part {part_id}")

    for part_id, expected in expected_counts.items():
        if seen_counts[part_id] != expected:
            raise ValueError(
                f"coverage mismatch for part {part_id}: expected {expected}, got {seen_counts[part_id]}"
            )
