#!/usr/bin/env python3
"""H1-E1-T2 smoke: server-side ingest metadata truth wins over client metadata."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import ezdxf
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.config import Settings
from api.deps import get_settings, get_supabase_client
from api.main import app
from api.supabase_client import SupabaseHTTPError


class FakeSupabaseClient:
    def __init__(self) -> None:
        self.projects: dict[str, dict[str, Any]] = {}
        self.file_objects: dict[str, dict[str, Any]] = {}
        self.storage: dict[tuple[str, str], bytes] = {}

    def get_auth_user(self, access_token: str) -> dict[str, Any]:
        if access_token == "token-u1":
            return {"id": "00000000-0000-0000-0000-000000000001", "email": "u1@example.com"}
        raise RuntimeError("invalid token")

    def _rows_for_table(self, table: str) -> list[dict[str, Any]]:
        if table == "app.projects":
            return list(self.projects.values())
        if table == "app.file_objects":
            return list(self.file_objects.values())
        return []

    @staticmethod
    def _matches(row: dict[str, Any], key: str, raw_filter: str) -> bool:
        value = row.get(key)
        if raw_filter.startswith("eq."):
            return str(value) == raw_filter[3:]
        if raw_filter.startswith("neq."):
            return str(value) != raw_filter[4:]
        if raw_filter.startswith("gte."):
            return str(value or "") >= raw_filter[4:]
        return True

    def select_rows(
        self,
        *,
        table: str,
        access_token: str,
        params: dict[str, str],
    ) -> list[dict[str, Any]]:
        _ = access_token
        rows = self._rows_for_table(table)
        meta_keys = {"select", "order", "limit", "offset"}
        for key, raw_filter in params.items():
            if key in meta_keys:
                continue
            rows = [row for row in rows if self._matches(row, key, raw_filter)]

        limit_raw = params.get("limit", "").strip()
        if limit_raw:
            rows = rows[: int(limit_raw)]
        return [dict(row) for row in rows]

    def insert_row(self, *, table: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        _ = access_token
        now = datetime.now(timezone.utc).isoformat()
        row = dict(payload)

        if table == "app.file_objects":
            row.setdefault("created_at", now)
            self.file_objects[str(row["id"])] = row
            return dict(row)

        raise RuntimeError(f"unsupported table insert: {table}")

    def delete_rows(self, *, table: str, access_token: str, filters: dict[str, str]) -> None:
        _ = (table, access_token, filters)

    def remove_object(self, *, access_token: str, bucket: str, object_key: str) -> None:
        _ = access_token
        self.storage.pop((bucket, object_key), None)

    def create_signed_upload_url(
        self,
        *,
        access_token: str,
        bucket: str,
        object_key: str,
        expires_in: int = 300,
    ) -> dict[str, Any]:
        _ = (access_token, expires_in)
        token = str(uuid4())
        return {
            "upload_url": f"https://upload.local/{bucket}/{object_key}?token={token}",
            "expires_at": datetime.now(timezone.utc).isoformat(),
        }

    def create_signed_download_url(
        self,
        *,
        access_token: str,
        bucket: str,
        object_key: str,
        expires_in: int = 900,
    ) -> dict[str, Any]:
        _ = (access_token, expires_in)
        return {
            "download_url": f"https://download.local/{bucket}/{object_key}",
            "expires_at": datetime.now(timezone.utc).isoformat(),
        }

    def download_signed_object(self, *, signed_url: str) -> bytes:
        parsed = urlparse(signed_url)
        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) < 2:
            raise SupabaseHTTPError("invalid signed download path")
        bucket = path_parts[0]
        object_key = "/".join(path_parts[1:])
        blob = self.storage.get((bucket, object_key))
        if blob is None:
            raise SupabaseHTTPError("object not found")
        return blob

    def put_uploaded_object(self, *, signed_upload_url: str, blob: bytes) -> tuple[str, str]:
        parsed = urlparse(signed_upload_url)
        _ = parse_qs(parsed.query)
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 2:
            raise RuntimeError("invalid upload path")
        bucket = parts[0]
        object_key = "/".join(parts[1:])
        self.storage[(bucket, object_key)] = blob
        return bucket, object_key


def _make_valid_dxf_bytes() -> bytes:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="vrs_h1e1t2_") as tmp:
        tmp_path = Path(tmp) / "part.dxf"
        doc = ezdxf.new("R2010")
        doc.modelspace().add_line((0.0, 0.0), (10.0, 0.0))
        doc.saveas(tmp_path)
        return tmp_path.read_bytes()


def _settings() -> Settings:
    return Settings(
        supabase_url="https://fake.supabase.local",
        supabase_anon_key="fake-anon",
        supabase_project_ref="",
        supabase_db_password="",
        database_url="",
        storage_bucket="source-files",
        max_dxf_size_mb=50,
        rate_limit_window_s=60,
        rate_limit_runs_per_window=10,
        rate_limit_bundles_per_window=4,
        rate_limit_upload_urls_per_window=100,
        signed_url_ttl_s=300,
        enable_security_headers=False,
        allowed_origins=("http://localhost:5173",),
    )


def main() -> int:
    fake = FakeSupabaseClient()
    app.dependency_overrides[get_supabase_client] = lambda: fake
    app.dependency_overrides[get_settings] = _settings

    try:
        client = TestClient(app)
        headers = {"Authorization": "Bearer token-u1"}
        user_id = "00000000-0000-0000-0000-000000000001"
        project_id = str(uuid4())
        fake.projects[project_id] = {
            "id": project_id,
            "owner_user_id": user_id,
            "lifecycle": "draft",
        }

        upload_url_resp = client.post(
            f"/v1/projects/{project_id}/files/upload-url",
            headers=headers,
            json={
                "filename": "part.dxf",
                "content_type": "application/dxf",
                "size_bytes": 1024,
                "file_kind": "source_dxf",
            },
        )
        if upload_url_resp.status_code != 200:
            raise RuntimeError(f"upload-url failed: {upload_url_resp.status_code} {upload_url_resp.text}")
        upload_payload = upload_url_resp.json()

        file_id = str(upload_payload["file_id"])
        storage_path = str(upload_payload["storage_path"])
        fake_blob = _make_valid_dxf_bytes()
        fake.put_uploaded_object(signed_upload_url=str(upload_payload["upload_url"]), blob=fake_blob)

        complete_resp = client.post(
            f"/v1/projects/{project_id}/files",
            headers=headers,
            json={
                "file_id": file_id,
                "file_name": "tampered_name.bin",
                "original_filename": "legacy_name.txt",
                "storage_path": storage_path,
                "storage_bucket": "evil-bucket",
                "file_kind": "source_dxf",
                "byte_size": 1,
                "size_bytes": 2,
                "mime_type": "text/plain",
                "content_type": "application/pdf",
                "sha256": "deadbeef",
                "content_hash_sha256": "cafebabe",
            },
        )
        if complete_resp.status_code != 200:
            raise RuntimeError(f"complete upload failed: {complete_resp.status_code} {complete_resp.text}")

        expected_sha = hashlib.sha256(fake_blob).hexdigest()
        expected_size = len(fake_blob)
        payload = complete_resp.json()
        if payload.get("storage_bucket") != "source-files":
            raise RuntimeError("storage_bucket did not stay canonical")
        if payload.get("file_name") != "part.dxf":
            raise RuntimeError("file_name is not derived from storage_path basename")
        if payload.get("byte_size") != expected_size:
            raise RuntimeError("byte_size was not computed from uploaded object")
        if payload.get("sha256") != expected_sha:
            raise RuntimeError("sha256 was not computed from uploaded object")
        if payload.get("mime_type") != "application/dxf":
            raise RuntimeError("mime_type was not server-derived from canonical file name")

        stored_row = fake.file_objects.get(file_id)
        if not stored_row:
            raise RuntimeError("missing stored app.file_objects row")
        if stored_row.get("storage_bucket") != "source-files":
            raise RuntimeError("stored storage_bucket mismatch")
        if stored_row.get("file_name") != "part.dxf":
            raise RuntimeError("stored file_name mismatch")
        if stored_row.get("byte_size") != expected_size:
            raise RuntimeError("stored byte_size mismatch")
        if stored_row.get("sha256") != expected_sha:
            raise RuntimeError("stored sha256 mismatch")
        if stored_row.get("mime_type") != "application/dxf":
            raise RuntimeError("stored mime_type mismatch")

        missing_upload_resp = client.post(
            f"/v1/projects/{project_id}/files/upload-url",
            headers=headers,
            json={
                "filename": "missing.dxf",
                "content_type": "application/dxf",
                "size_bytes": 64,
                "file_kind": "source_dxf",
            },
        )
        if missing_upload_resp.status_code != 200:
            raise RuntimeError("failed to create upload-url for missing-object scenario")
        missing_info = missing_upload_resp.json()
        missing_file_id = str(missing_info["file_id"])
        missing_storage_path = str(missing_info["storage_path"])

        missing_complete_resp = client.post(
            f"/v1/projects/{project_id}/files",
            headers=headers,
            json={
                "file_id": missing_file_id,
                "storage_path": missing_storage_path,
                "storage_bucket": "tampered-bucket",
                "file_kind": "source_dxf",
                "byte_size": 9999,
                "mime_type": "text/plain",
                "sha256": "not-real",
            },
        )
        if missing_complete_resp.status_code != 400:
            raise RuntimeError(
                "missing object complete should fail with HTTP 400 "
                f"(got {missing_complete_resp.status_code})"
            )
        if missing_file_id in fake.file_objects:
            raise RuntimeError("missing object scenario created misleading file_objects row")

        print("[PASS] H1-E1-T2 file hash es metadata kezeles smoke passed")
        return 0
    finally:
        app.dependency_overrides.clear()


if __name__ == "__main__":
    raise SystemExit(main())
