"""Route-level tests for E4-T2 preflight settings bridge in complete_upload."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID, uuid4

from fastapi import BackgroundTasks

import api.routes.files as files_mod
from api.auth import AuthenticatedUser
from api.routes.files import FileCompleteRequest, complete_upload


class _RouteFakeSupabase:
    def select_rows(
        self,
        *,
        table: str,
        access_token: str,
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if table == "app.projects":
            return [{"id": str(params.get("id", ""))}]
        raise AssertionError(f"unexpected select_rows table={table}")

    def insert_row(
        self,
        *,
        table: str,
        access_token: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if table != "app.file_objects":
            raise AssertionError(f"unexpected insert_row table={table}")
        return {
            **payload,
            "id": payload["id"],
            "created_at": "2026-04-21T00:00:00+00:00",
        }


def _run_complete_upload(*, snapshot: dict[str, Any] | None) -> tuple[list[Any], Any]:
    file_id = uuid4()
    project_id = uuid4()
    storage_path = f"projects/{project_id}/files/{file_id}/part.dxf"

    background_tasks = BackgroundTasks()
    response = complete_upload(
        project_id=project_id,
        req=FileCompleteRequest(
            file_id=UUID(str(file_id)),
            storage_path=storage_path,
            file_kind="source_dxf",
            rules_profile_snapshot_jsonb=snapshot,
        ),
        background_tasks=background_tasks,
        user=AuthenticatedUser(id="user-1", access_token="token"),
        supabase=_RouteFakeSupabase(),
        settings=SimpleNamespace(storage_bucket="source-files", signed_url_ttl_s=300, dxf_preflight_required=True, supabase_service_role_key=""),
    )
    return background_tasks.tasks, response


def test_complete_upload_snapshot_forwarded_to_preflight_runtime(monkeypatch: Any) -> None:
    snapshot = {
        "strict_mode": True,
        "auto_repair_enabled": False,
        "interactive_review_on_ambiguity": True,
        "max_gap_close_mm": 1.0,
        "duplicate_contour_merge_tolerance_mm": 0.05,
        "cut_color_map": [1, 3],
        "marking_color_map": [2],
    }

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

    tasks, response = _run_complete_upload(snapshot=snapshot)

    assert [task.func for task in tasks] == [
        files_mod.validate_dxf_file_async,
        files_mod.run_preflight_for_upload,
    ]
    preflight_kwargs = tasks[1].kwargs
    assert preflight_kwargs["rules_profile"] == snapshot
    assert response.file_kind == "source_dxf"


def test_complete_upload_without_snapshot_keeps_previous_runtime_behavior(
    monkeypatch: Any,
) -> None:
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

    tasks, response = _run_complete_upload(snapshot=None)

    assert [task.func for task in tasks] == [
        files_mod.validate_dxf_file_async,
        files_mod.run_preflight_for_upload,
    ]
    preflight_kwargs = tasks[1].kwargs
    assert preflight_kwargs.get("rules_profile") is None
    assert response.file_kind == "source_dxf"
