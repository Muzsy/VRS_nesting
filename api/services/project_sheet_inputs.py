from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from api.supabase_client import SupabaseClient, SupabaseHTTPError


@dataclass
class ProjectSheetInputError(Exception):
    status_code: int
    detail: str


def _sanitize_required(value: str, *, field: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ProjectSheetInputError(status_code=400, detail=f"invalid {field}")
    return cleaned


def _sanitize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _parse_required_qty(raw: int, *, field: str = "required_qty") -> int:
    if isinstance(raw, bool):
        raise ProjectSheetInputError(status_code=400, detail=f"invalid {field}")
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ProjectSheetInputError(status_code=400, detail=f"invalid {field}") from exc
    if value <= 0:
        raise ProjectSheetInputError(status_code=400, detail=f"invalid {field}")
    return value


def _parse_placement_priority(raw: int, *, field: str = "placement_priority") -> int:
    if isinstance(raw, bool):
        raise ProjectSheetInputError(status_code=400, detail=f"invalid {field}")
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ProjectSheetInputError(status_code=400, detail=f"invalid {field}") from exc
    if value < 0 or value > 100:
        raise ProjectSheetInputError(status_code=400, detail=f"invalid {field}")
    return value


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
        raise ProjectSheetInputError(status_code=404, detail="project not found")
    return rows[0]


def _load_sheet_revision_for_owner(
    *,
    supabase: SupabaseClient,
    access_token: str,
    sheet_revision_id: str,
    owner_user_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    revision_params = {
        "select": "id,sheet_definition_id,revision_no,lifecycle",
        "id": f"eq.{sheet_revision_id}",
        "limit": "1",
    }
    revision_rows = supabase.select_rows(table="app.sheet_revisions", access_token=access_token, params=revision_params)
    if not revision_rows:
        raise ProjectSheetInputError(status_code=404, detail="sheet revision not found")

    revision = revision_rows[0]
    sheet_definition_id = str(revision.get("sheet_definition_id") or "").strip()
    if not sheet_definition_id:
        raise ProjectSheetInputError(status_code=500, detail="sheet revision has empty sheet_definition_id")

    definition_params = {
        "select": "id,owner_user_id,code,name,current_revision_id",
        "id": f"eq.{sheet_definition_id}",
        "owner_user_id": f"eq.{owner_user_id}",
        "limit": "1",
    }
    definition_rows = supabase.select_rows(table="app.sheet_definitions", access_token=access_token, params=definition_params)
    if not definition_rows:
        raise ProjectSheetInputError(status_code=403, detail="sheet revision does not belong to owner")

    return revision, definition_rows[0]


def _load_existing_project_sheet_input(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
    sheet_revision_id: str,
) -> dict[str, Any] | None:
    params = {
        "select": "id,project_id,sheet_revision_id,required_qty,is_active,is_default,placement_priority,notes,created_at,updated_at",
        "project_id": f"eq.{project_id}",
        "sheet_revision_id": f"eq.{sheet_revision_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.project_sheet_inputs", access_token=access_token, params=params)
    if not rows:
        return None
    return rows[0]


def _insert_project_sheet_input(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
    sheet_revision_id: str,
    required_qty: int,
    is_active: bool,
    is_default: bool,
    placement_priority: int,
    notes: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "project_id": project_id,
        "sheet_revision_id": sheet_revision_id,
        "required_qty": required_qty,
        "is_active": is_active,
        "is_default": is_default,
        "placement_priority": placement_priority,
    }
    if notes is not None:
        payload["notes"] = notes
    return supabase.insert_row(table="app.project_sheet_inputs", access_token=access_token, payload=payload)


def _update_project_sheet_input(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
    project_sheet_input_id: str,
    required_qty: int,
    is_active: bool,
    is_default: bool,
    placement_priority: int,
    notes: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "required_qty": required_qty,
        "is_active": is_active,
        "is_default": is_default,
        "placement_priority": placement_priority,
        "notes": notes,
    }
    rows = supabase.update_rows(
        table="app.project_sheet_inputs",
        access_token=access_token,
        payload=payload,
        filters={
            "id": f"eq.{project_sheet_input_id}",
            "project_id": f"eq.{project_id}",
        },
    )
    if not rows:
        raise ProjectSheetInputError(status_code=404, detail="project sheet input not found")
    return rows[0]


def _clear_other_defaults_in_project(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
    keep_project_sheet_input_id: str,
) -> None:
    supabase.update_rows(
        table="app.project_sheet_inputs",
        access_token=access_token,
        payload={"is_default": False},
        filters={
            "project_id": f"eq.{project_id}",
            "id": f"neq.{keep_project_sheet_input_id}",
            "is_default": "eq.true",
        },
    )


def create_or_update_project_sheet_input(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
    sheet_revision_id: str,
    raw_required_qty: int,
    raw_is_active: bool = True,
    raw_is_default: bool = False,
    raw_placement_priority: int = 50,
    raw_notes: str | None = None,
) -> dict[str, Any]:
    project_id_clean = _sanitize_required(project_id, field="project_id")
    sheet_revision_id_clean = _sanitize_required(sheet_revision_id, field="sheet_revision_id")
    required_qty = _parse_required_qty(raw_required_qty)
    placement_priority = _parse_placement_priority(raw_placement_priority)
    notes = _sanitize_optional(raw_notes)
    is_active = bool(raw_is_active)
    is_default = bool(raw_is_default)

    project = _load_project_for_owner(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
        owner_user_id=owner_user_id,
    )
    sheet_revision, sheet_definition = _load_sheet_revision_for_owner(
        supabase=supabase,
        access_token=access_token,
        sheet_revision_id=sheet_revision_id_clean,
        owner_user_id=owner_user_id,
    )

    existing_input = _load_existing_project_sheet_input(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
        sheet_revision_id=sheet_revision_id_clean,
    )

    was_existing_input = existing_input is not None
    if existing_input is not None:
        project_sheet_input_id = str(existing_input.get("id") or "").strip()
        if not project_sheet_input_id:
            raise ProjectSheetInputError(status_code=500, detail="existing project sheet input has empty id")
        row = _update_project_sheet_input(
            supabase=supabase,
            access_token=access_token,
            project_id=project_id_clean,
            project_sheet_input_id=project_sheet_input_id,
            required_qty=required_qty,
            is_active=is_active,
            is_default=is_default,
            placement_priority=placement_priority,
            notes=notes,
        )
    else:
        try:
            row = _insert_project_sheet_input(
                supabase=supabase,
                access_token=access_token,
                project_id=project_id_clean,
                sheet_revision_id=sheet_revision_id_clean,
                required_qty=required_qty,
                is_active=is_active,
                is_default=is_default,
                placement_priority=placement_priority,
                notes=notes,
            )
        except SupabaseHTTPError as exc:
            is_duplicate = "project_sheet_inputs_project_id_sheet_revision_id_key" in str(exc) or "duplicate key" in str(exc)
            if not is_duplicate:
                raise
            race_existing = _load_existing_project_sheet_input(
                supabase=supabase,
                access_token=access_token,
                project_id=project_id_clean,
                sheet_revision_id=sheet_revision_id_clean,
            )
            if race_existing is None:
                raise
            race_id = str(race_existing.get("id") or "").strip()
            if not race_id:
                raise ProjectSheetInputError(status_code=500, detail="existing project sheet input has empty id")
            was_existing_input = True
            row = _update_project_sheet_input(
                supabase=supabase,
                access_token=access_token,
                project_id=project_id_clean,
                project_sheet_input_id=race_id,
                required_qty=required_qty,
                is_active=is_active,
                is_default=is_default,
                placement_priority=placement_priority,
                notes=notes,
            )

    project_sheet_input_id = str(row.get("id") or "").strip()
    if not project_sheet_input_id:
        raise ProjectSheetInputError(status_code=500, detail="project sheet input write returned empty id")

    if is_default:
        _clear_other_defaults_in_project(
            supabase=supabase,
            access_token=access_token,
            project_id=project_id_clean,
            keep_project_sheet_input_id=project_sheet_input_id,
        )

    return {
        "project": project,
        "sheet_revision": sheet_revision,
        "sheet_definition": sheet_definition,
        "project_sheet_input": row,
        "was_existing_input": was_existing_input,
    }


def list_project_sheet_inputs(
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

    params = {
        "select": "id,project_id,sheet_revision_id,required_qty,is_active,is_default,placement_priority,notes,created_at,updated_at",
        "project_id": f"eq.{project_id_clean}",
        "order": "is_default.desc,placement_priority.asc,created_at.asc",
    }
    rows = supabase.select_rows(table="app.project_sheet_inputs", access_token=access_token, params=params)
    return {
        "project": project,
        "items": rows,
    }
