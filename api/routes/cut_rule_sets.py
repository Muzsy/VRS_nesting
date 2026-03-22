from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from api.auth import AuthenticatedUser, get_current_user
from api.deps import get_supabase_client
from api.http_errors import raise_supabase_http_error
from api.request_models import StrictRequestModel
from api.services.cut_rule_sets import (
    CutRuleSetError,
    create_cut_rule_set,
    delete_cut_rule_set,
    get_cut_rule_set,
    list_cut_rule_sets,
    update_cut_rule_set,
)
from api.supabase_client import SupabaseClient, SupabaseHTTPError


router = APIRouter(prefix="/cut-rule-sets", tags=["cut-rule-sets"])


class CutRuleSetCreateRequest(StrictRequestModel):
    name: str
    machine_code: str | None = None
    material_code: str | None = None
    thickness_mm: float | None = None
    is_active: bool = True
    notes: str | None = None
    metadata_jsonb: dict[str, Any] | None = None


class CutRuleSetUpdateRequest(StrictRequestModel):
    is_active: bool | None = None
    notes: str | None = None
    machine_code: str | None = None
    material_code: str | None = None
    thickness_mm: float | None = None
    metadata_jsonb: dict[str, Any] | None = None


class CutRuleSetResponse(BaseModel):
    id: str
    owner_user_id: str
    name: str
    machine_code: str | None = None
    material_code: str | None = None
    thickness_mm: float | None = None
    version_no: int
    is_active: bool
    notes: str | None = None
    metadata_jsonb: dict[str, Any] | None = None
    created_at: str | None = None
    updated_at: str | None = None


def _as_response(row: dict[str, Any]) -> CutRuleSetResponse:
    return CutRuleSetResponse(
        id=str(row.get("id") or ""),
        owner_user_id=str(row.get("owner_user_id") or ""),
        name=str(row.get("name") or ""),
        machine_code=row.get("machine_code"),
        material_code=row.get("material_code"),
        thickness_mm=float(row["thickness_mm"]) if row.get("thickness_mm") is not None else None,
        version_no=int(row.get("version_no") or 1),
        is_active=bool(row.get("is_active", True)),
        notes=row.get("notes"),
        metadata_jsonb=row.get("metadata_jsonb"),
        created_at=str(row.get("created_at") or ""),
        updated_at=str(row.get("updated_at") or ""),
    )


@router.post("", response_model=CutRuleSetResponse, status_code=status.HTTP_201_CREATED)
def post_cut_rule_set(
    req: CutRuleSetCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> CutRuleSetResponse:
    try:
        result = create_cut_rule_set(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            name=req.name,
            machine_code=req.machine_code,
            material_code=req.material_code,
            thickness_mm=req.thickness_mm,
            is_active=req.is_active,
            notes=req.notes,
            metadata_jsonb=req.metadata_jsonb,
        )
    except CutRuleSetError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="create cut rule set", exc=exc)
    return _as_response(result)


@router.get("", response_model=list[CutRuleSetResponse])
def get_cut_rule_sets(
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> list[CutRuleSetResponse]:
    try:
        rows = list_cut_rule_sets(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
        )
    except CutRuleSetError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="list cut rule sets", exc=exc)
    return [_as_response(row) for row in rows]


@router.get("/{cut_rule_set_id}", response_model=CutRuleSetResponse)
def get_cut_rule_set_by_id(
    cut_rule_set_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> CutRuleSetResponse:
    try:
        result = get_cut_rule_set(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            cut_rule_set_id=str(cut_rule_set_id),
        )
    except CutRuleSetError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="get cut rule set", exc=exc)
    return _as_response(result)


@router.patch("/{cut_rule_set_id}", response_model=CutRuleSetResponse)
def patch_cut_rule_set(
    cut_rule_set_id: UUID,
    req: CutRuleSetUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> CutRuleSetResponse:
    updates = req.model_dump(exclude_unset=True)
    try:
        result = update_cut_rule_set(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            cut_rule_set_id=str(cut_rule_set_id),
            updates=updates,
        )
    except CutRuleSetError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="update cut rule set", exc=exc)
    return _as_response(result)


@router.delete("/{cut_rule_set_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_cut_rule_set_by_id(
    cut_rule_set_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> Response:
    try:
        delete_cut_rule_set(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            cut_rule_set_id=str(cut_rule_set_id),
        )
    except CutRuleSetError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="delete cut rule set", exc=exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
