#!/usr/bin/env python3
"""Per-sheet DXF exporter using BLOCK+INSERT with optional part geometry."""

from __future__ import annotations

import argparse
import json
import re
import sys
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
        out[part_id] = {
            "width": float(width),
            "height": float(height),
            "allowed_rotations": allowed_rotations,
            "outer": outer,
            "holes": holes,
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


def _block_name(part_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_]", "_", part_id)
    if not safe:
        safe = "PART"
    return f"PART_{safe.upper()}"


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


def _write_dxf(
    path: Path,
    sheet_w: float,
    sheet_h: float,
    part_defs: dict[str, dict[str, Any]],
    sheet_placements: list[dict[str, Any]],
) -> None:
    lines: list[str] = [
        "0",
        "SECTION",
        "2",
        "HEADER",
        "0",
        "ENDSEC",
        "0",
        "SECTION",
        "2",
        "BLOCKS",
    ]

    used_parts = sorted({str(p["part_id"]) for p in sheet_placements})
    for part_id in used_parts:
        pdef = part_defs[part_id]
        block = _block_name(part_id)

        lines.extend([
            "0",
            "BLOCK",
            "8",
            "PART_BLOCK",
            "2",
            block,
            "70",
            "0",
            "10",
            "0.000000",
            "20",
            "0.000000",
            "30",
            "0.0",
            "3",
            block,
            "1",
            "",
        ])

        _loop_to_lines(lines, pdef["outer"], "PART_OUTER")
        for hole in pdef["holes"]:
            _loop_to_lines(lines, hole, "PART_HOLE")

        lines.extend(["0", "ENDBLK"])

    lines.extend(["0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"])

    _add_line_entity(lines, 0.0, 0.0, sheet_w, 0.0, "SHEET")
    _add_line_entity(lines, sheet_w, 0.0, sheet_w, sheet_h, "SHEET")
    _add_line_entity(lines, sheet_w, sheet_h, 0.0, sheet_h, "SHEET")
    _add_line_entity(lines, 0.0, sheet_h, 0.0, 0.0, "SHEET")

    for placement in sheet_placements:
        part_id = str(placement["part_id"])
        block = _block_name(part_id)
        lines.extend(
            [
                "0",
                "INSERT",
                "8",
                "PART_INSERT",
                "2",
                block,
                "10",
                f"{float(placement['x']):.6f}",
                "20",
                f"{float(placement['y']):.6f}",
                "30",
                "0.0",
                "50",
                f"{float(placement['rotation_deg']):.6f}",
            ]
        )

    lines.extend(["0", "ENDSEC", "0", "EOF"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def export_per_sheet(input_payload: dict[str, Any], output_payload: dict[str, Any], out_dir: str | Path) -> dict[str, Any]:
    if output_payload.get("contract_version") != "v1":
        raise DxfExportError("output.contract_version must be v1")

    placements = output_payload.get("placements")
    if not isinstance(placements, list):
        raise DxfExportError("output.placements must be list")

    part_defs = _part_defs(input_payload)
    sheet_sizes = _sheet_sizes(input_payload)

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

    exported_files: list[str] = []
    sheet_metrics: list[dict[str, Any]] = []

    for sheet_index in sorted(grouped):
        sheet_placements = grouped[sheet_index]
        if not sheet_placements:
            continue

        sheet_w, sheet_h = sheet_sizes[sheet_index]
        file_name = f"sheet_{sheet_index + 1:03d}.dxf"
        file_path = out_path / file_name
        _write_dxf(file_path, sheet_w, sheet_h, part_defs, sheet_placements)

        exported_files.append(str(file_path.resolve()))
        sheet_metrics.append(
            {
                "sheet_index": sheet_index,
                "file": str(file_path.resolve()),
                "stock_width": sheet_w,
                "stock_height": sheet_h,
                "placed_count": len(sheet_placements),
                "export_mode": "block_insert",
                "used_part_blocks": sorted({_block_name(str(p["part_id"])) for p in sheet_placements}),
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
    parser.add_argument("--run-dir", default="", help="Run directory containing solver_input.json/solver_output.json/out/")
    parser.add_argument("--input", default="", help="Path to solver_input.json")
    parser.add_argument("--output", default="", help="Path to solver_output.json")
    parser.add_argument("--out-dir", default="", help="Directory for generated sheet_XXX.dxf files")
    parser.add_argument("--summary-json", default="", help="Optional path to write export summary json")
    return parser


def _resolve_cli_paths(args: argparse.Namespace, parser: argparse.ArgumentParser) -> tuple[Path, Path, Path]:
    run_dir_raw = str(args.run_dir or "").strip()
    input_raw = str(args.input or "").strip()
    output_raw = str(args.output or "").strip()
    out_dir_raw = str(args.out_dir or "").strip()

    if run_dir_raw:
        if input_raw or output_raw or out_dir_raw:
            parser.error("--run-dir cannot be used with --input/--output/--out-dir")
        run_dir = Path(run_dir_raw).resolve()
        return run_dir / "solver_input.json", run_dir / "solver_output.json", run_dir / "out"

    if not input_raw or not output_raw or not out_dir_raw:
        parser.error("either --run-dir or all of --input/--output/--out-dir must be provided")

    return Path(input_raw).resolve(), Path(output_raw).resolve(), Path(out_dir_raw).resolve()


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    input_path, output_path, out_dir = _resolve_cli_paths(args, parser)

    try:
        input_payload = _read_json(input_path)
        output_payload = _read_json(output_path)
        summary = export_per_sheet(input_payload, output_payload, out_dir)
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
    sys.exit(main())
