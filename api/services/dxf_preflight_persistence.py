#!/usr/bin/env python3
"""DXF Prefilter E3-T1 -- preflight persistence and artifact storage service (V1).

This module is the persistence bridge between the local E2 prefilter truth
(T1 inspect → T2 role resolution → T3 gap repair → T4 duplicate dedupe →
T5 normalized DXF writer → T6 acceptance gate → T7 diagnostics summary) and
canonical DB + storage truth.

Responsibilities:

* Create a ``preflight_runs`` row capturing the T6 acceptance outcome, the T7
  summary snapshot, source/normalized hashes, and a rules-profile JSONB snapshot.
* Expand ``t7_summary.issue_summary.items`` into per-row ``preflight_diagnostics``
  records (one row per normalized issue entry).
* Upload the T5 normalized DXF local artifact to the ``geometry-artifacts``
  bucket at a canonical content-addressed path.
* Create a ``preflight_artifacts`` row capturing the storage reference explicitly
  (``storage_bucket``, ``storage_path``, ``artifact_hash_sha256``, ``content_type``,
  ``size_bytes``, ``metadata_jsonb``).
* Return a persisted summary truth with run id, diagnostics count, artifact refs,
  and the persisted summary snapshot.

Scope boundary (intentional):

* does NOT create a FastAPI route or request model,
* does NOT run a new DXF parse / importer / validator probe,
* does NOT implement the full rules-profile domain
  (``dxf_rules_profiles`` / ``dxf_rules_profile_versions``) — rules profile is
  stored as a JSONB snapshot instead,
* does NOT add a geometry import gate or upload trigger,
* does NOT produce a signed download URL or artifact-listing endpoint,
* does NOT update the ``files.py`` finalize flow.

Canonical storage path pattern:
  ``projects/{project_id}/preflight/{preflight_run_id}/{artifact_kind}/{content_hash}.{ext}``
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

__all__ = [
    "DxfPreflightPersistenceError",
    "persist_preflight_run",
    "persist_preflight_failed_run",
    "canonical_preflight_storage_path",
    "RunSeqQueryGateway",
    "get_next_run_seq",
]

_PREFLIGHT_ARTIFACT_BUCKET = "geometry-artifacts"
_NORMALIZED_DXF_CONTENT_TYPE = "application/dxf"
_NORMALIZED_DXF_ARTIFACT_KIND = "normalized_dxf"


# ---------------------------------------------------------------------------
# Protocols (fake-able for tests)
# ---------------------------------------------------------------------------


class DbGateway(Protocol):
    """Minimal DB insert protocol — only what E3-T1 needs."""

    def insert_preflight_run(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        """Insert app.preflight_runs row; return the inserted row (with id)."""
        ...

    def insert_preflight_diagnostic(self, *, payload: dict[str, Any]) -> None:
        """Insert one app.preflight_diagnostics row."""
        ...

    def insert_preflight_artifact(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        """Insert app.preflight_artifacts row; return the inserted row (with id)."""
        ...


class StorageGateway(Protocol):
    """Minimal storage upload protocol — only what E3-T1 needs."""

    def upload_bytes(
        self,
        *,
        bucket: str,
        object_key: str,
        payload: bytes,
        content_type: str,
    ) -> None:
        """Upload raw bytes to the given bucket / object_key."""
        ...


class RunSeqQueryGateway(Protocol):
    """Minimal query protocol for resolving the next preflight run_seq."""

    def fetch_max_run_seq(self, *, source_file_object_id: str) -> int | None:
        """Return the current max run_seq for this source file, or None if no rows exist."""
        ...


# ---------------------------------------------------------------------------
# Public exception
# ---------------------------------------------------------------------------


class DxfPreflightPersistenceError(RuntimeError):
    """Raised for structural misuse or unrecoverable persistence failures.

    DXF-level issues that should surface as diagnostics should NOT raise this;
    this exception is reserved for caller-error or I/O failures.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def canonical_preflight_storage_path(
    *,
    project_id: str,
    preflight_run_id: str,
    artifact_kind: str,
    content_hash_sha256: str,
    extension: str,
) -> str:
    """Return the canonical storage path for a preflight artifact.

    Pattern:
        projects/{project_id}/preflight/{preflight_run_id}/{artifact_kind}/{content_hash}.{ext}
    """
    project = _require_id(project_id, field="project_id")
    run = _require_id(preflight_run_id, field="preflight_run_id")
    kind = _require_id(artifact_kind, field="artifact_kind")
    digest = _require_id(content_hash_sha256, field="content_hash_sha256")
    ext = _require_id(extension, field="extension").lower().lstrip(".")
    return f"projects/{project}/preflight/{run}/{kind}/{digest}.{ext}"


