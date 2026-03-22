"""H2-E4-T2 — Manufacturing plan builder service.

Builds persisted manufacturing plan truth from:
* run snapshot (manufacturing_manifest_jsonb)
* run projection (run_layout_sheets + run_layout_placements)
* manufacturing_canonical derivatives (part_revisions.selected_manufacturing_derivative_id)
* contour classification (geometry_contour_classes)
* explicit cut_rule_set_id (NO resolver logic)
* cut_rule_matching engine (read-only reuse)

**Non-negotiable scope boundaries**
* Snapshot-first: reads snapshot truth, never live project_manufacturing_selection.
* Explicit cut_rule_set_id input — no hidden resolver.
* Uses existing cut_rule_matching.py — no matching logic duplication.
* Writes ONLY to run_manufacturing_plans / run_manufacturing_contours.
* Never writes to geometry_contour_classes, cut_contour_rules, run_artifacts,
  or any earlier truth table.
* No preview SVG, no export artifact, no postprocessor activation.
* Idempotent: delete-then-insert per run (no duplicates).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

from api.services.cut_rule_matching import match_rules_for_derivative
from api.supabase_client import SupabaseClient

logger = logging.getLogger("vrs_api.manufacturing_plan_builder")


@dataclass
class ManufacturingPlanBuilderError(Exception):
    status_code: int
    detail: str


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def build_manufacturing_plan(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    run_id: str,
    cut_rule_set_id: str,
) -> dict[str, Any]:
    """Build persisted manufacturing plan for a run.

    Returns a summary dict with created plan/contour counts.
    """
    run_id = _require(run_id, "run_id")
    cut_rule_set_id = _require(cut_rule_set_id, "cut_rule_set_id")
    owner_user_id = _require(owner_user_id, "owner_user_id")

    # 1) Load run (owner-scoped)
    run = _load_run_for_owner(
        supabase=supabase,
        access_token=access_token,
        run_id=run_id,
        owner_user_id=owner_user_id,
    )

    # 2) Load snapshot and validate manufacturing selection
    snapshot = _load_snapshot(
        supabase=supabase,
        access_token=access_token,
        run_id=run_id,
    )
    mfg_manifest = snapshot.get("manufacturing_manifest_jsonb")
    if not isinstance(mfg_manifest, dict):
        raise ManufacturingPlanBuilderError(
            status_code=400,
            detail="snapshot missing manufacturing_manifest_jsonb",
        )
    if not mfg_manifest.get("selection_present"):
        raise ManufacturingPlanBuilderError(
            status_code=400,
            detail="snapshot has no manufacturing selection",
        )

    manufacturing_profile_version_id = str(
        mfg_manifest.get("active_manufacturing_profile_version_id") or ""
    ).strip() or None

    # 3) Load projection sheets + placements
    sheets = _load_sheets(supabase=supabase, access_token=access_token, run_id=run_id)
    if not sheets:
        raise ManufacturingPlanBuilderError(
            status_code=400,
            detail="run has no projection sheets",
        )

    placements = _load_placements(supabase=supabase, access_token=access_token, run_id=run_id)

    # 4) Resolve manufacturing derivative per placement
    placement_derivatives = _resolve_manufacturing_derivatives(
        supabase=supabase,
        access_token=access_token,
        placements=placements,
    )

    # 5) Match rules per derivative (using existing cut_rule_matching service)
    matching_cache: dict[str, dict[str, Any]] = {}
    for derivative_id in set(placement_derivatives.values()):
        if derivative_id and derivative_id not in matching_cache:
            matching_cache[derivative_id] = match_rules_for_derivative(
                supabase=supabase,
                access_token=access_token,
                cut_rule_set_id=cut_rule_set_id,
                geometry_derivative_id=derivative_id,
            )

    # 6) Idempotent: delete existing plans for this run
    _delete_existing_plans(supabase=supabase, access_token=access_token, run_id=run_id)

    # 7) Build and persist per-sheet plans + per-contour records
    total_plans = 0
    total_contours = 0
    global_cut_order = 0

    for sheet in sheets:
        sheet_id = str(sheet.get("id") or "").strip()
        if not sheet_id:
            continue

        sheet_placements = [
            p for p in placements
            if str(p.get("sheet_id") or "").strip() == sheet_id
        ]

        # Create plan record
        plan_summary = {
            "placement_count": len(sheet_placements),
            "builder_scope": "h2_e4_t2",
        }
        plan = supabase.insert_row(
            table="app.run_manufacturing_plans",
            access_token=access_token,
            payload={
                "run_id": run_id,
                "sheet_id": sheet_id,
                "manufacturing_profile_version_id": manufacturing_profile_version_id,
                "cut_rule_set_id": cut_rule_set_id,
                "status": "generated",
                "summary_jsonb": plan_summary,
            },
        )
        plan_id = str(plan.get("id") or "").strip()
        total_plans += 1

        # Deterministic placement ordering for cut_order_index
        sorted_placements = sorted(
            sheet_placements,
            key=lambda p: (
                int(p.get("placement_index") or 0),
                str(p.get("id") or ""),
            ),
        )

        for placement in sorted_placements:
            placement_id = str(placement.get("id") or "").strip()
            derivative_id = placement_derivatives.get(placement_id)

            if not derivative_id:
                logger.warning(
                    "skip_placement_no_manufacturing_derivative placement_id=%s",
                    placement_id,
                )
                continue

            matching_result = matching_cache.get(derivative_id, {})
            contours = matching_result.get("contours", [])

            # Get transform for entry point computation
            transform = placement.get("transform_jsonb") or {}
            tx = _safe_float(transform.get("x"), 0.0)
            ty = _safe_float(transform.get("y"), 0.0)
            rotation_deg = _safe_float(transform.get("rotation_deg"), 0.0)

            # Deterministic contour ordering
            sorted_contours = sorted(
                contours,
                key=lambda c: (
                    int(c.get("contour_index") or 0),
                    str(c.get("contour_kind") or ""),
                ),
            )

            for contour in sorted_contours:
                contour_index = contour.get("contour_index")
                contour_kind = str(contour.get("contour_kind") or "")
                feature_class = str(contour.get("feature_class") or "default")
                matched_rule_id = contour.get("matched_rule_id")
                rule_summary = contour.get("matched_rule_summary") or {}

                # Resolve contour_class_id from geometry_contour_classes
                contour_class_id = _resolve_contour_class_id(
                    supabase=supabase,
                    access_token=access_token,
                    geometry_derivative_id=derivative_id,
                    contour_index=contour_index,
                )

                # Basic machine-independent entry point (transformed)
                entry_point = _compute_entry_point(
                    tx=tx, ty=ty, rotation_deg=rotation_deg,
                )

                # Lead-in/lead-out from matched rule (structured descriptor, not geometry)
                lead_in = _build_lead_descriptor(rule_summary, direction="in")
                lead_out = _build_lead_descriptor(rule_summary, direction="out")

                contour_metadata = {
                    "builder_scope": "h2_e4_t2",
                    "matched_via": contour.get("matched_via"),
                    "unmatched_reason": contour.get("unmatched_reason"),
                }

                supabase.insert_row(
                    table="app.run_manufacturing_contours",
                    access_token=access_token,
                    payload={
                        "manufacturing_plan_id": plan_id,
                        "placement_id": placement_id,
                        "geometry_derivative_id": derivative_id,
                        "contour_class_id": contour_class_id,
                        "matched_rule_id": matched_rule_id,
                        "contour_index": contour_index,
                        "contour_kind": contour_kind,
                        "feature_class": feature_class,
                        "entry_point_jsonb": entry_point,
                        "lead_in_jsonb": lead_in,
                        "lead_out_jsonb": lead_out,
                        "cut_order_index": global_cut_order,
                        "metadata_jsonb": contour_metadata,
                    },
                )
                global_cut_order += 1
                total_contours += 1

    return {
        "run_id": run_id,
        "cut_rule_set_id": cut_rule_set_id,
        "manufacturing_profile_version_id": manufacturing_profile_version_id,
        "plans_created": total_plans,
        "contours_created": total_contours,
    }


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------


def _require(value: str | None, field: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise ManufacturingPlanBuilderError(status_code=400, detail=f"missing {field}")
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
        raise ManufacturingPlanBuilderError(
            status_code=404, detail="run not found or not owned by user",
        )
    return rows[0]


def _load_snapshot(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
) -> dict[str, Any]:
    rows = supabase.select_rows(
        table="app.nesting_run_snapshots",
        access_token=access_token,
        params={
            "select": "id,run_id,manufacturing_manifest_jsonb,includes_manufacturing",
            "run_id": f"eq.{run_id}",
            "limit": "1",
        },
    )
    if not rows:
        raise ManufacturingPlanBuilderError(
            status_code=404, detail="snapshot not found for run",
        )
    return rows[0]


def _load_sheets(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
) -> list[dict[str, Any]]:
    return supabase.select_rows(
        table="app.run_layout_sheets",
        access_token=access_token,
        params={
            "select": "id,run_id,sheet_index,sheet_revision_id,width_mm,height_mm,metadata_jsonb",
            "run_id": f"eq.{run_id}",
            "order": "sheet_index.asc",
        },
    )


def _load_placements(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
) -> list[dict[str, Any]]:
    return supabase.select_rows(
        table="app.run_layout_placements",
        access_token=access_token,
        params={
            "select": "id,run_id,sheet_id,placement_index,part_revision_id,transform_jsonb,bbox_jsonb,metadata_jsonb",
            "run_id": f"eq.{run_id}",
            "order": "sheet_id.asc,placement_index.asc",
        },
    )


def _resolve_manufacturing_derivatives(
    *,
    supabase: SupabaseClient,
    access_token: str,
    placements: list[dict[str, Any]],
) -> dict[str, str]:
    """Map placement_id -> manufacturing derivative_id via part_revisions."""
    result: dict[str, str] = {}
    part_rev_cache: dict[str, str | None] = {}

    for p in placements:
        placement_id = str(p.get("id") or "").strip()
        part_revision_id = str(p.get("part_revision_id") or "").strip()
        if not placement_id or not part_revision_id:
            continue

        if part_revision_id not in part_rev_cache:
            rows = supabase.select_rows(
                table="app.part_revisions",
                access_token=access_token,
                params={
                    "select": "id,selected_manufacturing_derivative_id",
                    "id": f"eq.{part_revision_id}",
                    "limit": "1",
                },
            )
            if rows:
                mfg_deriv_id = str(rows[0].get("selected_manufacturing_derivative_id") or "").strip()
                part_rev_cache[part_revision_id] = mfg_deriv_id or None
            else:
                part_rev_cache[part_revision_id] = None

        derivative_id = part_rev_cache.get(part_revision_id)
        if derivative_id:
            result[placement_id] = derivative_id

    return result


def _resolve_contour_class_id(
    *,
    supabase: SupabaseClient,
    access_token: str,
    geometry_derivative_id: str,
    contour_index: int | None,
) -> str | None:
    """Look up the contour_class record id for audit FK."""
    if contour_index is None:
        return None
    rows = supabase.select_rows(
        table="app.geometry_contour_classes",
        access_token=access_token,
        params={
            "select": "id",
            "geometry_derivative_id": f"eq.{geometry_derivative_id}",
            "contour_index": f"eq.{contour_index}",
            "limit": "1",
        },
    )
    if rows:
        return str(rows[0].get("id") or "").strip() or None
    return None


def _delete_existing_plans(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
) -> None:
    """Idempotent: delete all existing manufacturing plans (cascade deletes contours)."""
    supabase.delete_rows(
        table="app.run_manufacturing_plans",
        access_token=access_token,
        filters={"run_id": f"eq.{run_id}"},
    )


# ---------------------------------------------------------------------------
# Entry point / lead / cut-order helpers
# ---------------------------------------------------------------------------


def _compute_entry_point(
    *,
    tx: float,
    ty: float,
    rotation_deg: float,
) -> dict[str, Any]:
    """Basic machine-independent entry point descriptor.

    In this task scope, we provide the placement transform as the entry
    reference. Real machine-ready entry geometry is postprocessor scope.
    """
    return {
        "x": round(tx, 6),
        "y": round(ty, 6),
        "rotation_deg": round(rotation_deg, 6),
        "source": "placement_transform",
    }


def _build_lead_descriptor(
    rule_summary: dict[str, Any],
    *,
    direction: str,
) -> dict[str, Any]:
    """Build a structured lead-in or lead-out descriptor from matched rule.

    This is NOT machine-ready geometry — just a structured parameter
    descriptor for the plan truth layer.
    """
    prefix = f"lead_{direction}"
    lead_type = str(rule_summary.get(f"{prefix}_type") or "none")
    return {
        "type": lead_type,
        "source": "matched_rule",
    }
