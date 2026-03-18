#!/usr/bin/env python3

import pytest

from vrs_nesting.geometry.clean import GeometryCleanError, clean_ring, dedupe_and_prune_ring


def test_clean_ring_rejects_non_finite_points():
    with pytest.raises(GeometryCleanError, match="finite"):
        clean_ring([[0.0, 0.0], [10.0, 0.0], [float("nan"), 5.0]], where="ring")


def test_clean_ring_rejects_zero_area_collinear_ring():
    with pytest.raises(GeometryCleanError, match="near-zero area"):
        clean_ring([[0.0, 0.0], [5.0, 0.0], [10.0, 0.0]], where="ring")


def test_dedupe_and_prune_ring_drops_near_duplicate_closing_point():
    ring = dedupe_and_prune_ring(
        [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [1e-12, -1e-12]],
        min_edge_len=1e-6,
        where="ring",
    )

    assert len(ring) == 4
