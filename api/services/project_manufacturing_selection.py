from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from api.supabase_client import SupabaseClient, SupabaseHTTPError


@dataclass
class ProjectManufacturingSelectionError(Exception):
    status_code: int
    detail: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_required(value: str, *, field: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ProjectManufacturingSelectionError(status_code=400, detail=f"invalid {field}")
    return cleaned


def _parse_optional_positive_float(raw: Any, *, field: str) -> float | None:
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ProjectManufacturingSelectionError(status_code=400, detail=f"invalid {field}") from exc
    if value <= 0:
        raise ProjectManufacturingSelectionError(status_code=400, detail=f"invalid {field}")
    return value


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


def _is_duplicate_error(exc: SupabaseHTTPError) -> bool:
    text = str(exc)
    return "duplicate key" in text or "project_manufacturing_selection_pkey" in text


def _load_project_for_owner(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
    owner_user_id: str,
) -> dict[str, Any]:
    params = {
        "select": "id,owner_user_id,lifecycle",
        "id": f"eq.{project_id}",
        "owner_user_id": f"eq.{owner_user_id}",
        "lifecycle": "neq.archived",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.projects", access_token=access_token, params=params)
    if not rows:
        raise ProjectManufacturingSelectionError(status_code=404, detail="project not found")
    return rows[0]


def _load_manufacturing_profile_version(
    *,
    supabase: SupabaseClient,
    access_token: str,
    manufacturing_profile_version_id: str,
    owner_user_id: str,
    require_active: bool,
) -> dict[str, Any]:
    params = {
        "select": "id,manufacturing_profile_id,owner_user_id,version_no,lifecycle,is_active,machine_code,material_code,thickness_mm,kerf_mm",
        "id": f"eq.{manufacturing_profile_version_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.manufacturing_profile_versions", access_token=access_token, params=params)
    if not rows:
        raise ProjectManufacturingSelectionError(status_code=404, detail="manufacturing profile version not found")

    row = rows[0]
    version_owner_user_id = str(row.get("owner_user_id") or "").strip()
    if version_owner_user_id != owner_user_id:
        raise ProjectManufacturingSelectionError(status_code=403, detail="manufacturing profile version does not belong to owner")

    if require_active and "is_active" in row and not _normalize_bool(row.get("is_active")):
        raise ProjectManufacturingSelectionError(status_code=400, detail="manufacturing profile version is inactive")

    if not str(row.get("manufacturing_profile_id") or "").strip():
        raise ProjectManufacturingSelectionError(status_code=500, detail="manufacturing profile version has empty manufacturing_profile_id")
    return row


def _load_manufacturing_profile_for_owner(
    *,
    supabase: SupabaseClient,
    access_token: str,
    manufacturing_profile_id: str,
    owner_user_id: str,
) -> dict[str, Any]:
    params = {
        "select": "id,owner_user_id,profile_name",
        "id": f"eq.{manufacturing_profile_id}",
        "owner_user_id": f"eq.{owner_user_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.manufacturing_profiles", access_token=access_token, params=params)
    if not rows:
        raise ProjectManufacturingSelectionError(status_code=403, detail="manufacturing profile does not belong to owner")
    return rows[0]


def _load_selectable_project_technology_setup(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
) -> dict[str, Any] | None:
    params = {
        "select": "id,project_id,lifecycle,is_default,thickness_mm,machine_code,material_code",
        "project_id": f"eq.{project_id}",
        "lifecycle": "eq.approved",
        "order": "is_default.desc,created_at.asc,id.asc",
    }
    rows = supabase.select_rows(table="app.project_technology_setups", access_token=access_token, params=params)
    if not rows:
        return None

    default_rows = [row for row in rows if _normalize_bool(row.get("is_default"))]
    if len(default_rows) == 1:
        return default_rows[0]
    if len(default_rows) > 1:
        raise ProjectManufacturingSelectionError(status_code=400, detail="ambiguous default project technology setup")

    if len(rows) == 1:
        return rows[0]
    raise ProjectManufacturingSelectionError(status_code=400, detail="missing selectable project technology setup")


def _validate_technology_manufacturing_consistency(
    *,
    version: dict[str, Any],
    technology_setup: dict[str, Any] | None,
) -> None:
    if technology_setup is None:
        return

    technology_thickness = _parse_optional_positive_float(technology_setup.get("thickness_mm"), field="technology thickness_mm")
    version_thickness = _parse_optional_positive_float(version.get("thickness_mm"), field="manufacturing thickness_mm")
    if technology_thickness is None or version_thickness is None:
        return

    if abs(technology_thickness - version_thickness) > 1e-6:
        raise ProjectManufacturingSelectionError(
            status_code=400,
            detail="manufacturing profile version thickness does not match approved project technology setup",
        )


def _load_existing_project_selection(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
) -> dict[str, Any] | None:
    params = {
        "select": "project_id,active_manufacturing_profile_version_id,selected_at,selected_by",
        "project_id": f"eq.{project_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.project_manufacturing_selection", access_token=access_token, params=params)
    if not rows:
        return None
    return rows[0]


def _insert_project_selection(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
    active_manufacturing_profile_version_id: str,
    selected_by: str,
) -> dict[str, Any]:
    payload = {
        "project_id": project_id,
        "active_manufacturing_profile_version_id": active_manufacturing_profile_version_id,
        "selected_at": _now_iso(),
        "selected_by": selected_by,
    }
    return supabase.insert_row(table="app.project_manufacturing_selection", access_token=access_token, payload=payload)


def _update_project_selection(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
    active_manufacturing_profile_version_id: str,
    selected_by: str,
) -> dict[str, Any]:
    payload = {
        "active_manufacturing_profile_version_id": active_manufacturing_profile_version_id,
        "selected_at": _now_iso(),
        "selected_by": selected_by,
    }
    rows = supabase.update_rows(
        table="app.project_manufacturing_selection",
        access_token=access_token,
        payload=payload,
        filters={"project_id": f"eq.{project_id}"},
    )
    if not rows:
        raise ProjectManufacturingSelectionError(status_code=404, detail="project manufacturing selection not found")
    return rows[0]


def set_project_manufacturing_selection(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
    active_manufacturing_profile_version_id: str,
) -> dict[str, Any]:
    project_id_clean = _sanitize_required(project_id, field="project_id")
    active_version_id_clean = _sanitize_required(
        active_manufacturing_profile_version_id,
        field="active_manufacturing_profile_version_id",
    )

    project = _load_project_for_owner(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
        owner_user_id=owner_user_id,
    )
    version = _load_manufacturing_profile_version(
        supabase=supabase,
        access_token=access_token,
        manufacturing_profile_version_id=active_version_id_clean,
        owner_user_id=owner_user_id,
        require_active=True,
    )
    profile = _load_manufacturing_profile_for_owner(
        supabase=supabase,
        access_token=access_token,
        manufacturing_profile_id=str(version.get("manufacturing_profile_id") or "").strip(),
        owner_user_id=owner_user_id,
    )

    technology_setup = _load_selectable_project_technology_setup(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
    )
    _validate_technology_manufacturing_consistency(version=version, technology_setup=technology_setup)

    existing = _load_existing_project_selection(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
    )
    was_existing_selection = existing is not None

    if existing is not None:
        row = _update_project_selection(
            supabase=supabase,
            access_token=access_token,
            project_id=project_id_clean,
            active_manufacturing_profile_version_id=active_version_id_clean,
            selected_by=owner_user_id,
        )
    else:
        try:
            row = _insert_project_selection(
                supabase=supabase,
                access_token=access_token,
                project_id=project_id_clean,
                active_manufacturing_profile_version_id=active_version_id_clean,
                selected_by=owner_user_id,
            )
        except SupabaseHTTPError as exc:
            if not _is_duplicate_error(exc):
                raise
            race_existing = _load_existing_project_selection(
                supabase=supabase,
                access_token=access_token,
                project_id=project_id_clean,
            )
            if race_existing is None:
                raise
            was_existing_selection = True
            row = _update_project_selection(
                supabase=supabase,
                access_token=access_token,
                project_id=project_id_clean,
                active_manufacturing_profile_version_id=active_version_id_clean,
                selected_by=owner_user_id,
            )

    return {
        "project": project,
        "selection": row,
        "manufacturing_profile_version": version,
        "manufacturing_profile": profile,
        "was_existing_selection": was_existing_selection,
        "consistency_checked": technology_setup is not None,
    }


def get_project_manufacturing_selection(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
) -> dict[str, Any]:
    project_id_clean = _sanitize_required(project_id, field="project_id")

    project = _load_project_for_owner(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
        owner_user_id=owner_user_id,
    )

    selection = _load_existing_project_selection(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
    )
    if selection is None:
        raise ProjectManufacturingSelectionError(status_code=404, detail="project manufacturing selection not found")

    active_version_id = str(selection.get("active_manufacturing_profile_version_id") or "").strip()
    if not active_version_id:
        raise ProjectManufacturingSelectionError(status_code=500, detail="project manufacturing selection has empty version id")

    version = _load_manufacturing_profile_version(
        supabase=supabase,
        access_token=access_token,
        manufacturing_profile_version_id=active_version_id,
        owner_user_id=owner_user_id,
        require_active=False,
    )
    profile = _load_manufacturing_profile_for_owner(
        supabase=supabase,
        access_token=access_token,
        manufacturing_profile_id=str(version.get("manufacturing_profile_id") or "").strip(),
        owner_user_id=owner_user_id,
    )

    return {
        "project": project,
        "selection": selection,
        "manufacturing_profile_version": version,
        "manufacturing_profile": profile,
    }


def delete_project_manufacturing_selection(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
) -> dict[str, Any]:
    project_id_clean = _sanitize_required(project_id, field="project_id")

    project = _load_project_for_owner(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
        owner_user_id=owner_user_id,
    )

    selection = _load_existing_project_selection(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
    )
    if selection is None:
        raise ProjectManufacturingSelectionError(status_code=404, detail="project manufacturing selection not found")

    supabase.delete_rows(
        table="app.project_manufacturing_selection",
        access_token=access_token,
        filters={"project_id": f"eq.{project_id_clean}"},
    )

    return {
        "project": project,
        "selection": selection,
    }
