from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from api.supabase_client import SupabaseClient, SupabaseHTTPError

logger = logging.getLogger("vrs_api.geometry_derivative_generator")

_PRODUCER_VERSION = "geometry_derivative_generator.v1"
_NESTING_FORMAT_VERSION = "nesting_canonical.v1"
_VIEWER_FORMAT_VERSION = "viewer_outline.v1"
_MANUFACTURING_FORMAT_VERSION = "manufacturing_canonical.v1"


def _canonical_hash_sha256(payload: dict[str, Any]) -> str:
    canonical_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def _as_ring(raw: Any, *, where: str) -> list[list[float]]:
    if not isinstance(raw, list) or len(raw) < 3:
        raise ValueError(f"{where} must be a ring with at least 3 points")

    ring: list[list[float]] = []
    for idx, point in enumerate(raw):
        if not isinstance(point, list) or len(point) != 2:
            raise ValueError(f"{where}[{idx}] must be [x, y]")
        x, y = point
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise ValueError(f"{where}[{idx}] coordinates must be numeric")
        ring.append([float(x), float(y)])
    return ring


def _as_bbox(raw: Any, *, where: str) -> dict[str, float]:
    if not isinstance(raw, dict):
        raise ValueError(f"{where} must be an object")

    bbox: dict[str, float] = {}
    for key in ("min_x", "min_y", "max_x", "max_y", "width", "height"):
        value = raw.get(key)
        if not isinstance(value, (int, float)):
            raise ValueError(f"{where}.{key} must be numeric")
        bbox[key] = float(value)
    return bbox


def _load_canonical_geometry(geometry_revision: dict[str, Any]) -> tuple[list[list[float]], list[list[list[float]]], dict[str, float]]:
    canonical = geometry_revision.get("canonical_geometry_jsonb")
    if not isinstance(canonical, dict):
        raise ValueError("canonical_geometry_jsonb must be an object")

    outer_ring = _as_ring(canonical.get("outer_ring"), where="canonical_geometry_jsonb.outer_ring")

    hole_rings_raw = canonical.get("hole_rings")
    if not isinstance(hole_rings_raw, list):
        raise ValueError("canonical_geometry_jsonb.hole_rings must be an array")
    hole_rings = [
        _as_ring(ring_raw, where=f"canonical_geometry_jsonb.hole_rings[{idx}]")
        for idx, ring_raw in enumerate(hole_rings_raw)
    ]

    bbox = _as_bbox(canonical.get("bbox"), where="canonical_geometry_jsonb.bbox")
    return outer_ring, hole_rings, bbox


def _build_nesting_canonical_payload(
    *,
    geometry_revision: dict[str, Any],
    outer_ring: list[list[float]],
    hole_rings: list[list[list[float]]],
    bbox: dict[str, float],
) -> dict[str, Any]:
    return {
        "derivative_kind": "nesting_canonical",
        "format_version": _NESTING_FORMAT_VERSION,
        "units": "mm",
        "polygon": {
            "outer_ring": outer_ring,
            "hole_rings": hole_rings,
        },
        "bbox": bbox,
        "placement_hints": {
            "origin_ref": "bbox_min_corner",
            "rotation_unit": "deg",
        },
        "source_geometry_ref": {
            "geometry_revision_id": str(geometry_revision.get("id") or ""),
            "canonical_hash_sha256": str(geometry_revision.get("canonical_hash_sha256") or ""),
            "canonical_format_version": str(geometry_revision.get("canonical_format_version") or ""),
        },
    }


def _close_ring(ring: list[list[float]]) -> list[list[float]]:
    if not ring:
        return []
    closed = [list(point) for point in ring]
    if closed[0] != closed[-1]:
        closed.append(list(closed[0]))
    return closed


