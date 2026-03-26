from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from api.supabase_client import SupabaseClient, SupabaseHTTPError


@dataclass
class ProjectStrategyScoringSelectionError(Exception):
    status_code: int
    detail: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_required(value: str, *, field: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ProjectStrategyScoringSelectionError(status_code=400, detail=f"invalid {field}")
    return cleaned


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
    return "duplicate key" in text or "_pkey" in text


# ---------------------------------------------------------------------------
# Common helpers
# ---------------------------------------------------------------------------


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
        raise ProjectStrategyScoringSelectionError(status_code=404, detail="project not found")
    return rows[0]


# ---------------------------------------------------------------------------
# Strategy version loader
# ---------------------------------------------------------------------------


def _load_strategy_version_for_owner(
    *,
    supabase: SupabaseClient,
    access_token: str,
    version_id: str,
    owner_user_id: str,
    require_active: bool,
) -> dict[str, Any]:
    params = {
        "select": "id,run_strategy_profile_id,owner_user_id,version_no,lifecycle,is_active",
        "id": f"eq.{version_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.run_strategy_profile_versions", access_token=access_token, params=params)
    if not rows:
        raise ProjectStrategyScoringSelectionError(status_code=404, detail="run strategy profile version not found")

    row = rows[0]
    version_owner = str(row.get("owner_user_id") or "").strip()
    if version_owner != owner_user_id:
        raise ProjectStrategyScoringSelectionError(status_code=403, detail="run strategy profile version does not belong to owner")

    if require_active and "is_active" in row and not _normalize_bool(row.get("is_active")):
        raise ProjectStrategyScoringSelectionError(status_code=400, detail="run strategy profile version is inactive")

    return row


# ---------------------------------------------------------------------------
# Scoring version loader
# ---------------------------------------------------------------------------


def _load_scoring_version_for_owner(
    *,
    supabase: SupabaseClient,
    access_token: str,
    version_id: str,
    owner_user_id: str,
    require_active: bool,
) -> dict[str, Any]:
    params = {
        "select": "id,scoring_profile_id,owner_user_id,version_no,lifecycle,is_active",
        "id": f"eq.{version_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.scoring_profile_versions", access_token=access_token, params=params)
    if not rows:
        raise ProjectStrategyScoringSelectionError(status_code=404, detail="scoring profile version not found")

    row = rows[0]
    version_owner = str(row.get("owner_user_id") or "").strip()
    if version_owner != owner_user_id:
        raise ProjectStrategyScoringSelectionError(status_code=403, detail="scoring profile version does not belong to owner")

    if require_active and "is_active" in row and not _normalize_bool(row.get("is_active")):
        raise ProjectStrategyScoringSelectionError(status_code=400, detail="scoring profile version is inactive")

    return row


# ---------------------------------------------------------------------------
# Generic selection helpers (strategy / scoring share the same pattern)
# ---------------------------------------------------------------------------


def _load_existing_selection(
    *,
    supabase: SupabaseClient,
    access_token: str,
    table: str,
    project_id: str,
    select_cols: str,
) -> dict[str, Any] | None:
    params = {
        "select": select_cols,
        "project_id": f"eq.{project_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table=table, access_token=access_token, params=params)
    if not rows:
        return None
    return rows[0]


def _insert_selection(
    *,
    supabase: SupabaseClient,
    access_token: str,
    table: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return supabase.insert_row(table=table, access_token=access_token, payload=payload)


def _update_selection(
    *,
    supabase: SupabaseClient,
    access_token: str,
    table: str,
    project_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    rows = supabase.update_rows(
        table=table,
        access_token=access_token,
        payload=payload,
        filters={"project_id": f"eq.{project_id}"},
    )
    if not rows:
        raise ProjectStrategyScoringSelectionError(status_code=404, detail="selection not found")
    return rows[0]


def _upsert_selection(
    *,
    supabase: SupabaseClient,
    access_token: str,
    table: str,
    project_id: str,
    version_id_field: str,
    version_id: str,
    selected_by: str,
    select_cols: str,
) -> tuple[dict[str, Any], bool]:
    """Create-or-replace a project-level selection. Returns (row, was_existing)."""
    insert_payload = {
        "project_id": project_id,
        version_id_field: version_id,
        "selected_at": _now_iso(),
        "selected_by": selected_by,
    }
    update_payload = {
        version_id_field: version_id,
        "selected_at": _now_iso(),
        "selected_by": selected_by,
    }

    existing = _load_existing_selection(
        supabase=supabase,
        access_token=access_token,
        table=table,
        project_id=project_id,
        select_cols=select_cols,
    )

    if existing is not None:
        row = _update_selection(
            supabase=supabase,
            access_token=access_token,
            table=table,
            project_id=project_id,
            payload=update_payload,
        )
        return row, True

    try:
        row = _insert_selection(
            supabase=supabase,
            access_token=access_token,
            table=table,
            payload=insert_payload,
        )
        return row, False
    except SupabaseHTTPError as exc:
        if not _is_duplicate_error(exc):
            raise
        # race condition: another insert happened between check and insert
        row = _update_selection(
            supabase=supabase,
            access_token=access_token,
            table=table,
            project_id=project_id,
            payload=update_payload,
        )
        return row, True


# ===================================================================
# Strategy selection public API
# ===================================================================

_STRATEGY_TABLE = "app.project_run_strategy_selection"
_STRATEGY_VERSION_FIELD = "active_run_strategy_profile_version_id"
_STRATEGY_SELECT_COLS = "project_id,active_run_strategy_profile_version_id,selected_at,selected_by"


def set_project_run_strategy_selection(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
    active_run_strategy_profile_version_id: str,
) -> dict[str, Any]:
    project_id_clean = _sanitize_required(project_id, field="project_id")
    version_id_clean = _sanitize_required(active_run_strategy_profile_version_id, field="active_run_strategy_profile_version_id")

    project = _load_project_for_owner(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
        owner_user_id=owner_user_id,
    )
    version = _load_strategy_version_for_owner(
        supabase=supabase,
        access_token=access_token,
        version_id=version_id_clean,
        owner_user_id=owner_user_id,
        require_active=True,
    )

    row, was_existing = _upsert_selection(
        supabase=supabase,
        access_token=access_token,
        table=_STRATEGY_TABLE,
        project_id=project_id_clean,
        version_id_field=_STRATEGY_VERSION_FIELD,
        version_id=version_id_clean,
        selected_by=owner_user_id,
        select_cols=_STRATEGY_SELECT_COLS,
    )

    return {
        "project": project,
        "selection": row,
        "run_strategy_profile_version": version,
        "was_existing_selection": was_existing,
    }


def get_project_run_strategy_selection(
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

    selection = _load_existing_selection(
        supabase=supabase,
        access_token=access_token,
        table=_STRATEGY_TABLE,
        project_id=project_id_clean,
        select_cols=_STRATEGY_SELECT_COLS,
    )
    if selection is None:
        raise ProjectStrategyScoringSelectionError(status_code=404, detail="project run strategy selection not found")

    active_version_id = str(selection.get(_STRATEGY_VERSION_FIELD) or "").strip()
    if not active_version_id:
        raise ProjectStrategyScoringSelectionError(status_code=500, detail="project run strategy selection has empty version id")

    version = _load_strategy_version_for_owner(
        supabase=supabase,
        access_token=access_token,
        version_id=active_version_id,
        owner_user_id=owner_user_id,
        require_active=False,
    )

    return {
        "project": project,
        "selection": selection,
        "run_strategy_profile_version": version,
    }


def delete_project_run_strategy_selection(
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

    selection = _load_existing_selection(
        supabase=supabase,
        access_token=access_token,
        table=_STRATEGY_TABLE,
        project_id=project_id_clean,
        select_cols=_STRATEGY_SELECT_COLS,
    )
    if selection is None:
        raise ProjectStrategyScoringSelectionError(status_code=404, detail="project run strategy selection not found")

    supabase.delete_rows(
        table=_STRATEGY_TABLE,
        access_token=access_token,
        filters={"project_id": f"eq.{project_id_clean}"},
    )

    return {
        "project": project,
        "selection": selection,
    }


# ===================================================================
# Scoring selection public API
# ===================================================================

_SCORING_TABLE = "app.project_scoring_selection"
_SCORING_VERSION_FIELD = "active_scoring_profile_version_id"
_SCORING_SELECT_COLS = "project_id,active_scoring_profile_version_id,selected_at,selected_by"


def set_project_scoring_selection(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
    active_scoring_profile_version_id: str,
) -> dict[str, Any]:
    project_id_clean = _sanitize_required(project_id, field="project_id")
    version_id_clean = _sanitize_required(active_scoring_profile_version_id, field="active_scoring_profile_version_id")

    project = _load_project_for_owner(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
        owner_user_id=owner_user_id,
    )
    version = _load_scoring_version_for_owner(
        supabase=supabase,
        access_token=access_token,
        version_id=version_id_clean,
        owner_user_id=owner_user_id,
        require_active=True,
    )

    row, was_existing = _upsert_selection(
        supabase=supabase,
        access_token=access_token,
        table=_SCORING_TABLE,
        project_id=project_id_clean,
        version_id_field=_SCORING_VERSION_FIELD,
        version_id=version_id_clean,
        selected_by=owner_user_id,
        select_cols=_SCORING_SELECT_COLS,
    )

    return {
        "project": project,
        "selection": row,
        "scoring_profile_version": version,
        "was_existing_selection": was_existing,
    }


def get_project_scoring_selection(
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

    selection = _load_existing_selection(
        supabase=supabase,
        access_token=access_token,
        table=_SCORING_TABLE,
        project_id=project_id_clean,
        select_cols=_SCORING_SELECT_COLS,
    )
    if selection is None:
        raise ProjectStrategyScoringSelectionError(status_code=404, detail="project scoring selection not found")

    active_version_id = str(selection.get(_SCORING_VERSION_FIELD) or "").strip()
    if not active_version_id:
        raise ProjectStrategyScoringSelectionError(status_code=500, detail="project scoring selection has empty version id")

    version = _load_scoring_version_for_owner(
        supabase=supabase,
        access_token=access_token,
        version_id=active_version_id,
        owner_user_id=owner_user_id,
        require_active=False,
    )

    return {
        "project": project,
        "selection": selection,
        "scoring_profile_version": version,
    }


def delete_project_scoring_selection(
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

    selection = _load_existing_selection(
        supabase=supabase,
        access_token=access_token,
        table=_SCORING_TABLE,
        project_id=project_id_clean,
        select_cols=_SCORING_SELECT_COLS,
    )
    if selection is None:
        raise ProjectStrategyScoringSelectionError(status_code=404, detail="project scoring selection not found")

    supabase.delete_rows(
        table=_SCORING_TABLE,
        access_token=access_token,
        filters={"project_id": f"eq.{project_id_clean}"},
    )

    return {
        "project": project,
        "selection": selection,
    }
