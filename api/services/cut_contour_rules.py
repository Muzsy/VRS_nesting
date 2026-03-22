from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from api.supabase_client import SupabaseClient


VALID_CONTOUR_KINDS = {"outer", "inner"}
VALID_LEAD_TYPES = {"none", "line", "arc"}


@dataclass
class CutContourRuleError(Exception):
    status_code: int
    detail: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_contour_kind(value: str) -> str:
    cleaned = value.strip().lower()
    if cleaned not in VALID_CONTOUR_KINDS:
        raise CutContourRuleError(
            status_code=400,
            detail=f"invalid contour_kind: must be one of {sorted(VALID_CONTOUR_KINDS)}",
        )
    return cleaned


def _validate_lead_type(value: str, *, field: str) -> str:
    cleaned = value.strip().lower()
    if cleaned not in VALID_LEAD_TYPES:
        raise CutContourRuleError(
            status_code=400,
            detail=f"invalid {field}: must be one of {sorted(VALID_LEAD_TYPES)}",
        )
    return cleaned


def _validate_optional_positive_float(raw: Any, *, field: str) -> float | None:
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise CutContourRuleError(status_code=400, detail=f"invalid {field}") from exc
    if value <= 0:
        raise CutContourRuleError(status_code=400, detail=f"{field} must be positive")
    return value


def _validate_optional_non_negative_float(raw: Any, *, field: str) -> float | None:
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise CutContourRuleError(status_code=400, detail=f"invalid {field}") from exc
    if value < 0:
        raise CutContourRuleError(status_code=400, detail=f"{field} must be non-negative")
    return value


def _validate_min_max_contour_length(
    min_val: float | None,
    max_val: float | None,
) -> None:
    if min_val is not None and max_val is not None and min_val > max_val:
        raise CutContourRuleError(
            status_code=400,
            detail="min_contour_length_mm must be <= max_contour_length_mm",
        )


def _validate_positive_int(raw: Any, *, field: str) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise CutContourRuleError(status_code=400, detail=f"invalid {field}") from exc
    if value <= 0:
        raise CutContourRuleError(status_code=400, detail=f"{field} must be positive")
    return value


