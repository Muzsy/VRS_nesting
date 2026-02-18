from __future__ import annotations

import tempfile
from pathlib import Path

import ezdxf

from api.supabase_client import SupabaseClient, SupabaseHTTPError


def validate_dxf_file_async(
    *,
    supabase: SupabaseClient,
    access_token: str,
    bucket: str,
    project_file_id: str,
    storage_key: str,
) -> None:
    try:
        signed = supabase.create_signed_download_url(
            access_token=access_token,
            bucket=bucket,
            object_key=storage_key,
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

        supabase.update_rows(
            table="project_files",
            access_token=access_token,
            payload={"validation_status": "ok", "validation_error": None},
            filters={"id": f"eq.{project_file_id}"},
        )
    except Exception as exc:  # noqa: BLE001
        error_text = str(exc).strip()[:500] or "DXF validation failed"
        try:
            supabase.update_rows(
                table="project_files",
                access_token=access_token,
                payload={"validation_status": "error", "validation_error": error_text},
                filters={"id": f"eq.{project_file_id}"},
            )
        except Exception:
            return
