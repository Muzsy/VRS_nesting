from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.auth import AuthenticatedUser, get_current_user
from api.deps import get_supabase_client
from api.services.sheet_creation import SheetCreationError, create_sheet_revision
from api.supabase_client import SupabaseClient, SupabaseHTTPError


router = APIRouter(prefix="/sheets", tags=["sheets"])


class SheetCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=240)
    width_mm: float = Field(gt=0)
    height_mm: float = Field(gt=0)
    description: str | None = Field(default=None, max_length=2000)
    grain_direction: str | None = Field(default=None, max_length=80)
    notes: str | None = Field(default=None, max_length=2000)
    source_label: str | None = Field(default=None, max_length=240)


class SheetCreateResponse(BaseModel):
    sheet_definition_id: str
    sheet_revision_id: str
    revision_no: int
    lifecycle: str
    code: str
    name: str
    current_revision_id: str | None = None
    width_mm: float
    height_mm: float
    grain_direction: str | None = None
    was_existing_definition: bool


def _as_float(value: Any, *, field: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"sheet creation returned invalid {field}",
        ) from exc
    return parsed


def _as_create_response(result: dict[str, Any]) -> SheetCreateResponse:
    definition = result.get("sheet_definition")
    revision = result.get("sheet_revision")

    if not isinstance(definition, dict) or not isinstance(revision, dict):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="sheet creation returned invalid payload")

    sheet_definition_id = str(definition.get("id") or "").strip()
    sheet_revision_id = str(revision.get("id") or "").strip()
    if not sheet_definition_id or not sheet_revision_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="sheet creation returned empty ids")

    revision_no_raw = revision.get("revision_no")
    try:
        revision_no = int(revision_no_raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="sheet creation returned invalid revision_no") from exc

    current_revision_id_raw = definition.get("current_revision_id")
    current_revision_id = str(current_revision_id_raw).strip() if current_revision_id_raw is not None else None

    return SheetCreateResponse(
        sheet_definition_id=sheet_definition_id,
        sheet_revision_id=sheet_revision_id,
        revision_no=revision_no,
        lifecycle=str(revision.get("lifecycle") or "draft"),
        code=str(definition.get("code") or ""),
        name=str(definition.get("name") or ""),
        current_revision_id=current_revision_id,
        width_mm=_as_float(revision.get("width_mm"), field="width_mm"),
        height_mm=_as_float(revision.get("height_mm"), field="height_mm"),
        grain_direction=(str(revision.get("grain_direction")).strip() if revision.get("grain_direction") is not None else None),
        was_existing_definition=bool(result.get("was_existing_definition")),
    )


@router.post("", response_model=SheetCreateResponse, status_code=status.HTTP_201_CREATED)
def create_sheet(
    req: SheetCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> SheetCreateResponse:
    try:
        result = create_sheet_revision(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            raw_code=req.code,
            raw_name=req.name,
            raw_width_mm=req.width_mm,
            raw_height_mm=req.height_mm,
            raw_description=req.description,
            raw_grain_direction=req.grain_direction,
            raw_notes=req.notes,
            raw_source_label=req.source_label,
        )
    except SheetCreationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"sheet creation failed: {exc}") from exc

    return _as_create_response(result)
