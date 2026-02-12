#!/usr/bin/env python3
"""MVP per-sheet DXF exporter for table-solver placements."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


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


def _part_dims(input_payload: dict[str, Any]) -> dict[str, tuple[float, float, bool]]:
    parts = input_payload.get("parts")
    if not isinstance(parts, list):
        raise DxfExportError("input.parts must be a list")

    out: dict[str, tuple[float, float, bool]] = {}
    for part in parts:
        if not isinstance(part, dict):
            raise DxfExportError("part entry must be object")
        part_id = str(part.get("id", "")).strip()
        width = part.get("width")
        height = part.get("height")
        allow_rotation = bool(part.get("allow_rotation", False))
        if not part_id:
            raise DxfExportError("part.id must be non-empty")
        if not isinstance(width, (int, float)) or width <= 0:
            raise DxfExportError(f"invalid width for part {part_id}")
        if not isinstance(height, (int, float)) or height <= 0:
            raise DxfExportError(f"invalid height for part {part_id}")
        out[part_id] = (float(width), float(height), allow_rotation)

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


def _placement_rect(placement: dict[str, Any], dims: dict[str, tuple[float, float, bool]]) -> tuple[float, float, float, float]:
    part_id = str(placement.get("part_id", "")).strip()
    if part_id not in dims:
        raise DxfExportError(f"unknown part_id in placement: {part_id}")

    x = placement.get("x")
    y = placement.get("y")
    rot = placement.get("rotation_deg")
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        raise DxfExportError("placement x/y must be numeric")
    if not isinstance(rot, (int, float)):
        raise DxfExportError("placement.rotation_deg must be numeric")

    base_w, base_h, allow_rotation = dims[part_id]
    rot_norm = int(rot) % 360
    if rot_norm in (0, 180):
        w, h = base_w, base_h
    elif rot_norm in (90, 270):
        if not allow_rotation:
            raise DxfExportError(f"rotation not allowed for part {part_id}")
        w, h = base_h, base_w
    else:
        raise DxfExportError(f"unsupported rotation_deg: {rot}")

    x1 = float(x)
    y1 = float(y)
    return x1, y1, x1 + w, y1 + h


def _write_dxf(path: Path, sheet_w: float, sheet_h: float, part_rects: list[tuple[float, float, float, float]]) -> None:
    lines: list[str] = [
        "0", "SECTION", "2", "HEADER", "0", "ENDSEC",
        "0", "SECTION", "2", "ENTITIES",
    ]

    def add_line(x1: float, y1: float, x2: float, y2: float, layer: str) -> None:
        lines.extend(
            [
                "0", "LINE",
                "8", layer,
                "10", f"{x1:.6f}",
                "20", f"{y1:.6f}",
                "30", "0.0",
                "11", f"{x2:.6f}",
                "21", f"{y2:.6f}",
                "31", "0.0",
            ]
        )

    # Sheet boundary.
    add_line(0.0, 0.0, sheet_w, 0.0, "STOCK")
    add_line(sheet_w, 0.0, sheet_w, sheet_h, "STOCK")
    add_line(sheet_w, sheet_h, 0.0, sheet_h, "STOCK")
    add_line(0.0, sheet_h, 0.0, 0.0, "STOCK")

    for (x1, y1, x2, y2) in part_rects:
        add_line(x1, y1, x2, y1, "PART")
        add_line(x2, y1, x2, y2, "PART")
        add_line(x2, y2, x1, y2, "PART")
        add_line(x1, y2, x1, y1, "PART")

    lines.extend(["0", "ENDSEC", "0", "EOF"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def export_per_sheet(input_payload: dict[str, Any], output_payload: dict[str, Any], out_dir: str | Path) -> dict[str, Any]:
    if output_payload.get("contract_version") != "v1":
        raise DxfExportError("output.contract_version must be v1")

    placements = output_payload.get("placements")
    if not isinstance(placements, list):
        raise DxfExportError("output.placements must be list")

    dims = _part_dims(input_payload)
    sheet_sizes = _sheet_sizes(input_payload)

    grouped: dict[int, list[tuple[float, float, float, float]]] = defaultdict(list)
    for placement in placements:
        if not isinstance(placement, dict):
            raise DxfExportError("placement entry must be object")
        sheet_index = placement.get("sheet_index")
        if not isinstance(sheet_index, int) or sheet_index not in sheet_sizes:
            raise DxfExportError(f"invalid sheet_index: {sheet_index}")
        grouped[sheet_index].append(_placement_rect(placement, dims))

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    exported_files: list[str] = []
    sheet_metrics: list[dict[str, Any]] = []

    # Export only non-empty sheets (MVP requirement).
    for sheet_index in sorted(grouped):
        rects = grouped[sheet_index]
        if not rects:
            continue
        sheet_w, sheet_h = sheet_sizes[sheet_index]
        file_name = f"sheet_{sheet_index + 1:03d}.dxf"
        file_path = out_path / file_name
        _write_dxf(file_path, sheet_w, sheet_h, rects)
        exported_files.append(str(file_path.resolve()))
        sheet_metrics.append(
            {
                "sheet_index": sheet_index,
                "file": str(file_path.resolve()),
                "stock_width": sheet_w,
                "stock_height": sheet_h,
                "placed_count": len(rects),
            }
        )

    summary = {
        "exported_count": len(exported_files),
        "exported_files": exported_files,
        "sheet_metrics": sheet_metrics,
    }
    return summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export table-solver placements into per-sheet DXF files")
    parser.add_argument("--input", required=True, help="Path to solver_input.json")
    parser.add_argument("--output", required=True, help="Path to solver_output.json")
    parser.add_argument("--out-dir", required=True, help="Directory for generated sheet_XXX.dxf files")
    parser.add_argument("--summary-json", default="", help="Optional path to write export summary json")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        input_payload = _read_json(Path(args.input).resolve())
        output_payload = _read_json(Path(args.output).resolve())
        summary = export_per_sheet(input_payload, output_payload, args.out_dir)
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
    import sys

    sys.exit(main())
