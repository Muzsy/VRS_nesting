#!/usr/bin/env python3

import json

import pytest

from vrs_nesting.dxf.importer import DxfImportError, import_part_raw


def _write_fixture(path, entities):
    path.write_text(json.dumps({"entities": entities}), encoding="utf-8")


def test_import_part_raw_json_fixture_outer_and_inner_pass(tmp_path):
    fixture_path = tmp_path / "part_ok.json"
    _write_fixture(
        fixture_path,
        [
            {
                "layer": "CUT_OUTER",
                "type": "LWPOLYLINE",
                "closed": True,
                "points": [[0, 0], [10, 0], [10, 8], [0, 8]],
            },
            {
                "layer": "CUT_INNER",
                "type": "LWPOLYLINE",
                "closed": True,
                "points": [[2, 2], [4, 2], [4, 4], [2, 4]],
            },
        ],
    )

    part = import_part_raw(fixture_path)

    assert len(part.outer_points_mm) == 4
    assert len(part.holes_points_mm) == 1
    assert len(part.holes_points_mm[0]) == 4


def test_import_part_raw_json_fixture_open_outer_fails(tmp_path):
    fixture_path = tmp_path / "part_open_outer.json"
    _write_fixture(
        fixture_path,
        [
            {
                "layer": "CUT_OUTER",
                "type": "LINE",
                "points": [[0, 0], [10, 0]],
            },
            {
                "layer": "CUT_OUTER",
                "type": "LINE",
                "points": [[10, 0], [10, 8]],
            },
        ],
    )

    with pytest.raises(DxfImportError) as exc:
        import_part_raw(fixture_path)

    assert exc.value.code == "DXF_OPEN_OUTER_PATH"


def test_import_part_raw_json_fixture_missing_outer_fails(tmp_path):
    fixture_path = tmp_path / "part_no_outer.json"
    _write_fixture(
        fixture_path,
        [
            {
                "layer": "CUT_INNER",
                "type": "LWPOLYLINE",
                "closed": True,
                "points": [[2, 2], [4, 2], [4, 4], [2, 4]],
            }
        ],
    )

    with pytest.raises(DxfImportError) as exc:
        import_part_raw(fixture_path)

    assert exc.value.code == "DXF_NO_OUTER_LAYER"