def _build_viewer_outline_payload(
    *,
    geometry_revision: dict[str, Any],
    outer_ring: list[list[float]],
    hole_rings: list[list[list[float]]],
    bbox: dict[str, float],
) -> dict[str, Any]:
    return {
        "derivative_kind": "viewer_outline",
        "format_version": _VIEWER_FORMAT_VERSION,
        "units": "mm",
        "outline": {
            "outer_polyline": _close_ring(outer_ring),
            "hole_outlines": [_close_ring(ring) for ring in hole_rings],
        },
        "bbox": bbox,
        "render_hints": {
            "default_stroke_px": 1.5,
            "fill_rule": "evenodd",
        },
        "source_geometry_ref": {
            "geometry_revision_id": str(geometry_revision.get("id") or ""),
            "canonical_hash_sha256": str(geometry_revision.get("canonical_hash_sha256") or ""),
            "canonical_format_version": str(geometry_revision.get("canonical_format_version") or ""),
        },
    }


def _build_manufacturing_canonical_payload(
    *,
    geometry_revision: dict[str, Any],
    outer_ring: list[list[float]],
    hole_rings: list[list[list[float]]],
    bbox: dict[str, float],
) -> dict[str, Any]:
    """Build a manufacturing-oriented contour derivative.

    This is structurally distinct from the nesting_canonical payload:
    - Top-level key is ``contours`` (not ``polygon``).
    - Each contour is typed as ``outer`` or ``hole`` with an explicit index.
    - Contour winding is documented (outer=CCW, hole=CW by convention).
    - No placement_hints (manufacturing consumers derive their own).
    """
    contours: list[dict[str, Any]] = [
        {
            "contour_index": 0,
            "contour_role": "outer",
            "winding": "ccw",
            "points": outer_ring,
        },
    ]
    for hole_idx, hole_ring in enumerate(hole_rings):
        contours.append({
            "contour_index": hole_idx + 1,
            "contour_role": "hole",
            "winding": "cw",
            "points": hole_ring,
        })

    return {
        "derivative_kind": "manufacturing_canonical",
        "format_version": _MANUFACTURING_FORMAT_VERSION,
        "units": "mm",
        "contours": contours,
        "contour_summary": {
            "outer_count": 1,
            "hole_count": len(hole_rings),
            "total_count": 1 + len(hole_rings),
        },
        "bbox": bbox,
        "source_geometry_ref": {
            "geometry_revision_id": str(geometry_revision.get("id") or ""),
            "canonical_hash_sha256": str(geometry_revision.get("canonical_hash_sha256") or ""),
            "canonical_format_version": str(geometry_revision.get("canonical_format_version") or ""),
        },
    }


def _upsert_derivative(
    *,
    supabase: SupabaseClient,
    access_token: str,
    geometry_revision_id: str,
    derivative_kind: str,
    producer_version: str,
    format_version: str,
    derivative_jsonb: dict[str, Any],
    source_geometry_hash_sha256: str,
) -> dict[str, Any]:
    derivative_hash_sha256 = _canonical_hash_sha256(derivative_jsonb)
    payload = {
        "geometry_revision_id": geometry_revision_id,
        "derivative_kind": derivative_kind,
        "producer_version": producer_version,
        "format_version": format_version,
        "derivative_jsonb": derivative_jsonb,
        "derivative_hash_sha256": derivative_hash_sha256,
        "source_geometry_hash_sha256": source_geometry_hash_sha256,
    }

    params = {
        "select": "id,geometry_revision_id,derivative_kind",
        "geometry_revision_id": f"eq.{geometry_revision_id}",
        "derivative_kind": f"eq.{derivative_kind}",
        "limit": "1",
    }
    existing_rows = supabase.select_rows(table="app.geometry_derivatives", access_token=access_token, params=params)

    if existing_rows:
        existing_id = str(existing_rows[0].get("id") or "").strip()
        if not existing_id:
            raise ValueError(f"missing derivative id for {derivative_kind}")
        updated_rows = supabase.update_rows(
            table="app.geometry_derivatives",
            access_token=access_token,
            payload={
                "producer_version": producer_version,
                "format_version": format_version,
                "derivative_jsonb": derivative_jsonb,
                "derivative_hash_sha256": derivative_hash_sha256,
                "source_geometry_hash_sha256": source_geometry_hash_sha256,
            },
            filters={"id": f"eq.{existing_id}"},
        )
        if updated_rows:
            return updated_rows[0]
        return dict(payload, id=existing_id)

    try:
        return supabase.insert_row(table="app.geometry_derivatives", access_token=access_token, payload=payload)
    except SupabaseHTTPError as exc:
        # Retry path for concurrent insert/upsert races on unique(geometry_revision_id, derivative_kind).
        logger.warning(
            "geometry_derivative_insert_retry geometry_revision_id=%s derivative_kind=%s error=%s",
            geometry_revision_id,
            derivative_kind,
            str(exc).strip()[:500] or "insert failed",
        )
        rows_after_error = supabase.select_rows(table="app.geometry_derivatives", access_token=access_token, params=params)
        if not rows_after_error:
            raise
        existing_id = str(rows_after_error[0].get("id") or "").strip()
        if not existing_id:
            raise ValueError(f"missing derivative id for {derivative_kind}") from exc
        updated_rows = supabase.update_rows(
            table="app.geometry_derivatives",
            access_token=access_token,
            payload={
                "producer_version": producer_version,
                "format_version": format_version,
                "derivative_jsonb": derivative_jsonb,
                "derivative_hash_sha256": derivative_hash_sha256,
                "source_geometry_hash_sha256": source_geometry_hash_sha256,
            },
            filters={"id": f"eq.{existing_id}"},
        )
        if updated_rows:
            return updated_rows[0]
        return dict(payload, id=existing_id)


