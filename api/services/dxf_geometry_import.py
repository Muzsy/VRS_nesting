from __future__ import annotations

import hashlib
import json
import logging
import tempfile
from pathlib import Path
from typing import Any

from api.services.geometry_contour_classification import classify_manufacturing_derivative_contours
from api.services.geometry_derivative_generator import generate_h1_minimum_geometry_derivatives
from api.services.file_ingest_metadata import download_storage_object_blob
from api.services.geometry_validation_report import create_geometry_validation_report
from api.supabase_client import SupabaseClient, SupabaseHTTPError
from vrs_nesting.dxf.importer import DxfImportError, PartRaw, import_part_raw
from vrs_nesting.geometry.clean import clean_ring

logger = logging.getLogger("vrs_api.dxf_geometry_import")

_CANONICAL_FORMAT_VERSION = "normalized_geometry.v1"
_IMPORTER_REF = "vrs_nesting.dxf.importer.import_part_raw"
_NORMALIZER_REF = "api.services.dxf_geometry_import._normalize_part_raw_geometry"
_MIN_EDGE_LEN_MM = 1e-6


def _rotate_ring_to_canonical_start(ring: list[list[float]]) -> list[list[float]]:
    if len(ring) < 3:
        raise ValueError("ring must contain at least 3 points")

    best_index = 0
    best_key: tuple[float, float, float, float] | None = None
    ring_len = len(ring)
    for idx, point in enumerate(ring):
        next_point = ring[(idx + 1) % ring_len]
        key = (float(point[0]), float(point[1]), float(next_point[0]), float(next_point[1]))
        if best_key is None or key < best_key:
            best_key = key
            best_index = idx
    return [list(point) for point in (ring[best_index:] + ring[:best_index])]


def _normalize_ring(
    *,
    points: list[list[float]],
    ccw: bool,
    where: str,
) -> list[list[float]]:
    cleaned = clean_ring(points, min_edge_len=_MIN_EDGE_LEN_MM, ccw=ccw, where=where)
    return _rotate_ring_to_canonical_start(cleaned)


def _ring_sort_key(ring: list[list[float]]) -> tuple[float, ...]:
    flattened: list[float] = []
    for point in ring:
        flattened.extend((float(point[0]), float(point[1])))
    return tuple(flattened)


def _compute_bbox_jsonb(
    *,
    outer_ring: list[list[float]],
    hole_rings: list[list[list[float]]],
) -> dict[str, float]:
    all_points: list[list[float]] = list(outer_ring)
    for ring in hole_rings:
        all_points.extend(ring)
    if not all_points:
        raise ValueError("missing geometry points for bbox")

    xs = [float(point[0]) for point in all_points]
    ys = [float(point[1]) for point in all_points]
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


def _normalize_part_raw_geometry(
    *,
    part_raw: PartRaw,
    storage_bucket: str,
    storage_path: str,
) -> tuple[dict[str, Any], dict[str, float]]:
    outer_ring = _normalize_ring(points=part_raw.outer_points_mm, ccw=True, where="outer_ring")
    hole_rings = [
        _normalize_ring(points=hole_points, ccw=False, where=f"hole_rings[{idx}]")
        for idx, hole_points in enumerate(part_raw.holes_points_mm)
    ]
    hole_rings.sort(key=_ring_sort_key)
    bbox = _compute_bbox_jsonb(outer_ring=outer_ring, hole_rings=hole_rings)

    payload = {
        "geometry_role": "part",
        "format_version": _CANONICAL_FORMAT_VERSION,
        "units": "mm",
        "outer_ring": outer_ring,
        "hole_rings": hole_rings,
        "bbox": bbox,
        "normalizer_meta": {
            "normalizer": _NORMALIZER_REF,
            "normalizer_version": _CANONICAL_FORMAT_VERSION,
            "importer": _IMPORTER_REF,
            "ring_policy": {
                "outer_orientation": "ccw",
                "hole_orientation": "cw",
                "start_point_rule": "lexicographic_min_xy_then_next",
                "min_edge_len_mm": _MIN_EDGE_LEN_MM,
            },
            "source_entities_count": len(part_raw.source_entities),
        },
        "source_lineage": {
            "storage_bucket": storage_bucket,
            "storage_path": storage_path,
            "source_object_ref": f"{storage_bucket}/{storage_path}",
            "importer": _IMPORTER_REF,
            "normalizer": _NORMALIZER_REF,
        },
    }
    return payload, bbox


def _canonical_hash_sha256(payload: dict[str, Any]) -> str:
    canonical_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def build_canonical_geometry_from_part_raw(
    *,
    part_raw: PartRaw,
    storage_bucket: str,
    storage_path: str,
) -> tuple[dict[str, Any], dict[str, float]]:
    """Public pure helper for canonical geometry + bbox from importer output."""
    return _normalize_part_raw_geometry(
        part_raw=part_raw,
        storage_bucket=storage_bucket,
        storage_path=storage_path,
    )


def canonical_hash_sha256(payload: dict[str, Any]) -> str:
    """Public pure helper for canonical JSON hash generation."""
    return _canonical_hash_sha256(payload)


