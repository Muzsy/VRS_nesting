#!/usr/bin/env python3
"""Iterative multi-sheet wrapper around Sparrow runner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from vrs_nesting.runner.sparrow_runner import SparrowRunnerError, run_sparrow_in_dir


class MultiSheetWrapperError(RuntimeError):
    """Raised when multi-sheet wrapper cannot make progress."""


def _sheet_sizes_from_solver_input(payload: dict[str, Any]) -> list[tuple[float, float]]:
    stocks = payload.get("stocks")
    if not isinstance(stocks, list) or not stocks:
        raise MultiSheetWrapperError("solver_input.stocks must be non-empty list")

    out: list[tuple[float, float]] = []
    for idx, stock in enumerate(stocks):
        if not isinstance(stock, dict):
            raise MultiSheetWrapperError(f"stock[{idx}] must be object")
        width = stock.get("width")
        height = stock.get("height")
        quantity = stock.get("quantity")
        if not isinstance(width, (int, float)) or width <= 0:
            raise MultiSheetWrapperError(f"stock[{idx}].width must be positive")
        if not isinstance(height, (int, float)) or height <= 0:
            raise MultiSheetWrapperError(f"stock[{idx}].height must be positive")
        if not isinstance(quantity, int) or quantity <= 0:
            raise MultiSheetWrapperError(f"stock[{idx}].quantity must be positive integer")
        for _ in range(quantity):
            out.append((float(width), float(height)))
    return out


def _build_source_geometry_map(solver_input: dict[str, Any]) -> dict[str, Any]:
    parts = solver_input.get("parts")
    if not isinstance(parts, list):
        raise MultiSheetWrapperError("solver_input.parts must be list")

    entries: list[dict[str, Any]] = []
    for idx, part in enumerate(parts):
        if not isinstance(part, dict):
            raise MultiSheetWrapperError(f"solver_input.parts[{idx}] must be object")

        part_id = str(part.get("id", "")).strip()
        source_dxf_path = str(part.get("source_dxf_path", part.get("source_path", ""))).strip()
        source_layers = part.get("source_layers")
        source_base_offset = part.get("source_base_offset_mm", {"x": 0.0, "y": 0.0})

        if not part_id:
            raise MultiSheetWrapperError(f"solver_input.parts[{idx}].id must be non-empty")
        if not source_dxf_path:
            continue
        if not isinstance(source_layers, dict):
            raise MultiSheetWrapperError(f"solver_input.parts[{idx}].source_layers must be object")
        outer_layer = str(source_layers.get("outer", "")).strip()
        inner_layer = str(source_layers.get("inner", "")).strip()
        if not outer_layer or not inner_layer:
            raise MultiSheetWrapperError(f"solver_input.parts[{idx}].source_layers must include outer+inner")
        if not isinstance(source_base_offset, dict):
            raise MultiSheetWrapperError(f"solver_input.parts[{idx}].source_base_offset_mm must be object")
        base_x = source_base_offset.get("x", 0.0)
        base_y = source_base_offset.get("y", 0.0)
        if not isinstance(base_x, (int, float)) or not isinstance(base_y, (int, float)):
            raise MultiSheetWrapperError(f"solver_input.parts[{idx}].source_base_offset_mm.x/y must be numeric")

        entries.append(
            {
                "part_id": part_id,
                "source_dxf_path": source_dxf_path,
                "source_layers": {"outer": outer_layer, "inner": inner_layer},
                "source_base_offset_mm": {"x": float(base_x), "y": float(base_y)},
            }
        )

    entries.sort(key=lambda entry: (str(entry.get("part_id", "")), str(entry.get("source_dxf_path", ""))))
    return {"contract_version": "v1", "parts": entries}


def _shape_bbox(shape: Any, *, where: str) -> tuple[float, float]:
    if not isinstance(shape, dict):
        raise MultiSheetWrapperError(f"{where}.shape must be object")
    if str(shape.get("type", "")).strip() != "simple_polygon":
        raise MultiSheetWrapperError(f"{where}.shape.type must be simple_polygon")

    data = shape.get("data")
    if not isinstance(data, list) or len(data) < 3:
        raise MultiSheetWrapperError(f"{where}.shape.data must be list with >=3 points")

    points: list[tuple[float, float]] = []
    for pidx, point in enumerate(data):
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise MultiSheetWrapperError(f"{where}.shape.data[{pidx}] must be [x,y]")
        x = point[0]
        y = point[1]
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise MultiSheetWrapperError(f"{where}.shape.data[{pidx}] coordinates must be numeric")
        points.append((float(x), float(y)))

    unique_points = {(x, y) for x, y in points}
    if len(unique_points) < 3:
        raise MultiSheetWrapperError(f"{where}.shape.data must have at least 3 unique points")

    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    width = float(max(xs) - min(xs))
    height = float(max(ys) - min(ys))
    if width <= 0 or height <= 0:
        raise MultiSheetWrapperError(f"{where}.shape bbox must be positive")
    return width, height


def _normalize_orientations(raw: Any) -> list[int]:
    if not isinstance(raw, list):
        return [0]

    out: list[int] = []
    seen: set[int] = set()
    for value in raw:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        rot = int(float(value)) % 360
        if rot not in (0, 90, 180, 270):
            continue
        if rot not in seen:
            seen.add(rot)
            out.append(rot)

    if not out:
        return [0]
    return out


def _fits_any_stock(width: float, height: float, orientations: list[int], stock_sheets: list[tuple[float, float]]) -> bool:
    for stock_w, stock_h in stock_sheets:
        for rot in orientations:
            if rot in (90, 270):
                w, h = height, width
            else:
                w, h = width, height
            if w <= stock_w and h <= stock_h:
                return True
    return False


def _remaining_sort_key(item: dict[str, Any]) -> tuple[str, str, int]:
    return (str(item.get("part_id", "")), str(item.get("instance_id", "")), int(item.get("item_id", 0)))


def _expand_remaining_items(sparrow_instance: dict[str, Any], stock_sheets: list[tuple[float, float]]) -> list[dict[str, Any]]:
    items = sparrow_instance.get("items")
    if not isinstance(items, list) or not items:
        raise MultiSheetWrapperError("sparrow_instance.items must be non-empty list")

    remaining: list[dict[str, Any]] = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise MultiSheetWrapperError("sparrow_instance.items entries must be objects")

        demand = int(item.get("demand", 1))
        if demand <= 0:
            continue

        item_id = item.get("id", 0)
        if not isinstance(item_id, int):
            raise MultiSheetWrapperError(f"sparrow_instance.items[{idx}].id must be int")

        part_id = str(item.get("part_id", item_id))
        allowed_orientations = _normalize_orientations(item.get("allowed_orientations", [0.0]))
        pre_reason: str | None = None
        bbox_w = 0.0
        bbox_h = 0.0

        try:
            bbox_w, bbox_h = _shape_bbox(item.get("shape"), where=f"sparrow_instance.items[{idx}]")
            if not _fits_any_stock(bbox_w, bbox_h, allowed_orientations, stock_sheets):
                pre_reason = "too_large"
        except MultiSheetWrapperError:
            pre_reason = "invalid_geometry"

        for rep in range(demand):
            if demand == 1:
                instance_id = str(item.get("instance_id", f"{part_id}__0001"))
            else:
                instance_id = f"{part_id}__{rep + 1:04d}"

            remaining.append(
                {
                    "item_id": item_id,
                    "part_id": part_id,
                    "instance_id": instance_id,
                    "allowed_orientations": allowed_orientations,
                    "shape": item.get("shape"),
                    "dxf": str(item.get("dxf", "")),
                    "pre_reason": pre_reason,
                    "bbox_width": bbox_w,
                    "bbox_height": bbox_h,
                }
            )

    remaining.sort(key=_remaining_sort_key)
    return remaining


def _allocate_sheet_budgets(time_limit_s: int, sheet_count: int) -> list[int]:
    if sheet_count <= 0 or time_limit_s <= 0:
        return []

    attempts = min(sheet_count, time_limit_s)
    base = time_limit_s // attempts
    rem = time_limit_s % attempts
    budgets: list[int] = []
    for idx in range(attempts):
        budget = base + (1 if idx < rem else 0)
        if budget <= 0:
            continue
        budgets.append(int(budget))
    return budgets


def _sheet_instance_payload(name: str, strip_height: float, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for idx, item in enumerate(candidates):
        items.append(
            {
                "id": idx,
                "demand": 1,
                "dxf": item["dxf"],
                "instance_id": item["instance_id"],
                "part_id": item["part_id"],
                "allowed_orientations": item["allowed_orientations"],
                "shape": item["shape"],
            }
        )
    return {"name": name, "strip_height": strip_height, "items": items}


def _parse_sheet_placements(final_json_path: Path) -> list[dict[str, Any]]:
    data = json.loads(final_json_path.read_text(encoding="utf-8"))
    solution = data.get("solution")
    layout = solution.get("layout") if isinstance(solution, dict) else None
    placed = layout.get("placed_items") if isinstance(layout, dict) else None
    if not isinstance(placed, list):
        return []

    out: list[dict[str, Any]] = []
    for item in placed:
        if not isinstance(item, dict):
            continue
        transform = item.get("transformation")
        if not isinstance(transform, dict):
            continue
        trans = transform.get("translation")
        rot = transform.get("rotation")
        if not isinstance(trans, list) or len(trans) != 2:
            continue
        if not isinstance(rot, (int, float)):
            continue
        out.append(
            {
                "item_id": int(item.get("item_id", -1)),
                "x": float(trans[0]),
                "y": float(trans[1]),
                "rotation_deg": float(rot),
            }
        )
    return out


def _unplaced_reason(item: dict[str, Any], *, timeout_hit: bool) -> str:
    pre_reason = item.get("pre_reason")
    if isinstance(pre_reason, str) and pre_reason:
        return pre_reason
    if timeout_hit:
        return "timeout"
    return "no_feasible_position"


def _stable_float(value: float) -> float:
    # Stabilize tiny floating noise from Sparrow output for deterministic JSON artifacts.
    rounded = float(round(float(value), 3))
    if abs(rounded) <= 1e-3:
        return 0.0
    return rounded


def run_multi_sheet_wrapper(
    *,
    run_dir: str | Path,
    sparrow_instance: dict[str, Any],
    solver_input: dict[str, Any],
    seed: int,
    time_limit_s: int,
    sparrow_bin: str | None = None,
) -> dict[str, Any]:
    root = Path(run_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    if not isinstance(time_limit_s, int):
        raise MultiSheetWrapperError("time_limit_s must be integer")

    stock_sheets = _sheet_sizes_from_solver_input(solver_input)
    remaining = _expand_remaining_items(sparrow_instance, stock_sheets)

    all_placements: list[dict[str, Any]] = []
    raw_outputs: list[dict[str, Any]] = []
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []

    budgets = _allocate_sheet_budgets(time_limit_s, len(stock_sheets))

    for sheet_index, budget in enumerate(budgets):
        if not remaining:
            break

        sheet_w, sheet_h = stock_sheets[sheet_index]
        candidates = [item for item in remaining if item.get("pre_reason") is None]
        candidates.sort(key=_remaining_sort_key)
        if not candidates:
            continue

        sheet_dir = root / "sheets" / f"sheet_{sheet_index + 1:03d}"
        sheet_dir.mkdir(parents=True, exist_ok=True)

        strip_height = max(float(sheet_w), float(sheet_h)) + 1.0
        sheet_instance = _sheet_instance_payload(
            f"{sparrow_instance.get('name', 'dxf')}_sheet_{sheet_index + 1:03d}",
            strip_height,
            candidates,
        )
        sheet_instance_path = sheet_dir / "instance_sheet.json"
        sheet_instance_path.write_text(json.dumps(sheet_instance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        try:
            _, meta = run_sparrow_in_dir(
                str(sheet_instance_path),
                run_dir=sheet_dir,
                seed=seed + sheet_index,
                time_limit=budget,
                sparrow_bin=sparrow_bin,
            )
        except SparrowRunnerError as exc:
            raise MultiSheetWrapperError(f"sparrow run failed on sheet_{sheet_index + 1:03d}: {exc}") from exc

        final_json_path = Path(str(meta.get("final_json_path", ""))).resolve()
        sheet_placements = _parse_sheet_placements(final_json_path)

        placed_instance_ids: set[str] = set()
        for placed in sheet_placements:
            item_idx = int(placed["item_id"])
            if item_idx < 0 or item_idx >= len(candidates):
                continue
            instance = candidates[item_idx]
            placed_instance_ids.add(instance["instance_id"])
            all_placements.append(
                {
                    "instance_id": instance["instance_id"],
                    "part_id": instance["part_id"],
                    "sheet_index": sheet_index,
                    "x": _stable_float(float(placed["x"])),
                    "y": _stable_float(float(placed["y"])),
                    "rotation_deg": _stable_float(float(placed["rotation_deg"])),
                }
            )

        runner_meta = dict(meta)
        runner_meta["time_limit_s"] = int(budget)
        raw_outputs.append(
            {
                "sheet_index": sheet_index,
                "sheet_dir": str(sheet_dir),
                "runner_meta": runner_meta,
                "placed_count": len(placed_instance_ids),
            }
        )

        stdout_path = sheet_dir / "sparrow_stdout.log"
        stderr_path = sheet_dir / "sparrow_stderr.log"
        if stdout_path.is_file():
            stdout_chunks.append(stdout_path.read_text(encoding="utf-8"))
        if stderr_path.is_file():
            stderr_chunks.append(stderr_path.read_text(encoding="utf-8"))

        if placed_instance_ids:
            remaining = [item for item in remaining if item["instance_id"] not in placed_instance_ids]
            remaining.sort(key=_remaining_sort_key)

    timeout_hit = bool(remaining and len(budgets) < len(stock_sheets))

    all_placements.sort(
        key=lambda placement: (
            int(placement.get("sheet_index", 0)),
            str(placement.get("part_id", "")),
            str(placement.get("instance_id", "")),
        )
    )

    unplaced = [
        {
            "instance_id": item["instance_id"],
            "part_id": item["part_id"],
            "reason": _unplaced_reason(item, timeout_hit=timeout_hit),
        }
        for item in remaining
    ]
    unplaced.sort(key=lambda item: (str(item.get("part_id", "")), str(item.get("instance_id", ""))))

    status = "ok" if not remaining else "partial"

    solver_output = {
        "contract_version": "v1",
        "status": status,
        "geometry_mode": "source",
        "placements": all_placements,
        "unplaced": unplaced,
    }

    source_geometry_map = _build_source_geometry_map(solver_input)

    (root / "sparrow_output.json").write_text(json.dumps(raw_outputs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (root / "solver_output.json").write_text(json.dumps(solver_output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (root / "source_geometry_map.json").write_text(json.dumps(source_geometry_map, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (root / "sparrow_stdout.log").write_text("\n".join(stdout_chunks), encoding="utf-8")
    (root / "sparrow_stderr.log").write_text("\n".join(stderr_chunks), encoding="utf-8")

    return solver_output
