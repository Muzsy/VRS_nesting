from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field, model_validator

from api.auth import AuthenticatedUser, get_current_user
from api.deps import get_settings, get_supabase_client
from api.routes.run_configs import RunConfigPartEntry
from api.supabase_client import SupabaseClient, SupabaseHTTPError


router = APIRouter(prefix="/projects/{project_id}/runs", tags=["runs"])


class InlineRunConfig(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    schema_version: str = Field(default="dxf_v1", max_length=40)
    seed: int = Field(default=0, ge=0)
    time_limit_s: int = Field(default=60, ge=1, le=3600)
    spacing_mm: float = Field(default=2.0, ge=0.0, le=100.0)
    margin_mm: float = Field(default=5.0, ge=0.0, le=100.0)
    stock_file_id: str = Field(min_length=1)
    parts_config: list[RunConfigPartEntry] = Field(min_length=1)


class RunCreateRequest(BaseModel):
    run_config_id: str | None = None
    config: InlineRunConfig | None = None

    @model_validator(mode="after")
    def _validate_source(self) -> "RunCreateRequest":
        if not self.run_config_id and self.config is None:
            raise ValueError("either run_config_id or config is required")
        return self


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
    return RunResponse(
        id=str(row.get("id", "")),
        project_id=str(row.get("project_id", "")),
        run_config_id=str(run_config_id_raw) if run_config_id_raw is not None else None,
        triggered_by=str(row.get("triggered_by", "")),
        status=str(row.get("status", "queued")),
        queued_at=row.get("queued_at"),
        started_at=row.get("started_at"),
        finished_at=row.get("finished_at"),
        duration_sec=float(row.get("duration_sec")) if row.get("duration_sec") is not None else None,
        solver_exit_code=int(row.get("solver_exit_code")) if row.get("solver_exit_code") is not None else None,
        error_message=row.get("error_message"),
        metrics=_parse_metrics(row),
    )


def _ensure_project_access(*, supabase: SupabaseClient, access_token: str, user_id: str, project_id: str) -> None:
    params = {
        "select": "id",
        "id": f"eq.{project_id}",
        "owner_id": f"eq.{user_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="projects", access_token=access_token, params=params)
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")


def _ensure_project_files_exist(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
    file_ids: set[str],
) -> None:
    if not file_ids:
        return
    joined = ",".join(sorted(file_ids))
    params = {
        "select": "id",
        "project_id": f"eq.{project_id}",
        "id": f"in.({joined})",
    }
    rows = supabase.select_rows(table="project_files", access_token=access_token, params=params)
    found = {str(row.get("id", "")).strip() for row in rows}
    missing = sorted(file_ids - found)
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"unknown project files: {', '.join(missing)}")


def _fetch_run_row(*, supabase: SupabaseClient, access_token: str, run_id: str, project_id: str) -> dict[str, Any]:
    params = {
        "select": "id,project_id,run_config_id,triggered_by,status,queued_at,started_at,finished_at,duration_sec,solver_exit_code,error_message,placements_count,unplaced_count,sheet_count",
        "id": f"eq.{run_id}",
        "project_id": f"eq.{project_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="runs", access_token=access_token, params=params)
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    return rows[0]


def _insert_run_and_queue(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
    triggered_by: str,
    run_config_id: str | None,
) -> dict[str, Any]:
    run_payload: dict[str, Any] = {
        "project_id": project_id,
        "triggered_by": triggered_by,
        "status": "queued",
        "queued_at": _now_iso(),
    }
    if run_config_id is not None:
        run_payload["run_config_id"] = run_config_id

    run_row = supabase.insert_row(table="runs", access_token=access_token, payload=run_payload)
    run_id = str(run_row.get("id", "")).strip()
    if not run_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="run insert returned empty id")

    try:
        supabase.insert_row(
            table="run_queue",
            access_token=access_token,
            payload={"run_id": run_id, "priority": 0, "attempts": 0, "max_attempts": 3},
        )
    except SupabaseHTTPError as exc:
        try:
            supabase.delete_rows(table="runs", access_token=access_token, filters={"id": f"eq.{run_id}"})
        except SupabaseHTTPError:
            pass
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"queue insert failed: {exc}") from exc

    return run_row


def _resolve_run_config_id(
    *,
    req: RunCreateRequest,
    project_id: str,
    user: AuthenticatedUser,
    supabase: SupabaseClient,
) -> str | None:
    if req.run_config_id:
        params = {
            "select": "id",
            "id": f"eq.{req.run_config_id}",
            "project_id": f"eq.{project_id}",
            "limit": "1",
        }
        rows = supabase.select_rows(table="run_configs", access_token=user.access_token, params=params)
        if not rows:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run-config not found")
        return str(rows[0].get("id", "")).strip()

    inline = req.config
    if inline is None:
        return None

    file_ids = {inline.stock_file_id}
    for entry in inline.parts_config:
        file_ids.add(entry.file_id)
    _ensure_project_files_exist(
        supabase=supabase,
        access_token=user.access_token,
        project_id=project_id,
        file_ids=file_ids,
    )

    payload = {
        "project_id": project_id,
        "created_by": user.id,
        "name": inline.name.strip() if inline.name else None,
        "schema_version": inline.schema_version.strip() or "dxf_v1",
        "seed": int(inline.seed),
        "time_limit_s": int(inline.time_limit_s),
        "spacing_mm": float(inline.spacing_mm),
        "margin_mm": float(inline.margin_mm),
        "stock_file_id": inline.stock_file_id,
        "parts_config": [entry.model_dump() for entry in inline.parts_config],
    }
    row = supabase.insert_row(table="run_configs", access_token=user.access_token, payload=payload)
    return str(row.get("id", "")).strip() or None


