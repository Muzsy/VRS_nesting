from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from api.auth import AuthenticatedUser, get_current_user
from api.config import Settings
from api.deps import get_settings, get_supabase_client
from api.http_errors import raise_supabase_http_error
from api.rate_limit import enforce_user_rate_limit
from api.request_models import StrictRequestModel
from api.services.dxf_preflight_runtime import run_preflight_for_upload
from api.services.dxf_validation import validate_dxf_file_async
from api.services.file_ingest_metadata import canonical_file_name_from_storage_path, load_file_ingest_metadata
from api.supabase_client import SupabaseClient, SupabaseHTTPError


router = APIRouter(prefix="/projects/{project_id}/files", tags=["project-files"])

_ALLOWED_FILE_KINDS = {"source_dxf", "source_svg", "import_report", "artifact"}


class UploadUrlRequest(StrictRequestModel):
    filename: str = Field(min_length=1, max_length=260)
    content_type: str | None = Field(default="application/dxf", max_length=100)
    size_bytes: int = Field(gt=0)
    file_kind: str = Field(default="source_dxf", min_length=1, max_length=40)


class UploadUrlResponse(BaseModel):
    upload_url: str
    file_id: str
    storage_bucket: str
    storage_path: str
    expires_at: str


class FileCompleteRequest(StrictRequestModel):
    file_id: UUID
    file_name: str | None = Field(default=None, min_length=1, max_length=260)
    original_filename: str | None = Field(default=None, min_length=1, max_length=260)
    storage_path: str | None = Field(default=None, min_length=1)
    storage_key: str | None = Field(default=None, min_length=1)
    storage_bucket: str | None = Field(default=None, min_length=1, max_length=120)
    file_kind: str | None = Field(default=None, min_length=1, max_length=40)
    file_type: str | None = Field(default=None, min_length=1, max_length=40)
    byte_size: int | None = Field(default=None, gt=0)
    size_bytes: int | None = Field(default=None, gt=0)
    mime_type: str | None = Field(default=None, max_length=100)
    content_type: str | None = Field(default=None, max_length=100)
    sha256: str | None = Field(default=None, max_length=128)
    content_hash_sha256: str | None = Field(default=None, max_length=128)
    rules_profile_snapshot_jsonb: dict[str, Any] | None = None
    replaces_file_object_id: UUID | None = None


class FileReplaceRequest(StrictRequestModel):
    filename: str = Field(min_length=1, max_length=260)
    content_type: str | None = Field(default="application/dxf", max_length=100)
    size_bytes: int = Field(gt=0)


class FileReplaceResponse(BaseModel):
    upload_url: str
    file_id: str
    storage_bucket: str
    storage_path: str
    expires_at: str
    replaces_file_id: str


class ProjectFileResponse(BaseModel):
    id: str
    project_id: str
    storage_bucket: str
    storage_path: str
    file_name: str
    mime_type: str | None = None
    file_kind: str
    byte_size: int | None = None
    sha256: str | None = None
    uploaded_by: str | None = None
    created_at: str | None = None
    latest_preflight_summary: dict[str, Any] | None = None
    latest_preflight_diagnostics: dict[str, Any] | None = None


class ProjectFileListResponse(BaseModel):
    items: list[ProjectFileResponse]
    total: int
    page: int
    page_size: int


def _as_file_response(
    row: dict[str, Any],
    *,
    latest_preflight_summary: dict[str, Any] | None = None,
    latest_preflight_diagnostics: dict[str, Any] | None = None,
) -> ProjectFileResponse:
    uploaded_by = row.get("uploaded_by")
    return ProjectFileResponse(
        id=str(row.get("id", "")),
        project_id=str(row.get("project_id", "")),
        storage_bucket=str(row.get("storage_bucket", "")),
        storage_path=str(row.get("storage_path", "")),
        file_name=str(row.get("file_name", "")),
        mime_type=row.get("mime_type"),
        file_kind=str(row.get("file_kind", "")),
        byte_size=row.get("byte_size"),
        sha256=row.get("sha256"),
        uploaded_by=str(uploaded_by) if uploaded_by is not None else None,
        created_at=row.get("created_at"),
        latest_preflight_summary=latest_preflight_summary,
        latest_preflight_diagnostics=latest_preflight_diagnostics,
    )


