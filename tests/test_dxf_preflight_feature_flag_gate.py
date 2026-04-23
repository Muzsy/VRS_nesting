"""DXF Prefilter E3-T5 — Feature flag + rollout gate unit tests.

Current-code truth under test:
- Settings.dxf_preflight_required is parsed from API_DXF_PREFLIGHT_REQUIRED env (alias: DXF_PREFLIGHT_REQUIRED).
- complete_upload flag ON: registers validate_dxf_file_async + run_preflight_for_upload.
- complete_upload flag OFF: registers validate_dxf_file_async + import_source_dxf_geometry_revision_async.
- replace_file flag OFF: raises HTTP 409 without opening a replacement upload slot.
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import BackgroundTasks, HTTPException

import api.routes.files as files_mod
from api.auth import AuthenticatedUser
from api.config import Settings, load_settings
from api.routes.files import (
    FileCompleteRequest,
    FileReplaceRequest,
    complete_upload,
    replace_file,
)


# ---------------------------------------------------------------------------
# Settings parse tests
# ---------------------------------------------------------------------------


def _make_minimal_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    base = {
        "SUPABASE_URL": "http://fake.local",
        "SUPABASE_ANON_KEY": "anon-key",
    }
    if extra:
        base.update(extra)
    return base


def test_settings_dxf_preflight_required_default_is_true(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("API_DXF_PREFLIGHT_REQUIRED", "DXF_PREFLIGHT_REQUIRED"):
        monkeypatch.delenv(key, raising=False)
    env = _make_minimal_env()
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    settings = load_settings()
    assert settings.dxf_preflight_required is True


@pytest.mark.parametrize("raw", ["1", "true", "yes", "on", "TRUE", "YES"])
def test_settings_dxf_preflight_required_truthy(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    env = _make_minimal_env({"API_DXF_PREFLIGHT_REQUIRED": raw})
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    settings = load_settings()
    assert settings.dxf_preflight_required is True


@pytest.mark.parametrize("raw", ["0", "false", "no", "off", "FALSE", "OFF"])
def test_settings_dxf_preflight_required_falsy(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    env = _make_minimal_env({"API_DXF_PREFLIGHT_REQUIRED": raw})
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    settings = load_settings()
    assert settings.dxf_preflight_required is False


def test_settings_dxf_preflight_required_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("API_DXF_PREFLIGHT_REQUIRED", raising=False)
    env = _make_minimal_env({"DXF_PREFLIGHT_REQUIRED": "0"})
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    settings = load_settings()
    assert settings.dxf_preflight_required is False


def test_settings_canonical_env_takes_priority_over_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    env = _make_minimal_env({"API_DXF_PREFLIGHT_REQUIRED": "1", "DXF_PREFLIGHT_REQUIRED": "0"})
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    settings = load_settings()
    assert settings.dxf_preflight_required is True


# ---------------------------------------------------------------------------
# Minimal fake Supabase
# ---------------------------------------------------------------------------


def _parse_eq(value: Any) -> str | None:
    raw = str(value or "")
    return raw[3:] if raw.startswith("eq.") else None


class _FlagFakeSupabase:
    def __init__(self, *, project_id: str, owner_user_id: str) -> None:
        self.projects: list[dict[str, Any]] = [
            {"id": project_id, "owner_user_id": owner_user_id, "lifecycle": "active"}
        ]
        self.file_objects: list[dict[str, Any]] = []
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
                dict(r)
                for r in self.projects
                if (id_eq is None or str(r.get("id")) == id_eq)
                and (owner_eq is None or str(r.get("owner_user_id")) == owner_eq)
                and str(r.get("lifecycle")) != "archived"
            ]
            limit = str(params.get("limit", "")).strip()
            return rows[: int(limit)] if limit.isdigit() else rows

        if table == "app.file_objects":
            id_eq = _parse_eq(params.get("id"))
            proj_eq = _parse_eq(params.get("project_id"))
            rows = [
                dict(r)
                for r in self.file_objects
                if (id_eq is None or str(r.get("id")) == id_eq)
                and (proj_eq is None or str(r.get("project_id")) == proj_eq)
            ]
            limit = str(params.get("limit", "")).strip()
            return rows[: int(limit)] if limit.isdigit() else rows

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
# Fixtures
# ---------------------------------------------------------------------------

_PROJECT_ID = "a2000000-0000-0000-0000-000000000001"
_OWNER_ID = "b2000000-0000-0000-0000-000000000001"
_USER = AuthenticatedUser(id=_OWNER_ID, access_token="tok-flag")

_EXISTING_FILE_ID = "c2000000-0000-0000-0000-000000000001"
_EXISTING_FILE_OBJECT: dict[str, Any] = {
    "id": _EXISTING_FILE_ID,
    "project_id": _PROJECT_ID,
    "file_kind": "source_dxf",
    "storage_bucket": "test-bucket",
    "storage_path": f"projects/{_PROJECT_ID}/files/{_EXISTING_FILE_ID}/part.dxf",
    "file_name": "part.dxf",
    "uploaded_by": _OWNER_ID,
    "created_at": "2026-04-23T00:00:00+00:00",
}


def _make_settings(*, dxf_preflight_required: bool) -> Settings:
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


def _make_supabase(*, with_existing_file: bool = False) -> _FlagFakeSupabase:
    sb = _FlagFakeSupabase(project_id=_PROJECT_ID, owner_user_id=_OWNER_ID)
    if with_existing_file:
        sb.file_objects.append(dict(_EXISTING_FILE_OBJECT))
    return sb


def _patch_load_metadata(monkeypatch: pytest.MonkeyPatch, *, storage_path: str) -> None:
    filename = storage_path.rsplit("/", 1)[-1]
    monkeypatch.setattr(
        files_mod,
        "load_file_ingest_metadata",
        lambda **_kw: SimpleNamespace(
            sha256="deadbeef" * 8,
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


# ---------------------------------------------------------------------------
# complete_upload — flag ON
# ---------------------------------------------------------------------------


def test_complete_upload_flag_on_registers_preflight_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sb = _make_supabase()
    new_file_id = str(uuid4())
    storage_path = f"projects/{_PROJECT_ID}/files/{new_file_id}/part.dxf"
    _patch_load_metadata(monkeypatch, storage_path=storage_path)
    monkeypatch.setattr(files_mod, "validate_dxf_file_async", lambda **_kw: None)
    monkeypatch.setattr(files_mod, "run_preflight_for_upload", lambda **_kw: None)
    monkeypatch.setattr(files_mod, "import_source_dxf_geometry_revision_async", lambda **_kw: None)

    bg = BackgroundTasks()
    req = FileCompleteRequest(
        file_id=UUID(new_file_id),
        storage_path=storage_path,
        file_kind="source_dxf",
    )
    complete_upload(
        project_id=UUID(_PROJECT_ID),
        req=req,
        background_tasks=bg,
        user=_USER,
        supabase=sb,
        settings=_make_settings(dxf_preflight_required=True),
    )

    assert len(bg.tasks) == 2
    task_funcs = {t.func for t in bg.tasks}
    assert files_mod.validate_dxf_file_async in task_funcs
    assert files_mod.run_preflight_for_upload in task_funcs
    assert files_mod.import_source_dxf_geometry_revision_async not in task_funcs


def test_complete_upload_flag_on_preflight_task_uses_correct_file_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sb = _make_supabase()
    new_file_id = str(uuid4())
    storage_path = f"projects/{_PROJECT_ID}/files/{new_file_id}/part.dxf"
    _patch_load_metadata(monkeypatch, storage_path=storage_path)
    monkeypatch.setattr(files_mod, "validate_dxf_file_async", lambda **_kw: None)
    monkeypatch.setattr(files_mod, "run_preflight_for_upload", lambda **_kw: None)

    bg = BackgroundTasks()
    req = FileCompleteRequest(
        file_id=UUID(new_file_id),
        storage_path=storage_path,
        file_kind="source_dxf",
    )
    complete_upload(
        project_id=UUID(_PROJECT_ID),
        req=req,
        background_tasks=bg,
        user=_USER,
        supabase=sb,
        settings=_make_settings(dxf_preflight_required=True),
    )

    preflight_task = next(t for t in bg.tasks if t.func is files_mod.run_preflight_for_upload)
    assert preflight_task.kwargs.get("source_file_object_id") == new_file_id


# ---------------------------------------------------------------------------
# complete_upload — flag OFF
# ---------------------------------------------------------------------------


def test_complete_upload_flag_off_registers_legacy_import_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sb = _make_supabase()
    new_file_id = str(uuid4())
    storage_path = f"projects/{_PROJECT_ID}/files/{new_file_id}/part.dxf"
    _patch_load_metadata(monkeypatch, storage_path=storage_path)
    monkeypatch.setattr(files_mod, "validate_dxf_file_async", lambda **_kw: None)
    monkeypatch.setattr(files_mod, "run_preflight_for_upload", lambda **_kw: None)
    monkeypatch.setattr(files_mod, "import_source_dxf_geometry_revision_async", lambda **_kw: None)

    bg = BackgroundTasks()
    req = FileCompleteRequest(
        file_id=UUID(new_file_id),
        storage_path=storage_path,
        file_kind="source_dxf",
    )
    complete_upload(
        project_id=UUID(_PROJECT_ID),
        req=req,
        background_tasks=bg,
        user=_USER,
        supabase=sb,
        settings=_make_settings(dxf_preflight_required=False),
    )

    assert len(bg.tasks) == 2
    task_funcs = {t.func for t in bg.tasks}
    assert files_mod.validate_dxf_file_async in task_funcs
    assert files_mod.import_source_dxf_geometry_revision_async in task_funcs
    assert files_mod.run_preflight_for_upload not in task_funcs


def test_complete_upload_flag_off_legacy_import_uses_correct_file_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sb = _make_supabase()
    new_file_id = str(uuid4())
    storage_path = f"projects/{_PROJECT_ID}/files/{new_file_id}/part.dxf"
    _patch_load_metadata(monkeypatch, storage_path=storage_path)
    monkeypatch.setattr(files_mod, "validate_dxf_file_async", lambda **_kw: None)
    monkeypatch.setattr(files_mod, "import_source_dxf_geometry_revision_async", lambda **_kw: None)

    bg = BackgroundTasks()
    req = FileCompleteRequest(
        file_id=UUID(new_file_id),
        storage_path=storage_path,
        file_kind="source_dxf",
    )
    complete_upload(
        project_id=UUID(_PROJECT_ID),
        req=req,
        background_tasks=bg,
        user=_USER,
        supabase=sb,
        settings=_make_settings(dxf_preflight_required=False),
    )

    import_task = next(
        t for t in bg.tasks if t.func is files_mod.import_source_dxf_geometry_revision_async
    )
    assert import_task.kwargs.get("source_file_object_id") == new_file_id


# ---------------------------------------------------------------------------
# replace_file — flag gate
# ---------------------------------------------------------------------------


def test_replace_file_flag_off_raises_http_error() -> None:
    sb = _make_supabase(with_existing_file=True)
    req = FileReplaceRequest(filename="replacement.dxf", size_bytes=1024)
    with pytest.raises(HTTPException) as exc_info:
        replace_file(
            project_id=UUID(_PROJECT_ID),
            file_id=UUID(_EXISTING_FILE_ID),
            req=req,
            user=_USER,
            supabase=sb,
            settings=_make_settings(dxf_preflight_required=False),
        )
    assert exc_info.value.status_code == 409
    assert "disabled" in exc_info.value.detail.lower()


def test_replace_file_flag_off_does_not_open_upload_slot() -> None:
    sb = _make_supabase(with_existing_file=True)
    req = FileReplaceRequest(filename="replacement.dxf", size_bytes=1024)
    try:
        replace_file(
            project_id=UUID(_PROJECT_ID),
            file_id=UUID(_EXISTING_FILE_ID),
            req=req,
            user=_USER,
            supabase=sb,
            settings=_make_settings(dxf_preflight_required=False),
        )
    except HTTPException:
        pass
    assert len(sb.signed_upload_requests) == 0


def test_replace_file_flag_on_proceeds_normally() -> None:
    sb = _make_supabase(with_existing_file=True)
    req = FileReplaceRequest(filename="replacement.dxf", size_bytes=1024)
    result = replace_file(
        project_id=UUID(_PROJECT_ID),
        file_id=UUID(_EXISTING_FILE_ID),
        req=req,
        user=_USER,
        supabase=sb,
        settings=_make_settings(dxf_preflight_required=True),
    )
    assert result.upload_url.startswith("https://upload.local/")
    assert result.replaces_file_id == _EXISTING_FILE_ID
