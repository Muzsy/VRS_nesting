from __future__ import annotations

import json
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from api.auth import AuthenticatedUser, get_current_user
from api.config import Settings
from api.deps import get_settings, get_supabase_client
from api.http_errors import raise_supabase_http_error
from api.rate_limit import enforce_user_rate_limit
from api.request_models import StrictRequestModel
from api.services.run_creation import RunCreationError, create_queued_run_from_project_snapshot
from api.supabase_client import SupabaseClient, SupabaseHTTPError

router = APIRouter(prefix="/projects/{project_id}/runs", tags=["runs"])


class RunCreateRequest(StrictRequestModel):
    idempotency_key: str | None = Field(default=None, max_length=160)
    run_purpose: str = Field(default="nesting", min_length=1, max_length=120)
    time_limit_s: int | None = Field(default=None, ge=1, le=3600)
    sa_eval_budget_sec: int | None = Field(default=None, ge=1, le=3600)


class RunMetrics(BaseModel):
    placements_count: int
    unplaced_count: int
    sheet_count: int


class RunResponse(BaseModel):
    id: str
    project_id: str
    run_config_id: str | None = None
    triggered_by: str
    status: str
    queued_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    duration_sec: float | None = None
    solver_exit_code: int | None = None
    error_message: str | None = None
    metrics: RunMetrics | None = None


class RunListResponse(BaseModel):
    items: list[RunResponse]
    total: int
    page: int
    page_size: int


class RunLogLine(BaseModel):
    line_no: int
    text: str


class RunLogResponse(BaseModel):
    lines: list[RunLogLine]
    total_lines: int
    next_offset: int
    run_status: str
    stop_polling: bool


class RunArtifactResponse(BaseModel):
    id: str
    run_id: str
    artifact_type: str
    filename: str
    storage_key: str
    size_bytes: int | None = None
    sheet_index: int | None = None
    created_at: str | None = None


class RunArtifactListResponse(BaseModel):
    items: list[RunArtifactResponse]
    total: int


class ArtifactUrlResponse(BaseModel):
    artifact_id: str
    filename: str
    download_url: str
    expires_at: str


class BundleRequest(StrictRequestModel):
    artifact_ids: list[UUID] = Field(default_factory=list, max_length=100)


class BundleResponse(BaseModel):
    artifact_id: str
    filename: str
    bundle_url: str
    expires_at: str


class ViewerSheetResponse(BaseModel):
    sheet_index: int
    dxf_artifact_id: str | None = None
    svg_artifact_id: str | None = None
    dxf_filename: str | None = None
    svg_filename: str | None = None
    dxf_download_path: str | None = None
    svg_download_path: str | None = None
    dxf_url: str | None = None
    dxf_url_expires_at: str | None = None
    svg_url: str | None = None
    svg_url_expires_at: str | None = None
    width_mm: float | None = None
    height_mm: float | None = None
    utilization_pct: float | None = None
    placements_count: int


class ViewerPlacementResponse(BaseModel):
    instance_id: str
    part_id: str
    sheet_index: int
    x: float
    y: float
    rotation_deg: float
    width_mm: float
    height_mm: float


class ViewerUnplacedResponse(BaseModel):
    instance_id: str
    part_id: str
    reason: str | None = None


class ViewerDataResponse(BaseModel):
    run_id: str
    status: str
    sheet_count: int
    sheets: list[ViewerSheetResponse]
    placements: list[ViewerPlacementResponse]
    unplaced: list[ViewerUnplacedResponse]
    engine_backend: str | None = None
    engine_contract_version: str | None = None
    engine_profile: str | None = None
    input_artifact_source: str | None = None
    output_artifact_filename: str | None = None
    output_artifact_kind: str | None = None


_TERMINAL_STATES = {"done", "failed", "cancelled"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_metrics(row: dict[str, Any]) -> RunMetrics | None:
    placements = row.get("placements_count")
    unplaced = row.get("unplaced_count")
    sheets = row.get("sheet_count")
    if placements is None and unplaced is None and sheets is None:
        return None
    return RunMetrics(
        placements_count=int(placements or 0),
        unplaced_count=int(unplaced or 0),
        sheet_count=int(sheets or 0),
    )


def _to_run_response(row: dict[str, Any]) -> RunResponse:
    run_config_id_raw = row.get("run_config_id")
    triggered_by_raw = row.get("triggered_by")
    if triggered_by_raw is None:
        triggered_by_raw = row.get("requested_by")
    return RunResponse(
        id=str(row.get("id", "")),
        project_id=str(row.get("project_id", "")),
        run_config_id=str(run_config_id_raw) if run_config_id_raw is not None else None,
        triggered_by=str(triggered_by_raw or ""),
        status=str(row.get("status", "queued")),
        queued_at=row.get("queued_at"),
        started_at=row.get("started_at"),
        finished_at=row.get("finished_at"),
        duration_sec=float(row.get("duration_sec")) if row.get("duration_sec") is not None else None,
        solver_exit_code=int(row.get("solver_exit_code")) if row.get("solver_exit_code") is not None else None,
        error_message=row.get("error_message"),
        metrics=_parse_metrics(row),
    )


def _legacy_artifact_type_from_row(row: dict[str, Any]) -> str:
    metadata = row.get("metadata_jsonb")
    if isinstance(metadata, dict):
        legacy_raw = metadata.get("legacy_artifact_type")
        if isinstance(legacy_raw, str) and legacy_raw.strip():
            return legacy_raw.strip()

    raw_kind = str(row.get("artifact_kind") or row.get("artifact_type") or "").strip()
    if raw_kind == "log":
        return "run_log"
    return raw_kind


def _artifact_filename_from_row(row: dict[str, Any]) -> str:
    metadata = row.get("metadata_jsonb")
    if isinstance(metadata, dict):
        filename_raw = metadata.get("filename")
        if isinstance(filename_raw, str) and filename_raw.strip():
            return filename_raw.strip()
    filename_raw = row.get("filename")
    if isinstance(filename_raw, str) and filename_raw.strip():
        return filename_raw.strip()
    storage_path = str(row.get("storage_path") or row.get("storage_key") or "").strip()
    if not storage_path:
        return ""
    return storage_path.split("/")[-1]


def _artifact_int_meta(row: dict[str, Any], key: str) -> int | None:
    metadata = row.get("metadata_jsonb")
    if isinstance(metadata, dict):
        raw = metadata.get(key)
        if raw is not None:
            try:
                return int(raw)
            except (TypeError, ValueError):
                return None
    raw = row.get(key)
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _normalize_artifact_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id", "")),
        "run_id": str(row.get("run_id", "")),
        "artifact_type": _legacy_artifact_type_from_row(row),
        "filename": _artifact_filename_from_row(row),
        "storage_bucket": str(row.get("storage_bucket") or "").strip(),
        "storage_key": str(row.get("storage_path") or row.get("storage_key") or "").strip(),
        "size_bytes": _artifact_int_meta(row, "size_bytes"),
        "sheet_index": _artifact_int_meta(row, "sheet_index"),
        "created_at": row.get("created_at"),
    }


