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


class ProjectFileListResponse(BaseModel):
    items: list[ProjectFileResponse]
    total: int
    page: int
    page_size: int


def _as_file_response(
    row: dict[str, Any],
    *,
    latest_preflight_summary: dict[str, Any] | None = None,
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
    )


def _latest_preflight_summary_from_row(row: dict[str, Any]) -> dict[str, Any]:
    run_seq = row.get("run_seq")
    run_seq_value = int(run_seq) if isinstance(run_seq, int) and not isinstance(run_seq, bool) else None
    return {
        "preflight_run_id": str(row.get("id", "")),
        "run_seq": run_seq_value,
        "run_status": str(row.get("run_status", "")),
        "acceptance_outcome": row.get("acceptance_outcome"),
        "finished_at": row.get("finished_at"),
    }


def _fetch_latest_preflight_summary_by_file_id(
    *,
    supabase: SupabaseClient,
    access_token: str,
    file_ids: list[str],
) -> dict[str, dict[str, Any]]:
    if not file_ids:
        return {}

    in_values = ",".join(file_ids)
    params = {
        "select": "id,source_file_object_id,run_seq,run_status,acceptance_outcome,finished_at",
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
        latest_by_file_id[source_file_object_id] = _latest_preflight_summary_from_row(row)
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
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> ProjectFileListResponse:
    _ensure_project_access(supabase=supabase, user=user, project_id=project_id)

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

    latest_summary_by_file_id: dict[str, dict[str, Any]] = {}
    if include_preflight_summary:
        file_ids = [str(row.get("id", "")).strip() for row in rows if str(row.get("id", "")).strip()]
        try:
            latest_summary_by_file_id = _fetch_latest_preflight_summary_by_file_id(
                supabase=supabase,
                access_token=user.access_token,
                file_ids=file_ids,
            )
        except SupabaseHTTPError as exc:
            raise_supabase_http_error(operation="list file preflight summary", exc=exc)

    items = [
        _as_file_response(
            row,
            latest_preflight_summary=latest_summary_by_file_id.get(str(row.get("id", "")).strip()),
        )
        for row in rows
    ]
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
