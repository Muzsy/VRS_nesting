#!/usr/bin/env python3
"""DXF Prefilter E3-T1 -- preflight persistence and artifact storage smoke.

Deterministic smoke for the preflight persistence bridge. It wires up
fake DB and storage gateways (no real Supabase), runs the full
T7-summary → persist_preflight_run chain, and verifies the contract for
each scenario.

Scenarios covered:

* ACCEPTED FLOW -- run row, diagnostics, normalized DXF upload to
  geometry-artifacts bucket, preflight_artifacts row with explicit storage truth.
* REVIEW-REQUIRED FLOW -- outcome persisted, artifact still uploaded.
* REJECTED FLOW WITHOUT ARTIFACT -- no upload, no artifact row, run row OK.
* RULES PROFILE SNAPSHOT -- stored as JSONB, no FK domain required.
* CANONICAL STORAGE PATH SHAPE -- correct bucket / path / hash / extension.
* T7 SUMMARY SNAPSHOT -- summary_jsonb preserved verbatim in run row.
* DIAGNOSTICS ROWS FROM T7 ISSUE SUMMARY -- one row per normalized issue,
  correct seq / severity / code / source.
* OUTPUT SHAPE -- no acceptance_outcome computation, no route leak.
"""

from __future__ import annotations

import hashlib
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.dxf_preflight_persistence import (
    canonical_preflight_storage_path,
    persist_preflight_run,
)


# ---------------------------------------------------------------------------
# Fake gateways
# ---------------------------------------------------------------------------


class FakeDb:
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


class FakeStorage:
    def __init__(self) -> None:
        self.uploads: list[dict[str, Any]] = []

    def upload_bytes(self, *, bucket: str, object_key: str, payload: bytes, content_type: str) -> None:
        self.uploads.append({"bucket": bucket, "object_key": object_key,
                              "size": len(payload), "content_type": content_type})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_PROJECT_ID = str(uuid.uuid4())
_FILE_OBJECT_ID = str(uuid.uuid4())

FORBIDDEN_RESULT_KEYS = (
    "blocking_reasons",
    "review_required_reasons",
    "importer_probe",
    "validator_probe",
    "normalized_dxf",
    "acceptance_gate",
    "route",
    "fastapi",
)


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _write_dxf(path: Path) -> bytes:
    content = b"0\nSECTION\n2\nENTITIES\n0\nENDSEC\n0\nEOF\n"
    path.write_bytes(content)
    return content


def _t7_summary(outcome: str = "accepted_for_import", issues: list[dict] | None = None) -> dict:
    items = issues or []
    return {
        "source_inventory_summary": {"source_path": "/tmp/test.dxf"},
        "acceptance_summary": {"acceptance_outcome": outcome},
        "issue_summary": {
            "normalized_issues": items,
            "blocking_issues": [i for i in items if i.get("severity") == "blocking"],
            "review_required_issues": [i for i in items if i.get("severity") == "review_required"],
            "warning_issues": [],
            "info_issues": [],
            "counts_by_severity": {
                "blocking": sum(1 for i in items if i.get("severity") == "blocking"),
                "review_required": sum(1 for i in items if i.get("severity") == "review_required"),
                "warning": 0, "info": 0,
            },
        },
        "repair_summary": {"counts": {}},
        "role_mapping_summary": {},
        "artifact_references": [],
    }


def _gate_result(outcome: str, output_path: str = "") -> dict:
    return {
        "acceptance_outcome": outcome,
        "normalized_dxf_echo": {"output_path": output_path, "writer_backend": "ezdxf",
                                  "written_layers": ["CUT_OUTER"], "written_entity_count": 1},
        "importer_probe": {"is_pass": True},
        "validator_probe": {"is_pass": True, "status": "validated"},
        "blocking_reasons": [], "review_required_reasons": [], "diagnostics": {},
    }


def _writer_result(output_path: str = "") -> dict:
    return {
        "normalized_dxf": {"output_path": output_path, "writer_backend": "ezdxf",
                            "written_layers": ["CUT_OUTER"], "written_entity_count": 1,
                            "cut_contour_count": 1, "marking_entity_count": 0},
        "skipped_source_entities": [],
        "diagnostics": {"notes": []},
    }


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