def _to_artifact_response(row: dict[str, Any]) -> RunArtifactResponse:
    return RunArtifactResponse(
        id=str(row.get("id", "")),
        run_id=str(row.get("run_id", "")),
        artifact_type=str(row.get("artifact_type", "")),
        filename=str(row.get("filename", "")),
        storage_key=str(row.get("storage_key", "")),
        size_bytes=int(row.get("size_bytes")) if row.get("size_bytes") is not None else None,
        sheet_index=int(row.get("sheet_index")) if row.get("sheet_index") is not None else None,
        created_at=row.get("created_at"),
    )


def _fetch_run_artifacts(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: UUID,
    limit: int = 500,
) -> list[dict[str, Any]]:
    params = {
        "select": "id,run_id,artifact_kind,storage_bucket,storage_path,metadata_jsonb,created_at",
        "run_id": f"eq.{run_id}",
        "order": "created_at.asc",
        "limit": str(limit),
    }
    rows = supabase.select_rows(table="app.run_artifacts", access_token=access_token, params=params)
    return [_normalize_artifact_row(row) for row in rows]


def _artifact_download_link_path(project_id: UUID, run_id: UUID, artifact_id: str) -> str:
    return f"/v1/projects/{project_id}/runs/{run_id}/artifacts/{artifact_id}/download"


def _artifact_legacy_type(row: dict[str, Any]) -> str:
    metadata = row.get("metadata_jsonb")
    if not isinstance(metadata, dict):
        return ""
    value = metadata.get("legacy_artifact_type")
    return str(value or "").strip()


def _ensure_project_access(*, supabase: SupabaseClient, access_token: str, user_id: str, project_id: UUID) -> None:
    params = {
        "select": "id",
        "id": f"eq.{project_id}",
        "owner_user_id": f"eq.{user_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.projects", access_token=access_token, params=params)
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")


def _fetch_run_row(*, supabase: SupabaseClient, access_token: str, run_id: UUID, project_id: UUID) -> dict[str, Any]:
    params = {
        "select": "id,project_id,run_config_id,triggered_by:requested_by,status,queued_at,started_at,finished_at,duration_sec,solver_exit_code,error_message,placements_count,unplaced_count,sheet_count",
        "id": f"eq.{run_id}",
        "project_id": f"eq.{project_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.nesting_runs", access_token=access_token, params=params)
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    return rows[0]


@router.post("", response_model=RunResponse)
def create_run(
    project_id: UUID,
    req: RunCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
    settings: Settings = Depends(get_settings),
) -> RunResponse:
    _ensure_project_access(supabase=supabase, access_token=user.access_token, user_id=user.id, project_id=project_id)
    enforce_user_rate_limit(
        supabase=supabase,
        access_token=user.access_token,
        user_id=user.id,
        table="app.nesting_runs",
        timestamp_field="queued_at",
        limit=settings.rate_limit_runs_per_window,
        window_seconds=settings.rate_limit_window_s,
        route_key="POST /v1/projects/{project_id}/runs",
        filters={
            "requested_by": f"eq.{user.id}",
            "project_id": f"eq.{project_id}",
        },
    )

    try:
        result = create_queued_run_from_project_snapshot(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            project_id=str(project_id),
            run_purpose=req.run_purpose,
            idempotency_key=req.idempotency_key,
            time_limit_s=req.time_limit_s,
            sa_eval_budget_sec=req.sa_eval_budget_sec,
        )
    except RunCreationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="create run", exc=exc)
    run_row = result.get("run")
    if not isinstance(run_row, dict):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="run creation returned invalid payload")
    return _to_run_response(run_row)