def generate_h1_minimum_geometry_derivatives(
    *,
    supabase: SupabaseClient,
    access_token: str,
    geometry_revision: dict[str, Any],
) -> dict[str, Any]:
    geometry_revision_id = str(geometry_revision.get("id") or "").strip()
    if not geometry_revision_id:
        raise ValueError("missing geometry revision id")

    status = str(geometry_revision.get("status") or "").strip().lower()
    if status != "validated":
        return {
            "geometry_revision_id": geometry_revision_id,
            "generated": {},
            "skipped_reason": f"geometry status is {status or '<empty>'}",
        }

    source_geometry_hash_sha256 = str(geometry_revision.get("canonical_hash_sha256") or "").strip()
    if not source_geometry_hash_sha256:
        raise ValueError("missing canonical_hash_sha256 for derivative generation")

    outer_ring, hole_rings, bbox = _load_canonical_geometry(geometry_revision)

    nesting_payload = _build_nesting_canonical_payload(
        geometry_revision=geometry_revision,
        outer_ring=outer_ring,
        hole_rings=hole_rings,
        bbox=bbox,
    )
    viewer_payload = _build_viewer_outline_payload(
        geometry_revision=geometry_revision,
        outer_ring=outer_ring,
        hole_rings=hole_rings,
        bbox=bbox,
    )
    manufacturing_payload = _build_manufacturing_canonical_payload(
        geometry_revision=geometry_revision,
        outer_ring=outer_ring,
        hole_rings=hole_rings,
        bbox=bbox,
    )

    derivatives: dict[str, dict[str, Any]] = {}
    derivatives["nesting_canonical"] = _upsert_derivative(
        supabase=supabase,
        access_token=access_token,
        geometry_revision_id=geometry_revision_id,
        derivative_kind="nesting_canonical",
        producer_version=_PRODUCER_VERSION,
        format_version=_NESTING_FORMAT_VERSION,
        derivative_jsonb=nesting_payload,
        source_geometry_hash_sha256=source_geometry_hash_sha256,
    )
    derivatives["viewer_outline"] = _upsert_derivative(
        supabase=supabase,
        access_token=access_token,
        geometry_revision_id=geometry_revision_id,
        derivative_kind="viewer_outline",
        producer_version=_PRODUCER_VERSION,
        format_version=_VIEWER_FORMAT_VERSION,
        derivative_jsonb=viewer_payload,
        source_geometry_hash_sha256=source_geometry_hash_sha256,
    )
    derivatives["manufacturing_canonical"] = _upsert_derivative(
        supabase=supabase,
        access_token=access_token,
        geometry_revision_id=geometry_revision_id,
        derivative_kind="manufacturing_canonical",
        producer_version=_PRODUCER_VERSION,
        format_version=_MANUFACTURING_FORMAT_VERSION,
        derivative_jsonb=manufacturing_payload,
        source_geometry_hash_sha256=source_geometry_hash_sha256,
    )

    return {
        "geometry_revision_id": geometry_revision_id,
        "generated": derivatives,
        "skipped_reason": None,
    }
