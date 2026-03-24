from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from api.auth import AuthenticatedUser, get_current_user
from api.deps import get_supabase_client
from api.http_errors import raise_supabase_http_error
from api.request_models import StrictRequestModel
from api.services.run_strategy_profiles import (
    RunStrategyProfileError,
    create_run_strategy_profile,
    create_run_strategy_profile_version,
    delete_run_strategy_profile,
    delete_run_strategy_profile_version,
    get_run_strategy_profile,
    get_run_strategy_profile_version,
    list_run_strategy_profile_versions,
    list_run_strategy_profiles,
    update_run_strategy_profile,
    update_run_strategy_profile_version,
)
from api.supabase_client import SupabaseClient, SupabaseHTTPError


router = APIRouter(prefix="/run-strategy-profiles", tags=["run-strategy-profiles"])


# ---- request / response models ----


class RunStrategyProfileCreateRequest(StrictRequestModel):
    strategy_code: str
    display_name: str
    description: str | None = None
    lifecycle: str = "draft"
    is_active: bool = True
    metadata_jsonb: dict[str, Any] | None = None


class RunStrategyProfileUpdateRequest(StrictRequestModel):
    display_name: str | None = None
    description: str | None = None
    lifecycle: str | None = None
    is_active: bool | None = None
    metadata_jsonb: dict[str, Any] | None = None


class RunStrategyProfileResponse(BaseModel):
    id: str
    owner_user_id: str
    strategy_code: str
    display_name: str
    description: str | None = None
    lifecycle: str
    is_active: bool
    metadata_jsonb: dict[str, Any] | None = None
    created_at: str | None = None
    updated_at: str | None = None


class RunStrategyProfileVersionCreateRequest(StrictRequestModel):
    is_active: bool = True
    solver_config_jsonb: dict[str, Any] | None = None
    placement_config_jsonb: dict[str, Any] | None = None
    manufacturing_bias_jsonb: dict[str, Any] | None = None
    notes: str | None = None
    metadata_jsonb: dict[str, Any] | None = None


class RunStrategyProfileVersionUpdateRequest(StrictRequestModel):
    is_active: bool | None = None
    lifecycle: str | None = None
    solver_config_jsonb: dict[str, Any] | None = None
    placement_config_jsonb: dict[str, Any] | None = None
    manufacturing_bias_jsonb: dict[str, Any] | None = None
    notes: str | None = None
    metadata_jsonb: dict[str, Any] | None = None


class RunStrategyProfileVersionResponse(BaseModel):
    id: str
    run_strategy_profile_id: str
    owner_user_id: str
    version_no: int
    lifecycle: str
    is_active: bool
    solver_config_jsonb: dict[str, Any] | None = None
    placement_config_jsonb: dict[str, Any] | None = None
    manufacturing_bias_jsonb: dict[str, Any] | None = None
    notes: str | None = None
    metadata_jsonb: dict[str, Any] | None = None
    created_at: str | None = None
    updated_at: str | None = None


# ---- response builders ----


def _as_profile_response(row: dict[str, Any]) -> RunStrategyProfileResponse:
    return RunStrategyProfileResponse(
        id=str(row.get("id") or ""),
        owner_user_id=str(row.get("owner_user_id") or ""),
        strategy_code=str(row.get("strategy_code") or ""),
        display_name=str(row.get("display_name") or ""),
        description=row.get("description"),
        lifecycle=str(row.get("lifecycle") or "draft"),
        is_active=bool(row.get("is_active", True)),
        metadata_jsonb=row.get("metadata_jsonb"),
        created_at=str(row.get("created_at") or ""),
        updated_at=str(row.get("updated_at") or ""),
    )


def _as_version_response(row: dict[str, Any]) -> RunStrategyProfileVersionResponse:
    return RunStrategyProfileVersionResponse(
        id=str(row.get("id") or ""),
        run_strategy_profile_id=str(row.get("run_strategy_profile_id") or ""),
        owner_user_id=str(row.get("owner_user_id") or ""),
        version_no=int(row.get("version_no") or 1),
        lifecycle=str(row.get("lifecycle") or "draft"),
        is_active=bool(row.get("is_active", True)),
        solver_config_jsonb=row.get("solver_config_jsonb"),
        placement_config_jsonb=row.get("placement_config_jsonb"),
        manufacturing_bias_jsonb=row.get("manufacturing_bias_jsonb"),
        notes=row.get("notes"),
        metadata_jsonb=row.get("metadata_jsonb"),
        created_at=str(row.get("created_at") or ""),
        updated_at=str(row.get("updated_at") or ""),
    )


# ---- profile endpoints ----


