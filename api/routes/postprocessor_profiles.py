from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from api.auth import AuthenticatedUser, get_current_user
from api.deps import get_supabase_client
from api.http_errors import raise_supabase_http_error
from api.request_models import StrictRequestModel
from api.services.postprocessor_profiles import (
    PostprocessorProfileError,
    create_postprocessor_profile,
    create_postprocessor_profile_version,
    delete_postprocessor_profile,
    delete_postprocessor_profile_version,
    get_postprocessor_profile,
    get_postprocessor_profile_version,
    list_postprocessor_profile_versions,
    list_postprocessor_profiles,
    update_postprocessor_profile,
    update_postprocessor_profile_version,
)
from api.supabase_client import SupabaseClient, SupabaseHTTPError


router = APIRouter(prefix="/postprocessor-profiles", tags=["postprocessor-profiles"])


# ---- request / response models ----


class PostprocessorProfileCreateRequest(StrictRequestModel):
    profile_code: str
    display_name: str
    adapter_key: str = "generic"
    is_active: bool = True
    notes: str | None = None
    metadata_jsonb: dict[str, Any] | None = None


class PostprocessorProfileUpdateRequest(StrictRequestModel):
    display_name: str | None = None
    adapter_key: str | None = None
    is_active: bool | None = None
    notes: str | None = None
    metadata_jsonb: dict[str, Any] | None = None


class PostprocessorProfileResponse(BaseModel):
    id: str
    owner_user_id: str
    profile_code: str
    display_name: str
    adapter_key: str
    is_active: bool
    notes: str | None = None
    metadata_jsonb: dict[str, Any] | None = None
    created_at: str | None = None
    updated_at: str | None = None


class PostprocessorProfileVersionCreateRequest(StrictRequestModel):
    adapter_key: str = "generic"
    output_format: str = "json"
    schema_version: str = "v1"
    is_active: bool = True
    config_jsonb: dict[str, Any] | None = None
    notes: str | None = None
    metadata_jsonb: dict[str, Any] | None = None


class PostprocessorProfileVersionUpdateRequest(StrictRequestModel):
    adapter_key: str | None = None
    output_format: str | None = None
    schema_version: str | None = None
    is_active: bool | None = None
    lifecycle: str | None = None
    config_jsonb: dict[str, Any] | None = None
    notes: str | None = None
    metadata_jsonb: dict[str, Any] | None = None


class PostprocessorProfileVersionResponse(BaseModel):
    id: str
    postprocessor_profile_id: str
    owner_user_id: str
    version_no: int
    lifecycle: str
    is_active: bool
    adapter_key: str
    output_format: str
    schema_version: str
    config_jsonb: dict[str, Any] | None = None
    notes: str | None = None
    metadata_jsonb: dict[str, Any] | None = None
    created_at: str | None = None
    updated_at: str | None = None


# ---- response builders ----


def _as_profile_response(row: dict[str, Any]) -> PostprocessorProfileResponse:
    return PostprocessorProfileResponse(
        id=str(row.get("id") or ""),
        owner_user_id=str(row.get("owner_user_id") or ""),
        profile_code=str(row.get("profile_code") or ""),
        display_name=str(row.get("display_name") or ""),
        adapter_key=str(row.get("adapter_key") or "generic"),
        is_active=bool(row.get("is_active", True)),
        notes=row.get("notes"),
        metadata_jsonb=row.get("metadata_jsonb"),
        created_at=str(row.get("created_at") or ""),
        updated_at=str(row.get("updated_at") or ""),
    )


def _as_version_response(row: dict[str, Any]) -> PostprocessorProfileVersionResponse:
    return PostprocessorProfileVersionResponse(
        id=str(row.get("id") or ""),
        postprocessor_profile_id=str(row.get("postprocessor_profile_id") or ""),
        owner_user_id=str(row.get("owner_user_id") or ""),
        version_no=int(row.get("version_no") or 1),
        lifecycle=str(row.get("lifecycle") or "draft"),
        is_active=bool(row.get("is_active", True)),
        adapter_key=str(row.get("adapter_key") or "generic"),
        output_format=str(row.get("output_format") or "json"),
        schema_version=str(row.get("schema_version") or "v1"),
        config_jsonb=row.get("config_jsonb"),
        notes=row.get("notes"),
        metadata_jsonb=row.get("metadata_jsonb"),
        created_at=str(row.get("created_at") or ""),
        updated_at=str(row.get("updated_at") or ""),
    )


# ---- profile endpoints ----


