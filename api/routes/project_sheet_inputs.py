from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.auth import AuthenticatedUser, get_current_user
from api.deps import get_supabase_client
from api.http_errors import raise_supabase_http_error
from api.request_models import StrictRequestModel
from api.services.project_sheet_inputs import (
    ProjectSheetInputError,
    create_or_update_project_sheet_input,
    list_project_sheet_inputs,
)
from api.supabase_client import SupabaseClient, SupabaseHTTPError


router = APIRouter(prefix="/projects/{project_id}/sheet-inputs", tags=["project-sheet-inputs"])


class ProjectSheetInputUpsertRequest(StrictRequestModel):
    sheet_revision_id: UUID
    required_qty: int = Field(gt=0, le=1000000)
    is_active: bool = True
    is_default: bool = False
    placement_priority: int = Field(default=50, ge=0, le=100)
    notes: str | None = Field(default=None, max_length=2000)


class ProjectSheetInputUpsertResponse(BaseModel):
    project_sheet_input_id: str
    project_id: str
    sheet_revision_id: str
    required_qty: int
    is_active: bool
    is_default: bool
    placement_priority: int
    notes: str | None = None
    was_existing_input: bool


class ProjectSheetInputListItem(BaseModel):
    project_sheet_input_id: str
    sheet_revision_id: str
    required_qty: int
    is_active: bool
    is_default: bool
    placement_priority: int
    notes: str | None = None


class ProjectSheetInputListResponse(BaseModel):
    items: list[ProjectSheetInputListItem]
    total: int


def _as_upsert_response(result: dict[str, Any]) -> ProjectSheetInputUpsertResponse:
    row = result.get("project_sheet_input")
    if not isinstance(row, dict):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="project sheet input upsert returned invalid payload")

    project_sheet_input_id = str(row.get("id") or "").strip()
    project_id = str(row.get("project_id") or "").strip()
    sheet_revision_id = str(row.get("sheet_revision_id") or "").strip()
    if not project_sheet_input_id or not project_id or not sheet_revision_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="project sheet input upsert returned empty ids")

    try:
        required_qty = int(row.get("required_qty"))
        placement_priority = int(row.get("placement_priority"))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="project sheet input upsert returned invalid numeric fields",
        ) from exc

    return ProjectSheetInputUpsertResponse(
        project_sheet_input_id=project_sheet_input_id,
        project_id=project_id,
        sheet_revision_id=sheet_revision_id,
        required_qty=required_qty,
        is_active=bool(row.get("is_active")),
        is_default=bool(row.get("is_default")),
        placement_priority=placement_priority,
        notes=(str(row.get("notes")).strip() if row.get("notes") is not None else None),
        was_existing_input=bool(result.get("was_existing_input")),
    )


def _as_list_response(result: dict[str, Any]) -> ProjectSheetInputListResponse:
    rows = result.get("items")
    if not isinstance(rows, list):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="project sheet input list returned invalid payload")

    items: list[ProjectSheetInputListItem] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        project_sheet_input_id = str(row.get("id") or "").strip()
        sheet_revision_id = str(row.get("sheet_revision_id") or "").strip()
        if not project_sheet_input_id or not sheet_revision_id:
            continue
        try:
            required_qty = int(row.get("required_qty"))
            placement_priority = int(row.get("placement_priority"))
        except (TypeError, ValueError):
            continue
        items.append(
            ProjectSheetInputListItem(
                project_sheet_input_id=project_sheet_input_id,
                sheet_revision_id=sheet_revision_id,
                required_qty=required_qty,
                is_active=bool(row.get("is_active")),
                is_default=bool(row.get("is_default")),
                placement_priority=placement_priority,
                notes=(str(row.get("notes")).strip() if row.get("notes") is not None else None),
            )
        )
    return ProjectSheetInputListResponse(items=items, total=len(items))


@router.post("", response_model=ProjectSheetInputUpsertResponse, status_code=status.HTTP_201_CREATED)
def upsert_project_sheet_input(
    project_id: UUID,
    req: ProjectSheetInputUpsertRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> ProjectSheetInputUpsertResponse:
    try:
        result = create_or_update_project_sheet_input(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            project_id=str(project_id),
            sheet_revision_id=str(req.sheet_revision_id),
            raw_required_qty=req.required_qty,
            raw_is_active=req.is_active,
            raw_is_default=req.is_default,
            raw_placement_priority=req.placement_priority,
            raw_notes=req.notes,
        )
    except ProjectSheetInputError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="project sheet input upsert", exc=exc)
    return _as_upsert_response(result)


@router.get("", response_model=ProjectSheetInputListResponse)
def get_project_sheet_inputs(
    project_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> ProjectSheetInputListResponse:
    try:
        result = list_project_sheet_inputs(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            project_id=str(project_id),
        )
    except ProjectSheetInputError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="project sheet input list", exc=exc)
    return _as_list_response(result)
