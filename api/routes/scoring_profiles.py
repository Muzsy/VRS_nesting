from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from api.auth import AuthenticatedUser, get_current_user
from api.deps import get_supabase_client
from api.http_errors import raise_supabase_http_error
from api.request_models import StrictRequestModel
from api.services.scoring_profiles import (
    ScoringProfileError,
    create_scoring_profile,
    create_scoring_profile_version,
    delete_scoring_profile,
    delete_scoring_profile_version,
    get_scoring_profile,
    get_scoring_profile_version,
    list_scoring_profile_versions,
    list_scoring_profiles,
    update_scoring_profile,
    update_scoring_profile_version,
)
from api.supabase_client import SupabaseClient, SupabaseHTTPError


router = APIRouter(prefix="/scoring-profiles", tags=["scoring-profiles"])


# ---- request / response models ----


class ScoringProfileCreateRequest(StrictRequestModel):
    name: str
    description: str | None = None
    lifecycle: str = "draft"
    is_active: bool = True
    metadata_jsonb: dict[str, Any] | None = None


class ScoringProfileUpdateRequest(StrictRequestModel):
    name: str | None = None
    description: str | None = None
    lifecycle: str | None = None
    is_active: bool | None = None
    metadata_jsonb: dict[str, Any] | None = None


class ScoringProfileResponse(BaseModel):
    id: str
    owner_user_id: str
    name: str
    description: str | None = None
    lifecycle: str
    is_active: bool
    metadata_jsonb: dict[str, Any] | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ScoringProfileVersionCreateRequest(StrictRequestModel):
    is_active: bool = True
    weights_jsonb: dict[str, Any] | None = None
    tie_breaker_jsonb: dict[str, Any] | None = None
    threshold_jsonb: dict[str, Any] | None = None
    notes: str | None = None
    metadata_jsonb: dict[str, Any] | None = None


class ScoringProfileVersionUpdateRequest(StrictRequestModel):
    is_active: bool | None = None
    lifecycle: str | None = None
    weights_jsonb: dict[str, Any] | None = None
    tie_breaker_jsonb: dict[str, Any] | None = None
    threshold_jsonb: dict[str, Any] | None = None
    notes: str | None = None
    metadata_jsonb: dict[str, Any] | None = None


class ScoringProfileVersionResponse(BaseModel):
    id: str
    scoring_profile_id: str
    owner_user_id: str
    version_no: int
    lifecycle: str
    is_active: bool
    weights_jsonb: dict[str, Any] | None = None
    tie_breaker_jsonb: dict[str, Any] | None = None
    threshold_jsonb: dict[str, Any] | None = None
    notes: str | None = None
    metadata_jsonb: dict[str, Any] | None = None
    created_at: str | None = None
    updated_at: str | None = None


# ---- response builders ----


def _as_profile_response(row: dict[str, Any]) -> ScoringProfileResponse:
    return ScoringProfileResponse(
        id=str(row.get("id") or ""),
        owner_user_id=str(row.get("owner_user_id") or ""),
        name=str(row.get("name") or ""),
        description=row.get("description"),
        lifecycle=str(row.get("lifecycle") or "draft"),
        is_active=bool(row.get("is_active", True)),
        metadata_jsonb=row.get("metadata_jsonb"),
        created_at=str(row.get("created_at") or ""),
        updated_at=str(row.get("updated_at") or ""),
    )


def _as_version_response(row: dict[str, Any]) -> ScoringProfileVersionResponse:
    return ScoringProfileVersionResponse(
        id=str(row.get("id") or ""),
        scoring_profile_id=str(row.get("scoring_profile_id") or ""),
        owner_user_id=str(row.get("owner_user_id") or ""),
        version_no=int(row.get("version_no") or 1),
        lifecycle=str(row.get("lifecycle") or "draft"),
        is_active=bool(row.get("is_active", True)),
        weights_jsonb=row.get("weights_jsonb"),
        tie_breaker_jsonb=row.get("tie_breaker_jsonb"),
        threshold_jsonb=row.get("threshold_jsonb"),
        notes=row.get("notes"),
        metadata_jsonb=row.get("metadata_jsonb"),
        created_at=str(row.get("created_at") or ""),
        updated_at=str(row.get("updated_at") or ""),
    )


# ---- profile endpoints ----