@router.post("", response_model=RunResponse)
def create_run(
    project_id: str,
    req: RunCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> RunResponse:
    _ensure_project_access(supabase=supabase, access_token=user.access_token, user_id=user.id, project_id=project_id)

    try:
        run_config_id = _resolve_run_config_id(req=req, project_id=project_id, user=user, supabase=supabase)
        run_row = _insert_run_and_queue(
            supabase=supabase,
            access_token=user.access_token,
            project_id=project_id,
            triggered_by=user.id,
            run_config_id=run_config_id,
        )
    except SupabaseHTTPError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"create run failed: {exc}") from exc
    return _to_run_response(run_row)


@router.get("", response_model=RunListResponse)
def list_runs(
    project_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> RunListResponse:
    _ensure_project_access(supabase=supabase, access_token=user.access_token, user_id=user.id, project_id=project_id)

    params = {
        "select": "id,project_id,run_config_id,triggered_by,status,queued_at,started_at,finished_at,duration_sec,solver_exit_code,error_message,placements_count,unplaced_count,sheet_count",
        "project_id": f"eq.{project_id}",
        "order": "queued_at.desc",
        "limit": str(page_size),
        "offset": str((page - 1) * page_size),
    }
    if status_filter:
        params["status"] = f"eq.{status_filter}"

    try:
        rows = supabase.select_rows(table="runs", access_token=user.access_token, params=params)
    except SupabaseHTTPError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"list runs failed: {exc}") from exc

    items = [_to_run_response(row) for row in rows]
    return RunListResponse(items=items, total=len(items), page=page, page_size=page_size)


@router.get("/{run_id}", response_model=RunResponse)
def get_run(
    project_id: str,
    run_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> RunResponse:
    _ensure_project_access(supabase=supabase, access_token=user.access_token, user_id=user.id, project_id=project_id)

    try:
        row = _fetch_run_row(supabase=supabase, access_token=user.access_token, run_id=run_id, project_id=project_id)
    except SupabaseHTTPError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"get run failed: {exc}") from exc
    return _to_run_response(row)


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def cancel_run(
    project_id: str,
    run_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> Response:
    _ensure_project_access(supabase=supabase, access_token=user.access_token, user_id=user.id, project_id=project_id)

    try:
        row = _fetch_run_row(supabase=supabase, access_token=user.access_token, run_id=run_id, project_id=project_id)
    except SupabaseHTTPError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"cancel run failed: {exc}") from exc

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
            table="runs",
            access_token=user.access_token,
            payload=payload,
            filters={"id": f"eq.{run_id}", "project_id": f"eq.{project_id}"},
        )
        if run_status == "queued":
            supabase.delete_rows(table="run_queue", access_token=user.access_token, filters={"run_id": f"eq.{run_id}"})
    except SupabaseHTTPError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"cancel run failed: {exc}") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{run_id}/rerun", response_model=RunResponse)
def rerun(
    project_id: str,
    run_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> RunResponse:
    _ensure_project_access(supabase=supabase, access_token=user.access_token, user_id=user.id, project_id=project_id)

    try:
        source = _fetch_run_row(supabase=supabase, access_token=user.access_token, run_id=run_id, project_id=project_id)
    except SupabaseHTTPError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"rerun failed: {exc}") from exc

    source_cfg = source.get("run_config_id")
    if source_cfg is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="source run has no run_config_id")

    try:
        new_row = _insert_run_and_queue(
            supabase=supabase,
            access_token=user.access_token,
            project_id=project_id,
            triggered_by=user.id,
            run_config_id=str(source_cfg),
        )
    except SupabaseHTTPError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"rerun failed: {exc}") from exc
    return _to_run_response(new_row)


@router.get("/{run_id}/log", response_model=RunLogResponse)
def get_run_log(
    project_id: str,
    run_id: str,
    offset: int = Query(default=0, ge=0),
    lines: int = Query(default=100, ge=1, le=1000),
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> RunLogResponse:
    _ensure_project_access(supabase=supabase, access_token=user.access_token, user_id=user.id, project_id=project_id)

    try:
        run_row = _fetch_run_row(supabase=supabase, access_token=user.access_token, run_id=run_id, project_id=project_id)
    except SupabaseHTTPError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"get run log failed: {exc}") from exc

    run_status = str(run_row.get("status", "")).strip().lower()

    params = {
        "select": "id,storage_key,created_at",
        "run_id": f"eq.{run_id}",
        "artifact_type": "eq.run_log",
        "order": "created_at.desc",
        "limit": "1",
    }

    try:
        rows = supabase.select_rows(table="run_artifacts", access_token=user.access_token, params=params)
    except SupabaseHTTPError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"get run log failed: {exc}") from exc

    if not rows:
        return RunLogResponse(
            lines=[],
            total_lines=0,
            next_offset=offset,
            run_status=run_status,
            stop_polling=run_status in _TERMINAL_STATES,
        )

    storage_key = str(rows[0].get("storage_key", "")).strip()
    if not storage_key:
        return RunLogResponse(
            lines=[],
            total_lines=0,
            next_offset=offset,
            run_status=run_status,
            stop_polling=run_status in _TERMINAL_STATES,
        )

    settings = get_settings()
    try:
        signed = supabase.create_signed_download_url(
            access_token=user.access_token,
            bucket=settings.storage_bucket,
            object_key=storage_key,
            expires_in=900,
        )
        blob = supabase.download_signed_object(signed_url=str(signed["download_url"]))
    except SupabaseHTTPError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"get run log failed: {exc}") from exc

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
