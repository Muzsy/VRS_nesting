from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.auth import AuthenticatedUser, get_current_user
from api.deps import get_supabase_client
from api.http_errors import raise_supabase_http_error
from api.request_models import StrictRequestModel
from api.services.project_part_requirements import (
    ProjectPartRequirementError,
    create_or_update_project_part_requirement,
    list_project_part_requirements,
)
from api.supabase_client import SupabaseClient, SupabaseHTTPError


router = APIRouter(prefix="/projects/{project_id}/part-requirements", tags=["project-part-requirements"])


class ProjectPartRequirementUpsertRequest(StrictRequestModel):
    part_revision_id: UUID
    required_qty: int = Field(gt=0, le=1000000)
    placement_priority: int = Field(default=50, ge=0, le=100)
    placement_policy: str = Field(default="normal", min_length=1, max_length=40)
    is_active: bool = True
    notes: str | None = Field(default=None, max_length=2000)


class ProjectPartRequirementUpsertResponse(BaseModel):
    project_part_requirement_id: str
    project_id: str
    part_revision_id: str
    required_qty: int
    placement_priority: int
    placement_policy: str
    is_active: bool
    notes: str | None = None
    was_existing_requirement: bool


class ProjectPartRequirementListItem(BaseModel):
    project_part_requirement_id: str
    part_revision_id: str
    source_file_object_id: str | None = None
    required_qty: int
    placement_priority: int
    placement_policy: str
    is_active: bool
    notes: str | None = None


class ProjectPartRequirementListResponse(BaseModel):
    items: list[ProjectPartRequirementListItem]
    total: int


def _as_upsert_response(result: dict[str, Any]) -> ProjectPartRequirementUpsertResponse:
    row = result.get("project_part_requirement")
    if not isinstance(row, dict):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="project part requirement upsert returned invalid payload")

    project_part_requirement_id = str(row.get("id") or "").strip()
    project_id = str(row.get("project_id") or "").strip()
    part_revision_id = str(row.get("part_revision_id") or "").strip()
    if not project_part_requirement_id or not project_id or not part_revision_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="project part requirement upsert returned empty ids")

    try:
        required_qty = int(row.get("required_qty"))
        placement_priority = int(row.get("placement_priority"))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="project part requirement upsert returned invalid numeric fields",
        ) from exc

    placement_policy = str(row.get("placement_policy") or "").strip()
    if not placement_policy:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="project part requirement upsert returned empty placement_policy")

    return ProjectPartRequirementUpsertResponse(
        project_part_requirement_id=project_part_requirement_id,
        project_id=project_id,
        part_revision_id=part_revision_id,
        required_qty=required_qty,
        placement_priority=placement_priority,
        placement_policy=placement_policy,
        is_active=bool(row.get("is_active")),
        notes=(str(row.get("notes")).strip() if row.get("notes") is not None else None),
        was_existing_requirement=bool(result.get("was_existing_requirement")),
    )


def _as_list_response(result: dict[str, Any]) -> ProjectPartRequirementListResponse:
    rows = result.get("items")
    if not isinstance(rows, list):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="project part requirement list returned invalid payload")

    items: list[ProjectPartRequirementListItem] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        requirement_id = str(row.get("id") or "").strip()
        revision_id = str(row.get("part_revision_id") or "").strip()
        if not requirement_id or not revision_id:
            continue
        try:
            required_qty = int(row.get("required_qty"))
            placement_priority = int(row.get("placement_priority"))
        except (TypeError, ValueError):
            continue
        placement_policy = str(row.get("placement_policy") or "").strip()
        if not placement_policy:
            continue
        items.append(
            ProjectPartRequirementListItem(
                project_part_requirement_id=requirement_id,
                part_revision_id=revision_id,
                source_file_object_id=(str(row.get("source_file_object_id")).strip() if row.get("source_file_object_id") is not None else None),
                required_qty=required_qty,
                placement_priority=placement_priority,
                placement_policy=placement_policy,
                is_active=bool(row.get("is_active")),
                notes=(str(row.get("notes")).strip() if row.get("notes") is not None else None),
            )
        )
    return ProjectPartRequirementListResponse(items=items, total=len(items))


@router.post("", response_model=ProjectPartRequirementUpsertResponse, status_code=status.HTTP_201_CREATED)
def upsert_project_part_requirement(
    project_id: UUID,
    req: ProjectPartRequirementUpsertRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> ProjectPartRequirementUpsertResponse:
    try:
        result = create_or_update_project_part_requirement(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            project_id=str(project_id),
            part_revision_id=str(req.part_revision_id),
            raw_required_qty=req.required_qty,
            raw_placement_priority=req.placement_priority,
            raw_placement_policy=req.placement_policy,
            raw_is_active=req.is_active,
            raw_notes=req.notes,
        )
    except ProjectPartRequirementError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="project part requirement upsert", exc=exc)
    return _as_upsert_response(result)


@router.get("", response_model=ProjectPartRequirementListResponse)
def get_project_part_requirements(
    project_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> ProjectPartRequirementListResponse:
    try:
        result = list_project_part_requirements(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            project_id=str(project_id),
        )
    except ProjectPartRequirementError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="project part requirement list", exc=exc)
    return _as_list_response(result)
