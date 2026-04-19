#!/usr/bin/env python3
"""H1-E2-T3 smoke: geometry validation report generator flow."""

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
from api.services.geometry_validation_report import create_geometry_validation_report
from api.supabase_client import SupabaseHTTPError


class FakeSupabaseClient:
    def __init__(self) -> None:
        self.projects: dict[str, dict[str, Any]] = {}
        self.file_objects: dict[str, dict[str, Any]] = {}
        self.geometry_revisions: dict[str, dict[str, Any]] = {}
        self.geometry_validation_reports: dict[str, dict[str, Any]] = {}
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
        if table != "app.geometry_revisions":
            return []

        rows = list(self.geometry_revisions.values())
        for key, raw_filter in filters.items():
            rows = [row for row in rows if self._matches(row, key, raw_filter)]

        updated: list[dict[str, Any]] = []
        now = datetime.now(timezone.utc).isoformat()
        for row in rows:
            current = self.geometry_revisions[str(row["id"])]
            current.update(payload)
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

    with tempfile.TemporaryDirectory(prefix="vrs_h1e2t3_ok_") as tmp:
        tmp_path = Path(tmp) / "part.dxf"
        doc = ezdxf.new("R2010")
        msp = doc.modelspace()
        msp.add_lwpolyline([(0.0, 0.0), (100.0, 0.0), (100.0, 70.0), (0.0, 70.0)], dxfattribs={"layer": "CUT_OUTER", "closed": True})
        msp.add_lwpolyline([(10.0, 10.0), (30.0, 10.0), (30.0, 30.0), (10.0, 30.0)], dxfattribs={"layer": "CUT_INNER", "closed": True})
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


