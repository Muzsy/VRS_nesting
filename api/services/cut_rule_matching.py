"""H2-E3-T3 — Deterministic cut-rule matching engine.

Given a ``cut_rule_set_id`` and a ``geometry_derivative_id``, this service
reads the existing ``geometry_contour_classes`` truth and the
``cut_contour_rules`` truth, then selects the best matching rule for each
contour.

**Scope boundaries (non-negotiable)**
* Read-only — never writes back to ``geometry_contour_classes`` or any other
  persisted truth table.
* No resolver — expects an explicit ``cut_rule_set_id``, does not resolve
  manufacturing profiles or project manufacturing selections.
* No plan builder — returns an in-memory matching result; does not create
  ``run_manufacturing_plans`` / ``run_manufacturing_contours``.

**Matching precedence (tie-break)**
1. ``contour_kind`` must match exactly (mandatory filter).
2. Only ``enabled = true`` rules are considered.
3. ``perimeter_mm`` must fall within ``[min_contour_length_mm, max_contour_length_mm]``
   (NULL bounds are treated as unbounded).
4. Specific ``feature_class`` match beats ``default`` fallback.
5. Lower ``sort_order`` wins.
6. Lexicographically smaller ``id`` (UUID string) as final deterministic
   tie-break.
"""

from __future__ import annotations

import logging
from typing import Any

from api.supabase_client import SupabaseClient

logger = logging.getLogger("vrs_api.cut_rule_matching")


