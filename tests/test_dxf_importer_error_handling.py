#!/usr/bin/env python3

import json

import pytest

from vrs_nesting.dxf.importer import DxfImportError, import_part_raw


def test_import_part_raw_invalid_ring_maps_to_dxf_invalid_ring(tmp_path):
    fixture_path = tmp_path / "invalid_ring.json"
    fixture_path.write_text(
        json.dumps(
            {
                "entities": [
                    {
                        "layer": "CUT_OUTER",
                        "type": "LWPOLYLINE",
                        "closed": True,
                        "points": [[0, 0], [0, 0], [0, 0]],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(DxfImportError) as exc:
        import_part_raw(fixture_path)

    assert exc.value.code == "DXF_INVALID_RING"


def test_import_part_raw_invalid_dxf_content_maps_to_dxf_read_failed(tmp_path):
    invalid_dxf_path = tmp_path / "not_a_real_dxf.dxf"
    invalid_dxf_path.write_text("this is not a valid dxf file", encoding="utf-8")

    with pytest.raises(DxfImportError) as exc:
        import_part_raw(invalid_dxf_path)

    assert exc.value.code == "DXF_READ_FAILED"
