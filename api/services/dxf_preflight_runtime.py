#!/usr/bin/env python3
"""DXF Prefilter E3-T2 — Preflight runtime/orchestration service (V1).

Orchestrates the full T1→T7 + E3-T1 prefilter pipeline against a
storage-backed source DXF. Called as a FastAPI BackgroundTask after a
successful ``source_dxf`` upload finalize.

Pipeline order:
  1. ``inspect_dxf_source``                       (E2-T1)
  2. ``resolve_dxf_roles``                         (E2-T2)
  3. ``repair_dxf_gaps``                           (E2-T3)
  4. ``dedupe_dxf_duplicate_contours``             (E2-T4)
  5. ``write_normalized_dxf``                      (E2-T5)
  6. ``evaluate_dxf_prefilter_acceptance_gate``    (E2-T6)
  7. ``render_dxf_preflight_diagnostics_summary``  (E2-T7)
  8. ``persist_preflight_run``                     (E3-T1)

Scope boundary (intentional):

* does NOT create a FastAPI route or request model,
* does NOT implement a geometry import gate or replace/rerun flow,
* does NOT implement the full rules-profile domain; it consumes only the
  optional snapshot mapping passed from upload finalize,
* does NOT introduce worker queue, outbox, polling, or heartbeat,
* does NOT duplicate E2/T7 service logic.
"""

from __future__ import annotations

import logging
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from api.services.dxf_geometry_import import import_dxf_geometry_revision_from_storage
from api.services.dxf_preflight_acceptance_gate import evaluate_dxf_prefilter_acceptance_gate
from api.services.dxf_preflight_diagnostics_renderer import render_dxf_preflight_diagnostics_summary
from api.services.dxf_preflight_duplicate_dedupe import dedupe_dxf_duplicate_contours
from api.services.dxf_preflight_gap_repair import repair_dxf_gaps
from api.services.dxf_preflight_inspect import inspect_dxf_source
from api.services.dxf_preflight_normalized_dxf_writer import write_normalized_dxf
from api.services.dxf_preflight_persistence import (
    DbGateway,
    RunSeqQueryGateway,
    StorageGateway,
    get_next_run_seq,
    persist_preflight_failed_run,
    persist_preflight_run,
)
from api.services.dxf_preflight_role_resolver import resolve_dxf_roles
from api.services.file_ingest_metadata import download_storage_object_blob
from api.supabase_client import SupabaseClient, SupabaseHTTPError

logger = logging.getLogger("vrs_api.dxf_preflight_runtime")
_ACCEPTED_FOR_IMPORT = "accepted_for_import"
_NORMALIZED_DXF_ARTIFACT_KIND = "normalized_dxf"

__all__ = [
    "DxfPreflightRuntimeError",
    "run_preflight_for_upload",
]


