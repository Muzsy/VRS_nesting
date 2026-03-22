"""H2-E4-T3 — Manufacturing metrics calculator service.

Builds a persisted manufacturing metrics truth layer from:
* persisted run_manufacturing_plans + run_manufacturing_contours (H2-E4-T2)
* geometry_contour_classes perimeter_mm truth (H2-E2-T2)
* cut_contour_rules pierce_count truth (H2-E3-T2)

**Timing proxy model (machine-independent)**
* Default cut speed:   50 mm/s
* Default rapid speed: 200 mm/s
* Default pierce time: 0.5 s per pierce
* Formula: estimated_process_time_s =
*     (estimated_cut_length_mm / DEFAULT_CUT_SPEED_MM_S)
*   + (estimated_rapid_length_mm / DEFAULT_RAPID_SPEED_MM_S)
*   + (pierce_count * DEFAULT_PIERCE_TIME_S)

These are honest, documented, reproducible defaults — NOT calibrated
to any real machine or material profile.

**Non-negotiable scope boundaries**
* Reads ONLY persisted plan truth: run_manufacturing_contours,
  geometry_contour_classes, cut_contour_rules.
* Writes ONLY to run_manufacturing_metrics.
* Never writes to run_manufacturing_plans, run_manufacturing_contours,
  geometry_contour_classes, cut_contour_rules, run_artifacts, or
  any earlier truth table.
* No preview SVG, no export artifact, no postprocessor activation.
* No machine catalog / material resolver / pricing / costing.
* Idempotent: delete-then-insert per run_id (no duplicates).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

from api.supabase_client import SupabaseClient

logger = logging.getLogger("vrs_api.manufacturing_metrics_calculator")

# ---------------------------------------------------------------------------
# Timing proxy defaults (machine-independent, documented)
# ---------------------------------------------------------------------------

DEFAULT_CUT_SPEED_MM_S: float = 50.0
DEFAULT_RAPID_SPEED_MM_S: float = 200.0
DEFAULT_PIERCE_TIME_S: float = 0.5


@dataclass
class ManufacturingMetricsCalculatorError(Exception):
    status_code: int
    detail: str


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def calculate_manufacturing_metrics(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    run_id: str,
) -> dict[str, Any]:
    """Calculate and persist manufacturing metrics for a run.

    Returns a summary dict with the computed metrics.
    """
    run_id = _require(run_id, "run_id")
    owner_user_id = _require(owner_user_id, "owner_user_id")

    # 1) Verify run ownership
    _load_run_for_owner(
        supabase=supabase,
        access_token=access_token,
        run_id=run_id,
        owner_user_id=owner_user_id,
    )

    # 2) Load persisted manufacturing plans for this run
    plans = _load_manufacturing_plans(
        supabase=supabase,
        access_token=access_token,
        run_id=run_id,
    )
    if not plans:
        raise ManufacturingMetricsCalculatorError(
            status_code=400,
            detail="run has no persisted manufacturing plans",
        )

    # 3) Load all manufacturing contours for the plans
    plan_ids = [str(p.get("id") or "").strip() for p in plans if p.get("id")]
    contours = _load_manufacturing_contours(
        supabase=supabase,
        access_token=access_token,
        plan_ids=plan_ids,
    )

    # 4) Enrich contours with perimeter (from contour classes) and pierce_count (from rules)
    enriched = _enrich_contours(
        supabase=supabase,
        access_token=access_token,
        contours=contours,
    )

    # 5) Compute metrics
    metrics = _compute_metrics(enriched)

    # 6) Idempotent: delete existing metrics for this run, then insert
    _delete_existing_metrics(
        supabase=supabase,
        access_token=access_token,
        run_id=run_id,
    )

    metrics_row = {
        "run_id": run_id,
        "pierce_count": metrics["pierce_count"],
        "outer_contour_count": metrics["outer_contour_count"],
        "inner_contour_count": metrics["inner_contour_count"],
        "estimated_cut_length_mm": round(metrics["estimated_cut_length_mm"], 4),
        "estimated_rapid_length_mm": round(metrics["estimated_rapid_length_mm"], 4),
        "estimated_process_time_s": round(metrics["estimated_process_time_s"], 4),
        "metrics_jsonb": metrics["metrics_jsonb"],
    }

    supabase.insert_row(
        table="app.run_manufacturing_metrics",
        access_token=access_token,
        payload=metrics_row,
    )

    return metrics_row


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------


def _require(value: str | None, field: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise ManufacturingMetricsCalculatorError(
            status_code=400, detail=f"missing {field}",
        )
    return cleaned


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        f = float(value)
        return f if math.isfinite(f) else default
    except (TypeError, ValueError):
        return default


def _load_run_for_owner(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
    owner_user_id: str,
) -> dict[str, Any]:
    rows = supabase.select_rows(
        table="app.nesting_runs",
        access_token=access_token,
        params={
            "select": "id,owner_user_id,project_id,status",
            "id": f"eq.{run_id}",
            "owner_user_id": f"eq.{owner_user_id}",
            "limit": "1",
        },
    )
    if not rows:
        raise ManufacturingMetricsCalculatorError(
            status_code=404, detail="run not found or not owned by user",
        )
    return rows[0]


def _load_manufacturing_plans(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
) -> list[dict[str, Any]]:
    return supabase.select_rows(
        table="app.run_manufacturing_plans",
        access_token=access_token,
        params={
            "select": "id,run_id,sheet_id,status,summary_jsonb",
            "run_id": f"eq.{run_id}",
            "order": "sheet_id.asc",
        },
    )


def _load_manufacturing_contours(
    *,
    supabase: SupabaseClient,
    access_token: str,
    plan_ids: list[str],
) -> list[dict[str, Any]]:
    all_contours: list[dict[str, Any]] = []
    for plan_id in plan_ids:
        rows = supabase.select_rows(
            table="app.run_manufacturing_contours",
            access_token=access_token,
            params={
                "select": "id,manufacturing_plan_id,contour_index,contour_kind,"
                          "feature_class,contour_class_id,matched_rule_id,"
                          "entry_point_jsonb,cut_order_index",
                "manufacturing_plan_id": f"eq.{plan_id}",
                "order": "cut_order_index.asc",
            },
        )
        all_contours.extend(rows)
    return all_contours


def _load_contour_class(
    *,
    supabase: SupabaseClient,
    access_token: str,
    contour_class_id: str,
) -> dict[str, Any] | None:
    rows = supabase.select_rows(
        table="app.geometry_contour_classes",
        access_token=access_token,
        params={
            "select": "id,perimeter_mm,area_mm2,contour_kind",
            "id": f"eq.{contour_class_id}",
            "limit": "1",
        },
    )
    return rows[0] if rows else None


def _load_matched_rule(
    *,
    supabase: SupabaseClient,
    access_token: str,
    rule_id: str,
) -> dict[str, Any] | None:
    rows = supabase.select_rows(
        table="app.cut_contour_rules",
        access_token=access_token,
        params={
            "select": "id,pierce_count,contour_kind",
            "id": f"eq.{rule_id}",
            "limit": "1",
        },
    )
    return rows[0] if rows else None


# ---------------------------------------------------------------------------
# Enrichment + computation
# ---------------------------------------------------------------------------


@dataclass
class _EnrichedContour:
    contour_kind: str
    perimeter_mm: float
    pierce_count: int
    entry_x: float
    entry_y: float


def _enrich_contours(
    *,
    supabase: SupabaseClient,
    access_token: str,
    contours: list[dict[str, Any]],
) -> list[_EnrichedContour]:
    """Enrich each contour with perimeter and pierce_count from truth tables."""
    contour_class_cache: dict[str, dict[str, Any] | None] = {}
    rule_cache: dict[str, dict[str, Any] | None] = {}
    enriched: list[_EnrichedContour] = []

    for contour in contours:
        contour_kind = str(contour.get("contour_kind") or "")

        # Resolve perimeter from contour class
        perimeter_mm = 0.0
        contour_class_id = str(contour.get("contour_class_id") or "").strip()
        if contour_class_id:
            if contour_class_id not in contour_class_cache:
                contour_class_cache[contour_class_id] = _load_contour_class(
                    supabase=supabase,
                    access_token=access_token,
                    contour_class_id=contour_class_id,
                )
            cc = contour_class_cache.get(contour_class_id)
            if cc:
                perimeter_mm = _safe_float(cc.get("perimeter_mm"), 0.0)

        # Resolve pierce_count from matched rule
        pierce_count = 0
        rule_id = str(contour.get("matched_rule_id") or "").strip()
        if rule_id:
            if rule_id not in rule_cache:
                rule_cache[rule_id] = _load_matched_rule(
                    supabase=supabase,
                    access_token=access_token,
                    rule_id=rule_id,
                )
            rule = rule_cache.get(rule_id)
            if rule:
                pierce_count = max(0, int(rule.get("pierce_count") or 0))

        # Entry point for rapid distance
        entry_point = contour.get("entry_point_jsonb") or {}
        entry_x = _safe_float(entry_point.get("x"), 0.0)
        entry_y = _safe_float(entry_point.get("y"), 0.0)

        enriched.append(_EnrichedContour(
            contour_kind=contour_kind,
            perimeter_mm=perimeter_mm,
            pierce_count=pierce_count,
            entry_x=entry_x,
            entry_y=entry_y,
        ))

    return enriched


def _compute_metrics(enriched: list[_EnrichedContour]) -> dict[str, Any]:
    """Compute all manufacturing metrics from enriched contour list."""
    total_pierce_count = 0
    outer_contour_count = 0
    inner_contour_count = 0
    total_cut_length_mm = 0.0
    cut_length_outer = 0.0
    cut_length_inner = 0.0

    for ec in enriched:
        total_pierce_count += ec.pierce_count
        total_cut_length_mm += ec.perimeter_mm

        if ec.contour_kind == "outer":
            outer_contour_count += 1
            cut_length_outer += ec.perimeter_mm
        elif ec.contour_kind == "inner":
            inner_contour_count += 1
            cut_length_inner += ec.perimeter_mm

    # Rapid distance: sum of Euclidean distances between consecutive entry points
    total_rapid_length_mm = 0.0
    for i in range(1, len(enriched)):
        dx = enriched[i].entry_x - enriched[i - 1].entry_x
        dy = enriched[i].entry_y - enriched[i - 1].entry_y
        total_rapid_length_mm += math.sqrt(dx * dx + dy * dy)

    # Timing proxy (documented formula, machine-independent)
    cut_time_s = total_cut_length_mm / DEFAULT_CUT_SPEED_MM_S if total_cut_length_mm > 0 else 0.0
    rapid_time_s = total_rapid_length_mm / DEFAULT_RAPID_SPEED_MM_S if total_rapid_length_mm > 0 else 0.0
    pierce_time_s = total_pierce_count * DEFAULT_PIERCE_TIME_S
    estimated_process_time_s = cut_time_s + rapid_time_s + pierce_time_s

    metrics_jsonb: dict[str, Any] = {
        "calculator_scope": "h2_e4_t3",
        "contour_count_by_kind": {
            "outer": outer_contour_count,
            "inner": inner_contour_count,
        },
        "cut_length_by_contour_kind": {
            "outer_mm": round(cut_length_outer, 4),
            "inner_mm": round(cut_length_inner, 4),
            "total_mm": round(total_cut_length_mm, 4),
        },
        "timing_model": {
            "cut_time_s": round(cut_time_s, 4),
            "rapid_time_s": round(rapid_time_s, 4),
            "pierce_time_s": round(pierce_time_s, 4),
            "total_process_time_s": round(estimated_process_time_s, 4),
        },
        "timing_assumptions": {
            "cut_speed_mm_s": DEFAULT_CUT_SPEED_MM_S,
            "rapid_speed_mm_s": DEFAULT_RAPID_SPEED_MM_S,
            "pierce_time_s_per_pierce": DEFAULT_PIERCE_TIME_S,
            "model": "simple_linear_proxy",
            "note": "Machine-independent defaults. Not calibrated to any real machine or material.",
        },
    }

    return {
        "pierce_count": total_pierce_count,
        "outer_contour_count": outer_contour_count,
        "inner_contour_count": inner_contour_count,
        "estimated_cut_length_mm": total_cut_length_mm,
        "estimated_rapid_length_mm": total_rapid_length_mm,
        "estimated_process_time_s": estimated_process_time_s,
        "metrics_jsonb": metrics_jsonb,
    }


# ---------------------------------------------------------------------------
# Idempotent delete
# ---------------------------------------------------------------------------


def _delete_existing_metrics(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
) -> None:
    """Idempotent: delete existing manufacturing metrics for this run."""
    supabase.delete_rows(
        table="app.run_manufacturing_metrics",
        access_token=access_token,
        filters={"run_id": f"eq.{run_id}"},
    )