@router.get("", response_model=RunListResponse)
def list_runs(
    project_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: Literal["queued", "running", "done", "failed", "cancelled"] | None = Query(default=None, alias="status"),
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> RunListResponse:
    _ensure_project_access(supabase=supabase, access_token=user.access_token, user_id=user.id, project_id=project_id)

    params = {
        "select": "id,project_id,run_config_id,triggered_by:requested_by,status,queued_at,started_at,finished_at,duration_sec,solver_exit_code,error_message,placements_count,unplaced_count,sheet_count",
        "project_id": f"eq.{project_id}",
        "order": "queued_at.desc",
        "limit": str(page_size),
        "offset": str((page - 1) * page_size),
    }
    if status_filter:
        params["status"] = f"eq.{status_filter}"

    try:
        rows = supabase.select_rows(table="app.nesting_runs", access_token=user.access_token, params=params)
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="list runs", exc=exc)

    items = [_to_run_response(row) for row in rows]
    return RunListResponse(items=items, total=len(items), page=page, page_size=page_size)


@router.get("/{run_id}", response_model=RunResponse)
def get_run(
    project_id: UUID,
    run_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> RunResponse:
    _ensure_project_access(supabase=supabase, access_token=user.access_token, user_id=user.id, project_id=project_id)

    try:
        row = _fetch_run_row(supabase=supabase, access_token=user.access_token, run_id=run_id, project_id=project_id)
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="get run", exc=exc)
    return _to_run_response(row)


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def cancel_run(
    project_id: UUID,
    run_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> Response:
    _ensure_project_access(supabase=supabase, access_token=user.access_token, user_id=user.id, project_id=project_id)

    try:
        row = _fetch_run_row(supabase=supabase, access_token=user.access_token, run_id=run_id, project_id=project_id)
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="cancel run", exc=exc)

    run_status = str(row.get("status", "")).strip().lower()
    if run_status in _TERMINAL_STATES:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    if run_status == "queued":
        payload = {
            "status": "cancelled",
            "finished_at": _now_iso(),
            "error_message": "cancelled by user",
        }
    elif run_status == "running":
        payload = {
            "status": "cancelled",
            "error_message": "cancel requested by user",
        }
    else:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"run cannot be cancelled from status={run_status}")

    try:
        supabase.update_rows(
            table="app.nesting_runs",
            access_token=user.access_token,
            payload=payload,
            filters={"id": f"eq.{run_id}", "project_id": f"eq.{project_id}"},
        )
        if run_status == "queued":
            supabase.delete_rows(table="app.run_queue", access_token=user.access_token, filters={"run_id": f"eq.{run_id}"})
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="cancel run", exc=exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{run_id}/rerun", response_model=RunResponse)
def rerun(
    project_id: UUID,
    run_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> RunResponse:
    _ensure_project_access(supabase=supabase, access_token=user.access_token, user_id=user.id, project_id=project_id)

    try:
        source = _fetch_run_row(supabase=supabase, access_token=user.access_token, run_id=run_id, project_id=project_id)
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="rerun", exc=exc)

    source_cfg = source.get("run_config_id")
    if source_cfg is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="source run has no run_config_id")

    try:
        new_row = _insert_run_and_queue_with_quota(
            supabase=supabase,
            access_token=user.access_token,
            project_id=project_id,
            triggered_by=user.id,
            run_config_id=str(source_cfg),
        )
    except SupabaseHTTPError as exc:
        if _is_quota_exceeded_error(exc):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "monthly_run_quota_exceeded",
                    "message": "Monthly run quota exceeded. Please retry next month or increase your plan quota.",
                },
            ) from exc
        raise_supabase_http_error(operation="rerun", exc=exc)
    return _to_run_response(new_row)


@router.get("/{run_id}/log", response_model=RunLogResponse)
def get_run_log(
    project_id: UUID,
    run_id: UUID,
    offset: int = Query(default=0, ge=0),
    lines: int = Query(default=100, ge=1, le=1000),
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
    settings: Settings = Depends(get_settings),
) -> RunLogResponse:
    _ensure_project_access(supabase=supabase, access_token=user.access_token, user_id=user.id, project_id=project_id)

    try:
        run_row = _fetch_run_row(supabase=supabase, access_token=user.access_token, run_id=run_id, project_id=project_id)
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="get run log", exc=exc)

    run_status = str(run_row.get("status", "")).strip().lower()

    params = {
        "select": "id,storage_bucket,storage_path,metadata_jsonb,created_at",
        "run_id": f"eq.{run_id}",
        "artifact_kind": "eq.log",
        "order": "created_at.desc",
        "limit": "20",
    }

    try:
        rows = supabase.select_rows(table="app.run_artifacts", access_token=user.access_token, params=params)
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="get run log", exc=exc)

    if not rows:
        return RunLogResponse(
            lines=[],
            total_lines=0,
            next_offset=offset,
            run_status=run_status,
            stop_polling=run_status in _TERMINAL_STATES,
        )

    selected_row = rows[0]
    for row in rows:
        if _artifact_legacy_type(row) == "run_log":
            selected_row = row
            break

    storage_key = str(selected_row.get("storage_path", "")).strip()
    storage_bucket = str(selected_row.get("storage_bucket") or "").strip() or settings.storage_bucket
    if not storage_key:
        return RunLogResponse(
            lines=[],
            total_lines=0,
            next_offset=offset,
            run_status=run_status,
            stop_polling=run_status in _TERMINAL_STATES,
        )

    try:
        signed = supabase.create_signed_download_url(
            access_token=user.access_token,
            bucket=storage_bucket,
            object_key=storage_key,
            expires_in=settings.signed_url_ttl_s,
        )
        blob = supabase.download_signed_object(signed_url=str(signed["download_url"]))
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="get run log", exc=exc)

    all_lines = blob.decode("utf-8", errors="replace").splitlines()
    total = len(all_lines)
    if offset > total:
        offset = total
    end = min(total, offset + lines)

    line_items: list[RunLogLine] = []
    for idx in range(offset, end):
        line_items.append(RunLogLine(line_no=idx, text=all_lines[idx]))

    return RunLogResponse(
        lines=line_items,
        total_lines=total,
        next_offset=end,
        run_status=run_status,
        stop_polling=run_status in _TERMINAL_STATES,
    )


