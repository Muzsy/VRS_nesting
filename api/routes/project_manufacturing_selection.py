from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from api.auth import AuthenticatedUser, get_current_user
from api.deps import get_supabase_client
from api.http_errors import raise_supabase_http_error
from api.request_models import StrictRequestModel
from api.services.project_manufacturing_selection import (
    ProjectManufacturingSelectionError,
    delete_project_manufacturing_selection,
    get_project_manufacturing_selection,
    set_project_manufacturing_selection,
)
from api.supabase_client import SupabaseClient, SupabaseHTTPError


router = APIRouter(prefix="/projects/{project_id}/manufacturing-selection", tags=["project-manufacturing-selection"])


class ProjectManufacturingSelectionUpsertRequest(StrictRequestModel):
    active_manufacturing_profile_version_id: UUID


class ProjectManufacturingSelectionResponse(BaseModel):
    project_id: str
    active_manufacturing_profile_version_id: str
    selected_at: str | None = None
    selected_by: str
    manufacturing_profile_id: str | None = None
    version_no: int | None = None
    profile_name: str | None = None
    was_existing_selection: bool | None = None


def _as_selection_response(result: dict[str, Any], *, include_existing_flag: bool) -> ProjectManufacturingSelectionResponse:
    selection = result.get("selection")
    if not isinstance(selection, dict):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="project manufacturing selection returned invalid payload")

    version = result.get("manufacturing_profile_version")
    if version is not None and not isinstance(version, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="project manufacturing selection returned invalid version payload",
        )

    profile = result.get("manufacturing_profile")
    if profile is not None and not isinstance(profile, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="project manufacturing selection returned invalid profile payload",
        )

    project_id = str(selection.get("project_id") or "").strip()
    version_id = str(selection.get("active_manufacturing_profile_version_id") or "").strip()
    selected_by = str(selection.get("selected_by") or "").strip()
    if not project_id or not version_id or not selected_by:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="project manufacturing selection returned empty ids",
        )

    version_no: int | None = None
    if version is not None and version.get("version_no") is not None:
        try:
            version_no = int(version.get("version_no"))
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="project manufacturing selection returned invalid version_no",
            ) from exc

    was_existing_selection: bool | None = None
    if include_existing_flag:
        was_existing_selection = bool(result.get("was_existing_selection"))

    return ProjectManufacturingSelectionResponse(
        project_id=project_id,
        active_manufacturing_profile_version_id=version_id,
        selected_at=(str(selection.get("selected_at") or "").strip() or None),
        selected_by=selected_by,
        manufacturing_profile_id=(
            str(version.get("manufacturing_profile_id") or "").strip()
            if isinstance(version, dict)
            else None
        )
        or None,
        version_no=version_no,
        profile_name=(str(profile.get("profile_name") or "").strip() if isinstance(profile, dict) else None) or None,
        was_existing_selection=was_existing_selection,
    )


@router.put("", response_model=ProjectManufacturingSelectionResponse)
def put_project_manufacturing_selection(
    project_id: UUID,
    req: ProjectManufacturingSelectionUpsertRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> ProjectManufacturingSelectionResponse:
    try:
        result = set_project_manufacturing_selection(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            project_id=str(project_id),
            active_manufacturing_profile_version_id=str(req.active_manufacturing_profile_version_id),
        )
    except ProjectManufacturingSelectionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="set project manufacturing selection", exc=exc)
    return _as_selection_response(result, include_existing_flag=True)


@router.get("", response_model=ProjectManufacturingSelectionResponse)
def read_project_manufacturing_selection(
    project_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> ProjectManufacturingSelectionResponse:
    try:
        result = get_project_manufacturing_selection(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            project_id=str(project_id),
        )
    except ProjectManufacturingSelectionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="get project manufacturing selection", exc=exc)
    return _as_selection_response(result, include_existing_flag=False)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def remove_project_manufacturing_selection(
    project_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> Response:
    try:
        delete_project_manufacturing_selection(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            project_id=str(project_id),
        )
    except ProjectManufacturingSelectionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="delete project manufacturing selection", exc=exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
