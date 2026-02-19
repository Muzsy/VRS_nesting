from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from api.auth import AuthenticatedUser, get_current_user
from api.config import Settings
from api.deps import get_settings, get_supabase_client
from api.rate_limit import enforce_user_rate_limit
from api.services.dxf_validation import validate_dxf_file_async
from api.supabase_client import SupabaseClient, SupabaseHTTPError


router = APIRouter(prefix="/projects/{project_id}/files", tags=["project-files"])


class UploadUrlRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=260)
    content_type: str | None = Field(default="application/dxf", max_length=100)
    size_bytes: int = Field(gt=0)
    file_type: str = Field(min_length=1, max_length=40)


class UploadUrlResponse(BaseModel):
    upload_url: str
    file_id: str
    storage_key: str
    expires_at: str


class FileCompleteRequest(BaseModel):
    file_id: str = Field(min_length=1)
    original_filename: str = Field(min_length=1, max_length=260)
    storage_key: str = Field(min_length=1)
    file_type: str = Field(min_length=1, max_length=40)
    size_bytes: int = Field(gt=0)
    content_hash_sha256: str | None = Field(default=None, max_length=128)


class ProjectFileResponse(BaseModel):
    id: str
    project_id: str
    uploaded_by: str
    file_type: str
    original_filename: str
    storage_key: str
    size_bytes: int | None = None
    validation_status: str | None = None
    validation_error: str | None = None
    uploaded_at: str | None = None


class ProjectFileListResponse(BaseModel):
    items: list[ProjectFileResponse]
    total: int


def _as_file_response(row: dict[str, Any]) -> ProjectFileResponse:
    return ProjectFileResponse(
        id=str(row.get("id", "")),
        project_id=str(row.get("project_id", "")),
        uploaded_by=str(row.get("uploaded_by", "")),
        file_type=str(row.get("file_type", "")),
        original_filename=str(row.get("original_filename", "")),
        storage_key=str(row.get("storage_key", "")),
        size_bytes=row.get("size_bytes"),
        validation_status=row.get("validation_status"),
        validation_error=row.get("validation_error"),
        uploaded_at=row.get("uploaded_at"),
    )


def _sanitize_filename(raw_filename: str) -> str:
    safe_name = Path(raw_filename).name.strip()
    if not safe_name or safe_name in {".", ".."}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid filename")
    if "/" in safe_name or "\\" in safe_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid filename")
    return safe_name


def _ensure_project_access(
    *,
    supabase: SupabaseClient,
    user: AuthenticatedUser,
    project_id: str,
) -> None:
    params = {
        "select": "id",
        "id": f"eq.{project_id}",
        "owner_id": f"eq.{user.id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="projects", access_token=user.access_token, params=params)
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")


@router.post("/upload-url", response_model=UploadUrlResponse)
def create_upload_url(
    project_id: str,
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
        table="project_files",
        timestamp_field="uploaded_at",
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

    if not safe_name.lower().endswith(".dxf") and req.file_type in {"stock_dxf", "part_dxf"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="DXF file must have .dxf extension")

    file_id = str(uuid4())
    storage_key = f"users/{user.id}/projects/{project_id}/files/{file_id}/{safe_name}"

    try:
        signed = supabase.create_signed_upload_url(
            access_token=user.access_token,
            bucket=settings.storage_bucket,
            object_key=storage_key,
            expires_in=300,
        )
    except SupabaseHTTPError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"upload-url generation failed: {exc}") from exc

    return UploadUrlResponse(
        upload_url=str(signed["upload_url"]),
        file_id=file_id,
        storage_key=storage_key,
        expires_at=str(signed["expires_at"]),
    )


@router.post("", response_model=ProjectFileResponse)
def complete_upload(
    project_id: str,
    req: FileCompleteRequest,
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
    settings: Settings = Depends(get_settings),
) -> ProjectFileResponse:
    _ensure_project_access(supabase=supabase, user=user, project_id=project_id)

    expected_prefix = f"users/{user.id}/projects/{project_id}/files/{req.file_id}/"
    if not req.storage_key.startswith(expected_prefix):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden storage key for caller/project",
        )

    payload = {
        "id": req.file_id,
        "project_id": project_id,
        "uploaded_by": user.id,
        "file_type": req.file_type,
        "original_filename": _sanitize_filename(req.original_filename),
        "storage_key": req.storage_key,
        "size_bytes": req.size_bytes,
        "content_hash_sha256": req.content_hash_sha256,
        "validation_status": "pending",
        "validation_error": None,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        row = supabase.insert_row(table="project_files", access_token=user.access_token, payload=payload)
    except SupabaseHTTPError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"file metadata insert failed: {exc}") from exc

    if payload["original_filename"].lower().endswith(".dxf"):
        background_tasks.add_task(
            validate_dxf_file_async,
            supabase=supabase,
            access_token=user.access_token,
            bucket=settings.storage_bucket,
            project_file_id=req.file_id,
            storage_key=req.storage_key,
        )

    return _as_file_response(row)


@router.get("", response_model=ProjectFileListResponse)
def list_project_files(
    project_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> ProjectFileListResponse:
    _ensure_project_access(supabase=supabase, user=user, project_id=project_id)

    params = {
        "select": "id,project_id,uploaded_by,file_type,original_filename,storage_key,size_bytes,validation_status,validation_error,uploaded_at",
        "project_id": f"eq.{project_id}",
        "order": "uploaded_at.desc",
    }
    try:
        rows = supabase.select_rows(table="project_files", access_token=user.access_token, params=params)
    except SupabaseHTTPError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"list files failed: {exc}") from exc

    items = [_as_file_response(row) for row in rows]
    return ProjectFileListResponse(items=items, total=len(items))


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_project_file(
    project_id: str,
    file_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
    settings: Settings = Depends(get_settings),
) -> Response:
    _ensure_project_access(supabase=supabase, user=user, project_id=project_id)

    params = {
        "select": "id,storage_key",
        "id": f"eq.{file_id}",
        "project_id": f"eq.{project_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="project_files", access_token=user.access_token, params=params)
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="file not found")

    storage_key = str(rows[0].get("storage_key", "")).strip()

    try:
        supabase.delete_rows(
            table="project_files",
            access_token=user.access_token,
            filters={"id": f"eq.{file_id}", "project_id": f"eq.{project_id}"},
        )
    except SupabaseHTTPError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"delete file metadata failed: {exc}") from exc

    if storage_key:
        try:
            supabase.remove_object(
                access_token=user.access_token,
                bucket=settings.storage_bucket,
                object_key=storage_key,
            )
        except SupabaseHTTPError:
            return Response(status_code=status.HTTP_204_NO_CONTENT)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