def _latest_preflight_summary_from_row(row: dict[str, Any]) -> dict[str, Any]:
    summary_jsonb = row.get("summary_jsonb")
    summary_root = summary_jsonb if isinstance(summary_jsonb, dict) else {}
    issue_summary = summary_root.get("issue_summary")
    issue_summary_dict = issue_summary if isinstance(issue_summary, dict) else {}
    counts_by_severity = issue_summary_dict.get("counts_by_severity")
    severity_counts = counts_by_severity if isinstance(counts_by_severity, dict) else {}

    blocking_issue_count = _as_non_negative_int(severity_counts.get("blocking"))
    review_required_issue_count = _as_non_negative_int(severity_counts.get("review_required"))
    warning_issue_count = _as_non_negative_int(severity_counts.get("warning"))
    info_issue_count = _as_non_negative_int(severity_counts.get("info"))

    repair_summary = summary_root.get("repair_summary")
    repair_summary_dict = repair_summary if isinstance(repair_summary, dict) else {}
    repair_counts_raw = repair_summary_dict.get("counts")
    repair_counts = repair_counts_raw if isinstance(repair_counts_raw, dict) else {}
    applied_gap_repair_count = _as_non_negative_int(repair_counts.get("applied_gap_repair_count"))
    applied_duplicate_dedupe_count = _as_non_negative_int(repair_counts.get("applied_duplicate_dedupe_count"))

    run_seq = row.get("run_seq")
    run_seq_value = int(run_seq) if isinstance(run_seq, int) and not isinstance(run_seq, bool) else None
    run_status = str(row.get("run_status", "")).strip()
    acceptance_outcome = row.get("acceptance_outcome")
    return {
        "preflight_run_id": str(row.get("id", "")),
        "run_seq": run_seq_value,
        "run_status": run_status,
        "acceptance_outcome": acceptance_outcome,
        "finished_at": row.get("finished_at"),
        "blocking_issue_count": blocking_issue_count,
        "review_required_issue_count": review_required_issue_count,
        "warning_issue_count": warning_issue_count,
        "total_issue_count": blocking_issue_count + review_required_issue_count + warning_issue_count + info_issue_count,
        "applied_gap_repair_count": applied_gap_repair_count,
        "applied_duplicate_dedupe_count": applied_duplicate_dedupe_count,
        "total_repair_count": applied_gap_repair_count + applied_duplicate_dedupe_count,
        "recommended_action": _derive_recommended_action(
            run_status=run_status,
            acceptance_outcome=acceptance_outcome,
        ),
    }


