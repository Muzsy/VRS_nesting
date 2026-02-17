#!/usr/bin/env python3

from __future__ import annotations

import pytest

from vrs_nesting.dxf.exporter import _approx_block_name, export_per_sheet


def _input_payload_for_approx_source_entities() -> dict:
    return {
        "contract_version": "v1",
        "project_name": "approx_entity_preserve",
        "seed": 0,
        "time_limit_s": 30,
        "stocks": [{"id": "SHEET_A", "width": 200.0, "height": 200.0, "quantity": 1}],
        "parts": [
            {
                "id": "A-1",
                "width": 20.0,
                "height": 20.0,
                "quantity": 1,
                "allowed_rotations_deg": [0],
                "outer_points": [[0, 0], [20, 0], [20, 20], [0, 20]],
                "source_entities": [
                    {
                        "layer": "CUT_OUTER",
                        "type": "ARC",
                        "center": [10.0, 10.0],
                        "radius": 5.0,
                        "start_angle": 0.0,
                        "end_angle": 180.0,
                    }
                ],
            },
            {
                "id": "A_1",
                "width": 20.0,
                "height": 20.0,
                "quantity": 1,
                "allowed_rotations_deg": [0],
                "outer_points": [[0, 0], [20, 0], [20, 20], [0, 20]],
                "source_entities": [
                    {
                        "layer": "CUT_OUTER",
                        "type": "SPLINE",
                        "closed": False,
                        "points": [[0.0, 0.0], [10.0, 15.0], [20.0, 0.0]],
                    }
                ],
            },
        ],
    }


def _output_payload_for_approx_source_entities() -> dict:
    return {
        "contract_version": "v1",
        "status": "ok",
        "placements": [
            {"instance_id": "A-1__0001", "part_id": "A-1", "sheet_index": 0, "x": 10.0, "y": 10.0, "rotation_deg": 0.0},
            {"instance_id": "A_1__0001", "part_id": "A_1", "sheet_index": 0, "x": 40.0, "y": 10.0, "rotation_deg": 0.0},
        ],
        "unplaced": [],
    }


def test_approx_block_names_are_collision_safe():
    left = _approx_block_name("A-1")
    right = _approx_block_name("A_1")
    assert left != right


def test_export_per_sheet_approx_preserves_arc_spline_entities(tmp_path):
    ezdxf = pytest.importorskip("ezdxf")
    input_payload = _input_payload_for_approx_source_entities()
    output_payload = _output_payload_for_approx_source_entities()

    summary = export_per_sheet(input_payload, output_payload, tmp_path / "out", geometry_mode="approx")
    assert summary["exported_count"] == 1

    dxf_path = tmp_path / "out" / "sheet_001.dxf"
    doc = ezdxf.readfile(dxf_path)

    blocks = {block.name: block for block in doc.blocks}
    block_a = _approx_block_name("A-1")
    block_b = _approx_block_name("A_1")

    assert block_a in blocks
    assert block_b in blocks

    types_a = {entity.dxftype().upper() for entity in blocks[block_a]}
    types_b = {entity.dxftype().upper() for entity in blocks[block_b]}

    assert "ARC" in types_a
    assert "SPLINE" in types_b