class DxfPreflightRuntimeError(RuntimeError):
    """Raised for unrecoverable runtime/orchestration failures."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


# ---------------------------------------------------------------------------
# Concrete gateways (SupabaseClient wrappers)
# ---------------------------------------------------------------------------


class _SupabaseDbGateway:
    """Concrete DbGateway wrapping SupabaseClient for preflight runtime use."""

    def __init__(self, *, supabase: SupabaseClient, access_token: str) -> None:
        self._supabase = supabase
        self._access_token = access_token

    def insert_preflight_run(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        return self._supabase.insert_row(
            table="app.preflight_runs",
            access_token=self._access_token,
            payload=payload,
        )

    def insert_preflight_diagnostic(self, *, payload: dict[str, Any]) -> None:
        self._supabase.insert_row(
            table="app.preflight_diagnostics",
            access_token=self._access_token,
            payload=payload,
        )

    def insert_preflight_artifact(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        return self._supabase.insert_row(
            table="app.preflight_artifacts",
            access_token=self._access_token,
            payload=payload,
        )


class _SupabaseRunSeqQueryGateway:
    """Concrete RunSeqQueryGateway wrapping SupabaseClient."""

    def __init__(self, *, supabase: SupabaseClient, access_token: str) -> None:
        self._supabase = supabase
        self._access_token = access_token

    def fetch_max_run_seq(self, *, source_file_object_id: str) -> int | None:
        rows = self._supabase.select_rows(
            table="app.preflight_runs",
            access_token=self._access_token,
            params={
                "select": "run_seq",
                "source_file_object_id": f"eq.{source_file_object_id}",
                "order": "run_seq.desc",
                "limit": "1",
            },
        )
        if not rows:
            return None
        val = rows[0].get("run_seq")
        if isinstance(val, int) and not isinstance(val, bool):
            return val
        return None


class _SupabaseStorageGateway:
    """Concrete StorageGateway wrapping SupabaseClient via signed upload URL."""

    def __init__(
        self,
        *,
        supabase: SupabaseClient,
        access_token: str,
        signed_url_ttl_s: int,
        service_token: str | None = None,
    ) -> None:
        self._supabase = supabase
        self._access_token = access_token
        self._service_token = service_token
        self._ttl = signed_url_ttl_s

    def upload_bytes(
        self,
        *,
        bucket: str,
        object_key: str,
        payload: bytes,
        content_type: str,
    ) -> None:
        # Use service token for backend artifact uploads to bypass RLS policies
        # that restrict regular user tokens from writing to internal artifact paths.
        upload_token = self._service_token or self._access_token
        signed = self._supabase.create_signed_upload_url(
            access_token=upload_token,
            bucket=bucket,
            object_key=object_key,
            expires_in=self._ttl,
        )
        upload_url = str(signed.get("upload_url", "")).strip()
        if not upload_url:
            raise SupabaseHTTPError("signed upload url missing from response")
        self._supabase.upload_signed_object(
            signed_url=upload_url,
            payload=payload,
            content_type=content_type,
        )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_preflight_for_upload(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
    source_file_object_id: str,
    storage_bucket: str,
    storage_path: str,
    source_hash_sha256: str,
    created_by: str,
    signed_url_ttl_s: int,
    rules_profile: Mapping[str, Any] | None = None,
    service_token: str | None = None,
) -> None:
    """Run the full T1→T7 + E3-T1 prefilter pipeline as a background task.

    Called by the ``complete_upload`` route as a BackgroundTask after a
    successful source_dxf finalize. Failures are logged and, where possible,
    persisted as a minimal failed run row — they never propagate to the HTTP
    response.
    """
    _log_ctx = (
        f"project_id={project_id} "
        f"source_file_object_id={source_file_object_id} "
        f"storage_path={storage_path}"
    )

    db_gw: DbGateway = _SupabaseDbGateway(supabase=supabase, access_token=access_token)
    run_seq_gw: RunSeqQueryGateway = _SupabaseRunSeqQueryGateway(
        supabase=supabase, access_token=access_token
    )
    storage_gw: StorageGateway = _SupabaseStorageGateway(
        supabase=supabase,
        access_token=access_token,
        signed_url_ttl_s=signed_url_ttl_s,
        service_token=service_token,
    )

    try:
        run_seq = get_next_run_seq(
            source_file_object_id=source_file_object_id,
            db_query=run_seq_gw,
        )
    except Exception as exc:
        logger.warning(
            "preflight_runtime_run_seq_failed %s error=%s",
            _log_ctx,
            str(exc).strip()[:500],
        )
        run_seq = 1

    try:
        result = _execute_pipeline(
            supabase=supabase,
            access_token=access_token,
            project_id=project_id,
            source_file_object_id=source_file_object_id,
            storage_bucket=storage_bucket,
            storage_path=storage_path,
            signed_url_ttl_s=signed_url_ttl_s,
            run_seq=run_seq,
            db_gw=db_gw,
            storage_gw=storage_gw,
            rules_profile=rules_profile,
        )
        _trigger_geometry_import_after_gate(
            supabase=supabase,
            access_token=access_token,
            project_id=project_id,
            source_file_object_id=source_file_object_id,
            source_hash_sha256=source_hash_sha256,
            created_by=created_by,
            signed_url_ttl_s=signed_url_ttl_s,
            persisted_result=result,
        )
        logger.info(
            "preflight_runtime_complete %s run_seq=%s outcome=%s",
            _log_ctx,
            run_seq,
            result.get("acceptance_outcome"),
        )
    except Exception as exc:
        logger.warning(
            "preflight_runtime_failed %s run_seq=%s error=%s",
            _log_ctx,
            run_seq,
            str(exc).strip()[:500],
        )
        _try_persist_failed_run(
            project_id=project_id,
            source_file_object_id=source_file_object_id,
            run_seq=run_seq,
            error_message=str(exc).strip()[:2000],
            db=db_gw,
        )


# ---------------------------------------------------------------------------
# Internal pipeline execution
# ---------------------------------------------------------------------------


def _execute_pipeline(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
    source_file_object_id: str,
    storage_bucket: str,
    storage_path: str,
    signed_url_ttl_s: int,
    run_seq: int,
    db_gw: DbGateway,
    storage_gw: StorageGateway,
    rules_profile: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Download source DXF and execute the T1→T7 + E3-T1 pipeline."""
    blob = download_storage_object_blob(
        supabase=supabase,
        access_token=access_token,
        storage_bucket=storage_bucket,
        storage_path=storage_path,
        signed_url_ttl_s=signed_url_ttl_s,
    )

    with tempfile.TemporaryDirectory(prefix="vrs_preflight_") as tmpdir:
        tmp_path = Path(tmpdir)

        source_name = Path(storage_path).name or "source.dxf"
        source_local = tmp_path / source_name
        source_local.write_bytes(blob)

        normalized_local = tmp_path / "normalized.dxf"

        inspect_result = inspect_dxf_source(source_local)
        role_resolution = resolve_dxf_roles(inspect_result, rules_profile=rules_profile)
        gap_repair_result = repair_dxf_gaps(
            inspect_result, role_resolution, rules_profile=rules_profile
        )
        duplicate_dedupe_result = dedupe_dxf_duplicate_contours(
            inspect_result, role_resolution, gap_repair_result, rules_profile=rules_profile
        )
        normalized_dxf_writer_result = write_normalized_dxf(
            inspect_result,
            role_resolution,
            gap_repair_result,
            duplicate_dedupe_result,
            output_path=normalized_local,
            rules_profile=rules_profile,
        )
        acceptance_gate_result = evaluate_dxf_prefilter_acceptance_gate(
            inspect_result,
            role_resolution,
            gap_repair_result,
            duplicate_dedupe_result,
            normalized_dxf_writer_result,
        )
        t7_summary = render_dxf_preflight_diagnostics_summary(
            inspect_result,
            role_resolution,
            gap_repair_result,
            duplicate_dedupe_result,
            normalized_dxf_writer_result,
            acceptance_gate_result,
        )

        return persist_preflight_run(
            project_id=project_id,
            source_file_object_id=source_file_object_id,
            t7_summary=t7_summary,
            acceptance_gate_result=acceptance_gate_result,
            normalized_dxf_writer_result=normalized_dxf_writer_result,
            rules_profile=rules_profile,
            run_seq=run_seq,
            db=db_gw,
            storage=storage_gw,
        )


