from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
from typing import Any

from api.supabase_client import SupabaseClient


@dataclass
class RunEvaluationError(Exception):
    status_code: int
    detail: str


_SUPPORTED_COMPONENTS = {
    "utilization_weight",
    "unplaced_penalty",
    "sheet_count_penalty",
    "remnant_value_weight",
    "process_time_penalty",
}

_KNOWN_THRESHOLD_KEYS = {
    "min_utilization",
    "max_unplaced_ratio",
    "max_used_sheet_count",
    "max_estimated_process_time_s",
    "min_remnant_value",
}

_METRIC_INPUT_MAP = {
    "utilization": "utilization_ratio",
    "utilization_ratio": "utilization_ratio",
    "unplaced_ratio": "unplaced_ratio",
    "used_sheet_count": "used_sheet_count",
    "estimated_process_time_s": "estimated_process_time_s",
    "remnant_value": "remnant_value",
    "placed_count": "placed_count",
    "unplaced_count": "unplaced_count",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_required(value: str, *, field: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise RunEvaluationError(status_code=400, detail=f"invalid {field}")
    return cleaned


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


def _safe_float(raw: Any) -> float | None:
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    return value


def _safe_nonnegative_int(raw: Any) -> int:
    if raw is None:
        return 0
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 0
    if value < 0:
        return 0
    return value


def _round6(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 6)


def _clamp(value: float, *, low: float, high: float) -> float:
    return max(low, min(high, value))


def _clamp01(value: float) -> float:
    return _clamp(value, low=0.0, high=1.0)


def _as_dict(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    return {}


def _load_project_for_owner(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
    owner_user_id: str,
) -> dict[str, Any]:
    rows = supabase.select_rows(
        table="app.projects",
        access_token=access_token,
        params={
            "select": "id,owner_user_id,lifecycle",
            "id": f"eq.{project_id}",
            "owner_user_id": f"eq.{owner_user_id}",
            "lifecycle": "neq.archived",
            "limit": "1",
        },
    )
    if not rows:
        raise RunEvaluationError(status_code=404, detail="project not found")
    return rows[0]


def _load_run_for_project(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
    project_id: str,
) -> dict[str, Any]:
    rows = supabase.select_rows(
        table="app.nesting_runs",
        access_token=access_token,
        params={
            "select": "id,project_id,owner_user_id,status",
            "id": f"eq.{run_id}",
            "limit": "1",
        },
    )
    if not rows:
        raise RunEvaluationError(status_code=404, detail="run not found")

    run = rows[0]
    run_project_id = str(run.get("project_id") or "").strip()
    if run_project_id != project_id:
        raise RunEvaluationError(status_code=403, detail="run does not belong to project")
    return run


def _load_scoring_version_for_owner(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    version_id: str,
    require_active: bool,
) -> dict[str, Any]:
    rows = supabase.select_rows(
        table="app.scoring_profile_versions",
        access_token=access_token,
        params={
            "select": "id,scoring_profile_id,owner_user_id,version_no,lifecycle,is_active,weights_jsonb,tie_breaker_jsonb,threshold_jsonb",
            "id": f"eq.{version_id}",
            "limit": "1",
        },
    )
    if not rows:
        raise RunEvaluationError(status_code=404, detail="scoring profile version not found")

    version = rows[0]
    version_owner = str(version.get("owner_user_id") or "").strip()
    if version_owner != owner_user_id:
        raise RunEvaluationError(status_code=403, detail="scoring profile version does not belong to owner")

    if require_active and not _normalize_bool(version.get("is_active")):
        raise RunEvaluationError(status_code=400, detail="scoring profile version is inactive")

    return version


def _load_project_scoring_selection(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
) -> dict[str, Any] | None:
    rows = supabase.select_rows(
        table="app.project_scoring_selection",
        access_token=access_token,
        params={
            "select": "project_id,active_scoring_profile_version_id,selected_at,selected_by",
            "project_id": f"eq.{project_id}",
            "limit": "1",
        },
    )
    if not rows:
        return None
    return rows[0]


def _load_run_metrics(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
) -> dict[str, Any]:
    rows = supabase.select_rows(
        table="app.run_metrics",
        access_token=access_token,
        params={
            "select": "run_id,placed_count,unplaced_count,used_sheet_count,utilization_ratio,remnant_value,metrics_jsonb,created_at",
            "run_id": f"eq.{run_id}",
            "limit": "1",
        },
    )
    if not rows:
        raise RunEvaluationError(status_code=400, detail="run metrics not found")
    return rows[0]


def _load_run_manufacturing_metrics(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
) -> dict[str, Any] | None:
    rows = supabase.select_rows(
        table="app.run_manufacturing_metrics",
        access_token=access_token,
        params={
            "select": "run_id,estimated_process_time_s,estimated_cut_length_mm,estimated_rapid_length_mm,pierce_count,metrics_jsonb,created_at",
            "run_id": f"eq.{run_id}",
            "limit": "1",
        },
    )
    if not rows:
        return None
    return rows[0]


def _load_existing_evaluation(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
) -> dict[str, Any] | None:
    rows = supabase.select_rows(
        table="app.run_evaluations",
        access_token=access_token,
        params={
            "select": "run_id,scoring_profile_version_id,total_score,evaluation_jsonb,created_at",
            "run_id": f"eq.{run_id}",
            "limit": "1",
        },
    )
    if not rows:
        return None
    return rows[0]


def _weight_for_key(*, weights: dict[str, Any], key: str, warnings: list[str]) -> float:
    if key not in weights:
        return 0.0
    raw = _safe_float(weights.get(key))
    if raw is None:
        warnings.append(f"invalid weight for {key}; treated as 0")
        return 0.0
    return raw


def _component_payload(
    *,
    raw_value: float | int | None,
    normalized_value: float | None,
    weight: float,
    contribution: float,
    status: str,
    detail: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "raw_value": raw_value,
        "normalized_value": _round6(normalized_value),
        "weight": _round6(weight),
        "contribution": _round6(contribution) or 0.0,
        "status": status,
    }
    if detail is not None:
        payload["detail"] = detail
    return payload


def _score_components(
    *,
    scoring_version: dict[str, Any],
    run_metrics: dict[str, Any],
    run_manufacturing_metrics: dict[str, Any] | None,
) -> dict[str, Any]:
    warnings: list[str] = []

    weights = _as_dict(scoring_version.get("weights_jsonb"))
    thresholds = _as_dict(scoring_version.get("threshold_jsonb"))
    tie_breaker = _as_dict(scoring_version.get("tie_breaker_jsonb"))

    placed_count = _safe_nonnegative_int(run_metrics.get("placed_count"))
    unplaced_count = _safe_nonnegative_int(run_metrics.get("unplaced_count"))
    used_sheet_count = _safe_nonnegative_int(run_metrics.get("used_sheet_count"))
    utilization_ratio = _safe_float(run_metrics.get("utilization_ratio"))
    utilization_ratio = _clamp01(utilization_ratio or 0.0)

    remnant_value = _safe_float(run_metrics.get("remnant_value"))
    estimated_process_time_s: float | None = None
    if run_manufacturing_metrics is not None:
        estimated_process_time_s = _safe_float(run_manufacturing_metrics.get("estimated_process_time_s"))

    total_parts = placed_count + unplaced_count
    unplaced_ratio = 0.0 if total_parts <= 0 else _clamp01(float(unplaced_count) / float(total_parts))
    sheet_count_penalty_norm = 0.0 if used_sheet_count <= 1 else _clamp01(1.0 - (1.0 / float(used_sheet_count)))

    components: dict[str, dict[str, Any]] = {}
    applied_weight_abs_sum = 0.0
    weighted_sum = 0.0

    utilization_weight = _weight_for_key(weights=weights, key="utilization_weight", warnings=warnings)
    utilization_contribution = utilization_ratio * utilization_weight
    components["utilization_weight"] = _component_payload(
        raw_value=utilization_ratio,
        normalized_value=utilization_ratio,
        weight=utilization_weight,
        contribution=utilization_contribution,
        status="applied",
    )
    applied_weight_abs_sum += abs(utilization_weight)
    weighted_sum += utilization_contribution

    unplaced_weight = _weight_for_key(weights=weights, key="unplaced_penalty", warnings=warnings)
    unplaced_contribution = -(unplaced_ratio * unplaced_weight)
    components["unplaced_penalty"] = _component_payload(
        raw_value=unplaced_ratio,
        normalized_value=unplaced_ratio,
        weight=unplaced_weight,
        contribution=unplaced_contribution,
        status="applied",
    )
    applied_weight_abs_sum += abs(unplaced_weight)
    weighted_sum += unplaced_contribution

    sheet_count_weight = _weight_for_key(weights=weights, key="sheet_count_penalty", warnings=warnings)
    sheet_count_contribution = -(sheet_count_penalty_norm * sheet_count_weight)
    components["sheet_count_penalty"] = _component_payload(
        raw_value=used_sheet_count,
        normalized_value=sheet_count_penalty_norm,
        weight=sheet_count_weight,
        contribution=sheet_count_contribution,
        status="applied",
    )
    applied_weight_abs_sum += abs(sheet_count_weight)
    weighted_sum += sheet_count_contribution

    remnant_weight = _weight_for_key(weights=weights, key="remnant_value_weight", warnings=warnings)
    remnant_threshold = _safe_float(thresholds.get("target_remnant_value"))
    if remnant_threshold is None:
        remnant_threshold = _safe_float(thresholds.get("max_remnant_value"))
    if remnant_value is None:
        components["remnant_value_weight"] = _component_payload(
            raw_value=None,
            normalized_value=None,
            weight=remnant_weight,
            contribution=0.0,
            status="not_applied",
            detail="missing_metric",
        )
    elif remnant_threshold is None or remnant_threshold <= 0:
        components["remnant_value_weight"] = _component_payload(
            raw_value=remnant_value,
            normalized_value=None,
            weight=remnant_weight,
            contribution=0.0,
            status="not_applied",
            detail="missing_threshold",
        )
    else:
        remnant_norm = _clamp01(remnant_value / remnant_threshold)
        remnant_contribution = remnant_norm * remnant_weight
        components["remnant_value_weight"] = _component_payload(
            raw_value=remnant_value,
            normalized_value=remnant_norm,
            weight=remnant_weight,
            contribution=remnant_contribution,
            status="applied",
        )
        applied_weight_abs_sum += abs(remnant_weight)
        weighted_sum += remnant_contribution

    process_time_weight = _weight_for_key(weights=weights, key="process_time_penalty", warnings=warnings)
    process_time_threshold = _safe_float(thresholds.get("max_estimated_process_time_s"))
    if estimated_process_time_s is None:
        components["process_time_penalty"] = _component_payload(
            raw_value=None,
            normalized_value=None,
            weight=process_time_weight,
            contribution=0.0,
            status="not_applied",
            detail="missing_metric",
        )
    elif process_time_threshold is None or process_time_threshold <= 0:
        components["process_time_penalty"] = _component_payload(
            raw_value=estimated_process_time_s,
            normalized_value=None,
            weight=process_time_weight,
            contribution=0.0,
            status="not_applied",
            detail="missing_threshold",
        )
    else:
        process_time_norm = _clamp01(estimated_process_time_s / process_time_threshold)
        process_time_contribution = -(process_time_norm * process_time_weight)
        components["process_time_penalty"] = _component_payload(
            raw_value=estimated_process_time_s,
            normalized_value=process_time_norm,
            weight=process_time_weight,
            contribution=process_time_contribution,
            status="applied",
        )
        applied_weight_abs_sum += abs(process_time_weight)
        weighted_sum += process_time_contribution

    unsupported_components: list[str] = []
    for key, raw_weight in weights.items():
        if key in _SUPPORTED_COMPONENTS:
            continue
        unsupported_components.append(key)
        parsed_weight = _safe_float(raw_weight)
        components[key] = _component_payload(
            raw_value=None,
            normalized_value=None,
            weight=parsed_weight or 0.0,
            contribution=0.0,
            status="unsupported_metric",
            detail="not_applied_yet",
        )

    threshold_results: dict[str, Any] = {}
    for key in sorted(_KNOWN_THRESHOLD_KEYS):
        threshold_value = _safe_float(thresholds.get(key))
        if threshold_value is None:
            threshold_results[key] = {
                "status": "not_configured",
                "threshold_value": None,
                "actual_value": None,
                "passed": None,
            }
            continue

        if key == "min_utilization":
            actual = utilization_ratio
            passed = actual >= threshold_value
        elif key == "max_unplaced_ratio":
            actual = unplaced_ratio
            passed = actual <= threshold_value
        elif key == "max_used_sheet_count":
            actual = float(used_sheet_count)
            passed = actual <= threshold_value
        elif key == "max_estimated_process_time_s":
            if estimated_process_time_s is None:
                threshold_results[key] = {
                    "status": "missing_metric",
                    "threshold_value": _round6(threshold_value),
                    "actual_value": None,
                    "passed": None,
                }
                continue
            actual = estimated_process_time_s
            passed = actual <= threshold_value
        elif key == "min_remnant_value":
            if remnant_value is None:
                threshold_results[key] = {
                    "status": "missing_metric",
                    "threshold_value": _round6(threshold_value),
                    "actual_value": None,
                    "passed": None,
                }
                continue
            actual = remnant_value
            passed = actual >= threshold_value
        else:
            threshold_results[key] = {
                "status": "unsupported_key",
                "threshold_value": _round6(threshold_value),
                "actual_value": None,
                "passed": None,
            }
            continue

        threshold_results[key] = {
            "status": "passed" if passed else "failed",
            "threshold_value": _round6(threshold_value),
            "actual_value": _round6(actual),
            "passed": passed,
        }

    unsupported_threshold_keys = sorted(k for k in thresholds.keys() if k not in _KNOWN_THRESHOLD_KEYS)
    if unsupported_threshold_keys:
        warnings.append("unsupported threshold keys: " + ", ".join(unsupported_threshold_keys))

    metric_inputs = {
        "placed_count": placed_count,
        "unplaced_count": unplaced_count,
        "used_sheet_count": used_sheet_count,
        "utilization_ratio": _round6(utilization_ratio),
        "unplaced_ratio": _round6(unplaced_ratio),
        "remnant_value": _round6(remnant_value),
        "estimated_process_time_s": _round6(estimated_process_time_s),
    }

    tie_breaker_inputs: dict[str, Any] = {}
    unsupported_tie_breaker_keys: list[str] = []
    for key, value in tie_breaker.items():
        metric_key: str | None = None
        if key in _METRIC_INPUT_MAP:
            metric_key = _METRIC_INPUT_MAP[key]
        elif key in {"primary", "secondary", "tertiary"} and isinstance(value, str):
            metric_key = _METRIC_INPUT_MAP.get(value)

        if metric_key is None:
            unsupported_tie_breaker_keys.append(key)
            continue

        tie_breaker_inputs[key] = {
            "metric_key": metric_key,
            "actual_value": metric_inputs.get(metric_key),
        }

    if unsupported_tie_breaker_keys:
        warnings.append("unsupported tie_breaker keys: " + ", ".join(sorted(unsupported_tie_breaker_keys)))

    total_score = 0.0
    if applied_weight_abs_sum > 0.0:
        total_score = _clamp(weighted_sum / applied_weight_abs_sum, low=-1.0, high=1.0)

    evaluation_jsonb = {
        "scoring_profile_snapshot": {
            "id": str(scoring_version.get("id") or "").strip(),
            "scoring_profile_id": str(scoring_version.get("scoring_profile_id") or "").strip(),
            "version_no": int(scoring_version.get("version_no") or 0),
            "weights_jsonb": weights,
            "tie_breaker_jsonb": tie_breaker,
            "threshold_jsonb": thresholds,
        },
        "input_metrics": metric_inputs,
        "components": components,
        "threshold_results": threshold_results,
        "tie_breaker_inputs": tie_breaker_inputs,
        "unsupported_components": sorted(unsupported_components),
        "warnings": warnings,
        "score_summary": {
            "weighted_sum": _round6(weighted_sum),
            "normalizer": _round6(applied_weight_abs_sum),
            "total_score": _round6(total_score),
            "bounded_range": [-1.0, 1.0],
        },
    }

    return {
        "total_score": _round6(total_score) or 0.0,
        "evaluation_jsonb": evaluation_jsonb,
    }


def create_or_replace_run_evaluation(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
    run_id: str,
    scoring_profile_version_id: str | None,
) -> dict[str, Any]:
    project_id_clean = _sanitize_required(project_id, field="project_id")
    run_id_clean = _sanitize_required(run_id, field="run_id")
    explicit_version_id_clean = None
    if scoring_profile_version_id is not None:
        explicit_version_id_clean = _sanitize_required(scoring_profile_version_id, field="scoring_profile_version_id")

    project = _load_project_for_owner(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
        owner_user_id=owner_user_id,
    )
    run = _load_run_for_project(
        supabase=supabase,
        access_token=access_token,
        run_id=run_id_clean,
        project_id=project_id_clean,
    )

    resolved_from_project_selection = False
    if explicit_version_id_clean is not None:
        scoring_version = _load_scoring_version_for_owner(
            supabase=supabase,
            access_token=access_token,
            owner_user_id=owner_user_id,
            version_id=explicit_version_id_clean,
            require_active=True,
        )
        resolved_version_id = explicit_version_id_clean
    else:
        selection = _load_project_scoring_selection(
            supabase=supabase,
            access_token=access_token,
            project_id=project_id_clean,
        )
        if selection is None:
            raise RunEvaluationError(
                status_code=400,
                detail="scoring_profile_version_id is required when project scoring selection is not set",
            )
        resolved_version_id = _sanitize_required(
            str(selection.get("active_scoring_profile_version_id") or ""),
            field="active_scoring_profile_version_id",
        )
        scoring_version = _load_scoring_version_for_owner(
            supabase=supabase,
            access_token=access_token,
            owner_user_id=owner_user_id,
            version_id=resolved_version_id,
            require_active=True,
        )
        resolved_from_project_selection = True

    run_metrics = _load_run_metrics(
        supabase=supabase,
        access_token=access_token,
        run_id=run_id_clean,
    )
    run_manufacturing_metrics = _load_run_manufacturing_metrics(
        supabase=supabase,
        access_token=access_token,
        run_id=run_id_clean,
    )

    computed = _score_components(
        scoring_version=scoring_version,
        run_metrics=run_metrics,
        run_manufacturing_metrics=run_manufacturing_metrics,
    )

    existing = _load_existing_evaluation(
        supabase=supabase,
        access_token=access_token,
        run_id=run_id_clean,
    )
    was_replaced = existing is not None

    supabase.delete_rows(
        table="app.run_evaluations",
        access_token=access_token,
        filters={"run_id": f"eq.{run_id_clean}"},
    )

    insert_payload = {
        "run_id": run_id_clean,
        "scoring_profile_version_id": resolved_version_id,
        "total_score": computed["total_score"],
        "evaluation_jsonb": computed["evaluation_jsonb"],
        "created_at": _now_iso(),
    }
    evaluation = supabase.insert_row(
        table="app.run_evaluations",
        access_token=access_token,
        payload=insert_payload,
    )

    return {
        "project": project,
        "run": run,
        "scoring_profile_version": scoring_version,
        "evaluation": evaluation,
        "was_replaced": was_replaced,
        "resolved_from_project_selection": resolved_from_project_selection,
    }


def get_run_evaluation(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
    run_id: str,
) -> dict[str, Any]:
    project_id_clean = _sanitize_required(project_id, field="project_id")
    run_id_clean = _sanitize_required(run_id, field="run_id")

    project = _load_project_for_owner(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
        owner_user_id=owner_user_id,
    )
    run = _load_run_for_project(
        supabase=supabase,
        access_token=access_token,
        run_id=run_id_clean,
        project_id=project_id_clean,
    )

    evaluation = _load_existing_evaluation(
        supabase=supabase,
        access_token=access_token,
        run_id=run_id_clean,
    )
    if evaluation is None:
        raise RunEvaluationError(status_code=404, detail="run evaluation not found")

    return {
        "project": project,
        "run": run,
        "evaluation": evaluation,
    }


def delete_run_evaluation(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
    run_id: str,
) -> dict[str, Any]:
    project_id_clean = _sanitize_required(project_id, field="project_id")
    run_id_clean = _sanitize_required(run_id, field="run_id")

    project = _load_project_for_owner(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
        owner_user_id=owner_user_id,
    )
    run = _load_run_for_project(
        supabase=supabase,
        access_token=access_token,
        run_id=run_id_clean,
        project_id=project_id_clean,
    )

    existing = _load_existing_evaluation(
        supabase=supabase,
        access_token=access_token,
        run_id=run_id_clean,
    )
    if existing is None:
        raise RunEvaluationError(status_code=404, detail="run evaluation not found")

    supabase.delete_rows(
        table="app.run_evaluations",
        access_token=access_token,
        filters={"run_id": f"eq.{run_id_clean}"},
    )

    return {
        "project": project,
        "run": run,
        "evaluation": existing,
    }
