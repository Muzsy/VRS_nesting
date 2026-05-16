#!/usr/bin/env python3
"""Unit tests for lv8_polygon_validator.py — polygon-aware validation gate (T05)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
_VALIDATOR_PATH = REPO_ROOT / "scripts" / "experiments" / "lv8_polygon_validator.py"

spec = importlib.util.spec_from_file_location("lv8_polygon_validator", _VALIDATOR_PATH)
assert spec is not None and spec.loader is not None
_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_mod)  # type: ignore[arg-type]

validate = _mod.validate
_build_placed_polygon = _mod._build_placed_polygon

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fixture(
    width_mm: float = 500.0,
    height_mm: float = 500.0,
    spacing_mm: float = 0.0,
    margin_mm: float = 0.0,
    parts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "sheet": {
            "width_mm": width_mm,
            "height_mm": height_mm,
            "spacing_mm": spacing_mm,
            "margin_mm": margin_mm,
        },
        "parts": parts or [],
    }


def _rect_pts(w: float, h: float) -> list[list[float]]:
    return [[0.0, 0.0], [w, 0.0], [w, h], [0.0, h]]


def _make_prepacked(parts: list[dict[str, Any]]) -> dict[str, Any]:
    return {"parts": parts}


def _make_solver_output(
    placements: list[dict[str, Any]],
    sheets_used: int = 1,
    unplaced: list[Any] | None = None,
) -> dict[str, Any]:
    return {
        "placements": placements,
        "sheets_used": sheets_used,
        "unplaced": unplaced or [],
    }


def _placement(part_id: str, x: float, y: float, rot: float = 0.0, sheet: int = 0, instance: int = 0) -> dict[str, Any]:
    return {"part_id": part_id, "x_mm": x, "y_mm": y, "rotation_deg": rot, "sheet": sheet, "instance": instance}


# ---------------------------------------------------------------------------
# 1. Valid non-overlap fixture
# ---------------------------------------------------------------------------

class TestValidNonOverlap:
    def test_two_non_overlapping_rects_pass(self) -> None:
        fixture = _make_fixture(width_mm=500, height_mm=500)
        prepacked = _make_prepacked([
            {"id": "A", "outer_points_mm": _rect_pts(50, 50)},
            {"id": "B", "outer_points_mm": _rect_pts(50, 50)},
        ])
        solver_out = _make_solver_output([
            _placement("A", x=0, y=0, instance=0),
            _placement("B", x=100, y=0, instance=1),
        ], sheets_used=1)
        result = validate(
            fixture=fixture,
            prepacked_input=prepacked,
            solver_output=solver_out,
            cavity_plan=None,
            required_instances=2,
            spacing_mm=0.0,
            margin_mm=0.0,
        )
        assert result["valid_polygon_gate"] is True
        assert result["overlap_count"] == 0
        assert result["boundary_count"] == 0
        assert result["clearance_count"] == 0
        assert result["missing_geometry_count"] == 0
        assert result["validation_kind"] == "polygon-aware"
        assert result["legacy_aabb_validator"] is False

    def test_quantity_ok_true_when_all_placed(self) -> None:
        fixture = _make_fixture()
        prepacked = _make_prepacked([{"id": "A", "outer_points_mm": _rect_pts(10, 10)}])
        solver_out = _make_solver_output([_placement("A", 0, 0)], sheets_used=1)
        result = validate(
            fixture=fixture,
            prepacked_input=prepacked,
            solver_output=solver_out,
            cavity_plan=None,
            required_instances=1,
            spacing_mm=0.0,
            margin_mm=0.0,
        )
        assert result["quantity_ok"] is True
        assert result["valid_polygon_gate"] is True


# ---------------------------------------------------------------------------
# 2. Polygon overlap invalid
# ---------------------------------------------------------------------------

class TestPolygonOverlap:
    def test_overlapping_rects_fail(self) -> None:
        fixture = _make_fixture(width_mm=500, height_mm=500)
        prepacked = _make_prepacked([
            {"id": "A", "outer_points_mm": _rect_pts(100, 100)},
            {"id": "B", "outer_points_mm": _rect_pts(100, 100)},
        ])
        # Both placed at (0,0) → full overlap
        solver_out = _make_solver_output([
            _placement("A", x=0, y=0, instance=0),
            _placement("B", x=0, y=0, instance=1),
        ], sheets_used=1)
        result = validate(
            fixture=fixture,
            prepacked_input=prepacked,
            solver_output=solver_out,
            cavity_plan=None,
            required_instances=2,
            spacing_mm=0.0,
            margin_mm=0.0,
        )
        assert result["valid_polygon_gate"] is False
        assert result["overlap_count"] > 0

    def test_partially_overlapping_rects_fail(self) -> None:
        fixture = _make_fixture(width_mm=500, height_mm=500)
        prepacked = _make_prepacked([
            {"id": "A", "outer_points_mm": _rect_pts(100, 100)},
            {"id": "B", "outer_points_mm": _rect_pts(100, 100)},
        ])
        # B overlaps A by 50mm
        solver_out = _make_solver_output([
            _placement("A", x=0, y=0, instance=0),
            _placement("B", x=50, y=0, instance=1),
        ], sheets_used=1)
        result = validate(
            fixture=fixture,
            prepacked_input=prepacked,
            solver_output=solver_out,
            cavity_plan=None,
            required_instances=2,
            spacing_mm=0.0,
            margin_mm=0.0,
        )
        assert result["valid_polygon_gate"] is False
        assert result["overlap_count"] > 0

    def test_issues_sample_contains_overlap_code(self) -> None:
        fixture = _make_fixture()
        prepacked = _make_prepacked([{"id": "X", "outer_points_mm": _rect_pts(50, 50)}])
        solver_out = _make_solver_output([
            _placement("X", 0, 0, instance=0),
            _placement("X", 0, 0, instance=1),
        ], sheets_used=1)
        result = validate(
            fixture=fixture, prepacked_input=prepacked, solver_output=solver_out,
            cavity_plan=None, required_instances=2, spacing_mm=0.0, margin_mm=0.0,
        )
        codes = [i["code"] for i in result["issues_sample"]]
        assert "POLYGON_OVERLAP" in codes


# ---------------------------------------------------------------------------
# 3. Boundary / margin violation
# ---------------------------------------------------------------------------

class TestBoundaryViolation:
    def test_part_outside_margin_fails(self) -> None:
        fixture = _make_fixture(width_mm=200, height_mm=200, margin_mm=20.0)
        prepacked = _make_prepacked([{"id": "A", "outer_points_mm": _rect_pts(50, 50)}])
        # Placed at (0,0) → violates 20mm margin on left/bottom
        solver_out = _make_solver_output([_placement("A", x=0, y=0)], sheets_used=1)
        result = validate(
            fixture=fixture,
            prepacked_input=prepacked,
            solver_output=solver_out,
            cavity_plan=None,
            required_instances=1,
            spacing_mm=0.0,
            margin_mm=20.0,
        )
        assert result["valid_polygon_gate"] is False
        assert result["boundary_count"] > 0

    def test_part_within_margin_passes(self) -> None:
        fixture = _make_fixture(width_mm=200, height_mm=200, margin_mm=10.0)
        prepacked = _make_prepacked([{"id": "A", "outer_points_mm": _rect_pts(50, 50)}])
        # Placed at (10, 10) → within margin
        solver_out = _make_solver_output([_placement("A", x=10, y=10)], sheets_used=1)
        result = validate(
            fixture=fixture,
            prepacked_input=prepacked,
            solver_output=solver_out,
            cavity_plan=None,
            required_instances=1,
            spacing_mm=0.0,
            margin_mm=10.0,
        )
        assert result["valid_polygon_gate"] is True
        assert result["boundary_count"] == 0

    def test_part_exceeds_sheet_fails(self) -> None:
        fixture = _make_fixture(width_mm=100, height_mm=100)
        prepacked = _make_prepacked([{"id": "A", "outer_points_mm": _rect_pts(80, 80)}])
        # Placed at (50, 50) → extends to (130, 130), way outside
        solver_out = _make_solver_output([_placement("A", x=50, y=50)], sheets_used=1)
        result = validate(
            fixture=fixture, prepacked_input=prepacked, solver_output=solver_out,
            cavity_plan=None, required_instances=1, spacing_mm=0.0, margin_mm=0.0,
        )
        assert result["valid_polygon_gate"] is False
        assert result["boundary_count"] > 0


# ---------------------------------------------------------------------------
# 4. Clearance / spacing violation
# ---------------------------------------------------------------------------

class TestClearanceViolation:
    def test_parts_too_close_fail(self) -> None:
        fixture = _make_fixture(width_mm=500, height_mm=500, spacing_mm=10.0)
        prepacked = _make_prepacked([
            {"id": "A", "outer_points_mm": _rect_pts(50, 50)},
            {"id": "B", "outer_points_mm": _rect_pts(50, 50)},
        ])
        # A: (0,0)-(50,50), B: (55,0)-(105,50) — gap=5mm < 10mm
        solver_out = _make_solver_output([
            _placement("A", x=0, y=0, instance=0),
            _placement("B", x=55, y=0, instance=1),
        ], sheets_used=1)
        result = validate(
            fixture=fixture,
            prepacked_input=prepacked,
            solver_output=solver_out,
            cavity_plan=None,
            required_instances=2,
            spacing_mm=10.0,
            margin_mm=0.0,
        )
        assert result["valid_polygon_gate"] is False
        assert result["clearance_count"] > 0

    def test_parts_with_sufficient_spacing_pass(self) -> None:
        fixture = _make_fixture(width_mm=500, height_mm=500, spacing_mm=10.0)
        prepacked = _make_prepacked([
            {"id": "A", "outer_points_mm": _rect_pts(50, 50)},
            {"id": "B", "outer_points_mm": _rect_pts(50, 50)},
        ])
        # A: (0,0)-(50,50), B: (65,0) — gap=15mm >= 10mm
        solver_out = _make_solver_output([
            _placement("A", x=0, y=0, instance=0),
            _placement("B", x=65, y=0, instance=1),
        ], sheets_used=1)
        result = validate(
            fixture=fixture,
            prepacked_input=prepacked,
            solver_output=solver_out,
            cavity_plan=None,
            required_instances=2,
            spacing_mm=10.0,
            margin_mm=0.0,
        )
        assert result["valid_polygon_gate"] is True
        assert result["clearance_count"] == 0


# ---------------------------------------------------------------------------
# 5. Missing geometry
# ---------------------------------------------------------------------------

class TestMissingGeometry:
    def test_missing_part_id_in_prepacked_fails(self) -> None:
        fixture = _make_fixture()
        prepacked = _make_prepacked([])  # No geometry for "X"
        solver_out = _make_solver_output([_placement("X", 0, 0)], sheets_used=1)
        result = validate(
            fixture=fixture, prepacked_input=prepacked, solver_output=solver_out,
            cavity_plan=None, required_instances=1, spacing_mm=0.0, margin_mm=0.0,
        )
        assert result["valid_polygon_gate"] is False
        assert result["missing_geometry_count"] > 0


# ---------------------------------------------------------------------------
# 6. Polygon transform (rotation + normalization)
# ---------------------------------------------------------------------------

class TestPolygonTransform:
    def test_zero_rotation_no_shift(self) -> None:
        pts = [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]]
        poly = _build_placed_polygon(pts, x_mm=5.0, y_mm=7.0, rotation_deg=0.0)
        minx, miny, maxx, maxy = poly.bounds
        assert abs(minx - 5.0) < 0.01
        assert abs(miny - 7.0) < 0.01
        assert abs(maxx - 15.0) < 0.01
        assert abs(maxy - 17.0) < 0.01

    def test_90_rotation_normalizes_before_translate(self) -> None:
        # 10x5 rectangle rotated 90° → becomes 5x10
        pts = [[0.0, 0.0], [10.0, 0.0], [10.0, 5.0], [0.0, 5.0]]
        poly = _build_placed_polygon(pts, x_mm=0.0, y_mm=0.0, rotation_deg=90.0)
        minx, miny, maxx, maxy = poly.bounds
        assert abs(minx - 0.0) < 0.1
        assert abs(miny - 0.0) < 0.1
        assert abs(maxx - 5.0) < 0.1
        assert abs(maxy - 10.0) < 0.1
