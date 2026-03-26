from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from api.auth import AuthenticatedUser, get_current_user
from api.deps import get_supabase_client
from api.http_errors import raise_supabase_http_error
from api.request_models import StrictRequestModel
from api.services.run_evaluations import (
    RunEvaluationError,
    create_or_replace_run_evaluation,
    delete_run_evaluation,
    get_run_evaluation,
)
from api.supabase_client import SupabaseClient, SupabaseHTTPError


router = APIRouter(prefix="/projects/{project_id}/runs/{run_id}/evaluation", tags=["run-evaluations"])


class RunEvaluationUpsertRequest(StrictRequestModel):
    scoring_profile_version_id: UUID | None = None


class RunEvaluationResponse(BaseModel):
    run_id: str
    scoring_profile_version_id: str | None = None
    total_score: float | None = None
    evaluation_jsonb: dict[str, Any]
    created_at: str | None = None


class RunEvaluationUpsertResponse(BaseModel):
    evaluation: RunEvaluationResponse
    was_replaced: bool
    resolved_from_project_selection: bool


def _as_evaluation_response(row: dict[str, Any]) -> RunEvaluationResponse:
    run_id = str(row.get("run_id") or "").strip()
    if not run_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="run evaluation returned empty run_id")
    total_score_raw = row.get("total_score")
    total_score = float(total_score_raw) if total_score_raw is not None else None
    return RunEvaluationResponse(
        run_id=run_id,
        scoring_profile_version_id=str(row.get("scoring_profile_version_id") or "").strip() or None,
        total_score=total_score,
        evaluation_jsonb=row.get("evaluation_jsonb") if isinstance(row.get("evaluation_jsonb"), dict) else {},
        created_at=str(row.get("created_at") or "").strip() or None,
    )


@router.post("", response_model=RunEvaluationUpsertResponse)
def post_run_evaluation(
    project_id: UUID,
    run_id: UUID,
    req: RunEvaluationUpsertRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> RunEvaluationUpsertResponse:
    try:
        result = create_or_replace_run_evaluation(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            project_id=str(project_id),
            run_id=str(run_id),
            scoring_profile_version_id=(
                str(req.scoring_profile_version_id)
                if req.scoring_profile_version_id is not None
                else None
            ),
        )
    except RunEvaluationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="create run evaluation", exc=exc)

    row = result.get("evaluation")
    if not isinstance(row, dict):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="create run evaluation returned invalid payload")

    return RunEvaluationUpsertResponse(
        evaluation=_as_evaluation_response(row),
        was_replaced=bool(result.get("was_replaced")),
        resolved_from_project_selection=bool(result.get("resolved_from_project_selection")),
    )


@router.get("", response_model=RunEvaluationResponse)
def get_run_evaluation_by_run(
    project_id: UUID,
    run_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> RunEvaluationResponse:
    try:
        result = get_run_evaluation(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            project_id=str(project_id),
            run_id=str(run_id),
        )
    except RunEvaluationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="get run evaluation", exc=exc)

    row = result.get("evaluation")
    if not isinstance(row, dict):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="get run evaluation returned invalid payload")
    return _as_evaluation_response(row)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_run_evaluation_by_run(
    project_id: UUID,
    run_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> Response:
    try:
        delete_run_evaluation(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            project_id=str(project_id),
            run_id=str(run_id),
        )
    except RunEvaluationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="delete run evaluation", exc=exc)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
