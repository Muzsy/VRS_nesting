#!/usr/bin/env python3
"""H1-E2-T4 smoke: geometry derivative generator (H1 minimum)."""

from __future__ import annotations

import hashlib
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
from api.services.geometry_derivative_generator import generate_h1_minimum_geometry_derivatives
from api.supabase_client import SupabaseHTTPError


class FakeSupabaseClient:
    def __init__(self) -> None:
        self.projects: dict[str, dict[str, Any]] = {}
        self.file_objects: dict[str, dict[str, Any]] = {}
        self.geometry_revisions: dict[str, dict[str, Any]] = {}
        self.geometry_validation_reports: dict[str, dict[str, Any]] = {}
        self.geometry_derivatives: dict[str, dict[str, Any]] = {}
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
        if table == "app.geometry_validation_reports":
            return list(self.geometry_validation_reports.values())
        if table == "app.geometry_derivatives":
            return list(self.geometry_derivatives.values())
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

        if table == "app.geometry_validation_reports":
            row.setdefault("id", str(uuid4()))
            row.setdefault("created_at", now)
            self.geometry_validation_reports[str(row["id"])] = row
            return dict(row)

        if table == "app.geometry_derivatives":
            for existing in self.geometry_derivatives.values():
                if (
                    str(existing.get("geometry_revision_id")) == str(row.get("geometry_revision_id"))
                    and str(existing.get("derivative_kind")) == str(row.get("derivative_kind"))
                ):
                    raise SupabaseHTTPError("duplicate key value violates unique constraint geometry_derivatives_geometry_revision_kind")
            row.setdefault("id", str(uuid4()))
            row.setdefault("created_at", now)
            self.geometry_derivatives[str(row["id"])] = row
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
        if table == "app.geometry_revisions":
            storage = self.geometry_revisions
        elif table == "app.geometry_derivatives":
            storage = self.geometry_derivatives
        else:
            return []

        rows = list(storage.values())
        for key, raw_filter in filters.items():
            rows = [row for row in rows if self._matches(row, key, raw_filter)]

        updated: list[dict[str, Any]] = []
        now = datetime.now(timezone.utc).isoformat()
        for row in rows:
            current = storage[str(row["id"])]
            current.update(payload)
            if table == "app.geometry_revisions":
                current["updated_at"] = now
            updated.append(dict(current))
        return updated

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

    with tempfile.TemporaryDirectory(prefix="vrs_h1e2t4_ok_") as tmp:
        tmp_path = Path(tmp) / "part.dxf"
        doc = ezdxf.new("R2010")
        msp = doc.modelspace()
        msp.add_lwpolyline([(0.0, 0.0), (120.0, 0.0), (120.0, 80.0), (0.0, 80.0)], dxfattribs={"layer": "CUT_OUTER", "closed": True})
        msp.add_lwpolyline([(10.0, 10.0), (30.0, 10.0), (30.0, 25.0), (10.0, 25.0)], dxfattribs={"layer": "CUT_INNER", "closed": True})
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


