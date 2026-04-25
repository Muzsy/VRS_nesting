from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.auth import AuthenticatedUser, get_current_user
from api.deps import get_supabase_client
from api.http_errors import raise_supabase_http_error
from api.request_models import StrictRequestModel
from api.services.part_creation import PartCreationError, create_part_from_geometry_revision
from api.supabase_client import SupabaseClient, SupabaseHTTPError

logger = logging.getLogger("vrs_api.parts")

router = APIRouter(prefix="/projects/{project_id}/parts", tags=["parts"])


class PartCreateRequest(StrictRequestModel):
    code: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=240)
    geometry_revision_id: UUID
    description: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)
    source_label: str | None = Field(default=None, max_length=240)


class PartCreateResponse(BaseModel):
    part_definition_id: str
    part_revision_id: str
    revision_no: int
    lifecycle: str
    code: str
    name: str
    current_revision_id: str | None = None
    source_geometry_revision_id: str
    selected_nesting_derivative_id: str
    was_existing_definition: bool


def _as_create_response(result: dict[str, Any]) -> PartCreateResponse:
    definition = result.get("part_definition")
    revision = result.get("part_revision")
    derivative = result.get("selected_nesting_derivative")
    source_geometry = result.get("source_geometry_revision")

    if not isinstance(definition, dict) or not isinstance(revision, dict):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="part creation returned invalid payload")
    if not isinstance(derivative, dict) or not isinstance(source_geometry, dict):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="part creation returned invalid binding payload")

    part_definition_id = str(definition.get("id") or "").strip()
    part_revision_id = str(revision.get("id") or "").strip()
    source_geometry_revision_id = str(source_geometry.get("id") or "").strip()
    selected_nesting_derivative_id = str(derivative.get("id") or "").strip()
    if not part_definition_id or not part_revision_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="part creation returned empty ids")

    revision_no_raw = revision.get("revision_no")
    try:
        revision_no = int(revision_no_raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="part creation returned invalid revision_no") from exc

    current_revision_id_raw = definition.get("current_revision_id")
    current_revision_id = str(current_revision_id_raw).strip() if current_revision_id_raw is not None else None

    return PartCreateResponse(
        part_definition_id=part_definition_id,
        part_revision_id=part_revision_id,
        revision_no=revision_no,
        lifecycle=str(revision.get("lifecycle") or "draft"),
        code=str(definition.get("code") or ""),
        name=str(definition.get("name") or ""),
        current_revision_id=current_revision_id,
        source_geometry_revision_id=source_geometry_revision_id,
        selected_nesting_derivative_id=selected_nesting_derivative_id,
        was_existing_definition=bool(result.get("was_existing_definition")),
    )


@router.post("", response_model=PartCreateResponse, status_code=status.HTTP_201_CREATED)
def create_part(
    project_id: UUID,
    req: PartCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> PartCreateResponse:
    try:
        result = create_part_from_geometry_revision(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            project_id=str(project_id),
            raw_code=req.code,
            raw_name=req.name,
            geometry_revision_id=str(req.geometry_revision_id),
            raw_description=req.description,
            raw_notes=req.notes,
            raw_source_label=req.source_label,
        )
    except PartCreationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="part creation", exc=exc)

    revision = result.get("part_revision")
    if isinstance(revision, dict):
        part_revision_id = str(revision.get("id") or "").strip()
        if part_revision_id:
            try:
                supabase.insert_row(
                    table="app.project_part_requirements",
                    access_token=user.access_token,
                    payload={
                        "project_id": str(project_id),
                        "part_revision_id": part_revision_id,
                        "required_qty": 1,
                        "placement_priority": 50,
                        "placement_policy": "normal",
                        "is_active": True,
                    },
                )
            except Exception:
                logger.warning(
                    "create_part_auto_requirement_failed project_id=%s part_revision_id=%s",
                    project_id,
                    part_revision_id,
                )

    return _as_create_response(result)
