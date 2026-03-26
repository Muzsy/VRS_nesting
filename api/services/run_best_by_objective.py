from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from api.supabase_client import SupabaseClient


@dataclass
class RunBestByObjectiveError(Exception):
    status_code: int
    detail: str


_SUPPORTED_OBJECTIVES: tuple[str, ...] = (
    "material-best",
    "time-best",
    "priority-best",
    "cost-best",
)

_OBJECTIVE_SOURCE_TABLES: dict[str, list[str]] = {
    "material-best": [
        "app.run_batches",
        "app.run_batch_items",
        "app.run_ranking_results",
        "app.run_evaluations",
        "app.run_metrics",
    ],
    "time-best": [
        "app.run_batches",
        "app.run_batch_items",
        "app.run_ranking_results",
        "app.run_evaluations",
        "app.run_metrics",
        "app.run_manufacturing_metrics",
    ],
    "priority-best": [
        "app.run_batches",
        "app.run_batch_items",
        "app.run_ranking_results",
        "app.run_evaluations",
        "app.run_metrics",
        "app.nesting_run_snapshots",
        "app.run_layout_unplaced",
    ],
    "cost-best": [
        "app.run_batches",
        "app.run_batch_items",
        "app.run_ranking_results",
        "app.run_evaluations",
        "app.run_business_metrics",
    ],
}

_PRIORITY_HIGH_THRESHOLD = 20


def _sanitize_required(raw: str, *, field: str) -> str:
    value = str(raw or "").strip()
    if not value:
        raise RunBestByObjectiveError(status_code=400, detail=f"invalid {field}")
    return value


def _sanitize_optional(raw: Any) -> str | None:
    value = str(raw or "").strip()
    return value or None


def _sanitize_objective(raw: str | None) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip().lower()
    if not value:
        return None
    if value not in _SUPPORTED_OBJECTIVES:
        raise RunBestByObjectiveError(status_code=400, detail=f"unsupported objective: {value}")
    return value


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


def _safe_nonnegative_int(raw: Any) -> int | None:
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    if value < 0:
        return None
    return value


def _safe_positive_int(raw: Any) -> int | None:
    value = _safe_nonnegative_int(raw)
    if value is None or value <= 0:
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


def _as_list(raw: Any) -> list[Any]:
    if isinstance(raw, list):
        return list(raw)
    return []


def _desc_key(value: float | None) -> tuple[int, float]:
    if value is None:
        return (1, 0.0)
    return (0, -float(value))


def _asc_key(value: float | None) -> tuple[int, float]:
    if value is None:
        return (1, 0.0)
    return (0, float(value))


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
        raise RunBestByObjectiveError(status_code=404, detail="project not found")
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
        raise RunBestByObjectiveError(status_code=404, detail="run batch not found")
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
            "select": "batch_id,run_id,candidate_label,created_at",
            "batch_id": f"eq.{batch_id}",
            "order": "created_at.asc,run_id.asc",
        },
    )


def _load_rankings(
    *,
    supabase: SupabaseClient,
    access_token: str,
    batch_id: str,
) -> list[dict[str, Any]]:
    return supabase.select_rows(
        table="app.run_ranking_results",
        access_token=access_token,
        params={
            "select": "batch_id,run_id,rank_no,ranking_reason_jsonb,created_at",
            "batch_id": f"eq.{batch_id}",
            "order": "rank_no.asc,created_at.asc,run_id.asc",
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


def _load_run_metrics(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
) -> dict[str, Any] | None:
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
        return None
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
            "select": "run_id,estimated_process_time_s,estimated_cut_length_mm,estimated_rapid_length_mm,pierce_count,created_at",
            "run_id": f"eq.{run_id}",
            "limit": "1",
        },
    )
    if not rows:
        return None
    return rows[0]


def _load_run_snapshot(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
) -> dict[str, Any] | None:
    rows = supabase.select_rows(
        table="app.nesting_run_snapshots",
        access_token=access_token,
        params={
            "select": "run_id,parts_manifest_jsonb,snapshot_hash_sha256,snapshot_version",
            "run_id": f"eq.{run_id}",
            "limit": "1",
        },
    )
    if not rows:
        return None
    return rows[0]