def _canonical_hash(payload: dict[str, Any]) -> str:
    canonical_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


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
        fake.put_uploaded_object(signed_upload_url=str(ok_upload["upload_url"]), blob=_make_valid_dxf_bytes())

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

        ok_revisions = [row for row in fake.geometry_revisions.values() if str(row.get("source_file_object_id")) == ok_file_id]
        if len(ok_revisions) != 1:
            raise RuntimeError(f"expected 1 geometry revision for ok file, got {len(ok_revisions)}")
        ok_revision = ok_revisions[0]
        if ok_revision.get("status") != "validated":
            raise RuntimeError("valid geometry should end in validated status")

        revision_id = str(ok_revision.get("id"))
        derivatives = [row for row in fake.geometry_derivatives.values() if str(row.get("geometry_revision_id")) == revision_id]
        if len(derivatives) != 2:
            raise RuntimeError(f"expected exactly 2 derivatives for validated geometry, got {len(derivatives)}")

        by_kind = {str(row.get("derivative_kind")): row for row in derivatives}
        expected_kinds = {"nesting_canonical", "viewer_outline"}
        if set(by_kind.keys()) != expected_kinds:
            raise RuntimeError(f"unexpected derivative kinds: {sorted(by_kind.keys())}")

        nesting = by_kind["nesting_canonical"]
        viewer = by_kind["viewer_outline"]

        for kind, row in by_kind.items():
            if row.get("producer_version") != "geometry_derivative_generator.v1":
                raise RuntimeError(f"producer_version mismatch for {kind}")
            if row.get("source_geometry_hash_sha256") != ok_revision.get("canonical_hash_sha256"):
                raise RuntimeError(f"source_geometry_hash_sha256 mismatch for {kind}")
            derivative_json = row.get("derivative_jsonb")
            if not isinstance(derivative_json, dict):
                raise RuntimeError(f"derivative_jsonb missing for {kind}")
            expected_hash = _canonical_hash(derivative_json)
            if row.get("derivative_hash_sha256") != expected_hash:
                raise RuntimeError(f"derivative_hash_sha256 mismatch for {kind}")

        nesting_json = nesting.get("derivative_jsonb")
        viewer_json = viewer.get("derivative_jsonb")
        if not isinstance(nesting_json, dict) or not isinstance(viewer_json, dict):
            raise RuntimeError("missing derivative payloads")
        if nesting_json == viewer_json:
            raise RuntimeError("nesting_canonical and viewer_outline payloads must differ")

        polygon = nesting_json.get("polygon")
        if not isinstance(polygon, dict) or not isinstance(polygon.get("outer_ring"), list):
            raise RuntimeError("nesting_canonical payload structure mismatch")
        outline = viewer_json.get("outline")
        if not isinstance(outline, dict) or not isinstance(outline.get("outer_polyline"), list):
            raise RuntimeError("viewer_outline payload structure mismatch")

        ids_before = {kind: str(row.get("id")) for kind, row in by_kind.items()}
        hashes_before = {kind: str(row.get("derivative_hash_sha256")) for kind, row in by_kind.items()}
        regenerate_result = generate_h1_minimum_geometry_derivatives(
            supabase=fake,  # type: ignore[arg-type]
            access_token="token-u1",
            geometry_revision=ok_revision,
        )
        generated = regenerate_result.get("generated")
        if not isinstance(generated, dict) or set(generated.keys()) != expected_kinds:
            raise RuntimeError("regenerate result missing kinds")

        derivatives_after = [row for row in fake.geometry_derivatives.values() if str(row.get("geometry_revision_id")) == revision_id]
        if len(derivatives_after) != 2:
            raise RuntimeError("regenerate should not create duplicate derivative rows")
        by_kind_after = {str(row.get("derivative_kind")): row for row in derivatives_after}
        for kind in expected_kinds:
            if str(by_kind_after[kind].get("id")) != ids_before[kind]:
                raise RuntimeError(f"regenerate should update existing derivative id for {kind}")
            if str(by_kind_after[kind].get("derivative_hash_sha256")) != hashes_before[kind]:
                raise RuntimeError(f"regenerate hash changed unexpectedly for {kind}")

        rejected_revision = fake.insert_row(
            table="app.geometry_revisions",
            access_token="token-u1",
            payload={
                "project_id": project_id,
                "source_file_object_id": str(uuid4()),
                "geometry_role": "part",
                "revision_no": 999,
                "status": "rejected",
                "canonical_format_version": "normalized_geometry.v1",
                "canonical_geometry_jsonb": {
                    "geometry_role": "part",
                    "format_version": "normalized_geometry.v1",
                    "units": "mm",
                    "outer_ring": [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]],
                    "hole_rings": [],
                    "bbox": {
                        "min_x": 0.0,
                        "min_y": 0.0,
                        "max_x": 1.0,
                        "max_y": 1.0,
                        "width": 1.0,
                        "height": 1.0,
                    },
                },
                "canonical_hash_sha256": "abc",
                "source_hash_sha256": "def",
                "bbox_jsonb": {
                    "min_x": 0.0,
                    "min_y": 0.0,
                    "max_x": 1.0,
                    "max_y": 1.0,
                    "width": 1.0,
                    "height": 1.0,
                },
                "created_by": user_id,
            },
        )
        rejected_result = generate_h1_minimum_geometry_derivatives(
            supabase=fake,  # type: ignore[arg-type]
            access_token="token-u1",
            geometry_revision=rejected_revision,
        )
        if not str(rejected_result.get("skipped_reason") or ""):
            raise RuntimeError("rejected geometry should return skipped_reason")
        rejected_derivatives = [
            row for row in fake.geometry_derivatives.values() if str(row.get("geometry_revision_id")) == str(rejected_revision.get("id"))
        ]
        if rejected_derivatives:
            raise RuntimeError("rejected geometry must not create derivative rows")

        invalid_upload_resp = client.post(
            f"/v1/projects/{project_id}/files/upload-url",
            headers=headers,
            json={
                "filename": "part_invalid.dxf",
                "content_type": "application/dxf",
                "size_bytes": 64,
                "file_kind": "source_dxf",
            },
        )
        if invalid_upload_resp.status_code != 200:
            raise RuntimeError("invalid upload-url failed")
        invalid_upload = invalid_upload_resp.json()
        invalid_file_id = str(invalid_upload["file_id"])
        invalid_storage_path = str(invalid_upload["storage_path"])
        fake.put_uploaded_object(signed_upload_url=str(invalid_upload["upload_url"]), blob=b"not-a-dxf")

        invalid_complete_resp = client.post(
            f"/v1/projects/{project_id}/files",
            headers=headers,
            json={
                "file_id": invalid_file_id,
                "storage_path": invalid_storage_path,
                "file_kind": "source_dxf",
            },
        )
        if invalid_complete_resp.status_code != 200:
            raise RuntimeError(f"invalid complete failed: {invalid_complete_resp.status_code}")

        invalid_revisions = [
            row for row in fake.geometry_revisions.values() if str(row.get("source_file_object_id")) == invalid_file_id
        ]
        if invalid_revisions:
            raise RuntimeError("invalid DXF should not create parsed geometry revision")
        invalid_derivatives = [
            row for row in fake.geometry_derivatives.values() if str(row.get("geometry_revision_id")) in {str(r.get("id")) for r in invalid_revisions}
        ]
        if invalid_derivatives:
            raise RuntimeError("invalid DXF should not create derivatives")

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

        print("[PASS] H1-E2-T4 geometry derivative generator smoke passed")
        return 0
    finally:
        app.dependency_overrides.clear()


if __name__ == "__main__":
    raise SystemExit(main())