def _validate_non_empty_string(value: str, *, field: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise CutContourRuleError(status_code=400, detail=f"invalid {field}")
    return cleaned


def _load_owner_rule_set(
    *,
    supabase: SupabaseClient,
    access_token: str,
    cut_rule_set_id: str,
    owner_user_id: str,
) -> dict[str, Any]:
    params = {
        "select": "id,owner_user_id",
        "id": f"eq.{cut_rule_set_id}",
        "owner_user_id": f"eq.{owner_user_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.cut_rule_sets", access_token=access_token, params=params)
    if not rows:
        raise CutContourRuleError(status_code=404, detail="cut rule set not found")
    return rows[0]


def _load_contour_rule_for_owner(
    *,
    supabase: SupabaseClient,
    access_token: str,
    rule_id: str,
    cut_rule_set_id: str,
    owner_user_id: str,
) -> dict[str, Any]:
    _load_owner_rule_set(
        supabase=supabase,
        access_token=access_token,
        cut_rule_set_id=cut_rule_set_id,
        owner_user_id=owner_user_id,
    )
    params = {
        "select": "*",
        "id": f"eq.{rule_id}",
        "cut_rule_set_id": f"eq.{cut_rule_set_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.cut_contour_rules", access_token=access_token, params=params)
    if not rows:
        raise CutContourRuleError(status_code=404, detail="cut contour rule not found")
    return rows[0]


def create_cut_contour_rule(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    cut_rule_set_id: str,
    contour_kind: str,
    feature_class: str = "default",
    lead_in_type: str = "none",
    lead_in_length_mm: float | None = None,
    lead_in_radius_mm: float | None = None,
    lead_out_type: str = "none",
    lead_out_length_mm: float | None = None,
    lead_out_radius_mm: float | None = None,
    entry_side_policy: str = "auto",
    min_contour_length_mm: float | None = None,
    max_contour_length_mm: float | None = None,
    pierce_count: int = 1,
    cut_direction: str = "cw",
    sort_order: int = 0,
    enabled: bool = True,
    metadata_jsonb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _load_owner_rule_set(
        supabase=supabase,
        access_token=access_token,
        cut_rule_set_id=cut_rule_set_id,
        owner_user_id=owner_user_id,
    )

    contour_kind_clean = _validate_contour_kind(contour_kind)
    feature_class_clean = _validate_non_empty_string(feature_class, field="feature_class")
    lead_in_type_clean = _validate_lead_type(lead_in_type, field="lead_in_type")
    lead_in_length_val = _validate_optional_positive_float(lead_in_length_mm, field="lead_in_length_mm")
    lead_in_radius_val = _validate_optional_positive_float(lead_in_radius_mm, field="lead_in_radius_mm")
    lead_out_type_clean = _validate_lead_type(lead_out_type, field="lead_out_type")
    lead_out_length_val = _validate_optional_positive_float(lead_out_length_mm, field="lead_out_length_mm")
    lead_out_radius_val = _validate_optional_positive_float(lead_out_radius_mm, field="lead_out_radius_mm")
    entry_side_clean = _validate_non_empty_string(entry_side_policy, field="entry_side_policy")
    min_len = _validate_optional_non_negative_float(min_contour_length_mm, field="min_contour_length_mm")
    max_len = _validate_optional_non_negative_float(max_contour_length_mm, field="max_contour_length_mm")
    _validate_min_max_contour_length(min_len, max_len)
    pierce_val = _validate_positive_int(pierce_count, field="pierce_count")
    cut_dir_clean = _validate_non_empty_string(cut_direction, field="cut_direction")

    now = _now_iso()
    payload: dict[str, Any] = {
        "cut_rule_set_id": cut_rule_set_id,
        "contour_kind": contour_kind_clean,
        "feature_class": feature_class_clean,
        "lead_in_type": lead_in_type_clean,
        "lead_out_type": lead_out_type_clean,
        "entry_side_policy": entry_side_clean,
        "pierce_count": pierce_val,
        "cut_direction": cut_dir_clean,
        "sort_order": sort_order,
        "enabled": enabled,
        "metadata_jsonb": metadata_jsonb or {},
        "created_at": now,
        "updated_at": now,
    }
    if lead_in_length_val is not None:
        payload["lead_in_length_mm"] = lead_in_length_val
    if lead_in_radius_val is not None:
        payload["lead_in_radius_mm"] = lead_in_radius_val
    if lead_out_length_val is not None:
        payload["lead_out_length_mm"] = lead_out_length_val
    if lead_out_radius_val is not None:
        payload["lead_out_radius_mm"] = lead_out_radius_val
    if min_len is not None:
        payload["min_contour_length_mm"] = min_len
    if max_len is not None:
        payload["max_contour_length_mm"] = max_len

    return supabase.insert_row(table="app.cut_contour_rules", access_token=access_token, payload=payload)


def list_cut_contour_rules(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    cut_rule_set_id: str,
) -> list[dict[str, Any]]:
    _load_owner_rule_set(
        supabase=supabase,
        access_token=access_token,
        cut_rule_set_id=cut_rule_set_id,
        owner_user_id=owner_user_id,
    )
    params = {
        "select": "*",
        "cut_rule_set_id": f"eq.{cut_rule_set_id}",
        "order": "sort_order.asc,created_at.asc",
    }
    return supabase.select_rows(table="app.cut_contour_rules", access_token=access_token, params=params)


def get_cut_contour_rule(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    cut_rule_set_id: str,
    rule_id: str,
) -> dict[str, Any]:
    return _load_contour_rule_for_owner(
        supabase=supabase,
        access_token=access_token,
        rule_id=rule_id,
        cut_rule_set_id=cut_rule_set_id,
        owner_user_id=owner_user_id,
    )


def update_cut_contour_rule(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    cut_rule_set_id: str,
    rule_id: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    _load_contour_rule_for_owner(
        supabase=supabase,
        access_token=access_token,
        rule_id=rule_id,
        cut_rule_set_id=cut_rule_set_id,
        owner_user_id=owner_user_id,
    )

    payload: dict[str, Any] = {}

    if "contour_kind" in updates:
        payload["contour_kind"] = _validate_contour_kind(str(updates["contour_kind"]))
    if "feature_class" in updates:
        payload["feature_class"] = _validate_non_empty_string(str(updates["feature_class"]), field="feature_class")
    if "lead_in_type" in updates:
        payload["lead_in_type"] = _validate_lead_type(str(updates["lead_in_type"]), field="lead_in_type")
    if "lead_in_length_mm" in updates:
        payload["lead_in_length_mm"] = _validate_optional_positive_float(updates["lead_in_length_mm"], field="lead_in_length_mm")
    if "lead_in_radius_mm" in updates:
        payload["lead_in_radius_mm"] = _validate_optional_positive_float(updates["lead_in_radius_mm"], field="lead_in_radius_mm")
    if "lead_out_type" in updates:
        payload["lead_out_type"] = _validate_lead_type(str(updates["lead_out_type"]), field="lead_out_type")
    if "lead_out_length_mm" in updates:
        payload["lead_out_length_mm"] = _validate_optional_positive_float(updates["lead_out_length_mm"], field="lead_out_length_mm")
    if "lead_out_radius_mm" in updates:
        payload["lead_out_radius_mm"] = _validate_optional_positive_float(updates["lead_out_radius_mm"], field="lead_out_radius_mm")
    if "entry_side_policy" in updates:
        payload["entry_side_policy"] = _validate_non_empty_string(str(updates["entry_side_policy"]), field="entry_side_policy")
    if "pierce_count" in updates:
        payload["pierce_count"] = _validate_positive_int(updates["pierce_count"], field="pierce_count")
    if "cut_direction" in updates:
        payload["cut_direction"] = _validate_non_empty_string(str(updates["cut_direction"]), field="cut_direction")
    if "sort_order" in updates:
        payload["sort_order"] = int(updates["sort_order"])
    if "enabled" in updates:
        payload["enabled"] = bool(updates["enabled"])
    if "metadata_jsonb" in updates:
        payload["metadata_jsonb"] = updates["metadata_jsonb"] or {}

    # Validate min/max contour length cross-constraint
    min_val = payload.get("min_contour_length_mm")
    max_val = payload.get("max_contour_length_mm")
    if "min_contour_length_mm" in updates:
        min_val = _validate_optional_non_negative_float(updates["min_contour_length_mm"], field="min_contour_length_mm")
        payload["min_contour_length_mm"] = min_val
    if "max_contour_length_mm" in updates:
        max_val = _validate_optional_non_negative_float(updates["max_contour_length_mm"], field="max_contour_length_mm")
        payload["max_contour_length_mm"] = max_val
    if min_val is not None and max_val is not None:
        _validate_min_max_contour_length(min_val, max_val)

    if not payload:
        raise CutContourRuleError(status_code=400, detail="no valid fields to update")

    payload["updated_at"] = _now_iso()

    rows = supabase.update_rows(
        table="app.cut_contour_rules",
        access_token=access_token,
        payload=payload,
        filters={
            "id": f"eq.{rule_id}",
            "cut_rule_set_id": f"eq.{cut_rule_set_id}",
        },
    )
    if not rows:
        raise CutContourRuleError(status_code=404, detail="cut contour rule not found")
    return rows[0]


def delete_cut_contour_rule(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    cut_rule_set_id: str,
    rule_id: str,
) -> dict[str, Any]:
    row = _load_contour_rule_for_owner(
        supabase=supabase,
        access_token=access_token,
        rule_id=rule_id,
        cut_rule_set_id=cut_rule_set_id,
        owner_user_id=owner_user_id,
    )

    supabase.delete_rows(
        table="app.cut_contour_rules",
        access_token=access_token,
        filters={
            "id": f"eq.{rule_id}",
            "cut_rule_set_id": f"eq.{cut_rule_set_id}",
        },
    )

    return row
