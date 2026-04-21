"""Unit tests for DXF Prefilter E3-T3 geometry import gate integration."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import BackgroundTasks

import api.routes.files as files_mod
from api.auth import AuthenticatedUser
from api.routes.files import FileCompleteRequest, complete_upload
from api.services.dxf_preflight_runtime import run_preflight_for_upload

_RUNTIME_PATCH_BASE = "api.services.dxf_preflight_runtime"


def _make_fake_supabase() -> MagicMock:
    supabase = MagicMock()
    supabase.select_rows.return_value = []
    return supabase


def _persisted_result(
    *,
    acceptance_outcome: str,
    include_normalized_artifact: bool,
) -> dict[str, Any]:
    artifact_refs: list[dict[str, Any]] = []
    if include_normalized_artifact:
        artifact_refs.append(
            {
                "artifact_kind": "normalized_dxf",
                "storage_bucket": "geometry-artifacts",
                "storage_path": "projects/proj-1/preflight/run-1/normalized_dxf/hash.dxf",
            }
        )
    return {
        "preflight_run_id": "run-1",
        "acceptance_outcome": acceptance_outcome,
        "artifact_refs": artifact_refs,
    }


def _patch_runtime_pipeline(
    monkeypatch: Any,
    *,
    acceptance_outcome: str,
    include_normalized_artifact: bool,
) -> dict[str, MagicMock]:
    mocks: dict[str, MagicMock] = {}

    mocks["download"] = MagicMock(return_value=b"FAKE_DXF_BYTES")
    mocks["inspect"] = MagicMock(return_value={"source_path": "/tmp/fake.dxf"})
    mocks["roles"] = MagicMock(return_value={})
    mocks["gap"] = MagicMock(return_value={})
    mocks["dedupe"] = MagicMock(return_value={})
    mocks["writer"] = MagicMock(return_value={"normalized_dxf": {"output_path": ""}})
    mocks["gate"] = MagicMock(return_value={"acceptance_outcome": acceptance_outcome})
    mocks["t7"] = MagicMock(return_value={"issue_summary": {"normalized_issues": []}})
    mocks["persist"] = MagicMock(
        return_value=_persisted_result(
            acceptance_outcome=acceptance_outcome,
            include_normalized_artifact=include_normalized_artifact,
        )
    )
    mocks["import"] = MagicMock(return_value={"id": "geometry-revision-1"})

    monkeypatch.setattr(f"{_RUNTIME_PATCH_BASE}.download_storage_object_blob", mocks["download"])
    monkeypatch.setattr(f"{_RUNTIME_PATCH_BASE}.inspect_dxf_source", mocks["inspect"])
    monkeypatch.setattr(f"{_RUNTIME_PATCH_BASE}.resolve_dxf_roles", mocks["roles"])
    monkeypatch.setattr(f"{_RUNTIME_PATCH_BASE}.repair_dxf_gaps", mocks["gap"])
    monkeypatch.setattr(f"{_RUNTIME_PATCH_BASE}.dedupe_dxf_duplicate_contours", mocks["dedupe"])
    monkeypatch.setattr(f"{_RUNTIME_PATCH_BASE}.write_normalized_dxf", mocks["writer"])
    monkeypatch.setattr(
        f"{_RUNTIME_PATCH_BASE}.evaluate_dxf_prefilter_acceptance_gate",
        mocks["gate"],
    )
    monkeypatch.setattr(
        f"{_RUNTIME_PATCH_BASE}.render_dxf_preflight_diagnostics_summary",
        mocks["t7"],
    )
    monkeypatch.setattr(f"{_RUNTIME_PATCH_BASE}.persist_preflight_run", mocks["persist"])
    monkeypatch.setattr(
        f"{_RUNTIME_PATCH_BASE}.import_dxf_geometry_revision_from_storage",
        mocks["import"],
    )

    return mocks


def _run_runtime() -> None:
    supabase = _make_fake_supabase()
    run_preflight_for_upload(
        supabase=supabase,
        access_token="token",
        project_id="proj-1",
        source_file_object_id="file-1",
        storage_bucket="source-files",
        storage_path="projects/proj-1/files/file-1/part.dxf",
        source_hash_sha256="sourcehash",
        created_by="user-1",
        signed_url_ttl_s=300,
    )


def test_accepted_outcome_with_normalized_artifact_triggers_import(monkeypatch: Any) -> None:
    mocks = _patch_runtime_pipeline(
        monkeypatch,
        acceptance_outcome="accepted_for_import",
        include_normalized_artifact=True,
    )
    _run_runtime()

    mocks["import"].assert_called_once()
    _, kwargs = mocks["import"].call_args
    assert kwargs["storage_bucket"] == "geometry-artifacts"
    assert kwargs["storage_path"].endswith("/normalized_dxf/hash.dxf")


def test_rejected_outcome_skips_geometry_import(monkeypatch: Any) -> None:
    mocks = _patch_runtime_pipeline(
        monkeypatch,
        acceptance_outcome="preflight_rejected",
        include_normalized_artifact=True,
    )
    _run_runtime()
    mocks["import"].assert_not_called()


def test_review_required_outcome_skips_geometry_import(monkeypatch: Any) -> None:
    mocks = _patch_runtime_pipeline(
        monkeypatch,
        acceptance_outcome="preflight_review_required",
        include_normalized_artifact=True,
    )
    _run_runtime()
    mocks["import"].assert_not_called()


def test_accepted_outcome_without_normalized_artifact_skips_import(monkeypatch: Any) -> None:
    mocks = _patch_runtime_pipeline(
        monkeypatch,
        acceptance_outcome="accepted_for_import",
        include_normalized_artifact=False,
    )
    _run_runtime()
    mocks["import"].assert_not_called()


def test_geometry_import_error_is_swallowed_and_logged(
    monkeypatch: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mocks = _patch_runtime_pipeline(
        monkeypatch,
        acceptance_outcome="accepted_for_import",
        include_normalized_artifact=True,
    )
    mocks["import"].side_effect = RuntimeError("import failed")

    with caplog.at_level("WARNING", logger="vrs_api.dxf_preflight_runtime"):
        _run_runtime()

    assert "preflight_runtime_geometry_import_failed" in caplog.text


class _RouteFakeSupabase:
    def select_rows(self, *, table: str, access_token: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        if table == "app.projects":
            return [{"id": str(params.get("id", ""))}]
        raise AssertionError(f"unexpected select_rows table={table}")

    def insert_row(self, *, table: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        if table != "app.file_objects":
            raise AssertionError(f"unexpected insert_row table={table}")
        return {
            **payload,
            "id": payload["id"],
            "created_at": "2026-04-21T00:00:00+00:00",
        }


def test_route_no_longer_registers_direct_geometry_import_task(monkeypatch: Any) -> None:
    file_id = uuid4()
    project_id = uuid4()
    storage_path = f"projects/{project_id}/files/{file_id}/part.dxf"

    monkeypatch.setattr(
        "api.routes.files.load_file_ingest_metadata",
        MagicMock(
            return_value=SimpleNamespace(
                file_name="part.dxf",
                mime_type="application/dxf",
                byte_size=128,
                sha256="abc123",
            )
        ),
    )

    background_tasks = BackgroundTasks()
    response = complete_upload(
        project_id=project_id,
        req=FileCompleteRequest(
            file_id=UUID(str(file_id)),
            storage_path=storage_path,
            file_kind="source_dxf",
        ),
        background_tasks=background_tasks,
        user=AuthenticatedUser(id="user-1", access_token="token"),
        supabase=_RouteFakeSupabase(),
        settings=SimpleNamespace(storage_bucket="source-files", signed_url_ttl_s=300),
    )

    task_funcs = [task.func for task in background_tasks.tasks]
    assert task_funcs == [files_mod.validate_dxf_file_async, files_mod.run_preflight_for_upload]
    assert all(
        func.__name__ != "import_source_dxf_geometry_revision_async" for func in task_funcs
    )
    assert response.file_kind == "source_dxf"