def _latest_preflight_diagnostics_from_row(row: dict[str, Any]) -> dict[str, Any]:
    summary_jsonb = row.get("summary_jsonb")
    summary_root = summary_jsonb if isinstance(summary_jsonb, dict) else {}

    source_inventory_summary_raw = _as_dict(summary_root.get("source_inventory_summary"))
    role_mapping_summary_raw = _as_dict(summary_root.get("role_mapping_summary"))
    issue_summary_raw = _as_dict(summary_root.get("issue_summary"))
    repair_summary_raw = _as_dict(summary_root.get("repair_summary"))
    acceptance_summary_raw = _as_dict(summary_root.get("acceptance_summary"))

    issue_counts_by_severity_raw = _as_dict(issue_summary_raw.get("counts_by_severity"))
    repair_counts_raw = _as_dict(repair_summary_raw.get("counts"))

    return {
        "source_inventory_summary": {
            "found_layers": _as_string_list(source_inventory_summary_raw.get("found_layers")),
            "found_colors": _as_non_negative_int_list(source_inventory_summary_raw.get("found_colors")),
            "found_linetypes": _as_string_list(source_inventory_summary_raw.get("found_linetypes")),
            "entity_count": _as_non_negative_int(source_inventory_summary_raw.get("entity_count")),
            "contour_count": _as_non_negative_int(source_inventory_summary_raw.get("contour_count")),
            "open_path_layer_count": _as_non_negative_int(source_inventory_summary_raw.get("open_path_layer_count")),
            "open_path_total_count": _as_non_negative_int(source_inventory_summary_raw.get("open_path_total_count")),
            "duplicate_candidate_group_count": _as_non_negative_int(
                source_inventory_summary_raw.get("duplicate_candidate_group_count")
            ),
            "duplicate_candidate_member_count": _as_non_negative_int(
                source_inventory_summary_raw.get("duplicate_candidate_member_count")
            ),
        },
        "role_mapping_summary": {
            "resolved_role_inventory": {
                key: _as_non_negative_int(value)
                for key, value in _as_dict(role_mapping_summary_raw.get("resolved_role_inventory")).items()
            },
            "layer_role_assignments": _as_dict_list(role_mapping_summary_raw.get("layer_role_assignments")),
            "review_required_count": _as_non_negative_int(role_mapping_summary_raw.get("review_required_count")),
            "blocking_conflict_count": _as_non_negative_int(role_mapping_summary_raw.get("blocking_conflict_count")),
        },
        "issue_summary": {
            "counts_by_severity": {
                "blocking": _as_non_negative_int(issue_counts_by_severity_raw.get("blocking")),
                "review_required": _as_non_negative_int(issue_counts_by_severity_raw.get("review_required")),
                "warning": _as_non_negative_int(issue_counts_by_severity_raw.get("warning")),
                "info": _as_non_negative_int(issue_counts_by_severity_raw.get("info")),
            },
            "normalized_issues": [
                {
                    "severity": str(issue.get("severity", "")).strip(),
                    "family": str(issue.get("family", "")).strip(),
                    "code": str(issue.get("code", "")).strip(),
                    "message": str(issue.get("message", "")).strip(),
                    "source": str(issue.get("source", "")).strip(),
                }
                for issue in _as_dict_list(issue_summary_raw.get("normalized_issues"))
            ],
        },
        "repair_summary": {
            "counts": {
                "applied_gap_repair_count": _as_non_negative_int(repair_counts_raw.get("applied_gap_repair_count")),
                "applied_duplicate_dedupe_count": _as_non_negative_int(repair_counts_raw.get("applied_duplicate_dedupe_count")),
                "skipped_source_entity_count": _as_non_negative_int(repair_counts_raw.get("skipped_source_entity_count")),
                "remaining_open_path_count": _as_non_negative_int(repair_counts_raw.get("remaining_open_path_count")),
                "remaining_duplicate_count": _as_non_negative_int(repair_counts_raw.get("remaining_duplicate_count")),
                "remaining_review_required_signal_count": _as_non_negative_int(
                    repair_counts_raw.get("remaining_review_required_signal_count")
                ),
            },
            "applied_gap_repairs": _as_dict_list(repair_summary_raw.get("applied_gap_repairs")),
            "applied_duplicate_dedupes": _as_dict_list(repair_summary_raw.get("applied_duplicate_dedupes")),
            "skipped_source_entities": _as_dict_list(repair_summary_raw.get("skipped_source_entities")),
            "remaining_review_required_signals": _as_dict_list(repair_summary_raw.get("remaining_review_required_signals")),
        },
        "acceptance_summary": {
            "acceptance_outcome": str(acceptance_summary_raw.get("acceptance_outcome", "")).strip(),
            "precedence_rule_applied": str(acceptance_summary_raw.get("precedence_rule_applied", "")).strip(),
            "importer_probe": _as_dict(acceptance_summary_raw.get("importer_probe")),
            "validator_probe": _as_dict(acceptance_summary_raw.get("validator_probe")),
            "blocking_reason_count": _as_non_negative_int(acceptance_summary_raw.get("blocking_reason_count")),
            "review_required_reason_count": _as_non_negative_int(acceptance_summary_raw.get("review_required_reason_count")),
        },
        "artifact_references": [
            {
                "artifact_kind": str(artifact.get("artifact_kind", "")).strip(),
                "download_label": str(artifact.get("download_label", "")).strip(),
                "path": str(artifact.get("path", "")).strip(),
                "exists": bool(artifact.get("exists")),
            }
            for artifact in _as_dict_list(summary_root.get("artifact_references"))
        ],
    }


def _as_non_negative_int(raw: Any) -> int:
    if isinstance(raw, bool):
        return 0
    if isinstance(raw, int):
        return raw if raw >= 0 else 0
    if isinstance(raw, float) and raw.is_integer() and raw >= 0:
        return int(raw)
    return 0


def _as_dict(raw: Any) -> dict[str, Any]:
    return raw if isinstance(raw, dict) else {}


