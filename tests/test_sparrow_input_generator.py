#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vrs_nesting.project.model import DxfAssetSpec, DxfProjectModel
from vrs_nesting.sparrow.input_generator import build_sparrow_inputs


def _write_json_fixture(path: Path, entities: list[dict]) -> None:
    path.write_text(json.dumps({"entities": entities}, ensure_ascii=False) + "\n", encoding="utf-8")


def test_build_sparrow_inputs_source_base_offset_uses_prepared_geometry(tmp_path: Path):
    stock_path = tmp_path / "stock.json"
    part_path = tmp_path / "part.json"

    _write_json_fixture(
        stock_path,
        [
            {
                "layer": "CUT_OUTER",
                "type": "LWPOLYLINE",
                "closed": True,
                "points": [[0, 0], [100, 0], [100, 100], [0, 100]],
            }
        ],
    )
    _write_json_fixture(
        part_path,
        [
            {
                "layer": "CUT_OUTER",
                "type": "LWPOLYLINE",
                "closed": True,
                "points": [[0, 0], [10, 0], [10, 10], [0, 10]],
            }
        ],
    )

    project = DxfProjectModel(
        version="dxf_v1",
        name="offset_source_base",
        seed=0,
        time_limit_s=10,
        units="mm",
        spacing_mm=2.0,
        margin_mm=0.0,
        stocks_dxf=[DxfAssetSpec(id="stock_1", path=str(stock_path), quantity=1, allowed_rotations_deg=[0])],
        parts_dxf=[DxfAssetSpec(id="part_1", path=str(part_path), quantity=1, allowed_rotations_deg=[0])],
    )

    _, solver_input, _ = build_sparrow_inputs(project, project_dir=tmp_path)

    part_entry = solver_input["parts"][0]
    base = part_entry["source_base_offset_mm"]
    assert float(base["x"]) == pytest.approx(-1.0)
    assert float(base["y"]) == pytest.approx(-1.0)


def test_build_sparrow_inputs_exposes_spacing_and_margin_for_validator(tmp_path: Path):
    stock_path = tmp_path / "stock.json"
    part_path = tmp_path / "part.json"

    _write_json_fixture(
        stock_path,
        [
            {
                "layer": "CUT_OUTER",
                "type": "LWPOLYLINE",
                "closed": True,
                "points": [[0, 0], [100, 0], [100, 100], [0, 100]],
            }
        ],
    )
    _write_json_fixture(
        part_path,
        [
            {
                "layer": "CUT_OUTER",
                "type": "LWPOLYLINE",
                "closed": True,
                "points": [[0, 0], [10, 0], [10, 10], [0, 10]],
            }
        ],
    )

    project = DxfProjectModel(
        version="dxf_v1",
        name="spacing_margin_presence",
        seed=0,
        time_limit_s=10,
        units="mm",
        spacing_mm=1.5,
        margin_mm=0.75,
        stocks_dxf=[DxfAssetSpec(id="stock_1", path=str(stock_path), quantity=1, allowed_rotations_deg=[0])],
        parts_dxf=[DxfAssetSpec(id="part_1", path=str(part_path), quantity=1, allowed_rotations_deg=[0])],
    )

    _, solver_input, _ = build_sparrow_inputs(project, project_dir=tmp_path)

    assert float(solver_input["spacing_mm"]) == pytest.approx(1.5)
    assert float(solver_input["margin_mm"]) == pytest.approx(0.75)
