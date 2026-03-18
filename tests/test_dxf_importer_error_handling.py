#!/usr/bin/env python3

import json

import pytest

from vrs_nesting.dxf.importer import DxfImportError, import_part_raw
from vrs_nesting.dxf.importer import (
    CURVE_FLATTEN_TOL_MAX_SOURCE_UNITS,
    CURVE_FLATTEN_TOL_MIN_SOURCE_UNITS,
    MAX_CURVE_POINTS,
    _clamp_curve_flatten_tolerance,
    _flatten_curve_points,
)


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


def test_import_part_raw_nan_coordinate_rejected(tmp_path):
    fixture_path = tmp_path / "nan_coord.json"
    fixture_path.write_text(
        json.dumps(
            {
                "entities": [
                    {
                        "layer": "CUT_OUTER",
                        "type": "LWPOLYLINE",
                        "closed": True,
                        "points": [[0.0, 0.0], [10.0, 0.0], [float("nan"), 5.0]],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(DxfImportError) as exc:
        import_part_raw(fixture_path)

    assert exc.value.code == "DXF_INVALID_POINTS"


def test_import_part_raw_invalid_dxf_content_maps_to_dxf_read_failed(tmp_path):
    invalid_dxf_path = tmp_path / "not_a_real_dxf.dxf"
    invalid_dxf_path.write_text("this is not a valid dxf file", encoding="utf-8")

    with pytest.raises(DxfImportError) as exc:
        import_part_raw(invalid_dxf_path)

    assert exc.value.code == "DXF_READ_FAILED"


def test_import_part_raw_curve_contour_self_intersection_maps_to_dxf_invalid_ring(tmp_path):
    fixture_path = tmp_path / "self_intersecting_curve.json"
    fixture_path.write_text(
        json.dumps(
            {
                "entities": [
                    {
                        "layer": "CUT_OUTER",
                        "type": "SPLINE",
                        "closed": True,
                        "points": [[0, 0], [10, 10], [0, 10], [10, 0]],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(DxfImportError) as exc:
        import_part_raw(fixture_path)

    assert exc.value.code == "DXF_INVALID_RING"


def test_import_part_raw_dxf_ellipse_outer_supported(tmp_path):
    ezdxf = pytest.importorskip("ezdxf")
    path = tmp_path / "ellipse_outer.dxf"

    doc = ezdxf.new(setup=True)
    doc.header["$INSUNITS"] = 4
    msp = doc.modelspace()
    msp.add_ellipse(
        center=(20.0, 10.0),
        major_axis=(12.0, 0.0),
        ratio=0.5,
        dxfattribs={"layer": "CUT_OUTER"},
    )
    doc.saveas(path)

    part = import_part_raw(path)
    assert len(part.outer_points_mm) >= 8
    assert len(part.holes_points_mm) == 0


def test_import_part_raw_dxf_insert_block_decomposed(tmp_path):
    ezdxf = pytest.importorskip("ezdxf")
    path = tmp_path / "insert_outer.dxf"

    doc = ezdxf.new(setup=True)
    doc.header["$INSUNITS"] = 4
    block = doc.blocks.new(name="PART_BLOCK")
    block.add_lwpolyline(
        [(0.0, 0.0), (40.0, 0.0), (40.0, 20.0), (0.0, 20.0)],
        format="xy",
        close=True,
        dxfattribs={"layer": "CUT_OUTER"},
    )
    doc.modelspace().add_blockref("PART_BLOCK", (100.0, 200.0), dxfattribs={"layer": "CUT_OUTER"})
    doc.saveas(path)

    part = import_part_raw(path)
    xs = [float(point[0]) for point in part.outer_points_mm]
    ys = [float(point[1]) for point in part.outer_points_mm]
    assert min(xs) == pytest.approx(100.0)
    assert max(xs) == pytest.approx(140.0)
    assert min(ys) == pytest.approx(200.0)
    assert max(ys) == pytest.approx(220.0)


def test_import_part_raw_dxf_insunits_inch_scaled_to_mm(tmp_path):
    ezdxf = pytest.importorskip("ezdxf")
    path = tmp_path / "insunits_inch.dxf"

    doc = ezdxf.new(setup=True)
    doc.header["$INSUNITS"] = 1
    msp = doc.modelspace()
    msp.add_lwpolyline(
        [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)],
        format="xy",
        close=True,
        dxfattribs={"layer": "CUT_OUTER"},
    )
    doc.saveas(path)

    part = import_part_raw(path)
    xs = [float(point[0]) for point in part.outer_points_mm]
    ys = [float(point[1]) for point in part.outer_points_mm]
    assert max(xs) - min(xs) == pytest.approx(25.4, abs=1e-6)
    assert max(ys) - min(ys) == pytest.approx(25.4, abs=1e-6)


def test_clamp_curve_flatten_tolerance_limits_to_sane_range():
    assert _clamp_curve_flatten_tolerance(1e-20) == pytest.approx(CURVE_FLATTEN_TOL_MIN_SOURCE_UNITS)
    assert _clamp_curve_flatten_tolerance(1e9) == pytest.approx(CURVE_FLATTEN_TOL_MAX_SOURCE_UNITS)
    assert _clamp_curve_flatten_tolerance(0.25) == pytest.approx(0.25)


def test_flatten_curve_points_rejects_unbounded_tessellation():
    class _FakeVertex:
        def __init__(self, x: float, y: float) -> None:
            self.x = x
            self.y = y

    class _FakeCurve:
        def flattening(self, _tol: float):
            return [_FakeVertex(float(idx), 0.0) for idx in range(MAX_CURVE_POINTS + 1)]

    class _FakeEzdxf:
        class DXFError(Exception):
            pass

    with pytest.raises(DxfImportError) as exc:
        _flatten_curve_points(_FakeCurve(), where="curve", flatten_tol=0.1, ezdxf_module=_FakeEzdxf)

    assert exc.value.code == "DXF_CURVE_TOO_COMPLEX"
