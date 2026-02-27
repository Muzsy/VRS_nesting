#!/usr/bin/env python3
"""Spacing/margin offset helpers for prepared part and stock geometries."""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union

DEFAULT_MITRE_LIMIT = 2.0
DEFAULT_RUST_TIMEOUT_SEC = 10.0

PART_ENGINE_ENV = "VRS_OFFSET_PART_ENGINE"
ALLOW_SHAPELY_FALLBACK_ENV = "VRS_OFFSET_ALLOW_SHAPELY_FALLBACK"
RUST_BIN_ENV = "VRS_NESTING_ENGINE_BIN"
SHARED_RUST_BIN_ENV = "NESTING_ENGINE_BIN"
RUST_TIMEOUT_ENV = "VRS_NESTING_ENGINE_TIMEOUT_SEC"

ENGINE_RUST = "rust"
ENGINE_SHAPELY = "shapely"

STATUS_OK = "ok"
STATUS_HOLE_COLLAPSED = "hole_collapsed"
STATUS_SELF_INTERSECT = "self_intersect"
STATUS_ERROR = "error"

_LOG = logging.getLogger(__name__)


class GeometryOffsetError(ValueError):
    """Deterministic geometry offset error with stable code + message."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _env_is_truthy(name: str) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _part_offset_engine() -> str:
    value = os.environ.get(PART_ENGINE_ENV, ENGINE_RUST).strip().lower()
    if value in {ENGINE_RUST, ENGINE_SHAPELY}:
        return value
    raise GeometryOffsetError(
        "GEO_ENGINE_VALUE",
        f"{PART_ENGINE_ENV} must be '{ENGINE_RUST}' or '{ENGINE_SHAPELY}'",
    )


def _rust_timeout_sec() -> float:
    raw = os.environ.get(RUST_TIMEOUT_ENV, "").strip()
    if not raw:
        return DEFAULT_RUST_TIMEOUT_SEC
    try:
        timeout_sec = float(raw)
    except ValueError as exc:  # pragma: no cover - defensive conversion path
        raise GeometryOffsetError("GEO_PARAM_TYPE", f"{RUST_TIMEOUT_ENV} must be numeric") from exc
    if timeout_sec <= 0:
        raise GeometryOffsetError("GEO_PARAM_RANGE", f"{RUST_TIMEOUT_ENV} must be > 0")
    return timeout_sec


def _resolve_bin_candidate(candidate: str) -> str | None:
    resolved = shutil.which(candidate)
    if resolved:
        return str(Path(resolved).resolve())
    path = Path(candidate)
    if path.is_file() and os.access(path, os.X_OK):
        return str(path.resolve())
    return None


def _resolve_nesting_engine_bin() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    check_release_path = repo_root / "rust" / "nesting_engine" / "target" / "release" / "nesting_engine"
    candidates: list[str] = []
    for env_name in (RUST_BIN_ENV, SHARED_RUST_BIN_ENV):
        env_value = os.environ.get(env_name, "").strip()
        if env_value:
            candidates.append(env_value)
    candidates.append(str(check_release_path))
    candidates.append("nesting_engine")

    for candidate in candidates:
        resolved = _resolve_bin_candidate(candidate)
        if resolved:
            return resolved

    raise GeometryOffsetError(
        "GEO_RUST_BIN_NOT_FOUND",
        "nesting_engine binary not found; set VRS_NESTING_ENGINE_BIN or NESTING_ENGINE_BIN",
    )


def _to_closed_ring(points: Any, where: str) -> list[tuple[float, float]]:
    if not isinstance(points, list):
        raise GeometryOffsetError("GEO_POLYGON_TYPE", f"{where} must be list")
    ring: list[tuple[float, float]] = []
    for idx, point in enumerate(points):
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise GeometryOffsetError("GEO_POLYGON_TYPE", f"{where}[{idx}] must be [x, y]")
        x, y = point
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise GeometryOffsetError("GEO_POLYGON_TYPE", f"{where}[{idx}] coordinates must be numeric")
        ring.append((float(x), float(y)))

    if len(ring) < 3:
        raise GeometryOffsetError("GEO_POLYGON_RANGE", f"{where} must have at least 3 points")

    if ring[0] != ring[-1]:
        ring.append(ring[0])
    return ring


def _to_open_ring(points: Any, where: str) -> list[list[float]]:
    closed = _to_closed_ring(points, where)
    return [[x, y] for x, y in closed[:-1]]


def _as_polygon(outer_points: Any, holes_points: Any, where: str) -> Polygon:
    outer = _to_closed_ring(outer_points, f"{where}.outer")

    holes: list[list[tuple[float, float]]] = []
    if holes_points is not None:
        if not isinstance(holes_points, list):
            raise GeometryOffsetError("GEO_POLYGON_TYPE", f"{where}.holes must be list")
        for idx, hole in enumerate(holes_points):
            holes.append(_to_closed_ring(hole, f"{where}.holes[{idx}]"))

    polygon = Polygon(outer, holes)
    if polygon.is_empty or not polygon.is_valid or polygon.area <= 0:
        raise GeometryOffsetError("GEO_POLYGON_INVALID", f"{where} polygon invalid or empty")
    return polygon


def _largest_polygon(geom: Any, where: str) -> Polygon:
    if geom is None or geom.is_empty:
        raise GeometryOffsetError("GEO_OFFSET_EMPTY", f"{where} geometry became empty after offset")

    if isinstance(geom, Polygon):
        return geom

    if isinstance(geom, MultiPolygon):
        biggest = max(geom.geoms, key=lambda p: p.area, default=None)
        if biggest is None or biggest.is_empty:
            raise GeometryOffsetError("GEO_OFFSET_EMPTY", f"{where} multipolygon has no usable area")
        return biggest

    if hasattr(geom, "geoms"):
        polys = [g for g in geom.geoms if isinstance(g, Polygon)]
        if not polys:
            raise GeometryOffsetError("GEO_OFFSET_EMPTY", f"{where} has no polygon output")
        return max(polys, key=lambda p: p.area)

    raise GeometryOffsetError("GEO_OFFSET_TYPE", f"{where} returned unsupported geometry type")


def _polygon_to_payload(poly: Polygon) -> dict[str, Any]:
    outer = [[float(x), float(y)] for x, y in list(poly.exterior.coords)[:-1]]
    holes = [
        [[float(x), float(y)] for x, y in list(ring.coords)[:-1]]
        for ring in poly.interiors
    ]
    return {
        "outer_points_mm": outer,
        "holes_points_mm": holes,
    }


def _diagnostic_detail(diag: Any) -> str:
    if isinstance(diag, list) and diag and isinstance(diag[0], dict):
        detail = diag[0].get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail.strip()
    return ""


def _diagnostic_code(diag: Any) -> str:
    if isinstance(diag, list) and diag and isinstance(diag[0], dict):
        code = diag[0].get("code")
        if isinstance(code, str) and code.strip():
            return code.strip()
    return ""


def _rust_request_part(payload: dict[str, Any]) -> dict[str, Any]:
    outer = _to_open_ring(payload.get("outer_points_mm"), "part.outer")
    holes_raw = payload.get("holes_points_mm", [])
    if holes_raw is None:
        holes_raw = []
    if not isinstance(holes_raw, list):
        raise GeometryOffsetError("GEO_POLYGON_TYPE", "part.holes_points_mm must be list")
    holes = [_to_open_ring(hole, f"part.holes[{idx}]") for idx, hole in enumerate(holes_raw)]
    return {
        "id": "part_0",
        "outer_points_mm": outer,
        "holes_points_mm": holes,
    }


def _rust_request_stock(payload: dict[str, Any]) -> dict[str, Any]:
    outer = _to_open_ring(payload.get("outer_points_mm"), "stock.outer")
    holes_raw = payload.get("holes_points_mm", [])
    if holes_raw is None:
        holes_raw = []
    if not isinstance(holes_raw, list):
        raise GeometryOffsetError("GEO_POLYGON_TYPE", "stock.holes_points_mm must be list")
    holes = [_to_open_ring(hole, f"stock.holes[{idx}]") for idx, hole in enumerate(holes_raw)]
    return {
        "id": "stock_0",
        "outer_points_mm": outer,
        "holes_points_mm": holes,
    }


def _parse_rust_part_response(response_payload: Any) -> dict[str, Any]:
    if not isinstance(response_payload, dict):
        raise GeometryOffsetError("GEO_RUST_SCHEMA", "inflate-parts response must be object")
    parts = response_payload.get("parts")
    if not isinstance(parts, list) or len(parts) != 1 or not isinstance(parts[0], dict):
        raise GeometryOffsetError("GEO_RUST_SCHEMA", "inflate-parts response.parts must contain one object")

    part = parts[0]
    status = part.get("status")
    if not isinstance(status, str):
        raise GeometryOffsetError("GEO_RUST_SCHEMA", "inflate-parts part.status must be string")

    diagnostics = part.get("diagnostics", [])
    detail = _diagnostic_detail(diagnostics)
    code = _diagnostic_code(diagnostics)

    if status == STATUS_SELF_INTERSECT:
        if detail:
            raise GeometryOffsetError("GEO_RUST_SELF_INTERSECT", detail)
        raise GeometryOffsetError("GEO_RUST_SELF_INTERSECT", "Rust inflate returned self_intersect status")

    if status not in {STATUS_OK, STATUS_HOLE_COLLAPSED}:
        suffix = f" code={code}" if code else ""
        detail_msg = f" detail={detail}" if detail else ""
        raise GeometryOffsetError("GEO_RUST_STATUS", f"Rust inflate status={status}{suffix}{detail_msg}")

    poly = _as_polygon(
        part.get("inflated_outer_points_mm"),
        part.get("inflated_holes_points_mm", []),
        f"part.rust.{status}",
    )
    if status == STATUS_HOLE_COLLAPSED:
        _LOG.warning("offset_part_geometry: rust returned hole_collapsed; continuing with returned polygon")
    return _polygon_to_payload(poly)


def _parse_rust_stock_response(response_payload: Any) -> dict[str, Any]:
    if not isinstance(response_payload, dict):
        raise GeometryOffsetError("GEO_RUST_SCHEMA", "inflate-parts response must be object")
    stocks = response_payload.get("stocks")
    if not isinstance(stocks, list) or len(stocks) != 1 or not isinstance(stocks[0], dict):
        raise GeometryOffsetError("GEO_RUST_SCHEMA", "inflate-parts response.stocks must contain one object")

    stock = stocks[0]
    status = stock.get("status")
    if not isinstance(status, str):
        raise GeometryOffsetError("GEO_RUST_SCHEMA", "inflate-parts stock.status must be string")

    diagnostics = stock.get("diagnostics", [])
    detail = _diagnostic_detail(diagnostics)
    code = _diagnostic_code(diagnostics)

    if status == STATUS_SELF_INTERSECT:
        if detail:
            raise GeometryOffsetError("GEO_RUST_SELF_INTERSECT", detail)
        raise GeometryOffsetError("GEO_RUST_SELF_INTERSECT", "Rust stock offset returned self_intersect status")
    if status == STATUS_ERROR:
        suffix = f" code={code}" if code else ""
        detail_msg = f" detail={detail}" if detail else ""
        raise GeometryOffsetError("GEO_RUST_STATUS", f"Rust stock offset status=error{suffix}{detail_msg}")
    if status != STATUS_OK:
        suffix = f" code={code}" if code else ""
        detail_msg = f" detail={detail}" if detail else ""
        raise GeometryOffsetError("GEO_RUST_STATUS", f"Rust stock offset status={status}{suffix}{detail_msg}")

    poly = _as_polygon(
        stock.get("usable_outer_points_mm"),
        stock.get("usable_holes_points_mm", []),
        "stock.rust.ok",
    )
    return _polygon_to_payload(poly)


def _run_rust_pipeline(request: dict[str, Any]) -> dict[str, Any]:
    req_json = json.dumps(request, separators=(",", ":"), ensure_ascii=False)
    bin_path = _resolve_nesting_engine_bin()
    timeout_sec = _rust_timeout_sec()

    try:
        proc = subprocess.run(
            [bin_path, "inflate-parts"],
            input=req_json,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired as exc:
        raise GeometryOffsetError(
            "GEO_RUST_TIMEOUT",
            f"nesting_engine inflate-parts timed out after {timeout_sec}s",
        ) from exc
    except OSError as exc:
        raise GeometryOffsetError("GEO_RUST_EXEC", f"nesting_engine inflate-parts failed to start: {exc}") from exc

    if proc.returncode != 0:
        stderr = proc.stderr.strip() if proc.stderr else ""
        detail = f": {stderr}" if stderr else ""
        raise GeometryOffsetError(
            "GEO_RUST_EXIT",
            f"nesting_engine inflate-parts exited with {proc.returncode}{detail}",
        )

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise GeometryOffsetError("GEO_RUST_JSON", f"nesting_engine inflate-parts stdout parse failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise GeometryOffsetError("GEO_RUST_SCHEMA", "inflate-parts response must be object")
    return payload


def _offset_part_geometry_rust(
    payload: dict[str, Any],
    *,
    spacing_mm: float,
) -> dict[str, Any]:
    # kerf_mm remains for legacy compatibility; spacing_mm is the canonical clearance input.
    request = {
        "version": "pipeline_v1",
        "kerf_mm": float(spacing_mm),
        "margin_mm": 0.0,
        "spacing_mm": float(spacing_mm),
        "parts": [_rust_request_part(payload)],
        "stocks": [],
    }
    response_payload = _run_rust_pipeline(request)
    return _parse_rust_part_response(response_payload)


def _offset_part_geometry_shapely(
    payload: dict[str, Any],
    *,
    spacing_mm: float,
) -> dict[str, Any]:
    base = _as_polygon(payload.get("outer_points_mm"), payload.get("holes_points_mm", []), "part")
    dist = float(spacing_mm) / 2.0
    expanded = base.buffer(dist, join_style="mitre", mitre_limit=DEFAULT_MITRE_LIMIT)
    poly = _largest_polygon(expanded, "part")
    return _polygon_to_payload(poly)


def _offset_stock_geometry_rust(
    payload: dict[str, Any],
    *,
    margin_mm: float,
    spacing_mm: float,
) -> dict[str, Any]:
    # kerf_mm remains for legacy compatibility; spacing_mm is the canonical clearance input.
    request = {
        "version": "pipeline_v1",
        "kerf_mm": float(spacing_mm),
        "margin_mm": float(margin_mm),
        "spacing_mm": float(spacing_mm),
        "parts": [],
        "stocks": [_rust_request_stock(payload)],
    }
    response_payload = _run_rust_pipeline(request)
    return _parse_rust_stock_response(response_payload)


def _offset_stock_geometry_shapely(
    payload: dict[str, Any],
    *,
    margin_mm: float,
    spacing_mm: float,
) -> dict[str, Any]:
    inflate_delta = float(spacing_mm) / 2.0
    bin_offset = inflate_delta - float(margin_mm)
    base_outer = _as_polygon(payload.get("outer_points_mm"), [], "stock.outer")

    usable_outer = _largest_polygon(
        base_outer.buffer(bin_offset, join_style="mitre", mitre_limit=DEFAULT_MITRE_LIMIT),
        "stock.outer",
    )

    holes_payload = payload.get("holes_points_mm", [])
    if holes_payload is None:
        holes_payload = []
    if not isinstance(holes_payload, list):
        raise GeometryOffsetError("GEO_POLYGON_TYPE", "stock.holes_points_mm must be list")

    expanded_holes = []
    for idx, hole in enumerate(holes_payload):
        hpoly = _as_polygon(hole, [], f"stock.hole[{idx}]")
        expanded_holes.append(
            hpoly.buffer(inflate_delta, join_style="mitre", mitre_limit=DEFAULT_MITRE_LIMIT)
        )

    if expanded_holes:
        usable = usable_outer.difference(unary_union(expanded_holes))
    else:
        usable = usable_outer

    poly = _largest_polygon(usable, "stock.usable")
    return _polygon_to_payload(poly)


def polygon_bbox(payload: dict[str, Any]) -> tuple[float, float, float, float]:
    outer = payload.get("outer_points_mm")
    if not isinstance(outer, list) or not outer:
        raise GeometryOffsetError("GEO_POLYGON_TYPE", "outer_points_mm must be non-empty list")
    ring = _to_closed_ring(outer, "bbox.outer")
    xs = [pt[0] for pt in ring[:-1]]
    ys = [pt[1] for pt in ring[:-1]]
    return min(xs), min(ys), max(xs), max(ys)


def offset_part_geometry(
    payload: dict[str, Any],
    *,
    spacing_mm: float,
) -> dict[str, Any]:
    if spacing_mm < 0:
        raise GeometryOffsetError("GEO_PARAM_RANGE", "spacing_mm must be >= 0")

    if _part_offset_engine() == ENGINE_SHAPELY:
        _LOG.warning("offset_part_geometry: explicit shapely engine selected via %s", PART_ENGINE_ENV)
        return _offset_part_geometry_shapely(payload, spacing_mm=spacing_mm)

    try:
        return _offset_part_geometry_rust(payload, spacing_mm=spacing_mm)
    except GeometryOffsetError as exc:
        if exc.code == "GEO_RUST_SELF_INTERSECT":
            raise
        if exc.code.startswith("GEO_RUST_") and _env_is_truthy(ALLOW_SHAPELY_FALLBACK_ENV):
            _LOG.warning(
                "offset_part_geometry: rust path failed (%s), using explicit shapely fallback via %s",
                exc.code,
                ALLOW_SHAPELY_FALLBACK_ENV,
            )
            return _offset_part_geometry_shapely(payload, spacing_mm=spacing_mm)
        raise


def offset_stock_geometry(
    payload: dict[str, Any],
    *,
    margin_mm: float,
    spacing_mm: float,
) -> dict[str, Any]:
    if margin_mm < 0:
        raise GeometryOffsetError("GEO_PARAM_RANGE", "margin_mm must be >= 0")
    if spacing_mm < 0:
        raise GeometryOffsetError("GEO_PARAM_RANGE", "spacing_mm must be >= 0")

    try:
        return _offset_stock_geometry_rust(payload, margin_mm=margin_mm, spacing_mm=spacing_mm)
    except GeometryOffsetError as exc:
        if exc.code == "GEO_RUST_SELF_INTERSECT":
            raise
        if exc.code.startswith("GEO_RUST_") and _env_is_truthy(ALLOW_SHAPELY_FALLBACK_ENV):
            _LOG.warning(
                "offset_stock_geometry: rust path failed (%s), using explicit shapely fallback via %s",
                exc.code,
                ALLOW_SHAPELY_FALLBACK_ENV,
            )
            return _offset_stock_geometry_shapely(payload, margin_mm=margin_mm, spacing_mm=spacing_mm)
        raise