@router.get("/{run_id}/artifacts", response_model=RunArtifactListResponse)
def list_run_artifacts(
    project_id: UUID,
    run_id: UUID,
    limit: int = Query(default=200, ge=1, le=500),
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> RunArtifactListResponse:
    _ensure_project_access(supabase=supabase, access_token=user.access_token, user_id=user.id, project_id=project_id)
    _fetch_run_row(supabase=supabase, access_token=user.access_token, run_id=run_id, project_id=project_id)

    try:
        rows = _fetch_run_artifacts(supabase=supabase, access_token=user.access_token, run_id=run_id, limit=limit)
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="list artifacts", exc=exc)

    items = [_to_artifact_response(row) for row in rows]
    return RunArtifactListResponse(items=items, total=len(items))


def _resolve_artifact_for_run(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: UUID,
    artifact_id: UUID,
) -> dict[str, Any]:
    params = {
        "select": "id,run_id,artifact_kind,storage_bucket,storage_path,metadata_jsonb,created_at",
        "id": f"eq.{artifact_id}",
        "run_id": f"eq.{run_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.run_artifacts", access_token=access_token, params=params)
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="artifact not found")
    return _normalize_artifact_row(rows[0])


@router.get("/{run_id}/artifacts/{artifact_id}/url", response_model=ArtifactUrlResponse)
def get_artifact_url(
    project_id: UUID,
    run_id: UUID,
    artifact_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
    settings: Settings = Depends(get_settings),
) -> ArtifactUrlResponse:
    _ensure_project_access(supabase=supabase, access_token=user.access_token, user_id=user.id, project_id=project_id)
    _fetch_run_row(supabase=supabase, access_token=user.access_token, run_id=run_id, project_id=project_id)

    try:
        artifact = _resolve_artifact_for_run(
            supabase=supabase,
            access_token=user.access_token,
            run_id=run_id,
            artifact_id=artifact_id,
        )
        storage_bucket = str(artifact.get("storage_bucket") or "").strip() or settings.storage_bucket
        signed = supabase.create_signed_download_url(
            access_token=user.access_token,
            bucket=storage_bucket,
            object_key=str(artifact.get("storage_key", "")),
            expires_in=settings.signed_url_ttl_s,
        )
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="artifact url", exc=exc)

    return ArtifactUrlResponse(
        artifact_id=str(artifact.get("id", "")),
        filename=str(artifact.get("filename", "")),
        download_url=str(signed["download_url"]),
        expires_at=str(signed["expires_at"]),
    )