@router.post("", response_model=ScoringProfileResponse, status_code=status.HTTP_201_CREATED)
def post_scoring_profile(
    req: ScoringProfileCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> ScoringProfileResponse:
    try:
        result = create_scoring_profile(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            name=req.name,
            description=req.description,
            lifecycle=req.lifecycle,
            is_active=req.is_active,
            metadata_jsonb=req.metadata_jsonb,
        )
    except ScoringProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="create scoring profile", exc=exc)
    return _as_profile_response(result)


@router.get("", response_model=list[ScoringProfileResponse])
def get_scoring_profiles(
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> list[ScoringProfileResponse]:
    try:
        rows = list_scoring_profiles(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
        )
    except ScoringProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="list scoring profiles", exc=exc)
    return [_as_profile_response(row) for row in rows]


@router.get("/{profile_id}", response_model=ScoringProfileResponse)
def get_scoring_profile_by_id(
    profile_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> ScoringProfileResponse:
    try:
        result = get_scoring_profile(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            profile_id=str(profile_id),
        )
    except ScoringProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="get scoring profile", exc=exc)
    return _as_profile_response(result)


@router.patch("/{profile_id}", response_model=ScoringProfileResponse)
def patch_scoring_profile(
    profile_id: UUID,
    req: ScoringProfileUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> ScoringProfileResponse:
    updates = req.model_dump(exclude_unset=True)
    try:
        result = update_scoring_profile(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            profile_id=str(profile_id),
            updates=updates,
        )
    except ScoringProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="update scoring profile", exc=exc)
    return _as_profile_response(result)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_scoring_profile_by_id(
    profile_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> Response:
    try:
        delete_scoring_profile(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            profile_id=str(profile_id),
        )
    except ScoringProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="delete scoring profile", exc=exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---- version endpoints (nested under profile) ----


@router.post("/{profile_id}/versions", response_model=ScoringProfileVersionResponse, status_code=status.HTTP_201_CREATED)
def post_scoring_profile_version(
    profile_id: UUID,
    req: ScoringProfileVersionCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> ScoringProfileVersionResponse:
    try:
        result = create_scoring_profile_version(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            scoring_profile_id=str(profile_id),
            is_active=req.is_active,
            weights_jsonb=req.weights_jsonb,
            tie_breaker_jsonb=req.tie_breaker_jsonb,
            threshold_jsonb=req.threshold_jsonb,
            notes=req.notes,
            metadata_jsonb=req.metadata_jsonb,
        )
    except ScoringProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="create scoring profile version", exc=exc)
    return _as_version_response(result)


@router.get("/{profile_id}/versions", response_model=list[ScoringProfileVersionResponse])
def get_scoring_profile_versions(
    profile_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> list[ScoringProfileVersionResponse]:
    try:
        rows = list_scoring_profile_versions(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            scoring_profile_id=str(profile_id),
        )
    except ScoringProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="list scoring profile versions", exc=exc)
    return [_as_version_response(row) for row in rows]


@router.get("/{profile_id}/versions/{version_id}", response_model=ScoringProfileVersionResponse)
def get_scoring_profile_version_by_id(
    profile_id: UUID,
    version_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> ScoringProfileVersionResponse:
    try:
        result = get_scoring_profile_version(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            scoring_profile_id=str(profile_id),
            version_id=str(version_id),
        )
    except ScoringProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="get scoring profile version", exc=exc)
    return _as_version_response(result)


@router.patch("/{profile_id}/versions/{version_id}", response_model=ScoringProfileVersionResponse)
def patch_scoring_profile_version(
    profile_id: UUID,
    version_id: UUID,
    req: ScoringProfileVersionUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> ScoringProfileVersionResponse:
    updates = req.model_dump(exclude_unset=True)
    try:
        result = update_scoring_profile_version(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            scoring_profile_id=str(profile_id),
            version_id=str(version_id),
            updates=updates,
        )
    except ScoringProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="update scoring profile version", exc=exc)
    return _as_version_response(result)


@router.delete("/{profile_id}/versions/{version_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_scoring_profile_version_by_id(
    profile_id: UUID,
    version_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> Response:
    try:
        delete_scoring_profile_version(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            scoring_profile_id=str(profile_id),
            version_id=str(version_id),
        )
    except ScoringProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="delete scoring profile version", exc=exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
