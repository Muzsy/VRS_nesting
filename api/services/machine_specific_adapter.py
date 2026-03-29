"""Machine-specific adapter service (H2-E5-T4 + H2-E5-T5).

Generates per-sheet machine program artifacts from the persisted
``manufacturing_plan_json`` export artifact.

Supported targets (dispatched by snapshotted ``adapter_key`` + ``output_format``):

1. **Hypertherm Edge Connect** (H2-E5-T4)
   * adapter_key = ``hypertherm_edge_connect``
   * output_format = ``basic_plasma_eia_rs274d``
   * legacy_artifact_type = ``hypertherm_edge_connect_basic_plasma_eia``
   * file extension: ``.txt``

2. **LinuxCNC / QtPlasmaC** (H2-E5-T5)
   * adapter_key = ``linuxcnc_qtplasmac``
   * output_format = ``basic_manual_material_rs274ngc``
   * legacy_artifact_type = ``linuxcnc_qtplasmac_basic_manual_material``
   * file extension: ``.ngc``
   * Basic manual-material workflow only — no ``M190``/``M66`` auto material-change.

**Non-negotiable scope boundaries**

* Primer input: the persisted ``manufacturing_plan_json`` artifact.
* Never reads live ``project_manufacturing_selection``, raw solver output,
  worker run directories, or preview SVG artifacts.
* Canonical geometry lookup is allowed ONLY via ``plan_id`` + ``contour_index``
  -> ``run_manufacturing_contours.geometry_derivative_id``
  -> ``geometry_derivatives.derivative_jsonb`` (``manufacturing_canonical``).
* Writes ONLY to ``run_artifacts`` (``machine_program`` kind).
* Never writes to ``run_manufacturing_plans``, ``run_manufacturing_contours``,
  ``run_manufacturing_metrics``, ``geometry_contour_classes``,
  ``cut_contour_rules``, or ``postprocessor_profile_versions``.
* No ``machine_ready_bundle``, no zip, no generic fallback emitter,
  no worker auto-trigger, no frontend/export UI.
* Idempotent: delete-then-insert per run for the target legacy type.
* Deterministic: no volatile timestamps or non-deterministic fields in output.
* ``config_jsonb`` boundary: only ``program_format``, ``motion_output``,
  ``coordinate_mapping``, ``command_map``, ``lead_output``,
  ``artifact_packaging``, ``capabilities``, ``fallbacks``, ``export_guards``,
  and optionally ``process_mapping``.
* No general plugin-framework or dynamic adapter registry.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
from dataclasses import dataclass
from typing import Any, Callable

from api.supabase_client import SupabaseClient

UploadFn = Callable[..., None]
RegisterFn = Callable[..., None]

logger = logging.getLogger("vrs_api.machine_specific_adapter")

# ---------------------------------------------------------------------------
# Frozen target constants — Hypertherm Edge Connect (H2-E5-T4)
# ---------------------------------------------------------------------------

TARGET_ADAPTER_KEY = "hypertherm_edge_connect"
TARGET_OUTPUT_FORMAT = "basic_plasma_eia_rs274d"
TARGET_LEGACY_ARTIFACT_TYPE = "hypertherm_edge_connect_basic_plasma_eia"
_ARTIFACT_KIND = "machine_program"
_STORAGE_BUCKET = "run-artifacts"
_ADAPTER_VERSION = "h2_e5_t4_v1"

# ---------------------------------------------------------------------------
# Frozen target constants — LinuxCNC / QtPlasmaC (H2-E5-T5)
# ---------------------------------------------------------------------------

QTPLASMAC_ADAPTER_KEY = "linuxcnc_qtplasmac"
QTPLASMAC_OUTPUT_FORMAT = "basic_manual_material_rs274ngc"
QTPLASMAC_LEGACY_ARTIFACT_TYPE = "linuxcnc_qtplasmac_basic_manual_material"
_QTPLASMAC_ADAPTER_VERSION = "h2_e5_t5_v1"

# ---------------------------------------------------------------------------
# Supported target registry (dispatch lookup)
# ---------------------------------------------------------------------------

_SUPPORTED_TARGETS: dict[tuple[str, str], dict[str, str]] = {
    (TARGET_ADAPTER_KEY, TARGET_OUTPUT_FORMAT): {
        "legacy_artifact_type": TARGET_LEGACY_ARTIFACT_TYPE,
        "adapter_version": _ADAPTER_VERSION,
        "file_extension": ".txt",
        "storage_subfolder": TARGET_ADAPTER_KEY,
    },
    (QTPLASMAC_ADAPTER_KEY, QTPLASMAC_OUTPUT_FORMAT): {
        "legacy_artifact_type": QTPLASMAC_LEGACY_ARTIFACT_TYPE,
        "adapter_version": _QTPLASMAC_ADAPTER_VERSION,
        "file_extension": ".ngc",
        "storage_subfolder": QTPLASMAC_ADAPTER_KEY,
    },
}

# config_jsonb allowed top-level blocks
_ALLOWED_CONFIG_BLOCKS = frozenset({
    "program_format",
    "motion_output",
    "coordinate_mapping",
    "command_map",
    "lead_output",
    "artifact_packaging",
    "capabilities",
    "fallbacks",
    "export_guards",
    "process_mapping",
})

_REQUIRED_CONFIG_BLOCKS = frozenset({
    "program_format",
    "motion_output",
    "command_map",
    "artifact_packaging",
    "capabilities",
    "fallbacks",
    "export_guards",
})


@dataclass
class MachineSpecificAdapterError(Exception):
    status_code: int
    detail: str


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def generate_machine_programs_for_run(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    run_id: str,
    upload_object: UploadFn,
    register_artifact: RegisterFn,
) -> dict[str, Any]:
    """Generate per-sheet machine program artifacts for a run.

    Dispatches to the correct emitter based on the snapshotted
    ``adapter_key`` + ``output_format``.

    Returns a summary dict with the created artifact details.
    """
    run_id = _require(run_id, "run_id")
    owner_user_id = _require(owner_user_id, "owner_user_id")

    # 1) Verify run ownership and get project_id
    run = _load_run_for_owner(
        supabase=supabase,
        access_token=access_token,
        run_id=run_id,
        owner_user_id=owner_user_id,
    )
    project_id = _require(str(run.get("project_id") or ""), "project_id")

    # 2) Load the persisted manufacturing_plan_json artifact
    export_artifact = _load_export_artifact(
        supabase=supabase,
        access_token=access_token,
        run_id=run_id,
    )
    export_payload = _download_export_payload(
        supabase=supabase,
        access_token=access_token,
        export_artifact=export_artifact,
    )

    # 3) Load snapshot and validate postprocessor selection — dispatch target
    snapshot = _load_snapshot(
        supabase=supabase,
        access_token=access_token,
        run_id=run_id,
    )
    resolved = _resolve_and_validate_postprocessor_config(
        supabase=supabase,
        access_token=access_token,
        snapshot=snapshot,
    )
    config_jsonb = resolved["config_jsonb"]
    target_info = resolved["target_info"]
    adapter_key = resolved["adapter_key"]
    output_format = resolved["output_format"]

    # 4) Load geometry derivatives for contour point resolution
    geometry_cache = _build_geometry_cache(
        supabase=supabase,
        access_token=access_token,
        export_payload=export_payload,
    )

    # 5) Generate per-sheet machine programs
    sheets = export_payload.get("sheets")
    if not isinstance(sheets, list) or not sheets:
        raise MachineSpecificAdapterError(
            status_code=400,
            detail="manufacturing_plan_json has no sheets",
        )

    # Deterministic sheet ordering
    sorted_sheets = sorted(sheets, key=lambda s: int(s.get("sheet_index") or 0))

    file_ext = target_info["file_extension"]
    legacy_artifact_type = target_info["legacy_artifact_type"]
    adapter_version = target_info["adapter_version"]
    storage_subfolder = target_info["storage_subfolder"]

    programs: list[dict[str, Any]] = []
    for sheet_export in sorted_sheets:
        sheet_index = int(sheet_export.get("sheet_index") or 0)
        plan_id = str(sheet_export.get("plan_id") or "").strip()
        contours = sheet_export.get("contours")
        if not isinstance(contours, list):
            contours = []

        # Dispatch to the correct emitter
        if adapter_key == QTPLASMAC_ADAPTER_KEY:
            program_text = _emit_sheet_program_qtplasmac(
                config=config_jsonb,
                sheet_index=sheet_index,
                contours=contours,
                geometry_cache=geometry_cache,
                plan_id=plan_id,
            )
        else:
            program_text = _emit_sheet_program(
                config=config_jsonb,
                sheet_index=sheet_index,
                contours=contours,
                geometry_cache=geometry_cache,
                plan_id=plan_id,
            )

        program_bytes = program_text.encode("ascii", errors="replace")
        content_sha256 = hashlib.sha256(program_bytes).hexdigest()
        size_bytes = len(program_bytes)

        filename = f"{run_id}_sheet_{sheet_index}{file_ext}"
        storage_path = (
            f"projects/{project_id}/runs/{run_id}/"
            f"machine_program/{storage_subfolder}/{content_sha256}{file_ext}"
        )

        metadata: dict[str, Any] = {
            "legacy_artifact_type": legacy_artifact_type,
            "adapter_key": adapter_key,
            "output_format": output_format,
            "filename": filename,
            "sheet_index": sheet_index,
            "size_bytes": size_bytes,
            "content_sha256": content_sha256,
            "adapter_version": adapter_version,
        }

        programs.append({
            "sheet_index": sheet_index,
            "filename": filename,
            "storage_path": storage_path,
            "content_sha256": content_sha256,
            "size_bytes": size_bytes,
            "program_bytes": program_bytes,
            "metadata": metadata,
        })

    # 6) Idempotent: delete existing machine_program artifacts for this target
    _delete_existing_target_artifacts(
        supabase=supabase,
        access_token=access_token,
        run_id=run_id,
        legacy_artifact_type=legacy_artifact_type,
    )

    # 7) Upload and register each program
    for prog in programs:
        upload_object(
            bucket=_STORAGE_BUCKET,
            object_key=prog["storage_path"],
            payload=prog["program_bytes"],
        )
        register_artifact(
            run_id=run_id,
            artifact_kind=_ARTIFACT_KIND,
            storage_bucket=_STORAGE_BUCKET,
            storage_path=prog["storage_path"],
            metadata_json=prog["metadata"],
        )

    return {
        "run_id": run_id,
        "project_id": project_id,
        "adapter_key": adapter_key,
        "output_format": output_format,
        "programs_created": len(programs),
        "sheets": [
            {
                "sheet_index": p["sheet_index"],
                "filename": p["filename"],
                "storage_path": p["storage_path"],
                "content_sha256": p["content_sha256"],
                "size_bytes": p["size_bytes"],
            }
            for p in programs
        ],
    }


# ---------------------------------------------------------------------------
# Program emitter — Hypertherm Edge Connect (EIA/RS-274D basic plasma)
# ---------------------------------------------------------------------------


def _emit_sheet_program(
    *,
    config: dict[str, Any],
    sheet_index: int,
    contours: list[dict[str, Any]],
    geometry_cache: dict[str, dict[str, Any]],
    plan_id: str,
) -> str:
    """Emit a single-sheet EIA/RS-274D program from config + contours."""
    cmd = config.get("command_map", {})
    motion = config.get("motion_output", {})
    fmt = config.get("program_format", {})
    caps = config.get("capabilities", {})
    fallbacks = config.get("fallbacks", {})
    lead_cfg = config.get("lead_output", {})
    coord = config.get("coordinate_mapping", {})
    guards = config.get("export_guards", {})

    decimal_places = int(fmt.get("decimal_places", 3))
    line_ending = "\n" if fmt.get("line_ending", "lf") == "lf" else "\r\n"
    comment_style = fmt.get("comment_style", "parentheses")

    lines: list[str] = []

    # Comment header
    if caps.get("supports_comments", False):
        lines.append(_format_comment(
            f"SHEET {sheet_index} PLAN {plan_id}", style=comment_style,
        ))

    # Program start codes
    for code in (cmd.get("program_start") or []):
        lines.append(str(code))

    # Emit contours in deterministic order
    sorted_contours = sorted(
        contours,
        key=lambda c: (
            int(c.get("cut_order_index") if c.get("cut_order_index") is not None else 0),
            int(c.get("contour_index") if c.get("contour_index") is not None else 0),
        ),
    )

    process_on = cmd.get("process_on", "M07")
    process_off = cmd.get("process_off", "M08")
    rapid_code = cmd.get("rapid", "G00")
    linear_code = cmd.get("linear", "G01")
    arc_cw_code = cmd.get("arc_cw", "G02")
    arc_ccw_code = cmd.get("arc_ccw", "G03")
    supports_arcs = caps.get("supports_arcs", False)
    supports_ijk = caps.get("supports_ijk_arcs", False)
    unsupported_arc_policy = fallbacks.get("unsupported_arc", "error")
    unsupported_lead_policy = lead_cfg.get("unsupported_lead", "error")
    supported_lead_shapes = set(lead_cfg.get("supported_shapes") or [])
    distance_mode = motion.get("distance_mode", "incremental")

    for contour in sorted_contours:
        contour_index = contour.get("contour_index")
        derivative_id, points = _resolve_contour_points(
            contour=contour,
            plan_id=plan_id,
            geometry_cache=geometry_cache,
        )
        if not points:
            continue

        # Lead-in handling
        lead_in = contour.get("lead_in_jsonb") or {}
        lead_in_type = str(lead_in.get("type") or "none")
        if lead_in_type != "none" and lead_in_type not in supported_lead_shapes:
            if unsupported_lead_policy == "error":
                raise MachineSpecificAdapterError(
                    status_code=400,
                    detail=f"unsupported lead-in type '{lead_in_type}' for contour {contour_index}",
                )
            # fallback: skip lead-in silently

        # Rapid to entry point
        entry = points[0]
        lines.append(_motion_line(
            rapid_code, entry, decimal_places=decimal_places,
            distance_mode=distance_mode, prev_point=None,
        ))

        # Process on
        if process_on:
            lines.append(str(process_on))

        # Cut path
        prev = entry
        for pt in points[1:]:
            lines.append(_motion_line(
                linear_code, pt, decimal_places=decimal_places,
                distance_mode=distance_mode, prev_point=prev,
            ))
            prev = pt

        # Close contour back to start if needed
        if len(points) > 2:
            start = points[0]
            dist = math.hypot(prev[0] - start[0], prev[1] - start[1])
            if dist > 1e-6:
                lines.append(_motion_line(
                    linear_code, start, decimal_places=decimal_places,
                    distance_mode=distance_mode, prev_point=prev,
                ))

        # Lead-out handling
        lead_out = contour.get("lead_out_jsonb") or {}
        lead_out_type = str(lead_out.get("type") or "none")
        if lead_out_type != "none" and lead_out_type not in supported_lead_shapes:
            if unsupported_lead_policy == "error":
                raise MachineSpecificAdapterError(
                    status_code=400,
                    detail=f"unsupported lead-out type '{lead_out_type}' for contour {contour_index}",
                )

        # Process off
        if process_off:
            lines.append(str(process_off))

    # Export guards
    if guards.get("require_process_off_at_end", False):
        if not lines or lines[-1] != str(process_off):
            if process_off:
                lines.append(str(process_off))

    # Program end codes
    for code in (cmd.get("program_end") or []):
        lines.append(str(code))

    if guards.get("require_program_end", False):
        program_end_codes = cmd.get("program_end") or []
        if program_end_codes and (not lines or lines[-1] != str(program_end_codes[-1])):
            for code in program_end_codes:
                lines.append(str(code))

    # Guard: forbid empty output
    if guards.get("forbid_empty_output", False) and not lines:
        raise MachineSpecificAdapterError(
            status_code=400,
            detail=f"empty output for sheet {sheet_index}",
        )

    return line_ending.join(lines) + line_ending


# ---------------------------------------------------------------------------
# Program emitter — LinuxCNC / QtPlasmaC (RS-274NGC, basic manual-material)
# ---------------------------------------------------------------------------


def _emit_sheet_program_qtplasmac(
    *,
    config: dict[str, Any],
    sheet_index: int,
    contours: list[dict[str, Any]],
    geometry_cache: dict[str, dict[str, Any]],
    plan_id: str,
) -> str:
    """Emit a single-sheet RS-274NGC program for QtPlasmaC.

    Basic manual-material workflow only.  No M190/M66 auto material-change.
    No multi-tool, scribe, spot, or router workflows.
    """
    cmd = config.get("command_map", {})
    motion = config.get("motion_output", {})
    fmt = config.get("program_format", {})
    caps = config.get("capabilities", {})
    fallbacks = config.get("fallbacks", {})
    lead_cfg = config.get("lead_output", {})
    guards = config.get("export_guards", {})

    decimal_places = int(fmt.get("decimal_places", 4))
    line_ending = "\n" if fmt.get("line_ending", "lf") == "lf" else "\r\n"
    comment_style = fmt.get("comment_style", "semicolon")

    lines: list[str] = []

    # Comment header
    if caps.get("supports_comments", True):
        lines.append(_format_comment(
            f"SHEET {sheet_index} PLAN {plan_id}", style=comment_style,
        ))
        lines.append(_format_comment(
            "QtPlasmaC basic manual-material", style=comment_style,
        ))

    # Program start codes
    for code in (cmd.get("program_start") or []):
        lines.append(str(code))

    # Emit contours in deterministic order
    sorted_contours = sorted(
        contours,
        key=lambda c: (
            int(c.get("cut_order_index") if c.get("cut_order_index") is not None else 0),
            int(c.get("contour_index") if c.get("contour_index") is not None else 0),
        ),
    )

    process_on = cmd.get("process_on", "M03 $0 S1")
    process_off = cmd.get("process_off", "M05 $0")
    rapid_code = cmd.get("rapid", "G00")
    linear_code = cmd.get("linear", "G01")
    arc_cw_code = cmd.get("arc_cw", "G02")
    arc_ccw_code = cmd.get("arc_ccw", "G03")
    supports_arcs = caps.get("supports_arcs", False)
    unsupported_lead_policy = lead_cfg.get("unsupported_lead", "error")
    supported_lead_shapes = set(lead_cfg.get("supported_shapes") or [])
    distance_mode = motion.get("distance_mode", "absolute")

    for contour in sorted_contours:
        contour_index = contour.get("contour_index")
        derivative_id, points = _resolve_contour_points(
            contour=contour,
            plan_id=plan_id,
            geometry_cache=geometry_cache,
        )
        if not points:
            continue

        # Lead-in handling
        lead_in = contour.get("lead_in_jsonb") or {}
        lead_in_type = str(lead_in.get("type") or "none")
        if lead_in_type != "none" and lead_in_type not in supported_lead_shapes:
            if unsupported_lead_policy == "error":
                raise MachineSpecificAdapterError(
                    status_code=400,
                    detail=f"unsupported lead-in type '{lead_in_type}' for contour {contour_index}",
                )

        # Rapid to entry point
        entry = points[0]
        lines.append(_motion_line(
            rapid_code, entry, decimal_places=decimal_places,
            distance_mode=distance_mode, prev_point=None,
        ))

        # Process on (torch on)
        if process_on:
            lines.append(str(process_on))

        # Cut path
        prev = entry
        for pt in points[1:]:
            lines.append(_motion_line(
                linear_code, pt, decimal_places=decimal_places,
                distance_mode=distance_mode, prev_point=prev,
            ))
            prev = pt

        # Close contour back to start if needed
        if len(points) > 2:
            start = points[0]
            dist = math.hypot(prev[0] - start[0], prev[1] - start[1])
            if dist > 1e-6:
                lines.append(_motion_line(
                    linear_code, start, decimal_places=decimal_places,
                    distance_mode=distance_mode, prev_point=prev,
                ))

        # Lead-out handling
        lead_out = contour.get("lead_out_jsonb") or {}
        lead_out_type = str(lead_out.get("type") or "none")
        if lead_out_type != "none" and lead_out_type not in supported_lead_shapes:
            if unsupported_lead_policy == "error":
                raise MachineSpecificAdapterError(
                    status_code=400,
                    detail=f"unsupported lead-out type '{lead_out_type}' for contour {contour_index}",
                )

        # Process off (torch off)
        if process_off:
            lines.append(str(process_off))

    # Export guards
    if guards.get("require_process_off_at_end", False):
        if not lines or lines[-1] != str(process_off):
            if process_off:
                lines.append(str(process_off))

    # Program end codes
    for code in (cmd.get("program_end") or []):
        lines.append(str(code))

    if guards.get("require_program_end", False):
        program_end_codes = cmd.get("program_end") or []
        if program_end_codes and (not lines or lines[-1] != str(program_end_codes[-1])):
            for code in program_end_codes:
                lines.append(str(code))

    # Guard: forbid empty output
    if guards.get("forbid_empty_output", False) and not lines:
        raise MachineSpecificAdapterError(
            status_code=400,
            detail=f"empty output for sheet {sheet_index}",
        )

    return line_ending.join(lines) + line_ending


def _format_comment(text: str, *, style: str) -> str:
    if style == "parentheses":
        return f"({text})"
    if style == "semicolon":
        return f"; {text}"
    return f"({text})"


def _motion_line(
    code: str,
    point: tuple[float, float],
    *,
    decimal_places: int,
    distance_mode: str,
    prev_point: tuple[float, float] | None,
) -> str:
    if distance_mode == "incremental" and prev_point is not None:
        x = point[0] - prev_point[0]
        y = point[1] - prev_point[1]
    else:
        x = point[0]
        y = point[1]
    return f"{code} X{x:.{decimal_places}f} Y{y:.{decimal_places}f}"


# ---------------------------------------------------------------------------
# Geometry resolution (contour points from persisted truth)
# ---------------------------------------------------------------------------


def _resolve_contour_points(
    *,
    contour: dict[str, Any],
    plan_id: str,
    geometry_cache: dict[str, dict[str, Any]],
) -> tuple[str | None, list[tuple[float, float]]]:
    """Resolve contour geometry points from manufacturing_canonical derivative.

    Returns (derivative_id, list_of_xy_points).
    """
    contour_index = contour.get("contour_index")
    if contour_index is None:
        return None, []

    # The geometry_cache maps "plan_id:contour_index" -> derivative data
    cache_key = f"{plan_id}:{contour_index}"
    cached = geometry_cache.get(cache_key)
    if cached is None:
        return None, []

    derivative_id = cached.get("derivative_id")
    derivative_jsonb = cached.get("derivative_jsonb")
    if not isinstance(derivative_jsonb, dict):
        return derivative_id, []

    # manufacturing_canonical format: contours[].points
    mfg_contours = derivative_jsonb.get("contours")
    if not isinstance(mfg_contours, list):
        return derivative_id, []

    target_index = int(contour_index)
    for mc in mfg_contours:
        if not isinstance(mc, dict):
            continue
        if int(mc.get("contour_index", -1)) == target_index:
            raw_points = mc.get("points")
            if isinstance(raw_points, list):
                points: list[tuple[float, float]] = []
                for pt in raw_points:
                    if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                        points.append((float(pt[0]), float(pt[1])))
                return derivative_id, points

    return derivative_id, []


def _build_geometry_cache(
    *,
    supabase: SupabaseClient,
    access_token: str,
    export_payload: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Build cache: "plan_id:contour_index" -> {derivative_id, derivative_jsonb}.

    Resolution path:
    manufacturing_plan_json.sheets[].plan_id + contour_index
    -> run_manufacturing_contours (geometry_derivative_id)
    -> geometry_derivatives (derivative_jsonb)
    """
    cache: dict[str, dict[str, Any]] = {}
    derivative_cache: dict[str, dict[str, Any]] = {}

    sheets = export_payload.get("sheets")
    if not isinstance(sheets, list):
        return cache

    for sheet in sheets:
        if not isinstance(sheet, dict):
            continue
        plan_id = str(sheet.get("plan_id") or "").strip()
        if not plan_id:
            continue

        contours = sheet.get("contours")
        if not isinstance(contours, list):
            continue

        # Load manufacturing contour records for this plan
        mfg_contours = _load_manufacturing_contours_for_plan(
            supabase=supabase,
            access_token=access_token,
            plan_id=plan_id,
        )

        for mc in mfg_contours:
            contour_index = mc.get("contour_index")
            if contour_index is None:
                continue
            derivative_id = str(mc.get("geometry_derivative_id") or "").strip()
            if not derivative_id:
                continue

            # Load derivative if not cached
            if derivative_id not in derivative_cache:
                deriv = _load_geometry_derivative(
                    supabase=supabase,
                    access_token=access_token,
                    derivative_id=derivative_id,
                )
                derivative_cache[derivative_id] = deriv

            cache_key = f"{plan_id}:{contour_index}"
            cache[cache_key] = {
                "derivative_id": derivative_id,
                "derivative_jsonb": derivative_cache[derivative_id].get("derivative_jsonb"),
            }

    return cache


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------


