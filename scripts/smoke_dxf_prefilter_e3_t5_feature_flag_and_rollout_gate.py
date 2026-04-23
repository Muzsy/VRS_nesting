"""DXF Prefilter E3-T5 — Feature flag + rollout gate smoke.

Deterministic, no real I/O. Proves:
1. feature ON: source DXF finalize chooses preflight runtime path (validate + run_preflight_for_upload).
2. feature OFF: source DXF finalize chooses legacy direct geometry import path (validate + import_source_dxf_geometry_revision_async).
3. replacement route OFF: replace_file raises HTTP 409, no upload slot opened.
4. replacement route ON: replace_file returns signed upload slot normally.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4
from unittest.mock import patch
from fastapi import BackgroundTasks, HTTPException

PROJECT_ID = "a3000000-0000-0000-0000-000000000001"
OWNER_ID = "b3000000-0000-0000-0000-000000000001"
EXISTING_FILE_ID = "c3000000-0000-0000-0000-000000000001"

EXISTING_FILE_OBJECT: dict[str, Any] = {
    "id": EXISTING_FILE_ID,
    "project_id": PROJECT_ID,
    "file_kind": "source_dxf",
    "storage_bucket": "test-bucket",
    "storage_path": f"projects/{PROJECT_ID}/files/{EXISTING_FILE_ID}/part.dxf",
    "file_name": "part.dxf",
    "uploaded_by": OWNER_ID,
    "created_at": "2026-04-23T00:00:00+00:00",
}


# ---------------------------------------------------------------------------
# Fake Supabase
# ---------------------------------------------------------------------------


def _parse_eq(value: Any) -> str | None:
    raw = str(value or "")
    return raw[3:] if raw.startswith("eq.") else None


class _SmokeFakeSupabase:
    def __init__(self, *, with_existing_file: bool = False) -> None:
        self.projects: list[dict[str, Any]] = [
            {"id": PROJECT_ID, "owner_user_id": OWNER_ID, "lifecycle": "active"}
        ]
        self.file_objects: list[dict[str, Any]] = []
        if with_existing_file:
            self.file_objects.append(dict(EXISTING_FILE_OBJECT))
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
        row.setdefault("created_at", "2026-04-23T00:00:01+00:00")
        if table == "app.file_objects":
            self.file_objects.append(row)
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


def _make_settings(*, dxf_preflight_required: bool) -> Any:
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
        dxf_preflight_required=dxf_preflight_required,
        allowed_origins=(),
    )


def _make_user() -> Any:
    from api.auth import AuthenticatedUser
    return AuthenticatedUser(id=OWNER_ID, access_token="tok-smoke-e3t5")


# ---------------------------------------------------------------------------
# Scenario 1: feature ON → validate + preflight runtime path
# ---------------------------------------------------------------------------


def scenario_feature_on_preflight_path() -> None:
    print("Scenario 1: feature ON -> validate + run_preflight_for_upload")
    import api.routes.files as files_mod
    from api.routes.files import FileCompleteRequest, complete_upload

    sb = _SmokeFakeSupabase()
    settings = _make_settings(dxf_preflight_required=True)
    user = _make_user()
    new_file_id = str(uuid4())
    storage_path = f"projects/{PROJECT_ID}/files/{new_file_id}/part.dxf"

    with (
        patch.object(files_mod, "load_file_ingest_metadata", return_value=SimpleNamespace(
            sha256="deadbeef" * 8,
            mime_type="application/dxf",
            byte_size=2048,
            file_name="part.dxf",
        )),
        patch.object(files_mod, "canonical_file_name_from_storage_path", side_effect=lambda p: p.rsplit("/", 1)[-1]),
        patch.object(files_mod, "validate_dxf_file_async", side_effect=lambda **_kw: None),
        patch.object(files_mod, "run_preflight_for_upload", side_effect=lambda **_kw: None),
        patch.object(files_mod, "import_source_dxf_geometry_revision_async", side_effect=lambda **_kw: None),
    ):
        bg = BackgroundTasks()
        req = FileCompleteRequest(
            file_id=UUID(new_file_id),
            storage_path=storage_path,
            file_kind="source_dxf",
        )
        complete_upload(
            project_id=UUID(PROJECT_ID),
            req=req,
            background_tasks=bg,
            user=user,
            supabase=sb,
            settings=settings,
        )

        task_funcs = {t.func for t in bg.tasks}
        _assert(len(bg.tasks) == 2, "exactly 2 background tasks registered (flag ON)")
        _assert(files_mod.validate_dxf_file_async in task_funcs, "validate_dxf_file_async registered")
        _assert(files_mod.run_preflight_for_upload in task_funcs, "run_preflight_for_upload registered")
        _assert(
            files_mod.import_source_dxf_geometry_revision_async not in task_funcs,
            "import_source_dxf_geometry_revision_async NOT registered (flag ON)",
        )

        preflight_task = next(t for t in bg.tasks if t.func is files_mod.run_preflight_for_upload)
        _assert(
            preflight_task.kwargs.get("source_file_object_id") == new_file_id,
            "preflight task uses correct source_file_object_id",
        )


# ---------------------------------------------------------------------------
# Scenario 2: feature OFF → validate + legacy direct geometry import path
# ---------------------------------------------------------------------------


def scenario_feature_off_legacy_import_path() -> None:
    print("Scenario 2: feature OFF -> validate + import_source_dxf_geometry_revision_async")
    import api.routes.files as files_mod
    from api.routes.files import FileCompleteRequest, complete_upload

    sb = _SmokeFakeSupabase()
    settings = _make_settings(dxf_preflight_required=False)
    user = _make_user()
    new_file_id = str(uuid4())
    storage_path = f"projects/{PROJECT_ID}/files/{new_file_id}/part.dxf"

    with (
        patch.object(files_mod, "load_file_ingest_metadata", return_value=SimpleNamespace(
            sha256="deadbeef" * 8,
            mime_type="application/dxf",
            byte_size=2048,
            file_name="part.dxf",
        )),
        patch.object(files_mod, "canonical_file_name_from_storage_path", side_effect=lambda p: p.rsplit("/", 1)[-1]),
        patch.object(files_mod, "validate_dxf_file_async", side_effect=lambda **_kw: None),
        patch.object(files_mod, "run_preflight_for_upload", side_effect=lambda **_kw: None),
        patch.object(files_mod, "import_source_dxf_geometry_revision_async", side_effect=lambda **_kw: None),
    ):
        bg = BackgroundTasks()
        req = FileCompleteRequest(
            file_id=UUID(new_file_id),
            storage_path=storage_path,
            file_kind="source_dxf",
        )
        complete_upload(
            project_id=UUID(PROJECT_ID),
            req=req,
            background_tasks=bg,
            user=user,
            supabase=sb,
            settings=settings,
        )

        task_funcs = {t.func for t in bg.tasks}
        _assert(len(bg.tasks) == 2, "exactly 2 background tasks registered (flag OFF)")
        _assert(files_mod.validate_dxf_file_async in task_funcs, "validate_dxf_file_async registered")
        _assert(
            files_mod.import_source_dxf_geometry_revision_async in task_funcs,
            "import_source_dxf_geometry_revision_async registered (legacy path)",
        )
        _assert(
            files_mod.run_preflight_for_upload not in task_funcs,
            "run_preflight_for_upload NOT registered (flag OFF)",
        )

        import_task = next(
            t for t in bg.tasks if t.func is files_mod.import_source_dxf_geometry_revision_async
        )
        _assert(
            import_task.kwargs.get("source_file_object_id") == new_file_id,
            "legacy import task uses correct source_file_object_id",
        )


# ---------------------------------------------------------------------------
# Scenario 3: replacement route flag OFF → 409, no upload slot
# ---------------------------------------------------------------------------


def scenario_replacement_route_flag_off() -> None:
    print("Scenario 3: replacement route flag OFF -> HTTP 409, no upload slot opened")
    from api.routes.files import FileReplaceRequest, replace_file

    sb = _SmokeFakeSupabase(with_existing_file=True)
    settings = _make_settings(dxf_preflight_required=False)
    user = _make_user()

    req = FileReplaceRequest(filename="replacement.dxf", size_bytes=2048)
    raised = False
    try:
        replace_file(
            project_id=UUID(PROJECT_ID),
            file_id=UUID(EXISTING_FILE_ID),
            req=req,
            user=user,
            supabase=sb,
            settings=settings,
        )
    except HTTPException as exc:
        raised = True
        _assert(exc.status_code == 409, f"HTTP status is 409 (got {exc.status_code})")
        _assert("disabled" in exc.detail.lower(), f"detail mentions 'disabled': {exc.detail}")

    _assert(raised, "HTTPException was raised (flag OFF)")
    _assert(len(sb.signed_upload_requests) == 0, "no signed upload URL was created")


# ---------------------------------------------------------------------------
# Scenario 4: replacement route flag ON → proceeds normally
# ---------------------------------------------------------------------------


def scenario_replacement_route_flag_on() -> None:
    print("Scenario 4: replacement route flag ON -> signed upload slot returned")
    from api.routes.files import FileReplaceRequest, replace_file

    sb = _SmokeFakeSupabase(with_existing_file=True)
    settings = _make_settings(dxf_preflight_required=True)
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
    _assert(result.replaces_file_id == EXISTING_FILE_ID, "replaces_file_id matches target")
    _assert(len(sb.signed_upload_requests) == 1, "exactly 1 signed upload URL created")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    print("=== DXF E3-T5 smoke: feature flag + rollout gate ===")
    scenario_feature_on_preflight_path()
    scenario_feature_off_legacy_import_path()
    scenario_replacement_route_flag_off()
    scenario_replacement_route_flag_on()
    print("=== ALL SCENARIOS PASSED ===")