def match_rules_for_derivative(
    *,
    supabase: SupabaseClient,
    access_token: str,
    cut_rule_set_id: str,
    geometry_derivative_id: str,
) -> dict[str, Any]:
    """Match cut-contour rules to classified contours of a derivative.

    Returns a dict with:
    * ``geometry_derivative_id``
    * ``cut_rule_set_id``
    * ``contours`` — list of per-contour matching results
    * ``matched_count`` / ``unmatched_count``
    """
    cut_rule_set_id = str(cut_rule_set_id).strip()
    geometry_derivative_id = str(geometry_derivative_id).strip()
    if not cut_rule_set_id:
        raise ValueError("missing cut_rule_set_id")
    if not geometry_derivative_id:
        raise ValueError("missing geometry_derivative_id")

    contour_classes = _load_contour_classes(
        supabase=supabase,
        access_token=access_token,
        geometry_derivative_id=geometry_derivative_id,
    )

    rules = _load_enabled_rules(
        supabase=supabase,
        access_token=access_token,
        cut_rule_set_id=cut_rule_set_id,
    )

    contour_results: list[dict[str, Any]] = []
    matched_count = 0
    unmatched_count = 0

    for cc in contour_classes:
        result = _match_single_contour(contour_class=cc, rules=rules)
        contour_results.append(result)
        if result.get("matched_rule_id"):
            matched_count += 1
        else:
            unmatched_count += 1

    return {
        "geometry_derivative_id": geometry_derivative_id,
        "cut_rule_set_id": cut_rule_set_id,
        "contours": contour_results,
        "matched_count": matched_count,
        "unmatched_count": unmatched_count,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_contour_classes(
    *,
    supabase: SupabaseClient,
    access_token: str,
    geometry_derivative_id: str,
) -> list[dict[str, Any]]:
    """Load all geometry_contour_classes rows for a derivative."""
    params = {
        "select": "*",
        "geometry_derivative_id": f"eq.{geometry_derivative_id}",
        "order": "contour_index.asc",
    }
    return supabase.select_rows(
        table="app.geometry_contour_classes",
        access_token=access_token,
        params=params,
    )


def _load_enabled_rules(
    *,
    supabase: SupabaseClient,
    access_token: str,
    cut_rule_set_id: str,
) -> list[dict[str, Any]]:
    """Load all enabled cut_contour_rules for a rule set."""
    params = {
        "select": "*",
        "cut_rule_set_id": f"eq.{cut_rule_set_id}",
        "enabled": "eq.true",
        "order": "sort_order.asc",
    }
    return supabase.select_rows(
        table="app.cut_contour_rules",
        access_token=access_token,
        params=params,
    )


def _match_single_contour(
    *,
    contour_class: dict[str, Any],
    rules: list[dict[str, Any]],
) -> dict[str, Any]:
    """Select the best matching rule for a single contour class record.

    Matching precedence:
    1. ``contour_kind`` exact match (mandatory).
    2. ``perimeter_mm`` within ``[min_contour_length_mm, max_contour_length_mm]``.
    3. Specific ``feature_class`` > ``default``.
    4. Lower ``sort_order`` wins.
    5. Lexicographic ``id`` as final tie-break.
    """
    contour_index = contour_class.get("contour_index")
    contour_kind = str(contour_class.get("contour_kind") or "").strip()
    feature_class = str(contour_class.get("feature_class") or "default").strip()
    perimeter_mm = contour_class.get("perimeter_mm")

    base = {
        "contour_index": contour_index,
        "contour_kind": contour_kind,
        "feature_class": feature_class,
    }

    # Step 1: filter by contour_kind
    kind_candidates = [
        r for r in rules
        if str(r.get("contour_kind") or "").strip() == contour_kind
    ]
    if not kind_candidates:
        return {
            **base,
            "matched_rule_id": None,
            "matched_rule_summary": None,
            "matched_via": None,
            "unmatched_reason": f"no rules for contour_kind={contour_kind}",
        }

    # Step 2: filter by perimeter range
    range_candidates = _filter_by_perimeter(kind_candidates, perimeter_mm)
    if not range_candidates:
        return {
            **base,
            "matched_rule_id": None,
            "matched_rule_summary": None,
            "matched_via": None,
            "unmatched_reason": (
                f"all rules for contour_kind={contour_kind} exclude "
                f"perimeter_mm={perimeter_mm}"
            ),
        }

    # Step 3: try specific feature_class first, then default fallback
    specific = [
        r for r in range_candidates
        if str(r.get("feature_class") or "").strip() == feature_class
        and feature_class != "default"
    ]
    if specific:
        winner = _pick_best(specific)
        return {
            **base,
            "matched_rule_id": str(winner["id"]),
            "matched_rule_summary": _rule_summary(winner),
            "matched_via": "feature_class",
            "unmatched_reason": None,
        }

    default_candidates = [
        r for r in range_candidates
        if str(r.get("feature_class") or "").strip() == "default"
    ]
    if default_candidates:
        winner = _pick_best(default_candidates)
        return {
            **base,
            "matched_rule_id": str(winner["id"]),
            "matched_rule_summary": _rule_summary(winner),
            "matched_via": "default",
            "unmatched_reason": None,
        }

    # If the contour itself has feature_class=default but no default rules
    # exist, still try exact match on "default"
    if feature_class == "default":
        exact_default = [
            r for r in range_candidates
            if str(r.get("feature_class") or "").strip() == "default"
        ]
        if exact_default:
            winner = _pick_best(exact_default)
            return {
                **base,
                "matched_rule_id": str(winner["id"]),
                "matched_rule_summary": _rule_summary(winner),
                "matched_via": "default",
                "unmatched_reason": None,
            }

    return {
        **base,
        "matched_rule_id": None,
        "matched_rule_summary": None,
        "matched_via": None,
        "unmatched_reason": (
            f"no matching feature_class={feature_class} or default rule "
            f"for contour_kind={contour_kind}"
        ),
    }


def _filter_by_perimeter(
    rules: list[dict[str, Any]],
    perimeter_mm: float | None,
) -> list[dict[str, Any]]:
    """Keep rules whose min/max contour length range covers the perimeter."""
    if perimeter_mm is None:
        # No perimeter info — skip range filtering, keep all
        return list(rules)

    perimeter = float(perimeter_mm)
    result: list[dict[str, Any]] = []
    for r in rules:
        min_len = r.get("min_contour_length_mm")
        max_len = r.get("max_contour_length_mm")
        if min_len is not None and perimeter < float(min_len):
            continue
        if max_len is not None and perimeter > float(max_len):
            continue
        result.append(r)
    return result


def _pick_best(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Deterministic tie-break among candidates.

    Sort by (sort_order ASC, id ASC) and pick the first.
    """
    return sorted(
        candidates,
        key=lambda r: (int(r.get("sort_order") or 0), str(r.get("id") or "")),
    )[0]


def _rule_summary(rule: dict[str, Any]) -> dict[str, Any]:
    """Compact summary of a matched rule for the result payload."""
    return {
        "id": str(rule.get("id") or ""),
        "contour_kind": str(rule.get("contour_kind") or ""),
        "feature_class": str(rule.get("feature_class") or ""),
        "lead_in_type": str(rule.get("lead_in_type") or ""),
        "lead_out_type": str(rule.get("lead_out_type") or ""),
        "sort_order": rule.get("sort_order"),
        "enabled": rule.get("enabled"),
    }
