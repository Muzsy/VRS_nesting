#!/usr/bin/env python3

import math

from vrs_nesting.geometry.polygonize import (
    ARC_POLYGONIZE_MIN_SEGMENTS,
    CURVE_FLATTEN_TOLERANCE_MM,
    arc_to_points,
)


def _sagitta_for_segment(a: list[float], b: list[float], radius: float) -> float:
    chord = math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))
    half = chord * 0.5
    if half >= radius:
        return radius
    return radius - math.sqrt((radius * radius) - (half * half))


def test_arc_to_points_min_segments_enforced_for_small_arc():
    points = arc_to_points(
        center_x=0.0,
        center_y=0.0,
        radius=10.0,
        start_angle_deg=0.0,
        end_angle_deg=90.0,
        max_chord_error_mm=10.0,
        min_segments=ARC_POLYGONIZE_MIN_SEGMENTS,
    )

    assert len(points) == ARC_POLYGONIZE_MIN_SEGMENTS + 1


def test_arc_to_points_chord_error_respects_policy_tolerance():
    points = arc_to_points(
        center_x=0.0,
        center_y=0.0,
        radius=50.0,
        start_angle_deg=0.0,
        end_angle_deg=180.0,
        max_chord_error_mm=CURVE_FLATTEN_TOLERANCE_MM,
        min_segments=2,
    )

    for idx in range(len(points) - 1):
        sagitta = _sagitta_for_segment(points[idx], points[idx + 1], radius=50.0)
        assert sagitta <= CURVE_FLATTEN_TOLERANCE_MM + 1e-9


def test_arc_to_points_zero_span_means_full_circle():
    points = arc_to_points(
        center_x=2.0,
        center_y=-3.0,
        radius=12.0,
        start_angle_deg=15.0,
        end_angle_deg=15.0,
    )

    assert len(points) >= ARC_POLYGONIZE_MIN_SEGMENTS + 1
    assert math.dist(points[0], points[-1]) <= 1e-9


def test_arc_to_points_deterministic_for_identical_inputs():
    kwargs = {
        "center_x": 1.5,
        "center_y": -7.0,
        "radius": 17.5,
        "start_angle_deg": 23.0,
        "end_angle_deg": 278.0,
        "max_chord_error_mm": CURVE_FLATTEN_TOLERANCE_MM,
        "min_segments": ARC_POLYGONIZE_MIN_SEGMENTS,
    }
    first = arc_to_points(**kwargs)
    second = arc_to_points(**kwargs)

    assert first == second
