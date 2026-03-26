from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from api.auth import AuthenticatedUser, get_current_user
from api.deps import get_supabase_client
from api.http_errors import raise_supabase_http_error
from api.request_models import StrictRequestModel
from api.services.project_strategy_scoring_selection import (
    ProjectStrategyScoringSelectionError,
    delete_project_run_strategy_selection,
    delete_project_scoring_selection,
    get_project_run_strategy_selection,
    get_project_scoring_selection,
    set_project_run_strategy_selection,
    set_project_scoring_selection,
)
from api.supabase_client import SupabaseClient, SupabaseHTTPError


# ===================================================================
# Strategy selection router
# ===================================================================

strategy_router = APIRouter(
    prefix="/projects/{project_id}/run-strategy-selection",
    tags=["project-run-strategy-selection"],
)


class StrategySelectionUpsertRequest(StrictRequestModel):
    active_run_strategy_profile_version_id: UUID


class StrategySelectionResponse(BaseModel):
    project_id: str
    active_run_strategy_profile_version_id: str
    selected_at: str | None = None
    selected_by: str
    run_strategy_profile_id: str | None = None
    version_no: int | None = None
    was_existing_selection: bool | None = None


def _as_strategy_response(result: dict[str, Any], *, include_existing_flag: bool) -> StrategySelectionResponse:
    selection = result.get("selection")
    if not isinstance(selection, dict):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="strategy selection returned invalid payload")

    version = result.get("run_strategy_profile_version")

    project_id = str(selection.get("project_id") or "").strip()
    version_id = str(selection.get("active_run_strategy_profile_version_id") or "").strip()
    selected_by = str(selection.get("selected_by") or "").strip()
    if not project_id or not version_id or not selected_by:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="strategy selection returned empty ids")

    version_no: int | None = None
    profile_id: str | None = None
    if isinstance(version, dict):
        if version.get("version_no") is not None:
            try:
                version_no = int(version["version_no"])
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="invalid version_no") from exc
        profile_id = str(version.get("run_strategy_profile_id") or "").strip() or None

    was_existing: bool | None = None
    if include_existing_flag:
        was_existing = bool(result.get("was_existing_selection"))

    return StrategySelectionResponse(
        project_id=project_id,
        active_run_strategy_profile_version_id=version_id,
        selected_at=(str(selection.get("selected_at") or "").strip() or None),
        selected_by=selected_by,
        run_strategy_profile_id=profile_id,
        version_no=version_no,
        was_existing_selection=was_existing,
    )


@strategy_router.put("", response_model=StrategySelectionResponse)
def put_project_run_strategy_selection(
    project_id: UUID,
    req: StrategySelectionUpsertRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> StrategySelectionResponse:
    try:
        result = set_project_run_strategy_selection(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            project_id=str(project_id),
            active_run_strategy_profile_version_id=str(req.active_run_strategy_profile_version_id),
        )
    except ProjectStrategyScoringSelectionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="set project run strategy selection", exc=exc)
    return _as_strategy_response(result, include_existing_flag=True)


@strategy_router.get("", response_model=StrategySelectionResponse)
def read_project_run_strategy_selection(
    project_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> StrategySelectionResponse:
    try:
        result = get_project_run_strategy_selection(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            project_id=str(project_id),
        )
    except ProjectStrategyScoringSelectionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="get project run strategy selection", exc=exc)
    return _as_strategy_response(result, include_existing_flag=False)


@strategy_router.delete("", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def remove_project_run_strategy_selection(
    project_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> Response:
    try:
        delete_project_run_strategy_selection(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            project_id=str(project_id),
        )
    except ProjectStrategyScoringSelectionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="delete project run strategy selection", exc=exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ===================================================================
# Scoring selection router
# ===================================================================

scoring_router = APIRouter(
    prefix="/projects/{project_id}/scoring-selection",
    tags=["project-scoring-selection"],
)


class ScoringSelectionUpsertRequest(StrictRequestModel):
    active_scoring_profile_version_id: UUID


class ScoringSelectionResponse(BaseModel):
    project_id: str
    active_scoring_profile_version_id: str
    selected_at: str | None = None
    selected_by: str
    scoring_profile_id: str | None = None
    version_no: int | None = None
    was_existing_selection: bool | None = None


def _as_scoring_response(result: dict[str, Any], *, include_existing_flag: bool) -> ScoringSelectionResponse:
    selection = result.get("selection")
    if not isinstance(selection, dict):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="scoring selection returned invalid payload")

    version = result.get("scoring_profile_version")

    project_id = str(selection.get("project_id") or "").strip()
    version_id = str(selection.get("active_scoring_profile_version_id") or "").strip()
    selected_by = str(selection.get("selected_by") or "").strip()
    if not project_id or not version_id or not selected_by:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="scoring selection returned empty ids")

    version_no: int | None = None
    profile_id: str | None = None
    if isinstance(version, dict):
        if version.get("version_no") is not None:
            try:
                version_no = int(version["version_no"])
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="invalid version_no") from exc
        profile_id = str(version.get("scoring_profile_id") or "").strip() or None

    was_existing: bool | None = None
    if include_existing_flag:
        was_existing = bool(result.get("was_existing_selection"))

    return ScoringSelectionResponse(
        project_id=project_id,
        active_scoring_profile_version_id=version_id,
        selected_at=(str(selection.get("selected_at") or "").strip() or None),
        selected_by=selected_by,
        scoring_profile_id=profile_id,
        version_no=version_no,
        was_existing_selection=was_existing,
    )


@scoring_router.put("", response_model=ScoringSelectionResponse)
def put_project_scoring_selection(
    project_id: UUID,
    req: ScoringSelectionUpsertRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> ScoringSelectionResponse:
    try:
        result = set_project_scoring_selection(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            project_id=str(project_id),
            active_scoring_profile_version_id=str(req.active_scoring_profile_version_id),
        )
    except ProjectStrategyScoringSelectionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="set project scoring selection", exc=exc)
    return _as_scoring_response(result, include_existing_flag=True)


@scoring_router.get("", response_model=ScoringSelectionResponse)
def read_project_scoring_selection(
    project_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> ScoringSelectionResponse:
    try:
        result = get_project_scoring_selection(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            project_id=str(project_id),
        )
    except ProjectStrategyScoringSelectionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="get project scoring selection", exc=exc)
    return _as_scoring_response(result, include_existing_flag=False)


@scoring_router.delete("", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def remove_project_scoring_selection(
    project_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> Response:
    try:
        delete_project_scoring_selection(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            project_id=str(project_id),
        )
    except ProjectStrategyScoringSelectionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="delete project scoring selection", exc=exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