def _load_run_unplaced_rows(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
) -> list[dict[str, Any]]:
    return supabase.select_rows(
        table="app.run_layout_unplaced",
        access_token=access_token,
        params={
            "select": "run_id,part_revision_id,remaining_qty,reason,created_at",
            "run_id": f"eq.{run_id}",
            "order": "part_revision_id.asc,created_at.asc",
        },
    )


def _build_run_contexts(
    *,
    supabase: SupabaseClient,
    access_token: str,
    batch_id: str,
) -> list[dict[str, Any]]:
    batch_items = _load_batch_items(supabase=supabase, access_token=access_token, batch_id=batch_id)
    candidate_labels: dict[str, str | None] = {}
    for item in batch_items:
        run_id = _sanitize_optional(item.get("run_id"))
        if run_id is None:
            continue
        candidate_labels[run_id] = _sanitize_optional(item.get("candidate_label"))

    ranking_rows = _load_rankings(supabase=supabase, access_token=access_token, batch_id=batch_id)
    if not ranking_rows:
        raise RunBestByObjectiveError(status_code=404, detail="run batch ranking not found")

    contexts: list[dict[str, Any]] = []
    for ranking_row in ranking_rows:
        run_id = _sanitize_required(ranking_row.get("run_id"), field="run_id")
        rank_no_raw = _safe_nonnegative_int(ranking_row.get("rank_no"))
        if rank_no_raw is None or rank_no_raw <= 0:
            raise RunBestByObjectiveError(
                status_code=500,
                detail=f"invalid ranking row rank_no for run_id={run_id}",
            )
        contexts.append(
            {
                "run_id": run_id,
                "rank_no": rank_no_raw,
                "candidate_label": candidate_labels.get(run_id),
                "ranking_reason_jsonb": _as_dict(ranking_row.get("ranking_reason_jsonb")),
                "evaluation": _load_run_evaluation(supabase=supabase, access_token=access_token, run_id=run_id),
                "run_metrics": _load_run_metrics(supabase=supabase, access_token=access_token, run_id=run_id),
                "run_manufacturing_metrics": _load_run_manufacturing_metrics(
                    supabase=supabase,
                    access_token=access_token,
                    run_id=run_id,
                ),
                "snapshot": _load_run_snapshot(supabase=supabase, access_token=access_token, run_id=run_id),
                "run_unplaced_rows": _load_run_unplaced_rows(supabase=supabase, access_token=access_token, run_id=run_id),
            }
        )

    contexts.sort(key=lambda row: (int(row["rank_no"]), str(row["run_id"])))
    return contexts


