"""DXF Prefilter E3-T4 — Replace file + implicit preflight rerun unit tests.

Current-code truth under test:
- POST /projects/{project_id}/files/{file_id}/replace returns signed upload slot.
- replace route validates target existence, project membership, source_dxf kind.
- complete_upload with replaces_file_object_id persists lineage truth.
- complete_upload registers exactly the same 2 background tasks for replacement finalize.
- No separate manual rerun endpoint exists.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import BackgroundTasks, HTTPException

import api.routes.files as files_mod
from api.auth import AuthenticatedUser
from api.config import Settings
from api.routes.files import (
    FileCompleteRequest,
    FileReplaceRequest,
    complete_upload,
    replace_file,
)


# ---------------------------------------------------------------------------
# Minimal fake Supabase
# ---------------------------------------------------------------------------


def _parse_eq(value: Any) -> str | None:
    raw = str(value or "")
    if raw.startswith("eq."):
        return raw[3:]
    return None


class _ReplaceFakeSupabase:
    def __init__(self, *, project_id: str, owner_user_id: str) -> None:
        self.projects: list[dict[str, Any]] = [
            {"id": project_id, "owner_user_id": owner_user_id, "lifecycle": "active"}
        ]
        self.file_objects: list[dict[str, Any]] = []
        self.preflight_runs: list[dict[str, Any]] = []
        self.preflight_diagnostics: list[dict[str, Any]] = []
        self.preflight_artifacts: list[dict[str, Any]] = []
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
                dict(row)
                for row in self.projects
                if (id_eq is None or str(row.get("id")) == id_eq)
                and (owner_eq is None or str(row.get("owner_user_id")) == owner_eq)
                and str(row.get("lifecycle")) != "archived"
            ]
            limit_raw = str(params.get("limit", "")).strip()
            if limit_raw.isdigit():
                rows = rows[: int(limit_raw)]
            return rows

        if table == "app.file_objects":
            id_eq = _parse_eq(params.get("id"))
            project_eq = _parse_eq(params.get("project_id"))
            rows = [
                dict(row)
                for row in self.file_objects
                if (id_eq is None or str(row.get("id")) == id_eq)
                and (project_eq is None or str(row.get("project_id")) == project_eq)
            ]
            limit_raw = str(params.get("limit", "")).strip()
            if limit_raw.isdigit():
                rows = rows[: int(limit_raw)]
            return rows

        return []

    def insert_row(self, *, table: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        row = dict(payload)
        if table == "app.file_objects":
            row.setdefault("created_at", "2026-04-24T00:00:01+00:00")
            self.file_objects.append(row)
            return dict(row)
        if table == "app.preflight_runs":
            row.setdefault("id", self._next_id("pf-run"))
            self.preflight_runs.append(row)
            return dict(row)
        if table == "app.preflight_diagnostics":
            row.setdefault("id", self._next_id("pf-diag"))
            self.preflight_diagnostics.append(row)
            return dict(row)
        if table == "app.preflight_artifacts":
            row.setdefault("id", self._next_id("pf-art"))
            self.preflight_artifacts.append(row)
            return dict(row)
        raise AssertionError(f"unexpected insert_row table={table!r}")

    def create_signed_upload_url(
        self, *, access_token: str, bucket: str, object_key: str, expires_in: int
    ) -> dict[str, Any]:
        token = self._next_id("signed")
        self.signed_upload_requests.append(
            {"bucket": bucket, "object_key": object_key, "expires_in": expires_in}
        )
        return {
            "upload_url": f"https://upload.local/{token}",
            "expires_at": "2026-12-31T00:00:00+00:00",
        }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_PROJECT_ID = "a0000000-0000-0000-0000-000000000001"
_OWNER_ID = "b0000000-0000-0000-0000-000000000001"
_USER = AuthenticatedUser(id=_OWNER_ID, access_token="tok-replace")

_SETTINGS = Settings(
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
    dxf_preflight_required=True,
    allowed_origins=(),
)

_EXISTING_FILE_ID = "c0000000-0000-0000-0000-000000000001"
_EXISTING_FILE_OBJECT: dict[str, Any] = {
    "id": _EXISTING_FILE_ID,
    "project_id": _PROJECT_ID,
    "file_kind": "source_dxf",
    "storage_bucket": "test-bucket",
    "storage_path": f"projects/{_PROJECT_ID}/files/{_EXISTING_FILE_ID}/part.dxf",
    "file_name": "part.dxf",
    "uploaded_by": _OWNER_ID,
    "created_at": "2026-04-24T00:00:00+00:00",
}


def _make_supabase(*, with_existing_file: bool = True) -> _ReplaceFakeSupabase:
    sb = _ReplaceFakeSupabase(project_id=_PROJECT_ID, owner_user_id=_OWNER_ID)
    if with_existing_file:
        sb.file_objects.append(dict(_EXISTING_FILE_OBJECT))
    return sb


# ---------------------------------------------------------------------------
# replace_file route tests
# ---------------------------------------------------------------------------


def test_replace_route_returns_signed_upload_slot() -> None:
    sb = _make_supabase()
    req = FileReplaceRequest(
        filename="replacement.dxf",
        content_type="application/dxf",
        size_bytes=1024,
    )
    result = replace_file(
        project_id=UUID(_PROJECT_ID),
        file_id=UUID(_EXISTING_FILE_ID),
        req=req,
        user=_USER,
        supabase=sb,
        settings=_SETTINGS,
    )

    assert result.upload_url.startswith("https://upload.local/")
    assert result.file_id != _EXISTING_FILE_ID
    assert result.replaces_file_id == _EXISTING_FILE_ID
    assert result.storage_bucket == "test-bucket"
    assert f"/{result.file_id}/" in result.storage_path
    assert result.storage_path.endswith("replacement.dxf")
    assert len(sb.signed_upload_requests) == 1


_ARTIFACT_FILE_ID = "d0000000-0000-0000-0000-000000000001"
_OTHER_PROJ_FILE_ID = "e0000000-0000-0000-0000-000000000001"
_OTHER_PROJECT_ID = "f0000000-0000-0000-0000-000000000001"


def test_replace_route_rejects_non_source_dxf_target() -> None:
    sb = _make_supabase(with_existing_file=False)
    artifact_file: dict[str, Any] = {
        "id": _ARTIFACT_FILE_ID,
        "project_id": _PROJECT_ID,
        "file_kind": "artifact",
        "storage_bucket": "test-bucket",
        "storage_path": f"projects/{_PROJECT_ID}/files/{_ARTIFACT_FILE_ID}/out.dxf",
        "file_name": "out.dxf",
        "uploaded_by": _OWNER_ID,
        "created_at": "2026-04-24T00:00:00+00:00",
    }
    sb.file_objects.append(artifact_file)

    req = FileReplaceRequest(filename="new.dxf", size_bytes=1024)
    with pytest.raises(HTTPException) as exc_info:
        replace_file(
            project_id=UUID(_PROJECT_ID),
            file_id=UUID(_ARTIFACT_FILE_ID),
            req=req,
            user=_USER,
            supabase=sb,
            settings=_SETTINGS,
        )
    assert exc_info.value.status_code == 400
    assert "source_dxf" in exc_info.value.detail


def test_replace_route_rejects_wrong_project_target() -> None:
    sb = _make_supabase(with_existing_file=False)
    other_project_file: dict[str, Any] = {
        "id": _OTHER_PROJ_FILE_ID,
        "project_id": _OTHER_PROJECT_ID,
        "file_kind": "source_dxf",
        "storage_bucket": "test-bucket",
        "storage_path": f"projects/{_OTHER_PROJECT_ID}/files/{_OTHER_PROJ_FILE_ID}/part.dxf",
        "file_name": "part.dxf",
        "uploaded_by": _OWNER_ID,
        "created_at": "2026-04-24T00:00:00+00:00",
    }
    sb.file_objects.append(other_project_file)

    req = FileReplaceRequest(filename="new.dxf", size_bytes=1024)
    with pytest.raises(HTTPException) as exc_info:
        replace_file(
            project_id=UUID(_PROJECT_ID),
            file_id=UUID(_OTHER_PROJ_FILE_ID),
            req=req,
            user=_USER,
            supabase=sb,
            settings=_SETTINGS,
        )
    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# complete_upload replacement finalize tests
# ---------------------------------------------------------------------------


def _patch_load_metadata(monkeypatch: pytest.MonkeyPatch, *, storage_path: str) -> None:
    filename = storage_path.rsplit("/", 1)[-1]
    monkeypatch.setattr(
        files_mod,
        "load_file_ingest_metadata",
        lambda **_kwargs: SimpleNamespace(
            sha256="abc123def456",
            mime_type="application/dxf",
            byte_size=2048,
            file_name=filename,
        ),
    )
    monkeypatch.setattr(
        files_mod,
        "canonical_file_name_from_storage_path",
        lambda path: path.rsplit("/", 1)[-1],
    )


def test_complete_upload_replacement_finalize_persists_lineage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sb = _make_supabase()
    new_file_id = str(uuid4())
    storage_path = f"projects/{_PROJECT_ID}/files/{new_file_id}/replacement.dxf"

    _patch_load_metadata(monkeypatch, storage_path=storage_path)

    monkeypatch.setattr(files_mod, "validate_dxf_file_async", lambda **_kwargs: None)
    monkeypatch.setattr(files_mod, "run_preflight_for_upload", lambda **_kwargs: None)

    req = FileCompleteRequest(
        file_id=UUID(new_file_id),
        storage_path=storage_path,
        file_kind="source_dxf",
        replaces_file_object_id=UUID(_EXISTING_FILE_ID),
    )

    result = complete_upload(
        project_id=UUID(_PROJECT_ID),
        req=req,
        background_tasks=BackgroundTasks(),
        user=_USER,
        supabase=sb,
        settings=_SETTINGS,
    )

    assert result.id == new_file_id

    inserted = next((f for f in sb.file_objects if f.get("id") == new_file_id), None)
    assert inserted is not None
    assert inserted.get("replaces_file_object_id") == _EXISTING_FILE_ID

    original = next((f for f in sb.file_objects if f.get("id") == _EXISTING_FILE_ID), None)
    assert original is not None
    assert original.get("replaces_file_object_id") is None


def test_complete_upload_replacement_registers_two_background_tasks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sb = _make_supabase()
    new_file_id = str(uuid4())
    storage_path = f"projects/{_PROJECT_ID}/files/{new_file_id}/replacement.dxf"

    _patch_load_metadata(monkeypatch, storage_path=storage_path)

    validate_calls: list[dict[str, Any]] = []
    preflight_calls: list[dict[str, Any]] = []

    monkeypatch.setattr(
        files_mod,
        "validate_dxf_file_async",
        lambda **kwargs: validate_calls.append(kwargs),
    )
    monkeypatch.setattr(
        files_mod,
        "run_preflight_for_upload",
        lambda **kwargs: preflight_calls.append(kwargs),
    )

    bg = BackgroundTasks()
    req = FileCompleteRequest(
        file_id=UUID(new_file_id),
        storage_path=storage_path,
        file_kind="source_dxf",
        replaces_file_object_id=UUID(_EXISTING_FILE_ID),
    )
    complete_upload(
        project_id=UUID(_PROJECT_ID),
        req=req,
        background_tasks=bg,
        user=_USER,
        supabase=sb,
        settings=_SETTINGS,
    )

    assert len(bg.tasks) == 2

    task_funcs = {task.func for task in bg.tasks}
    assert files_mod.validate_dxf_file_async in task_funcs
    assert files_mod.run_preflight_for_upload in task_funcs

    preflight_task = next(t for t in bg.tasks if t.func is files_mod.run_preflight_for_upload)
    assert preflight_task.kwargs.get("source_file_object_id") == new_file_id


def test_complete_upload_without_replacement_no_lineage_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sb = _make_supabase(with_existing_file=False)
    new_file_id = str(uuid4())
    storage_path = f"projects/{_PROJECT_ID}/files/{new_file_id}/first_upload.dxf"

    _patch_load_metadata(monkeypatch, storage_path=storage_path)
    monkeypatch.setattr(files_mod, "validate_dxf_file_async", lambda **_kwargs: None)
    monkeypatch.setattr(files_mod, "run_preflight_for_upload", lambda **_kwargs: None)

    req = FileCompleteRequest(
        file_id=UUID(new_file_id),
        storage_path=storage_path,
        file_kind="source_dxf",
    )
    complete_upload(
        project_id=UUID(_PROJECT_ID),
        req=req,
        background_tasks=BackgroundTasks(),
        user=_USER,
        supabase=sb,
        settings=_SETTINGS,
    )

    inserted = next((f for f in sb.file_objects if f.get("id") == new_file_id), None)
    assert inserted is not None
    assert "replaces_file_object_id" not in inserted


# ---------------------------------------------------------------------------
# No separate rerun endpoint guard
# ---------------------------------------------------------------------------


def test_no_manual_rerun_endpoint_exists() -> None:
    import api.main as main_mod

    app = main_mod.app
    route_paths = {getattr(r, "path", "") for r in app.routes}
    # The files router must not have a manual preflight-rerun route.
    # (Nesting runs have their own rerun route elsewhere — not in scope here.)
    dxf_rerun_routes = [
        p for p in route_paths
        if "files" in p and "rerun" in p.lower()
    ]
    assert not dxf_rerun_routes, f"unexpected DXF files rerun routes found: {dxf_rerun_routes}"
