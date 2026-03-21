from __future__ import annotations

import logging
import math
from typing import Any

from api.supabase_client import SupabaseClient, SupabaseHTTPError

logger = logging.getLogger("vrs_api.geometry_contour_classification")

_CONTOUR_ROLE_TO_KIND = {
    "outer": "outer",
    "hole": "inner",
}


def _is_closed(points: list[list[float]]) -> bool:
    """A contour is closed if the first and last points coincide."""
    if len(points) < 2:
        return False
    first = points[0]
    last = points[-1]
    return (
        abs(first[0] - last[0]) < 1e-9
        and abs(first[1] - last[1]) < 1e-9
    )


def _compute_area(points: list[list[float]]) -> float:
    """Shoelace formula for signed area, returns absolute value in mm2."""
    n = len(points)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += points[i][0] * points[j][1]
        area -= points[j][0] * points[i][1]
    return abs(area) / 2.0


def _compute_perimeter(points: list[list[float]]) -> float:
    """Sum of edge lengths in mm."""
    n = len(points)
    if n < 2:
        return 0.0
    total = 0.0
    for i in range(n):
        j = (i + 1) % n
        dx = points[j][0] - points[i][0]
        dy = points[j][1] - points[i][1]
        total += math.sqrt(dx * dx + dy * dy)
    return total


def _compute_bbox(points: list[list[float]]) -> dict[str, float]:
    """Axis-aligned bounding box from points."""
    if not points:
        return {"min_x": 0.0, "min_y": 0.0, "max_x": 0.0, "max_y": 0.0, "width": 0.0, "height": 0.0}
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    min_x = min(xs)
    min_y = min(ys)
    max_x = max(xs)
    max_y = max(ys)
    return {
        "min_x": min_x,
        "min_y": min_y,
        "max_x": max_x,
        "max_y": max_y,
        "width": max_x - min_x,
        "height": max_y - min_y,
    }


def classify_manufacturing_derivative_contours(
    *,
    supabase: SupabaseClient,
    access_token: str,
    geometry_derivative: dict[str, Any],
) -> dict[str, Any]:
    """Classify contours from a manufacturing_canonical derivative.

    Creates or updates geometry_contour_classes records for each contour
    in the derivative payload. Only processes manufacturing_canonical
    derivatives; skips all others.

    Returns a summary dict with classified count or skip reason.
    """
    derivative_id = str(geometry_derivative.get("id") or "").strip()
    if not derivative_id:
        raise ValueError("missing geometry derivative id")

    derivative_kind = str(geometry_derivative.get("derivative_kind") or "").strip()
    if derivative_kind != "manufacturing_canonical":
        return {
            "geometry_derivative_id": derivative_id,
            "classified_count": 0,
            "skipped_reason": f"derivative_kind is {derivative_kind or '<empty>'}, not manufacturing_canonical",
        }

    payload = geometry_derivative.get("derivative_jsonb")
    if not isinstance(payload, dict):
        raise ValueError("derivative_jsonb must be an object")

    contours = payload.get("contours")
    if not isinstance(contours, list):
        raise ValueError("derivative_jsonb.contours must be an array")

    classified_count = 0
    for contour in contours:
        if not isinstance(contour, dict):
            logger.warning("skipping non-dict contour in derivative %s", derivative_id)
            continue

        contour_index = contour.get("contour_index")
        if contour_index is None:
            logger.warning("skipping contour without contour_index in derivative %s", derivative_id)
            continue

        contour_role = str(contour.get("contour_role") or "").strip()
        contour_kind = _CONTOUR_ROLE_TO_KIND.get(contour_role, contour_role)

        points = contour.get("points")
        if not isinstance(points, list):
            points = []

        closed = _is_closed(points)
        area = _compute_area(points)
        perimeter = _compute_perimeter(points)
        bbox = _compute_bbox(points)

        metadata = {
            "source_contour_role": contour_role,
            "source_winding": str(contour.get("winding") or ""),
            "source_point_count": len(points),
        }

        row_payload = {
            "geometry_derivative_id": derivative_id,
            "contour_index": int(contour_index),
            "contour_kind": contour_kind,
            "feature_class": "default",
            "is_closed": closed,
            "area_mm2": round(area, 4),
            "perimeter_mm": round(perimeter, 4),
            "bbox_jsonb": bbox,
            "metadata_jsonb": metadata,
        }

        _upsert_contour_class(
            supabase=supabase,
            access_token=access_token,
            derivative_id=derivative_id,
            contour_index=int(contour_index),
            payload=row_payload,
        )
        classified_count += 1

    return {
        "geometry_derivative_id": derivative_id,
        "classified_count": classified_count,
        "skipped_reason": None,
    }


def _upsert_contour_class(
    *,
    supabase: SupabaseClient,
    access_token: str,
    derivative_id: str,
    contour_index: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Insert or update a contour class record (idempotent on unique constraint)."""
    params = {
        "select": "id",
        "geometry_derivative_id": f"eq.{derivative_id}",
        "contour_index": f"eq.{contour_index}",
        "limit": "1",
    }
    existing_rows = supabase.select_rows(
        table="app.geometry_contour_classes",
        access_token=access_token,
        params=params,
    )

    if existing_rows:
        existing_id = str(existing_rows[0].get("id") or "").strip()
        if not existing_id:
            raise ValueError(f"missing contour class id for derivative={derivative_id} index={contour_index}")
        update_payload = {k: v for k, v in payload.items() if k != "geometry_derivative_id" and k != "contour_index"}
        updated_rows = supabase.update_rows(
            table="app.geometry_contour_classes",
            access_token=access_token,
            payload=update_payload,
            filters={"id": f"eq.{existing_id}"},
        )
        if updated_rows:
            return updated_rows[0]
        return dict(payload, id=existing_id)

    try:
        return supabase.insert_row(
            table="app.geometry_contour_classes",
            access_token=access_token,
            payload=payload,
        )
    except SupabaseHTTPError as exc:
        logger.warning(
            "contour_class_insert_retry derivative_id=%s contour_index=%d error=%s",
            derivative_id,
            contour_index,
            str(exc).strip()[:500] or "insert failed",
        )
        rows_after_error = supabase.select_rows(
            table="app.geometry_contour_classes",
            access_token=access_token,
            params=params,
        )
        if not rows_after_error:
            raise
        existing_id = str(rows_after_error[0].get("id") or "").strip()
        if not existing_id:
            raise ValueError(f"missing contour class id for derivative={derivative_id} index={contour_index}") from exc
        update_payload = {k: v for k, v in payload.items() if k != "geometry_derivative_id" and k != "contour_index"}
        updated_rows = supabase.update_rows(
            table="app.geometry_contour_classes",
            access_token=access_token,
            payload=update_payload,
            filters={"id": f"eq.{existing_id}"},
        )
        if updated_rows:
            return updated_rows[0]
        return dict(payload, id=existing_id)