def persist_preflight_run(
    *,
    project_id: str,
    source_file_object_id: str,
    t7_summary: Mapping[str, Any],
    acceptance_gate_result: Mapping[str, Any],
    normalized_dxf_writer_result: Mapping[str, Any],
    rules_profile: Mapping[str, Any] | None = None,
    run_seq: int = 1,
    db: DbGateway,
    storage: StorageGateway,
) -> dict[str, Any]:
    """Persist the local T1→T7 preflight truth to DB + canonical artifact storage.

    Parameters
    ----------
    project_id:
        UUID string of the owning project.
    source_file_object_id:
        UUID string of the source ``app.file_objects`` row.
    t7_summary:
        The shape returned by
        ``api.services.dxf_preflight_diagnostics_renderer.render_dxf_preflight_diagnostics_summary``.
    acceptance_gate_result:
        The shape returned by
        ``api.services.dxf_preflight_acceptance_gate.evaluate_dxf_prefilter_acceptance_gate``.
    normalized_dxf_writer_result:
        The shape returned by
        ``api.services.dxf_preflight_normalized_dxf_writer.write_normalized_dxf``.
    rules_profile:
        Optional in-memory rules profile mapping. Stored as JSONB snapshot.
        No FK to a rules-profile domain table is required or created.
    run_seq:
        Monotone sequence counter for this source file's preflight runs.
    db:
        DB gateway implementing ``DbGateway`` protocol.
    storage:
        Storage gateway implementing ``StorageGateway`` protocol.

    Returns
    -------
    dict[str, Any]
        Persisted summary truth with ``preflight_run_id``, ``diagnostics_count``,
        ``artifact_refs``, ``acceptance_outcome``, ``summary_snapshot``.
    """
    _require_str_id(project_id, field="project_id")
    _require_str_id(source_file_object_id, field="source_file_object_id")
    if not isinstance(t7_summary, Mapping):
        raise DxfPreflightPersistenceError(
            "DXF_PERSISTENCE_INVALID_T7_SUMMARY",
            "t7_summary must be a mapping as produced by render_dxf_preflight_diagnostics_summary().",
        )
    if not isinstance(acceptance_gate_result, Mapping):
        raise DxfPreflightPersistenceError(
            "DXF_PERSISTENCE_INVALID_ACCEPTANCE_GATE_RESULT",
            "acceptance_gate_result must be a mapping as produced by evaluate_dxf_prefilter_acceptance_gate().",
        )
    if not isinstance(normalized_dxf_writer_result, Mapping):
        raise DxfPreflightPersistenceError(
            "DXF_PERSISTENCE_INVALID_NORMALIZED_DXF_WRITER_RESULT",
            "normalized_dxf_writer_result must be a mapping as produced by write_normalized_dxf().",
        )
    if not isinstance(run_seq, int) or isinstance(run_seq, bool) or run_seq < 1:
        raise DxfPreflightPersistenceError(
            "DXF_PERSISTENCE_INVALID_RUN_SEQ",
            "run_seq must be a positive integer.",
        )

    acceptance_outcome = str(acceptance_gate_result.get("acceptance_outcome", "")).strip() or None
    run_status = _derive_run_status(acceptance_outcome)

    # Extract normalized DXF path + hashes.
    normalized_dxf = acceptance_gate_result.get("normalized_dxf_echo") or {}
    if not isinstance(normalized_dxf, Mapping):
        normalized_dxf = {}
    normalized_output_path = str(normalized_dxf.get("output_path", "")).strip()

    source_hash_sha256 = _sha256_of_file(normalized_output_path) if normalized_output_path else None
    normalized_hash_sha256: str | None = None

    now = datetime.now(timezone.utc).isoformat()
    summary_jsonb = _as_jsonable(dict(t7_summary))
    rules_profile_snapshot_jsonb = _as_jsonable(dict(rules_profile) if rules_profile else {})

    run_row = db.insert_preflight_run(
        payload={
            "project_id": project_id,
            "source_file_object_id": source_file_object_id,
            "run_seq": run_seq,
            "run_status": run_status,
            "acceptance_outcome": acceptance_outcome,
            "rules_profile_snapshot_jsonb": rules_profile_snapshot_jsonb,
            "summary_jsonb": summary_jsonb,
            "source_hash_sha256": source_hash_sha256,
            "normalized_hash_sha256": normalized_hash_sha256,
            "started_at": now,
            "finished_at": now,
        }
    )
    preflight_run_id = str(run_row.get("id", "")).strip()
    if not preflight_run_id:
        raise DxfPreflightPersistenceError(
            "DXF_PERSISTENCE_RUN_INSERT_FAILED",
            "insert_preflight_run did not return a row with id.",
        )

    # Insert diagnostics rows from T7 issue_summary.
    issue_summary = _as_dict(t7_summary.get("issue_summary"))
    normalized_issues = _as_dict_list(issue_summary.get("normalized_issues"))
    diagnostics_count = _insert_diagnostics(
        db=db,
        preflight_run_id=preflight_run_id,
        normalized_issues=normalized_issues,
    )

    # Upload normalized DXF artifact and register preflight_artifacts row.
    artifact_refs: list[dict[str, Any]] = []
    if normalized_output_path:
        artifact_ref = _upload_and_register_normalized_dxf(
            db=db,
            storage=storage,
            preflight_run_id=preflight_run_id,
            project_id=project_id,
            local_path=normalized_output_path,
        )
        if artifact_ref is not None:
            artifact_refs.append(artifact_ref)
            # Backfill normalized_hash_sha256 in the run row if possible.
            # (Not re-updated here to avoid an extra PATCH round-trip in V1;
            #  the hash is already in the artifact row's artifact_hash_sha256.)
            normalized_hash_sha256 = artifact_ref.get("artifact_hash_sha256")

    return {
        "preflight_run_id": preflight_run_id,
        "project_id": project_id,
        "source_file_object_id": source_file_object_id,
        "run_seq": run_seq,
        "run_status": run_status,
        "acceptance_outcome": acceptance_outcome,
        "diagnostics_count": diagnostics_count,
        "artifact_refs": artifact_refs,
        "normalized_hash_sha256": normalized_hash_sha256,
        "summary_snapshot": summary_jsonb,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _insert_diagnostics(
    *,
    db: DbGateway,
    preflight_run_id: str,
    normalized_issues: list[dict[str, Any]],
) -> int:
    """Expand T7 normalized issues into per-row preflight_diagnostics inserts."""
    count = 0
    for seq, issue in enumerate(normalized_issues):
        severity = str(issue.get("severity", "info")).strip()
        code = str(issue.get("code", "UNKNOWN")).strip() or "UNKNOWN"
        message = str(issue.get("message", "")).strip()
        source = str(issue.get("source", "")).strip()
        family = str(issue.get("family", "")).strip()
        details_jsonb = _as_jsonable(issue.get("details", {}))
        db.insert_preflight_diagnostic(
            payload={
                "preflight_run_id": preflight_run_id,
                "diagnostic_seq": seq,
                "severity": severity,
                "code": code,
                "message": message,
                "source": source,
                "family": family,
                "details_jsonb": details_jsonb,
            }
        )
        count += 1
    return count


def _upload_and_register_normalized_dxf(
    *,
    db: DbGateway,
    storage: StorageGateway,
    preflight_run_id: str,
    project_id: str,
    local_path: str,
) -> dict[str, Any] | None:
    """Upload local normalized DXF to geometry-artifacts bucket and register artifact row."""
    path = Path(local_path)
    if not path.is_file():
        return None

    payload_bytes = path.read_bytes()
    content_hash = hashlib.sha256(payload_bytes).hexdigest()
    size_bytes = len(payload_bytes)
    extension = path.suffix.lower().lstrip(".") or "dxf"

    storage_path = canonical_preflight_storage_path(
        project_id=project_id,
        preflight_run_id=preflight_run_id,
        artifact_kind=_NORMALIZED_DXF_ARTIFACT_KIND,
        content_hash_sha256=content_hash,
        extension=extension,
    )

    storage.upload_bytes(
        bucket=_PREFLIGHT_ARTIFACT_BUCKET,
        object_key=storage_path,
        payload=payload_bytes,
        content_type=_NORMALIZED_DXF_CONTENT_TYPE,
    )

    artifact_row = db.insert_preflight_artifact(
        payload={
            "preflight_run_id": preflight_run_id,
            "artifact_kind": _NORMALIZED_DXF_ARTIFACT_KIND,
            "storage_bucket": _PREFLIGHT_ARTIFACT_BUCKET,
            "storage_path": storage_path,
            "artifact_hash_sha256": content_hash,
            "content_type": _NORMALIZED_DXF_CONTENT_TYPE,
            "size_bytes": size_bytes,
            "metadata_jsonb": {
                "local_source_path": str(path),
                "extension": extension,
                "writer_backend": "ezdxf",
            },
        }
    )

    return {
        "artifact_id": str(artifact_row.get("id", "")),
        "artifact_kind": _NORMALIZED_DXF_ARTIFACT_KIND,
        "storage_bucket": _PREFLIGHT_ARTIFACT_BUCKET,
        "storage_path": storage_path,
        "artifact_hash_sha256": content_hash,
        "content_type": _NORMALIZED_DXF_CONTENT_TYPE,
        "size_bytes": size_bytes,
    }


def _derive_run_status(acceptance_outcome: str | None) -> str:
    if acceptance_outcome in {
        "accepted_for_import",
        "preflight_review_required",
        "preflight_rejected",
    }:
        return "preflight_complete"
    return "preflight_complete"


def _sha256_of_file(path_str: str) -> str | None:
    path = Path(path_str)
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_id(value: str, *, field: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise DxfPreflightPersistenceError(
            "DXF_PERSISTENCE_INVALID_ARGUMENT",
            f"{field} must be a non-empty string.",
        )
    return cleaned


def _require_str_id(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise DxfPreflightPersistenceError(
            "DXF_PERSISTENCE_INVALID_ARGUMENT",
            f"{field} must be a non-empty string.",
        )
    cleaned = value.strip()
    if not cleaned:
        raise DxfPreflightPersistenceError(
            "DXF_PERSISTENCE_INVALID_ARGUMENT",
            f"{field} must be a non-empty string.",
        )
    return cleaned


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return {str(k): v for k, v in value.items()}
    return {}


def _as_dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [
        {str(k): v for k, v in item.items()}
        for item in value
        if isinstance(item, Mapping)
    ]


def _as_jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _as_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_as_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


# ---------------------------------------------------------------------------
# E3-T2 trigger helpers (run_seq resolution + failed-run persistence)
# ---------------------------------------------------------------------------


def get_next_run_seq(
    *,
    source_file_object_id: str,
    db_query: RunSeqQueryGateway,
) -> int:
    """Return the next monotone run_seq for the given source file.

    Queries ``app.preflight_runs`` via ``db_query.fetch_max_run_seq`` and
    returns ``max + 1``, or ``1`` if no prior run exists.
    """
    _require_str_id(source_file_object_id, field="source_file_object_id")
    current_max = db_query.fetch_max_run_seq(source_file_object_id=source_file_object_id)
    if current_max is None:
        return 1
    if not isinstance(current_max, int) or isinstance(current_max, bool) or current_max < 1:
        return 1
    return current_max + 1


def persist_preflight_failed_run(
    *,
    project_id: str,
    source_file_object_id: str,
    run_seq: int,
    error_message: str,
    db: DbGateway,
) -> dict[str, Any]:
    """Persist a minimal failed preflight run row (no diagnostics, no artifact).

    Used by the E3-T2 runtime when the pipeline fails before the T7 summary
    is available, so a full ``persist_preflight_run`` call is not possible.
    Returns the inserted row dict.
    """
    _require_str_id(project_id, field="project_id")
    _require_str_id(source_file_object_id, field="source_file_object_id")
    if not isinstance(run_seq, int) or isinstance(run_seq, bool) or run_seq < 1:
        raise DxfPreflightPersistenceError(
            "DXF_PERSISTENCE_INVALID_RUN_SEQ",
            "run_seq must be a positive integer.",
        )
    now = datetime.now(timezone.utc).isoformat()
    safe_message = str(error_message or "").strip()[:2000]
    run_row = db.insert_preflight_run(
        payload={
            "project_id": project_id,
            "source_file_object_id": source_file_object_id,
            "run_seq": run_seq,
            "run_status": "preflight_failed",
            "acceptance_outcome": None,
            "rules_profile_snapshot_jsonb": {},
            "summary_jsonb": {"error": safe_message},
            "source_hash_sha256": None,
            "normalized_hash_sha256": None,
            "started_at": now,
            "finished_at": now,
        }
    )
    return dict(run_row)
