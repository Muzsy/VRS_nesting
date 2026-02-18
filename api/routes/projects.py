from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from api.auth import AuthenticatedUser, get_current_user
from api.deps import get_supabase_client
from api.supabase_client import SupabaseClient, SupabaseHTTPError


router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)


class ProjectResponse(BaseModel):
    id: str
    owner_id: str
    name: str
    description: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    archived_at: str | None = None


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
    page: int
    page_size: int


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_project_response(payload: dict[str, Any]) -> ProjectResponse:
    return ProjectResponse(
        id=str(payload.get("id", "")),
        owner_id=str(payload.get("owner_id", "")),
        name=str(payload.get("name", "")),
        description=payload.get("description"),
        created_at=payload.get("created_at"),
        updated_at=payload.get("updated_at"),
        archived_at=payload.get("archived_at"),
    )


@router.post("", response_model=ProjectResponse)
def create_project(
    req: ProjectCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> ProjectResponse:
    payload = {
        "owner_id": user.id,
        "name": req.name.strip(),
        "description": req.description.strip() or None,
    }
    try:
        row = supabase.insert_row(table="projects", access_token=user.access_token, payload=payload)
    except SupabaseHTTPError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"create project failed: {exc}") from exc
    return _to_project_response(row)


@router.get("", response_model=ProjectListResponse)
def list_projects(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    archived: bool = Query(default=False),
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> ProjectListResponse:
    offset = (page - 1) * page_size
    params = {
        "select": "id,owner_id,name,description,created_at,updated_at,archived_at",
        "owner_id": f"eq.{user.id}",
        "order": "updated_at.desc.nullslast,created_at.desc",
        "limit": str(page_size),
        "offset": str(offset),
    }
    params["archived_at"] = "not.is.null" if archived else "is.null"

    try:
        rows = supabase.select_rows(table="projects", access_token=user.access_token, params=params)
    except SupabaseHTTPError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"list projects failed: {exc}") from exc

    items = [_to_project_response(row) for row in rows]
    return ProjectListResponse(items=items, total=len(items), page=page, page_size=page_size)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> ProjectResponse:
    params = {
        "select": "id,owner_id,name,description,created_at,updated_at,archived_at",
        "id": f"eq.{project_id}",
        "owner_id": f"eq.{user.id}",
        "limit": "1",
    }
    try:
        rows = supabase.select_rows(table="projects", access_token=user.access_token, params=params)
    except SupabaseHTTPError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"get project failed: {exc}") from exc

    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return _to_project_response(rows[0])


@router.patch("/{project_id}", response_model=ProjectResponse)
def patch_project(
    project_id: str,
    req: ProjectUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> ProjectResponse:
    payload: dict[str, Any] = {"updated_at": _now_iso()}
    if req.name is not None:
        payload["name"] = req.name.strip()
    if req.description is not None:
        payload["description"] = req.description.strip() or None

    try:
        rows = supabase.update_rows(
            table="projects",
            access_token=user.access_token,
            payload=payload,
            filters={"id": f"eq.{project_id}", "owner_id": f"eq.{user.id}"},
        )
    except SupabaseHTTPError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"patch project failed: {exc}") from exc

    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return _to_project_response(rows[0])


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def archive_project(
    project_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> Response:
    payload = {"archived_at": _now_iso(), "updated_at": _now_iso()}
    try:
        rows = supabase.update_rows(
            table="projects",
            access_token=user.access_token,
            payload=payload,
            filters={"id": f"eq.{project_id}", "owner_id": f"eq.{user.id}"},
        )
    except SupabaseHTTPError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"archive project failed: {exc}") from exc

    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
