from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from api.supabase_client import SupabaseClient


@dataclass
class CutRuleSetError(Exception):
    status_code: int
    detail: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_required(value: str, *, field: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise CutRuleSetError(status_code=400, detail=f"invalid {field}")
    return cleaned


def _validate_optional_non_empty(value: str | None, *, field: str) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        raise CutRuleSetError(status_code=400, detail=f"invalid {field}")
    return cleaned


def _parse_optional_positive_float(raw: Any, *, field: str) -> float | None:
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise CutRuleSetError(status_code=400, detail=f"invalid {field}") from exc
    if value <= 0:
        raise CutRuleSetError(status_code=400, detail=f"{field} must be positive")
    return value


def _next_version_no(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    name: str,
) -> int:
    """Determine next version_no for the given owner + name combination."""
    params = {
        "select": "version_no",
        "owner_user_id": f"eq.{owner_user_id}",
        "name": f"eq.{name}",
        "order": "version_no.desc",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.cut_rule_sets", access_token=access_token, params=params)
    if not rows:
        return 1
    current_max = rows[0].get("version_no")
    if current_max is None:
        return 1
    return int(current_max) + 1


def _load_cut_rule_set_for_owner(
    *,
    supabase: SupabaseClient,
    access_token: str,
    cut_rule_set_id: str,
    owner_user_id: str,
) -> dict[str, Any]:
    params = {
        "select": "*",
        "id": f"eq.{cut_rule_set_id}",
        "owner_user_id": f"eq.{owner_user_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.cut_rule_sets", access_token=access_token, params=params)
    if not rows:
        raise CutRuleSetError(status_code=404, detail="cut rule set not found")
    return rows[0]


def create_cut_rule_set(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    name: str,
    machine_code: str | None = None,
    material_code: str | None = None,
    thickness_mm: float | None = None,
    is_active: bool = True,
    notes: str | None = None,
    metadata_jsonb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    name_clean = _sanitize_required(name, field="name")
    machine_code_clean = _validate_optional_non_empty(machine_code, field="machine_code")
    material_code_clean = _validate_optional_non_empty(material_code, field="material_code")
    thickness_val = _parse_optional_positive_float(thickness_mm, field="thickness_mm")

    version_no = _next_version_no(
        supabase=supabase,
        access_token=access_token,
        owner_user_id=owner_user_id,
        name=name_clean,
    )

    now = _now_iso()
    payload: dict[str, Any] = {
        "owner_user_id": owner_user_id,
        "name": name_clean,
        "version_no": version_no,
        "is_active": is_active,
        "metadata_jsonb": metadata_jsonb or {},
        "created_at": now,
        "updated_at": now,
    }
    if machine_code_clean is not None:
        payload["machine_code"] = machine_code_clean
    if material_code_clean is not None:
        payload["material_code"] = material_code_clean
    if thickness_val is not None:
        payload["thickness_mm"] = thickness_val
    if notes is not None:
        payload["notes"] = notes.strip() or None

    return supabase.insert_row(table="app.cut_rule_sets", access_token=access_token, payload=payload)


def list_cut_rule_sets(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
) -> list[dict[str, Any]]:
    params = {
        "select": "*",
        "owner_user_id": f"eq.{owner_user_id}",
        "order": "name.asc,version_no.desc",
    }
    return supabase.select_rows(table="app.cut_rule_sets", access_token=access_token, params=params)


def get_cut_rule_set(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    cut_rule_set_id: str,
) -> dict[str, Any]:
    cut_rule_set_id_clean = _sanitize_required(cut_rule_set_id, field="cut_rule_set_id")
    return _load_cut_rule_set_for_owner(
        supabase=supabase,
        access_token=access_token,
        cut_rule_set_id=cut_rule_set_id_clean,
        owner_user_id=owner_user_id,
    )


def update_cut_rule_set(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    cut_rule_set_id: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    cut_rule_set_id_clean = _sanitize_required(cut_rule_set_id, field="cut_rule_set_id")

    _load_cut_rule_set_for_owner(
        supabase=supabase,
        access_token=access_token,
        cut_rule_set_id=cut_rule_set_id_clean,
        owner_user_id=owner_user_id,
    )

    payload: dict[str, Any] = {}

    if "is_active" in updates:
        payload["is_active"] = bool(updates["is_active"])
    if "notes" in updates:
        raw_notes = updates["notes"]
        payload["notes"] = (raw_notes.strip() if isinstance(raw_notes, str) else raw_notes) or None
    if "metadata_jsonb" in updates:
        payload["metadata_jsonb"] = updates["metadata_jsonb"] or {}
    if "machine_code" in updates:
        mc = updates["machine_code"]
        if mc is not None:
            payload["machine_code"] = _sanitize_required(str(mc), field="machine_code")
        else:
            payload["machine_code"] = None
    if "material_code" in updates:
        mc = updates["material_code"]
        if mc is not None:
            payload["material_code"] = _sanitize_required(str(mc), field="material_code")
        else:
            payload["material_code"] = None
    if "thickness_mm" in updates:
        payload["thickness_mm"] = _parse_optional_positive_float(updates["thickness_mm"], field="thickness_mm")

    if not payload:
        raise CutRuleSetError(status_code=400, detail="no valid fields to update")

    payload["updated_at"] = _now_iso()

    rows = supabase.update_rows(
        table="app.cut_rule_sets",
        access_token=access_token,
        payload=payload,
        filters={
            "id": f"eq.{cut_rule_set_id_clean}",
            "owner_user_id": f"eq.{owner_user_id}",
        },
    )
    if not rows:
        raise CutRuleSetError(status_code=404, detail="cut rule set not found")
    return rows[0]


def delete_cut_rule_set(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    cut_rule_set_id: str,
) -> dict[str, Any]:
    cut_rule_set_id_clean = _sanitize_required(cut_rule_set_id, field="cut_rule_set_id")

    row = _load_cut_rule_set_for_owner(
        supabase=supabase,
        access_token=access_token,
        cut_rule_set_id=cut_rule_set_id_clean,
        owner_user_id=owner_user_id,
    )

    supabase.delete_rows(
        table="app.cut_rule_sets",
        access_token=access_token,
        filters={
            "id": f"eq.{cut_rule_set_id_clean}",
            "owner_user_id": f"eq.{owner_user_id}",
        },
    )

    return row
