#!/usr/bin/env python3

from __future__ import annotations

import pytest
from shapely.geometry import Polygon

from vrs_nesting.geometry.offset import DEFAULT_MITRE_LIMIT, offset_part_geometry


def test_offset_part_geometry_uses_explicit_mitre_limit_guardrail():
    assert DEFAULT_MITRE_LIMIT == pytest.approx(2.0)

    payload = {
        "outer_points_mm": [[0.0, 0.0], [1.0, 100.0], [2.0, 0.0]],
        "holes_points_mm": [],
    }

    out = offset_part_geometry(payload, spacing_mm=2.0)
    poly = Polygon(out["outer_points_mm"])
    min_x, min_y, max_x, max_y = poly.bounds

    assert min_x < 0.0
    assert min_y < 0.0
    # With mitre_limit=2 and dist=1, spike cap is bounded around y=102.
    assert max_y <= 102.2
