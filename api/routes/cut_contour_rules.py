from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from api.auth import AuthenticatedUser, get_current_user
from api.deps import get_supabase_client
from api.http_errors import raise_supabase_http_error
from api.request_models import StrictRequestModel
from api.services.cut_contour_rules import (
    CutContourRuleError,
    create_cut_contour_rule,
    delete_cut_contour_rule,
    get_cut_contour_rule,
    list_cut_contour_rules,
    update_cut_contour_rule,
)
from api.supabase_client import SupabaseClient, SupabaseHTTPError


router = APIRouter(prefix="/cut-rule-sets/{cut_rule_set_id}/rules", tags=["cut-contour-rules"])


class CutContourRuleCreateRequest(StrictRequestModel):
    contour_kind: str
    feature_class: str = "default"
    lead_in_type: str = "none"
    lead_in_length_mm: float | None = None
    lead_in_radius_mm: float | None = None
    lead_out_type: str = "none"
    lead_out_length_mm: float | None = None
    lead_out_radius_mm: float | None = None
    entry_side_policy: str = "auto"
    min_contour_length_mm: float | None = None
    max_contour_length_mm: float | None = None
    pierce_count: int = 1
    cut_direction: str = "cw"
    sort_order: int = 0
    enabled: bool = True
    metadata_jsonb: dict[str, Any] | None = None


class CutContourRuleUpdateRequest(StrictRequestModel):
    contour_kind: str | None = None
    feature_class: str | None = None
    lead_in_type: str | None = None
    lead_in_length_mm: float | None = None
    lead_in_radius_mm: float | None = None
    lead_out_type: str | None = None
    lead_out_length_mm: float | None = None
    lead_out_radius_mm: float | None = None
    entry_side_policy: str | None = None
    min_contour_length_mm: float | None = None
    max_contour_length_mm: float | None = None
    pierce_count: int | None = None
    cut_direction: str | None = None
    sort_order: int | None = None
    enabled: bool | None = None
    metadata_jsonb: dict[str, Any] | None = None


class CutContourRuleResponse(BaseModel):
    id: str
    cut_rule_set_id: str
    contour_kind: str
    feature_class: str
    lead_in_type: str
    lead_in_length_mm: float | None = None
    lead_in_radius_mm: float | None = None
    lead_out_type: str
    lead_out_length_mm: float | None = None
    lead_out_radius_mm: float | None = None
    entry_side_policy: str
    min_contour_length_mm: float | None = None
    max_contour_length_mm: float | None = None
    pierce_count: int
    cut_direction: str
    sort_order: int
    enabled: bool
    metadata_jsonb: dict[str, Any] | None = None
    created_at: str | None = None
    updated_at: str | None = None


def _as_response(row: dict[str, Any]) -> CutContourRuleResponse:
    return CutContourRuleResponse(
        id=str(row.get("id") or ""),
        cut_rule_set_id=str(row.get("cut_rule_set_id") or ""),
        contour_kind=str(row.get("contour_kind") or ""),
        feature_class=str(row.get("feature_class") or "default"),
        lead_in_type=str(row.get("lead_in_type") or "none"),
        lead_in_length_mm=float(row["lead_in_length_mm"]) if row.get("lead_in_length_mm") is not None else None,
        lead_in_radius_mm=float(row["lead_in_radius_mm"]) if row.get("lead_in_radius_mm") is not None else None,
        lead_out_type=str(row.get("lead_out_type") or "none"),
        lead_out_length_mm=float(row["lead_out_length_mm"]) if row.get("lead_out_length_mm") is not None else None,
        lead_out_radius_mm=float(row["lead_out_radius_mm"]) if row.get("lead_out_radius_mm") is not None else None,
        entry_side_policy=str(row.get("entry_side_policy") or "auto"),
        min_contour_length_mm=float(row["min_contour_length_mm"]) if row.get("min_contour_length_mm") is not None else None,
        max_contour_length_mm=float(row["max_contour_length_mm"]) if row.get("max_contour_length_mm") is not None else None,
        pierce_count=int(row.get("pierce_count") or 1),
        cut_direction=str(row.get("cut_direction") or "cw"),
        sort_order=int(row.get("sort_order") or 0),
        enabled=bool(row.get("enabled", True)),
        metadata_jsonb=row.get("metadata_jsonb"),
        created_at=str(row.get("created_at") or ""),
        updated_at=str(row.get("updated_at") or ""),
    )


@router.post("", response_model=CutContourRuleResponse, status_code=status.HTTP_201_CREATED)
def post_cut_contour_rule(
    cut_rule_set_id: UUID,
    req: CutContourRuleCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> CutContourRuleResponse:
    try:
        result = create_cut_contour_rule(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            cut_rule_set_id=str(cut_rule_set_id),
            contour_kind=req.contour_kind,
            feature_class=req.feature_class,
            lead_in_type=req.lead_in_type,
            lead_in_length_mm=req.lead_in_length_mm,
            lead_in_radius_mm=req.lead_in_radius_mm,
            lead_out_type=req.lead_out_type,
            lead_out_length_mm=req.lead_out_length_mm,
            lead_out_radius_mm=req.lead_out_radius_mm,
            entry_side_policy=req.entry_side_policy,
            min_contour_length_mm=req.min_contour_length_mm,
            max_contour_length_mm=req.max_contour_length_mm,
            pierce_count=req.pierce_count,
            cut_direction=req.cut_direction,
            sort_order=req.sort_order,
            enabled=req.enabled,
            metadata_jsonb=req.metadata_jsonb,
        )
    except CutContourRuleError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="create cut contour rule", exc=exc)
    return _as_response(result)


@router.get("", response_model=list[CutContourRuleResponse])
def get_cut_contour_rules(
    cut_rule_set_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> list[CutContourRuleResponse]:
    try:
        rows = list_cut_contour_rules(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            cut_rule_set_id=str(cut_rule_set_id),
        )
    except CutContourRuleError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="list cut contour rules", exc=exc)
    return [_as_response(row) for row in rows]


@router.get("/{rule_id}", response_model=CutContourRuleResponse)
def get_cut_contour_rule_by_id(
    cut_rule_set_id: UUID,
    rule_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> CutContourRuleResponse:
    try:
        result = get_cut_contour_rule(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            cut_rule_set_id=str(cut_rule_set_id),
            rule_id=str(rule_id),
        )
    except CutContourRuleError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="get cut contour rule", exc=exc)
    return _as_response(result)


@router.patch("/{rule_id}", response_model=CutContourRuleResponse)
def patch_cut_contour_rule(
    cut_rule_set_id: UUID,
    rule_id: UUID,
    req: CutContourRuleUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> CutContourRuleResponse:
    updates = req.model_dump(exclude_unset=True)
    try:
        result = update_cut_contour_rule(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            cut_rule_set_id=str(cut_rule_set_id),
            rule_id=str(rule_id),
            updates=updates,
        )
    except CutContourRuleError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="update cut contour rule", exc=exc)
    return _as_response(result)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_cut_contour_rule_by_id(
    cut_rule_set_id: UUID,
    rule_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> Response:
    try:
        delete_cut_contour_rule(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            cut_rule_set_id=str(cut_rule_set_id),
            rule_id=str(rule_id),
        )
    except CutContourRuleError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="delete cut contour rule", exc=exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
