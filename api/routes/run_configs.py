from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from api.auth import AuthenticatedUser, get_current_user
from api.deps import get_supabase_client
from api.http_errors import raise_supabase_http_error
from api.request_models import StrictRequestModel
from api.supabase_client import SupabaseClient, SupabaseHTTPError
from vrs_nesting.config.nesting_quality_profiles import (
    compact_runtime_policy,
    normalize_quality_profile_name,
    validate_runtime_policy,
)


router = APIRouter(prefix="/projects/{project_id}/run-configs", tags=["run-configs"])

_ALLOWED_ROTATIONS = {0, 90, 180, 270}
_ALLOWED_ENGINE_BACKEND_HINTS = {"sparrow_v1", "nesting_engine_v2"}
_ALLOWED_SOLVER_OVERRIDE_KEYS = {
    "quality_profile",
    "sa_eval_budget_sec",
    "nesting_engine_runtime_policy",
    "engine_backend_hint",
}


class RunConfigPartEntry(StrictRequestModel):
    file_id: UUID
    quantity: int = Field(default=1, ge=1, le=10000)
    allowed_rotations_deg: list[int] = Field(default_factory=lambda: [0, 90, 180, 270])


class RunConfigCreateRequest(StrictRequestModel):
    name: str | None = Field(default=None, max_length=120)
    schema_version: str = Field(default="dxf_v1", max_length=40)
    seed: int = Field(default=0, ge=0)
    time_limit_s: int = Field(default=60, ge=1, le=3600)
    spacing_mm: float = Field(default=2.0, ge=0.0, le=100.0)
    margin_mm: float = Field(default=5.0, ge=0.0, le=100.0)
    stock_file_id: UUID
    parts_config: list[RunConfigPartEntry] = Field(min_length=1, max_length=500)
    run_strategy_profile_version_id: UUID | None = None
    solver_config_overrides_jsonb: dict[str, Any] | None = None


class RunConfigResponse(BaseModel):
    id: str
    project_id: str
    created_by: str
    name: str | None = None
    schema_version: str
    seed: int
    time_limit_s: int
    spacing_mm: float
    margin_mm: float
    stock_file_id: str | None = None
    parts_config: list[RunConfigPartEntry]
    run_strategy_profile_version_id: str | None = None
    solver_config_overrides_jsonb: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None


class RunConfigListResponse(BaseModel):
    items: list[RunConfigResponse]
    total: int


def _parse_parts_config(raw: Any) -> list[RunConfigPartEntry]:
    out: list[RunConfigPartEntry] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if isinstance(item, dict):
            try:
                out.append(
                    RunConfigPartEntry(
                        file_id=UUID(str(item.get("file_id", "")).strip()),
                        quantity=int(item.get("quantity") or 1),
                        allowed_rotations_deg=[int(v) for v in (item.get("allowed_rotations_deg") or [0, 90, 180, 270])],
                    )
                )
            except (TypeError, ValueError):
                continue
    return out


def _to_response(payload: dict[str, Any]) -> RunConfigResponse:
    raw_overrides = payload.get("solver_config_overrides_jsonb")
    solver_overrides = raw_overrides if isinstance(raw_overrides, dict) else {}
    return RunConfigResponse(
        id=str(payload.get("id", "")),
        project_id=str(payload.get("project_id", "")),
        created_by=str(payload.get("created_by", "")),
        name=payload.get("name"),
        schema_version=str(payload.get("schema_version", "dxf_v1")),
        seed=int(payload.get("seed") or 0),
        time_limit_s=int(payload.get("time_limit_s") or 60),
        spacing_mm=float(payload.get("spacing_mm") or 0.0),
        margin_mm=float(payload.get("margin_mm") or 0.0),
        stock_file_id=str(payload.get("stock_file_id")) if payload.get("stock_file_id") is not None else None,
        parts_config=_parse_parts_config(payload.get("parts_config")),
        run_strategy_profile_version_id=(
            str(payload.get("run_strategy_profile_version_id"))
            if payload.get("run_strategy_profile_version_id") is not None
            else None
        ),
        solver_config_overrides_jsonb=solver_overrides,
        created_at=payload.get("created_at"),
    )


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


def _ensure_project_files_exist(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: UUID,
    file_ids: set[UUID],
) -> None:
    if not file_ids:
        return
    joined = ",".join(sorted(str(file_id) for file_id in file_ids))
    params = {
        "select": "id",
        "project_id": f"eq.{project_id}",
        "id": f"in.({joined})",
    }
    rows = supabase.select_rows(table="app.file_objects", access_token=access_token, params=params)
    found: set[UUID] = set()
    for row in rows:
        try:
            found.add(UUID(str(row.get("id", "")).strip()))
        except (TypeError, ValueError):
            continue
    missing = sorted(file_ids - found)
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"unknown project files: {', '.join(str(item) for item in missing)}")


def _validate_rotations(parts: list[RunConfigPartEntry]) -> None:
    for entry in parts:
        values = entry.allowed_rotations_deg or [0, 90, 180, 270]
        if not all(value in _ALLOWED_ROTATIONS for value in values):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid allowed_rotations_deg value")