@router.get("/{run_id}/artifacts/{artifact_id}/download")
def download_artifact_proxy(
    project_id: UUID,
    run_id: UUID,
    artifact_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    artifact_url = get_artifact_url(
        project_id=project_id,
        run_id=run_id,
        artifact_id=artifact_id,
        user=user,
        supabase=supabase,
        settings=settings,
    )
    return RedirectResponse(url=artifact_url.download_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


def _parse_solver_input_part_sizes(payload: dict[str, Any]) -> dict[str, tuple[float, float]]:
    out: dict[str, tuple[float, float]] = {}
    parts = payload.get("parts")
    if not isinstance(parts, list):
        return out
    for item in parts:
        if not isinstance(item, dict):
            continue
        part_id = str(item.get("id", "")).strip()
        if not part_id:
            continue
        width = float(item.get("width") or item.get("width_mm") or 0.0)
        height = float(item.get("height") or item.get("height_mm") or 0.0)
        if width <= 0 or height <= 0:
            inferred = _sheet_size_from_outer_points(item.get("outer_points_mm"))
            if inferred is None:
                inferred = _sheet_size_from_outer_points(item.get("outer_points"))
            if inferred is not None:
                width, height = inferred
        if width <= 0 or height <= 0:
            continue
        out[part_id] = (width, height)
    return out


def _sheet_size_from_outer_points(points: Any) -> tuple[float, float] | None:
    if not isinstance(points, list) or len(points) < 3:
        return None
    xs: list[float] = []
    ys: list[float] = []
    for point in points:
        if not isinstance(point, list) or len(point) < 2:
            continue
        try:
            xs.append(float(point[0]))
            ys.append(float(point[1]))
        except (TypeError, ValueError):
            continue
    if len(xs) < 3 or len(ys) < 3:
        return None
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    if width <= 0 or height <= 0:
        return None
    return width, height


def _coerce_positive_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed <= 0:
        return None
    return parsed


def _coerce_nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return None
    return parsed


def _coerce_int(value: Any, *, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_float(value: Any, *, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _artifact_basename(filename: str) -> str:
    value = str(filename or "").strip()
    if not value:
        return ""
    return value.split("/")[-1]


def _stable_sorted_artifacts(artifact_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    indexed = list(enumerate(artifact_rows))
    indexed.sort(
        key=lambda item: (
            str(item[1].get("created_at") or ""),
            _artifact_basename(str(item[1].get("filename") or "")).lower(),
            str(item[1].get("artifact_type") or "").strip().lower(),
            str(item[1].get("id") or "").strip(),
            item[0],
        )
    )
    return [row for _, row in indexed]


def _ordered_solver_input_artifacts(artifact_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[tuple[tuple[int, int, str, str], dict[str, Any]]] = []
    for row in _stable_sorted_artifacts(artifact_rows):
        artifact_type = str(row.get("artifact_type") or "").strip().lower()
        basename = _artifact_basename(str(row.get("filename") or "")).lower()
        if artifact_type != "solver_input" and basename != "solver_input.json":
            continue
        score = (
            0 if basename == "solver_input.json" else 1,
            0 if artifact_type == "solver_input" else 1,
            basename,
            str(row.get("id") or ""),
        )
        candidates.append((score, row))
    candidates.sort(key=lambda item: item[0])
    return [row for _, row in candidates]


def _ordered_engine_meta_artifacts(artifact_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[tuple[tuple[int, int, str, str], dict[str, Any]]] = []
    for row in _stable_sorted_artifacts(artifact_rows):
        artifact_type = str(row.get("artifact_type") or "").strip().lower()
        basename = _artifact_basename(str(row.get("filename") or "")).lower()
        if artifact_type != "engine_meta" and basename != "engine_meta.json":
            continue
        score = (
            0 if basename == "engine_meta.json" else 1,
            0 if artifact_type == "engine_meta" else 1,
            basename,
            str(row.get("id") or ""),
        )
        candidates.append((score, row))
    candidates.sort(key=lambda item: item[0])
    return [row for _, row in candidates]


def _output_kind_from_row(row: dict[str, Any]) -> str | None:
    artifact_type = str(row.get("artifact_type") or "").strip().lower()
    basename = _artifact_basename(str(row.get("filename") or "")).lower()
    if artifact_type == "nesting_output" or basename == "nesting_output.json":
        return "nesting_output"
    if artifact_type == "solver_output" or basename == "solver_output.json":
        return "solver_output"
    return None


def _ordered_solver_output_artifacts(
    artifact_rows: list[dict[str, Any]],
    *,
    engine_backend: str | None,
) -> list[tuple[str, dict[str, Any]]]:
    normalized_backend = str(engine_backend or "").strip().lower()
    preferred_kind: str | None = None
    if normalized_backend == "nesting_engine_v2":
        preferred_kind = "nesting_output"
    elif normalized_backend == "sparrow_v1":
        preferred_kind = "solver_output"

    candidates: list[tuple[tuple[int, int, int, str, str], str, dict[str, Any]]] = []
    for row in _stable_sorted_artifacts(artifact_rows):
        kind = _output_kind_from_row(row)
        if kind is None:
            continue
        basename = _artifact_basename(str(row.get("filename") or "")).lower()
        artifact_type = str(row.get("artifact_type") or "").strip().lower()
        if preferred_kind is not None:
            preferred_rank = 0 if kind == preferred_kind else 1
        else:
            preferred_rank = 0 if kind == "solver_output" else 1
        score = (
            preferred_rank,
            0 if basename == f"{kind}.json" else 1,
            0 if artifact_type == kind else 1,
            basename,
            str(row.get("id") or ""),
        )
        candidates.append((score, kind, row))
    candidates.sort(key=lambda item: item[0])
    return [(kind, row) for _, kind, row in candidates]


def _download_artifact_json(
    *,
    row: dict[str, Any],
    supabase: SupabaseClient,
    access_token: str,
    settings: Settings,
) -> dict[str, Any] | None:
    storage_key = str(row.get("storage_key") or "").strip()
    if not storage_key:
        return None
    try:
        artifact_bucket = str(row.get("storage_bucket") or "").strip() or settings.storage_bucket
        signed = supabase.create_signed_download_url(
            access_token=access_token,
            bucket=artifact_bucket,
            object_key=storage_key,
            expires_in=settings.signed_url_ttl_s,
        )
        blob = supabase.download_signed_object(signed_url=str(signed["download_url"]))
        parsed = json.loads(blob.decode("utf-8"))
    except (SupabaseHTTPError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _parse_solver_input_sheet_sizes(
    payload: dict[str, Any],
    *,
    sheet_count_hint: int = 0,
) -> dict[int, tuple[float, float]]:
    out: dict[int, tuple[float, float]] = {}
    stocks = payload.get("stocks")
    if isinstance(stocks, list):
        sheet_index = 0
        for item in stocks:
            if not isinstance(item, dict):
                continue
            qty = _coerce_positive_int(item.get("quantity")) or 0
            if qty <= 0:
                continue

            width = _coerce_float(item.get("width"), default=0.0)
            height = _coerce_float(item.get("height"), default=0.0)
            if width <= 0 or height <= 0:
                inferred = _sheet_size_from_outer_points(item.get("outer_points"))
                if inferred is None:
                    continue
                width, height = inferred

            for _ in range(qty):
                out[sheet_index] = (width, height)
                sheet_index += 1
        if out:
            return out

    sheet = payload.get("sheet")
    if not isinstance(sheet, dict):
        return out
    width = _coerce_float(sheet.get("width_mm"), default=0.0)
    height = _coerce_float(sheet.get("height_mm"), default=0.0)
    if width <= 0 or height <= 0:
        return out

    quantity = (
        _coerce_positive_int(sheet.get("quantity"))
        or _coerce_positive_int(sheet.get("required_qty"))
        or _coerce_positive_int(sheet.get("count"))
        or 1
    )
    target_count = max(quantity, max(int(sheet_count_hint), 0), 1)
    for idx in range(target_count):
        out[idx] = (width, height)
    return out


def _parse_solver_output(
    payload: dict[str, Any],
    *,
    part_sizes: dict[str, tuple[float, float]],
) -> tuple[list[ViewerPlacementResponse], list[ViewerUnplacedResponse], int]:
    placements: list[ViewerPlacementResponse] = []
    max_sheet_index = -1
    for item in payload.get("placements", []) if isinstance(payload.get("placements"), list) else []:
        if not isinstance(item, dict):
            continue
        part_id = str(item.get("part_id", "")).strip()
        part_width, part_height = part_sizes.get(part_id, (10.0, 10.0))
        instance_id = str(item.get("instance_id", "")).strip()
        if not instance_id:
            instance_raw = item.get("instance")
            if instance_raw is not None:
                if part_id:
                    instance_id = f"{part_id}:{_coerce_int(instance_raw, default=0)}"
                else:
                    instance_id = str(_coerce_int(instance_raw, default=0))
        sheet_index = _coerce_nonnegative_int(item.get("sheet_index"))
        if sheet_index is None:
            sheet_index = _coerce_int(item.get("sheet"), default=0)
        max_sheet_index = max(max_sheet_index, int(sheet_index))
        placements.append(
            ViewerPlacementResponse(
                instance_id=instance_id,
                part_id=part_id,
                sheet_index=int(sheet_index),
                x=_coerce_float(item.get("x_mm"), default=_coerce_float(item.get("x"), default=0.0)),
                y=_coerce_float(item.get("y_mm"), default=_coerce_float(item.get("y"), default=0.0)),
                rotation_deg=_coerce_float(item.get("rotation_deg"), default=0.0),
                width_mm=part_width,
                height_mm=part_height,
            )
        )

    unplaced: list[ViewerUnplacedResponse] = []
    for item in payload.get("unplaced", []) if isinstance(payload.get("unplaced"), list) else []:
        if not isinstance(item, dict):
            continue
        part_id = str(item.get("part_id", "")).strip()
        instance_id = str(item.get("instance_id", "")).strip()
        if not instance_id:
            instance_raw = item.get("instance")
            if instance_raw is not None:
                if part_id:
                    instance_id = f"{part_id}:{_coerce_int(instance_raw, default=0)}"
                else:
                    instance_id = str(_coerce_int(instance_raw, default=0))
        unplaced.append(
            ViewerUnplacedResponse(
                instance_id=instance_id,
                part_id=part_id,
                reason=str(item.get("reason", "")) or None,
            )
        )
    objective = payload.get("objective")
    objective_sheets_used = _coerce_int(objective.get("sheets_used"), default=0) if isinstance(objective, dict) else 0
    sheets_used = max(
        _coerce_int(payload.get("sheets_used"), default=0),
        objective_sheets_used,
        max_sheet_index + 1 if max_sheet_index >= 0 else 0,
    )
    return placements, unplaced, sheets_used


@router.get("/{run_id}/viewer-data", response_model=ViewerDataResponse)
def get_viewer_data(
    project_id: UUID,
    run_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
    settings: Settings = Depends(get_settings),
) -> ViewerDataResponse:
    _ensure_project_access(supabase=supabase, access_token=user.access_token, user_id=user.id, project_id=project_id)
    run_row = _fetch_run_row(supabase=supabase, access_token=user.access_token, run_id=run_id, project_id=project_id)

    try:
        artifact_rows = _fetch_run_artifacts(supabase=supabase, access_token=user.access_token, run_id=run_id, limit=500)
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="viewer-data", exc=exc)

    by_sheet: dict[int, dict[str, Any]] = {}
    solver_payload: dict[str, Any] = {}
    solver_input_payload: dict[str, Any] = {}
    engine_meta_payload: dict[str, Any] = {}
    input_artifact_source = "unknown"
    output_artifact_filename: str | None = None
    output_artifact_kind: str | None = None

    for row in artifact_rows:
        artifact_id = str(row.get("id", ""))
        filename = str(row.get("filename", ""))
        sheet_index = row.get("sheet_index")
        artifact_type = str(row.get("artifact_type", ""))

        effective_sheet: int | None = int(sheet_index) if sheet_index is not None else None
        if effective_sheet is None and filename.startswith("out/sheet_"):
            stem = filename.split("/")[-1].split(".")[0]
            token = stem.split("_", 1)[1] if "_" in stem else ""
            if token.isdigit():
                effective_sheet = int(token) - 1

        if effective_sheet is not None:
            slot = by_sheet.setdefault(
                effective_sheet,
                {"dxf_artifact_id": None, "svg_artifact_id": None, "dxf_filename": None, "svg_filename": None},
            )
            if artifact_type == "sheet_dxf" or (artifact_type == "" and filename.startswith("out/sheet_") and filename.endswith(".dxf")):
                slot["dxf_artifact_id"] = artifact_id
                slot["dxf_filename"] = filename
            if artifact_type == "sheet_svg" or (artifact_type == "" and filename.startswith("out/sheet_") and filename.endswith(".svg")):
                slot["svg_artifact_id"] = artifact_id
                slot["svg_filename"] = filename

    for row in _ordered_engine_meta_artifacts(artifact_rows):
        parsed = _download_artifact_json(row=row, supabase=supabase, access_token=user.access_token, settings=settings)
        if parsed is not None:
            engine_meta_payload = parsed
            break

    engine_backend = str(engine_meta_payload.get("engine_backend") or "").strip() or None
    for row in _ordered_solver_output_artifacts(artifact_rows, engine_backend=engine_backend):
        output_kind, output_row = row
        parsed = _download_artifact_json(
            row=output_row,
            supabase=supabase,
            access_token=user.access_token,
            settings=settings,
        )
        if parsed is None:
            continue
        solver_payload = parsed
        output_artifact_kind = output_kind
        output_artifact_filename = _artifact_basename(str(output_row.get("filename") or "")) or None
        break

    for row in _ordered_solver_input_artifacts(artifact_rows):
        parsed = _download_artifact_json(row=row, supabase=supabase, access_token=user.access_token, settings=settings)
        if parsed is not None:
            solver_input_payload = parsed
            input_artifact_source = "artifact"
            break

    # Deterministic fallback: if no solver_input artifact was found in the
    # run_artifacts table, attempt to read from the well-known snapshot storage
    # path that the worker uploads for every run.  This covers older runs
    # created before the worker registered solver_input as a formal artifact.
    if not solver_input_payload:
        _snapshot_key = f"runs/{run_id}/inputs/solver_input_snapshot.json"
        try:
            signed = supabase.create_signed_download_url(
                access_token=user.access_token,
                bucket=settings.storage_bucket,
                object_key=_snapshot_key,
                expires_in=settings.signed_url_ttl_s,
            )
            blob = supabase.download_signed_object(signed_url=str(signed["download_url"]))
            parsed = json.loads(blob.decode("utf-8"))
            if isinstance(parsed, dict):
                solver_input_payload = parsed
                input_artifact_source = "snapshot_fallback"
        except (SupabaseHTTPError, json.JSONDecodeError, Exception):  # noqa: BLE001
            solver_input_payload = {}

    part_sizes = _parse_solver_input_part_sizes(solver_input_payload)
    placements, unplaced, parsed_sheets_used = _parse_solver_output(solver_payload, part_sizes=part_sizes)
    sheet_sizes = _parse_solver_input_sheet_sizes(
        solver_input_payload,
        sheet_count_hint=max(parsed_sheets_used, 0),
    )
    placements_per_sheet: dict[int, int] = {}
    area_per_sheet: dict[int, float] = {}
    for item in placements:
        placements_per_sheet[item.sheet_index] = placements_per_sheet.get(item.sheet_index, 0) + 1
        area_per_sheet[item.sheet_index] = area_per_sheet.get(item.sheet_index, 0.0) + (item.width_mm * item.height_mm)

    sheet_indices = sorted(
        set(by_sheet.keys())
        | set(placements_per_sheet.keys())
        | set(sheet_sizes.keys())
        | set(range(max(parsed_sheets_used, 0)))
    )
    sheets: list[ViewerSheetResponse] = []
    for idx in sheet_indices:
        slot = by_sheet.get(idx, {})
        dxf_artifact_id = slot.get("dxf_artifact_id")
        svg_artifact_id = slot.get("svg_artifact_id")

        dxf_download_path = _artifact_download_link_path(project_id, run_id, dxf_artifact_id) if dxf_artifact_id else None
        svg_download_path = _artifact_download_link_path(project_id, run_id, svg_artifact_id) if svg_artifact_id else None

        dxf_url: str | None = None
        dxf_url_expires_at: str | None = None
        if dxf_artifact_id:
            try:
                dxf_signed = get_artifact_url(
                    project_id=project_id,
                    run_id=run_id,
                    artifact_id=UUID(str(dxf_artifact_id)),
                    user=user,
                    supabase=supabase,
                    settings=settings,
                )
                dxf_url = dxf_signed.download_url
                dxf_url_expires_at = dxf_signed.expires_at
            except (HTTPException, ValueError):
                dxf_url = None
                dxf_url_expires_at = None

        svg_url: str | None = None
        svg_url_expires_at: str | None = None
        if svg_artifact_id:
            try:
                svg_signed = get_artifact_url(
                    project_id=project_id,
                    run_id=run_id,
                    artifact_id=UUID(str(svg_artifact_id)),
                    user=user,
                    supabase=supabase,
                    settings=settings,
                )
                svg_url = svg_signed.download_url
                svg_url_expires_at = svg_signed.expires_at
            except (HTTPException, ValueError):
                svg_url = None
                svg_url_expires_at = None

        width_mm: float | None = None
        height_mm: float | None = None
        utilization_pct: float | None = None
        if idx in sheet_sizes:
            width_mm, height_mm = sheet_sizes[idx]
            sheet_area = width_mm * height_mm
            if sheet_area > 0:
                utilization_pct = round((area_per_sheet.get(idx, 0.0) / sheet_area) * 100.0, 3)

        sheets.append(
            ViewerSheetResponse(
                sheet_index=idx,
                dxf_artifact_id=dxf_artifact_id,
                svg_artifact_id=svg_artifact_id,
                dxf_filename=slot.get("dxf_filename"),
                svg_filename=slot.get("svg_filename"),
                dxf_download_path=dxf_download_path,
                svg_download_path=svg_download_path,
                dxf_url=dxf_url,
                dxf_url_expires_at=dxf_url_expires_at,
                svg_url=svg_url,
                svg_url_expires_at=svg_url_expires_at,
                width_mm=width_mm,
                height_mm=height_mm,
                utilization_pct=utilization_pct,
                placements_count=placements_per_sheet.get(idx, 0),
            )
        )

    reported_sheet_count = int(run_row.get("sheet_count") or 0)
    computed_sheet_count = len(sheets)
    sheet_count = max(reported_sheet_count, computed_sheet_count)

    return ViewerDataResponse(
        run_id=str(run_id),
        status=str(run_row.get("status", "")),
        sheet_count=sheet_count,
        sheets=sheets,
        placements=placements,
        unplaced=unplaced,
        engine_backend=str(engine_meta_payload.get("engine_backend") or "").strip() or None,
        engine_contract_version=str(engine_meta_payload.get("engine_contract_version") or "").strip() or None,
        engine_profile=str(engine_meta_payload.get("engine_profile") or "").strip() or None,
        input_artifact_source=input_artifact_source,
        output_artifact_filename=output_artifact_filename,
        output_artifact_kind=output_artifact_kind,
    )


@router.post("/{run_id}/artifacts/bundle", response_model=BundleResponse)
def create_artifacts_bundle(
    project_id: UUID,
    run_id: UUID,
    req: BundleRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
    settings: Settings = Depends(get_settings),
) -> BundleResponse:
    _ensure_project_access(supabase=supabase, access_token=user.access_token, user_id=user.id, project_id=project_id)
    _fetch_run_row(supabase=supabase, access_token=user.access_token, run_id=run_id, project_id=project_id)
    enforce_user_rate_limit(
        supabase=supabase,
        access_token=user.access_token,
        user_id=user.id,
        table="app.run_artifacts",
        timestamp_field="created_at",
        limit=settings.rate_limit_bundles_per_window,
        window_seconds=settings.rate_limit_window_s,
        route_key="POST /v1/projects/{project_id}/runs/{run_id}/artifacts/bundle",
        filters={"artifact_kind": "eq.bundle_zip", "run_id": f"eq.{run_id}"},
    )

    try:
        artifact_rows = _fetch_run_artifacts(supabase=supabase, access_token=user.access_token, run_id=run_id, limit=500)
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="bundle build", exc=exc)

    if not artifact_rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="no artifacts available for bundle")

    selected_ids = {str(item) for item in req.artifact_ids}
    selected_rows = artifact_rows if not selected_ids else [row for row in artifact_rows if str(row.get("id", "")) in selected_ids]
    if not selected_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="selected artifacts not found")

    bundle_filename = f"bundle_{run_id}.zip"
    bundle_storage_key = f"runs/{run_id}/artifacts/{bundle_filename}"
    bundle_storage_bucket = str(selected_rows[0].get("storage_bucket") or "").strip() or settings.storage_bucket

    bundle_size = 0
    try:
        with tempfile.TemporaryDirectory(prefix=f"vrs_bundle_{str(run_id)[:8]}_") as temp_dir:
            temp_root = Path(temp_dir)
            zip_path = temp_root / bundle_filename

            with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
                used_names: set[str] = set()
                for index, row in enumerate(selected_rows):
                    storage_key = str(row.get("storage_key", ""))
                    filename = str(row.get("filename", "")).strip() or "artifact.bin"
                    arcname = filename.split("/")[-1]
                    if arcname in used_names:
                        base, dot, ext = arcname.partition(".")
                        suffix = 1
                        while f"{base}_{suffix}{dot}{ext}" in used_names:
                            suffix += 1
                        arcname = f"{base}_{suffix}{dot}{ext}"
                    used_names.add(arcname)

                    signed = supabase.create_signed_download_url(
                        access_token=user.access_token,
                        bucket=str(row.get("storage_bucket") or "").strip() or settings.storage_bucket,
                        object_key=storage_key,
                        expires_in=settings.signed_url_ttl_s,
                    )
                    source_path = temp_root / f"artifact_{index:04d}.bin"
                    supabase.download_signed_object_to_file(
                        signed_url=str(signed["download_url"]),
                        destination_path=str(source_path),
                    )
                    zf.write(source_path, arcname=arcname)
                    source_path.unlink(missing_ok=True)

            bundle_size = zip_path.stat().st_size
            upload_signed = supabase.create_signed_upload_url(
                access_token=user.access_token,
                bucket=bundle_storage_bucket,
                object_key=bundle_storage_key,
                expires_in=settings.signed_url_ttl_s,
            )
            supabase.upload_signed_object_from_file(
                signed_url=str(upload_signed["upload_url"]),
                file_path=str(zip_path),
                content_type="application/zip",
            )

        existing = supabase.select_rows(
            table="app.run_artifacts",
            access_token=user.access_token,
            params={
                "select": "id",
                "run_id": f"eq.{run_id}",
                "artifact_kind": "eq.bundle_zip",
            },
        )
        for row in existing:
            supabase.delete_rows(
                table="app.run_artifacts",
                access_token=user.access_token,
                filters={"id": f"eq.{row.get('id')}", "run_id": f"eq.{run_id}"},
            )
        inserted = supabase.insert_row(
            table="app.run_artifacts",
            access_token=user.access_token,
            payload={
                "run_id": str(run_id),
                "artifact_kind": "bundle_zip",
                "storage_bucket": bundle_storage_bucket,
                "storage_path": bundle_storage_key,
                "metadata_jsonb": {
                    "legacy_artifact_type": "bundle_zip",
                    "filename": bundle_filename,
                    "size_bytes": bundle_size,
                },
            },
        )
        signed_download = supabase.create_signed_download_url(
            access_token=user.access_token,
            bucket=bundle_storage_bucket,
            object_key=bundle_storage_key,
            expires_in=settings.signed_url_ttl_s,
        )
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="bundle build", exc=exc)

    return BundleResponse(
        artifact_id=str(inserted.get("id", "")),
        filename=bundle_filename,
        bundle_url=str(signed_download["download_url"]),
        expires_at=str(signed_download["expires_at"]),
    )
