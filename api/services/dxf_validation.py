from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import ezdxf

from api.services.file_ingest_metadata import download_storage_object_blob
from api.supabase_client import SupabaseClient

logger = logging.getLogger("vrs_api.dxf_validation")


def validate_dxf_file_async(
    *,
    supabase: SupabaseClient,
    access_token: str,
    bucket: str,
    file_object_id: str,
    storage_path: str,
) -> None:
    try:
        blob = download_storage_object_blob(
            supabase=supabase,
            access_token=access_token,
            storage_bucket=bucket,
            storage_path=storage_path,
            signed_url_ttl_s=600,
        )
        with tempfile.TemporaryDirectory(prefix="vrs_dxf_validate_") as tmp:
            tmp_path = Path(tmp) / "uploaded.dxf"
            tmp_path.write_bytes(blob)
            ezdxf.readfile(tmp_path)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "dxf_validation_failed file_object_id=%s bucket=%s storage_path=%s error=%s",
            file_object_id,
            bucket,
            storage_path,
            str(exc).strip()[:500] or "DXF validation failed",
        )