@router.post("", response_model=PostprocessorProfileResponse, status_code=status.HTTP_201_CREATED)
def post_postprocessor_profile(
    req: PostprocessorProfileCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> PostprocessorProfileResponse:
    try:
        result = create_postprocessor_profile(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            profile_code=req.profile_code,
            display_name=req.display_name,
            adapter_key=req.adapter_key,
            is_active=req.is_active,
            notes=req.notes,
            metadata_jsonb=req.metadata_jsonb,
        )
    except PostprocessorProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="create postprocessor profile", exc=exc)
    return _as_profile_response(result)


@router.get("", response_model=list[PostprocessorProfileResponse])
def get_postprocessor_profiles(
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> list[PostprocessorProfileResponse]:
    try:
        rows = list_postprocessor_profiles(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
        )
    except PostprocessorProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="list postprocessor profiles", exc=exc)
    return [_as_profile_response(row) for row in rows]


@router.get("/{profile_id}", response_model=PostprocessorProfileResponse)
def get_postprocessor_profile_by_id(
    profile_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> PostprocessorProfileResponse:
    try:
        result = get_postprocessor_profile(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            profile_id=str(profile_id),
        )
    except PostprocessorProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="get postprocessor profile", exc=exc)
    return _as_profile_response(result)


@router.patch("/{profile_id}", response_model=PostprocessorProfileResponse)
def patch_postprocessor_profile(
    profile_id: UUID,
    req: PostprocessorProfileUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> PostprocessorProfileResponse:
    updates = req.model_dump(exclude_unset=True)
    try:
        result = update_postprocessor_profile(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            profile_id=str(profile_id),
            updates=updates,
        )
    except PostprocessorProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="update postprocessor profile", exc=exc)
    return _as_profile_response(result)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_postprocessor_profile_by_id(
    profile_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> Response:
    try:
        delete_postprocessor_profile(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            profile_id=str(profile_id),
        )
    except PostprocessorProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="delete postprocessor profile", exc=exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---- version endpoints (nested under profile) ----


@router.post("/{profile_id}/versions", response_model=PostprocessorProfileVersionResponse, status_code=status.HTTP_201_CREATED)
def post_postprocessor_profile_version(
    profile_id: UUID,
    req: PostprocessorProfileVersionCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> PostprocessorProfileVersionResponse:
    try:
        result = create_postprocessor_profile_version(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            postprocessor_profile_id=str(profile_id),
            adapter_key=req.adapter_key,
            output_format=req.output_format,
            schema_version=req.schema_version,
            is_active=req.is_active,
            config_jsonb=req.config_jsonb,
            notes=req.notes,
            metadata_jsonb=req.metadata_jsonb,
        )
    except PostprocessorProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="create postprocessor profile version", exc=exc)
    return _as_version_response(result)


@router.get("/{profile_id}/versions", response_model=list[PostprocessorProfileVersionResponse])
def get_postprocessor_profile_versions(
    profile_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> list[PostprocessorProfileVersionResponse]:
    try:
        rows = list_postprocessor_profile_versions(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            postprocessor_profile_id=str(profile_id),
        )
    except PostprocessorProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="list postprocessor profile versions", exc=exc)
    return [_as_version_response(row) for row in rows]


@router.get("/{profile_id}/versions/{version_id}", response_model=PostprocessorProfileVersionResponse)
def get_postprocessor_profile_version_by_id(
    profile_id: UUID,
    version_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> PostprocessorProfileVersionResponse:
    try:
        result = get_postprocessor_profile_version(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            postprocessor_profile_id=str(profile_id),
            version_id=str(version_id),
        )
    except PostprocessorProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="get postprocessor profile version", exc=exc)
    return _as_version_response(result)


@router.patch("/{profile_id}/versions/{version_id}", response_model=PostprocessorProfileVersionResponse)
def patch_postprocessor_profile_version(
    profile_id: UUID,
    version_id: UUID,
    req: PostprocessorProfileVersionUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> PostprocessorProfileVersionResponse:
    updates = req.model_dump(exclude_unset=True)
    try:
        result = update_postprocessor_profile_version(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            postprocessor_profile_id=str(profile_id),
            version_id=str(version_id),
            updates=updates,
        )
    except PostprocessorProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="update postprocessor profile version", exc=exc)
    return _as_version_response(result)


@router.delete("/{profile_id}/versions/{version_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_postprocessor_profile_version_by_id(
    profile_id: UUID,
    version_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> Response:
    try:
        delete_postprocessor_profile_version(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            postprocessor_profile_id=str(profile_id),
            version_id=str(version_id),
        )
    except PostprocessorProfileError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="delete postprocessor profile version", exc=exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
