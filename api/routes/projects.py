from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from api.auth import AuthenticatedUser, get_current_user
from api.deps import get_supabase_client
from api.http_errors import raise_supabase_http_error
from api.request_models import StrictRequestModel
from api.supabase_client import SupabaseClient, SupabaseHTTPError

logger = logging.getLogger("vrs_api.projects")


router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreateRequest(StrictRequestModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)


class ProjectUpdateRequest(StrictRequestModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)


class ProjectResponse(BaseModel):
    id: str
    owner_user_id: str
    lifecycle: str
    name: str
    description: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
    page: int
    page_size: int


def _default_technology_setup_payload(project_id: str) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "display_name": "Default Setup",
        "lifecycle": "approved",
        "is_default": False,
        "machine_code": "DEFAULT",
        "material_code": "DEFAULT",
        "thickness_mm": 3.0,
        "kerf_mm": 0.2,
        "spacing_mm": 0.0,
        "margin_mm": 0.0,
        "rotation_step_deg": 90,
        "allow_free_rotation": False,
    }


def _to_project_response(payload: dict[str, Any]) -> ProjectResponse:
    return ProjectResponse(
        id=str(payload.get("id", "")),
        owner_user_id=str(payload.get("owner_user_id", "")),
        lifecycle=str(payload.get("lifecycle", "")),
        name=str(payload.get("name", "")),
        description=payload.get("description"),
        created_at=payload.get("created_at"),
        updated_at=payload.get("updated_at"),
    )


@router.post("", response_model=ProjectResponse)
def create_project(
    req: ProjectCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> ProjectResponse:
    payload = {
        "owner_user_id": user.id,
        "name": req.name.strip(),
        "description": req.description.strip() or None,
    }
    try:
        row = supabase.insert_row(table="app.projects", access_token=user.access_token, payload=payload)
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="create project", exc=exc)
    project_id = str(row.get("id", "")).strip()
    if project_id:
        try:
            supabase.insert_row(
                table="app.project_technology_setups",
                access_token=user.access_token,
                payload=_default_technology_setup_payload(project_id),
            )
        except Exception:
            logger.warning("create_project_default_technology_setup_failed project_id=%s", project_id)
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
        "select": "id,owner_user_id,lifecycle,name,description,created_at,updated_at",
        "owner_user_id": f"eq.{user.id}",
        "order": "updated_at.desc.nullslast,created_at.desc",
        "limit": str(page_size),
        "offset": str(offset),
    }
    params["lifecycle"] = "eq.archived" if archived else "neq.archived"

    try:
        rows = supabase.select_rows(table="app.projects", access_token=user.access_token, params=params)
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="list projects", exc=exc)

    items = [_to_project_response(row) for row in rows]
    return ProjectListResponse(items=items, total=len(items), page=page, page_size=page_size)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> ProjectResponse:
    params = {
        "select": "id,owner_user_id,lifecycle,name,description,created_at,updated_at",
        "id": f"eq.{project_id}",
        "owner_user_id": f"eq.{user.id}",
        "limit": "1",
    }
    try:
        rows = supabase.select_rows(table="app.projects", access_token=user.access_token, params=params)
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="get project", exc=exc)

    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return _to_project_response(rows[0])


@router.patch("/{project_id}", response_model=ProjectResponse)
def patch_project(
    project_id: UUID,
    req: ProjectUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> ProjectResponse:
    payload: dict[str, Any] = {}
    if req.name is not None:
        payload["name"] = req.name.strip()
    if req.description is not None:
        payload["description"] = req.description.strip() or None

    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="no fields to update")

    try:
        rows = supabase.update_rows(
            table="app.projects",
            access_token=user.access_token,
            payload=payload,
            filters={"id": f"eq.{project_id}", "owner_user_id": f"eq.{user.id}"},
        )
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="patch project", exc=exc)

    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return _to_project_response(rows[0])


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def archive_project(
    project_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> Response:
    payload = {"lifecycle": "archived"}
    try:
        rows = supabase.update_rows(
            table="app.projects",
            access_token=user.access_token,
            payload=payload,
            filters={"id": f"eq.{project_id}", "owner_user_id": f"eq.{user.id}"},
        )
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="archive project", exc=exc)

    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
