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


def _expand_remaining_items(sparrow_instance: dict[str, Any]) -> list[dict[str, Any]]:
    items = sparrow_instance.get("items")
    if not isinstance(items, list) or not items:
        raise MultiSheetWrapperError("sparrow_instance.items must be non-empty list")

    remaining: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            raise MultiSheetWrapperError("sparrow_instance.items entries must be objects")
        demand = int(item.get("demand", 1))
        if demand <= 0:
            continue
        for rep in range(demand):
            if demand == 1:
                instance_id = str(item.get("instance_id", f"{item.get('part_id', 'part')}__0001"))
            else:
                base = str(item.get("part_id", item.get("id", "part")))
                instance_id = f"{base}__{rep + 1:04d}"
            remaining.append(
                {
                    "item_id": int(item.get("id", 0)),
                    "part_id": str(item.get("part_id", item.get("id", ""))),
                    "instance_id": instance_id,
                    "allowed_orientations": list(item.get("allowed_orientations", [0.0])),
                    "shape": item.get("shape"),
                    "dxf": str(item.get("dxf", "")),
                }
            )
    return remaining


def _sheet_instance_payload(name: str, strip_height: float, remaining: list[dict[str, Any]]) -> dict[str, Any]:
    items = []
    for idx, item in enumerate(remaining):
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

    stock_sheets = _sheet_sizes_from_solver_input(solver_input)
    remaining = _expand_remaining_items(sparrow_instance)

    all_placements: list[dict[str, Any]] = []
    raw_outputs: list[dict[str, Any]] = []
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []

    for sheet_index, (sheet_w, sheet_h) in enumerate(stock_sheets):
        if not remaining:
            break

        sheet_dir = root / "sheets" / f"sheet_{sheet_index + 1:03d}"
        sheet_dir.mkdir(parents=True, exist_ok=True)

        strip_height = max(float(sheet_w), float(sheet_h)) + 1.0
        sheet_instance = _sheet_instance_payload(
            f"{sparrow_instance.get('name', 'dxf')}_sheet_{sheet_index + 1:03d}",
            strip_height,
            remaining,
        )
        sheet_instance_path = sheet_dir / "instance_sheet.json"
        sheet_instance_path.write_text(json.dumps(sheet_instance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        try:
            _, meta = run_sparrow_in_dir(
                str(sheet_instance_path),
                run_dir=sheet_dir,
                seed=seed + sheet_index,
                time_limit=time_limit_s,
                sparrow_bin=sparrow_bin,
            )
        except SparrowRunnerError as exc:
            raise MultiSheetWrapperError(f"sparrow run failed on sheet_{sheet_index + 1:03d}: {exc}") from exc

        final_json_path = Path(str(meta.get("final_json_path", ""))).resolve()
        sheet_placements = _parse_sheet_placements(final_json_path)
        if not sheet_placements:
            break

        placed_instance_ids: set[str] = set()
        for placed in sheet_placements:
            item_idx = int(placed["item_id"])
            if item_idx < 0 or item_idx >= len(remaining):
                continue
            instance = remaining[item_idx]
            placed_instance_ids.add(instance["instance_id"])
            all_placements.append(
                {
                    "instance_id": instance["instance_id"],
                    "part_id": instance["part_id"],
                    "sheet_index": sheet_index,
                    "x": placed["x"],
                    "y": placed["y"],
                    "rotation_deg": placed["rotation_deg"],
                }
            )

        raw_outputs.append(
            {
                "sheet_index": sheet_index,
                "sheet_dir": str(sheet_dir),
                "runner_meta": meta,
                "placed_count": len(placed_instance_ids),
            }
        )

        stdout_path = sheet_dir / "sparrow_stdout.log"
        stderr_path = sheet_dir / "sparrow_stderr.log"
        if stdout_path.is_file():
            stdout_chunks.append(stdout_path.read_text(encoding="utf-8"))
        if stderr_path.is_file():
            stderr_chunks.append(stderr_path.read_text(encoding="utf-8"))

        if not placed_instance_ids:
            break
        remaining = [item for item in remaining if item["instance_id"] not in placed_instance_ids]

    if all_placements and not remaining:
        status = "ok"
    elif all_placements and remaining:
        status = "partial"
    else:
        raise MultiSheetWrapperError("MULTISHEET_NO_PROGRESS: Sparrow placed no instances")

    unplaced = [{"instance_id": item["instance_id"], "part_id": item["part_id"], "reason": "NO_STOCK_LEFT"} for item in remaining]

    solver_output = {
        "contract_version": "v1",
        "status": status,
        "placements": all_placements,
        "unplaced": unplaced,
    }

    (root / "sparrow_output.json").write_text(json.dumps(raw_outputs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (root / "solver_output.json").write_text(json.dumps(solver_output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (root / "sparrow_stdout.log").write_text("\n".join(stdout_chunks), encoding="utf-8")
    (root / "sparrow_stderr.log").write_text("\n".join(stderr_chunks), encoding="utf-8")

    return solver_output
