#!/usr/bin/env python3
"""H1-E2-T1 smoke: source_dxf -> parsed geometry_revisions chain."""

from __future__ import annotations

import json
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
from api.services.dxf_geometry_import import import_source_dxf_geometry_revision
from api.supabase_client import SupabaseHTTPError


class FakeSupabaseClient:
    def __init__(self) -> None:
        self.projects: dict[str, dict[str, Any]] = {}
        self.file_objects: dict[str, dict[str, Any]] = {}
        self.geometry_revisions: dict[str, dict[str, Any]] = {}
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
        if table == "app.geometry_revisions":
            return list(self.geometry_revisions.values())
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

        if table == "app.file_objects":
            row.setdefault("id", str(uuid4()))
            row.setdefault("created_at", now)
            self.file_objects[str(row["id"])] = row
            return dict(row)

        if table == "app.geometry_revisions":
            row.setdefault("id", str(uuid4()))
            row.setdefault("created_at", now)
            row.setdefault("updated_at", now)
            self.geometry_revisions[str(row["id"])] = row
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

    with tempfile.TemporaryDirectory(prefix="vrs_h1e2t1_") as tmp:
        tmp_path = Path(tmp) / "part.dxf"
        doc = ezdxf.new("R2010")
        msp = doc.modelspace()
        msp.add_lwpolyline([(0.0, 0.0), (40.0, 0.0), (40.0, 30.0), (0.0, 30.0)], dxfattribs={"layer": "CUT_OUTER", "closed": True})
        msp.add_lwpolyline([(10.0, 10.0), (20.0, 10.0), (20.0, 20.0), (10.0, 20.0)], dxfattribs={"layer": "CUT_INNER", "closed": True})
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

        ok_upload_resp = client.post(
            f"/v1/projects/{project_id}/files/upload-url",
            headers=headers,
            json={
                "filename": "part_ok.dxf",
                "content_type": "application/dxf",
                "size_bytes": 1024,
                "file_kind": "source_dxf",
            },
        )
        if ok_upload_resp.status_code != 200:
            raise RuntimeError(f"ok upload-url failed: {ok_upload_resp.status_code} {ok_upload_resp.text}")
        ok_upload = ok_upload_resp.json()
        ok_file_id = str(ok_upload["file_id"])
        ok_storage_path = str(ok_upload["storage_path"])
        fake.put_uploaded_object(
            signed_upload_url=str(ok_upload["upload_url"]),
            blob=_make_valid_dxf_bytes(),
        )

        ok_complete_resp = client.post(
            f"/v1/projects/{project_id}/files",
            headers=headers,
            json={
                "file_id": ok_file_id,
                "storage_path": ok_storage_path,
                "file_kind": "source_dxf",
            },
        )
        if ok_complete_resp.status_code != 200:
            raise RuntimeError(f"ok complete failed: {ok_complete_resp.status_code} {ok_complete_resp.text}")

        ok_file_row = fake.file_objects.get(ok_file_id)
        if not ok_file_row:
            raise RuntimeError("ok file row missing")
        ok_revisions = [row for row in fake.geometry_revisions.values() if str(row.get("source_file_object_id")) == ok_file_id]
        if len(ok_revisions) != 1:
            raise RuntimeError(f"expected exactly one geometry revision for ok file, got {len(ok_revisions)}")
        ok_revision = ok_revisions[0]

        if ok_revision.get("project_id") != project_id:
            raise RuntimeError("project_id mismatch in geometry revision")
        if ok_revision.get("source_file_object_id") != ok_file_id:
            raise RuntimeError("source_file_object_id mismatch in geometry revision")
        if ok_revision.get("geometry_role") != "part":
            raise RuntimeError("geometry_role mismatch in geometry revision")
        if ok_revision.get("status") != "parsed":
            raise RuntimeError("status mismatch in geometry revision")
        if ok_revision.get("revision_no") != 1:
            raise RuntimeError("revision_no mismatch in geometry revision")
        if ok_revision.get("canonical_format_version") != "part_raw.v1":
            raise RuntimeError("canonical_format_version mismatch in geometry revision")
        if ok_revision.get("source_hash_sha256") != ok_file_row.get("sha256"):
            raise RuntimeError("source_hash_sha256 mismatch in geometry revision")
        if ok_revision.get("created_by") != user_id:
            raise RuntimeError("created_by mismatch in geometry revision")

        canonical_geometry = ok_revision.get("canonical_geometry_jsonb")
        if not isinstance(canonical_geometry, dict):
            raise RuntimeError("canonical_geometry_jsonb is missing or not object")
        if not canonical_geometry.get("outer_points_mm"):
            raise RuntimeError("canonical_geometry_jsonb.outer_points_mm missing")
        if "holes_points_mm" not in canonical_geometry:
            raise RuntimeError("canonical_geometry_jsonb.holes_points_mm missing")
        source_lineage = canonical_geometry.get("source_lineage")
        if not isinstance(source_lineage, dict):
            raise RuntimeError("canonical_geometry_jsonb.source_lineage missing")
        if source_lineage.get("storage_path") != ok_storage_path:
            raise RuntimeError("source_lineage storage_path mismatch")

        canonical_hash_expected = json.dumps(
            canonical_geometry,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        import hashlib

        if ok_revision.get("canonical_hash_sha256") != hashlib.sha256(canonical_hash_expected.encode("utf-8")).hexdigest():
            raise RuntimeError("canonical_hash_sha256 mismatch in geometry revision")

        bbox = ok_revision.get("bbox_jsonb")
        if not isinstance(bbox, dict):
            raise RuntimeError("bbox_jsonb missing in geometry revision")
        for key in ("min_x", "min_y", "max_x", "max_y", "width", "height"):
            if key not in bbox:
                raise RuntimeError(f"bbox_jsonb.{key} missing")

        second_revision = import_source_dxf_geometry_revision(
            supabase=fake,  # type: ignore[arg-type]
            access_token="token-u1",
            project_id=project_id,
            source_file_object_id=ok_file_id,
            storage_bucket="source-files",
            storage_path=ok_storage_path,
            source_hash_sha256=str(ok_file_row.get("sha256") or ""),
            created_by=user_id,
            signed_url_ttl_s=300,
        )
        if second_revision.get("revision_no") != 2:
            raise RuntimeError("second revision_no mismatch for same source file")

        bad_upload_resp = client.post(
            f"/v1/projects/{project_id}/files/upload-url",
            headers=headers,
            json={
                "filename": "part_bad.dxf",
                "content_type": "application/dxf",
                "size_bytes": 32,
                "file_kind": "source_dxf",
            },
        )
        if bad_upload_resp.status_code != 200:
            raise RuntimeError("bad upload-url failed")
        bad_upload = bad_upload_resp.json()
        bad_file_id = str(bad_upload["file_id"])
        bad_storage_path = str(bad_upload["storage_path"])
        fake.put_uploaded_object(
            signed_upload_url=str(bad_upload["upload_url"]),
            blob=b"this-is-not-a-dxf-file",
        )

        bad_complete_resp = client.post(
            f"/v1/projects/{project_id}/files",
            headers=headers,
            json={
                "file_id": bad_file_id,
                "storage_path": bad_storage_path,
                "file_kind": "source_dxf",
            },
        )
        if bad_complete_resp.status_code != 200:
            raise RuntimeError(f"bad complete failed: {bad_complete_resp.status_code} {bad_complete_resp.text}")
        bad_revisions = [row for row in fake.geometry_revisions.values() if str(row.get("source_file_object_id")) == bad_file_id]
        if bad_revisions:
            raise RuntimeError("invalid DXF should not create parsed geometry revision")

        missing_upload_resp = client.post(
            f"/v1/projects/{project_id}/files/upload-url",
            headers=headers,
            json={
                "filename": "part_missing.dxf",
                "content_type": "application/dxf",
                "size_bytes": 64,
                "file_kind": "source_dxf",
            },
        )
        if missing_upload_resp.status_code != 200:
            raise RuntimeError("missing upload-url failed")
        missing_upload = missing_upload_resp.json()
        missing_file_id = str(missing_upload["file_id"])
        missing_storage_path = str(missing_upload["storage_path"])

        missing_complete_resp = client.post(
            f"/v1/projects/{project_id}/files",
            headers=headers,
            json={
                "file_id": missing_file_id,
                "storage_path": missing_storage_path,
                "file_kind": "source_dxf",
            },
        )
        if missing_complete_resp.status_code != 400:
            raise RuntimeError(
                "missing object complete should fail with HTTP 400 "
                f"(got {missing_complete_resp.status_code})"
            )
        if missing_file_id in fake.file_objects:
            raise RuntimeError("missing object should not create file_objects row")
        missing_revisions = [row for row in fake.geometry_revisions.values() if str(row.get("source_file_object_id")) == missing_file_id]
        if missing_revisions:
            raise RuntimeError("missing object should not create parsed geometry revision")

        print("[PASS] H1-E2-T1 dxf parser integracio smoke passed")
        return 0
    finally:
        app.dependency_overrides.clear()


if __name__ == "__main__":
    raise SystemExit(main())
