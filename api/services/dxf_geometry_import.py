from __future__ import annotations

import hashlib
import json
import logging
import tempfile
from pathlib import Path
from typing import Any

from api.services.file_ingest_metadata import download_storage_object_blob
from api.supabase_client import SupabaseClient, SupabaseHTTPError
from vrs_nesting.dxf.importer import DxfImportError, PartRaw, import_part_raw

logger = logging.getLogger("vrs_api.dxf_geometry_import")

_CANONICAL_FORMAT_VERSION = "part_raw.v1"
_IMPORTER_REF = "vrs_nesting.dxf.importer.import_part_raw"


def _build_canonical_geometry_payload(
    *,
    part_raw: PartRaw,
    storage_bucket: str,
    storage_path: str,
) -> dict[str, Any]:
    return {
        "geometry_role": "part",
        "format": _CANONICAL_FORMAT_VERSION,
        "outer_points_mm": part_raw.outer_points_mm,
        "holes_points_mm": part_raw.holes_points_mm,
        "source_lineage": {
            "storage_bucket": storage_bucket,
            "storage_path": storage_path,
            "importer": _IMPORTER_REF,
            "importer_source_path": part_raw.source_path,
        },
    }


def _canonical_hash_sha256(payload: dict[str, Any]) -> str:
    canonical_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def _compute_bbox_jsonb(part_raw: PartRaw) -> dict[str, float]:
    all_points: list[list[float]] = list(part_raw.outer_points_mm)
    for ring in part_raw.holes_points_mm:
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

    canonical_geometry_jsonb = _build_canonical_geometry_payload(
        part_raw=part_raw,
        storage_bucket=storage_bucket,
        storage_path=storage_path,
    )
    canonical_hash_sha256 = _canonical_hash_sha256(canonical_geometry_jsonb)
    bbox_jsonb = _compute_bbox_jsonb(part_raw)
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
        "canonical_hash_sha256": canonical_hash_sha256,
        "source_hash_sha256": source_hash_sha256.strip(),
        "bbox_jsonb": bbox_jsonb,
        "created_by": created_by,
    }
    return supabase.insert_row(table="app.geometry_revisions", access_token=access_token, payload=payload)


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
