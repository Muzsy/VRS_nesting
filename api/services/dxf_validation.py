from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import ezdxf

from api.supabase_client import SupabaseClient, SupabaseHTTPError

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
        signed = supabase.create_signed_download_url(
            access_token=access_token,
            bucket=bucket,
            object_key=storage_path,
            expires_in=600,
        )
        download_url = str(signed.get("download_url", "")).strip()
        if not download_url:
            raise SupabaseHTTPError("missing signed download url for dxf validation")

        blob = supabase.download_signed_object(signed_url=download_url)
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