def _scenario_canonical_storage_path_shape() -> None:
    path = canonical_preflight_storage_path(
        project_id="proj-abc",
        preflight_run_id="run-xyz",
        artifact_kind="normalized_dxf",
        content_hash_sha256="deadbeef",
        extension="dxf",
    )
    _assert(
        path == "projects/proj-abc/preflight/run-xyz/normalized_dxf/deadbeef.dxf",
        f"canonical path shape wrong: {path}",
    )


def _scenario_accepted_flow(tmpdir: Path) -> None:
    dxf_path = tmpdir / "accepted.dxf"
    content = _write_dxf(dxf_path)
    db = FakeDb()
    storage = FakeStorage()

    result = persist_preflight_run(
        project_id=_PROJECT_ID,
        source_file_object_id=_FILE_OBJECT_ID,
        t7_summary=_t7_summary("accepted_for_import"),
        acceptance_gate_result=_gate_result("accepted_for_import", str(dxf_path)),
        normalized_dxf_writer_result=_writer_result(str(dxf_path)),
        db=db,
        storage=storage,
    )

    _assert(len(db.runs) == 1, "accepted flow must create 1 run row")
    _assert(db.runs[0]["acceptance_outcome"] == "accepted_for_import",
            "run row must have accepted outcome")
    _assert(len(storage.uploads) == 1, "accepted flow must upload 1 artifact")
    _assert(storage.uploads[0]["bucket"] == "geometry-artifacts",
            "upload must go to geometry-artifacts bucket")
    expected_hash = hashlib.sha256(content).hexdigest()
    _assert(expected_hash in storage.uploads[0]["object_key"],
            "storage path must contain content hash")
    _assert(len(db.artifacts) == 1, "accepted flow must create 1 artifact row")
    artifact = db.artifacts[0]
    _assert(artifact["storage_bucket"] == "geometry-artifacts",
            "artifact row must have explicit storage_bucket")
    _assert("storage_path" in artifact, "artifact row must have storage_path")
    _assert("artifact_hash_sha256" in artifact, "artifact row must have hash")
    _assert(len(result["artifact_refs"]) == 1, "result must have 1 artifact ref")

    for forbidden in FORBIDDEN_RESULT_KEYS:
        _assert(forbidden not in result, f"result must not expose '{forbidden}'")


def _scenario_review_required_flow(tmpdir: Path) -> None:
    dxf_path = tmpdir / "review.dxf"
    _write_dxf(dxf_path)
    db = FakeDb()
    storage = FakeStorage()

    result = persist_preflight_run(
        project_id=_PROJECT_ID,
        source_file_object_id=_FILE_OBJECT_ID,
        t7_summary=_t7_summary("preflight_review_required"),
        acceptance_gate_result=_gate_result("preflight_review_required", str(dxf_path)),
        normalized_dxf_writer_result=_writer_result(str(dxf_path)),
        db=db,
        storage=storage,
    )

    _assert(result["acceptance_outcome"] == "preflight_review_required",
            "review-required outcome must be persisted")
    _assert(len(storage.uploads) == 1, "review-required flow still uploads artifact")
    _assert(result["run_status"] == "preflight_complete", "run_status must be preflight_complete")


def _scenario_rejected_flow_no_artifact() -> None:
    db = FakeDb()
    storage = FakeStorage()

    result = persist_preflight_run(
        project_id=_PROJECT_ID,
        source_file_object_id=_FILE_OBJECT_ID,
        t7_summary=_t7_summary("preflight_rejected"),
        acceptance_gate_result=_gate_result("preflight_rejected", output_path=""),
        normalized_dxf_writer_result=_writer_result(output_path=""),
        db=db,
        storage=storage,
    )

    _assert(result["acceptance_outcome"] == "preflight_rejected",
            "rejected outcome must be persisted")
    _assert(len(storage.uploads) == 0, "no upload when no local artifact")
    _assert(len(db.artifacts) == 0, "no artifact row when no local artifact")
    _assert(result["artifact_refs"] == [], "empty artifact_refs when no artifact")
    _assert(len(db.runs) == 1, "run row must still be created")