def _require(value: str | None, field: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise MachineSpecificAdapterError(status_code=400, detail=f"missing {field}")
    return cleaned


def _load_run_for_owner(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
    owner_user_id: str,
) -> dict[str, Any]:
    rows = supabase.select_rows(
        table="app.nesting_runs",
        access_token=access_token,
        params={
            "select": "id,owner_user_id,project_id,status",
            "id": f"eq.{run_id}",
            "owner_user_id": f"eq.{owner_user_id}",
            "limit": "1",
        },
    )
    if not rows:
        raise MachineSpecificAdapterError(
            status_code=404, detail="run not found or not owned by user",
        )
    return rows[0]


def _load_export_artifact(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
) -> dict[str, Any]:
    """Load the manufacturing_plan_json artifact record for the run."""
    rows = supabase.select_rows(
        table="app.run_artifacts",
        access_token=access_token,
        params={
            "select": "id,run_id,artifact_kind,storage_bucket,storage_path,metadata_jsonb",
            "run_id": f"eq.{run_id}",
            "artifact_kind": "eq.manufacturing_plan_json",
            "limit": "1",
        },
    )
    if not rows:
        raise MachineSpecificAdapterError(
            status_code=400,
            detail="manufacturing_plan_json artifact not found for run",
        )
    return rows[0]


def _download_export_payload(
    *,
    supabase: SupabaseClient,
    access_token: str,
    export_artifact: dict[str, Any],
) -> dict[str, Any]:
    """Download and parse the manufacturing_plan_json artifact content."""
    bucket = str(export_artifact.get("storage_bucket") or "").strip()
    storage_path = str(export_artifact.get("storage_path") or "").strip()
    if not bucket or not storage_path:
        raise MachineSpecificAdapterError(
            status_code=400,
            detail="manufacturing_plan_json artifact has no storage path",
        )

    signed = supabase.create_signed_download_url(
        access_token=access_token,
        bucket=bucket,
        object_key=storage_path,
    )
    download_url = str(signed.get("download_url") or "").strip()
    if not download_url:
        raise MachineSpecificAdapterError(
            status_code=500,
            detail="failed to create signed download url for export artifact",
        )

    raw_bytes = supabase.download_signed_object(signed_url=download_url)
    try:
        payload = json.loads(raw_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise MachineSpecificAdapterError(
            status_code=400,
            detail="manufacturing_plan_json artifact is not valid JSON",
        ) from exc

    if not isinstance(payload, dict):
        raise MachineSpecificAdapterError(
            status_code=400,
            detail="manufacturing_plan_json artifact payload is not an object",
        )
    return payload


def _load_snapshot(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
) -> dict[str, Any]:
    rows = supabase.select_rows(
        table="app.nesting_run_snapshots",
        access_token=access_token,
        params={
            "select": "id,run_id,manufacturing_manifest_jsonb,includes_manufacturing,includes_postprocess",
            "run_id": f"eq.{run_id}",
            "limit": "1",
        },
    )
    if not rows:
        raise MachineSpecificAdapterError(
            status_code=404, detail="snapshot not found for run",
        )
    return rows[0]


def _resolve_and_validate_postprocessor_config(
    *,
    supabase: SupabaseClient,
    access_token: str,
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Resolve postprocessor config from snapshot and dispatch to target.

    Returns a dict with keys: ``config_jsonb``, ``target_info``,
    ``adapter_key``, ``output_format``.
    """
    mfg_manifest = snapshot.get("manufacturing_manifest_jsonb")
    if not isinstance(mfg_manifest, dict):
        raise MachineSpecificAdapterError(
            status_code=400,
            detail="snapshot missing manufacturing_manifest_jsonb",
        )

    if not mfg_manifest.get("postprocess_selection_present"):
        raise MachineSpecificAdapterError(
            status_code=400,
            detail="snapshot has no postprocessor selection",
        )

    pp_version = mfg_manifest.get("postprocessor_profile_version")
    if not isinstance(pp_version, dict):
        raise MachineSpecificAdapterError(
            status_code=400,
            detail="snapshot missing postprocessor_profile_version",
        )

    # Resolve adapter_key and output_format from snapshot
    snapshot_adapter_key = str(pp_version.get("adapter_key") or "").strip()
    snapshot_output_format = str(pp_version.get("output_format") or "").strip()

    if not snapshot_adapter_key:
        raise MachineSpecificAdapterError(
            status_code=400,
            detail="snapshot postprocessor selection missing adapter_key",
        )
    if not snapshot_output_format:
        raise MachineSpecificAdapterError(
            status_code=400,
            detail="snapshot postprocessor selection missing output_format",
        )

    # Dispatch: look up in supported targets
    target_key = (snapshot_adapter_key, snapshot_output_format)
    target_info = _SUPPORTED_TARGETS.get(target_key)
    if target_info is None:
        supported = ", ".join(
            f"{k[0]}/{k[1]}" for k in sorted(_SUPPORTED_TARGETS.keys())
        )
        raise MachineSpecificAdapterError(
            status_code=400,
            detail=f"unsupported adapter_key/output_format: "
                   f"'{snapshot_adapter_key}/{snapshot_output_format}'. "
                   f"Supported: {supported}",
        )

    # Load the actual config_jsonb from the postprocessor profile version
    pp_version_id = str(
        pp_version.get("active_postprocessor_profile_version_id") or "",
    ).strip()
    if not pp_version_id:
        raise MachineSpecificAdapterError(
            status_code=400,
            detail="snapshot postprocessor selection missing version id",
        )

    config_jsonb = _load_postprocessor_config(
        supabase=supabase,
        access_token=access_token,
        version_id=pp_version_id,
    )

    # Validate required config blocks
    _validate_config_boundary(config_jsonb)

    return {
        "config_jsonb": config_jsonb,
        "target_info": target_info,
        "adapter_key": snapshot_adapter_key,
        "output_format": snapshot_output_format,
    }


def _load_postprocessor_config(
    *,
    supabase: SupabaseClient,
    access_token: str,
    version_id: str,
) -> dict[str, Any]:
    """Load config_jsonb from postprocessor_profile_versions (read-only)."""
    rows = supabase.select_rows(
        table="app.postprocessor_profile_versions",
        access_token=access_token,
        params={
            "select": "id,config_jsonb",
            "id": f"eq.{version_id}",
            "limit": "1",
        },
    )
    if not rows:
        raise MachineSpecificAdapterError(
            status_code=400,
            detail="postprocessor profile version not found",
        )
    config = rows[0].get("config_jsonb")
    if not isinstance(config, dict):
        raise MachineSpecificAdapterError(
            status_code=400,
            detail="postprocessor profile version has no config_jsonb",
        )
    return config


def _validate_config_boundary(config: dict[str, Any]) -> None:
    """Enforce the narrowed config_jsonb boundary for this adapter."""
    for block_name in _REQUIRED_CONFIG_BLOCKS:
        if block_name not in config:
            raise MachineSpecificAdapterError(
                status_code=400,
                detail=f"required config block missing: {block_name}",
            )


def _load_manufacturing_contours_for_plan(
    *,
    supabase: SupabaseClient,
    access_token: str,
    plan_id: str,
) -> list[dict[str, Any]]:
    return supabase.select_rows(
        table="app.run_manufacturing_contours",
        access_token=access_token,
        params={
            "select": "id,manufacturing_plan_id,contour_index,geometry_derivative_id",
            "manufacturing_plan_id": f"eq.{plan_id}",
            "order": "contour_index.asc",
        },
    )


def _load_geometry_derivative(
    *,
    supabase: SupabaseClient,
    access_token: str,
    derivative_id: str,
) -> dict[str, Any]:
    rows = supabase.select_rows(
        table="app.geometry_derivatives",
        access_token=access_token,
        params={
            "select": "id,derivative_kind,derivative_jsonb",
            "id": f"eq.{derivative_id}",
            "limit": "1",
        },
    )
    if not rows:
        raise MachineSpecificAdapterError(
            status_code=400,
            detail=f"geometry derivative not found: {derivative_id}",
        )
    return rows[0]


def _delete_existing_target_artifacts(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
    legacy_artifact_type: str,
) -> None:
    """Idempotent: delete existing machine_program artifacts for a specific target legacy type."""
    existing = supabase.select_rows(
        table="app.run_artifacts",
        access_token=access_token,
        params={
            "select": "id,metadata_jsonb",
            "run_id": f"eq.{run_id}",
            "artifact_kind": f"eq.{_ARTIFACT_KIND}",
        },
    )
    for row in existing:
        meta = row.get("metadata_jsonb")
        if isinstance(meta, dict) and meta.get("legacy_artifact_type") == legacy_artifact_type:
            artifact_id = str(row.get("id") or "").strip()
            if artifact_id:
                supabase.delete_rows(
                    table="app.run_artifacts",
                    access_token=access_token,
                    filters={"id": f"eq.{artifact_id}"},
                )
