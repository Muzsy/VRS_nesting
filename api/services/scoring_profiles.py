from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from api.supabase_client import SupabaseClient


@dataclass
class ScoringProfileError(Exception):
    status_code: int
    detail: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_required(value: str, *, field: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ScoringProfileError(status_code=400, detail=f"invalid {field}")
    return cleaned


def _validate_optional_non_empty(value: str | None, *, field: str) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        raise ScoringProfileError(status_code=400, detail=f"invalid {field}")
    return cleaned


# ---- profile helpers ----


def _load_profile_for_owner(
    *,
    supabase: SupabaseClient,
    access_token: str,
    profile_id: str,
    owner_user_id: str,
) -> dict[str, Any]:
    params = {
        "select": "*",
        "id": f"eq.{profile_id}",
        "owner_user_id": f"eq.{owner_user_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.scoring_profiles", access_token=access_token, params=params)
    if not rows:
        raise ScoringProfileError(status_code=404, detail="scoring profile not found")
    return rows[0]


# ---- profile CRUD ----


def create_scoring_profile(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    name: str,
    description: str | None = None,
    lifecycle: str = "draft",
    is_active: bool = True,
    metadata_jsonb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    name_clean = _sanitize_required(name, field="name")

    now = _now_iso()
    payload: dict[str, Any] = {
        "owner_user_id": owner_user_id,
        "name": name_clean,
        "lifecycle": lifecycle,
        "is_active": is_active,
        "metadata_jsonb": metadata_jsonb or {},
        "created_at": now,
        "updated_at": now,
    }
    if description is not None:
        payload["description"] = description.strip() or None

    return supabase.insert_row(table="app.scoring_profiles", access_token=access_token, payload=payload)


def list_scoring_profiles(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
) -> list[dict[str, Any]]:
    params = {
        "select": "*",
        "owner_user_id": f"eq.{owner_user_id}",
        "order": "name.asc,created_at.asc",
    }
    return supabase.select_rows(table="app.scoring_profiles", access_token=access_token, params=params)


def get_scoring_profile(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    profile_id: str,
) -> dict[str, Any]:
    profile_id_clean = _sanitize_required(profile_id, field="profile_id")
    return _load_profile_for_owner(
        supabase=supabase,
        access_token=access_token,
        profile_id=profile_id_clean,
        owner_user_id=owner_user_id,
    )


def update_scoring_profile(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    profile_id: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    profile_id_clean = _sanitize_required(profile_id, field="profile_id")

    _load_profile_for_owner(
        supabase=supabase,
        access_token=access_token,
        profile_id=profile_id_clean,
        owner_user_id=owner_user_id,
    )

    payload: dict[str, Any] = {}

    if "name" in updates:
        payload["name"] = _sanitize_required(str(updates["name"]), field="name")
    if "description" in updates:
        raw_desc = updates["description"]
        payload["description"] = (raw_desc.strip() if isinstance(raw_desc, str) else raw_desc) or None
    if "lifecycle" in updates:
        payload["lifecycle"] = _sanitize_required(str(updates["lifecycle"]), field="lifecycle")
    if "is_active" in updates:
        payload["is_active"] = bool(updates["is_active"])
    if "metadata_jsonb" in updates:
        payload["metadata_jsonb"] = updates["metadata_jsonb"] or {}

    if not payload:
        raise ScoringProfileError(status_code=400, detail="no valid fields to update")

    payload["updated_at"] = _now_iso()

    rows = supabase.update_rows(
        table="app.scoring_profiles",
        access_token=access_token,
        payload=payload,
        filters={
            "id": f"eq.{profile_id_clean}",
            "owner_user_id": f"eq.{owner_user_id}",
        },
    )
    if not rows:
        raise ScoringProfileError(status_code=404, detail="scoring profile not found")
    return rows[0]


def delete_scoring_profile(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    profile_id: str,
) -> dict[str, Any]:
    profile_id_clean = _sanitize_required(profile_id, field="profile_id")

    row = _load_profile_for_owner(
        supabase=supabase,
        access_token=access_token,
        profile_id=profile_id_clean,
        owner_user_id=owner_user_id,
    )

    supabase.delete_rows(
        table="app.scoring_profiles",
        access_token=access_token,
        filters={
            "id": f"eq.{profile_id_clean}",
            "owner_user_id": f"eq.{owner_user_id}",
        },
    )

    return row


# ---- version helpers ----


def _next_version_no(
    *,
    supabase: SupabaseClient,
    access_token: str,
    scoring_profile_id: str,
) -> int:
    params = {
        "select": "version_no",
        "scoring_profile_id": f"eq.{scoring_profile_id}",
        "order": "version_no.desc",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.scoring_profile_versions", access_token=access_token, params=params)
    if not rows:
        return 1
    current_max = rows[0].get("version_no")
    if current_max is None:
        return 1
    return int(current_max) + 1


def _load_version_for_owner(
    *,
    supabase: SupabaseClient,
    access_token: str,
    version_id: str,
    scoring_profile_id: str,
    owner_user_id: str,
) -> dict[str, Any]:
    _load_profile_for_owner(
        supabase=supabase,
        access_token=access_token,
        profile_id=scoring_profile_id,
        owner_user_id=owner_user_id,
    )
    params = {
        "select": "*",
        "id": f"eq.{version_id}",
        "scoring_profile_id": f"eq.{scoring_profile_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.scoring_profile_versions", access_token=access_token, params=params)
    if not rows:
        raise ScoringProfileError(status_code=404, detail="scoring profile version not found")
    return rows[0]


# ---- version CRUD ----


def create_scoring_profile_version(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    scoring_profile_id: str,
    is_active: bool = True,
    weights_jsonb: dict[str, Any] | None = None,
    tie_breaker_jsonb: dict[str, Any] | None = None,
    threshold_jsonb: dict[str, Any] | None = None,
    notes: str | None = None,
    metadata_jsonb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profile_id_clean = _sanitize_required(scoring_profile_id, field="scoring_profile_id")

    _load_profile_for_owner(
        supabase=supabase,
        access_token=access_token,
        profile_id=profile_id_clean,
        owner_user_id=owner_user_id,
    )

    version_no = _next_version_no(
        supabase=supabase,
        access_token=access_token,
        scoring_profile_id=profile_id_clean,
    )

    now = _now_iso()
    payload: dict[str, Any] = {
        "scoring_profile_id": profile_id_clean,
        "owner_user_id": owner_user_id,
        "version_no": version_no,
        "lifecycle": "draft",
        "is_active": is_active,
        "weights_jsonb": weights_jsonb or {},
        "tie_breaker_jsonb": tie_breaker_jsonb or {},
        "threshold_jsonb": threshold_jsonb or {},
        "metadata_jsonb": metadata_jsonb or {},
        "created_at": now,
        "updated_at": now,
    }
    if notes is not None:
        payload["notes"] = notes.strip() or None

    return supabase.insert_row(table="app.scoring_profile_versions", access_token=access_token, payload=payload)


def list_scoring_profile_versions(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    scoring_profile_id: str,
) -> list[dict[str, Any]]:
    profile_id_clean = _sanitize_required(scoring_profile_id, field="scoring_profile_id")

    _load_profile_for_owner(
        supabase=supabase,
        access_token=access_token,
        profile_id=profile_id_clean,
        owner_user_id=owner_user_id,
    )

    params = {
        "select": "*",
        "scoring_profile_id": f"eq.{profile_id_clean}",
        "order": "version_no.desc",
    }
    return supabase.select_rows(table="app.scoring_profile_versions", access_token=access_token, params=params)


def get_scoring_profile_version(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    scoring_profile_id: str,
    version_id: str,
) -> dict[str, Any]:
    version_id_clean = _sanitize_required(version_id, field="version_id")
    profile_id_clean = _sanitize_required(scoring_profile_id, field="scoring_profile_id")
    return _load_version_for_owner(
        supabase=supabase,
        access_token=access_token,
        version_id=version_id_clean,
        scoring_profile_id=profile_id_clean,
        owner_user_id=owner_user_id,
    )


def update_scoring_profile_version(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    scoring_profile_id: str,
    version_id: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    version_id_clean = _sanitize_required(version_id, field="version_id")
    profile_id_clean = _sanitize_required(scoring_profile_id, field="scoring_profile_id")

    _load_version_for_owner(
        supabase=supabase,
        access_token=access_token,
        version_id=version_id_clean,
        scoring_profile_id=profile_id_clean,
        owner_user_id=owner_user_id,
    )

    payload: dict[str, Any] = {}

    if "is_active" in updates:
        payload["is_active"] = bool(updates["is_active"])
    if "lifecycle" in updates:
        payload["lifecycle"] = _sanitize_required(str(updates["lifecycle"]), field="lifecycle")
    if "weights_jsonb" in updates:
        payload["weights_jsonb"] = updates["weights_jsonb"] or {}
    if "tie_breaker_jsonb" in updates:
        payload["tie_breaker_jsonb"] = updates["tie_breaker_jsonb"] or {}
    if "threshold_jsonb" in updates:
        payload["threshold_jsonb"] = updates["threshold_jsonb"] or {}
    if "notes" in updates:
        raw_notes = updates["notes"]
        payload["notes"] = (raw_notes.strip() if isinstance(raw_notes, str) else raw_notes) or None
    if "metadata_jsonb" in updates:
        payload["metadata_jsonb"] = updates["metadata_jsonb"] or {}

    if not payload:
        raise ScoringProfileError(status_code=400, detail="no valid fields to update")

    payload["updated_at"] = _now_iso()

    rows = supabase.update_rows(
        table="app.scoring_profile_versions",
        access_token=access_token,
        payload=payload,
        filters={
            "id": f"eq.{version_id_clean}",
            "scoring_profile_id": f"eq.{profile_id_clean}",
        },
    )
    if not rows:
        raise ScoringProfileError(status_code=404, detail="scoring profile version not found")
    return rows[0]


def delete_scoring_profile_version(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    scoring_profile_id: str,
    version_id: str,
) -> dict[str, Any]:
    version_id_clean = _sanitize_required(version_id, field="version_id")
    profile_id_clean = _sanitize_required(scoring_profile_id, field="scoring_profile_id")

    row = _load_version_for_owner(
        supabase=supabase,
        access_token=access_token,
        version_id=version_id_clean,
        scoring_profile_id=profile_id_clean,
        owner_user_id=owner_user_id,
    )

    supabase.delete_rows(
        table="app.scoring_profile_versions",
        access_token=access_token,
        filters={
            "id": f"eq.{version_id_clean}",
            "scoring_profile_id": f"eq.{profile_id_clean}",
        },
    )

    return row
