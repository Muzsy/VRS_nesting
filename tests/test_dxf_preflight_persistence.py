"""Unit tests for DXF Prefilter E3-T1 -- preflight persistence service.

Uses a deterministic fake Supabase gateway (no network, no DB) to verify:
- canonical_preflight_storage_path shape,
- accepted / review-required / rejected flow persistence,
- preflight_diagnostics row generation from T7 issue summary,
- summary_jsonb snapshot preservation,
- normalized DXF upload to geometry-artifacts bucket,
- preflight_artifacts row with explicit storage truth,
- no rules-profile FK domain requirement,
- no route / request-model / acceptance-outcome generation by this service,
- structural error cases (invalid inputs).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import Any

import pytest

from api.services.dxf_preflight_persistence import (
    DxfPreflightPersistenceError,
    canonical_preflight_storage_path,
    persist_preflight_run,
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
        self,
        *,
        bucket: str,
        object_key: str,
        payload: bytes,
        content_type: str,
    ) -> None:
        self.uploads.append(
            {
                "bucket": bucket,
                "object_key": object_key,
                "size_bytes": len(payload),
                "content_type": content_type,
            }
        )


# ---------------------------------------------------------------------------
# Fixtures helpers
# ---------------------------------------------------------------------------

_PROJECT_ID = str(uuid.uuid4())
_FILE_OBJECT_ID = str(uuid.uuid4())


def _make_t7_summary(
    *,
    acceptance_outcome: str = "accepted_for_import",
    issues: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    normalized_issues = issues or []
    return {
        "source_inventory_summary": {"source_path": "/tmp/test.dxf"},
        "acceptance_summary": {"acceptance_outcome": acceptance_outcome},
        "issue_summary": {
            "normalized_issues": normalized_issues,
            "blocking_issues": [i for i in normalized_issues if i.get("severity") == "blocking"],
            "review_required_issues": [i for i in normalized_issues if i.get("severity") == "review_required"],
            "warning_issues": [],
            "info_issues": [],
            "counts_by_severity": {
                "blocking": sum(1 for i in normalized_issues if i.get("severity") == "blocking"),
                "review_required": sum(1 for i in normalized_issues if i.get("severity") == "review_required"),
                "warning": 0,
                "info": 0,
            },
        },
        "repair_summary": {"counts": {}},
        "role_mapping_summary": {},
        "artifact_references": [],
    }


def _make_acceptance_gate_result(
    *,
    outcome: str = "accepted_for_import",
    output_path: str = "",
) -> dict[str, Any]:
    return {
        "acceptance_outcome": outcome,
        "normalized_dxf_echo": {
            "output_path": output_path,
            "writer_backend": "ezdxf",
            "written_layers": ["CUT_OUTER"],
            "written_entity_count": 1,
        },
        "importer_probe": {"is_pass": True},
        "validator_probe": {"is_pass": True, "status": "validated"},
        "blocking_reasons": [],
        "review_required_reasons": [],
        "diagnostics": {},
    }


def _make_normalized_dxf_writer_result(*, output_path: str = "") -> dict[str, Any]:
    return {
        "normalized_dxf": {
            "output_path": output_path,
            "writer_backend": "ezdxf",
            "written_layers": ["CUT_OUTER"],
            "written_entity_count": 1,
            "cut_contour_count": 1,
            "marking_entity_count": 0,
        },
        "skipped_source_entities": [],
        "diagnostics": {"notes": []},
    }


def _write_dummy_dxf(path: Path) -> bytes:
    content = b"0\nSECTION\n2\nENTITIES\n0\nENDSEC\n0\nEOF\n"
    path.write_bytes(content)
    return content


# ---------------------------------------------------------------------------
# canonical_preflight_storage_path
# ---------------------------------------------------------------------------


def test_canonical_storage_path_shape() -> None:
    path = canonical_preflight_storage_path(
        project_id="proj-abc",
        preflight_run_id="run-xyz",
        artifact_kind="normalized_dxf",
        content_hash_sha256="deadbeef1234",
        extension="dxf",
    )
    assert path == "projects/proj-abc/preflight/run-xyz/normalized_dxf/deadbeef1234.dxf"


def test_canonical_storage_path_strips_dot_from_extension() -> None:
    path = canonical_preflight_storage_path(
        project_id="p",
        preflight_run_id="r",
        artifact_kind="normalized_dxf",
        content_hash_sha256="abc123",
        extension=".dxf",
    )
    assert path.endswith("/abc123.dxf")
    assert "..dxf" not in path


def test_canonical_storage_path_lowercases_extension() -> None:
    path = canonical_preflight_storage_path(
        project_id="p",
        preflight_run_id="r",
        artifact_kind="normalized_dxf",
        content_hash_sha256="abc",
        extension="DXF",
    )
    assert path.endswith(".dxf")


def test_canonical_storage_path_rejects_empty_project_id() -> None:
    with pytest.raises(DxfPreflightPersistenceError):
        canonical_preflight_storage_path(
            project_id="",
            preflight_run_id="r",
            artifact_kind="normalized_dxf",
            content_hash_sha256="abc",
            extension="dxf",
        )


# ---------------------------------------------------------------------------
# persist_preflight_run — output shape
# ---------------------------------------------------------------------------


def test_persist_run_returns_required_keys(tmp_path: Path) -> None:
    dxf_path = tmp_path / "out.dxf"
    _write_dummy_dxf(dxf_path)

    db = FakeDbGateway()
    storage = FakeStorageGateway()

    result = persist_preflight_run(
        project_id=_PROJECT_ID,
        source_file_object_id=_FILE_OBJECT_ID,
        t7_summary=_make_t7_summary(),
        acceptance_gate_result=_make_acceptance_gate_result(output_path=str(dxf_path)),
        normalized_dxf_writer_result=_make_normalized_dxf_writer_result(output_path=str(dxf_path)),
        db=db,
        storage=storage,
    )

    for key in ("preflight_run_id", "project_id", "source_file_object_id",
                "run_seq", "run_status", "acceptance_outcome",
                "diagnostics_count", "artifact_refs", "summary_snapshot"):
        assert key in result, f"missing key: {key}"


def test_persist_run_must_not_emit_acceptance_outcome_itself(tmp_path: Path) -> None:
    """The service must not produce acceptance_outcome; it only persists what T6 already decided."""
    dxf_path = tmp_path / "out.dxf"
    _write_dummy_dxf(dxf_path)

    db = FakeDbGateway()
    storage = FakeStorageGateway()

    result = persist_preflight_run(
        project_id=_PROJECT_ID,
        source_file_object_id=_FILE_OBJECT_ID,
        t7_summary=_make_t7_summary(acceptance_outcome="accepted_for_import"),
        acceptance_gate_result=_make_acceptance_gate_result(
            outcome="accepted_for_import", output_path=str(dxf_path)
        ),
        normalized_dxf_writer_result=_make_normalized_dxf_writer_result(output_path=str(dxf_path)),
        db=db,
        storage=storage,
    )
    # The service echoes the T6 outcome; it does not recompute it.
    assert result["acceptance_outcome"] == "accepted_for_import"
    # No new acceptance-gate world keys
    for forbidden in ("accepted_for_import", "preflight_rejected", "blocking_reasons",
                      "importer_probe", "validator_probe"):
        assert forbidden not in result


# ---------------------------------------------------------------------------
# persist_preflight_run — accepted flow
# ---------------------------------------------------------------------------


def test_accepted_flow_creates_run_row(tmp_path: Path) -> None:
    dxf_path = tmp_path / "out.dxf"
    _write_dummy_dxf(dxf_path)
    db = FakeDbGateway()
    storage = FakeStorageGateway()

    persist_preflight_run(
        project_id=_PROJECT_ID,
        source_file_object_id=_FILE_OBJECT_ID,
        t7_summary=_make_t7_summary(),
        acceptance_gate_result=_make_acceptance_gate_result(
            outcome="accepted_for_import", output_path=str(dxf_path)
        ),
        normalized_dxf_writer_result=_make_normalized_dxf_writer_result(output_path=str(dxf_path)),
        db=db,
        storage=storage,
    )

    assert len(db.runs) == 1
    run = db.runs[0]
    assert run["project_id"] == _PROJECT_ID
    assert run["source_file_object_id"] == _FILE_OBJECT_ID
    assert run["acceptance_outcome"] == "accepted_for_import"
    assert run["run_status"] == "preflight_complete"


def test_accepted_flow_uploads_normalized_dxf_to_geometry_artifacts(tmp_path: Path) -> None:
    dxf_path = tmp_path / "out.dxf"
    content = _write_dummy_dxf(dxf_path)
    db = FakeDbGateway()
    storage = FakeStorageGateway()

    persist_preflight_run(
        project_id=_PROJECT_ID,
        source_file_object_id=_FILE_OBJECT_ID,
        t7_summary=_make_t7_summary(),
        acceptance_gate_result=_make_acceptance_gate_result(
            outcome="accepted_for_import", output_path=str(dxf_path)
        ),
        normalized_dxf_writer_result=_make_normalized_dxf_writer_result(output_path=str(dxf_path)),
        db=db,
        storage=storage,
    )

    assert len(storage.uploads) == 1
    upload = storage.uploads[0]
    assert upload["bucket"] == "geometry-artifacts"
    expected_hash = hashlib.sha256(content).hexdigest()
    assert expected_hash in upload["object_key"]
    assert upload["object_key"].startswith(f"projects/{_PROJECT_ID}/preflight/")
    assert "/normalized_dxf/" in upload["object_key"]
    assert upload["object_key"].endswith(".dxf")


def test_accepted_flow_creates_preflight_artifact_row(tmp_path: Path) -> None:
    dxf_path = tmp_path / "out.dxf"
    content = _write_dummy_dxf(dxf_path)
    db = FakeDbGateway()
    storage = FakeStorageGateway()

    persist_preflight_run(
        project_id=_PROJECT_ID,
        source_file_object_id=_FILE_OBJECT_ID,
        t7_summary=_make_t7_summary(),
        acceptance_gate_result=_make_acceptance_gate_result(
            outcome="accepted_for_import", output_path=str(dxf_path)
        ),
        normalized_dxf_writer_result=_make_normalized_dxf_writer_result(output_path=str(dxf_path)),
        db=db,
        storage=storage,
    )

    assert len(db.artifacts) == 1
    artifact = db.artifacts[0]
    assert artifact["storage_bucket"] == "geometry-artifacts"
    assert artifact["artifact_kind"] == "normalized_dxf"
    assert artifact["storage_path"].startswith(f"projects/{_PROJECT_ID}/preflight/")
    assert artifact["artifact_hash_sha256"] == hashlib.sha256(content).hexdigest()
    assert artifact["size_bytes"] == len(content)
    assert artifact["content_type"] == "application/dxf"


# ---------------------------------------------------------------------------
# persist_preflight_run — review-required flow
# ---------------------------------------------------------------------------


def test_review_required_flow_outcome_persisted(tmp_path: Path) -> None:
    dxf_path = tmp_path / "out.dxf"
    _write_dummy_dxf(dxf_path)
    db = FakeDbGateway()
    storage = FakeStorageGateway()

    result = persist_preflight_run(
        project_id=_PROJECT_ID,
        source_file_object_id=_FILE_OBJECT_ID,
        t7_summary=_make_t7_summary(acceptance_outcome="preflight_review_required"),
        acceptance_gate_result=_make_acceptance_gate_result(
            outcome="preflight_review_required", output_path=str(dxf_path)
        ),
        normalized_dxf_writer_result=_make_normalized_dxf_writer_result(output_path=str(dxf_path)),
        db=db,
        storage=storage,
    )

    assert result["acceptance_outcome"] == "preflight_review_required"
    assert result["run_status"] == "preflight_complete"
    assert len(db.runs) == 1
    assert db.runs[0]["acceptance_outcome"] == "preflight_review_required"


def test_review_required_flow_still_uploads_artifact(tmp_path: Path) -> None:
    dxf_path = tmp_path / "out.dxf"
    _write_dummy_dxf(dxf_path)
    db = FakeDbGateway()
    storage = FakeStorageGateway()

    persist_preflight_run(
        project_id=_PROJECT_ID,
        source_file_object_id=_FILE_OBJECT_ID,
        t7_summary=_make_t7_summary(acceptance_outcome="preflight_review_required"),
        acceptance_gate_result=_make_acceptance_gate_result(
            outcome="preflight_review_required", output_path=str(dxf_path)
        ),
        normalized_dxf_writer_result=_make_normalized_dxf_writer_result(output_path=str(dxf_path)),
        db=db,
        storage=storage,
    )

    assert len(storage.uploads) == 1, "artifact must be uploaded even in review-required flow"


# ---------------------------------------------------------------------------
# persist_preflight_run — rejected flow
# ---------------------------------------------------------------------------


def test_rejected_flow_with_no_local_artifact(tmp_path: Path) -> None:
    """If no local normalized DXF exists, no upload or artifact row is created."""
    db = FakeDbGateway()
    storage = FakeStorageGateway()

    result = persist_preflight_run(
        project_id=_PROJECT_ID,
        source_file_object_id=_FILE_OBJECT_ID,
        t7_summary=_make_t7_summary(acceptance_outcome="preflight_rejected"),
        acceptance_gate_result=_make_acceptance_gate_result(
            outcome="preflight_rejected", output_path=""
        ),
        normalized_dxf_writer_result=_make_normalized_dxf_writer_result(output_path=""),
        db=db,
        storage=storage,
    )

    assert result["acceptance_outcome"] == "preflight_rejected"
    assert len(storage.uploads) == 0
    assert len(db.artifacts) == 0
    assert result["artifact_refs"] == []


def test_rejected_flow_with_local_artifact_uploads_it(tmp_path: Path) -> None:
    """Even a rejected run uploads the normalized DXF if it exists."""
    dxf_path = tmp_path / "out.dxf"
    _write_dummy_dxf(dxf_path)
    db = FakeDbGateway()
    storage = FakeStorageGateway()

    result = persist_preflight_run(
        project_id=_PROJECT_ID,
        source_file_object_id=_FILE_OBJECT_ID,
        t7_summary=_make_t7_summary(acceptance_outcome="preflight_rejected"),
        acceptance_gate_result=_make_acceptance_gate_result(
            outcome="preflight_rejected", output_path=str(dxf_path)
        ),
        normalized_dxf_writer_result=_make_normalized_dxf_writer_result(output_path=str(dxf_path)),
        db=db,
        storage=storage,
    )

    assert len(storage.uploads) == 1
    assert len(db.artifacts) == 1
    assert len(result["artifact_refs"]) == 1


# ---------------------------------------------------------------------------
# persist_preflight_run — diagnostics rows from T7 issue summary
# ---------------------------------------------------------------------------


def test_diagnostics_rows_from_t7_issue_summary(tmp_path: Path) -> None:
    issues = [
        {
            "severity": "blocking",
            "source": "role_resolver",
            "family": "cut_like_topology_ambiguous",
            "code": "ROLE_RESOLVER_CUT_LIKE_TOPOLOGY_AMBIGUOUS",
            "display_code": "ROLE_RESOLVER_CUT_LIKE_TOPOLOGY_AMBIGUOUS",
            "message": "Topology ambiguous.",
            "details": {"layer": "LASER_X"},
        },
        {
            "severity": "review_required",
            "source": "gap_repair",
            "family": "gap_candidate_over_threshold",
            "code": "GAP_REPAIR_GAP_CANDIDATE_OVER_THRESHOLD",
            "display_code": "GAP_REPAIR_GAP_CANDIDATE_OVER_THRESHOLD",
            "message": "Gap over threshold.",
            "details": {"gap_mm": 3.5},
        },
    ]
    db = FakeDbGateway()
    storage = FakeStorageGateway()

    result = persist_preflight_run(
        project_id=_PROJECT_ID,
        source_file_object_id=_FILE_OBJECT_ID,
        t7_summary=_make_t7_summary(issues=issues),
        acceptance_gate_result=_make_acceptance_gate_result(outcome="preflight_rejected"),
        normalized_dxf_writer_result=_make_normalized_dxf_writer_result(),
        db=db,
        storage=storage,
    )

    assert result["diagnostics_count"] == 2
    assert len(db.diagnostics) == 2

    first = db.diagnostics[0]
    assert first["severity"] == "blocking"
    assert first["source"] == "role_resolver"
    assert first["family"] == "cut_like_topology_ambiguous"
    assert first["code"] == "ROLE_RESOLVER_CUT_LIKE_TOPOLOGY_AMBIGUOUS"
    assert first["diagnostic_seq"] == 0

    second = db.diagnostics[1]
    assert second["severity"] == "review_required"
    assert second["diagnostic_seq"] == 1


def test_empty_issue_summary_produces_zero_diagnostics(tmp_path: Path) -> None:
    db = FakeDbGateway()
    storage = FakeStorageGateway()

    result = persist_preflight_run(
        project_id=_PROJECT_ID,
        source_file_object_id=_FILE_OBJECT_ID,
        t7_summary=_make_t7_summary(issues=[]),
        acceptance_gate_result=_make_acceptance_gate_result(),
        normalized_dxf_writer_result=_make_normalized_dxf_writer_result(),
        db=db,
        storage=storage,
    )

    assert result["diagnostics_count"] == 0
    assert len(db.diagnostics) == 0


# ---------------------------------------------------------------------------
# persist_preflight_run — summary_jsonb snapshot
# ---------------------------------------------------------------------------


def test_summary_jsonb_snapshot_preserves_t7_structure(tmp_path: Path) -> None:
    t7 = _make_t7_summary()
    db = FakeDbGateway()
    storage = FakeStorageGateway()

    result = persist_preflight_run(
        project_id=_PROJECT_ID,
        source_file_object_id=_FILE_OBJECT_ID,
        t7_summary=t7,
        acceptance_gate_result=_make_acceptance_gate_result(),
        normalized_dxf_writer_result=_make_normalized_dxf_writer_result(),
        db=db,
        storage=storage,
    )

    assert "summary_snapshot" in result
    snapshot = result["summary_snapshot"]
    assert isinstance(snapshot, dict)
    assert "issue_summary" in snapshot
    assert "acceptance_summary" in snapshot

    # The run row must also have summary_jsonb.
    assert len(db.runs) == 1
    assert "summary_jsonb" in db.runs[0]
    assert "issue_summary" in db.runs[0]["summary_jsonb"]


# ---------------------------------------------------------------------------
# persist_preflight_run — rules profile snapshot (no FK domain needed)
# ---------------------------------------------------------------------------


def test_rules_profile_snapshot_stored_without_fk(tmp_path: Path) -> None:
    profile = {"auto_repair_enabled": True, "max_gap_close_mm": 1.5, "strict_mode": False}
    db = FakeDbGateway()
    storage = FakeStorageGateway()

    persist_preflight_run(
        project_id=_PROJECT_ID,
        source_file_object_id=_FILE_OBJECT_ID,
        t7_summary=_make_t7_summary(),
        acceptance_gate_result=_make_acceptance_gate_result(),
        normalized_dxf_writer_result=_make_normalized_dxf_writer_result(),
        rules_profile=profile,
        db=db,
        storage=storage,
    )

    run_row = db.runs[0]
    snapshot = run_row["rules_profile_snapshot_jsonb"]
    assert snapshot["auto_repair_enabled"] is True
    assert snapshot["max_gap_close_mm"] == 1.5


def test_rules_profile_none_stores_empty_snapshot(tmp_path: Path) -> None:
    db = FakeDbGateway()
    storage = FakeStorageGateway()

    persist_preflight_run(
        project_id=_PROJECT_ID,
        source_file_object_id=_FILE_OBJECT_ID,
        t7_summary=_make_t7_summary(),
        acceptance_gate_result=_make_acceptance_gate_result(),
        normalized_dxf_writer_result=_make_normalized_dxf_writer_result(),
        rules_profile=None,
        db=db,
        storage=storage,
    )

    run_row = db.runs[0]
    assert run_row["rules_profile_snapshot_jsonb"] == {}


# ---------------------------------------------------------------------------
# persist_preflight_run — artifact storage truth
# ---------------------------------------------------------------------------


def test_artifact_row_has_explicit_storage_truth(tmp_path: Path) -> None:
    dxf_path = tmp_path / "out.dxf"
    _write_dummy_dxf(dxf_path)
    db = FakeDbGateway()
    storage = FakeStorageGateway()

    persist_preflight_run(
        project_id=_PROJECT_ID,
        source_file_object_id=_FILE_OBJECT_ID,
        t7_summary=_make_t7_summary(),
        acceptance_gate_result=_make_acceptance_gate_result(output_path=str(dxf_path)),
        normalized_dxf_writer_result=_make_normalized_dxf_writer_result(output_path=str(dxf_path)),
        db=db,
        storage=storage,
    )

    artifact = db.artifacts[0]
    # Explicit storage truth fields must be present — not buried in metadata_jsonb.
    assert "storage_bucket" in artifact
    assert "storage_path" in artifact
    assert "artifact_hash_sha256" in artifact
    assert "content_type" in artifact
    assert "size_bytes" in artifact
    assert artifact["storage_bucket"] == "geometry-artifacts"


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_invalid_project_id_raises() -> None:
    db = FakeDbGateway()
    storage = FakeStorageGateway()
    with pytest.raises(DxfPreflightPersistenceError):
        persist_preflight_run(
            project_id="",
            source_file_object_id=_FILE_OBJECT_ID,
            t7_summary=_make_t7_summary(),
            acceptance_gate_result=_make_acceptance_gate_result(),
            normalized_dxf_writer_result=_make_normalized_dxf_writer_result(),
            db=db,
            storage=storage,
        )


def test_non_mapping_t7_summary_raises() -> None:
    db = FakeDbGateway()
    storage = FakeStorageGateway()
    with pytest.raises(DxfPreflightPersistenceError):
        persist_preflight_run(
            project_id=_PROJECT_ID,
            source_file_object_id=_FILE_OBJECT_ID,
            t7_summary="not a mapping",  # type: ignore[arg-type]
            acceptance_gate_result=_make_acceptance_gate_result(),
            normalized_dxf_writer_result=_make_normalized_dxf_writer_result(),
            db=db,
            storage=storage,
        )


def test_non_mapping_acceptance_gate_result_raises() -> None:
    db = FakeDbGateway()
    storage = FakeStorageGateway()
    with pytest.raises(DxfPreflightPersistenceError):
        persist_preflight_run(
            project_id=_PROJECT_ID,
            source_file_object_id=_FILE_OBJECT_ID,
            t7_summary=_make_t7_summary(),
            acceptance_gate_result=None,  # type: ignore[arg-type]
            normalized_dxf_writer_result=_make_normalized_dxf_writer_result(),
            db=db,
            storage=storage,
        )


def test_invalid_run_seq_raises() -> None:
    db = FakeDbGateway()
    storage = FakeStorageGateway()
    with pytest.raises(DxfPreflightPersistenceError):
        persist_preflight_run(
            project_id=_PROJECT_ID,
            source_file_object_id=_FILE_OBJECT_ID,
            t7_summary=_make_t7_summary(),
            acceptance_gate_result=_make_acceptance_gate_result(),
            normalized_dxf_writer_result=_make_normalized_dxf_writer_result(),
            run_seq=0,
            db=db,
            storage=storage,
        )


def test_no_route_or_request_model_in_service() -> None:
    """The persistence service must not import FastAPI or create routes."""
    import importlib.util
    import sys

    spec = importlib.util.find_spec("api.services.dxf_preflight_persistence")
    assert spec is not None

    source_path = spec.origin
    assert source_path is not None

    with open(source_path) as f:
        source = f.read()

    for forbidden in ("fastapi", "APIRouter", "HTTPException", "@app.post", "@router.post"):
        assert forbidden not in source, f"Persistence service must not reference '{forbidden}'"
