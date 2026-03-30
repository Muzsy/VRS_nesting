from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any

from api.supabase_client import SupabaseClient
from vrs_nesting.config.nesting_quality_profiles import (
    DEFAULT_QUALITY_PROFILE,
    compact_runtime_policy,
    normalize_quality_profile_name,
    runtime_policy_for_quality_profile,
)


SNAPSHOT_VERSION = "h2_e5_t2_snapshot_v1"


@dataclass
class RunSnapshotBuilderError(Exception):
    status_code: int
    detail: str


def _sanitize_required(value: str, *, field: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise RunSnapshotBuilderError(status_code=400, detail=f"invalid {field}")
    return cleaned


def _sanitize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _parse_positive_int(raw: Any, *, field: str) -> int:
    if isinstance(raw, bool):
        raise RunSnapshotBuilderError(status_code=400, detail=f"invalid {field}")
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise RunSnapshotBuilderError(status_code=400, detail=f"invalid {field}") from exc
    if value <= 0:
        raise RunSnapshotBuilderError(status_code=400, detail=f"invalid {field}")
    return value


def _parse_priority(raw: Any, *, field: str) -> int:
    if isinstance(raw, bool):
        raise RunSnapshotBuilderError(status_code=400, detail=f"invalid {field}")
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise RunSnapshotBuilderError(status_code=400, detail=f"invalid {field}") from exc
    if value < 0 or value > 100:
        raise RunSnapshotBuilderError(status_code=400, detail=f"invalid {field}")
    return value


def _parse_positive_float(raw: Any, *, field: str) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise RunSnapshotBuilderError(status_code=400, detail=f"invalid {field}") from exc
    if not math.isfinite(value) or value <= 0.0:
        raise RunSnapshotBuilderError(status_code=400, detail=f"invalid {field}")
    return value


def _parse_nonnegative_float(raw: Any, *, field: str) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise RunSnapshotBuilderError(status_code=400, detail=f"invalid {field}") from exc
    if not math.isfinite(value) or value < 0.0:
        raise RunSnapshotBuilderError(status_code=400, detail=f"invalid {field}")
    return value


def _parse_finite_float(raw: Any, *, field: str) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise RunSnapshotBuilderError(status_code=400, detail=f"invalid {field}") from exc
    if not math.isfinite(value):
        raise RunSnapshotBuilderError(status_code=400, detail=f"invalid {field}")
    return value


def _parse_point_like(raw: Any, *, field: str) -> list[float]:
    if isinstance(raw, list) and len(raw) == 2:
        x_raw, y_raw = raw
    elif isinstance(raw, dict):
        x_raw = raw.get("x")
        y_raw = raw.get("y")
    else:
        raise RunSnapshotBuilderError(status_code=400, detail=f"invalid {field}")
    try:
        x = float(x_raw)
        y = float(y_raw)
    except (TypeError, ValueError) as exc:
        raise RunSnapshotBuilderError(status_code=400, detail=f"invalid {field}") from exc
    if not math.isfinite(x) or not math.isfinite(y):
        raise RunSnapshotBuilderError(status_code=400, detail=f"invalid {field}")
    return [x, y]


def _parse_ring_payload(raw: Any, *, field: str) -> list[list[float]]:
    if not isinstance(raw, list) or len(raw) < 3:
        raise RunSnapshotBuilderError(status_code=400, detail=f"invalid {field}")
    return [_parse_point_like(point_raw, field=f"{field}[{idx}]") for idx, point_raw in enumerate(raw)]


def _parse_hole_rings_payload(raw: Any, *, field: str) -> list[list[list[float]]]:
    if not isinstance(raw, list):
        raise RunSnapshotBuilderError(status_code=400, detail=f"invalid {field}")
    return [_parse_ring_payload(ring_raw, field=f"{field}[{idx}]") for idx, ring_raw in enumerate(raw)]


def _parse_bbox_payload(raw: Any, *, field: str) -> dict[str, float]:
    if not isinstance(raw, dict):
        raise RunSnapshotBuilderError(status_code=400, detail=f"invalid {field}")
    return {
        "min_x": _parse_finite_float(raw.get("min_x"), field=f"{field}.min_x"),
        "min_y": _parse_finite_float(raw.get("min_y"), field=f"{field}.min_y"),
        "max_x": _parse_finite_float(raw.get("max_x"), field=f"{field}.max_x"),
        "max_y": _parse_finite_float(raw.get("max_y"), field=f"{field}.max_y"),
        "width": _parse_positive_float(raw.get("width"), field=f"{field}.width"),
        "height": _parse_positive_float(raw.get("height"), field=f"{field}.height"),
    }


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


def _load_project_for_owner(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
    owner_user_id: str,
) -> dict[str, Any]:
    params = {
        "select": "id,owner_user_id,name,lifecycle",
        "id": f"eq.{project_id}",
        "owner_user_id": f"eq.{owner_user_id}",
        "lifecycle": "neq.archived",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.projects", access_token=access_token, params=params)
    if not rows:
        raise RunSnapshotBuilderError(status_code=404, detail="project not found")
    return rows[0]


def _load_project_settings(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
) -> dict[str, Any]:
    params = {
        "select": "project_id,default_units,default_rotation_step_deg,notes",
        "project_id": f"eq.{project_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.project_settings", access_token=access_token, params=params)
    if not rows:
        return {
            "project_id": project_id,
            "default_units": "mm",
            "default_rotation_step_deg": 90,
            "notes": None,
        }
    return rows[0]


def _select_technology_setup(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
) -> dict[str, Any]:
    params = {
        "select": "id,project_id,preset_id,display_name,lifecycle,is_default,machine_code,material_code,thickness_mm,kerf_mm,spacing_mm,margin_mm,rotation_step_deg,allow_free_rotation,notes",
        "project_id": f"eq.{project_id}",
        "lifecycle": "eq.approved",
        "order": "is_default.desc,created_at.asc,id.asc",
    }
    rows = supabase.select_rows(table="app.project_technology_setups", access_token=access_token, params=params)
    if not rows:
        raise RunSnapshotBuilderError(status_code=400, detail="missing approved project technology setup")

    default_rows = [row for row in rows if _normalize_bool(row.get("is_default"))]
    if len(default_rows) == 1:
        return default_rows[0]
    if len(default_rows) > 1:
        raise RunSnapshotBuilderError(status_code=400, detail="ambiguous default technology setup")

    if len(rows) == 1:
        return rows[0]
    raise RunSnapshotBuilderError(status_code=400, detail="missing selectable project technology setup")


def _load_part_definition_for_owner(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    part_definition_id: str,
) -> dict[str, Any]:
    params = {
        "select": "id,owner_user_id,code,name,current_revision_id",
        "id": f"eq.{part_definition_id}",
        "owner_user_id": f"eq.{owner_user_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.part_definitions", access_token=access_token, params=params)
    if not rows:
        raise RunSnapshotBuilderError(status_code=403, detail="part definition does not belong to owner")
    return rows[0]


def _load_sheet_definition_for_owner(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    sheet_definition_id: str,
) -> dict[str, Any]:
    params = {
        "select": "id,owner_user_id,code,name,current_revision_id",
        "id": f"eq.{sheet_definition_id}",
        "owner_user_id": f"eq.{owner_user_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.sheet_definitions", access_token=access_token, params=params)
    if not rows:
        raise RunSnapshotBuilderError(status_code=403, detail="sheet definition does not belong to owner")
    return rows[0]


def _load_part_revision(*, supabase: SupabaseClient, access_token: str, part_revision_id: str) -> dict[str, Any]:
    params = {
        "select": "id,part_definition_id,revision_no,lifecycle,source_geometry_revision_id,selected_nesting_derivative_id",
        "id": f"eq.{part_revision_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.part_revisions", access_token=access_token, params=params)
    if not rows:
        raise RunSnapshotBuilderError(status_code=404, detail="part revision not found")
    return rows[0]


def _load_sheet_revision(*, supabase: SupabaseClient, access_token: str, sheet_revision_id: str) -> dict[str, Any]:
    params = {
        "select": "id,sheet_definition_id,revision_no,lifecycle,width_mm,height_mm,grain_direction",
        "id": f"eq.{sheet_revision_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.sheet_revisions", access_token=access_token, params=params)
    if not rows:
        raise RunSnapshotBuilderError(status_code=404, detail="sheet revision not found")
    return rows[0]


def _load_geometry_derivative(*, supabase: SupabaseClient, access_token: str, derivative_id: str) -> dict[str, Any]:
    params = {
        "select": "id,geometry_revision_id,derivative_kind,derivative_jsonb,derivative_hash_sha256,source_geometry_hash_sha256",
        "id": f"eq.{derivative_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.geometry_derivatives", access_token=access_token, params=params)
    if not rows:
        raise RunSnapshotBuilderError(status_code=400, detail="part revision selected derivative not found")
    return rows[0]


def _extract_nesting_geometry_payload(derivative: dict[str, Any], *, part_revision_id: str) -> tuple[list[list[float]], list[list[list[float]]], dict[str, float]]:
    derivative_json = derivative.get("derivative_jsonb")
    if not isinstance(derivative_json, dict):
        raise RunSnapshotBuilderError(
            status_code=400,
            detail=f"nesting derivative payload missing for part revision: {part_revision_id}",
        )
    polygon = derivative_json.get("polygon")
    if not isinstance(polygon, dict):
        raise RunSnapshotBuilderError(
            status_code=400,
            detail=f"nesting derivative polygon missing for part revision: {part_revision_id}",
        )

    outer_ring = _parse_ring_payload(
        polygon.get("outer_ring"),
        field=f"derivative_jsonb.polygon.outer_ring[{part_revision_id}]",
    )
    hole_rings = _parse_hole_rings_payload(
        polygon.get("hole_rings", []),
        field=f"derivative_jsonb.polygon.hole_rings[{part_revision_id}]",
    )
    bbox = _parse_bbox_payload(
        derivative_json.get("bbox"),
        field=f"derivative_jsonb.bbox[{part_revision_id}]",
    )
    return outer_ring, hole_rings, bbox


def _build_parts_and_geometry_manifest(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    params = {
        "select": "id,project_id,part_revision_id,required_qty,placement_priority,placement_policy,is_active,notes",
        "project_id": f"eq.{project_id}",
        "is_active": "eq.true",
        "required_qty": "gt.0",
    }
    rows = supabase.select_rows(table="app.project_part_requirements", access_token=access_token, params=params)
    if not rows:
        raise RunSnapshotBuilderError(status_code=400, detail="missing active project part requirements")

    parts_manifest: list[dict[str, Any]] = []
    geometry_by_derivative: dict[str, dict[str, Any]] = {}

    for row in rows:
        requirement_id = _sanitize_required(str(row.get("id") or ""), field="project_part_requirement_id")
        part_revision_id = _sanitize_required(str(row.get("part_revision_id") or ""), field="part_revision_id")
        required_qty = _parse_positive_int(row.get("required_qty"), field="required_qty")
        placement_priority = _parse_priority(row.get("placement_priority"), field="placement_priority")
        placement_policy = _sanitize_required(str(row.get("placement_policy") or ""), field="placement_policy").lower()

        part_revision = _load_part_revision(supabase=supabase, access_token=access_token, part_revision_id=part_revision_id)
        lifecycle = str(part_revision.get("lifecycle") or "").strip().lower()
        if lifecycle != "approved":
            raise RunSnapshotBuilderError(status_code=400, detail=f"part revision is not approved: {part_revision_id}")

        part_definition_id = _sanitize_required(
            str(part_revision.get("part_definition_id") or ""), field="part_definition_id"
        )
        part_definition = _load_part_definition_for_owner(
            supabase=supabase,
            access_token=access_token,
            owner_user_id=owner_user_id,
            part_definition_id=part_definition_id,
        )

        derivative_id = _sanitize_required(
            str(part_revision.get("selected_nesting_derivative_id") or ""), field="selected_nesting_derivative_id"
        )
        source_geometry_revision_id = _sanitize_required(
            str(part_revision.get("source_geometry_revision_id") or ""), field="source_geometry_revision_id"
        )
        derivative = _load_geometry_derivative(supabase=supabase, access_token=access_token, derivative_id=derivative_id)
        derivative_kind = str(derivative.get("derivative_kind") or "").strip().lower()
        if derivative_kind != "nesting_canonical":
            raise RunSnapshotBuilderError(status_code=400, detail=f"unsupported derivative kind for part revision: {part_revision_id}")

        derivative_geometry_id = _sanitize_required(
            str(derivative.get("geometry_revision_id") or ""), field="derivative.geometry_revision_id"
        )
        if derivative_geometry_id != source_geometry_revision_id:
            raise RunSnapshotBuilderError(status_code=400, detail=f"derivative geometry mismatch for part revision: {part_revision_id}")
        outer_ring, hole_rings, bbox = _extract_nesting_geometry_payload(derivative, part_revision_id=part_revision_id)

        revision_no = _parse_positive_int(part_revision.get("revision_no"), field="revision_no")
        part_code = _sanitize_required(str(part_definition.get("code") or ""), field="part_code")
        part_name = _sanitize_required(str(part_definition.get("name") or ""), field="part_name")

        parts_manifest.append(
            {
                "project_part_requirement_id": requirement_id,
                "part_revision_id": part_revision_id,
                "part_definition_id": part_definition_id,
                "part_code": part_code,
                "part_name": part_name,
                "revision_no": revision_no,
                "required_qty": required_qty,
                "placement_priority": placement_priority,
                "placement_policy": placement_policy,
                "selected_nesting_derivative_id": derivative_id,
                "source_geometry_revision_id": source_geometry_revision_id,
            }
        )

        geometry_by_derivative[derivative_id] = {
            "selected_nesting_derivative_id": derivative_id,
            "source_geometry_revision_id": derivative_geometry_id,
            "derivative_kind": derivative_kind,
            "derivative_hash_sha256": _sanitize_optional(str(derivative.get("derivative_hash_sha256") or "")),
            "source_geometry_hash_sha256": _sanitize_optional(str(derivative.get("source_geometry_hash_sha256") or "")),
            "polygon": {
                "outer_ring": outer_ring,
                "hole_rings": hole_rings,
            },
            "bbox": bbox,
        }

    parts_manifest.sort(
        key=lambda item: (
            int(item["placement_priority"]),
            str(item["part_code"]),
            int(item["revision_no"]),
            str(item["project_part_requirement_id"]),
        )
    )
    geometry_manifest = list(geometry_by_derivative.values())
    geometry_manifest.sort(key=lambda item: str(item["selected_nesting_derivative_id"]))
    return parts_manifest, geometry_manifest


def _build_sheets_manifest(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
) -> list[dict[str, Any]]:
    params = {
        "select": "id,project_id,sheet_revision_id,required_qty,is_active,is_default,placement_priority,notes",
        "project_id": f"eq.{project_id}",
        "is_active": "eq.true",
        "required_qty": "gt.0",
    }
    rows = supabase.select_rows(table="app.project_sheet_inputs", access_token=access_token, params=params)
    if not rows:
        raise RunSnapshotBuilderError(status_code=400, detail="missing active project sheet inputs")

    sheets_manifest: list[dict[str, Any]] = []
    for row in rows:
        project_sheet_input_id = _sanitize_required(str(row.get("id") or ""), field="project_sheet_input_id")
        sheet_revision_id = _sanitize_required(str(row.get("sheet_revision_id") or ""), field="sheet_revision_id")
        required_qty = _parse_positive_int(row.get("required_qty"), field="required_qty")
        placement_priority = _parse_priority(row.get("placement_priority"), field="placement_priority")
        is_default = _normalize_bool(row.get("is_default"))

        sheet_revision = _load_sheet_revision(supabase=supabase, access_token=access_token, sheet_revision_id=sheet_revision_id)
        lifecycle = str(sheet_revision.get("lifecycle") or "").strip().lower()
        if lifecycle != "approved":
            raise RunSnapshotBuilderError(status_code=400, detail=f"sheet revision is not approved: {sheet_revision_id}")

        sheet_definition_id = _sanitize_required(
            str(sheet_revision.get("sheet_definition_id") or ""), field="sheet_definition_id"
        )
        sheet_definition = _load_sheet_definition_for_owner(
            supabase=supabase,
            access_token=access_token,
            owner_user_id=owner_user_id,
            sheet_definition_id=sheet_definition_id,
        )

        revision_no = _parse_positive_int(sheet_revision.get("revision_no"), field="revision_no")
        width_mm = _parse_positive_float(sheet_revision.get("width_mm"), field="width_mm")
        height_mm = _parse_positive_float(sheet_revision.get("height_mm"), field="height_mm")
        grain_direction = _sanitize_optional(str(sheet_revision.get("grain_direction") or ""))

        sheet_code = _sanitize_required(str(sheet_definition.get("code") or ""), field="sheet_code")
        sheet_name = _sanitize_required(str(sheet_definition.get("name") or ""), field="sheet_name")

        sheets_manifest.append(
            {
                "project_sheet_input_id": project_sheet_input_id,
                "sheet_revision_id": sheet_revision_id,
                "sheet_definition_id": sheet_definition_id,
                "sheet_code": sheet_code,
                "sheet_name": sheet_name,
                "revision_no": revision_no,
                "required_qty": required_qty,
                "is_default": is_default,
                "placement_priority": placement_priority,
                "width_mm": width_mm,
                "height_mm": height_mm,
                "grain_direction": grain_direction,
            }
        )

    sheets_manifest.sort(
        key=lambda item: (
            0 if bool(item["is_default"]) else 1,
            int(item["placement_priority"]),
            str(item["sheet_code"]),
            int(item["revision_no"]),
            str(item["project_sheet_input_id"]),
        )
    )
    return sheets_manifest


def _load_project_manufacturing_selection(
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


def _load_manufacturing_profile_version_for_snapshot(
    *,
    supabase: SupabaseClient,
    access_token: str,
    manufacturing_profile_version_id: str,
) -> dict[str, Any]:
    params = {
        "select": "id,manufacturing_profile_id,version_no,lifecycle,is_active,machine_code,material_code,thickness_mm,kerf_mm,config_jsonb,active_postprocessor_profile_version_id",
        "id": f"eq.{manufacturing_profile_version_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.manufacturing_profile_versions", access_token=access_token, params=params)
    if not rows:
        raise RunSnapshotBuilderError(status_code=400, detail="manufacturing profile version not found for snapshot")
    return rows[0]


def _load_postprocessor_profile_version_for_snapshot(
    *,
    supabase: SupabaseClient,
    access_token: str,
    postprocessor_profile_version_id: str,
) -> dict[str, Any] | None:
    params = {
        "select": "id,postprocessor_profile_id,owner_user_id,version_no,lifecycle,is_active,adapter_key,output_format,schema_version,config_jsonb",
        "id": f"eq.{postprocessor_profile_version_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.postprocessor_profile_versions", access_token=access_token, params=params)
    if not rows:
        return None
    return rows[0]


def _build_manufacturing_manifest(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
) -> tuple[dict[str, Any], bool]:
    selection = _load_project_manufacturing_selection(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id,
    )

    if selection is None:
        manifest = {
            "mode": "h2_e5_t2_snapshot_selection",
            "project_id": project_id,
            "selection_present": False,
            "postprocess_selection_present": False,
        }
        return manifest, False

    active_version_id = _sanitize_required(
        str(selection.get("active_manufacturing_profile_version_id") or ""),
        field="active_manufacturing_profile_version_id",
    )
    selected_at = str(selection.get("selected_at") or "")
    selected_by = str(selection.get("selected_by") or "")

    version = _load_manufacturing_profile_version_for_snapshot(
        supabase=supabase,
        access_token=access_token,
        manufacturing_profile_version_id=active_version_id,
    )

    version_no_raw = version.get("version_no")
    version_no = int(version_no_raw) if version_no_raw is not None else None
    lifecycle = str(version.get("lifecycle") or "").strip().lower() or None
    is_active = _normalize_bool(version.get("is_active"))
    machine_code = _sanitize_optional(str(version.get("machine_code") or ""))
    material_code = _sanitize_optional(str(version.get("material_code") or ""))

    thickness_raw = version.get("thickness_mm")
    thickness_mm: float | None = None
    if thickness_raw is not None:
        thickness_mm = float(thickness_raw)

    kerf_raw = version.get("kerf_mm")
    kerf_mm: float | None = None
    if kerf_raw is not None:
        kerf_mm = float(kerf_raw)

    config_jsonb = version.get("config_jsonb")
    if not isinstance(config_jsonb, dict):
        config_jsonb = {}

    manufacturing_profile_id = _sanitize_optional(
        str(version.get("manufacturing_profile_id") or "")
    )

    # --- postprocessor selection resolution ---
    postprocess_selection_present = False
    postprocessor_snapshot: dict[str, Any] | None = None
    active_pp_version_id = _sanitize_optional(str(version.get("active_postprocessor_profile_version_id") or ""))

    if active_pp_version_id:
        pp_version = _load_postprocessor_profile_version_for_snapshot(
            supabase=supabase,
            access_token=access_token,
            postprocessor_profile_version_id=active_pp_version_id,
        )
        if pp_version is not None:
            pp_is_active = _normalize_bool(pp_version.get("is_active"))
            if pp_is_active:
                postprocess_selection_present = True
                postprocessor_snapshot = {
                    "active_postprocessor_profile_version_id": active_pp_version_id,
                    "postprocessor_profile_id": _sanitize_optional(str(pp_version.get("postprocessor_profile_id") or "")),
                    "version_no": int(pp_version["version_no"]) if pp_version.get("version_no") is not None else None,
                    "lifecycle": str(pp_version.get("lifecycle") or "").strip().lower() or None,
                    "is_active": pp_is_active,
                    "adapter_key": _sanitize_optional(str(pp_version.get("adapter_key") or "")),
                    "output_format": _sanitize_optional(str(pp_version.get("output_format") or "")),
                    "schema_version": _sanitize_optional(str(pp_version.get("schema_version") or "")),
                }

    manifest: dict[str, Any] = {
        "mode": "h2_e5_t2_snapshot_selection",
        "project_id": project_id,
        "selection_present": True,
        "selected_at": selected_at,
        "selected_by": selected_by,
        "active_manufacturing_profile_version_id": active_version_id,
        "manufacturing_profile_version": {
            "manufacturing_profile_id": manufacturing_profile_id,
            "version_no": version_no,
            "lifecycle": lifecycle,
            "is_active": is_active,
            "machine_code": machine_code,
            "material_code": material_code,
            "thickness_mm": thickness_mm,
            "kerf_mm": kerf_mm,
            "config_jsonb": config_jsonb,
        },
        "postprocess_selection_present": postprocess_selection_present,
    }
    if postprocessor_snapshot is not None:
        manifest["postprocessor_profile_version"] = postprocessor_snapshot
    return manifest, True


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _snapshot_hash(snapshot_payload: dict[str, Any]) -> str:
    canonical = _canonical_json(snapshot_payload)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_run_snapshot_payload(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
    quality_profile: str | None = None,
    time_limit_s: int | None = None,
    sa_eval_budget_sec: int | None = None,
) -> dict[str, Any]:
    project_id_clean = _sanitize_required(project_id, field="project_id")

    project = _load_project_for_owner(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
        owner_user_id=owner_user_id,
    )
    project_settings = _load_project_settings(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
    )
    technology_setup = _select_technology_setup(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
    )

    parts_manifest, geometry_manifest = _build_parts_and_geometry_manifest(
        supabase=supabase,
        access_token=access_token,
        owner_user_id=owner_user_id,
        project_id=project_id_clean,
    )
    sheets_manifest = _build_sheets_manifest(
        supabase=supabase,
        access_token=access_token,
        owner_user_id=owner_user_id,
        project_id=project_id_clean,
    )

    default_units = _sanitize_required(str(project_settings.get("default_units") or "mm"), field="default_units")
    default_rotation_step_deg = _parse_positive_int(
        project_settings.get("default_rotation_step_deg", 90), field="default_rotation_step_deg"
    )

    technology_rotation_step = _parse_positive_int(technology_setup.get("rotation_step_deg"), field="rotation_step_deg")
    technology_kerf_mm = _parse_nonnegative_float(technology_setup.get("kerf_mm"), field="kerf_mm")
    technology_spacing_mm = _parse_nonnegative_float(technology_setup.get("spacing_mm"), field="spacing_mm")
    technology_margin_mm = _parse_nonnegative_float(technology_setup.get("margin_mm"), field="margin_mm")
    resolved_quality_profile = normalize_quality_profile_name(
        quality_profile,
        default=DEFAULT_QUALITY_PROFILE,
    )
    nesting_runtime_policy = compact_runtime_policy(
        runtime_policy_for_quality_profile(resolved_quality_profile)
    )
    if "compaction" not in nesting_runtime_policy:
        # Keep snapshot runtime policy explicit for compaction mode even on legacy profiles.
        nesting_runtime_policy["compaction"] = "off"
    if sa_eval_budget_sec is not None and sa_eval_budget_sec > 0:
        nesting_runtime_policy["sa_eval_budget_sec"] = sa_eval_budget_sec

    project_manifest_jsonb = {
        "project_id": _sanitize_required(str(project.get("id") or ""), field="project.id"),
        "project_name": _sanitize_required(str(project.get("name") or ""), field="project.name"),
        "project_lifecycle": _sanitize_required(str(project.get("lifecycle") or ""), field="project.lifecycle").lower(),
        "default_units": default_units,
        "default_rotation_step_deg": default_rotation_step_deg,
        "project_settings_notes": _sanitize_optional(str(project_settings.get("notes") or "")),
    }

    technology_manifest_jsonb = {
        "technology_setup_id": _sanitize_required(str(technology_setup.get("id") or ""), field="technology_setup_id"),
        "machine_code": _sanitize_required(str(technology_setup.get("machine_code") or ""), field="machine_code"),
        "material_code": _sanitize_required(str(technology_setup.get("material_code") or ""), field="material_code"),
        "thickness_mm": _parse_positive_float(technology_setup.get("thickness_mm"), field="thickness_mm"),
        "kerf_mm": technology_kerf_mm,
        "spacing_mm": technology_spacing_mm,
        "margin_mm": technology_margin_mm,
        "rotation_step_deg": technology_rotation_step,
        "allow_free_rotation": _normalize_bool(technology_setup.get("allow_free_rotation")),
        "display_name": _sanitize_optional(str(technology_setup.get("display_name") or "")),
        "preset_id": _sanitize_optional(str(technology_setup.get("preset_id") or "")),
    }

    effective_time_limit_s = time_limit_s if (time_limit_s is not None and time_limit_s > 0) else 60

    solver_config_jsonb = {
        "units": default_units,
        "seed": 0,
        "time_limit_s": effective_time_limit_s,
        "rotation_step_deg": technology_rotation_step,
        "allow_free_rotation": bool(technology_manifest_jsonb["allow_free_rotation"]),
        "kerf_mm": technology_kerf_mm,
        "spacing_mm": technology_spacing_mm,
        "margin_mm": technology_margin_mm,
        "quality_profile": resolved_quality_profile,
        "engine_backend_hint": "nesting_engine_v2",
        "nesting_engine_runtime_policy": nesting_runtime_policy,
        "snapshot_mode": "h1_minimum_builder",
        **({"sa_eval_budget_sec": sa_eval_budget_sec} if sa_eval_budget_sec is not None and sa_eval_budget_sec > 0 else {}),
    }

    manufacturing_manifest_jsonb, includes_manufacturing = _build_manufacturing_manifest(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
    )
    includes_postprocess = bool(manufacturing_manifest_jsonb.get("postprocess_selection_present"))

    hash_payload = {
        "snapshot_version": SNAPSHOT_VERSION,
        "project_manifest_jsonb": project_manifest_jsonb,
        "technology_manifest_jsonb": technology_manifest_jsonb,
        "parts_manifest_jsonb": parts_manifest,
        "sheets_manifest_jsonb": sheets_manifest,
        "geometry_manifest_jsonb": geometry_manifest,
        "solver_config_jsonb": solver_config_jsonb,
        "manufacturing_manifest_jsonb": manufacturing_manifest_jsonb,
    }
    snapshot_hash_sha256 = _snapshot_hash(hash_payload)

    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "project_manifest_jsonb": project_manifest_jsonb,
        "technology_manifest_jsonb": technology_manifest_jsonb,
        "parts_manifest_jsonb": parts_manifest,
        "sheets_manifest_jsonb": sheets_manifest,
        "geometry_manifest_jsonb": geometry_manifest,
        "solver_config_jsonb": solver_config_jsonb,
        "manufacturing_manifest_jsonb": manufacturing_manifest_jsonb,
        "includes_manufacturing": includes_manufacturing,
        "includes_postprocess": includes_postprocess,
        "snapshot_hash_sha256": snapshot_hash_sha256,
    }
