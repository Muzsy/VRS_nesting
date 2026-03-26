from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from functools import cmp_to_key
import math
from typing import Any
from uuid import uuid4

from api.supabase_client import SupabaseClient


@dataclass
class RunRankingError(Exception):
    status_code: int
    detail: str


_PROFILE_SLOT_KEYS = ("primary", "secondary", "tertiary")

_METRIC_DIRECTIONS: dict[str, str] = {
    "utilization_ratio": "desc",
    "unplaced_ratio": "asc",
    "used_sheet_count": "asc",
    "estimated_process_time_s": "asc",
    "remnant_value": "desc",
    "placed_count": "desc",
    "unplaced_count": "asc",
}

_PROFILE_METRIC_PRIORITY: tuple[str, ...] = (
    "utilization_ratio",
    "unplaced_ratio",
    "used_sheet_count",
    "estimated_process_time_s",
    "remnant_value",
    "placed_count",
    "unplaced_count",
)

_CANONICAL_FALLBACK_METRICS: tuple[tuple[str, str], ...] = (
    ("utilization_ratio", "desc"),
    ("unplaced_ratio", "asc"),
    ("used_sheet_count", "asc"),
    ("estimated_process_time_s", "asc"),
)

_METRIC_ALIASES: dict[str, str] = {
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
        raise RunRankingError(status_code=400, detail=f"invalid {field}")
    return cleaned


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


def _round6(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 6)


def _as_dict(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    return {}


def _normalize_metric_key(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    cleaned = raw.strip()
    if not cleaned:
        return None
    return _METRIC_ALIASES.get(cleaned)


def _load_project_for_owner(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
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
        raise RunRankingError(status_code=404, detail="project not found")
    return rows[0]


def _load_batch_for_project(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
    batch_id: str,
) -> dict[str, Any]:
    rows = supabase.select_rows(
        table="app.run_batches",
        access_token=access_token,
        params={
            "select": "id,project_id,created_by,batch_kind,notes,created_at",
            "id": f"eq.{batch_id}",
            "project_id": f"eq.{project_id}",
            "limit": "1",
        },
    )
    if not rows:
        raise RunRankingError(status_code=404, detail="run batch not found")
    return rows[0]


def _load_batch_items(
    *,
    supabase: SupabaseClient,
    access_token: str,
    batch_id: str,
) -> list[dict[str, Any]]:
    return supabase.select_rows(
        table="app.run_batch_items",
        access_token=access_token,
        params={
            "select": "batch_id,run_id,candidate_label,strategy_profile_version_id,scoring_profile_version_id,created_at",
            "batch_id": f"eq.{batch_id}",
            "order": "created_at.asc,run_id.asc",
        },
    )


def _load_run_evaluation(
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


def _load_scoring_profile_version_for_owner(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    scoring_profile_version_id: str,
) -> dict[str, Any] | None:
    rows = supabase.select_rows(
        table="app.scoring_profile_versions",
        access_token=access_token,
        params={
            "select": "id,owner_user_id,tie_breaker_jsonb",
            "id": f"eq.{scoring_profile_version_id}",
            "owner_user_id": f"eq.{owner_user_id}",
            "limit": "1",
        },
    )
    if not rows:
        return None
    return rows[0]


def _list_existing_rankings(
    *,
    supabase: SupabaseClient,
    access_token: str,
    batch_id: str,
) -> list[dict[str, Any]]:
    return supabase.select_rows(
        table="app.run_ranking_results",
        access_token=access_token,
        params={
            "select": "id,batch_id,run_id,rank_no,ranking_reason_jsonb,created_at",
            "batch_id": f"eq.{batch_id}",
            "order": "rank_no.asc,created_at.asc,id.asc",
        },
    )


def _extract_metric_inputs(evaluation_jsonb: dict[str, Any]) -> dict[str, float | None]:
    input_metrics = _as_dict(evaluation_jsonb.get("input_metrics"))
    tie_breaker_inputs = _as_dict(evaluation_jsonb.get("tie_breaker_inputs"))

    snapshot: dict[str, float | None] = {}
    for metric_key in _PROFILE_METRIC_PRIORITY:
        snapshot[metric_key] = _safe_float(input_metrics.get(metric_key))

    for tie_break_value in tie_breaker_inputs.values():
        tie_break_item = _as_dict(tie_break_value)
        metric_key = _normalize_metric_key(tie_break_item.get("metric_key"))
        if metric_key is None:
            continue
        actual_value = _safe_float(tie_break_item.get("actual_value"))
        if actual_value is None:
            continue
        snapshot[metric_key] = actual_value

    return snapshot


def _extract_profile_tie_break_metric_keys(scoring_version: dict[str, Any] | None) -> list[str]:
    if scoring_version is None:
        return []
    tie_breaker_jsonb = _as_dict(scoring_version.get("tie_breaker_jsonb"))
    if not tie_breaker_jsonb:
        return []

    collected: list[str] = []

    for slot_key in _PROFILE_SLOT_KEYS:
        metric_key = _normalize_metric_key(tie_breaker_jsonb.get(slot_key))
        if metric_key is not None:
            collected.append(metric_key)

    for key in sorted(tie_breaker_jsonb.keys()):
        if key in _PROFILE_SLOT_KEYS:
            continue
        key_metric = _normalize_metric_key(key)
        if key_metric is not None:
            collected.append(key_metric)
            continue
        value_metric = _normalize_metric_key(tie_breaker_jsonb.get(key))
        if value_metric is not None:
            collected.append(value_metric)

    deduped: list[str] = []
    for metric_key in collected:
        if metric_key not in _METRIC_DIRECTIONS:
            continue
        if metric_key in deduped:
            continue
        deduped.append(metric_key)
    return deduped


def _build_profile_metric_keys(candidates: list[dict[str, Any]]) -> list[str]:
    requested: set[str] = set()
    for candidate in candidates:
        for metric_key in candidate.get("profile_requested_metric_keys", []):
            if isinstance(metric_key, str):
                requested.add(metric_key)

    ordered = [metric_key for metric_key in _PROFILE_METRIC_PRIORITY if metric_key in requested]
    extras = sorted(metric_key for metric_key in requested if metric_key not in ordered)
    return ordered + extras


def _compare_numbers(*, left: Any, right: Any, direction: str, require_both: bool) -> int:
    left_value = _safe_float(left)
    right_value = _safe_float(right)

    if left_value is None or right_value is None:
        if require_both:
            return 0
        if left_value is None and right_value is None:
            return 0
        return 1 if left_value is None else -1

    if left_value == right_value:
        return 0

    if direction == "desc":
        return -1 if left_value > right_value else 1
    return -1 if left_value < right_value else 1


def _compare_text(*, left: Any, right: Any) -> int:
    left_text = str(left or "").strip()
    right_text = str(right or "").strip()
    if left_text == right_text:
        return 0
    return -1 if left_text < right_text else 1


def _compare_candidates(
    left: dict[str, Any],
    right: dict[str, Any],
    *,
    profile_metric_keys: list[str],
) -> int:
    score_cmp = _compare_numbers(
        left=left["total_score"],
        right=right["total_score"],
        direction="desc",
        require_both=False,
    )
    if score_cmp != 0:
        return score_cmp

    left_metrics = left["metrics"]
    right_metrics = right["metrics"]

    for metric_key in profile_metric_keys:
        metric_cmp = _compare_numbers(
            left=left_metrics.get(metric_key),
            right=right_metrics.get(metric_key),
            direction=_METRIC_DIRECTIONS.get(metric_key, "asc"),
            require_both=True,
        )
        if metric_cmp != 0:
            return metric_cmp

    for metric_key, direction in _CANONICAL_FALLBACK_METRICS:
        metric_cmp = _compare_numbers(
            left=left_metrics.get(metric_key),
            right=right_metrics.get(metric_key),
            direction=direction,
            require_both=True,
        )
        if metric_cmp != 0:
            return metric_cmp

    label_cmp = _compare_text(left=left.get("candidate_label"), right=right.get("candidate_label"))
    if label_cmp != 0:
        return label_cmp

    return _compare_text(left=left["run_id"], right=right["run_id"])


def _first_decisive_criterion(
    *,
    current: dict[str, Any],
    previous: dict[str, Any] | None,
    profile_metric_keys: list[str],
) -> dict[str, str]:
    if previous is None:
        return {
            "criterion": "batch_first_item",
            "source": "initial",
        }

    score_cmp = _compare_numbers(
        left=current["total_score"],
        right=previous["total_score"],
        direction="desc",
        require_both=False,
    )
    if score_cmp != 0:
        return {"criterion": "total_score_desc", "source": "total_score"}

    current_metrics = current["metrics"]
    previous_metrics = previous["metrics"]

    for metric_key in profile_metric_keys:
        metric_cmp = _compare_numbers(
            left=current_metrics.get(metric_key),
            right=previous_metrics.get(metric_key),
            direction=_METRIC_DIRECTIONS.get(metric_key, "asc"),
            require_both=True,
        )
        if metric_cmp != 0:
            return {
                "criterion": f"profile:{metric_key}:{_METRIC_DIRECTIONS.get(metric_key, 'asc')}",
                "source": "profile_tie_break",
            }

    for metric_key, direction in _CANONICAL_FALLBACK_METRICS:
        metric_cmp = _compare_numbers(
            left=current_metrics.get(metric_key),
            right=previous_metrics.get(metric_key),
            direction=direction,
            require_both=True,
        )
        if metric_cmp != 0:
            return {
                "criterion": f"canonical:{metric_key}:{direction}",
                "source": "canonical_fallback",
            }

    label_cmp = _compare_text(left=current.get("candidate_label"), right=previous.get("candidate_label"))
    if label_cmp != 0:
        return {"criterion": "candidate_label:asc", "source": "terminal_fallback"}

    return {"criterion": "run_id:asc", "source": "terminal_fallback"}


def _build_ranking_reason(
    *,
    candidate: dict[str, Any],
    rank_no: int,
    profile_metric_keys: list[str],
    decisive: dict[str, str],
) -> dict[str, Any]:
    metrics = candidate["metrics"]
    canonical_keys = [metric_key for metric_key, _ in _CANONICAL_FALLBACK_METRICS]
    components = _as_dict(candidate["evaluation_jsonb"].get("components"))

    profile_values: dict[str, float | None] = {}
    for metric_key in profile_metric_keys:
        profile_values[metric_key] = _round6(_safe_float(metrics.get(metric_key)))

    canonical_values: dict[str, float | None] = {}
    for metric_key in canonical_keys:
        canonical_values[metric_key] = _round6(_safe_float(metrics.get(metric_key)))

    return {
        "rank_no": rank_no,
        "total_score": _round6(candidate["total_score"]),
        "scoring_profile_version_id": candidate["evaluation_scoring_profile_version_id"],
        "candidate_label": candidate.get("candidate_label"),
        "tie_break_source": decisive["source"],
        "tie_break_trace": {
            "decisive_against_previous": decisive["criterion"],
            "profile_metric_keys": profile_metric_keys,
            "canonical_fallback_metric_keys": canonical_keys,
            "profile_values": profile_values,
            "canonical_values": canonical_values,
            "terminal_values": {
                "candidate_label": candidate.get("candidate_label"),
                "run_id": candidate["run_id"],
            },
        },
        "warnings": list(candidate["warnings"]),
        "evaluation_summary_ref": {
            "source_table": "app.run_evaluations",
            "run_id": candidate["run_id"],
            "components_present": bool(components),
            "score_is_persisted": True,
            "score_recalculated_by_ranking": False,
        },
    }


def create_or_replace_run_batch_ranking(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
    batch_id: str,
) -> dict[str, Any]:
    project_id_clean = _sanitize_required(project_id, field="project_id")
    batch_id_clean = _sanitize_required(batch_id, field="batch_id")

    project = _load_project_for_owner(
        supabase=supabase,
        access_token=access_token,
        owner_user_id=owner_user_id,
        project_id=project_id_clean,
    )
    batch = _load_batch_for_project(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
        batch_id=batch_id_clean,
    )
    batch_items = _load_batch_items(
        supabase=supabase,
        access_token=access_token,
        batch_id=batch_id_clean,
    )
    if not batch_items:
        raise RunRankingError(status_code=400, detail="run batch has no items")

    candidates: list[dict[str, Any]] = []
    for batch_item in batch_items:
        run_id = _sanitize_required(str(batch_item.get("run_id") or ""), field="run_id")
        evaluation = _load_run_evaluation(
            supabase=supabase,
            access_token=access_token,
            run_id=run_id,
        )
        if evaluation is None:
            raise RunRankingError(
                status_code=400,
                detail=f"missing run evaluation for run_id={run_id}",
            )

        total_score = _safe_float(evaluation.get("total_score"))
        if total_score is None:
            raise RunRankingError(
                status_code=400,
                detail=f"run evaluation has invalid total_score for run_id={run_id}",
            )

        evaluation_jsonb = _as_dict(evaluation.get("evaluation_jsonb"))
        item_scoring_profile_version_id = str(batch_item.get("scoring_profile_version_id") or "").strip() or None
        evaluation_scoring_profile_version_id = str(evaluation.get("scoring_profile_version_id") or "").strip() or None

        if item_scoring_profile_version_id and evaluation_scoring_profile_version_id is None:
            raise RunRankingError(
                status_code=409,
                detail=f"scoring context mismatch for run_id={run_id}: batch item has scoring_profile_version_id but evaluation has null",
            )
        if (
            item_scoring_profile_version_id
            and evaluation_scoring_profile_version_id
            and item_scoring_profile_version_id != evaluation_scoring_profile_version_id
        ):
            raise RunRankingError(
                status_code=409,
                detail=f"scoring context mismatch for run_id={run_id}: batch item and evaluation scoring_profile_version_id differ",
            )

        warnings: list[str] = []
        if item_scoring_profile_version_id is None and evaluation_scoring_profile_version_id is not None:
            warnings.append("batch_item_missing_scoring_context_used_evaluation_context")
        if item_scoring_profile_version_id is None and evaluation_scoring_profile_version_id is None:
            warnings.append("scoring_context_missing_in_batch_item_and_evaluation")

        scoring_version = None
        if evaluation_scoring_profile_version_id is not None:
            scoring_version = _load_scoring_profile_version_for_owner(
                supabase=supabase,
                access_token=access_token,
                owner_user_id=owner_user_id,
                scoring_profile_version_id=evaluation_scoring_profile_version_id,
            )
            if scoring_version is None:
                warnings.append("scoring_profile_version_not_accessible_for_owner")

        candidates.append(
            {
                "run_id": run_id,
                "candidate_label": str(batch_item.get("candidate_label") or "").strip() or None,
                "total_score": total_score,
                "metrics": _extract_metric_inputs(evaluation_jsonb),
                "evaluation_jsonb": evaluation_jsonb,
                "evaluation_scoring_profile_version_id": evaluation_scoring_profile_version_id,
                "profile_requested_metric_keys": _extract_profile_tie_break_metric_keys(scoring_version),
                "warnings": warnings,
            }
        )

    profile_metric_keys = _build_profile_metric_keys(candidates)
    sorted_candidates = sorted(
        candidates,
        key=cmp_to_key(
            lambda left, right: _compare_candidates(
                left,
                right,
                profile_metric_keys=profile_metric_keys,
            )
        ),
    )

    existing_rankings = _list_existing_rankings(
        supabase=supabase,
        access_token=access_token,
        batch_id=batch_id_clean,
    )
    was_replaced = bool(existing_rankings)

    supabase.delete_rows(
        table="app.run_ranking_results",
        access_token=access_token,
        filters={"batch_id": f"eq.{batch_id_clean}"},
    )

    persisted_items: list[dict[str, Any]] = []
    previous_candidate: dict[str, Any] | None = None
    for rank_no, candidate in enumerate(sorted_candidates, start=1):
        decisive = _first_decisive_criterion(
            current=candidate,
            previous=previous_candidate,
            profile_metric_keys=profile_metric_keys,
        )
        ranking_reason_jsonb = _build_ranking_reason(
            candidate=candidate,
            rank_no=rank_no,
            profile_metric_keys=profile_metric_keys,
            decisive=decisive,
        )
        row = supabase.insert_row(
            table="app.run_ranking_results",
            access_token=access_token,
            payload={
                "id": str(uuid4()),
                "batch_id": batch_id_clean,
                "run_id": candidate["run_id"],
                "rank_no": rank_no,
                "ranking_reason_jsonb": ranking_reason_jsonb,
                "created_at": _now_iso(),
            },
        )
        persisted_items.append(row)
        previous_candidate = candidate

    return {
        "project": project,
        "batch": batch,
        "items": persisted_items,
        "total": len(persisted_items),
        "was_replaced": was_replaced,
    }


def list_run_batch_ranking(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
    batch_id: str,
) -> dict[str, Any]:
    project_id_clean = _sanitize_required(project_id, field="project_id")
    batch_id_clean = _sanitize_required(batch_id, field="batch_id")

    project = _load_project_for_owner(
        supabase=supabase,
        access_token=access_token,
        owner_user_id=owner_user_id,
        project_id=project_id_clean,
    )
    batch = _load_batch_for_project(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
        batch_id=batch_id_clean,
    )
    items = _list_existing_rankings(
        supabase=supabase,
        access_token=access_token,
        batch_id=batch_id_clean,
    )

    return {
        "project": project,
        "batch": batch,
        "items": items,
        "total": len(items),
    }


def delete_run_batch_ranking(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
    batch_id: str,
) -> dict[str, Any]:
    project_id_clean = _sanitize_required(project_id, field="project_id")
    batch_id_clean = _sanitize_required(batch_id, field="batch_id")

    project = _load_project_for_owner(
        supabase=supabase,
        access_token=access_token,
        owner_user_id=owner_user_id,
        project_id=project_id_clean,
    )
    batch = _load_batch_for_project(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
        batch_id=batch_id_clean,
    )
    existing = _list_existing_rankings(
        supabase=supabase,
        access_token=access_token,
        batch_id=batch_id_clean,
    )
    if not existing:
        raise RunRankingError(status_code=404, detail="run batch ranking not found")

    supabase.delete_rows(
        table="app.run_ranking_results",
        access_token=access_token,
        filters={"batch_id": f"eq.{batch_id_clean}"},
    )

    return {
        "project": project,
        "batch": batch,
        "items": existing,
        "total_deleted": len(existing),
    }
