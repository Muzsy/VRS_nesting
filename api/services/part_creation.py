from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from api.supabase_client import SupabaseClient


@dataclass
class PartCreationError(Exception):
    status_code: int
    detail: str


def _sanitize_required(value: str, *, field: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise PartCreationError(status_code=400, detail=f"invalid {field}")
    return cleaned


def _sanitize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


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
        raise PartCreationError(status_code=404, detail="project not found")
    return rows[0]


def _load_geometry_revision(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
    geometry_revision_id: str,
) -> dict[str, Any]:
    params = {
        "select": "id,project_id,status,canonical_hash_sha256",
        "id": f"eq.{geometry_revision_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.geometry_revisions", access_token=access_token, params=params)
    if not rows:
        raise PartCreationError(status_code=404, detail="geometry revision not found")

    row = rows[0]
    row_project_id = str(row.get("project_id") or "").strip()
    if row_project_id != project_id:
        raise PartCreationError(status_code=403, detail="geometry revision does not belong to project")

    status = str(row.get("status") or "").strip().lower()
    if status != "validated":
        raise PartCreationError(status_code=400, detail=f"geometry revision is not validated (status={status or '<empty>'})")
    return row


def _load_nesting_derivative(
    *,
    supabase: SupabaseClient,
    access_token: str,
    geometry_revision_id: str,
) -> dict[str, Any]:
    params = {
        "select": "id,geometry_revision_id,derivative_kind",
        "geometry_revision_id": f"eq.{geometry_revision_id}",
        "derivative_kind": "eq.nesting_canonical",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.geometry_derivatives", access_token=access_token, params=params)
    if not rows:
        raise PartCreationError(status_code=400, detail="missing nesting_canonical derivative for geometry revision")
    return rows[0]


def _load_manufacturing_derivative(
    *,
    supabase: SupabaseClient,
    access_token: str,
    geometry_revision_id: str,
) -> dict[str, Any] | None:
    """Load the manufacturing_canonical derivative for the given geometry revision.

    Returns None if no manufacturing derivative exists yet (optional binding).
    """
    params = {
        "select": "id,geometry_revision_id,derivative_kind",
        "geometry_revision_id": f"eq.{geometry_revision_id}",
        "derivative_kind": "eq.manufacturing_canonical",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.geometry_derivatives", access_token=access_token, params=params)
    if not rows:
        return None
    return rows[0]


def _load_existing_part_definition(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    code: str,
) -> dict[str, Any] | None:
    params = {
        "select": "id,owner_user_id,code,name,description,current_revision_id",
        "owner_user_id": f"eq.{owner_user_id}",
        "code": f"eq.{code}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.part_definitions", access_token=access_token, params=params)
    if not rows:
        return None
    return rows[0]


def _create_part_definition(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    code: str,
    name: str,
    description: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "owner_user_id": owner_user_id,
        "code": code,
        "name": name,
    }
    if description is not None:
        payload["description"] = description
    return supabase.insert_row(table="app.part_definitions", access_token=access_token, payload=payload)


def _create_part_revision_atomic(
    *,
    supabase: SupabaseClient,
    access_token: str,
    part_definition_id: str,
    source_geometry_revision_id: str,
    selected_nesting_derivative_id: str,
    selected_manufacturing_derivative_id: str | None,
    source_label: str | None,
    source_checksum_sha256: str | None,
    notes: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Insert a part_revision and update part_definition.current_revision_id atomically.

    Returns (part_definition, part_revision) as returned by the DB function.
    The PostgreSQL function holds a SELECT FOR UPDATE lock on the definition row,
    so revision_no is assigned safely without application-level retries.
    """
    rpc_result = supabase.execute_rpc(
        function_name="create_part_revision_atomic",
        access_token=access_token,
        payload={
            "p_part_definition_id": part_definition_id,
            "p_source_geometry_revision_id": source_geometry_revision_id,
            "p_selected_nesting_derivative_id": selected_nesting_derivative_id,
            "p_selected_manufacturing_derivative_id": selected_manufacturing_derivative_id,
            "p_source_label": source_label,
            "p_source_checksum_sha256": source_checksum_sha256,
            "p_notes": notes,
        },
    )
    if not isinstance(rpc_result, dict):
        raise PartCreationError(status_code=500, detail="create_part_revision_atomic returned unexpected payload")
    part_definition = rpc_result.get("part_definition")
    part_revision = rpc_result.get("part_revision")
    if not isinstance(part_definition, dict) or not isinstance(part_revision, dict):
        raise PartCreationError(status_code=500, detail="create_part_revision_atomic returned incomplete payload")
    return part_definition, part_revision


def create_part_from_geometry_revision(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
    raw_code: str,
    raw_name: str,
    geometry_revision_id: str,
    raw_description: str | None = None,
    raw_notes: str | None = None,
    raw_source_label: str | None = None,
) -> dict[str, Any]:
    code = _sanitize_required(raw_code, field="code")
    name = _sanitize_required(raw_name, field="name")
    geometry_id = _sanitize_required(geometry_revision_id, field="geometry_revision_id")
    description = _sanitize_optional(raw_description)
    notes = _sanitize_optional(raw_notes)
    source_label = _sanitize_optional(raw_source_label)

    _load_project_for_owner(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id,
        owner_user_id=owner_user_id,
    )

    geometry_revision = _load_geometry_revision(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id,
        geometry_revision_id=geometry_id,
    )

    derivative = _load_nesting_derivative(
        supabase=supabase,
        access_token=access_token,
        geometry_revision_id=geometry_id,
    )

    manufacturing_derivative = _load_manufacturing_derivative(
        supabase=supabase,
        access_token=access_token,
        geometry_revision_id=geometry_id,
    )

    part_definition = _load_existing_part_definition(
        supabase=supabase,
        access_token=access_token,
        owner_user_id=owner_user_id,
        code=code,
    )

    was_existing_definition = part_definition is not None
    if part_definition is None:
        part_definition = _create_part_definition(
            supabase=supabase,
            access_token=access_token,
            owner_user_id=owner_user_id,
            code=code,
            name=name,
            description=description,
        )

    part_definition_id = str(part_definition.get("id") or "").strip()
    if not part_definition_id:
        raise PartCreationError(status_code=500, detail="part_definition insert returned empty id")

    source_checksum_sha256 = str(geometry_revision.get("canonical_hash_sha256") or "").strip() or None
    derivative_id = str(derivative.get("id") or "").strip()
    if not derivative_id:
        raise PartCreationError(status_code=500, detail="derivative lookup returned empty id")

    manufacturing_derivative_id: str | None = None
    if manufacturing_derivative is not None:
        manufacturing_derivative_id = str(manufacturing_derivative.get("id") or "").strip() or None

    part_definition, part_revision = _create_part_revision_atomic(
        supabase=supabase,
        access_token=access_token,
        part_definition_id=part_definition_id,
        source_geometry_revision_id=geometry_id,
        selected_nesting_derivative_id=derivative_id,
        selected_manufacturing_derivative_id=manufacturing_derivative_id,
        source_label=source_label,
        source_checksum_sha256=source_checksum_sha256,
        notes=notes,
    )

    result: dict[str, Any] = {
        "part_definition": part_definition,
        "part_revision": part_revision,
        "source_geometry_revision": geometry_revision,
        "selected_nesting_derivative": derivative,
        "was_existing_definition": was_existing_definition,
    }
    if manufacturing_derivative is not None:
        result["selected_manufacturing_derivative"] = manufacturing_derivative
    return result
