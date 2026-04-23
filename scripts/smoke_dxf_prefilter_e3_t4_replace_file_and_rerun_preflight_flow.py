"""DXF Prefilter E3-T4 — Replace file + implicit preflight rerun smoke.

Deterministic, no real I/O. Proves:
1. replace route -> signed upload URL + new file_id + replacement target evidence.
2. finalize replacement -> new file row + persisted lineage truth (replaces_file_object_id).
3. Background tasks registered for new replacement file_id (validate + preflight).
4. Original file_objects row remains intact (not overwritten in-place).
5. No manual rerun endpoint registered on the files router.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4
from unittest.mock import patch
from fastapi import BackgroundTasks, HTTPException

PROJECT_ID = "a1000000-0000-0000-0000-000000000001"
OWNER_ID = "b1000000-0000-0000-0000-000000000001"
EXISTING_FILE_ID = "c1000000-0000-0000-0000-000000000001"

EXISTING_FILE_OBJECT: dict[str, Any] = {
    "id": EXISTING_FILE_ID,
    "project_id": PROJECT_ID,
    "file_kind": "source_dxf",
    "storage_bucket": "test-bucket",
    "storage_path": f"projects/{PROJECT_ID}/files/{EXISTING_FILE_ID}/part.dxf",
    "file_name": "part.dxf",
    "uploaded_by": OWNER_ID,
    "created_at": "2026-04-24T00:00:00+00:00",
}


# ---------------------------------------------------------------------------
# Fake Supabase
# ---------------------------------------------------------------------------


def _parse_eq(value: Any) -> str | None:
    raw = str(value or "")
    return raw[3:] if raw.startswith("eq.") else None


class _SmokeFakeSupabase:
    def __init__(self) -> None:
        self.projects: list[dict[str, Any]] = [
            {"id": PROJECT_ID, "owner_user_id": OWNER_ID, "lifecycle": "active"}
        ]
        self.file_objects: list[dict[str, Any]] = [dict(EXISTING_FILE_OBJECT)]
        self.preflight_runs: list[dict[str, Any]] = []
        self.signed_upload_requests: list[dict[str, Any]] = []
        self._id_counter = 0

    def _next_id(self, prefix: str) -> str:
        self._id_counter += 1
        return f"{prefix}-{self._id_counter}"

    def select_rows(self, *, table: str, access_token: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        if table == "app.projects":
            id_eq = _parse_eq(params.get("id"))
            owner_eq = _parse_eq(params.get("owner_user_id"))
            rows = [
                dict(r) for r in self.projects
                if (id_eq is None or str(r.get("id")) == id_eq)
                and (owner_eq is None or str(r.get("owner_user_id")) == owner_eq)
                and str(r.get("lifecycle")) != "archived"
            ]
            limit = str(params.get("limit", "")).strip()
            return rows[:int(limit)] if limit.isdigit() else rows

        if table == "app.file_objects":
            id_eq = _parse_eq(params.get("id"))
            proj_eq = _parse_eq(params.get("project_id"))
            rows = [
                dict(r) for r in self.file_objects
                if (id_eq is None or str(r.get("id")) == id_eq)
                and (proj_eq is None or str(r.get("project_id")) == proj_eq)
            ]
            limit = str(params.get("limit", "")).strip()
            return rows[:int(limit)] if limit.isdigit() else rows

        return []

    def insert_row(self, *, table: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        row = dict(payload)
        if table == "app.file_objects":
            row.setdefault("created_at", "2026-04-24T00:00:01+00:00")
            self.file_objects.append(row)
        elif table in ("app.preflight_runs", "app.preflight_diagnostics", "app.preflight_artifacts"):
            row.setdefault("id", self._next_id("row"))
            self.preflight_runs.append(row)
        return dict(row)

    def create_signed_upload_url(
        self, *, access_token: str, bucket: str, object_key: str, expires_in: int
    ) -> dict[str, Any]:
        token = self._next_id("signed")
        self.signed_upload_requests.append({"bucket": bucket, "object_key": object_key})
        return {
            "upload_url": f"https://upload.local/{token}",
            "expires_at": "2026-12-31T00:00:00+00:00",
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert(condition: bool, msg: str) -> None:
    if not condition:
        print(f"  FAIL: {msg}", file=sys.stderr)
        sys.exit(1)
    print(f"  OK: {msg}")


def _make_settings() -> Any:
    from api.config import Settings
    return Settings(
        supabase_url="http://fake.local",
        supabase_anon_key="anon",
        supabase_project_ref="ref",
        supabase_db_password="pw",
        database_url="postgresql://fake",
        storage_bucket="test-bucket",
        max_dxf_size_mb=50,
        rate_limit_window_s=60,
        rate_limit_runs_per_window=100,
        rate_limit_bundles_per_window=100,
        rate_limit_upload_urls_per_window=100,
        signed_url_ttl_s=3600,
        enable_security_headers=False,
        allowed_origins=(),
    )


def _make_user() -> Any:
    from api.auth import AuthenticatedUser
    return AuthenticatedUser(id=OWNER_ID, access_token="tok-smoke")


# ---------------------------------------------------------------------------
# Scenario 1: replace route -> signed slot + new file_id + replacement evidence
# ---------------------------------------------------------------------------

def scenario_replace_route_returns_signed_slot() -> None:
    print("Scenario 1: replace route -> signed upload slot")
    import api.routes.files as files_mod
    from api.routes.files import FileReplaceRequest, replace_file

    sb = _SmokeFakeSupabase()
    settings = _make_settings()
    user = _make_user()

    req = FileReplaceRequest(filename="replacement.dxf", size_bytes=2048)
    result = replace_file(
        project_id=UUID(PROJECT_ID),
        file_id=UUID(EXISTING_FILE_ID),
        req=req,
        user=user,
        supabase=sb,
        settings=settings,
    )

    _assert(result.upload_url.startswith("https://upload.local/"), "upload_url is a signed URL")
    _assert(result.file_id != EXISTING_FILE_ID, "new file_id is different from target")
    _assert(result.replaces_file_id == EXISTING_FILE_ID, "replaces_file_id matches target")
    _assert(result.storage_bucket == "test-bucket", "storage_bucket correct")
    _assert(f"/{result.file_id}/" in result.storage_path, "storage_path contains new file_id")
    _assert(result.storage_path.endswith("replacement.dxf"), "storage_path ends with filename")
    _assert(len(sb.signed_upload_requests) == 1, "exactly 1 signed upload request made")
    _assert(len(sb.file_objects) == 1, "original file_objects row not touched (no insert yet)")

    return result.file_id


# ---------------------------------------------------------------------------
# Scenario 2: finalize replacement -> persisted lineage + implicit preflight rerun
# ---------------------------------------------------------------------------

def scenario_finalize_replacement(new_file_id: str) -> None:
    print("Scenario 2: finalize replacement -> lineage truth + background tasks")
    import api.routes.files as files_mod
    from api.routes.files import FileCompleteRequest, complete_upload

    sb = _SmokeFakeSupabase()
    settings = _make_settings()
    user = _make_user()

    storage_path = f"projects/{PROJECT_ID}/files/{new_file_id}/replacement.dxf"

    validate_calls: list[dict[str, Any]] = []
    preflight_calls: list[dict[str, Any]] = []

    with (
        patch.object(files_mod, "load_file_ingest_metadata", return_value=SimpleNamespace(
            sha256="deadbeef" * 8,
            mime_type="application/dxf",
            byte_size=2048,
            file_name="replacement.dxf",
        )),
        patch.object(files_mod, "canonical_file_name_from_storage_path", side_effect=lambda p: p.rsplit("/", 1)[-1]),
        patch.object(files_mod, "validate_dxf_file_async", side_effect=lambda **kw: validate_calls.append(kw)),
        patch.object(files_mod, "run_preflight_for_upload", side_effect=lambda **kw: preflight_calls.append(kw)),
    ):
        req = FileCompleteRequest(
            file_id=UUID(new_file_id),
            storage_path=storage_path,
            file_kind="source_dxf",
            replaces_file_object_id=UUID(EXISTING_FILE_ID),
        )
        bg = BackgroundTasks()
        result = complete_upload(
            project_id=UUID(PROJECT_ID),
            req=req,
            background_tasks=bg,
            user=user,
            supabase=sb,
            settings=settings,
        )

        _assert(result.id == new_file_id, "new file row has correct id")

        new_row = next((f for f in sb.file_objects if f.get("id") == new_file_id), None)
        _assert(new_row is not None, "new file row inserted")
        _assert(new_row.get("replaces_file_object_id") == EXISTING_FILE_ID, "replaces_file_object_id persisted")

        original_row = next((f for f in sb.file_objects if f.get("id") == EXISTING_FILE_ID), None)
        _assert(original_row is not None, "original file row still exists")
        _assert(original_row.get("replaces_file_object_id") is None, "original row not touched")

        _assert(len(bg.tasks) == 2, "exactly 2 background tasks registered")

        mock_validate = files_mod.validate_dxf_file_async
        mock_preflight = files_mod.run_preflight_for_upload

        validate_registered = any(t.func is mock_validate for t in bg.tasks)
        preflight_registered = any(t.func is mock_preflight for t in bg.tasks)
        _assert(validate_registered, "validate_dxf_file_async task registered")
        _assert(preflight_registered, "run_preflight_for_upload task registered")

        preflight_task = next(t for t in bg.tasks if t.func is mock_preflight)
        _assert(
            preflight_task.kwargs.get("source_file_object_id") == new_file_id,
            "preflight runs for new replacement file_id",
        )


# ---------------------------------------------------------------------------
# Scenario 3: no manual rerun endpoint on the files router
# ---------------------------------------------------------------------------

def scenario_no_rerun_endpoint() -> None:
    print("Scenario 3: no manual rerun endpoint on files router")
    import api.main as main_mod

    app = main_mod.app
    route_paths = [getattr(r, "path", "") for r in app.routes]
    dxf_rerun = [p for p in route_paths if "files" in p and "rerun" in p.lower()]
    _assert(not dxf_rerun, f"no DXF files rerun route exists (found: {dxf_rerun})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== DXF E3-T4 smoke: replace file + implicit preflight rerun ===")
    new_file_id = scenario_replace_route_returns_signed_slot()
    scenario_finalize_replacement(new_file_id)
    scenario_no_rerun_endpoint()
    print("=== ALL SCENARIOS PASSED ===")
