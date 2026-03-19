from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from api.supabase_client import SupabaseClient


@dataclass
class SheetCreationError(Exception):
    status_code: int
    detail: str


def _sanitize_required(value: str, *, field: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise SheetCreationError(status_code=400, detail=f"invalid {field}")
    return cleaned


def _sanitize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_grain_direction(raw: str | None) -> str | None:
    cleaned = _sanitize_optional(raw)
    if cleaned is None:
        return None
    return cleaned.lower()


def _parse_positive_mm(raw: float, *, field: str) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise SheetCreationError(status_code=400, detail=f"invalid {field}") from exc
    if not math.isfinite(value) or value <= 0.0:
        raise SheetCreationError(status_code=400, detail=f"invalid {field}")
    return value


def _load_existing_sheet_definition(
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
    rows = supabase.select_rows(table="app.sheet_definitions", access_token=access_token, params=params)
    if not rows:
        return None
    return rows[0]


def _create_sheet_definition(
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
    return supabase.insert_row(table="app.sheet_definitions", access_token=access_token, payload=payload)


def _create_sheet_revision_atomic(
    *,
    supabase: SupabaseClient,
    access_token: str,
    sheet_definition_id: str,
    width_mm: float,
    height_mm: float,
    grain_direction: str | None,
    source_label: str | None,
    notes: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Insert a sheet_revision and update sheet_definition.current_revision_id atomically.

    Returns (sheet_definition, sheet_revision) as returned by the DB function.
    The PostgreSQL function holds a SELECT FOR UPDATE lock on the definition row,
    so revision_no is assigned safely without application-level retries.
    """
    rpc_result = supabase.execute_rpc(
        function_name="create_sheet_revision_atomic",
        access_token=access_token,
        payload={
            "p_sheet_definition_id": sheet_definition_id,
            "p_width_mm": width_mm,
            "p_height_mm": height_mm,
            "p_grain_direction": grain_direction,
            "p_source_label": source_label,
            "p_notes": notes,
        },
    )
    if not isinstance(rpc_result, dict):
        raise SheetCreationError(status_code=500, detail="create_sheet_revision_atomic returned unexpected payload")
    sheet_definition = rpc_result.get("sheet_definition")
    sheet_revision = rpc_result.get("sheet_revision")
    if not isinstance(sheet_definition, dict) or not isinstance(sheet_revision, dict):
        raise SheetCreationError(status_code=500, detail="create_sheet_revision_atomic returned incomplete payload")
    return sheet_definition, sheet_revision


def create_sheet_revision(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    raw_code: str,
    raw_name: str,
    raw_width_mm: float,
    raw_height_mm: float,
    raw_description: str | None = None,
    raw_grain_direction: str | None = None,
    raw_notes: str | None = None,
    raw_source_label: str | None = None,
) -> dict[str, Any]:
    code = _sanitize_required(raw_code, field="code")
    name = _sanitize_required(raw_name, field="name")
    width_mm = _parse_positive_mm(raw_width_mm, field="width_mm")
    height_mm = _parse_positive_mm(raw_height_mm, field="height_mm")
    description = _sanitize_optional(raw_description)
    grain_direction = _normalize_grain_direction(raw_grain_direction)
    notes = _sanitize_optional(raw_notes)
    source_label = _sanitize_optional(raw_source_label)

    sheet_definition = _load_existing_sheet_definition(
        supabase=supabase,
        access_token=access_token,
        owner_user_id=owner_user_id,
        code=code,
    )

    was_existing_definition = sheet_definition is not None
    if sheet_definition is None:
        sheet_definition = _create_sheet_definition(
            supabase=supabase,
            access_token=access_token,
            owner_user_id=owner_user_id,
            code=code,
            name=name,
            description=description,
        )

    sheet_definition_id = str(sheet_definition.get("id") or "").strip()
    if not sheet_definition_id:
        raise SheetCreationError(status_code=500, detail="sheet_definition insert returned empty id")

    sheet_definition, sheet_revision = _create_sheet_revision_atomic(
        supabase=supabase,
        access_token=access_token,
        sheet_definition_id=sheet_definition_id,
        width_mm=width_mm,
        height_mm=height_mm,
        grain_direction=grain_direction,
        source_label=source_label,
        notes=notes,
    )

    return {
        "sheet_definition": sheet_definition,
        "sheet_revision": sheet_revision,
        "was_existing_definition": was_existing_definition,
    }
