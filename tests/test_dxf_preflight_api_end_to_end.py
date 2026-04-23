"""DXF Prefilter E5-T2 -- API-level end-to-end preflight pack.

Current-code truth chain under test:
- complete_upload(...) route enqueues BackgroundTasks,
- run_preflight_for_upload(...) executes full T1->T7 + E3-T1 pipeline,
- persisted preflight truth is projected by list_project_files(...summary+diagnostics).

Scope notes:
- Route-callable style (no TestClient / no ASGI stack).
- Core runtime pipeline is real; only I/O seams are patched:
  load_file_ingest_metadata, download_storage_object_blob, geometry-import side effect.
- Explicit ezdxf dependency declaration is required because T5/T6 write/read a
  real normalized DXF artifact.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import BackgroundTasks

pytest.importorskip("ezdxf")

import api.routes.files as files_mod
from api.auth import AuthenticatedUser
from api.routes.files import FileCompleteRequest, complete_upload, list_project_files


def _parse_eq(value: Any) -> str | None:
    raw = str(value or "")
    if raw.startswith("eq."):
        return raw[3:]
    return None


def _parse_neq(value: Any) -> str | None:
    raw = str(value or "")
    if raw.startswith("neq."):
        return raw[4:]
    return None


def _parse_in(value: Any) -> set[str]:
    raw = str(value or "")
    if raw.startswith("in.(") and raw.endswith(")"):
        return {token for token in raw[4:-1].split(",") if token}
    return set()


class _ApiFlowFakeSupabase:
    """In-memory fake Supabase surface for route + runtime + projection E2E."""

    def __init__(self, *, project_id: str, owner_user_id: str) -> None:
        self.projects: list[dict[str, Any]] = [
            {
                "id": project_id,
                "owner_user_id": owner_user_id,
                "lifecycle": "active",
            }
        ]
        self.file_objects: list[dict[str, Any]] = []
        self.preflight_runs: list[dict[str, Any]] = []
        self.preflight_diagnostics: list[dict[str, Any]] = []
        self.preflight_artifacts: list[dict[str, Any]] = []

        self.select_calls: list[tuple[str, dict[str, Any]]] = []
        self.signed_upload_requests: list[dict[str, Any]] = []
        self.upload_events: list[dict[str, Any]] = []
        self.uploaded_payload_by_object: dict[tuple[str, str], bytes] = {}

        self._signed_upload_lookup: dict[str, tuple[str, str]] = {}
        self._id_counter = 0
        self._created_at_counter = 0

    def _next_id(self, prefix: str) -> str:
        self._id_counter += 1
        return f"{prefix}-{self._id_counter}"

    def _next_created_at(self) -> str:
        self._created_at_counter += 1
        second = self._created_at_counter % 60
        return f"2026-04-23T00:00:{second:02d}+00:00"

    def select_rows(self, *, table: str, access_token: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        self.select_calls.append((table, dict(params)))

        if table == "app.projects":
            id_eq = _parse_eq(params.get("id"))
            owner_eq = _parse_eq(params.get("owner_user_id"))
            lifecycle_neq = _parse_neq(params.get("lifecycle"))

            rows = []
            for row in self.projects:
                if id_eq is not None and str(row.get("id")) != id_eq:
                    continue
                if owner_eq is not None and str(row.get("owner_user_id")) != owner_eq:
                    continue
                if lifecycle_neq is not None and str(row.get("lifecycle")) == lifecycle_neq:
                    continue
                rows.append(dict(row))

            limit_raw = str(params.get("limit", "")).strip()
            if limit_raw.isdigit():
                rows = rows[: int(limit_raw)]
            return rows

        if table == "app.file_objects":
            project_eq = _parse_eq(params.get("project_id"))
            rows = [
                dict(row)
                for row in self.file_objects
                if project_eq is None or str(row.get("project_id")) == project_eq
            ]
            order = str(params.get("order", "")).strip().lower()
            if "created_at.desc" in order:
                rows.sort(key=lambda row: str(row.get("created_at", "")), reverse=True)

            offset = int(str(params.get("offset", "0")) or 0)
            limit = int(str(params.get("limit", str(len(rows)))) or len(rows))
            return rows[offset : offset + limit]

        if table == "app.preflight_runs":
            rows = [dict(row) for row in self.preflight_runs]
            source_eq = _parse_eq(params.get("source_file_object_id"))
            source_in = _parse_in(params.get("source_file_object_id"))
            if source_eq is not None:
                rows = [row for row in rows if str(row.get("source_file_object_id")) == source_eq]
            elif source_in:
                rows = [row for row in rows if str(row.get("source_file_object_id")) in source_in]

            order = str(params.get("order", "")).strip().lower()
            if order == "run_seq.desc":
                rows.sort(
                    key=lambda row: int(row.get("run_seq", 0)) if isinstance(row.get("run_seq"), int) else -1,
                    reverse=True,
                )
            elif order == "source_file_object_id.asc,run_seq.desc,finished_at.desc":
                rows.sort(
                    key=lambda row: (
                        str(row.get("source_file_object_id", "")),
                        -(int(row.get("run_seq", 0)) if isinstance(row.get("run_seq"), int) else -1),
                        str(row.get("finished_at", "")),
                    )
                )

            limit_raw = str(params.get("limit", "")).strip()
            if limit_raw.isdigit():
                rows = rows[: int(limit_raw)]
            return rows

        raise AssertionError(f"unexpected select_rows table={table!r}")

    def insert_row(self, *, table: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        row = dict(payload)

        if table == "app.file_objects":
            row.setdefault("created_at", self._next_created_at())
            self.file_objects.append(row)
            return dict(row)

        if table == "app.preflight_runs":
            row.setdefault("id", self._next_id("preflight-run"))
            row.setdefault("created_at", self._next_created_at())
            self.preflight_runs.append(row)
            return dict(row)

        if table == "app.preflight_diagnostics":
            row.setdefault("id", self._next_id("preflight-diagnostic"))
            self.preflight_diagnostics.append(row)
            return dict(row)

        if table == "app.preflight_artifacts":
            row.setdefault("id", self._next_id("preflight-artifact"))
            self.preflight_artifacts.append(row)
            return dict(row)

        raise AssertionError(f"unexpected insert_row table={table!r}")

    def create_signed_upload_url(
        self,
        *,
        access_token: str,
        bucket: str,
        object_key: str,
        expires_in: int,
    ) -> dict[str, Any]:
        token = self._next_id("signed")
        upload_url = f"https://upload.local/{token}"
        self._signed_upload_lookup[upload_url] = (bucket, object_key)
        self.signed_upload_requests.append(
            {
                "bucket": bucket,
                "object_key": object_key,
                "expires_in": expires_in,
            }
        )
        return {
            "upload_url": upload_url,
            "expires_at": "2026-12-31T00:00:00+00:00",
        }

    def upload_signed_object(self, *, signed_url: str, payload: bytes, content_type: str) -> None:
        if signed_url not in self._signed_upload_lookup:
            raise AssertionError(f"unknown signed upload URL: {signed_url}")
        bucket, object_key = self._signed_upload_lookup[signed_url]
        self.upload_events.append(
            {
                "signed_url": signed_url,
                "bucket": bucket,
                "object_key": object_key,
                "content_type": content_type,
                "size_bytes": len(payload),
            }
        )
        self.uploaded_payload_by_object[(bucket, object_key)] = payload


@dataclass(frozen=True)
class _ApiScenario:
    name: str
    entities: list[dict[str, Any]]
    rules_profile_snapshot: dict[str, Any]
    expected_outcome: str
    expected_recommended_action: str
    expected_geometry_import_call_count: int


_USER = AuthenticatedUser(id="user-e2e", access_token="token-e2e")

_ACCEPTED_ENTITIES = [
    {
        "layer": "CUT_OUTER",
        "type": "LWPOLYLINE",
        "closed": True,
        "points": [[0, 0], [120, 0], [120, 70], [0, 70]],
    }
]

_CONFLICT_ENTITIES = [
    {
        "layer": "CUT_OUTER",
        "type": "LWPOLYLINE",
        "closed": True,
        "points": [[0, 0], [120, 0], [120, 70], [0, 70]],
    },
    {
        "layer": "CUSTOM_CUT",
        "type": "LWPOLYLINE",
        "closed": True,
        "color_index": 1,
        "points": [[10, 10], [30, 10], [30, 20], [10, 20]],
    },
    {
        "layer": "CUSTOM_CUT",
        "type": "LINE",
        "closed": False,
        "color_index": 2,
        "points": [[5, 5], [50, 5]],
    },
]

_ACCEPTED_RULES_PROFILE = {
    "strict_mode": False,
    "auto_repair_enabled": True,
    "interactive_review_on_ambiguity": True,
    "max_gap_close_mm": 1.0,
    "duplicate_contour_merge_tolerance_mm": 0.05,
}

_LENIENT_RULES_PROFILE = {
    "strict_mode": False,
    "auto_repair_enabled": True,
    "interactive_review_on_ambiguity": True,
    "max_gap_close_mm": 1.0,
    "duplicate_contour_merge_tolerance_mm": 0.05,
    "cut_color_map": [1],
    "marking_color_map": [2],
}

_STRICT_RULES_PROFILE = {
    "strict_mode": True,
    "auto_repair_enabled": True,
    "interactive_review_on_ambiguity": True,
    "max_gap_close_mm": 1.0,
    "duplicate_contour_merge_tolerance_mm": 0.05,
    "cut_color_map": [1],
    "marking_color_map": [2],
}


def _fixture_blob_from_entities(entities: list[dict[str, Any]]) -> bytes:
    payload = {"entities": entities}
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _run_api_flow_scenario(
    *,
    monkeypatch: Any,
    scenario: _ApiScenario,
) -> dict[str, Any]:
    project_id = uuid4()
    file_id = uuid4()
    storage_path = f"projects/{project_id}/files/{file_id}/{scenario.name}.json"

    fixture_blob = _fixture_blob_from_entities(scenario.entities)
    source_hash_sha256 = hashlib.sha256(fixture_blob).hexdigest()

    supabase = _ApiFlowFakeSupabase(project_id=str(project_id), owner_user_id=_USER.id)

    ingest_metadata = SimpleNamespace(
        file_name="source.dxf",
        mime_type="application/dxf",
        byte_size=len(fixture_blob),
        sha256=source_hash_sha256,
    )
    monkeypatch.setattr(
        "api.routes.files.load_file_ingest_metadata",
        lambda **_: ingest_metadata,
    )

    monkeypatch.setattr(
        "api.services.dxf_preflight_runtime.download_storage_object_blob",
        lambda **_: fixture_blob,
    )

    geometry_import_calls: list[dict[str, Any]] = []

    def _record_geometry_import(**kwargs: Any) -> dict[str, Any]:
        geometry_import_calls.append(dict(kwargs))
        return {"id": f"geometry-revision-{len(geometry_import_calls)}"}

    monkeypatch.setattr(
        "api.services.dxf_preflight_runtime.import_dxf_geometry_revision_from_storage",
        _record_geometry_import,
    )

    background_tasks = BackgroundTasks()
    complete_response = complete_upload(
        project_id=project_id,
        req=FileCompleteRequest(
            file_id=UUID(str(file_id)),
            storage_path=storage_path,
            file_kind="source_dxf",
            rules_profile_snapshot_jsonb=scenario.rules_profile_snapshot,
        ),
        background_tasks=background_tasks,
        user=_USER,
        supabase=supabase,
        settings=SimpleNamespace(storage_bucket="source-files", signed_url_ttl_s=300),
    )

    task_funcs = [task.func for task in background_tasks.tasks]
    assert task_funcs == [
        files_mod.validate_dxf_file_async,
        files_mod.run_preflight_for_upload,
    ]

    preflight_tasks = [task for task in background_tasks.tasks if task.func is files_mod.run_preflight_for_upload]
    assert len(preflight_tasks) == 1
    preflight_task = preflight_tasks[0]
    assert preflight_task.kwargs["rules_profile"] == scenario.rules_profile_snapshot

    # Explicitly execute the runtime task captured from BackgroundTasks.
    preflight_task.func(*preflight_task.args, **preflight_task.kwargs)

    list_response = list_project_files(
        project_id=project_id,
        page=1,
        page_size=50,
        include_preflight_summary=True,
        include_preflight_diagnostics=True,
        user=_USER,
        supabase=supabase,
    )

    return {
        "project_id": str(project_id),
        "file_id": str(file_id),
        "storage_path": storage_path,
        "source_hash_sha256": source_hash_sha256,
        "complete_response": complete_response,
        "background_tasks": background_tasks,
        "preflight_task_kwargs": dict(preflight_task.kwargs),
        "list_response": list_response,
        "supabase": supabase,
        "geometry_import_calls": geometry_import_calls,
    }


def _assert_common_flow_truth(result: dict[str, Any], scenario: _ApiScenario) -> None:
    supabase = result["supabase"]
    list_response = result["list_response"]

    assert result["complete_response"].file_kind == "source_dxf"
    assert list_response.total == 1
    assert len(supabase.preflight_runs) == 1
    assert len(supabase.preflight_artifacts) == 1
    assert len(supabase.signed_upload_requests) >= 1
    assert len(supabase.upload_events) >= 1

    persisted_run = supabase.preflight_runs[0]
    assert persisted_run["source_file_object_id"] == result["file_id"]
    assert persisted_run["acceptance_outcome"] == scenario.expected_outcome
    assert persisted_run["rules_profile_snapshot_jsonb"] == scenario.rules_profile_snapshot

    artifact_row = supabase.preflight_artifacts[0]
    artifact_object = (
        str(artifact_row.get("storage_bucket", "")),
        str(artifact_row.get("storage_path", "")),
    )
    assert artifact_object in supabase.uploaded_payload_by_object
    assert supabase.uploaded_payload_by_object[artifact_object]

    item = list_response.items[0]
    summary = item.latest_preflight_summary
    diagnostics = item.latest_preflight_diagnostics

    assert summary is not None
    assert diagnostics is not None
    assert summary["acceptance_outcome"] == scenario.expected_outcome
    assert summary["recommended_action"] == scenario.expected_recommended_action

    # Diagnostics projection must include issue / repair / acceptance blocks.
    assert "issue_summary" in diagnostics
    assert "repair_summary" in diagnostics
    assert "acceptance_summary" in diagnostics

    assert len(result["geometry_import_calls"]) == scenario.expected_geometry_import_call_count


def test_preflight_api_e2e_accepted_flow_persists_projection_and_triggers_geometry_import(
    monkeypatch: Any,
) -> None:
    scenario = _ApiScenario(
        name="accepted",
        entities=_ACCEPTED_ENTITIES,
        rules_profile_snapshot=_ACCEPTED_RULES_PROFILE,
        expected_outcome="accepted_for_import",
        expected_recommended_action="ready_for_next_step",
        expected_geometry_import_call_count=1,
    )

    result = _run_api_flow_scenario(monkeypatch=monkeypatch, scenario=scenario)
    _assert_common_flow_truth(result, scenario)

    diagnostics = result["list_response"].items[0].latest_preflight_diagnostics
    assert diagnostics is not None
    assert diagnostics["acceptance_summary"]["acceptance_outcome"] == "accepted_for_import"

    geometry_call = result["geometry_import_calls"][0]
    assert geometry_call["project_id"] == result["project_id"]
    assert geometry_call["source_file_object_id"] == result["file_id"]
    assert geometry_call["source_hash_sha256"] == result["source_hash_sha256"]


def test_preflight_api_e2e_lenient_review_required_skips_geometry_import_and_keeps_diagnostics(
    monkeypatch: Any,
) -> None:
    scenario = _ApiScenario(
        name="lenient_review_required",
        entities=_CONFLICT_ENTITIES,
        rules_profile_snapshot=_LENIENT_RULES_PROFILE,
        expected_outcome="preflight_review_required",
        expected_recommended_action="review_required_wait_for_diagnostics",
        expected_geometry_import_call_count=0,
    )

    result = _run_api_flow_scenario(monkeypatch=monkeypatch, scenario=scenario)
    _assert_common_flow_truth(result, scenario)

    diagnostics = result["list_response"].items[0].latest_preflight_diagnostics
    assert diagnostics is not None
    issue_counts = diagnostics["issue_summary"]["counts_by_severity"]
    assert issue_counts["review_required"] >= 1
    assert diagnostics["acceptance_summary"]["review_required_reason_count"] >= 1

    # Bridge proof: strict_mode=False snapshot persisted from complete_upload -> runtime.
    persisted_run = result["supabase"].preflight_runs[0]
    assert persisted_run["rules_profile_snapshot_jsonb"]["strict_mode"] is False


def test_preflight_api_e2e_strict_rejected_skips_geometry_import_and_projects_rejected_state(
    monkeypatch: Any,
) -> None:
    scenario = _ApiScenario(
        name="strict_rejected",
        entities=_CONFLICT_ENTITIES,
        rules_profile_snapshot=_STRICT_RULES_PROFILE,
        expected_outcome="preflight_rejected",
        expected_recommended_action="rejected_fix_and_reupload",
        expected_geometry_import_call_count=0,
    )

    result = _run_api_flow_scenario(monkeypatch=monkeypatch, scenario=scenario)
    _assert_common_flow_truth(result, scenario)

    diagnostics = result["list_response"].items[0].latest_preflight_diagnostics
    assert diagnostics is not None
    assert diagnostics["acceptance_summary"]["acceptance_outcome"] == "preflight_rejected"
    assert diagnostics["acceptance_summary"]["blocking_reason_count"] >= 1

    # Bridge proof: strict_mode=True snapshot persisted from complete_upload -> runtime.
    persisted_run = result["supabase"].preflight_runs[0]
    assert persisted_run["rules_profile_snapshot_jsonb"]["strict_mode"] is True
