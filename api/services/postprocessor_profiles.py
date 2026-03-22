from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from api.supabase_client import SupabaseClient


@dataclass
class PostprocessorProfileError(Exception):
    status_code: int
    detail: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_required(value: str, *, field: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise PostprocessorProfileError(status_code=400, detail=f"invalid {field}")
    return cleaned


def _validate_optional_non_empty(value: str | None, *, field: str) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        raise PostprocessorProfileError(status_code=400, detail=f"invalid {field}")
    return cleaned


def _parse_positive_int(raw: Any, *, field: str) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise PostprocessorProfileError(status_code=400, detail=f"invalid {field}") from exc
    if value <= 0:
        raise PostprocessorProfileError(status_code=400, detail=f"{field} must be positive")
    return value


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
    rows = supabase.select_rows(table="app.postprocessor_profiles", access_token=access_token, params=params)
    if not rows:
        raise PostprocessorProfileError(status_code=404, detail="postprocessor profile not found")
    return rows[0]


# ---- profile CRUD ----


def create_postprocessor_profile(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    profile_code: str,
    display_name: str,
    adapter_key: str = "generic",
    is_active: bool = True,
    notes: str | None = None,
    metadata_jsonb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profile_code_clean = _sanitize_required(profile_code, field="profile_code")
    display_name_clean = _sanitize_required(display_name, field="display_name")
    adapter_key_clean = _sanitize_required(adapter_key, field="adapter_key")

    now = _now_iso()
    payload: dict[str, Any] = {
        "owner_user_id": owner_user_id,
        "profile_code": profile_code_clean,
        "display_name": display_name_clean,
        "adapter_key": adapter_key_clean,
        "is_active": is_active,
        "metadata_jsonb": metadata_jsonb or {},
        "created_at": now,
        "updated_at": now,
    }
    if notes is not None:
        payload["notes"] = notes.strip() or None

    return supabase.insert_row(table="app.postprocessor_profiles", access_token=access_token, payload=payload)


def list_postprocessor_profiles(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
) -> list[dict[str, Any]]:
    params = {
        "select": "*",
        "owner_user_id": f"eq.{owner_user_id}",
        "order": "profile_code.asc,created_at.asc",
    }
    return supabase.select_rows(table="app.postprocessor_profiles", access_token=access_token, params=params)


def get_postprocessor_profile(
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


def update_postprocessor_profile(
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

    if "display_name" in updates:
        payload["display_name"] = _sanitize_required(str(updates["display_name"]), field="display_name")
    if "adapter_key" in updates:
        payload["adapter_key"] = _sanitize_required(str(updates["adapter_key"]), field="adapter_key")
    if "is_active" in updates:
        payload["is_active"] = bool(updates["is_active"])
    if "notes" in updates:
        raw_notes = updates["notes"]
        payload["notes"] = (raw_notes.strip() if isinstance(raw_notes, str) else raw_notes) or None
    if "metadata_jsonb" in updates:
        payload["metadata_jsonb"] = updates["metadata_jsonb"] or {}

    if not payload:
        raise PostprocessorProfileError(status_code=400, detail="no valid fields to update")

    payload["updated_at"] = _now_iso()

    rows = supabase.update_rows(
        table="app.postprocessor_profiles",
        access_token=access_token,
        payload=payload,
        filters={
            "id": f"eq.{profile_id_clean}",
            "owner_user_id": f"eq.{owner_user_id}",
        },
    )
    if not rows:
        raise PostprocessorProfileError(status_code=404, detail="postprocessor profile not found")
    return rows[0]


def delete_postprocessor_profile(
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
        table="app.postprocessor_profiles",
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
    postprocessor_profile_id: str,
) -> int:
    params = {
        "select": "version_no",
        "postprocessor_profile_id": f"eq.{postprocessor_profile_id}",
        "order": "version_no.desc",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.postprocessor_profile_versions", access_token=access_token, params=params)
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
    postprocessor_profile_id: str,
    owner_user_id: str,
) -> dict[str, Any]:
    _load_profile_for_owner(
        supabase=supabase,
        access_token=access_token,
        profile_id=postprocessor_profile_id,
        owner_user_id=owner_user_id,
    )
    params = {
        "select": "*",
        "id": f"eq.{version_id}",
        "postprocessor_profile_id": f"eq.{postprocessor_profile_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.postprocessor_profile_versions", access_token=access_token, params=params)
    if not rows:
        raise PostprocessorProfileError(status_code=404, detail="postprocessor profile version not found")
    return rows[0]


# ---- version CRUD ----


def create_postprocessor_profile_version(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    postprocessor_profile_id: str,
    adapter_key: str = "generic",
    output_format: str = "json",
    schema_version: str = "v1",
    is_active: bool = True,
    config_jsonb: dict[str, Any] | None = None,
    notes: str | None = None,
    metadata_jsonb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profile_id_clean = _sanitize_required(postprocessor_profile_id, field="postprocessor_profile_id")

    _load_profile_for_owner(
        supabase=supabase,
        access_token=access_token,
        profile_id=profile_id_clean,
        owner_user_id=owner_user_id,
    )

    adapter_key_clean = _sanitize_required(adapter_key, field="adapter_key")
    output_format_clean = _sanitize_required(output_format, field="output_format")
    schema_version_clean = _sanitize_required(schema_version, field="schema_version")

    version_no = _next_version_no(
        supabase=supabase,
        access_token=access_token,
        postprocessor_profile_id=profile_id_clean,
    )

    now = _now_iso()
    payload: dict[str, Any] = {
        "postprocessor_profile_id": profile_id_clean,
        "owner_user_id": owner_user_id,
        "version_no": version_no,
        "lifecycle": "draft",
        "is_active": is_active,
        "adapter_key": adapter_key_clean,
        "output_format": output_format_clean,
        "schema_version": schema_version_clean,
        "config_jsonb": config_jsonb or {},
        "metadata_jsonb": metadata_jsonb or {},
        "created_at": now,
        "updated_at": now,
    }
    if notes is not None:
        payload["notes"] = notes.strip() or None

    return supabase.insert_row(table="app.postprocessor_profile_versions", access_token=access_token, payload=payload)


def list_postprocessor_profile_versions(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    postprocessor_profile_id: str,
) -> list[dict[str, Any]]:
    profile_id_clean = _sanitize_required(postprocessor_profile_id, field="postprocessor_profile_id")

    _load_profile_for_owner(
        supabase=supabase,
        access_token=access_token,
        profile_id=profile_id_clean,
        owner_user_id=owner_user_id,
    )

    params = {
        "select": "*",
        "postprocessor_profile_id": f"eq.{profile_id_clean}",
        "order": "version_no.desc",
    }
    return supabase.select_rows(table="app.postprocessor_profile_versions", access_token=access_token, params=params)


def get_postprocessor_profile_version(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    postprocessor_profile_id: str,
    version_id: str,
) -> dict[str, Any]:
    version_id_clean = _sanitize_required(version_id, field="version_id")
    profile_id_clean = _sanitize_required(postprocessor_profile_id, field="postprocessor_profile_id")
    return _load_version_for_owner(
        supabase=supabase,
        access_token=access_token,
        version_id=version_id_clean,
        postprocessor_profile_id=profile_id_clean,
        owner_user_id=owner_user_id,
    )


def update_postprocessor_profile_version(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    postprocessor_profile_id: str,
    version_id: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    version_id_clean = _sanitize_required(version_id, field="version_id")
    profile_id_clean = _sanitize_required(postprocessor_profile_id, field="postprocessor_profile_id")

    _load_version_for_owner(
        supabase=supabase,
        access_token=access_token,
        version_id=version_id_clean,
        postprocessor_profile_id=profile_id_clean,
        owner_user_id=owner_user_id,
    )

    payload: dict[str, Any] = {}

    if "adapter_key" in updates:
        payload["adapter_key"] = _sanitize_required(str(updates["adapter_key"]), field="adapter_key")
    if "output_format" in updates:
        payload["output_format"] = _sanitize_required(str(updates["output_format"]), field="output_format")
    if "schema_version" in updates:
        payload["schema_version"] = _sanitize_required(str(updates["schema_version"]), field="schema_version")
    if "is_active" in updates:
        payload["is_active"] = bool(updates["is_active"])
    if "lifecycle" in updates:
        payload["lifecycle"] = _sanitize_required(str(updates["lifecycle"]), field="lifecycle")
    if "config_jsonb" in updates:
        payload["config_jsonb"] = updates["config_jsonb"] or {}
    if "notes" in updates:
        raw_notes = updates["notes"]
        payload["notes"] = (raw_notes.strip() if isinstance(raw_notes, str) else raw_notes) or None
    if "metadata_jsonb" in updates:
        payload["metadata_jsonb"] = updates["metadata_jsonb"] or {}

    if not payload:
        raise PostprocessorProfileError(status_code=400, detail="no valid fields to update")

    payload["updated_at"] = _now_iso()

    rows = supabase.update_rows(
        table="app.postprocessor_profile_versions",
        access_token=access_token,
        payload=payload,
        filters={
            "id": f"eq.{version_id_clean}",
            "postprocessor_profile_id": f"eq.{profile_id_clean}",
        },
    )
    if not rows:
        raise PostprocessorProfileError(status_code=404, detail="postprocessor profile version not found")
    return rows[0]


def delete_postprocessor_profile_version(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    postprocessor_profile_id: str,
    version_id: str,
) -> dict[str, Any]:
    version_id_clean = _sanitize_required(version_id, field="version_id")
    profile_id_clean = _sanitize_required(postprocessor_profile_id, field="postprocessor_profile_id")

    row = _load_version_for_owner(
        supabase=supabase,
        access_token=access_token,
        version_id=version_id_clean,
        postprocessor_profile_id=profile_id_clean,
        owner_user_id=owner_user_id,
    )

    supabase.delete_rows(
        table="app.postprocessor_profile_versions",
        access_token=access_token,
        filters={
            "id": f"eq.{version_id_clean}",
            "postprocessor_profile_id": f"eq.{profile_id_clean}",
        },
    )

    return row