def _as_dict_list(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _as_string_list(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw]


def _as_non_negative_int_list(raw: Any) -> list[int]:
    if not isinstance(raw, list):
        return []
    values: list[int] = []
    for item in raw:
        if isinstance(item, bool):
            continue
        if isinstance(item, int) and item >= 0:
            values.append(item)
            continue
        if isinstance(item, float) and item.is_integer() and item >= 0:
            values.append(int(item))
    return values


def _derive_recommended_action(*, run_status: str, acceptance_outcome: Any) -> str:
    outcome = str(acceptance_outcome or "").strip().lower()
    if outcome == "accepted_for_import":
        return "ready_for_next_step"
    if outcome == "preflight_review_required":
        return "review_required_wait_for_diagnostics"
    if outcome == "preflight_rejected":
        return "rejected_fix_and_reupload"

    status_value = run_status.strip().lower()
    if status_value == "preflight_failed":
        return "rejected_fix_and_reupload"
    if status_value in {
        "preflight_queued",
        "preflight_running",
        "preflight_in_progress",
        "queued",
        "running",
        "in_progress",
    }:
        return "preflight_in_progress"
    if status_value == "preflight_complete":
        return "review_required_wait_for_diagnostics"
    return "preflight_not_started"


def _fetch_latest_preflight_row_by_file_id(
    *,
    supabase: SupabaseClient,
    access_token: str,
    file_ids: list[str],
) -> dict[str, dict[str, Any]]:
    if not file_ids:
        return {}

    in_values = ",".join(file_ids)
    params = {
        "select": "id,source_file_object_id,run_seq,run_status,acceptance_outcome,finished_at,summary_jsonb",
        "source_file_object_id": f"in.({in_values})",
        "order": "source_file_object_id.asc,run_seq.desc,finished_at.desc",
    }
    rows = supabase.select_rows(
        table="app.preflight_runs",
        access_token=access_token,
        params=params,
    )

    latest_by_file_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        source_file_object_id = str(row.get("source_file_object_id", "")).strip()
        if not source_file_object_id or source_file_object_id in latest_by_file_id:
            continue
        latest_by_file_id[source_file_object_id] = row
    return latest_by_file_id


def _coerce_rules_profile_snapshot(rules_profile_snapshot_jsonb: dict[str, Any] | None) -> dict[str, Any] | None:
    if rules_profile_snapshot_jsonb is None:
        return None
    if not isinstance(rules_profile_snapshot_jsonb, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="rules_profile_snapshot_jsonb must be a JSON object",
        )
    try:
        json.dumps(rules_profile_snapshot_jsonb, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="rules_profile_snapshot_jsonb must be JSON-serializable",
        ) from exc
    return rules_profile_snapshot_jsonb


def _sanitize_filename(raw_filename: str) -> str:
    safe_name = Path(raw_filename).name.strip()
    if not safe_name or safe_name in {".", ".."}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid filename")
    if "/" in safe_name or "\\" in safe_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid filename")
    return safe_name


def _normalize_file_kind(*, file_kind: str | None, file_type: str | None) -> str:
    raw = (file_kind or file_type or "").strip().lower()
    if raw in {"stock_dxf", "part_dxf"}:
        return "source_dxf"
    if raw in _ALLOWED_FILE_KINDS:
        return raw
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"unsupported file_kind: {raw or '<empty>'}")


def _ensure_project_access(
    *,
    supabase: SupabaseClient,
    user: AuthenticatedUser,
    project_id: UUID,
) -> None:
    params = {
        "select": "id",
        "id": f"eq.{project_id}",
        "owner_user_id": f"eq.{user.id}",
        "lifecycle": "neq.archived",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.projects", access_token=user.access_token, params=params)
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")


def _validate_replacement_target(
    *,
    supabase: SupabaseClient,
    user: AuthenticatedUser,
    project_id: UUID,
    replaces_file_object_id: UUID,
) -> None:
    params = {
        "select": "id,file_kind",
        "id": f"eq.{replaces_file_object_id}",
        "project_id": f"eq.{project_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.file_objects", access_token=user.access_token, params=params)
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="replacement target file not found in project")
    if str(rows[0].get("file_kind", "")).strip() != "source_dxf":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="replacement target must be a source_dxf file")