@router.post("", response_model=RunStrategyProfileResponse, status_code=status.HTTP_201_CREATED)
def post_run_strategy_profile(
    req: RunStrategyProfileCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> RunStrategyProfileResponse:
    try:
        result = create_run_strategy_profile(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            strategy_code=req.strategy_code,
            display_name=req.display_name,
            description=req.description,
            lifecycle=req.lifecycle,
            is_active=req.is_active,
            metadata_jsonb=req.metadata_jsonb,
        )
    except RunStrategyProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="create run strategy profile", exc=exc)
    return _as_profile_response(result)


@router.get("", response_model=list[RunStrategyProfileResponse])
def get_run_strategy_profiles(
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> list[RunStrategyProfileResponse]:
    try:
        rows = list_run_strategy_profiles(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
        )
    except RunStrategyProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="list run strategy profiles", exc=exc)
    return [_as_profile_response(row) for row in rows]


@router.get("/{profile_id}", response_model=RunStrategyProfileResponse)
def get_run_strategy_profile_by_id(
    profile_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> RunStrategyProfileResponse:
    try:
        result = get_run_strategy_profile(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            profile_id=str(profile_id),
        )
    except RunStrategyProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="get run strategy profile", exc=exc)
    return _as_profile_response(result)


@router.patch("/{profile_id}", response_model=RunStrategyProfileResponse)
def patch_run_strategy_profile(
    profile_id: UUID,
    req: RunStrategyProfileUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> RunStrategyProfileResponse:
    updates = req.model_dump(exclude_unset=True)
    try:
        result = update_run_strategy_profile(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            profile_id=str(profile_id),
            updates=updates,
        )
    except RunStrategyProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="update run strategy profile", exc=exc)
    return _as_profile_response(result)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_run_strategy_profile_by_id(
    profile_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> Response:
    try:
        delete_run_strategy_profile(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            profile_id=str(profile_id),
        )
    except RunStrategyProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="delete run strategy profile", exc=exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---- version endpoints (nested under profile) ----


@router.post("/{profile_id}/versions", response_model=RunStrategyProfileVersionResponse, status_code=status.HTTP_201_CREATED)
def post_run_strategy_profile_version(
    profile_id: UUID,
    req: RunStrategyProfileVersionCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> RunStrategyProfileVersionResponse:
    try:
        result = create_run_strategy_profile_version(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            run_strategy_profile_id=str(profile_id),
            is_active=req.is_active,
            solver_config_jsonb=req.solver_config_jsonb,
            placement_config_jsonb=req.placement_config_jsonb,
            manufacturing_bias_jsonb=req.manufacturing_bias_jsonb,
            notes=req.notes,
            metadata_jsonb=req.metadata_jsonb,
        )
    except RunStrategyProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="create run strategy profile version", exc=exc)
    return _as_version_response(result)


@router.get("/{profile_id}/versions", response_model=list[RunStrategyProfileVersionResponse])
def get_run_strategy_profile_versions(
    profile_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> list[RunStrategyProfileVersionResponse]:
    try:
        rows = list_run_strategy_profile_versions(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            run_strategy_profile_id=str(profile_id),
        )
    except RunStrategyProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="list run strategy profile versions", exc=exc)
    return [_as_version_response(row) for row in rows]


@router.get("/{profile_id}/versions/{version_id}", response_model=RunStrategyProfileVersionResponse)
def get_run_strategy_profile_version_by_id(
    profile_id: UUID,
    version_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> RunStrategyProfileVersionResponse:
    try:
        result = get_run_strategy_profile_version(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            run_strategy_profile_id=str(profile_id),
            version_id=str(version_id),
        )
    except RunStrategyProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="get run strategy profile version", exc=exc)
    return _as_version_response(result)


@router.patch("/{profile_id}/versions/{version_id}", response_model=RunStrategyProfileVersionResponse)
def patch_run_strategy_profile_version(
    profile_id: UUID,
    version_id: UUID,
    req: RunStrategyProfileVersionUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> RunStrategyProfileVersionResponse:
    updates = req.model_dump(exclude_unset=True)
    try:
        result = update_run_strategy_profile_version(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            run_strategy_profile_id=str(profile_id),
            version_id=str(version_id),
            updates=updates,
        )
    except RunStrategyProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="update run strategy profile version", exc=exc)
    return _as_version_response(result)


@router.delete("/{profile_id}/versions/{version_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_run_strategy_profile_version_by_id(
    profile_id: UUID,
    version_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> Response:
    try:
        delete_run_strategy_profile_version(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            run_strategy_profile_id=str(profile_id),
            version_id=str(version_id),
        )
    except RunStrategyProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="delete run strategy profile version", exc=exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
