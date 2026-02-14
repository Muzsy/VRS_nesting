#!/usr/bin/env python3
"""Smoke test for source-geometry DXF export (BLOCK/INSERT + ARC/SPLINE presence)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vrs_nesting.dxf.importer import import_part_raw
from vrs_nesting.run_artifacts.run_dir import create_run_dir


FIX_DIR = ROOT / "samples" / "dxf_demo"


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _require_ezdxf() -> None:
    if importlib.util.find_spec("ezdxf") is None:
        raise AssertionError(
            "ezdxf dependency missing for source geometry smoke. "
            "Install with: python3 -m pip install --break-system-packages ezdxf"
        )


def _bbox(points: list[list[float]]) -> tuple[float, float, float, float]:
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def main() -> int:
    _require_ezdxf()
    import ezdxf  # type: ignore

    stock_fixture = FIX_DIR / "stock_rect_1000x2000.dxf"
    part_fixture = FIX_DIR / "part_arc_spline_chaining_ok.dxf"
    if not stock_fixture.is_file():
        raise AssertionError(f"missing fixture: {stock_fixture}")
    if not part_fixture.is_file():
        raise AssertionError(f"missing fixture: {part_fixture}")

    part_raw = import_part_raw(part_fixture)
    min_x, min_y, max_x, max_y = _bbox(part_raw.outer_points_mm)

    with tempfile.TemporaryDirectory(prefix="vrs_src_geo_export_") as tmp:
        run_root = Path(tmp) / "runs"
        ctx = create_run_dir(run_root=str(run_root))

        solver_input = {
            "contract_version": "v1",
            "project_name": "source_export_smoke",
            "seed": 0,
            "time_limit_s": 60,
            "stocks": [{"id": "sheet_1", "width": 1000, "height": 2000, "quantity": 1}],
            "parts": [
                {
                    "id": "part_1",
                    "width": float(max_x - min_x),
                    "height": float(max_y - min_y),
                    "quantity": 1,
                    "allowed_rotations_deg": [0, 90, 180, 270],
                    "source_dxf_path": str(part_fixture.resolve()),
                    "source_layers": {"outer": "CUT_OUTER", "inner": "CUT_INNER"},
                    "source_base_offset_mm": {"x": float(min_x), "y": float(min_y)},
                }
            ],
        }
        solver_output = {
            "contract_version": "v1",
            "status": "ok",
            "geometry_mode": "source",
            "placements": [
                {
                    "instance_id": "part_1__0001",
                    "part_id": "part_1",
                    "sheet_index": 0,
                    "x": 120.0,
                    "y": 240.0,
                    "rotation_deg": 90.0,
                }
            ],
            "unplaced": [],
        }
        source_geometry_map = {
            "contract_version": "v1",
            "parts": [
                {
                    "part_id": "part_1",
                    "source_dxf_path": str(part_fixture.resolve()),
                    "source_layers": {"outer": "CUT_OUTER", "inner": "CUT_INNER"},
                    "source_base_offset_mm": {"x": float(min_x), "y": float(min_y)},
                }
            ],
        }

        _write_json(ctx.run_dir / "solver_input.json", solver_input)
        _write_json(ctx.run_dir / "solver_output.json", solver_output)
        _write_json(ctx.run_dir / "source_geometry_map.json", source_geometry_map)

        cmd = [
            sys.executable,
            str(ROOT / "vrs_nesting" / "dxf" / "exporter.py"),
            "--run-dir",
            str(ctx.run_dir),
            "--geometry-mode",
            "source",
        ]
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise AssertionError(f"exporter failed rc={proc.returncode}, stderr={proc.stderr}")

        dxf_path = ctx.out_dir / "sheet_001.dxf"
        if not dxf_path.is_file():
            raise AssertionError(f"missing exported dxf: {dxf_path}")

        doc = ezdxf.readfile(dxf_path)
        inserts = [entity for entity in doc.modelspace() if entity.dxftype().upper() == "INSERT"]
        if not inserts:
            raise AssertionError("no INSERT entity in exported modelspace")

        insert_block_name = str(inserts[0].dxf.name)
        if insert_block_name not in doc.blocks:
            raise AssertionError(f"insert references missing block: {insert_block_name}")

        block_types = {entity.dxftype().upper() for entity in doc.blocks.get(insert_block_name)}
        if "ARC" not in block_types and "SPLINE" not in block_types:
            raise AssertionError(f"referenced block has no ARC/SPLINE: {sorted(block_types)}")

    print("[OK] source geometry export smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
