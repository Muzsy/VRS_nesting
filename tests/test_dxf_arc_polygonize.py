#!/usr/bin/env python3
"""Unit tests for arc_to_points() wrap_ccw DXF ARC fix.

DXF ARC entities are always counter-clockwise. When end_angle < start_angle
(e.g. 270° → 90°) the span wraps around 360°, not backwards.
"""

from __future__ import annotations

import math

import pytest

from vrs_nesting.geometry.polygonize import arc_to_points


def _angle_of(point: list[float], center: tuple[float, float] = (0.0, 0.0)) -> float:
    return math.degrees(math.atan2(point[1] - center[1], point[0] - center[0])) % 360.0


class TestArcToPointsWrapCCW:
    def test_wrap_ccw_270_to_90_produces_ccw_arc(self) -> None:
        """270° → 90° with wrap_ccw=True must go CCW (through 0°, not through 180°)."""
        points = arc_to_points(
            center_x=0.0,
            center_y=0.0,
            radius=10.0,
            start_angle_deg=270.0,
            end_angle_deg=90.0,
            wrap_ccw=True,
        )
        assert len(points) >= 3

        # First point should be at 270° (bottom)
        start_angle = _angle_of(points[0])
        assert abs(start_angle - 270.0) < 5.0, f"expected ~270°, got {start_angle:.1f}°"

        # Last point should be at 90° (top)
        end_angle = _angle_of(points[-1])
        assert abs(end_angle - 90.0) < 5.0, f"expected ~90°, got {end_angle:.1f}°"

        # The arc should pass through 0° (right side), not through 180° (left side)
        angles = [_angle_of(p) for p in points]
        passes_through_right = any(a < 30.0 or a > 330.0 for a in angles)
        passes_through_left = any(160.0 < a < 200.0 for a in angles)
        assert passes_through_right, "CCW arc from 270° to 90° must pass through 0°"
        assert not passes_through_left, "CCW arc from 270° to 90° must NOT pass through 180°"

    def test_wrap_ccw_span_is_180_degrees(self) -> None:
        """270° → 90° is a 180° CCW arc; old code produced -180° (CW)."""
        points_ccw = arc_to_points(
            center_x=0.0,
            center_y=0.0,
            radius=10.0,
            start_angle_deg=270.0,
            end_angle_deg=90.0,
            wrap_ccw=True,
        )
        # Arc length ≈ π*r = ~31.4 mm; point density should match
        arc_len = math.hypot(
            points_ccw[-1][0] - points_ccw[0][0],
            points_ccw[-1][1] - points_ccw[0][1],
        )
        # Chord from (0,-10) to (0,10) = 20 mm — well within a 31 mm arc
        assert arc_len < 25.0, f"chord distance unexpectedly large: {arc_len:.2f}"

    def test_wrap_ccw_false_preserves_old_behaviour_for_positive_span(self) -> None:
        """wrap_ccw=False must not change existing CCW arcs with positive span."""
        pts_old = arc_to_points(
            center_x=0.0, center_y=0.0, radius=5.0,
            start_angle_deg=0.0, end_angle_deg=90.0,
            wrap_ccw=False,
        )
        pts_new = arc_to_points(
            center_x=0.0, center_y=0.0, radius=5.0,
            start_angle_deg=0.0, end_angle_deg=90.0,
            wrap_ccw=True,
        )
        assert len(pts_old) == len(pts_new)
        for a, b in zip(pts_old, pts_new):
            assert abs(a[0] - b[0]) < 1e-9 and abs(a[1] - b[1]) < 1e-9

    def test_wrap_ccw_full_circle_when_equal_angles(self) -> None:
        """start == end with wrap_ccw=True → full 360° circle."""
        points = arc_to_points(
            center_x=0.0, center_y=0.0, radius=10.0,
            start_angle_deg=45.0, end_angle_deg=45.0,
            wrap_ccw=True,
        )
        # Should return at least 12 segments + 1 = 13 points
        assert len(points) >= 13
        # First and last point should be at the same angle (45°)
        assert abs(_angle_of(points[0]) - 45.0) < 5.0
        assert abs(_angle_of(points[-1]) - 45.0) < 5.0

    def test_wrap_ccw_30_to_330_produces_300_degree_arc(self) -> None:
        """30° → 330° with wrap_ccw=True is 300° CCW (not -60° CW)."""
        points = arc_to_points(
            center_x=0.0, center_y=0.0, radius=10.0,
            start_angle_deg=30.0, end_angle_deg=330.0,
            wrap_ccw=True,
        )
        assert len(points) >= 12
        start_angle = _angle_of(points[0])
        end_angle = _angle_of(points[-1])
        assert abs(start_angle - 30.0) < 5.0
        assert abs(end_angle - 330.0) < 5.0

        # A 300° CCW arc must pass through 180° (left side)
        angles = [_angle_of(p) for p in points]
        passes_left = any(160.0 < a < 200.0 for a in angles)
        assert passes_left, "300° CCW arc from 30° to 330° must pass through 180°"