def _build_priority_projection(
    *,
    snapshot_row: dict[str, Any] | None,
    unplaced_rows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if snapshot_row is None:
        return None

    raw_parts = _as_list(snapshot_row.get("parts_manifest_jsonb"))
    parts: list[dict[str, Any]] = []
    for item in raw_parts:
        part = _as_dict(item)
        part_revision_id = _sanitize_optional(part.get("part_revision_id"))
        required_qty = _safe_positive_int(part.get("required_qty"))
        placement_priority = _safe_nonnegative_int(part.get("placement_priority"))
        if part_revision_id is None or required_qty is None or placement_priority is None:
            continue
        bounded_priority = max(0, min(100, placement_priority))
        weight = max(1, 101 - bounded_priority)
        parts.append(
            {
                "part_revision_id": part_revision_id,
                "required_qty": required_qty,
                "placement_priority": bounded_priority,
                "priority_weight": weight,
            }
        )
    if not parts:
        return None

    unplaced_by_part: dict[str, int] = {}
    for row in unplaced_rows:
        part_revision_id = _sanitize_optional(row.get("part_revision_id"))
        remaining_qty = _safe_positive_int(row.get("remaining_qty"))
        if part_revision_id is None or remaining_qty is None:
            continue
        unplaced_by_part[part_revision_id] = unplaced_by_part.get(part_revision_id, 0) + remaining_qty

    total_weighted_demand = 0.0
    fulfilled_weighted_qty = 0.0
    high_priority_missing_weight = 0.0
    missing_part_rows: list[dict[str, Any]] = []
    for part in parts:
        required_qty = int(part["required_qty"])
        weight = float(part["priority_weight"])
        placement_priority = int(part["placement_priority"])
        part_revision_id = str(part["part_revision_id"])
        missing_qty = min(required_qty, max(0, int(unplaced_by_part.get(part_revision_id, 0))))
        fulfilled_qty = max(0, required_qty - missing_qty)

        part_total_weighted = float(required_qty) * weight
        part_fulfilled_weighted = float(fulfilled_qty) * weight
        part_missing_weighted = float(missing_qty) * weight

        total_weighted_demand += part_total_weighted
        fulfilled_weighted_qty += part_fulfilled_weighted
        if placement_priority <= _PRIORITY_HIGH_THRESHOLD:
            high_priority_missing_weight += part_missing_weighted
        if missing_qty > 0:
            missing_part_rows.append(
                {
                    "part_revision_id": part_revision_id,
                    "missing_qty": missing_qty,
                    "placement_priority": placement_priority,
                    "missing_weight": _round6(part_missing_weighted),
                }
            )

    if total_weighted_demand <= 0.0:
        return None

    missing_part_rows.sort(
        key=lambda row: (
            _desc_key(_safe_float(row.get("missing_weight"))),
            _asc_key(_safe_float(row.get("placement_priority"))),
            str(row.get("part_revision_id") or ""),
        )
    )

    ratio = fulfilled_weighted_qty / total_weighted_demand
    return {
        "priority_fulfilment_ratio": _round6(ratio),
        "high_priority_missing_weight": _round6(high_priority_missing_weight),
        "total_weighted_demand": _round6(total_weighted_demand),
        "fulfilled_weighted_qty": _round6(fulfilled_weighted_qty),
        "missing_top": missing_part_rows[:3],
        "formula": {
            "priority_weight": "101 - placement_priority",
            "ratio": "fulfilled_weighted_qty / total_weighted_demand",
            "high_priority_threshold": _PRIORITY_HIGH_THRESHOLD,
        },
    }


def _decisive_rule(
    *,
    winner: dict[str, Any],
    runner_up: dict[str, Any] | None,
    criteria_names: list[str],
) -> tuple[str, list[str]]:
    if runner_up is None:
        return ("single_candidate", [])

    winner_values = winner.get("criteria_trace")
    runner_values = runner_up.get("criteria_trace")
    if not isinstance(winner_values, dict) or not isinstance(runner_values, dict):
        return ("single_candidate", [])

    for idx, criterion in enumerate(criteria_names):
        if winner_values.get(criterion) != runner_values.get(criterion):
            if idx <= 0:
                return (criterion, [])
            return (criterion, criteria_names[1 : idx + 1])
    return ("run_id_asc", criteria_names[1:])


def _objective_response(
    *,
    objective: str,
    status: str,
    batch_id: str,
    run_id: str | None,
    rank_no: int | None,
    candidate_label: str | None,
    objective_value: float | None,
    objective_reason_jsonb: dict[str, Any],
) -> dict[str, Any]:
    return {
        "objective": objective,
        "status": status,
        "batch_id": batch_id,
        "run_id": run_id,
        "rank_no": rank_no,
        "candidate_label": candidate_label,
        "objective_value": _round6(objective_value),
        "objective_reason_jsonb": objective_reason_jsonb,
    }


def _evaluate_material_best(*, batch_id: str, run_contexts: list[dict[str, Any]]) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    missing_sources: list[str] = []
    for ctx in run_contexts:
        run_metrics = ctx.get("run_metrics")
        evaluation = ctx.get("evaluation")
        if run_metrics is None:
            missing_sources.append(f"app.run_metrics:{ctx['run_id']}")
            continue
        if evaluation is None:
            missing_sources.append(f"app.run_evaluations:{ctx['run_id']}")
            continue
        utilization_ratio = _safe_float(run_metrics.get("utilization_ratio"))
        used_sheet_count = _safe_float(run_metrics.get("used_sheet_count"))
        unplaced_count = _safe_float(run_metrics.get("unplaced_count"))
        remnant_value = _safe_float(run_metrics.get("remnant_value"))
        candidates.append(
            {
                "run_id": ctx["run_id"],
                "rank_no": int(ctx["rank_no"]),
                "candidate_label": ctx.get("candidate_label"),
                "utilization_ratio": utilization_ratio,
                "used_sheet_count": used_sheet_count,
                "unplaced_count": unplaced_count,
                "remnant_value": remnant_value,
                "criteria_trace": {
                    "utilization_ratio_desc": [_desc_key(utilization_ratio)[0], _round6(utilization_ratio)],
                    "used_sheet_count_asc": [_asc_key(used_sheet_count)[0], _round6(used_sheet_count)],
                    "unplaced_count_asc": [_asc_key(unplaced_count)[0], _round6(unplaced_count)],
                    "remnant_value_desc": [_desc_key(remnant_value)[0], _round6(remnant_value)],
                    "rank_no_asc": int(ctx["rank_no"]),
                    "run_id_asc": str(ctx["run_id"]),
                },
            }
        )

    if not candidates:
        return _objective_response(
            objective="material-best",
            status="unavailable_missing_sources",
            batch_id=batch_id,
            run_id=None,
            rank_no=None,
            candidate_label=None,
            objective_value=None,
            objective_reason_jsonb={
                "source_tables": list(_OBJECTIVE_SOURCE_TABLES["material-best"]),
                "metric_snapshot": {},
                "ordering_trace": {
                    "ordering_rules": [
                        "utilization_ratio DESC",
                        "used_sheet_count ASC",
                        "unplaced_count ASC",
                        "remnant_value DESC",
                        "rank_no ASC",
                        "run_id ASC",
                    ],
                    "winner": None,
                },
                "used_fallbacks": [],
                "missing_sources": sorted(set(missing_sources)),
            },
        )

    criteria_names = [
        "utilization_ratio_desc",
        "used_sheet_count_asc",
        "unplaced_count_asc",
        "remnant_value_desc",
        "rank_no_asc",
        "run_id_asc",
    ]
    candidates.sort(
        key=lambda row: (
            _desc_key(_safe_float(row.get("utilization_ratio"))),
            _asc_key(_safe_float(row.get("used_sheet_count"))),
            _asc_key(_safe_float(row.get("unplaced_count"))),
            _desc_key(_safe_float(row.get("remnant_value"))),
            int(row.get("rank_no") or 0),
            str(row.get("run_id") or ""),
        )
    )
    winner = candidates[0]
    runner_up = candidates[1] if len(candidates) > 1 else None
    decisive_rule, used_fallbacks = _decisive_rule(
        winner=winner,
        runner_up=runner_up,
        criteria_names=criteria_names,
    )

    return _objective_response(
        objective="material-best",
        status="available",
        batch_id=batch_id,
        run_id=str(winner["run_id"]),
        rank_no=int(winner["rank_no"]),
        candidate_label=_sanitize_optional(winner.get("candidate_label")),
        objective_value=_safe_float(winner.get("utilization_ratio")),
        objective_reason_jsonb={
            "source_tables": list(_OBJECTIVE_SOURCE_TABLES["material-best"]),
            "metric_snapshot": {
                "utilization_ratio": _round6(_safe_float(winner.get("utilization_ratio"))),
                "used_sheet_count": _round6(_safe_float(winner.get("used_sheet_count"))),
                "unplaced_count": _round6(_safe_float(winner.get("unplaced_count"))),
                "remnant_value": _round6(_safe_float(winner.get("remnant_value"))),
                "rank_no": int(winner["rank_no"]),
            },
            "ordering_trace": {
                "ordering_rules": [
                    "utilization_ratio DESC",
                    "used_sheet_count ASC",
                    "unplaced_count ASC",
                    "remnant_value DESC",
                    "rank_no ASC",
                    "run_id ASC",
                ],
                "decisive_rule": decisive_rule,
                "winner": str(winner["run_id"]),
            },
            "used_fallbacks": used_fallbacks,
            "missing_sources": sorted(set(missing_sources)),
        },
    )


def _evaluate_time_best(*, batch_id: str, run_contexts: list[dict[str, Any]]) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    missing_sources: list[str] = []
    for ctx in run_contexts:
        run_metrics = ctx.get("run_metrics")
        run_manufacturing_metrics = ctx.get("run_manufacturing_metrics")
        evaluation = ctx.get("evaluation")
        if run_manufacturing_metrics is None:
            missing_sources.append(f"app.run_manufacturing_metrics:{ctx['run_id']}")
            continue
        if run_metrics is None:
            missing_sources.append(f"app.run_metrics:{ctx['run_id']}")
            continue
        if evaluation is None:
            missing_sources.append(f"app.run_evaluations:{ctx['run_id']}")
            continue
        estimated_process_time_s = _safe_float(run_manufacturing_metrics.get("estimated_process_time_s"))
        used_sheet_count = _safe_float(run_metrics.get("used_sheet_count"))
        utilization_ratio = _safe_float(run_metrics.get("utilization_ratio"))
        candidates.append(
            {
                "run_id": ctx["run_id"],
                "rank_no": int(ctx["rank_no"]),
                "candidate_label": ctx.get("candidate_label"),
                "estimated_process_time_s": estimated_process_time_s,
                "used_sheet_count": used_sheet_count,
                "utilization_ratio": utilization_ratio,
                "criteria_trace": {
                    "estimated_process_time_s_asc": [_asc_key(estimated_process_time_s)[0], _round6(estimated_process_time_s)],
                    "used_sheet_count_asc": [_asc_key(used_sheet_count)[0], _round6(used_sheet_count)],
                    "utilization_ratio_desc": [_desc_key(utilization_ratio)[0], _round6(utilization_ratio)],
                    "rank_no_asc": int(ctx["rank_no"]),
                    "run_id_asc": str(ctx["run_id"]),
                },
            }
        )

    if not candidates:
        return _objective_response(
            objective="time-best",
            status="unavailable_missing_sources",
            batch_id=batch_id,
            run_id=None,
            rank_no=None,
            candidate_label=None,
            objective_value=None,
            objective_reason_jsonb={
                "source_tables": list(_OBJECTIVE_SOURCE_TABLES["time-best"]),
                "metric_snapshot": {},
                "ordering_trace": {
                    "ordering_rules": [
                        "estimated_process_time_s ASC",
                        "used_sheet_count ASC",
                        "utilization_ratio DESC",
                        "rank_no ASC",
                        "run_id ASC",
                    ],
                    "winner": None,
                },
                "used_fallbacks": [],
                "missing_sources": sorted(set(missing_sources)),
            },
        )

    criteria_names = [
        "estimated_process_time_s_asc",
        "used_sheet_count_asc",
        "utilization_ratio_desc",
        "rank_no_asc",
        "run_id_asc",
    ]
    candidates.sort(
        key=lambda row: (
            _asc_key(_safe_float(row.get("estimated_process_time_s"))),
            _asc_key(_safe_float(row.get("used_sheet_count"))),
            _desc_key(_safe_float(row.get("utilization_ratio"))),
            int(row.get("rank_no") or 0),
            str(row.get("run_id") or ""),
        )
    )
    winner = candidates[0]
    runner_up = candidates[1] if len(candidates) > 1 else None
    decisive_rule, used_fallbacks = _decisive_rule(
        winner=winner,
        runner_up=runner_up,
        criteria_names=criteria_names,
    )

    return _objective_response(
        objective="time-best",
        status="available",
        batch_id=batch_id,
        run_id=str(winner["run_id"]),
        rank_no=int(winner["rank_no"]),
        candidate_label=_sanitize_optional(winner.get("candidate_label")),
        objective_value=_safe_float(winner.get("estimated_process_time_s")),
        objective_reason_jsonb={
            "source_tables": list(_OBJECTIVE_SOURCE_TABLES["time-best"]),
            "metric_snapshot": {
                "estimated_process_time_s": _round6(_safe_float(winner.get("estimated_process_time_s"))),
                "used_sheet_count": _round6(_safe_float(winner.get("used_sheet_count"))),
                "utilization_ratio": _round6(_safe_float(winner.get("utilization_ratio"))),
                "rank_no": int(winner["rank_no"]),
            },
            "ordering_trace": {
                "ordering_rules": [
                    "estimated_process_time_s ASC",
                    "used_sheet_count ASC",
                    "utilization_ratio DESC",
                    "rank_no ASC",
                    "run_id ASC",
                ],
                "decisive_rule": decisive_rule,
                "winner": str(winner["run_id"]),
            },
            "used_fallbacks": used_fallbacks,
            "missing_sources": sorted(set(missing_sources)),
        },
    )


def _evaluate_priority_best(*, batch_id: str, run_contexts: list[dict[str, Any]]) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    missing_sources: list[str] = []
    for ctx in run_contexts:
        evaluation = ctx.get("evaluation")
        run_metrics = ctx.get("run_metrics")
        if evaluation is None:
            missing_sources.append(f"app.run_evaluations:{ctx['run_id']}")
            continue
        if run_metrics is None:
            missing_sources.append(f"app.run_metrics:{ctx['run_id']}")
            continue

        projection = _build_priority_projection(
            snapshot_row=ctx.get("snapshot"),
            unplaced_rows=ctx.get("run_unplaced_rows") if isinstance(ctx.get("run_unplaced_rows"), list) else [],
        )
        if projection is None:
            missing_sources.append(f"app.nesting_run_snapshots:{ctx['run_id']}")
            continue

        priority_ratio = _safe_float(projection.get("priority_fulfilment_ratio"))
        high_priority_missing_weight = _safe_float(projection.get("high_priority_missing_weight"))
        unplaced_count = _safe_float(_as_dict(run_metrics).get("unplaced_count"))
        candidates.append(
            {
                "run_id": ctx["run_id"],
                "rank_no": int(ctx["rank_no"]),
                "candidate_label": ctx.get("candidate_label"),
                "priority_projection": projection,
                "priority_ratio": priority_ratio,
                "high_priority_missing_weight": high_priority_missing_weight,
                "unplaced_count": unplaced_count,
                "criteria_trace": {
                    "priority_fulfilment_ratio_desc": [_desc_key(priority_ratio)[0], _round6(priority_ratio)],
                    "high_priority_missing_weight_asc": [
                        _asc_key(high_priority_missing_weight)[0],
                        _round6(high_priority_missing_weight),
                    ],
                    "unplaced_count_asc": [_asc_key(unplaced_count)[0], _round6(unplaced_count)],
                    "rank_no_asc": int(ctx["rank_no"]),
                    "run_id_asc": str(ctx["run_id"]),
                },
            }
        )

    if not candidates:
        return _objective_response(
            objective="priority-best",
            status="unavailable_missing_sources",
            batch_id=batch_id,
            run_id=None,
            rank_no=None,
            candidate_label=None,
            objective_value=None,
            objective_reason_jsonb={
                "source_tables": list(_OBJECTIVE_SOURCE_TABLES["priority-best"]),
                "metric_snapshot": {},
                "ordering_trace": {
                    "ordering_rules": [
                        "priority_fulfilment_ratio DESC",
                        "high_priority_missing_weight ASC",
                        "unplaced_count ASC",
                        "rank_no ASC",
                        "run_id ASC",
                    ],
                    "winner": None,
                },
                "used_fallbacks": [],
                "missing_sources": sorted(set(missing_sources)),
            },
        )

    criteria_names = [
        "priority_fulfilment_ratio_desc",
        "high_priority_missing_weight_asc",
        "unplaced_count_asc",
        "rank_no_asc",
        "run_id_asc",
    ]
    candidates.sort(
        key=lambda row: (
            _desc_key(_safe_float(row.get("priority_ratio"))),
            _asc_key(_safe_float(row.get("high_priority_missing_weight"))),
            _asc_key(_safe_float(row.get("unplaced_count"))),
            int(row.get("rank_no") or 0),
            str(row.get("run_id") or ""),
        )
    )
    winner = candidates[0]
    runner_up = candidates[1] if len(candidates) > 1 else None
    decisive_rule, used_fallbacks = _decisive_rule(
        winner=winner,
        runner_up=runner_up,
        criteria_names=criteria_names,
    )
    priority_projection = _as_dict(winner.get("priority_projection"))

    return _objective_response(
        objective="priority-best",
        status="available",
        batch_id=batch_id,
        run_id=str(winner["run_id"]),
        rank_no=int(winner["rank_no"]),
        candidate_label=_sanitize_optional(winner.get("candidate_label")),
        objective_value=_safe_float(priority_projection.get("priority_fulfilment_ratio")),
        objective_reason_jsonb={
            "source_tables": list(_OBJECTIVE_SOURCE_TABLES["priority-best"]),
            "metric_snapshot": {
                "priority_fulfilment_ratio": _round6(_safe_float(priority_projection.get("priority_fulfilment_ratio"))),
                "high_priority_missing_weight": _round6(_safe_float(priority_projection.get("high_priority_missing_weight"))),
                "total_weighted_demand": _round6(_safe_float(priority_projection.get("total_weighted_demand"))),
                "fulfilled_weighted_qty": _round6(_safe_float(priority_projection.get("fulfilled_weighted_qty"))),
                "unplaced_count": _round6(_safe_float(winner.get("unplaced_count"))),
                "rank_no": int(winner["rank_no"]),
                "missing_top": _as_list(priority_projection.get("missing_top")),
                "formula": _as_dict(priority_projection.get("formula")),
            },
            "ordering_trace": {
                "ordering_rules": [
                    "priority_fulfilment_ratio DESC",
                    "high_priority_missing_weight ASC",
                    "unplaced_count ASC",
                    "rank_no ASC",
                    "run_id ASC",
                ],
                "decisive_rule": decisive_rule,
                "winner": str(winner["run_id"]),
            },
            "used_fallbacks": used_fallbacks,
            "missing_sources": sorted(set(missing_sources)),
        },
    )


def _evaluate_cost_best(*, batch_id: str) -> dict[str, Any]:
    return _objective_response(
        objective="cost-best",
        status="unsupported_pending_business_metrics",
        batch_id=batch_id,
        run_id=None,
        rank_no=None,
        candidate_label=None,
        objective_value=None,
        objective_reason_jsonb={
            "source_tables": list(_OBJECTIVE_SOURCE_TABLES["cost-best"]),
            "metric_snapshot": {},
            "ordering_trace": {
                "ordering_rules": [],
                "winner": None,
            },
            "used_fallbacks": [],
            "unsupported_reason": (
                "cost-best is intentionally unsupported in H3-E3-T3 because app.run_business_metrics truth is not available."
            ),
            "missing_sources": ["app.run_business_metrics"],
        },
    )


def _evaluate_objective(
    *,
    objective: str,
    batch_id: str,
    run_contexts: list[dict[str, Any]],
) -> dict[str, Any]:
    if objective == "material-best":
        return _evaluate_material_best(batch_id=batch_id, run_contexts=run_contexts)
    if objective == "time-best":
        return _evaluate_time_best(batch_id=batch_id, run_contexts=run_contexts)
    if objective == "priority-best":
        return _evaluate_priority_best(batch_id=batch_id, run_contexts=run_contexts)
    if objective == "cost-best":
        return _evaluate_cost_best(batch_id=batch_id)
    raise RunBestByObjectiveError(status_code=400, detail=f"unsupported objective: {objective}")


def list_best_by_objective(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
    batch_id: str,
    objective: str | None = None,
) -> dict[str, Any]:
    project_id_clean = _sanitize_required(project_id, field="project_id")
    batch_id_clean = _sanitize_required(batch_id, field="batch_id")
    objective_clean = _sanitize_objective(objective)

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
    run_contexts = _build_run_contexts(
        supabase=supabase,
        access_token=access_token,
        batch_id=batch_id_clean,
    )

    objectives = [objective_clean] if objective_clean is not None else list(_SUPPORTED_OBJECTIVES)
    items = [
        _evaluate_objective(objective=objective_key, batch_id=batch_id_clean, run_contexts=run_contexts)
        for objective_key in objectives
    ]

    return {
        "project": project,
        "batch": batch,
        "batch_id": batch_id_clean,
        "items": items,
        "total": len(items),
    }
