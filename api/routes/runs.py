from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
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


class BundleRequest(BaseModel):
    artifact_ids: list[str] = Field(default_factory=list)


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
    dxf_url: str | None = None
    svg_url: str | None = None
    placements_count: int


class ViewerPlacementResponse(BaseModel):
    instance_id: str
    part_id: str
    sheet_index: int
    x: float
    y: float
    rotation_deg: float


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
    run_id: str,
) -> list[dict[str, Any]]:
    params = {
        "select": "id,run_id,artifact_type,filename,storage_key,size_bytes,sheet_index,created_at",
        "run_id": f"eq.{run_id}",
        "order": "created_at.asc",
    }
    return supabase.select_rows(table="run_artifacts", access_token=access_token, params=params)


def _artifact_download_link_path(project_id: str, run_id: str, artifact_id: str) -> str:
    return f"/v1/projects/{project_id}/runs/{run_id}/artifacts/{artifact_id}/download"


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


@router.get("/{run_id}/artifacts", response_model=RunArtifactListResponse)
def list_run_artifacts(
    project_id: str,
    run_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> RunArtifactListResponse:
    _ensure_project_access(supabase=supabase, access_token=user.access_token, user_id=user.id, project_id=project_id)
    _fetch_run_row(supabase=supabase, access_token=user.access_token, run_id=run_id, project_id=project_id)

    try:
        rows = _fetch_run_artifacts(supabase=supabase, access_token=user.access_token, run_id=run_id)
    except SupabaseHTTPError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"list artifacts failed: {exc}") from exc

    items = [_to_artifact_response(row) for row in rows]
    return RunArtifactListResponse(items=items, total=len(items))


def _resolve_artifact_for_run(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
    artifact_id: str,
) -> dict[str, Any]:
    params = {
        "select": "id,run_id,artifact_type,filename,storage_key,size_bytes,sheet_index,created_at",
        "id": f"eq.{artifact_id}",
        "run_id": f"eq.{run_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="run_artifacts", access_token=access_token, params=params)
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="artifact not found")
    return rows[0]


@router.get("/{run_id}/artifacts/{artifact_id}/url", response_model=ArtifactUrlResponse)
def get_artifact_url(
    project_id: str,
    run_id: str,
    artifact_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
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
        settings = get_settings()
        signed = supabase.create_signed_download_url(
            access_token=user.access_token,
            bucket=settings.storage_bucket,
            object_key=str(artifact.get("storage_key", "")),
            expires_in=900,
        )
    except SupabaseHTTPError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"artifact url failed: {exc}") from exc

    return ArtifactUrlResponse(
        artifact_id=str(artifact.get("id", "")),
        filename=str(artifact.get("filename", "")),
        download_url=str(signed["download_url"]),
        expires_at=str(signed["expires_at"]),
    )


