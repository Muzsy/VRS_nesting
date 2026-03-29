#!/usr/bin/env python3
"""Generate deterministic DXF fixtures for H3 quality benchmark cases."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import sys

try:
    import ezdxf  # type: ignore
except Exception as exc:  # noqa: BLE001
    raise SystemExit(
        "ezdxf dependency missing for benchmark fixture generation. "
        "Install with: python3 -m pip install --break-system-packages ezdxf"
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUTPUT_ROOT = ROOT / "samples" / "trial_run_quality" / "fixtures"


@dataclass(frozen=True)
class _PartSpec:
    file_name: str
    shape: str
    points: tuple[tuple[float, float], ...] = ()
    center: tuple[float, float] = (0.0, 0.0)
    radius: float = 0.0


@dataclass(frozen=True)
class _CaseSpec:
    case_id: str
    fixture_kind: str
    sheet_width_mm: float
    sheet_height_mm: float
    stock_margin_mm: float
    parts: tuple[_PartSpec, ...]


CASE_SPECS: dict[str, _CaseSpec] = {
    "triangles_rotation_pair": _CaseSpec(
        case_id="triangles_rotation_pair",
        fixture_kind="triangles_rotation_pair",
        sheet_width_mm=1200.0,
        sheet_height_mm=800.0,
        stock_margin_mm=10.0,
        parts=(
            _PartSpec(
                file_name="triangle_a.dxf",
                shape="polygon",
                points=((0.0, 0.0), (280.0, 0.0), (40.0, 120.0)),
            ),
            _PartSpec(
                file_name="triangle_b.dxf",
                shape="polygon",
                points=((0.0, 0.0), (260.0, 0.0), (210.0, 160.0)),
            ),
        ),
    ),
    "circles_dense_pack": _CaseSpec(
        case_id="circles_dense_pack",
        fixture_kind="circles_dense_pack",
        sheet_width_mm=1000.0,
        sheet_height_mm=700.0,
        stock_margin_mm=8.0,
        parts=(
            _PartSpec(
                file_name="circle_120.dxf",
                shape="circle",
                center=(120.0, 120.0),
                radius=120.0,
            ),
        ),
    ),
    "lshape_rect_mix": _CaseSpec(
        case_id="lshape_rect_mix",
        fixture_kind="lshape_rect_mix",
        sheet_width_mm=1300.0,
        sheet_height_mm=900.0,
        stock_margin_mm=10.0,
        parts=(
            _PartSpec(
                file_name="lshape_a.dxf",
                shape="polygon",
                points=((0.0, 0.0), (260.0, 0.0), (260.0, 80.0), (110.0, 80.0), (110.0, 260.0), (0.0, 260.0)),
            ),
            _PartSpec(
                file_name="rect_long.dxf",
                shape="polygon",
                points=((0.0, 0.0), (360.0, 0.0), (360.0, 90.0), (0.0, 90.0)),
            ),
        ),
    ),
}


def _new_doc() -> Any:
    doc = ezdxf.new("R2010")
    if "CUT_OUTER" not in doc.layers:
        doc.layers.new(name="CUT_OUTER")
    # Keep unit semantics explicit (4 = millimeters).
    doc.header["$INSUNITS"] = 4
    return doc


def _write_polygon(path: Path, points: tuple[tuple[float, float], ...]) -> None:
    doc = _new_doc()
    msp = doc.modelspace()
    msp.add_lwpolyline(list(points), dxfattribs={"layer": "CUT_OUTER", "closed": True})
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(path)


def _write_circle(path: Path, center: tuple[float, float], radius: float) -> None:
    doc = _new_doc()
    msp = doc.modelspace()
    msp.add_circle(center, radius, dxfattribs={"layer": "CUT_OUTER"})
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(path)


def _write_stock(path: Path, *, width_mm: float, height_mm: float, margin_mm: float) -> None:
    x0 = float(margin_mm)
    y0 = float(margin_mm)
    x1 = x0 + float(width_mm)
    y1 = y0 + float(height_mm)
    _write_polygon(path, ((x0, y0), (x1, y0), (x1, y1), (x0, y1)))


def generate_benchmark_fixtures(
    *,
    output_root: Path,
    case_ids: list[str] | None = None,
) -> dict[str, Any]:
    selected_ids = case_ids or sorted(CASE_SPECS.keys())
    for case_id in selected_ids:
        if case_id not in CASE_SPECS:
            raise ValueError(f"unknown benchmark case: {case_id}")

    output_root = output_root.resolve()
    results: list[dict[str, Any]] = []
    for case_id in selected_ids:
        case = CASE_SPECS[case_id]
        case_dir = output_root / case.case_id
        parts_dir = case_dir / "parts"
        stock_path = case_dir / "stock.dxf"
        _write_stock(
            stock_path,
            width_mm=case.sheet_width_mm,
            height_mm=case.sheet_height_mm,
            margin_mm=case.stock_margin_mm,
        )

        generated_part_files: list[str] = []
        for part in case.parts:
            part_path = parts_dir / part.file_name
            if part.shape == "polygon":
                _write_polygon(part_path, part.points)
            elif part.shape == "circle":
                _write_circle(part_path, part.center, part.radius)
            else:
                raise ValueError(f"unsupported part shape={part.shape} for case={case.case_id}")
            generated_part_files.append(part.file_name)

        results.append(
            {
                "case_id": case.case_id,
                "fixture_kind": case.fixture_kind,
                "case_dir": str(case_dir),
                "parts_dir": str(parts_dir),
                "stock_path": str(stock_path),
                "sheet_width_mm": case.sheet_width_mm,
                "sheet_height_mm": case.sheet_height_mm,
                "part_files": sorted(generated_part_files),
            }
        )

    return {
        "version": "h3_quality_benchmark_fixture_pack_v1",
        "output_root": str(output_root),
        "cases": results,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Target directory for generated benchmark fixtures",
    )
    parser.add_argument(
        "--case",
        action="append",
        default=[],
        help=f"Generate only the given case id. Allowed: {', '.join(sorted(CASE_SPECS.keys()))}",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    output_root = Path(str(args.output_root))
    selected_ids = [str(item).strip() for item in args.case if str(item).strip()]
    payload = generate_benchmark_fixtures(output_root=output_root, case_ids=selected_ids or None)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