@router.post("/upload-url", response_model=UploadUrlResponse)
def create_upload_url(
    project_id: UUID,
    req: UploadUrlRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
    settings: Settings = Depends(get_settings),
) -> UploadUrlResponse:
    _ensure_project_access(supabase=supabase, user=user, project_id=project_id)
    enforce_user_rate_limit(
        supabase=supabase,
        access_token=user.access_token,
        user_id=user.id,
        table="app.file_objects",
        timestamp_field="created_at",
        limit=settings.rate_limit_upload_urls_per_window,
        window_seconds=settings.rate_limit_window_s,
        route_key="POST /v1/projects/{project_id}/files/upload-url",
        filters={
            "uploaded_by": f"eq.{user.id}",
            "project_id": f"eq.{project_id}",
        },
    )

    if req.size_bytes > settings.max_dxf_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"file too large: max={settings.max_dxf_size_bytes} bytes",
        )

    safe_name = _sanitize_filename(req.filename)
    normalized_kind = _normalize_file_kind(file_kind=req.file_kind, file_type=None)
    if normalized_kind == "source_dxf" and not safe_name.lower().endswith(".dxf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="DXF file must have .dxf extension")

    file_id = str(uuid4())
    storage_path = f"projects/{project_id}/files/{file_id}/{safe_name}"

    try:
        signed = supabase.create_signed_upload_url(
            access_token=user.access_token,
            bucket=settings.storage_bucket,
            object_key=storage_path,
            expires_in=300,
        )
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="upload-url generation", exc=exc)

    return UploadUrlResponse(
        upload_url=str(signed["upload_url"]),
        file_id=file_id,
        storage_bucket=settings.storage_bucket,
        storage_path=storage_path,
        expires_at=str(signed["expires_at"]),
    )


@router.post("", response_model=ProjectFileResponse)
def complete_upload(
    project_id: UUID,
    req: FileCompleteRequest,
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
    settings: Settings = Depends(get_settings),
) -> ProjectFileResponse:
    _ensure_project_access(supabase=supabase, user=user, project_id=project_id)

    storage_path = (req.storage_path or req.storage_key or "").strip()
    if not storage_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="missing storage_path")
    expected_prefix = f"projects/{project_id}/files/{req.file_id}/"
    if not storage_path.startswith(expected_prefix):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden storage path for project/file",
        )

    normalized_kind = _normalize_file_kind(file_kind=req.file_kind, file_type=req.file_type)
    storage_bucket = settings.storage_bucket.strip()
    if not storage_bucket:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="invalid storage bucket config")
    try:
        canonical_file_name = canonical_file_name_from_storage_path(storage_path)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    try:
        ingest_metadata = load_file_ingest_metadata(
            supabase=supabase,
            access_token=user.access_token,
            storage_bucket=storage_bucket,
            storage_path=storage_path,
            signed_url_ttl_s=settings.signed_url_ttl_s,
        )
    except (SupabaseHTTPError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="metadata extraction failed") from exc

    source_hash_sha256 = str(ingest_metadata.sha256 or "").strip()
    if not source_hash_sha256:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="metadata extraction failed: missing sha256")

    if req.replaces_file_object_id is not None:
        _validate_replacement_target(
            supabase=supabase,
            user=user,
            project_id=project_id,
            replaces_file_object_id=req.replaces_file_object_id,
        )

    payload = {
        "id": str(req.file_id),
        "project_id": str(project_id),
        "storage_bucket": storage_bucket,
        "storage_path": storage_path,
        "file_name": _sanitize_filename(canonical_file_name),
        "mime_type": ingest_metadata.mime_type,
        "file_kind": normalized_kind,
        "byte_size": ingest_metadata.byte_size,
        "sha256": source_hash_sha256,
        "uploaded_by": user.id,
    }
    if req.replaces_file_object_id is not None:
        payload["replaces_file_object_id"] = str(req.replaces_file_object_id)

    try:
        row = supabase.insert_row(table="app.file_objects", access_token=user.access_token, payload=payload)
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="file metadata insert", exc=exc)

    rules_profile_snapshot = _coerce_rules_profile_snapshot(req.rules_profile_snapshot_jsonb)

    if normalized_kind == "source_dxf" and ingest_metadata.file_name.lower().endswith(".dxf"):
        # Legacy, file-level DXF readability check kept as a secondary signal.
        background_tasks.add_task(
            validate_dxf_file_async,
            supabase=supabase,
            access_token=user.access_token,
            bucket=storage_bucket,
            file_object_id=str(req.file_id),
            storage_path=storage_path,
        )
        background_tasks.add_task(
            run_preflight_for_upload,
            supabase=supabase,
            access_token=user.access_token,
            project_id=str(project_id),
            source_file_object_id=str(req.file_id),
            storage_bucket=storage_bucket,
            storage_path=storage_path,
            source_hash_sha256=source_hash_sha256,
            created_by=user.id,
            signed_url_ttl_s=settings.signed_url_ttl_s,
            rules_profile=rules_profile_snapshot,
        )

    return _as_file_response(row)


