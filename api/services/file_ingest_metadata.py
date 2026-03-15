from __future__ import annotations

import hashlib
import mimetypes
from dataclasses import dataclass
from pathlib import PurePosixPath

from api.supabase_client import SupabaseClient, SupabaseHTTPError

_MIME_BY_SUFFIX = {
    ".dxf": "application/dxf",
    ".svg": "image/svg+xml",
    ".json": "application/json",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".zip": "application/zip",
}


@dataclass(frozen=True)
class FileIngestMetadata:
    file_name: str
    mime_type: str
    byte_size: int
    sha256: str


def canonical_file_name_from_storage_path(storage_path: str) -> str:
    raw_path = storage_path.strip()
    if not raw_path:
        raise ValueError("missing storage_path")

    file_name = PurePosixPath(raw_path).name.strip()
    if not file_name or file_name in {".", ".."}:
        raise ValueError("invalid storage_path filename")

    return file_name


def _infer_mime_type(file_name: str) -> str:
    suffix = PurePosixPath(file_name).suffix.lower()
    if suffix in _MIME_BY_SUFFIX:
        return _MIME_BY_SUFFIX[suffix]

    guessed, _ = mimetypes.guess_type(file_name, strict=False)
    if guessed:
        return guessed
    return "application/octet-stream"


def download_storage_object_blob(
    *,
    supabase: SupabaseClient,
    access_token: str,
    storage_bucket: str,
    storage_path: str,
    signed_url_ttl_s: int,
) -> bytes:
    bucket = storage_bucket.strip()
    object_key = storage_path.strip()
    if not bucket:
        raise ValueError("missing storage_bucket")
    if not object_key:
        raise ValueError("missing storage_path")

    signed = supabase.create_signed_download_url(
        access_token=access_token,
        bucket=bucket,
        object_key=object_key,
        expires_in=signed_url_ttl_s,
    )
    download_url = str(signed.get("download_url", "")).strip()
    if not download_url:
        raise SupabaseHTTPError("missing signed download url")

    blob = supabase.download_signed_object(signed_url=download_url)
    if not isinstance(blob, (bytes, bytearray)):
        raise SupabaseHTTPError("downloaded object is not bytes")
    return bytes(blob)


def load_file_ingest_metadata(
    *,
    supabase: SupabaseClient,
    access_token: str,
    storage_bucket: str,
    storage_path: str,
    signed_url_ttl_s: int,
) -> FileIngestMetadata:
    file_name = canonical_file_name_from_storage_path(storage_path)
    blob = download_storage_object_blob(
        supabase=supabase,
        access_token=access_token,
        storage_bucket=storage_bucket,
        storage_path=storage_path,
        signed_url_ttl_s=signed_url_ttl_s,
    )
    byte_size = len(blob)
    if byte_size <= 0:
        raise SupabaseHTTPError("downloaded object is empty")

    return FileIngestMetadata(
        file_name=file_name,
        mime_type=_infer_mime_type(file_name),
        byte_size=byte_size,
        sha256=hashlib.sha256(blob).hexdigest(),
    )
