#!/usr/bin/env python3
"""DXF Prefilter E3-T3 geometry import gate integration smoke."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID, uuid4

from fastapi import BackgroundTasks

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import api.routes.files as files_mod
import api.services.dxf_preflight_runtime as runtime_mod
from api.auth import AuthenticatedUser
from api.routes.files import FileCompleteRequest, complete_upload
from api.services.dxf_preflight_runtime import run_preflight_for_upload


def _assert(condition: bool, message: str) -> None:
    if not condition:
        print(f"  FAIL: {message}")
        raise SystemExit(1)


def _scenario(name: str) -> None:
    print(f"  {name} ... ", end="", flush=True)


def _ok() -> None:
    print("OK")


def _runtime_supabase() -> MagicMock:
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
                "storage_path": "projects/p1/preflight/run-1/normalized_dxf/hash.dxf",
            }
        )
    return {
        "preflight_run_id": "run-1",
        "acceptance_outcome": acceptance_outcome,
        "artifact_refs": artifact_refs,
    }


def _patch_runtime(
    *,
    acceptance_outcome: str,
    include_normalized_artifact: bool,
) -> tuple[list[tuple[Any, str, Any]], MagicMock]:
    import_mock = MagicMock(return_value={"id": "geometry-revision-1"})
    patches: dict[str, Any] = {
        "download_storage_object_blob": MagicMock(return_value=b"FAKE_DXF_BYTES"),
        "inspect_dxf_source": MagicMock(return_value={"source_path": "/tmp/fake.dxf"}),
        "resolve_dxf_roles": MagicMock(return_value={}),
        "repair_dxf_gaps": MagicMock(return_value={}),
        "dedupe_dxf_duplicate_contours": MagicMock(return_value={}),
        "write_normalized_dxf": MagicMock(return_value={"normalized_dxf": {"output_path": ""}}),
        "evaluate_dxf_prefilter_acceptance_gate": MagicMock(
            return_value={"acceptance_outcome": acceptance_outcome}
        ),
        "render_dxf_preflight_diagnostics_summary": MagicMock(
            return_value={"issue_summary": {"normalized_issues": []}}
        ),
        "persist_preflight_run": MagicMock(
            return_value=_persisted_result(
                acceptance_outcome=acceptance_outcome,
                include_normalized_artifact=include_normalized_artifact,
            )
        ),
        "import_dxf_geometry_revision_from_storage": import_mock,
    }
    originals: list[tuple[Any, str, Any]] = []
    for attr, replacement in patches.items():
        originals.append((runtime_mod, attr, getattr(runtime_mod, attr)))
        setattr(runtime_mod, attr, replacement)
    return originals, import_mock


def _restore_patches(patches: list[tuple[Any, str, Any]]) -> None:
    for module, attr, original in patches:
        setattr(module, attr, original)


def _run_runtime() -> None:
    run_preflight_for_upload(
        supabase=_runtime_supabase(),
        access_token="token",
        project_id="p1",
        source_file_object_id="f1",
        storage_bucket="source-files",
        storage_path="projects/p1/files/f1/part.dxf",
        source_hash_sha256="sourcehash",
        created_by="u1",
        signed_url_ttl_s=300,
    )


def scenario_runtime_accepted_import() -> None:
    _scenario("RUNTIME ACCEPTED IMPORT")
    patches, import_mock = _patch_runtime(
        acceptance_outcome="accepted_for_import",
        include_normalized_artifact=True,
    )
    try:
        _run_runtime()
        _assert(import_mock.call_count == 1, "geometry import should be called once")
    finally:
        _restore_patches(patches)
    _ok()


def scenario_runtime_rejected_skip() -> None:
    _scenario("RUNTIME REJECTED SKIP")
    patches, import_mock = _patch_runtime(
        acceptance_outcome="preflight_rejected",
        include_normalized_artifact=True,
    )
    try:
        _run_runtime()
        _assert(import_mock.call_count == 0, "geometry import should be skipped")
    finally:
        _restore_patches(patches)
    _ok()


def scenario_runtime_review_skip() -> None:
    _scenario("RUNTIME REVIEW SKIP")
    patches, import_mock = _patch_runtime(
        acceptance_outcome="preflight_review_required",
        include_normalized_artifact=True,
    )
    try:
        _run_runtime()
        _assert(import_mock.call_count == 0, "geometry import should be skipped")
    finally:
        _restore_patches(patches)
    _ok()


def scenario_runtime_missing_artifact_skip() -> None:
    _scenario("RUNTIME MISSING ARTIFACT SKIP")
    patches, import_mock = _patch_runtime(
        acceptance_outcome="accepted_for_import",
        include_normalized_artifact=False,
    )
    try:
        _run_runtime()
        _assert(import_mock.call_count == 0, "geometry import should be skipped")
    finally:
        _restore_patches(patches)
    _ok()


class _RouteFakeSupabase:
    def select_rows(self, *, table: str, access_token: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        if table == "app.projects":
            return [{"id": str(params.get("id", ""))}]
        raise AssertionError(f"unexpected select_rows table={table}")

    def insert_row(self, *, table: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        if table != "app.file_objects":
            raise AssertionError(f"unexpected insert_row table={table}")
        return {**payload, "created_at": "2026-04-21T00:00:00+00:00"}


def scenario_route_registers_only_two_tasks() -> None:
    _scenario("ROUTE TWO TASKS")
    original_loader = files_mod.load_file_ingest_metadata
    files_mod.load_file_ingest_metadata = MagicMock(
        return_value=SimpleNamespace(
            file_name="part.dxf",
            mime_type="application/dxf",
            byte_size=128,
            sha256="abc123",
        )
    )

    file_id = uuid4()
    project_id = uuid4()
    storage_path = f"projects/{project_id}/files/{file_id}/part.dxf"

    try:
        background_tasks = BackgroundTasks()
        complete_upload(
            project_id=UUID(str(project_id)),
            req=FileCompleteRequest(
                file_id=UUID(str(file_id)),
                storage_path=storage_path,
                file_kind="source_dxf",
            ),
            background_tasks=background_tasks,
            user=AuthenticatedUser(id="u1", access_token="token"),
            supabase=_RouteFakeSupabase(),
            settings=SimpleNamespace(storage_bucket="source-files", signed_url_ttl_s=300),
        )
        task_funcs = [task.func for task in background_tasks.tasks]
        _assert(len(task_funcs) == 2, f"expected 2 tasks, got {len(task_funcs)}")
        _assert(task_funcs[0] is files_mod.validate_dxf_file_async, "task[0] should be validate")
        _assert(task_funcs[1] is files_mod.run_preflight_for_upload, "task[1] should be preflight")
    finally:
        files_mod.load_file_ingest_metadata = original_loader
    _ok()


def main() -> None:
    print("DXF Prefilter E3-T3 smoke:")
    scenario_route_registers_only_two_tasks()
    scenario_runtime_accepted_import()
    scenario_runtime_rejected_skip()
    scenario_runtime_review_skip()
    scenario_runtime_missing_artifact_skip()
    print("All smoke scenarios passed.")


if __name__ == "__main__":
    main()
