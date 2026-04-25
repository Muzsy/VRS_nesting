from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from api.supabase_client import SupabaseClient
from vrs_nesting.config.nesting_quality_profiles import (
    DEFAULT_QUALITY_PROFILE,
    compact_runtime_policy,
    normalize_quality_profile_name,
    runtime_policy_for_quality_profile,
    validate_runtime_policy,
)

_KNOWN_PROFILE_SOLVER_KEYS = frozenset({
    "quality_profile",
    "sa_eval_budget_sec",
    "nesting_engine_runtime_policy",
    "engine_backend_hint",
})

_SUPPORTED_ENGINE_BACKEND_HINTS = frozenset({"sparrow_v1", "nesting_engine_v2"})
_DEFAULT_ENGINE_BACKEND_HINT = "nesting_engine_v2"


@dataclass
class RunStrategyResolutionError(Exception):
    status_code: int
    detail: str


@dataclass
class ResolvedRunStrategy:
    quality_profile: str
    nesting_engine_runtime_policy: dict[str, Any]
    sa_eval_budget_sec: int | None
    engine_backend_hint: str
    strategy_profile_version_id: str | None
    strategy_resolution_source: str
    field_sources: dict[str, str]
    overrides_applied: list[str]
    trace_jsonb: dict[str, Any]


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


def _normalize_engine_backend_hint(raw: str | None) -> str:
    if raw is None:
        return _DEFAULT_ENGINE_BACKEND_HINT
    cleaned = str(raw).strip().lower()
    if cleaned not in _SUPPORTED_ENGINE_BACKEND_HINTS:
        raise RunStrategyResolutionError(status_code=400, detail=f"invalid engine_backend_hint: {raw!r}")
    return cleaned


def _load_run_config(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
    run_config_id: str,
) -> dict[str, Any]:
    params = {
        "select": "id,project_id,created_by,run_strategy_profile_version_id,solver_config_overrides_jsonb",
        "id": f"eq.{run_config_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.run_configs", access_token=access_token, params=params)
    if not rows:
        raise RunStrategyResolutionError(status_code=404, detail="run_config not found")

    row = rows[0]
    if str(row.get("project_id") or "").strip() != project_id:
        raise RunStrategyResolutionError(status_code=400, detail="run_config does not belong to project")
    if str(row.get("created_by") or "").strip() != owner_user_id:
        raise RunStrategyResolutionError(status_code=403, detail="run_config does not belong to owner")
    return row


def _load_project_strategy_selection(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
) -> dict[str, Any] | None:
    params = {
        "select": "project_id,active_run_strategy_profile_version_id,selected_at,selected_by",
        "project_id": f"eq.{project_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.project_run_strategy_selection", access_token=access_token, params=params)
    return rows[0] if rows else None


def _load_strategy_profile_version(
    *,
    supabase: SupabaseClient,
    access_token: str,
    version_id: str,
    owner_user_id: str,
    require_active: bool,
) -> dict[str, Any]:
    params = {
        "select": (
            "id,run_strategy_profile_id,owner_user_id,version_no,lifecycle,is_active,"
            "solver_config_jsonb,placement_config_jsonb,manufacturing_bias_jsonb"
        ),
        "id": f"eq.{version_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.run_strategy_profile_versions", access_token=access_token, params=params)
    if not rows:
        raise RunStrategyResolutionError(status_code=404, detail="run strategy profile version not found")

    row = rows[0]
    if str(row.get("owner_user_id") or "").strip() != owner_user_id:
        raise RunStrategyResolutionError(status_code=403, detail="run strategy profile version does not belong to owner")
    if require_active and not _normalize_bool(row.get("is_active")):
        raise RunStrategyResolutionError(status_code=400, detail="run strategy profile version is inactive")
    return row