def _normalize_bool(raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        cleaned = raw.strip().lower()
        if cleaned in {"true", "t", "1", "yes", "y"}:
            return True
        if cleaned in {"false", "f", "0", "no", "n"}:
            return False
    if isinstance(raw, (int, float)):
        return bool(raw)
    return bool(raw)


def _validate_strategy_version_for_owner(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    version_id: str,
) -> None:
    params = {
        "select": "id,owner_user_id,is_active",
        "id": f"eq.{version_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.run_strategy_profile_versions", access_token=access_token, params=params)
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run strategy profile version not found")
    row = rows[0]
    version_owner = str(row.get("owner_user_id") or "").strip()
    if version_owner != owner_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="run strategy profile version does not belong to owner")
    if "is_active" in row and not _normalize_bool(row.get("is_active")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="run strategy profile version is inactive")


def _parse_sa_eval_budget_sec(raw: Any) -> int:
    if isinstance(raw, bool):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid solver override sa_eval_budget_sec")
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid solver override sa_eval_budget_sec") from exc
    if value < 1 or value > 3600:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid solver override sa_eval_budget_sec")
    return value


def _normalize_engine_backend_hint(raw: Any) -> str:
    value = str(raw or "").strip().lower()
    if value not in _ALLOWED_ENGINE_BACKEND_HINTS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid solver override engine_backend_hint")
    return value


def _normalize_solver_config_overrides(raw: dict[str, Any] | None) -> dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="solver_config_overrides_jsonb must be an object")
    out: dict[str, Any] = {}
    for key, value in raw.items():
        if key not in _ALLOWED_SOLVER_OVERRIDE_KEYS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"unsupported solver override key: {key}")
        if key == "quality_profile":
            if not isinstance(value, str) or not value.strip():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid solver override quality_profile")
            try:
                out[key] = normalize_quality_profile_name(value)
            except ValueError as exc:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
            continue
        if key == "sa_eval_budget_sec":
            out[key] = _parse_sa_eval_budget_sec(value)
            continue
        if key == "nesting_engine_runtime_policy":
            if not isinstance(value, dict):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid solver override nesting_engine_runtime_policy")
            try:
                out[key] = compact_runtime_policy(validate_runtime_policy(value))
            except ValueError as exc:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
            continue
        if key == "engine_backend_hint":
            out[key] = _normalize_engine_backend_hint(value)
            continue
    return out


@router.post("", response_model=RunConfigResponse)
def create_run_config(
    project_id: UUID,
    req: RunConfigCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> RunConfigResponse:
    _ensure_project_access(supabase=supabase, access_token=user.access_token, user_id=user.id, project_id=project_id)
    _validate_rotations(req.parts_config)
    strategy_version_id = str(req.run_strategy_profile_version_id) if req.run_strategy_profile_version_id is not None else None
    if strategy_version_id is not None:
        _validate_strategy_version_for_owner(
            supabase=supabase,
            access_token=user.access_token,
            owner_user_id=user.id,
            version_id=strategy_version_id,
        )
    solver_config_overrides = _normalize_solver_config_overrides(req.solver_config_overrides_jsonb)

    file_ids: set[UUID] = {req.stock_file_id}
    for entry in req.parts_config:
        file_ids.add(entry.file_id)
    _ensure_project_files_exist(
        supabase=supabase,
        access_token=user.access_token,
        project_id=project_id,
        file_ids=file_ids,
    )

    payload = {
        "project_id": str(project_id),
        "created_by": user.id,
        "name": req.name.strip() if req.name else None,
        "schema_version": req.schema_version.strip() or "dxf_v1",
        "seed": int(req.seed),
        "time_limit_s": int(req.time_limit_s),
        "spacing_mm": float(req.spacing_mm),
        "margin_mm": float(req.margin_mm),
        "stock_file_id": str(req.stock_file_id),
        "parts_config": [
            {
                "file_id": str(entry.file_id),
                "quantity": int(entry.quantity),
                "allowed_rotations_deg": [int(v) for v in entry.allowed_rotations_deg],
            }
            for entry in req.parts_config
        ],
        "run_strategy_profile_version_id": strategy_version_id,
        "solver_config_overrides_jsonb": solver_config_overrides,
    }

    try:
        row = supabase.insert_row(table="app.run_configs", access_token=user.access_token, payload=payload)
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="create run-config", exc=exc)
    return _to_response(row)


@router.get("", response_model=RunConfigListResponse)
def list_run_configs(
    project_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> RunConfigListResponse:
    _ensure_project_access(supabase=supabase, access_token=user.access_token, user_id=user.id, project_id=project_id)

    params = {
        "select": (
            "id,project_id,created_by,name,schema_version,seed,time_limit_s,spacing_mm,margin_mm,"
            "stock_file_id,parts_config,run_strategy_profile_version_id,solver_config_overrides_jsonb,created_at"
        ),
        "project_id": f"eq.{project_id}",
        "order": "created_at.desc",
        "limit": str(limit),
    }
    try:
        rows = supabase.select_rows(table="app.run_configs", access_token=user.access_token, params=params)
    except SupabaseHTTPError as exc:
        raise_supabase_http_error(operation="list run-configs", exc=exc)

    items = [_to_response(row) for row in rows]
    return RunConfigListResponse(items=items, total=len(items))
