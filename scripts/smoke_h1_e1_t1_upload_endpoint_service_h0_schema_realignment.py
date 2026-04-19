#!/usr/bin/env python3
"""H1-E1-T1 smoke: H0-aligned project + file upload flow with in-memory fake Supabase."""

from __future__ import annotations

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


class FakeSupabaseClient:
    def __init__(self) -> None:
        self.projects: dict[str, dict[str, Any]] = {}
        self.file_objects: dict[str, dict[str, Any]] = {}
        self.storage: dict[tuple[str, str], bytes] = {}

    def get_auth_user(self, access_token: str) -> dict[str, Any]:
        if access_token == "token-u1":
            return {"id": "00000000-0000-0000-0000-000000000001", "email": "u1@example.com"}
        if access_token == "token-u2":
            return {"id": "00000000-0000-0000-0000-000000000002", "email": "u2@example.com"}
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
            text = str(value or "")
            return text >= raw_filter[4:]
        if raw_filter == "is.null":
            return value is None
        if raw_filter == "not.is.null":
            return value is not None
        return True

    @staticmethod
    def _apply_order(rows: list[dict[str, Any]], order_clause: str) -> list[dict[str, Any]]:
        ordered = list(rows)
        for token in reversed([part.strip() for part in order_clause.split(",") if part.strip()]):
            key = token.split(".")[0]
            reverse = ".desc" in token
            ordered.sort(key=lambda row: str(row.get(key) or ""), reverse=reverse)
        return ordered

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

        order_clause = params.get("order", "").strip()
        if order_clause:
            rows = self._apply_order(rows, order_clause)

        offset = int(params.get("offset", "0") or "0")
        limit_raw = params.get("limit", "")
        if limit_raw:
            limit = int(limit_raw)
            rows = rows[offset : offset + limit]
        else:
            rows = rows[offset:]

        return [dict(row) for row in rows]

    def insert_row(self, *, table: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        _ = access_token
        now = datetime.now(timezone.utc).isoformat()
        row = dict(payload)

        if table == "app.projects":
            row.setdefault("id", str(uuid4()))
            row.setdefault("lifecycle", "draft")
            row.setdefault("created_at", now)
            row.setdefault("updated_at", now)
            self.projects[str(row["id"])] = row
            return dict(row)

        if table == "app.file_objects":
            row.setdefault("id", str(uuid4()))
            row.setdefault("created_at", now)
            self.file_objects[str(row["id"])] = row
            return dict(row)

        raise RuntimeError(f"unsupported table insert: {table}")

    def update_rows(
        self,
        *,
        table: str,
        access_token: str,
        payload: dict[str, Any],
        filters: dict[str, str],
    ) -> list[dict[str, Any]]:
        _ = access_token
        rows = self._rows_for_table(table)
        out: list[dict[str, Any]] = []
        for row in rows:
            if all(self._matches(row, key, filt) for key, filt in filters.items()):
                row.update(payload)
                if table == "app.projects":
                    row["updated_at"] = datetime.now(timezone.utc).isoformat()
                out.append(dict(row))
        return out

    def delete_rows(self, *, table: str, access_token: str, filters: dict[str, str]) -> None:
        _ = access_token
        if table == "app.file_objects":
            for file_id, row in list(self.file_objects.items()):
                if all(self._matches(row, key, filt) for key, filt in filters.items()):
                    del self.file_objects[file_id]
            return
        raise RuntimeError(f"unsupported table delete: {table}")

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
            return b""
        bucket = path_parts[0]
        object_key = "/".join(path_parts[1:])
        return self.storage.get((bucket, object_key), b"")

    def remove_object(self, *, access_token: str, bucket: str, object_key: str) -> None:
        _ = access_token
        self.storage.pop((bucket, object_key), None)

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

    with tempfile.TemporaryDirectory(prefix="vrs_h1e1t1_") as tmp:
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
        h1 = {"Authorization": "Bearer token-u1"}
        h2 = {"Authorization": "Bearer token-u2"}

        create_project = client.post("/v1/projects", headers=h1, json={"name": "H0 ingest", "description": ""})
        if create_project.status_code != 200:
            raise RuntimeError(f"create project failed: {create_project.status_code} {create_project.text}")
        project_payload = create_project.json()
        project_id = str(project_payload["id"])

        if project_payload.get("owner_user_id") != "00000000-0000-0000-0000-000000000001":
            raise RuntimeError("owner_user_id mismatch")
        if project_payload.get("lifecycle") != "draft":
            raise RuntimeError("new project lifecycle is not draft")
        if "owner_id" in project_payload or "archived_at" in project_payload:
            raise RuntimeError("legacy project fields leaked in response")

        get_project = client.get(f"/v1/projects/{project_id}", headers=h1)
        if get_project.status_code != 200:
            raise RuntimeError("get project failed")

        archive_project = client.delete(f"/v1/projects/{project_id}", headers=h1)
        if archive_project.status_code != 204:
            raise RuntimeError("archive project failed")

        archived_list = client.get("/v1/projects?archived=true", headers=h1)
        if archived_list.status_code != 200:
            raise RuntimeError("archived list failed")
        archived_ids = {str(item.get("id")) for item in archived_list.json().get("items", [])}
        if project_id not in archived_ids:
            raise RuntimeError("archived project missing in archived list")

        active_project_resp = client.post("/v1/projects", headers=h1, json={"name": "Upload", "description": ""})
        if active_project_resp.status_code != 200:
            raise RuntimeError("active project create failed")
        active_project_id = str(active_project_resp.json()["id"])

        upload_url_resp = client.post(
            f"/v1/projects/{active_project_id}/files/upload-url",
            headers=h1,
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
        storage_bucket = str(upload_payload["storage_bucket"])
        expected_prefix = f"projects/{active_project_id}/files/{file_id}/"
        if not storage_path.startswith(expected_prefix):
            raise RuntimeError("storage_path does not follow H0 canonical pattern")
        if storage_path.startswith("users/"):
            raise RuntimeError("legacy users/{user_id}/projects path detected")

        fake.put_uploaded_object(signed_upload_url=str(upload_payload["upload_url"]), blob=_make_valid_dxf_bytes())

        complete_resp = client.post(
            f"/v1/projects/{active_project_id}/files",
            headers=h1,
            json={
                "file_id": file_id,
                "file_name": "part.dxf",
                "storage_path": storage_path,
                "storage_bucket": storage_bucket,
                "file_kind": "source_dxf",
                "byte_size": 1024,
                "mime_type": "application/dxf",
                "sha256": "",
            },
        )
        if complete_resp.status_code != 200:
            raise RuntimeError(f"complete upload failed: {complete_resp.status_code} {complete_resp.text}")
        file_payload = complete_resp.json()

        for forbidden_field in ("validation_status", "validation_error", "original_filename", "storage_key", "file_type"):
            if forbidden_field in file_payload:
                raise RuntimeError(f"legacy field leaked in file response: {forbidden_field}")

        list_resp = client.get(f"/v1/projects/{active_project_id}/files", headers=h1)
        if list_resp.status_code != 200:
            raise RuntimeError("list files failed")
        list_payload = list_resp.json()
        if list_payload.get("total") != 1:
            raise RuntimeError("list files total mismatch")

        row = fake.file_objects.get(file_id)
        if not row:
            raise RuntimeError("file object row missing from fake app.file_objects")
        if row.get("file_kind") != "source_dxf":
            raise RuntimeError("file_kind mismatch in stored row")
        if row.get("storage_path") != storage_path:
            raise RuntimeError("storage_path mismatch in stored row")
        if row.get("storage_bucket") != "source-files":
            raise RuntimeError("storage_bucket mismatch in stored row")

        cross_user_status = client.get(f"/v1/projects/{active_project_id}/files", headers=h2).status_code
        if cross_user_status not in (403, 404):
            raise RuntimeError(f"unexpected cross-user status: {cross_user_status}")

        delete_resp = client.delete(f"/v1/projects/{active_project_id}/files/{file_id}", headers=h1)
        if delete_resp.status_code != 204:
            raise RuntimeError("delete file failed")
        if file_id in fake.file_objects:
            raise RuntimeError("file row still present after delete")
        if (storage_bucket, storage_path) in fake.storage:
            raise RuntimeError("storage object still present after delete")

        print("[PASS] H1-E1-T1 H0 schema realignment smoke passed")
        return 0
    finally:
        app.dependency_overrides.clear()


if __name__ == "__main__":
    raise SystemExit(main())
