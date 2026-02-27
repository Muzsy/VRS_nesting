#!/usr/bin/env python3

from __future__ import annotations

import json
import logging
import subprocess

import pytest
from shapely.geometry import Polygon

import vrs_nesting.geometry.offset as offset_mod
from vrs_nesting.geometry.offset import DEFAULT_MITRE_LIMIT, GeometryOffsetError, offset_part_geometry


def test_offset_part_geometry_calls_rust_inflate_parts(monkeypatch: pytest.MonkeyPatch):
    payload = {
        "outer_points_mm": [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]],
        "holes_points_mm": [],
    }
    captured: dict[str, object] = {}

    monkeypatch.delenv(offset_mod.PART_ENGINE_ENV, raising=False)
    monkeypatch.delenv(offset_mod.ALLOW_SHAPELY_FALLBACK_ENV, raising=False)
    monkeypatch.setattr(offset_mod, "_resolve_nesting_engine_bin", lambda: "/tmp/nesting_engine")

    def fake_run(
        cmd: list[str],
        *,
        input: str,
        capture_output: bool,
        text: bool,
        check: bool,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        captured["cmd"] = cmd
        captured["input"] = input
        captured["capture_output"] = capture_output
        captured["text"] = text
        captured["check"] = check
        captured["timeout"] = timeout
        response = {
            "version": "pipeline_v1",
            "parts": [
                {
                    "id": "part_0",
                    "status": "ok",
                    "inflated_outer_points_mm": [[-1.0, -1.0], [11.0, -1.0], [11.0, 11.0], [-1.0, 11.0]],
                    "inflated_holes_points_mm": [],
                    "diagnostics": [],
                }
            ],
        }
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(response), stderr="")

    monkeypatch.setattr(offset_mod.subprocess, "run", fake_run)

    out = offset_part_geometry(payload, spacing_mm=2.0)

    assert captured["cmd"] == ["/tmp/nesting_engine", "inflate-parts"]
    assert captured["capture_output"] is True
    assert captured["text"] is True
    assert captured["check"] is False
    request = json.loads(str(captured["input"]))
    assert request["version"] == "pipeline_v1"
    assert request["kerf_mm"] == pytest.approx(2.0)
    assert request["margin_mm"] == pytest.approx(0.0)
    assert request["spacing_mm"] == pytest.approx(2.0)
    assert request["parts"][0]["outer_points_mm"] == payload["outer_points_mm"]
    assert out["outer_points_mm"] == [[-1.0, -1.0], [11.0, -1.0], [11.0, 11.0], [-1.0, 11.0]]


def test_offset_part_geometry_self_intersect_status_raises(monkeypatch: pytest.MonkeyPatch):
    payload = {
        "outer_points_mm": [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]],
        "holes_points_mm": [],
    }
    monkeypatch.delenv(offset_mod.PART_ENGINE_ENV, raising=False)
    monkeypatch.delenv(offset_mod.ALLOW_SHAPELY_FALLBACK_ENV, raising=False)
    monkeypatch.setattr(offset_mod, "_resolve_nesting_engine_bin", lambda: "/tmp/nesting_engine")

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        response = {
            "version": "pipeline_v1",
            "parts": [
                {
                    "id": "part_0",
                    "status": "self_intersect",
                    "inflated_outer_points_mm": [],
                    "inflated_holes_points_mm": [],
                    "diagnostics": [{"code": "SELF_INTERSECT", "detail": "outer polygon self-intersects after inflate"}],
                }
            ],
        }
        return subprocess.CompletedProcess(["/tmp/nesting_engine", "inflate-parts"], 0, stdout=json.dumps(response), stderr="")

    monkeypatch.setattr(offset_mod.subprocess, "run", fake_run)

    with pytest.raises(GeometryOffsetError, match="GEO_RUST_SELF_INTERSECT"):
        offset_part_geometry(payload, spacing_mm=2.0)


def test_offset_part_geometry_hole_collapsed_does_not_crash(monkeypatch: pytest.MonkeyPatch):
    payload = {
        "outer_points_mm": [[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0]],
        "holes_points_mm": [[[8.0, 8.0], [12.0, 8.0], [12.0, 12.0], [8.0, 12.0]]],
    }
    monkeypatch.delenv(offset_mod.PART_ENGINE_ENV, raising=False)
    monkeypatch.delenv(offset_mod.ALLOW_SHAPELY_FALLBACK_ENV, raising=False)
    monkeypatch.setattr(offset_mod, "_resolve_nesting_engine_bin", lambda: "/tmp/nesting_engine")

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        response = {
            "version": "pipeline_v1",
            "parts": [
                {
                    "id": "part_0",
                    "status": "hole_collapsed",
                    "inflated_outer_points_mm": [[-1.0, -1.0], [21.0, -1.0], [21.0, 21.0], [-1.0, 21.0]],
                    "inflated_holes_points_mm": [],
                    "diagnostics": [{"code": "HOLE_COLLAPSED", "detail": "hole collapsed in inflated geometry"}],
                }
            ],
        }
        return subprocess.CompletedProcess(["/tmp/nesting_engine", "inflate-parts"], 0, stdout=json.dumps(response), stderr="")

    monkeypatch.setattr(offset_mod.subprocess, "run", fake_run)

    out = offset_part_geometry(payload, spacing_mm=2.0)
    assert out["holes_points_mm"] == []
    assert out["outer_points_mm"] == [[-1.0, -1.0], [21.0, -1.0], [21.0, 21.0], [-1.0, 21.0]]


