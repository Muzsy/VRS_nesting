from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from api.auth import AuthenticatedUser, get_current_user
from api.deps import get_supabase_client
from api.http_errors import raise_supabase_http_error
from api.request_models import StrictRequestModel
from api.services.run_batches import (
    RunBatchError,
    attach_run_batch_item,
    create_run_batch,
    delete_run_batch,
    get_run_batch,
    list_run_batch_items,
    list_run_batches,
    remove_run_batch_item,
)
from api.supabase_client import SupabaseClient, SupabaseHTTPError


router = APIRouter(prefix="/projects/{project_id}/run-batches", tags=["run-batches"])


class RunBatchCreateRequest(StrictRequestModel):
    batch_kind: str = Field(default="comparison", min_length=1, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)


class RunBatchResponse(BaseModel):
    id: str
    project_id: str
    created_by: str | None = None
    batch_kind: str
    notes: str | None = None
    created_at: str | None = None


class RunBatchListResponse(BaseModel):
    items: list[RunBatchResponse]
    total: int


class RunBatchItemAttachRequest(StrictRequestModel):
    run_id: UUID
    candidate_label: str | None = Field(default=None, max_length=120)
    strategy_profile_version_id: UUID | None = None
    scoring_profile_version_id: UUID | None = None


class RunBatchItemResponse(BaseModel):
    batch_id: str
    run_id: str
    candidate_label: str | None = None
    strategy_profile_version_id: str | None = None
    scoring_profile_version_id: str | None = None
    created_at: str | None = None


class RunBatchItemListResponse(BaseModel):
    items: list[RunBatchItemResponse]
    total: int


def _as_run_batch_response(row: dict[str, Any]) -> RunBatchResponse:
    batch_id = str(row.get("id") or "").strip()
    project_id = str(row.get("project_id") or "").strip()
    batch_kind = str(row.get("batch_kind") or "").strip()
    if not batch_id or not project_id or not batch_kind:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="run batch returned empty ids")

    created_by_raw = str(row.get("created_by") or "").strip() or None
    notes_raw = str(row.get("notes") or "").strip() or None
    created_at_raw = str(row.get("created_at") or "").strip() or None

    return RunBatchResponse(
        id=batch_id,
        project_id=project_id,
        created_by=created_by_raw,
        batch_kind=batch_kind,
        notes=notes_raw,
        created_at=created_at_raw,
    )


def _as_run_batch_item_response(row: dict[str, Any]) -> RunBatchItemResponse:
    batch_id = str(row.get("batch_id") or "").strip()
    run_id = str(row.get("run_id") or "").strip()
    if not batch_id or not run_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="run batch item returned empty ids")

    return RunBatchItemResponse(
        batch_id=batch_id,
        run_id=run_id,
        candidate_label=str(row.get("candidate_label") or "").strip() or None,
        strategy_profile_version_id=str(row.get("strategy_profile_version_id") or "").strip() or None,
        scoring_profile_version_id=str(row.get("scoring_profile_version_id") or "").strip() or None,
        created_at=str(row.get("created_at") or "").strip() or None,
    )


@router.post("", response_model=RunBatchResponse)
def post_run_batch(
    project_id: UUID,
    req: RunBatchCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> RunBatchResponse:
    try:
        result = create_run_batch(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            project_id=str(project_id),
            batch_kind=req.batch_kind,
            notes=req.notes,
        )
    except RunBatchError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="create run batch", exc=exc)

    row = result.get("batch")
    if not isinstance(row, dict):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="create run batch returned invalid payload")
    return _as_run_batch_response(row)


@router.get("", response_model=RunBatchListResponse)
def get_run_batches(
    project_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> RunBatchListResponse:
    try:
        result = list_run_batches(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            project_id=str(project_id),
        )
    except RunBatchError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="list run batches", exc=exc)

    rows = result.get("items")
    if not isinstance(rows, list):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="list run batches returned invalid payload")
    items = [_as_run_batch_response(row) for row in rows if isinstance(row, dict)]
    return RunBatchListResponse(items=items, total=len(items))


@router.get("/{batch_id}", response_model=RunBatchResponse)
def get_run_batch_by_id(
    project_id: UUID,
    batch_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> RunBatchResponse:
    try:
        result = get_run_batch(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            project_id=str(project_id),
            batch_id=str(batch_id),
        )
    except RunBatchError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="get run batch", exc=exc)

    row = result.get("batch")
    if not isinstance(row, dict):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="get run batch returned invalid payload")
    return _as_run_batch_response(row)


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_run_batch_by_id(
    project_id: UUID,
    batch_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> Response:
    try:
        delete_run_batch(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            project_id=str(project_id),
            batch_id=str(batch_id),
        )
    except RunBatchError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="delete run batch", exc=exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{batch_id}/items", response_model=RunBatchItemResponse)
def post_run_batch_item(
    project_id: UUID,
    batch_id: UUID,
    req: RunBatchItemAttachRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> RunBatchItemResponse:
    try:
        result = attach_run_batch_item(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            project_id=str(project_id),
            batch_id=str(batch_id),
            run_id=str(req.run_id),
            candidate_label=req.candidate_label,
            strategy_profile_version_id=(
                str(req.strategy_profile_version_id)
                if req.strategy_profile_version_id is not None
                else None
            ),
            scoring_profile_version_id=(
                str(req.scoring_profile_version_id)
                if req.scoring_profile_version_id is not None
                else None
            ),
        )
    except RunBatchError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="attach run batch item", exc=exc)

    row = result.get("item")
    if not isinstance(row, dict):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="attach run batch item returned invalid payload")
    return _as_run_batch_item_response(row)


@router.get("/{batch_id}/items", response_model=RunBatchItemListResponse)
def get_run_batch_items(
    project_id: UUID,
    batch_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> RunBatchItemListResponse:
    try:
        result = list_run_batch_items(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            project_id=str(project_id),
            batch_id=str(batch_id),
        )
    except RunBatchError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="list run batch items", exc=exc)

    rows = result.get("items")
    if not isinstance(rows, list):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="list run batch items returned invalid payload")
    items = [_as_run_batch_item_response(row) for row in rows if isinstance(row, dict)]
    return RunBatchItemListResponse(items=items, total=len(items))


@router.delete("/{batch_id}/items/{run_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_run_batch_item_by_id(
    project_id: UUID,
    batch_id: UUID,
    run_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> Response:
    try:
        remove_run_batch_item(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            project_id=str(project_id),
            batch_id=str(batch_id),
            run_id=str(run_id),
        )
    except RunBatchError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="remove run batch item", exc=exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