def build_canonical_geometry_probe_from_part_raw(
    *,
    part_raw: PartRaw,
    storage_bucket: str,
    storage_path: str,
) -> dict[str, Any]:
    """Return canonical payload + bbox + hash in one deterministic bundle."""
    canonical_geometry_jsonb, bbox_jsonb = build_canonical_geometry_from_part_raw(
        part_raw=part_raw,
        storage_bucket=storage_bucket,
        storage_path=storage_path,
    )
    return {
        "canonical_format_version": _CANONICAL_FORMAT_VERSION,
        "canonical_geometry_jsonb": canonical_geometry_jsonb,
        "bbox_jsonb": bbox_jsonb,
        "canonical_hash_sha256": canonical_hash_sha256(canonical_geometry_jsonb),
    }


def _next_revision_no(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
    source_file_object_id: str,
) -> int:
    params = {
        "select": "revision_no",
        "project_id": f"eq.{project_id}",
        "source_file_object_id": f"eq.{source_file_object_id}",
        "order": "revision_no.desc",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.geometry_revisions", access_token=access_token, params=params)
    if not rows:
        return 1

    latest = rows[0].get("revision_no")
    try:
        latest_revision_no = int(latest)
    except (TypeError, ValueError):
        latest_revision_no = 0
    if latest_revision_no < 0:
        latest_revision_no = 0
    return latest_revision_no + 1


def import_source_dxf_geometry_revision(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
    source_file_object_id: str,
    storage_bucket: str,
    storage_path: str,
    source_hash_sha256: str,
    created_by: str,
    signed_url_ttl_s: int,
) -> dict[str, Any]:
    blob = download_storage_object_blob(
        supabase=supabase,
        access_token=access_token,
        storage_bucket=storage_bucket,
        storage_path=storage_path,
        signed_url_ttl_s=signed_url_ttl_s,
    )
    with tempfile.TemporaryDirectory(prefix="vrs_dxf_geometry_import_") as tmp:
        tmp_path = Path(tmp) / "source.dxf"
        tmp_path.write_bytes(blob)
        part_raw = import_part_raw(str(tmp_path))

    canonical_geometry_jsonb, bbox_jsonb = build_canonical_geometry_from_part_raw(
        part_raw=part_raw,
        storage_bucket=storage_bucket,
        storage_path=storage_path,
    )
    canonical_hash_value = canonical_hash_sha256(canonical_geometry_jsonb)
    source_hash = source_hash_sha256.strip()
    if not source_hash:
        raise ValueError("missing source_hash_sha256")
    revision_no = _next_revision_no(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id,
        source_file_object_id=source_file_object_id,
    )

    payload = {
        "project_id": project_id,
        "source_file_object_id": source_file_object_id,
        "geometry_role": "part",
        "revision_no": revision_no,
        "status": "parsed",
        "canonical_format_version": _CANONICAL_FORMAT_VERSION,
        "canonical_geometry_jsonb": canonical_geometry_jsonb,
        "canonical_hash_sha256": canonical_hash_value,
        "source_hash_sha256": source_hash,
        "bbox_jsonb": bbox_jsonb,
        "created_by": created_by,
    }
    geometry_revision = supabase.insert_row(table="app.geometry_revisions", access_token=access_token, payload=payload)
    validation_result = create_geometry_validation_report(
        supabase=supabase,
        access_token=access_token,
        geometry_revision=geometry_revision,
    )
    validated_geometry_revision = validation_result.get("geometry_revision")
    current_geometry_revision = geometry_revision
    if isinstance(validated_geometry_revision, dict):
        current_geometry_revision = validated_geometry_revision

    derivative_result = generate_h1_minimum_geometry_derivatives(
        supabase=supabase,
        access_token=access_token,
        geometry_revision=current_geometry_revision,
    )

    # H2-E2-T2: classify contours for manufacturing_canonical derivative
    generated = derivative_result.get("generated")
    if isinstance(generated, dict):
        mfg_derivative = generated.get("manufacturing_canonical")
        if isinstance(mfg_derivative, dict) and mfg_derivative.get("id"):
            try:
                classify_manufacturing_derivative_contours(
                    supabase=supabase,
                    access_token=access_token,
                    geometry_derivative=mfg_derivative,
                )
            except Exception:
                logger.warning(
                    "contour_classification_failed geometry_revision_id=%s",
                    str(current_geometry_revision.get("id") or ""),
                    exc_info=True,
                )

    return current_geometry_revision


def import_source_dxf_geometry_revision_async(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
    source_file_object_id: str,
    storage_bucket: str,
    storage_path: str,
    source_hash_sha256: str,
    created_by: str,
    signed_url_ttl_s: int,
) -> None:
    try:
        import_source_dxf_geometry_revision(
            supabase=supabase,
            access_token=access_token,
            project_id=project_id,
            source_file_object_id=source_file_object_id,
            storage_bucket=storage_bucket,
            storage_path=storage_path,
            source_hash_sha256=source_hash_sha256,
            created_by=created_by,
            signed_url_ttl_s=signed_url_ttl_s,
        )
    except (DxfImportError, SupabaseHTTPError, ValueError) as exc:
        logger.warning(
            "geometry_import_failed source_file_object_id=%s bucket=%s storage_path=%s error=%s",
            source_file_object_id,
            storage_bucket,
            storage_path,
            str(exc).strip()[:500] or "geometry import failed",
        )