def test_offset_part_geometry_explicit_shapely_engine_guardrail(monkeypatch: pytest.MonkeyPatch):
    assert DEFAULT_MITRE_LIMIT == pytest.approx(2.0)

    payload = {
        "outer_points_mm": [[0.0, 0.0], [1.0, 100.0], [2.0, 0.0]],
        "holes_points_mm": [],
    }
    monkeypatch.setenv(offset_mod.PART_ENGINE_ENV, offset_mod.ENGINE_SHAPELY)
    monkeypatch.setattr(offset_mod.subprocess, "run", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("rust path must not be called")))

    out = offset_part_geometry(payload, spacing_mm=2.0)
    poly = Polygon(out["outer_points_mm"])
    min_x, min_y, max_x, max_y = poly.bounds

    assert min_x < 0.0
    assert min_y < 0.0
    assert max_y <= 102.2


def test_stock_no_fallback_without_env(monkeypatch: pytest.MonkeyPatch):
    payload = {
        "outer_points_mm": [[0.0, 0.0], [100.0, 0.0], [100.0, 100.0], [0.0, 100.0]],
        "holes_points_mm": [],
    }

    monkeypatch.delenv(offset_mod.ALLOW_SHAPELY_FALLBACK_ENV, raising=False)

    def fake_rust(*args: object, **kwargs: object) -> dict[str, object]:
        raise GeometryOffsetError("GEO_RUST_TIMEOUT", "mocked timeout")

    monkeypatch.setattr(offset_mod, "_offset_stock_geometry_rust", fake_rust)
    monkeypatch.setattr(
        offset_mod,
        "_offset_stock_geometry_shapely",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("shapely fallback must remain disabled")),
    )

    with pytest.raises(GeometryOffsetError, match="GEO_RUST_TIMEOUT"):
        offset_mod.offset_stock_geometry(payload, margin_mm=1.0, spacing_mm=0.2)


def test_stock_fallback_with_env_warns(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture):
    payload = {
        "outer_points_mm": [[0.0, 0.0], [80.0, 0.0], [80.0, 60.0], [0.0, 60.0]],
        "holes_points_mm": [],
    }
    fallback_result = {
        "outer_points_mm": [[5.0, 5.0], [75.0, 5.0], [75.0, 55.0], [5.0, 55.0]],
        "holes_points_mm": [],
    }
    called = {"shapely": False}

    monkeypatch.setenv(offset_mod.ALLOW_SHAPELY_FALLBACK_ENV, "1")

    def fake_rust(*args: object, **kwargs: object) -> dict[str, object]:
        raise GeometryOffsetError("GEO_RUST_TIMEOUT", "mocked timeout")

    def fake_shapely(*args: object, **kwargs: object) -> dict[str, object]:
        called["shapely"] = True
        return fallback_result

    monkeypatch.setattr(offset_mod, "_offset_stock_geometry_rust", fake_rust)
    monkeypatch.setattr(offset_mod, "_offset_stock_geometry_shapely", fake_shapely)

    with caplog.at_level(logging.WARNING):
        out = offset_mod.offset_stock_geometry(payload, margin_mm=1.5, spacing_mm=0.2)

    assert called["shapely"] is True
    assert out == fallback_result
    assert offset_mod.ALLOW_SHAPELY_FALLBACK_ENV in caplog.text
    assert "GEO_RUST_TIMEOUT" in caplog.text


def test_stock_shapely_model_supports_positive_bin_offset():
    payload = {
        "outer_points_mm": [[0.0, 0.0], [100.0, 0.0], [100.0, 60.0], [0.0, 60.0]],
        "holes_points_mm": [],
    }

    out = offset_mod._offset_stock_geometry_shapely(payload, margin_mm=1.0, spacing_mm=4.0)
    min_x, min_y, max_x, max_y = offset_mod.polygon_bbox(out)

    assert min_x < 0.0
    assert min_y < 0.0
    assert max_x > 100.0
    assert max_y > 60.0


def test_stock_shapely_hole_expand_uses_spacing_half_only():
    payload = {
        "outer_points_mm": [[0.0, 0.0], [100.0, 0.0], [100.0, 100.0], [0.0, 100.0]],
        "holes_points_mm": [[[40.0, 40.0], [60.0, 40.0], [60.0, 60.0], [40.0, 60.0]]],
    }

    out = offset_mod._offset_stock_geometry_shapely(payload, margin_mm=10.0, spacing_mm=4.0)
    hole = out["holes_points_mm"][0]
    xs = [pt[0] for pt in hole]
    ys = [pt[1] for pt in hole]
    hole_w = max(xs) - min(xs)
    hole_h = max(ys) - min(ys)

    assert hole_w == pytest.approx(24.0, abs=0.2)
    assert hole_h == pytest.approx(24.0, abs=0.2)