def _trigger_geometry_import_after_gate(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
    source_file_object_id: str,
    source_hash_sha256: str,
    created_by: str,
    signed_url_ttl_s: int,
    persisted_result: Mapping[str, Any],
) -> None:
    """Trigger geometry import only when persisted acceptance outcome is pass."""
    acceptance_outcome = str(persisted_result.get("acceptance_outcome", "")).strip()
    if acceptance_outcome != _ACCEPTED_FOR_IMPORT:
        logger.info(
            "preflight_runtime_geometry_import_skipped "
            "project_id=%s source_file_object_id=%s acceptance_outcome=%s",
            project_id,
            source_file_object_id,
            acceptance_outcome or "<empty>",
        )
        return

    normalized_ref = _find_normalized_dxf_artifact_ref(
        persisted_result.get("artifact_refs")
    )
    if normalized_ref is None:
        logger.warning(
            "preflight_runtime_geometry_import_missing_normalized_artifact "
            "project_id=%s source_file_object_id=%s acceptance_outcome=%s",
            project_id,
            source_file_object_id,
            acceptance_outcome,
        )
        return

    storage_bucket = str(normalized_ref.get("storage_bucket", "")).strip()
    storage_path = str(normalized_ref.get("storage_path", "")).strip()
    if not storage_bucket or not storage_path:
        logger.warning(
            "preflight_runtime_geometry_import_invalid_normalized_artifact "
            "project_id=%s source_file_object_id=%s acceptance_outcome=%s",
            project_id,
            source_file_object_id,
            acceptance_outcome,
        )
        return

    try:
        import_dxf_geometry_revision_from_storage(
            supabase=supabase,
            access_token=access_token,
            project_id=project_id,
            source_file_object_id=source_file_object_id,
            storage_bucket=storage_bucket,
            storage_path=storage_path,
            source_hash_sha256=source_hash_sha256,
            created_by=created_by,
            signed_url_ttl_s=signed_url_ttl_s,
        )
    except Exception as exc:
        logger.warning(
            "preflight_runtime_geometry_import_failed "
            "project_id=%s source_file_object_id=%s bucket=%s storage_path=%s error=%s",
            project_id,
            source_file_object_id,
            storage_bucket,
            storage_path,
            str(exc).strip()[:500],
        )
        return

    logger.info(
        "preflight_runtime_geometry_import_complete "
        "project_id=%s source_file_object_id=%s bucket=%s storage_path=%s",
        project_id,
        source_file_object_id,
        storage_bucket,
        storage_path,
    )


def _find_normalized_dxf_artifact_ref(artifact_refs: Any) -> dict[str, Any] | None:
    if not isinstance(artifact_refs, list):
        return None
    for item in artifact_refs:
        if not isinstance(item, Mapping):
            continue
        artifact_kind = str(item.get("artifact_kind", "")).strip()
        if artifact_kind == _NORMALIZED_DXF_ARTIFACT_KIND:
            return {str(k): v for k, v in item.items()}
    return None


def _try_persist_failed_run(
    *,
    project_id: str,
    source_file_object_id: str,
    run_seq: int,
    error_message: str,
    db: DbGateway,
) -> None:
    """Best-effort persist of a minimal failed run row; swallows its own errors."""
    try:
        persist_preflight_failed_run(
            project_id=project_id,
            source_file_object_id=source_file_object_id,
            run_seq=run_seq,
            error_message=error_message,
            db=db,
        )
    except Exception as inner_exc:
        logger.warning(
            "preflight_runtime_failed_run_persist_error "
            "project_id=%s source_file_object_id=%s error=%s",
            project_id,
            source_file_object_id,
            str(inner_exc).strip()[:500],
        )