def _scenario_diagnostics_rows_from_t7(tmpdir: Path) -> None:
    issues = [
        {"severity": "blocking", "source": "role_resolver", "family": "foo",
         "code": "ROLE_RESOLVER_FOO", "display_code": "ROLE_RESOLVER_FOO",
         "message": "Blocking issue.", "details": {}},
        {"severity": "review_required", "source": "gap_repair", "family": "bar",
         "code": "GAP_REPAIR_BAR", "display_code": "GAP_REPAIR_BAR",
         "message": "Review required issue.", "details": {"gap_mm": 2.5}},
    ]
    db = FakeDb()
    storage = FakeStorage()

    result = persist_preflight_run(
        project_id=_PROJECT_ID,
        source_file_object_id=_FILE_OBJECT_ID,
        t7_summary=_t7_summary("preflight_rejected", issues=issues),
        acceptance_gate_result=_gate_result("preflight_rejected"),
        normalized_dxf_writer_result=_writer_result(),
        db=db,
        storage=storage,
    )

    _assert(result["diagnostics_count"] == 2, f"expected 2 diagnostics, got {result['diagnostics_count']}")
    _assert(len(db.diagnostics) == 2, f"expected 2 diagnostic rows, got {len(db.diagnostics)}")
    _assert(db.diagnostics[0]["severity"] == "blocking", "first diag must be blocking")
    _assert(db.diagnostics[0]["diagnostic_seq"] == 0, "seq must start at 0")
    _assert(db.diagnostics[1]["severity"] == "review_required", "second diag must be review_required")
    _assert(db.diagnostics[1]["diagnostic_seq"] == 1, "seq must be sequential")


def _scenario_t7_summary_snapshot_in_run_row() -> None:
    t7 = _t7_summary("accepted_for_import")
    db = FakeDb()
    storage = FakeStorage()

    persist_preflight_run(
        project_id=_PROJECT_ID,
        source_file_object_id=_FILE_OBJECT_ID,
        t7_summary=t7,
        acceptance_gate_result=_gate_result("accepted_for_import"),
        normalized_dxf_writer_result=_writer_result(),
        db=db,
        storage=storage,
    )

    run = db.runs[0]
    _assert("summary_jsonb" in run, "run row must have summary_jsonb")
    _assert("issue_summary" in run["summary_jsonb"],
            "summary_jsonb must contain issue_summary from T7")
    _assert("acceptance_summary" in run["summary_jsonb"],
            "summary_jsonb must contain acceptance_summary from T7")


def _scenario_rules_profile_snapshot_no_fk() -> None:
    profile = {"auto_repair_enabled": True, "max_gap_close_mm": 2.0, "strict_mode": False}
    db = FakeDb()
    storage = FakeStorage()

    persist_preflight_run(
        project_id=_PROJECT_ID,
        source_file_object_id=_FILE_OBJECT_ID,
        t7_summary=_t7_summary(),
        acceptance_gate_result=_gate_result("accepted_for_import"),
        normalized_dxf_writer_result=_writer_result(),
        rules_profile=profile,
        db=db,
        storage=storage,
    )

    snapshot = db.runs[0]["rules_profile_snapshot_jsonb"]
    _assert(snapshot["auto_repair_enabled"] is True, "rules profile snapshot must be persisted")
    _assert(snapshot["max_gap_close_mm"] == 2.0, "rules profile max_gap_close_mm must be in snapshot")
    # No FK to dxf_rules_profiles table — just JSONB snapshot is sufficient.


def _scenario_no_route_or_request_model_in_service() -> None:
    import importlib.util
    spec = importlib.util.find_spec("api.services.dxf_preflight_persistence")
    assert spec is not None and spec.origin
    with open(spec.origin) as f:
        source = f.read()
    for forbidden in ("fastapi", "APIRouter", "HTTPException", "@app.post", "@router.post"):
        _assert(forbidden not in source,
                f"persistence service must not reference '{forbidden}'")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def main() -> int:
    with tempfile.TemporaryDirectory() as _tmp:
        tmpdir = Path(_tmp)

        _scenario_canonical_storage_path_shape()
        _scenario_accepted_flow(tmpdir)
        _scenario_review_required_flow(tmpdir)
        _scenario_rejected_flow_no_artifact()
        _scenario_diagnostics_rows_from_t7(tmpdir)
        _scenario_t7_summary_snapshot_in_run_row()
        _scenario_rules_profile_snapshot_no_fk()
        _scenario_no_route_or_request_model_in_service()

    print("[OK] DXF Prefilter E3-T1 preflight persistence and artifact storage smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