def _dedupe_list(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def resolve_run_strategy(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
    run_config_id: str | None,
    request_run_strategy_profile_version_id: str | None,
    request_quality_profile: str | None,
    request_engine_backend_hint: str | None,
    request_nesting_engine_runtime_policy: dict[str, Any] | None,
    request_sa_eval_budget_sec: int | None,
) -> ResolvedRunStrategy:
    field_sources: dict[str, str] = {}
    overrides_applied: list[str] = []

    # --- Step 1: Load run_config if provided, extract strategy fields ---
    rc_profile_version_id: str | None = None
    rc_overrides: dict[str, Any] = {}
    if run_config_id:
        rc_row = _load_run_config(
            supabase=supabase,
            access_token=access_token,
            owner_user_id=owner_user_id,
            project_id=project_id,
            run_config_id=run_config_id,
        )
        raw_pv_id = rc_row.get("run_strategy_profile_version_id")
        if raw_pv_id is not None:
            rc_profile_version_id = str(raw_pv_id).strip() or None
        raw_overrides = rc_row.get("solver_config_overrides_jsonb")
        if isinstance(raw_overrides, dict):
            rc_overrides = {k: v for k, v in raw_overrides.items() if k in _KNOWN_PROFILE_SOLVER_KEYS}

    # --- Step 2: Determine effective profile version ID and resolution source ---
    effective_profile_version_id: str | None = None
    profile_source: str

    req_pv_id = (str(request_run_strategy_profile_version_id).strip() or None) if request_run_strategy_profile_version_id else None

    if req_pv_id:
        effective_profile_version_id = req_pv_id
        profile_source = "request"
    elif rc_profile_version_id:
        effective_profile_version_id = rc_profile_version_id
        profile_source = "run_config"
    else:
        selection = _load_project_strategy_selection(
            supabase=supabase,
            access_token=access_token,
            project_id=project_id,
        )
        if selection is not None:
            sel_version_id = str(selection.get("active_run_strategy_profile_version_id") or "").strip()
            if sel_version_id:
                effective_profile_version_id = sel_version_id
                profile_source = "project_selection"
            else:
                profile_source = "global_default"
        else:
            profile_source = "global_default"

    # --- Step 3: Load profile version solver_config_jsonb if available ---
    profile_solver_config: dict[str, Any] = {}
    if effective_profile_version_id:
        require_active = profile_source == "request"
        version_row = _load_strategy_profile_version(
            supabase=supabase,
            access_token=access_token,
            version_id=effective_profile_version_id,
            owner_user_id=owner_user_id,
            require_active=require_active,
        )
        raw_solver_cfg = version_row.get("solver_config_jsonb")
        if isinstance(raw_solver_cfg, dict):
            profile_solver_config = {k: v for k, v in raw_solver_cfg.items() if k in _KNOWN_PROFILE_SOLVER_KEYS}

    profile_label = "profile" if effective_profile_version_id else "global_default"

    # --- Step 4: Build base values from profile (or global default) ---
    # quality_profile
    base_quality_profile: str
    raw_qp = profile_solver_config.get("quality_profile")
    if raw_qp is not None:
        try:
            base_quality_profile = normalize_quality_profile_name(str(raw_qp))
            field_sources["quality_profile"] = profile_label
        except ValueError:
            base_quality_profile = DEFAULT_QUALITY_PROFILE
            field_sources["quality_profile"] = "global_default"
    else:
        base_quality_profile = DEFAULT_QUALITY_PROFILE
        field_sources["quality_profile"] = "global_default"

    # engine_backend_hint
    base_backend_hint: str
    raw_bh = profile_solver_config.get("engine_backend_hint")
    if raw_bh is not None:
        try:
            base_backend_hint = _normalize_engine_backend_hint(str(raw_bh))
            field_sources["engine_backend_hint"] = profile_label
        except RunStrategyResolutionError:
            base_backend_hint = _DEFAULT_ENGINE_BACKEND_HINT
            field_sources["engine_backend_hint"] = "global_default"
    else:
        base_backend_hint = _DEFAULT_ENGINE_BACKEND_HINT
        field_sources["engine_backend_hint"] = "global_default"

    # sa_eval_budget_sec
    base_sa_eval_budget_sec: int | None = None
    raw_sa = profile_solver_config.get("sa_eval_budget_sec")
    if raw_sa is not None:
        try:
            v = int(raw_sa)
            if v > 0:
                base_sa_eval_budget_sec = v
                field_sources["sa_eval_budget_sec"] = profile_label
        except (TypeError, ValueError):
            pass

    # nesting_engine_runtime_policy from profile
    base_runtime_policy: dict[str, Any]
    raw_rtp = profile_solver_config.get("nesting_engine_runtime_policy")
    if isinstance(raw_rtp, dict):
        try:
            base_runtime_policy = compact_runtime_policy(validate_runtime_policy(raw_rtp))
            field_sources["nesting_engine_runtime_policy"] = profile_label
        except (ValueError, Exception):
            base_runtime_policy = compact_runtime_policy(runtime_policy_for_quality_profile(base_quality_profile))
            field_sources["nesting_engine_runtime_policy"] = "global_default"
    else:
        base_runtime_policy = compact_runtime_policy(runtime_policy_for_quality_profile(base_quality_profile))
        field_sources.setdefault("nesting_engine_runtime_policy", "global_default")

    # --- Step 5: Apply run_config solver_config_overrides ---
    eff_quality_profile = base_quality_profile
    eff_backend_hint = base_backend_hint
    eff_sa_eval_budget_sec = base_sa_eval_budget_sec
    eff_runtime_policy = dict(base_runtime_policy)

    if rc_overrides:
        if "quality_profile" in rc_overrides:
            try:
                eff_quality_profile = normalize_quality_profile_name(str(rc_overrides["quality_profile"]))
                field_sources["quality_profile"] = "run_config_override"
                overrides_applied.append("quality_profile")
            except ValueError as exc:
                raise RunStrategyResolutionError(status_code=400, detail=str(exc)) from exc

        if "engine_backend_hint" in rc_overrides:
            eff_backend_hint = _normalize_engine_backend_hint(str(rc_overrides["engine_backend_hint"]))
            field_sources["engine_backend_hint"] = "run_config_override"
            overrides_applied.append("engine_backend_hint")

        if "sa_eval_budget_sec" in rc_overrides:
            try:
                v = int(rc_overrides["sa_eval_budget_sec"])
                if v > 0:
                    eff_sa_eval_budget_sec = v
                    field_sources["sa_eval_budget_sec"] = "run_config_override"
                    overrides_applied.append("sa_eval_budget_sec")
                else:
                    raise RunStrategyResolutionError(status_code=400, detail="invalid sa_eval_budget_sec in run_config override")
            except (TypeError, ValueError) as exc:
                raise RunStrategyResolutionError(status_code=400, detail="invalid sa_eval_budget_sec in run_config override") from exc

        if "nesting_engine_runtime_policy" in rc_overrides:
            rtp_raw = rc_overrides["nesting_engine_runtime_policy"]
            if not isinstance(rtp_raw, dict):
                raise RunStrategyResolutionError(status_code=400, detail="invalid nesting_engine_runtime_policy in run_config override")
            try:
                eff_runtime_policy = compact_runtime_policy(validate_runtime_policy(rtp_raw))
                field_sources["nesting_engine_runtime_policy"] = "run_config_override"
                overrides_applied.append("nesting_engine_runtime_policy")
            except ValueError as exc:
                raise RunStrategyResolutionError(status_code=400, detail="invalid nesting_engine_runtime_policy in run_config override") from exc

    # --- Step 6: Apply explicit request overrides (highest precedence) ---
    has_request_solver_overrides = False

    if request_quality_profile is not None:
        qp_cleaned = str(request_quality_profile).strip()
        if qp_cleaned:
            try:
                eff_quality_profile = normalize_quality_profile_name(qp_cleaned)
                field_sources["quality_profile"] = "request"
                overrides_applied.append("quality_profile")
                has_request_solver_overrides = True
            except ValueError as exc:
                raise RunStrategyResolutionError(status_code=400, detail=str(exc)) from exc

    if request_engine_backend_hint is not None:
        bh_cleaned = str(request_engine_backend_hint).strip()
        if bh_cleaned:
            eff_backend_hint = _normalize_engine_backend_hint(bh_cleaned)
            field_sources["engine_backend_hint"] = "request"
            overrides_applied.append("engine_backend_hint")
            has_request_solver_overrides = True

    if request_sa_eval_budget_sec is not None:
        try:
            v = int(request_sa_eval_budget_sec)
            if v > 0:
                eff_sa_eval_budget_sec = v
                field_sources["sa_eval_budget_sec"] = "request"
                overrides_applied.append("sa_eval_budget_sec")
                has_request_solver_overrides = True
            else:
                raise RunStrategyResolutionError(status_code=400, detail="invalid sa_eval_budget_sec")
        except (TypeError, ValueError) as exc:
            raise RunStrategyResolutionError(status_code=400, detail="invalid sa_eval_budget_sec") from exc

    if request_nesting_engine_runtime_policy is not None:
        if not isinstance(request_nesting_engine_runtime_policy, dict):
            raise RunStrategyResolutionError(status_code=400, detail="invalid nesting_engine_runtime_policy")
        try:
            eff_runtime_policy = compact_runtime_policy(validate_runtime_policy(request_nesting_engine_runtime_policy))
            field_sources["nesting_engine_runtime_policy"] = "request"
            overrides_applied.append("nesting_engine_runtime_policy")
            has_request_solver_overrides = True
        except ValueError as exc:
            raise RunStrategyResolutionError(status_code=400, detail="invalid nesting_engine_runtime_policy") from exc

    # --- Step 7: Embed sa_eval_budget_sec into runtime policy if set ---
    if eff_sa_eval_budget_sec is not None and eff_sa_eval_budget_sec > 0:
        eff_runtime_policy["sa_eval_budget_sec"] = eff_sa_eval_budget_sec

    # --- Step 8: Determine strategy_resolution_source ---
    if req_pv_id:
        strategy_resolution_source = "request"
    elif has_request_solver_overrides:
        strategy_resolution_source = f"{profile_source}_with_request_override" if profile_source != "global_default" else "request_override"
    else:
        strategy_resolution_source = profile_source

    # --- Step 9: Build trace_jsonb ---
    trace_jsonb: dict[str, Any] = {
        "strategy_resolution_source": strategy_resolution_source,
        "effective_strategy_profile_version_id": effective_profile_version_id,
        "profile_source": profile_source,
        "field_sources": dict(field_sources),
        "overrides_applied": _dedupe_list(overrides_applied),
        "run_config_id": run_config_id,
        "request_had_profile_version": bool(req_pv_id),
        "request_had_solver_overrides": has_request_solver_overrides,
    }

    return ResolvedRunStrategy(
        quality_profile=eff_quality_profile,
        nesting_engine_runtime_policy=eff_runtime_policy,
        sa_eval_budget_sec=eff_sa_eval_budget_sec,
        engine_backend_hint=eff_backend_hint,
        strategy_profile_version_id=effective_profile_version_id,
        strategy_resolution_source=strategy_resolution_source,
        field_sources=dict(field_sources),
        overrides_applied=_dedupe_list(overrides_applied),
        trace_jsonb=trace_jsonb,
    )