@router.get("/{run_id}/artifacts/{artifact_id}/download")
def download_artifact_proxy(
    project_id: str,
    run_id: str,
    artifact_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> RedirectResponse:
    artifact_url = get_artifact_url(
        project_id=project_id,
        run_id=run_id,
        artifact_id=artifact_id,
        user=user,
        supabase=supabase,
    )
    return RedirectResponse(url=artifact_url.download_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


def _parse_solver_output(payload: dict[str, Any]) -> tuple[list[ViewerPlacementResponse], list[ViewerUnplacedResponse]]:
    placements: list[ViewerPlacementResponse] = []
    for item in payload.get("placements", []) if isinstance(payload.get("placements"), list) else []:
        if not isinstance(item, dict):
            continue
        placements.append(
            ViewerPlacementResponse(
                instance_id=str(item.get("instance_id", "")),
                part_id=str(item.get("part_id", "")),
                sheet_index=int(item.get("sheet_index", 0)),
                x=float(item.get("x", 0.0)),
                y=float(item.get("y", 0.0)),
                rotation_deg=float(item.get("rotation_deg", 0.0)),
            )
        )

    unplaced: list[ViewerUnplacedResponse] = []
    for item in payload.get("unplaced", []) if isinstance(payload.get("unplaced"), list) else []:
        if not isinstance(item, dict):
            continue
        unplaced.append(
            ViewerUnplacedResponse(
                instance_id=str(item.get("instance_id", "")),
                part_id=str(item.get("part_id", "")),
                reason=str(item.get("reason", "")) or None,
            )
        )
    return placements, unplaced


@router.get("/{run_id}/viewer-data", response_model=ViewerDataResponse)
def get_viewer_data(
    project_id: str,
    run_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> ViewerDataResponse:
    _ensure_project_access(supabase=supabase, access_token=user.access_token, user_id=user.id, project_id=project_id)
    run_row = _fetch_run_row(supabase=supabase, access_token=user.access_token, run_id=run_id, project_id=project_id)

    try:
        artifact_rows = _fetch_run_artifacts(supabase=supabase, access_token=user.access_token, run_id=run_id)
    except SupabaseHTTPError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"viewer-data failed: {exc}") from exc

    settings = get_settings()
    by_sheet: dict[int, dict[str, Any]] = {}
    solver_payload: dict[str, Any] = {}

    for row in artifact_rows:
        artifact_id = str(row.get("id", ""))
        filename = str(row.get("filename", ""))
        storage_key = str(row.get("storage_key", ""))
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
            if filename.endswith(".dxf"):
                slot["dxf_artifact_id"] = artifact_id
                slot["dxf_filename"] = filename
            if filename.endswith(".svg"):
                slot["svg_artifact_id"] = artifact_id
                slot["svg_filename"] = filename

        if artifact_type == "solver_output" or filename.endswith("solver_output.json"):
            try:
                signed = supabase.create_signed_download_url(
                    access_token=user.access_token,
                    bucket=settings.storage_bucket,
                    object_key=storage_key,
                    expires_in=900,
                )
                blob = supabase.download_signed_object(signed_url=str(signed["download_url"]))
                parsed = json.loads(blob.decode("utf-8"))
                if isinstance(parsed, dict):
                    solver_payload = parsed
            except (SupabaseHTTPError, json.JSONDecodeError):
                solver_payload = {}

    placements, unplaced = _parse_solver_output(solver_payload)
    placements_per_sheet: dict[int, int] = {}
    for item in placements:
        placements_per_sheet[item.sheet_index] = placements_per_sheet.get(item.sheet_index, 0) + 1

    sheet_indices = sorted(set(by_sheet.keys()) | set(placements_per_sheet.keys()))
    sheets: list[ViewerSheetResponse] = []
    for idx in sheet_indices:
        slot = by_sheet.get(idx, {})
        dxf_artifact_id = slot.get("dxf_artifact_id")
        svg_artifact_id = slot.get("svg_artifact_id")
        dxf_url = _artifact_download_link_path(project_id, run_id, dxf_artifact_id) if dxf_artifact_id else None
        svg_url = _artifact_download_link_path(project_id, run_id, svg_artifact_id) if svg_artifact_id else None
        sheets.append(
            ViewerSheetResponse(
                sheet_index=idx,
                dxf_artifact_id=dxf_artifact_id,
                svg_artifact_id=svg_artifact_id,
                dxf_filename=slot.get("dxf_filename"),
                svg_filename=slot.get("svg_filename"),
                dxf_url=dxf_url,
                svg_url=svg_url,
                placements_count=placements_per_sheet.get(idx, 0),
            )
        )

    reported_sheet_count = int(run_row.get("sheet_count") or 0)
    computed_sheet_count = len(sheets)
    sheet_count = max(reported_sheet_count, computed_sheet_count)

    return ViewerDataResponse(
        run_id=run_id,
        status=str(run_row.get("status", "")),
        sheet_count=sheet_count,
        sheets=sheets,
        placements=placements,
        unplaced=unplaced,
    )


@router.post("/{run_id}/artifacts/bundle", response_model=BundleResponse)
def create_artifacts_bundle(
    project_id: str,
    run_id: str,
    req: BundleRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> BundleResponse:
    _ensure_project_access(supabase=supabase, access_token=user.access_token, user_id=user.id, project_id=project_id)
    _fetch_run_row(supabase=supabase, access_token=user.access_token, run_id=run_id, project_id=project_id)

    try:
        artifact_rows = _fetch_run_artifacts(supabase=supabase, access_token=user.access_token, run_id=run_id)
    except SupabaseHTTPError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"bundle build failed: {exc}") from exc

    if not artifact_rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="no artifacts available for bundle")

    selected_ids = {item.strip() for item in req.artifact_ids if item.strip()}
    selected_rows = artifact_rows if not selected_ids else [row for row in artifact_rows if str(row.get("id", "")) in selected_ids]
    if not selected_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="selected artifacts not found")

    settings = get_settings()
    bundle_filename = f"bundle_{run_id}.zip"
    bundle_storage_key = f"runs/{run_id}/artifacts/{bundle_filename}"

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        used_names: set[str] = set()
        for row in selected_rows:
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
                bucket=settings.storage_bucket,
                object_key=storage_key,
                expires_in=900,
            )
            blob = supabase.download_signed_object(signed_url=str(signed["download_url"]))
            zf.writestr(arcname, blob)

    payload = zip_buffer.getvalue()
    try:
        upload_signed = supabase.create_signed_upload_url(
            access_token=user.access_token,
            bucket=settings.storage_bucket,
            object_key=bundle_storage_key,
            expires_in=900,
        )
        supabase.upload_signed_object(
            signed_url=str(upload_signed["upload_url"]),
            payload=payload,
            content_type="application/zip",
        )
        existing = supabase.select_rows(
            table="run_artifacts",
            access_token=user.access_token,
            params={
                "select": "id",
                "run_id": f"eq.{run_id}",
                "artifact_type": "eq.bundle_zip",
            },
        )
        for row in existing:
            supabase.delete_rows(
                table="run_artifacts",
                access_token=user.access_token,
                filters={"id": f"eq.{row.get('id')}", "run_id": f"eq.{run_id}"},
            )
        inserted = supabase.insert_row(
            table="run_artifacts",
            access_token=user.access_token,
            payload={
                "run_id": run_id,
                "artifact_type": "bundle_zip",
                "filename": bundle_filename,
                "storage_key": bundle_storage_key,
                "size_bytes": len(payload),
                "sheet_index": None,
            },
        )
        signed_download = supabase.create_signed_download_url(
            access_token=user.access_token,
            bucket=settings.storage_bucket,
            object_key=bundle_storage_key,
            expires_in=300,
        )
    except SupabaseHTTPError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"bundle build failed: {exc}") from exc

    return BundleResponse(
        artifact_id=str(inserted.get("id", "")),
        filename=bundle_filename,
        bundle_url=str(signed_download["download_url"]),
        expires_at=str(signed_download["expires_at"]),
    )