@router.get("", response_model=ProjectFileListResponse)
def list_project_files(
    project_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    include_preflight_summary: bool = Query(default=False),
    include_preflight_diagnostics: bool = Query(default=False),
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> ProjectFileListResponse:
    _ensure_project_access(supabase=supabase, user=user, project_id=project_id)
    include_preflight_summary_flag = include_preflight_summary if isinstance(include_preflight_summary, bool) else False
    include_preflight_diagnostics_flag = (
        include_preflight_diagnostics if isinstance(include_preflight_diagnostics, bool) else False
    )

    offset = (page - 1) * page_size
    params = {
        "select": "id,project_id,storage_bucket,storage_path,file_name,mime_type,file_kind,byte_size,sha256,uploaded_by,created_at",
        "project_id": f"eq.{project_id}",
        "order": "created_at.desc",
        "limit": str(page_size),
        "offset": str(offset),
    }
    try:
        rows = supabase.select_rows(table="app.file_objects", access_token=user.access_token, params=params)
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="list files", exc=exc)

    latest_preflight_row_by_file_id: dict[str, dict[str, Any]] = {}
    if include_preflight_summary_flag or include_preflight_diagnostics_flag:
        file_ids = [str(row.get("id", "")).strip() for row in rows if str(row.get("id", "")).strip()]
        try:
            latest_preflight_row_by_file_id = _fetch_latest_preflight_row_by_file_id(
                supabase=supabase,
                access_token=user.access_token,
                file_ids=file_ids,
            )
        except SupabaseHTTPError as exc:
            raise_supabase_http_error(operation="list file latest preflight projection", exc=exc)

    items: list[ProjectFileResponse] = []
    for row in rows:
        file_id = str(row.get("id", "")).strip()
        latest_row = latest_preflight_row_by_file_id.get(file_id)
        items.append(
            _as_file_response(
                row,
                latest_preflight_summary=(
                    _latest_preflight_summary_from_row(latest_row) if include_preflight_summary_flag and latest_row else None
                ),
                latest_preflight_diagnostics=(
                    _latest_preflight_diagnostics_from_row(latest_row)
                    if include_preflight_diagnostics_flag and latest_row
                    else None
                ),
            )
        )

    return ProjectFileListResponse(items=items, total=len(items), page=page, page_size=page_size)


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_project_file(
    project_id: UUID,
    file_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
    settings: Settings = Depends(get_settings),
) -> Response:
    _ensure_project_access(supabase=supabase, user=user, project_id=project_id)

    params = {
        "select": "id,storage_bucket,storage_path",
        "id": f"eq.{file_id}",
        "project_id": f"eq.{project_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.file_objects", access_token=user.access_token, params=params)
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="file not found")

    storage_path = str(rows[0].get("storage_path", "")).strip()
    storage_bucket = str(rows[0].get("storage_bucket", "")).strip() or settings.storage_bucket

    try:
        supabase.delete_rows(
            table="app.file_objects",
            access_token=user.access_token,
            filters={"id": f"eq.{file_id}", "project_id": f"eq.{project_id}"},
        )
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="delete file metadata", exc=exc)

    if storage_path:
        try:
            supabase.remove_object(
                access_token=user.access_token,
                bucket=storage_bucket,
                object_key=storage_path,
            )
        except SupabaseHTTPError:
            return Response(status_code=status.HTTP_204_NO_CONTENT)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{file_id}/replace", response_model=FileReplaceResponse)
def replace_file(
    project_id: UUID,
    file_id: UUID,
    req: FileReplaceRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
    settings: Settings = Depends(get_settings),
) -> FileReplaceResponse:
    _ensure_project_access(supabase=supabase, user=user, project_id=project_id)
    _validate_replacement_target(
        supabase=supabase,
        user=user,
        project_id=project_id,
        replaces_file_object_id=file_id,
    )

    if settings.max_dxf_size_bytes > 0 and req.size_bytes > settings.max_dxf_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"file too large: max={settings.max_dxf_size_bytes} bytes",
        )

    safe_name = _sanitize_filename(req.filename)
    if not safe_name.lower().endswith(".dxf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="replacement DXF file must have .dxf extension")

    new_file_id = str(uuid4())
    storage_path = f"projects/{project_id}/files/{new_file_id}/{safe_name}"

    try:
        signed = supabase.create_signed_upload_url(
            access_token=user.access_token,
            bucket=settings.storage_bucket,
            object_key=storage_path,
            expires_in=300,
        )
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="replacement upload-url generation", exc=exc)

    return FileReplaceResponse(
        upload_url=str(signed["upload_url"]),
        file_id=new_file_id,
        storage_bucket=settings.storage_bucket,
        storage_path=storage_path,
        expires_at=str(signed["expires_at"]),
        replaces_file_id=str(file_id),
    )
