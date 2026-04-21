"""Unit tests for DXF Prefilter E3-T2 — preflight runtime/orchestration service.

Uses deterministic fake gateways and monkeypatching (no network, no DB, no
real DXF file I/O) to verify:
- T1→T7 + E3-T1 pipeline step ordering,
- accepted flow calls persist_preflight_run,
- runtime error triggers _try_persist_failed_run / persist_preflight_failed_run,
- run_seq is computed from app.preflight_runs truth via get_next_run_seq,
- rules_profile plumbing is passed through the whole chain,
- no FastAPI / APIRouter scope in the service module,
- persist_preflight_failed_run stores preflight_failed run status,
- get_next_run_seq returns 1 when no prior runs exist,
- get_next_run_seq returns max+1 when prior runs exist.
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

from api.services.dxf_preflight_persistence import (
    DxfPreflightPersistenceError,
    get_next_run_seq,
    persist_preflight_failed_run,
)
from api.services.dxf_preflight_runtime import (
    DxfPreflightRuntimeError,
    run_preflight_for_upload,
)


# ---------------------------------------------------------------------------
# Fake gateways
# ---------------------------------------------------------------------------


class FakeDbGateway:
    def __init__(self) -> None:
        self.runs: list[dict[str, Any]] = []
        self.diagnostics: list[dict[str, Any]] = []
        self.artifacts: list[dict[str, Any]] = []

    def insert_preflight_run(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        row = {**payload, "id": str(uuid.uuid4())}
        self.runs.append(row)
        return row

    def insert_preflight_diagnostic(self, *, payload: dict[str, Any]) -> None:
        self.diagnostics.append(payload)

    def insert_preflight_artifact(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        row = {**payload, "id": str(uuid.uuid4())}
        self.artifacts.append(row)
        return row


class FakeStorageGateway:
    def __init__(self) -> None:
        self.uploads: list[dict[str, Any]] = []

    def upload_bytes(
        self, *, bucket: str, object_key: str, payload: bytes, content_type: str
    ) -> None:
        self.uploads.append({"bucket": bucket, "object_key": object_key})


class FakeRunSeqQueryGateway:
    def __init__(self, *, max_run_seq: int | None = None) -> None:
        self._max = max_run_seq

    def fetch_max_run_seq(self, *, source_file_object_id: str) -> int | None:
        return self._max


# ---------------------------------------------------------------------------
# Helper: minimal fake T7 summary / acceptance gate / writer shapes
# ---------------------------------------------------------------------------

_FAKE_INSPECT = {"source_path": "/tmp/fake.dxf", "source_sha256": "abc"}
_FAKE_ROLES = {"layer_role_assignments": {}}
_FAKE_GAP = {"applied_gap_repairs": []}
_FAKE_DEDUPE = {"deduped_contour_working_set": []}
_FAKE_WRITER = {"output_path": "", "entity_count": 0}
_FAKE_GATE = {
    "acceptance_outcome": "accepted_for_import",
    "normalized_dxf_echo": {"output_path": ""},
    "blocking_reasons": [],
    "review_required_reasons": [],
}
_FAKE_T7 = {
    "acceptance_outcome": "accepted_for_import",
    "issue_summary": {"normalized_issues": []},
    "repair_summary": {},
    "entity_summary": {},
}

_FAKE_PERSIST_RESULT = {
    "preflight_run_id": str(uuid.uuid4()),
    "project_id": "proj-1",
    "source_file_object_id": "file-1",
    "run_seq": 1,
    "run_status": "preflight_complete",
    "acceptance_outcome": "accepted_for_import",
    "diagnostics_count": 0,
    "artifact_refs": [],
    "normalized_hash_sha256": None,
    "summary_snapshot": _FAKE_T7,
}

_FAKE_RULES_PROFILE = {
    "strict_mode": True,
    "auto_repair_enabled": True,
    "interactive_review_on_ambiguity": False,
    "max_gap_close_mm": 0.75,
    "duplicate_contour_merge_tolerance_mm": 0.025,
    "cut_color_map": [1, 7],
    "marking_color_map": [2],
}


# ---------------------------------------------------------------------------
# Tests: get_next_run_seq
# ---------------------------------------------------------------------------


def test_get_next_run_seq_no_prior_runs() -> None:
    gw = FakeRunSeqQueryGateway(max_run_seq=None)
    assert get_next_run_seq(source_file_object_id="file-1", db_query=gw) == 1


def test_get_next_run_seq_with_prior_runs() -> None:
    gw = FakeRunSeqQueryGateway(max_run_seq=3)
    assert get_next_run_seq(source_file_object_id="file-1", db_query=gw) == 4


def test_get_next_run_seq_max_zero_treated_as_no_runs() -> None:
    gw = FakeRunSeqQueryGateway(max_run_seq=0)
    assert get_next_run_seq(source_file_object_id="file-1", db_query=gw) == 1


# ---------------------------------------------------------------------------
# Tests: persist_preflight_failed_run
# ---------------------------------------------------------------------------


def test_persist_preflight_failed_run_stores_failed_status() -> None:
    db = FakeDbGateway()
    result = persist_preflight_failed_run(
        project_id="proj-1",
        source_file_object_id="file-1",
        run_seq=2,
        error_message="inspect failed",
        db=db,
    )
    assert db.runs, "should have inserted a run row"
    row = db.runs[0]
    assert row["run_status"] == "preflight_failed"
    assert row["run_seq"] == 2
    assert row["project_id"] == "proj-1"
    assert "error" in row["summary_jsonb"]


def test_persist_preflight_failed_run_invalid_run_seq_raises() -> None:
    db = FakeDbGateway()
    with pytest.raises(DxfPreflightPersistenceError):
        persist_preflight_failed_run(
            project_id="proj-1",
            source_file_object_id="file-1",
            run_seq=0,
            error_message="oops",
            db=db,
        )


# ---------------------------------------------------------------------------
# Tests: run_preflight_for_upload pipeline ordering
# ---------------------------------------------------------------------------

_PIPELINE_PATCH_BASE = "api.services.dxf_preflight_runtime"


def _make_fake_supabase() -> MagicMock:
    supabase = MagicMock()
    supabase.select_rows.return_value = []
    return supabase


def _patch_pipeline(monkeypatch: Any) -> dict[str, MagicMock]:
    """Patch all E2/T7 + E3-T1 service calls and storage download."""
    mocks: dict[str, MagicMock] = {}

    mocks["download"] = MagicMock(return_value=b"FAKE_DXF_BYTES")
    mocks["inspect"] = MagicMock(return_value=_FAKE_INSPECT)
    mocks["roles"] = MagicMock(return_value=_FAKE_ROLES)
    mocks["gap"] = MagicMock(return_value=_FAKE_GAP)
    mocks["dedupe"] = MagicMock(return_value=_FAKE_DEDUPE)
    mocks["writer"] = MagicMock(return_value=_FAKE_WRITER)
    mocks["gate"] = MagicMock(return_value=_FAKE_GATE)
    mocks["t7"] = MagicMock(return_value=_FAKE_T7)
    mocks["persist"] = MagicMock(return_value=_FAKE_PERSIST_RESULT)

    monkeypatch.setattr(f"{_PIPELINE_PATCH_BASE}.download_storage_object_blob", mocks["download"])
    monkeypatch.setattr(f"{_PIPELINE_PATCH_BASE}.inspect_dxf_source", mocks["inspect"])
    monkeypatch.setattr(f"{_PIPELINE_PATCH_BASE}.resolve_dxf_roles", mocks["roles"])
    monkeypatch.setattr(f"{_PIPELINE_PATCH_BASE}.repair_dxf_gaps", mocks["gap"])
    monkeypatch.setattr(f"{_PIPELINE_PATCH_BASE}.dedupe_dxf_duplicate_contours", mocks["dedupe"])
    monkeypatch.setattr(f"{_PIPELINE_PATCH_BASE}.write_normalized_dxf", mocks["writer"])
    monkeypatch.setattr(
        f"{_PIPELINE_PATCH_BASE}.evaluate_dxf_prefilter_acceptance_gate", mocks["gate"]
    )
    monkeypatch.setattr(
        f"{_PIPELINE_PATCH_BASE}.render_dxf_preflight_diagnostics_summary", mocks["t7"]
    )
    monkeypatch.setattr(f"{_PIPELINE_PATCH_BASE}.persist_preflight_run", mocks["persist"])

    return mocks


def test_pipeline_calls_all_steps_in_order(monkeypatch: Any) -> None:
    mocks = _patch_pipeline(monkeypatch)
    supabase = _make_fake_supabase()

    run_preflight_for_upload(
        supabase=supabase,
        access_token="tok",
        project_id="proj-1",
        source_file_object_id="file-1",
        storage_bucket="source-files",
        storage_path="projects/proj-1/files/file-1/part.dxf",
        source_hash_sha256="deadbeef",
        created_by="user-1",
        signed_url_ttl_s=300,
    )

    mocks["download"].assert_called_once()
    mocks["inspect"].assert_called_once()
    mocks["roles"].assert_called_once()
    mocks["gap"].assert_called_once()
    mocks["dedupe"].assert_called_once()
    mocks["writer"].assert_called_once()
    mocks["gate"].assert_called_once()
    mocks["t7"].assert_called_once()
    mocks["persist"].assert_called_once()


def test_accepted_flow_persist_called_with_run_seq(monkeypatch: Any) -> None:
    mocks = _patch_pipeline(monkeypatch)
    supabase = _make_fake_supabase()
    # Simulate 2 existing runs so run_seq should be 3.
    supabase.select_rows.return_value = [{"run_seq": 2}]

    run_preflight_for_upload(
        supabase=supabase,
        access_token="tok",
        project_id="proj-1",
        source_file_object_id="file-1",
        storage_bucket="source-files",
        storage_path="projects/proj-1/files/file-1/part.dxf",
        source_hash_sha256="deadbeef",
        created_by="user-1",
        signed_url_ttl_s=300,
    )

    _, kwargs = mocks["persist"].call_args
    assert kwargs["run_seq"] == 3


def test_rules_profile_none_passed_to_persist(monkeypatch: Any) -> None:
    mocks = _patch_pipeline(monkeypatch)
    supabase = _make_fake_supabase()

    run_preflight_for_upload(
        supabase=supabase,
        access_token="tok",
        project_id="proj-1",
        source_file_object_id="file-1",
        storage_bucket="source-files",
        storage_path="projects/proj-1/files/file-1/part.dxf",
        source_hash_sha256="deadbeef",
        created_by="user-1",
        signed_url_ttl_s=300,
    )

    _, kwargs = mocks["persist"].call_args
    assert kwargs.get("rules_profile") is None


def test_rules_profile_mapping_passed_through_pipeline_and_persist(monkeypatch: Any) -> None:
    mocks = _patch_pipeline(monkeypatch)
    supabase = _make_fake_supabase()

    run_preflight_for_upload(
        supabase=supabase,
        access_token="tok",
        project_id="proj-1",
        source_file_object_id="file-1",
        storage_bucket="source-files",
        storage_path="projects/proj-1/files/file-1/part.dxf",
        source_hash_sha256="deadbeef",
        created_by="user-1",
        signed_url_ttl_s=300,
        rules_profile=_FAKE_RULES_PROFILE,
    )

    _, roles_kwargs = mocks["roles"].call_args
    _, gap_kwargs = mocks["gap"].call_args
    _, dedupe_kwargs = mocks["dedupe"].call_args
    _, writer_kwargs = mocks["writer"].call_args
    _, persist_kwargs = mocks["persist"].call_args

    assert roles_kwargs.get("rules_profile") == _FAKE_RULES_PROFILE
    assert gap_kwargs.get("rules_profile") == _FAKE_RULES_PROFILE
    assert dedupe_kwargs.get("rules_profile") == _FAKE_RULES_PROFILE
    assert writer_kwargs.get("rules_profile") == _FAKE_RULES_PROFILE
    assert persist_kwargs.get("rules_profile") == _FAKE_RULES_PROFILE


def test_pipeline_error_triggers_failed_run_persist(monkeypatch: Any) -> None:
    mocks = _patch_pipeline(monkeypatch)
    supabase = _make_fake_supabase()

    mocks["inspect"].side_effect = RuntimeError("inspect exploded")

    failed_persist = MagicMock()
    monkeypatch.setattr(f"{_PIPELINE_PATCH_BASE}.persist_preflight_failed_run", failed_persist)

    run_preflight_for_upload(
        supabase=supabase,
        access_token="tok",
        project_id="proj-1",
        source_file_object_id="file-1",
        storage_bucket="source-files",
        storage_path="projects/proj-1/files/file-1/part.dxf",
        source_hash_sha256="deadbeef",
        created_by="user-1",
        signed_url_ttl_s=300,
    )

    failed_persist.assert_called_once()
    _, kwargs = failed_persist.call_args
    assert kwargs["project_id"] == "proj-1"
    assert kwargs["source_file_object_id"] == "file-1"
    assert "exploded" in kwargs["error_message"]


def test_run_seq_fallback_to_1_when_query_fails(monkeypatch: Any) -> None:
    mocks = _patch_pipeline(monkeypatch)
    supabase = _make_fake_supabase()
    supabase.select_rows.side_effect = RuntimeError("db down")

    run_preflight_for_upload(
        supabase=supabase,
        access_token="tok",
        project_id="proj-1",
        source_file_object_id="file-1",
        storage_bucket="source-files",
        storage_path="projects/proj-1/files/file-1/part.dxf",
        source_hash_sha256="deadbeef",
        created_by="user-1",
        signed_url_ttl_s=300,
    )

    _, kwargs = mocks["persist"].call_args
    assert kwargs["run_seq"] == 1


# ---------------------------------------------------------------------------
# Tests: no FastAPI / route scope in the service module
# ---------------------------------------------------------------------------


def test_no_route_or_fastapi_scope_in_runtime_module() -> None:
    import api.services.dxf_preflight_runtime as mod
    import inspect

    src = inspect.getsource(mod)
    for forbidden in ("APIRouter", "HTTPException", "@router.", "@app."):
        assert forbidden not in src, f"service must not contain '{forbidden}'"
