#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path

import pytest

from vrs_nesting.dxf.exporter import export_per_sheet
from vrs_nesting.dxf.importer import import_part_raw


def _write_ellipse_part_dxf(path: Path) -> None:
    ezdxf = pytest.importorskip("ezdxf")
    doc = ezdxf.new(setup=True)
    doc.header["$INSUNITS"] = 4
    msp = doc.modelspace()
    msp.add_ellipse(
        center=(20.0, 10.0),
        major_axis=(10.0, 0.0),
        ratio=0.5,
        dxfattribs={"layer": "CUT_OUTER"},
    )
    doc.saveas(path)


def test_export_per_sheet_source_mode_preserves_ellipse_geometry(tmp_path: Path):
    ezdxf = pytest.importorskip("ezdxf")

    source_dxf = tmp_path / "part_ellipse.dxf"
    _write_ellipse_part_dxf(source_dxf)

    raw = import_part_raw(source_dxf)
    xs = [float(point[0]) for point in raw.outer_points_mm]
    ys = [float(point[1]) for point in raw.outer_points_mm]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    input_payload = {
        "contract_version": "v1",
        "project_name": "ellipse_source_mode",
        "seed": 0,
        "time_limit_s": 10,
        "stocks": [{"id": "SHEET_A", "width": 200.0, "height": 200.0, "quantity": 1}],
        "parts": [
            {
                "id": "ELL_PART",
                "width": float(max_x - min_x),
                "height": float(max_y - min_y),
                "quantity": 1,
                "allowed_rotations_deg": [0],
                "source_dxf_path": str(source_dxf.resolve()),
                "source_layers": {"outer": "CUT_OUTER", "inner": "CUT_INNER"},
                "source_base_offset_mm": {"x": float(min_x), "y": float(min_y)},
            }
        ],
    }
    output_payload = {
        "contract_version": "v1",
        "status": "ok",
        "placements": [
            {
                "instance_id": "ELL_PART__0001",
                "part_id": "ELL_PART",
                "sheet_index": 0,
                "x": 20.0,
                "y": 30.0,
                "rotation_deg": 0.0,
            }
        ],
        "unplaced": [],
    }

    summary = export_per_sheet(input_payload, output_payload, tmp_path / "out", geometry_mode="source")
    assert summary["exported_count"] == 1

    exported = tmp_path / "out" / "sheet_001.dxf"
    doc = ezdxf.readfile(exported)

    inserts = [entity for entity in doc.modelspace() if entity.dxftype().upper() == "INSERT"]
    assert inserts

    block_name = str(inserts[0].dxf.name)
    assert block_name in doc.blocks
    block_types = {entity.dxftype().upper() for entity in doc.blocks.get(block_name)}

    # ELLIPSE source entity must not be dropped during source export.
    assert "ELLIPSE" in block_types or "LWPOLYLINE" in block_types
