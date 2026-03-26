from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from api.auth import AuthenticatedUser, get_current_user
from api.deps import get_supabase_client
from api.http_errors import raise_supabase_http_error
from api.services.run_best_by_objective import (
    RunBestByObjectiveError,
    list_best_by_objective,
)
from api.supabase_client import SupabaseClient, SupabaseHTTPError


router = APIRouter(
    prefix="/projects/{project_id}/run-batches/{batch_id}/best-by-objective",
    tags=["run-best-by-objective"],
)


class BestByObjectiveItemResponse(BaseModel):
    objective: str
    status: str
    batch_id: str
    run_id: str | None = None
    rank_no: int | None = None
    candidate_label: str | None = None
    objective_value: float | None = None
    objective_reason_jsonb: dict[str, Any]


class BestByObjectiveListResponse(BaseModel):
    batch_id: str
    items: list[BestByObjectiveItemResponse]
    total: int


def _as_item_response(row: dict[str, Any]) -> BestByObjectiveItemResponse:
    objective = str(row.get("objective") or "").strip()
    status_value = str(row.get("status") or "").strip()
    batch_id = str(row.get("batch_id") or "").strip()
    if not objective or not status_value or not batch_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="best-by-objective returned invalid payload",
        )

    objective_value_raw = row.get("objective_value")
    objective_value = float(objective_value_raw) if objective_value_raw is not None else None
    rank_no_raw = row.get("rank_no")
    rank_no = int(rank_no_raw) if rank_no_raw is not None else None
    reason_raw = row.get("objective_reason_jsonb")
    reason = reason_raw if isinstance(reason_raw, dict) else {}

    return BestByObjectiveItemResponse(
        objective=objective,
        status=status_value,
        batch_id=batch_id,
        run_id=str(row.get("run_id") or "").strip() or None,
        rank_no=rank_no,
        candidate_label=str(row.get("candidate_label") or "").strip() or None,
        objective_value=objective_value,
        objective_reason_jsonb=reason,
    )


@router.get("", response_model=BestByObjectiveListResponse)
def get_run_batch_best_by_objective(
    project_id: UUID,
    batch_id: UUID,
    objective: str | None = Query(default=None),
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> BestByObjectiveListResponse:
    try:
        result = list_best_by_objective(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            project_id=str(project_id),
            batch_id=str(batch_id),
            objective=objective,
        )
    except RunBestByObjectiveError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="list run batch best by objective", exc=exc)

    rows = result.get("items")
    if not isinstance(rows, list):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="list run batch best by objective returned invalid payload",
        )
    items = [_as_item_response(row) for row in rows if isinstance(row, dict)]
    return BestByObjectiveListResponse(
        batch_id=str(result.get("batch_id") or "").strip() or str(batch_id),
        items=items,
        total=int(result.get("total") or len(items)),
    )
