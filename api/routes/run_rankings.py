from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from api.auth import AuthenticatedUser, get_current_user
from api.deps import get_supabase_client
from api.http_errors import raise_supabase_http_error
from api.request_models import StrictRequestModel
from api.services.run_rankings import (
    RunRankingError,
    create_or_replace_run_batch_ranking,
    delete_run_batch_ranking,
    list_run_batch_ranking,
)
from api.supabase_client import SupabaseClient, SupabaseHTTPError


router = APIRouter(prefix="/projects/{project_id}/run-batches/{batch_id}/ranking", tags=["run-rankings"])


class RunBatchRankingUpsertRequest(StrictRequestModel):
    pass


class RunBatchRankingItemResponse(BaseModel):
    id: str | None = None
    batch_id: str
    run_id: str
    rank_no: int
    ranking_reason_jsonb: dict[str, Any]
    created_at: str | None = None


class RunBatchRankingUpsertResponse(BaseModel):
    items: list[RunBatchRankingItemResponse]
    total: int
    was_replaced: bool


class RunBatchRankingListResponse(BaseModel):
    items: list[RunBatchRankingItemResponse]
    total: int


def _as_item_response(row: dict[str, Any]) -> RunBatchRankingItemResponse:
    batch_id = str(row.get("batch_id") or "").strip()
    run_id = str(row.get("run_id") or "").strip()
    if not batch_id or not run_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="run ranking returned empty ids")
    return RunBatchRankingItemResponse(
        id=str(row.get("id") or "").strip() or None,
        batch_id=batch_id,
        run_id=run_id,
        rank_no=int(row.get("rank_no") or 0),
        ranking_reason_jsonb=row.get("ranking_reason_jsonb") if isinstance(row.get("ranking_reason_jsonb"), dict) else {},
        created_at=str(row.get("created_at") or "").strip() or None,
    )


@router.post("", response_model=RunBatchRankingUpsertResponse)
def post_run_batch_ranking(
    project_id: UUID,
    batch_id: UUID,
    req: RunBatchRankingUpsertRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> RunBatchRankingUpsertResponse:
    _ = req
    try:
        result = create_or_replace_run_batch_ranking(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            project_id=str(project_id),
            batch_id=str(batch_id),
        )
    except RunRankingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="create run batch ranking", exc=exc)

    rows = result.get("items")
    if not isinstance(rows, list):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="create run batch ranking returned invalid payload")
    items = [_as_item_response(row) for row in rows if isinstance(row, dict)]
    return RunBatchRankingUpsertResponse(
        items=items,
        total=int(result.get("total") or len(items)),
        was_replaced=bool(result.get("was_replaced")),
    )


@router.get("", response_model=RunBatchRankingListResponse)
def get_run_batch_ranking(
    project_id: UUID,
    batch_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> RunBatchRankingListResponse:
    try:
        result = list_run_batch_ranking(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            project_id=str(project_id),
            batch_id=str(batch_id),
        )
    except RunRankingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="list run batch ranking", exc=exc)

    rows = result.get("items")
    if not isinstance(rows, list):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="list run batch ranking returned invalid payload")
    items = [_as_item_response(row) for row in rows if isinstance(row, dict)]
    return RunBatchRankingListResponse(items=items, total=len(items))


@router.delete("", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_run_batch_ranking_by_batch(
    project_id: UUID,
    batch_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> Response:
    try:
        delete_run_batch_ranking(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            project_id=str(project_id),
            batch_id=str(batch_id),
        )
    except RunRankingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="delete run batch ranking", exc=exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
