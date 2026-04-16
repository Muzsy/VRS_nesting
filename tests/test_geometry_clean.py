#!/usr/bin/env python3

import os

import pytest

from vrs_nesting.geometry.clean import (
    GeometryCleanError,
    RDP_SIMPLIFY_ENV_VAR,
    RDP_SIMPLIFY_MAX_TOL_MM,
    clean_ring,
    dedupe_and_prune_ring,
    rdp_tol_mm_from_env,
    simplify_ring_rdp,
)


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


# ---------------------------------------------------------------------------
# C1: RDP-simplify opt-in
# ---------------------------------------------------------------------------


def _dense_rectangle(width: float, height: float, steps_per_edge: int) -> list[list[float]]:
    """Axis-aligned rectangle with `steps_per_edge` interior collinear points."""
    pts: list[list[float]] = []
    for i in range(steps_per_edge):
        pts.append([width * i / steps_per_edge, 0.0])
    for i in range(steps_per_edge):
        pts.append([width, height * i / steps_per_edge])
    for i in range(steps_per_edge):
        pts.append([width - width * i / steps_per_edge, height])
    for i in range(steps_per_edge):
        pts.append([0.0, height - height * i / steps_per_edge])
    return pts


def test_simplify_ring_rdp_collapses_collinear_rectangle_edges():
    # 40-vertex rectangle (10 per edge) → RDP @ 0.2 mm must collapse to 4 corners
    ring_tuples = [(x, y) for x, y in _dense_rectangle(100.0, 50.0, steps_per_edge=10)]
    simplified = simplify_ring_rdp(ring_tuples, tol_mm=0.2)
    assert len(simplified) == 4
    # all 4 corners must be present (order-independent)
    as_set = {(round(x, 6), round(y, 6)) for x, y in simplified}
    assert as_set == {(0.0, 0.0), (100.0, 0.0), (100.0, 50.0), (0.0, 50.0)}


def test_simplify_ring_rdp_is_idempotent():
    ring_tuples = [(x, y) for x, y in _dense_rectangle(100.0, 50.0, steps_per_edge=10)]
    once = simplify_ring_rdp(ring_tuples, tol_mm=0.2)
    twice = simplify_ring_rdp(once, tol_mm=0.2)
    assert once == twice


def test_simplify_ring_rdp_preserves_signed_area_sign():
    # Both CCW and CW dense rectangles: orientation must be preserved.
    ccw = [(x, y) for x, y in _dense_rectangle(100.0, 50.0, steps_per_edge=10)]
    cw = list(reversed(ccw))

    def _area(pts: list[tuple[float, float]]) -> float:
        n = len(pts)
        s = 0.0
        for i in range(n):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % n]
            s += x1 * y2 - x2 * y1
        return 0.5 * s

    sim_ccw = simplify_ring_rdp(ccw, tol_mm=0.2)
    sim_cw = simplify_ring_rdp(cw, tol_mm=0.2)
    assert _area(sim_ccw) > 0
    assert _area(sim_cw) < 0


def test_simplify_ring_rdp_tol_zero_is_noop():
    ring_tuples = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    out = simplify_ring_rdp(ring_tuples, tol_mm=0.0)
    assert out == ring_tuples


def test_simplify_ring_rdp_falls_back_on_degenerate_collapse():
    # Sliver ring: all points nearly collinear → RDP with a generous tol
    # would collapse to ≤2 points; we require fallback to the input.
    ring_tuples = [(0.0, 0.0), (10.0, 1e-4), (20.0, 0.0), (10.0, -1e-4)]
    out = simplify_ring_rdp(ring_tuples, tol_mm=1.0)
    assert out == ring_tuples


def test_clean_ring_default_is_unchanged_without_simplify_tol():
    # Regression: clean_ring with no simplify_tol_mm must match prior behavior.
    ring_tuples = _dense_rectangle(100.0, 50.0, steps_per_edge=10)
    out = clean_ring(ring_tuples, min_edge_len=1e-6, ccw=True, where="t")
    assert len(out) == len(ring_tuples)


def test_clean_ring_with_simplify_tol_collapses_dense_rectangle():
    ring_tuples = _dense_rectangle(100.0, 50.0, steps_per_edge=10)
    out = clean_ring(
        ring_tuples,
        min_edge_len=1e-6,
        ccw=True,
        simplify_tol_mm=0.2,
        where="t",
    )
    assert len(out) == 4


def test_rdp_tol_from_env_accepts_valid_positive_tol(monkeypatch):
    monkeypatch.setenv(RDP_SIMPLIFY_ENV_VAR, "0.2")
    assert rdp_tol_mm_from_env() == pytest.approx(0.2)


def test_rdp_tol_from_env_rejects_non_positive(monkeypatch):
    for bad in ("0", "-0.1", "0.0"):
        monkeypatch.setenv(RDP_SIMPLIFY_ENV_VAR, bad)
        assert rdp_tol_mm_from_env() is None


def test_rdp_tol_from_env_rejects_non_finite(monkeypatch):
    for bad in ("nan", "inf", "-inf"):
        monkeypatch.setenv(RDP_SIMPLIFY_ENV_VAR, bad)
        assert rdp_tol_mm_from_env() is None


def test_rdp_tol_from_env_rejects_above_max(monkeypatch):
    above = RDP_SIMPLIFY_MAX_TOL_MM * 2
    monkeypatch.setenv(RDP_SIMPLIFY_ENV_VAR, str(above))
    assert rdp_tol_mm_from_env() is None


def test_rdp_tol_from_env_rejects_garbage(monkeypatch):
    for bad in ("", "   ", "abc", "1.0.0"):
        monkeypatch.setenv(RDP_SIMPLIFY_ENV_VAR, bad)
        assert rdp_tol_mm_from_env() is None


def test_rdp_tol_from_env_returns_none_when_unset(monkeypatch):
    monkeypatch.delenv(RDP_SIMPLIFY_ENV_VAR, raising=False)
    assert rdp_tol_mm_from_env() is None
