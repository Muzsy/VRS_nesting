from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from api.supabase_client import SupabaseClient, SupabaseHTTPError


PLACEMENT_POLICIES = {"hard_first", "soft_prefer", "normal", "defer"}


@dataclass
class ProjectPartRequirementError(Exception):
    status_code: int
    detail: str


def _sanitize_required(value: str, *, field: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ProjectPartRequirementError(status_code=400, detail=f"invalid {field}")
    return cleaned


def _sanitize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _parse_required_qty(raw: int, *, field: str = "required_qty") -> int:
    if isinstance(raw, bool):
        raise ProjectPartRequirementError(status_code=400, detail=f"invalid {field}")
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ProjectPartRequirementError(status_code=400, detail=f"invalid {field}") from exc
    if value <= 0:
        raise ProjectPartRequirementError(status_code=400, detail=f"invalid {field}")
    return value


def _parse_placement_priority(raw: int, *, field: str = "placement_priority") -> int:
    if isinstance(raw, bool):
        raise ProjectPartRequirementError(status_code=400, detail=f"invalid {field}")
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ProjectPartRequirementError(status_code=400, detail=f"invalid {field}") from exc
    if value < 0 or value > 100:
        raise ProjectPartRequirementError(status_code=400, detail=f"invalid {field}")
    return value


def _parse_placement_policy(raw: str, *, field: str = "placement_policy") -> str:
    if not isinstance(raw, str):
        raise ProjectPartRequirementError(status_code=400, detail=f"invalid {field}")
    cleaned = raw.strip().lower()
    if cleaned not in PLACEMENT_POLICIES:
        raise ProjectPartRequirementError(status_code=400, detail=f"invalid {field}")
    return cleaned


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
        raise ProjectPartRequirementError(status_code=404, detail="project not found")
    return rows[0]


def _load_part_revision_for_owner(
    *,
    supabase: SupabaseClient,
    access_token: str,
    part_revision_id: str,
    owner_user_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    revision_params = {
        "select": "id,part_definition_id,revision_no,lifecycle",
        "id": f"eq.{part_revision_id}",
        "limit": "1",
    }
    revision_rows = supabase.select_rows(table="app.part_revisions", access_token=access_token, params=revision_params)
    if not revision_rows:
        raise ProjectPartRequirementError(status_code=404, detail="part revision not found")

    revision = revision_rows[0]
    part_definition_id = str(revision.get("part_definition_id") or "").strip()
    if not part_definition_id:
        raise ProjectPartRequirementError(status_code=500, detail="part revision has empty part_definition_id")

    definition_params = {
        "select": "id,owner_user_id,code,name,current_revision_id",
        "id": f"eq.{part_definition_id}",
        "owner_user_id": f"eq.{owner_user_id}",
        "limit": "1",
    }
    definition_rows = supabase.select_rows(table="app.part_definitions", access_token=access_token, params=definition_params)
    if not definition_rows:
        raise ProjectPartRequirementError(status_code=403, detail="part revision does not belong to owner")
    return revision, definition_rows[0]


def _load_existing_project_part_requirement(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
    part_revision_id: str,
) -> dict[str, Any] | None:
    params = {
        "select": "id,project_id,part_revision_id,required_qty,placement_priority,placement_policy,is_active,notes,created_at,updated_at",
        "project_id": f"eq.{project_id}",
        "part_revision_id": f"eq.{part_revision_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.project_part_requirements", access_token=access_token, params=params)
    if not rows:
        return None
    return rows[0]


def _insert_project_part_requirement(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
    part_revision_id: str,
    required_qty: int,
    placement_priority: int,
    placement_policy: str,
    is_active: bool,
    notes: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "project_id": project_id,
        "part_revision_id": part_revision_id,
        "required_qty": required_qty,
        "placement_priority": placement_priority,
        "placement_policy": placement_policy,
        "is_active": is_active,
    }
    if notes is not None:
        payload["notes"] = notes
    return supabase.insert_row(table="app.project_part_requirements", access_token=access_token, payload=payload)


def _update_project_part_requirement(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
    project_part_requirement_id: str,
    required_qty: int,
    placement_priority: int,
    placement_policy: str,
    is_active: bool,
    notes: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "required_qty": required_qty,
        "placement_priority": placement_priority,
        "placement_policy": placement_policy,
        "is_active": is_active,
        "notes": notes,
    }
    rows = supabase.update_rows(
        table="app.project_part_requirements",
        access_token=access_token,
        payload=payload,
        filters={
            "id": f"eq.{project_part_requirement_id}",
            "project_id": f"eq.{project_id}",
        },
    )
    if not rows:
        raise ProjectPartRequirementError(status_code=404, detail="project part requirement not found")
    return rows[0]


def create_or_update_project_part_requirement(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
    part_revision_id: str,
    raw_required_qty: int,
    raw_placement_priority: int = 50,
    raw_placement_policy: str = "normal",
    raw_is_active: bool = True,
    raw_notes: str | None = None,
) -> dict[str, Any]:
    project_id_clean = _sanitize_required(project_id, field="project_id")
    part_revision_id_clean = _sanitize_required(part_revision_id, field="part_revision_id")
    required_qty = _parse_required_qty(raw_required_qty)
    placement_priority = _parse_placement_priority(raw_placement_priority)
    placement_policy = _parse_placement_policy(raw_placement_policy)
    is_active = bool(raw_is_active)
    notes = _sanitize_optional(raw_notes)

    project = _load_project_for_owner(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
        owner_user_id=owner_user_id,
    )
    part_revision, part_definition = _load_part_revision_for_owner(
        supabase=supabase,
        access_token=access_token,
        part_revision_id=part_revision_id_clean,
        owner_user_id=owner_user_id,
    )

    existing_requirement = _load_existing_project_part_requirement(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
        part_revision_id=part_revision_id_clean,
    )
    was_existing_requirement = existing_requirement is not None

    if existing_requirement is not None:
        requirement_id = str(existing_requirement.get("id") or "").strip()
        if not requirement_id:
            raise ProjectPartRequirementError(status_code=500, detail="existing project part requirement has empty id")
        row = _update_project_part_requirement(
            supabase=supabase,
            access_token=access_token,
            project_id=project_id_clean,
            project_part_requirement_id=requirement_id,
            required_qty=required_qty,
            placement_priority=placement_priority,
            placement_policy=placement_policy,
            is_active=is_active,
            notes=notes,
        )
    else:
        try:
            row = _insert_project_part_requirement(
                supabase=supabase,
                access_token=access_token,
                project_id=project_id_clean,
                part_revision_id=part_revision_id_clean,
                required_qty=required_qty,
                placement_priority=placement_priority,
                placement_policy=placement_policy,
                is_active=is_active,
                notes=notes,
            )
        except SupabaseHTTPError as exc:
            is_duplicate = "project_part_requirements_project_id_part_revision_id_key" in str(exc) or "duplicate key" in str(exc)
            if not is_duplicate:
                raise
            race_existing = _load_existing_project_part_requirement(
                supabase=supabase,
                access_token=access_token,
                project_id=project_id_clean,
                part_revision_id=part_revision_id_clean,
            )
            if race_existing is None:
                raise
            race_id = str(race_existing.get("id") or "").strip()
            if not race_id:
                raise ProjectPartRequirementError(status_code=500, detail="existing project part requirement has empty id")
            was_existing_requirement = True
            row = _update_project_part_requirement(
                supabase=supabase,
                access_token=access_token,
                project_id=project_id_clean,
                project_part_requirement_id=race_id,
                required_qty=required_qty,
                placement_priority=placement_priority,
                placement_policy=placement_policy,
                is_active=is_active,
                notes=notes,
            )

    if not str(row.get("id") or "").strip():
        raise ProjectPartRequirementError(status_code=500, detail="project part requirement write returned empty id")

    return {
        "project": project,
        "part_revision": part_revision,
        "part_definition": part_definition,
        "project_part_requirement": row,
        "was_existing_requirement": was_existing_requirement,
    }


def list_project_part_requirements(
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
        "select": "id,project_id,part_revision_id,required_qty,placement_priority,placement_policy,is_active,notes,created_at,updated_at",
        "project_id": f"eq.{project_id_clean}",
        "order": "placement_priority.asc,created_at.asc",
    }
    rows = supabase.select_rows(table="app.project_part_requirements", access_token=access_token, params=params)
    return {
        "project": project,
        "items": rows,
    }