def _assert_issue_sorting(issues: list[dict[str, Any]]) -> None:
    severity_rank = {"error": 0, "warning": 1, "info": 2}
    keys = []
    for issue in issues:
        keys.append((
            severity_rank.get(str(issue.get("severity")), 99),
            str(issue.get("code", "")),
            str(issue.get("path", "")),
            str(issue.get("message", "")),
        ))
    if keys != sorted(keys):
        raise RuntimeError("issues list is not deterministically ordered")


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

        ok_revisions = [row for row in fake.geometry_revisions.values() if str(row.get("source_file_object_id")) == ok_file_id]
        if len(ok_revisions) != 1:
            raise RuntimeError(f"expected 1 geometry revision for ok file, got {len(ok_revisions)}")
        ok_revision = ok_revisions[0]

        if ok_revision.get("status") != "validated":
            raise RuntimeError("valid geometry should end in validated status")

        ok_reports = [
            row for row in fake.geometry_validation_reports.values() if str(row.get("geometry_revision_id")) == str(ok_revision.get("id"))
        ]
        if len(ok_reports) != 1:
            raise RuntimeError(f"expected 1 validation report for valid geometry, got {len(ok_reports)}")

        ok_report = ok_reports[0]
        if ok_report.get("status") != "validated":
            raise RuntimeError("validation report status mismatch for valid geometry")
        if ok_report.get("validation_seq") != 1:
            raise RuntimeError("validation_seq must start from 1")
        if ok_report.get("validator_version") != "geometry_validator.v1":
            raise RuntimeError("validator_version mismatch")

        ok_summary = ok_report.get("summary_jsonb")
        if not isinstance(ok_summary, dict):
            raise RuntimeError("summary_jsonb missing for valid geometry")
        if ok_summary.get("is_pass") is not True:
            raise RuntimeError("valid geometry summary must be pass")
        if int(ok_summary.get("error_count", -1)) != 0:
            raise RuntimeError("valid geometry summary must have zero errors")
        if ok_summary.get("canonical_format_version") != "normalized_geometry.v1":
            raise RuntimeError("summary canonical_format_version mismatch")

        ok_report_json = ok_report.get("report_jsonb")
        if not isinstance(ok_report_json, dict):
            raise RuntimeError("report_jsonb missing for valid geometry")
        if not isinstance(ok_report_json.get("issues"), list):
            raise RuntimeError("report_jsonb.issues missing")
        _assert_issue_sorting(ok_report_json.get("issues") or [])
        if not isinstance(ok_report_json.get("severity_summary"), dict):
            raise RuntimeError("report_jsonb.severity_summary missing")
        if not isinstance(ok_report_json.get("topology_checks"), dict):
            raise RuntimeError("report_jsonb.topology_checks missing")
        geometry_ref = ok_report_json.get("validated_geometry_ref")
        if not isinstance(geometry_ref, dict) or str(geometry_ref.get("geometry_revision_id")) != str(ok_revision.get("id")):
            raise RuntimeError("validated_geometry_ref missing or inconsistent")

        second_valid_report_bundle = create_geometry_validation_report(
            supabase=fake,  # type: ignore[arg-type]
            access_token="token-u1",
            geometry_revision=ok_revision,
        )
        second_valid_report = second_valid_report_bundle.get("validation_report")
        if not isinstance(second_valid_report, dict):
            raise RuntimeError("second validation report result missing")
        if second_valid_report.get("validation_seq") != 2:
            raise RuntimeError("validation_seq should increment on repeated validation")

        bad_revision = fake.insert_row(
            table="app.geometry_revisions",
            access_token="token-u1",
            payload={
                "project_id": project_id,
                "source_file_object_id": str(uuid4()),
                "geometry_role": "part",
                "revision_no": 999,
                "status": "parsed",
                "canonical_format_version": "normalized_geometry.v1",
                "canonical_geometry_jsonb": {
                    "geometry_role": "part",
                    "format_version": "normalized_geometry.v1",
                    "outer_ring": [],
                    "hole_rings": "invalid",
                    "bbox": {},
                    "units": "mm",
                },
                "canonical_hash_sha256": "not-a-real-hash",
                "source_hash_sha256": "",
                "bbox_jsonb": {},
                "created_by": user_id,
            },
        )

        bad_report_bundle = create_geometry_validation_report(
            supabase=fake,  # type: ignore[arg-type]
            access_token="token-u1",
            geometry_revision=bad_revision,
        )
        bad_report = bad_report_bundle.get("validation_report")
        bad_revision_after = bad_report_bundle.get("geometry_revision")
        if not isinstance(bad_report, dict) or not isinstance(bad_revision_after, dict):
            raise RuntimeError("rejected validation bundle malformed")

        if bad_report.get("status") != "rejected":
            raise RuntimeError("bad canonical geometry must generate rejected report")
        if bad_revision_after.get("status") != "rejected":
            raise RuntimeError("geometry revision status must become rejected")

        bad_summary = bad_report.get("summary_jsonb")
        if not isinstance(bad_summary, dict) or bad_summary.get("is_pass") is not False:
            raise RuntimeError("rejected summary must have is_pass=false")
        if int(bad_summary.get("error_count", 0)) <= 0:
            raise RuntimeError("rejected summary must contain at least one error")

        bad_report_json = bad_report.get("report_jsonb")
        if not isinstance(bad_report_json, dict):
            raise RuntimeError("rejected report_jsonb missing")
        bad_issues = bad_report_json.get("issues")
        if not isinstance(bad_issues, list) or not bad_issues:
            raise RuntimeError("rejected report must include issues")
        if not any(str(issue.get("severity")) == "error" for issue in bad_issues if isinstance(issue, dict)):
            raise RuntimeError("rejected report must contain error severity issues")
        _assert_issue_sorting([issue for issue in bad_issues if isinstance(issue, dict)])

        invalid_upload_resp = client.post(
            f"/v1/projects/{project_id}/files/upload-url",
            headers=headers,
            json={
                "filename": "part_invalid.dxf",
                "content_type": "application/dxf",
                "size_bytes": 32,
                "file_kind": "source_dxf",
            },
        )
        if invalid_upload_resp.status_code != 200:
            raise RuntimeError("invalid upload-url failed")
        invalid_upload = invalid_upload_resp.json()
        invalid_file_id = str(invalid_upload["file_id"])
        invalid_storage_path = str(invalid_upload["storage_path"])
        fake.put_uploaded_object(
            signed_upload_url=str(invalid_upload["upload_url"]),
            blob=b"not-a-dxf",
        )

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
        missing_revisions = [
            row for row in fake.geometry_revisions.values() if str(row.get("source_file_object_id")) == missing_file_id
        ]
        if missing_revisions:
            raise RuntimeError("missing object should not create geometry revision")

        print("[PASS] H1-E2-T3 validation report generator smoke passed")
        return 0
    finally:
        app.dependency_overrides.clear()


if __name__ == "__main__":
    raise SystemExit(main())
