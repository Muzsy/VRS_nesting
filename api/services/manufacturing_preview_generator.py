"""H2-E5-T1 — Manufacturing preview SVG generator service.

Generates per-sheet manufacturing preview SVG artifacts from:
* persisted run_manufacturing_plans + run_manufacturing_contours (H2-E4-T2)
* run_layout_sheets for sheet dimensions
* geometry_derivatives (manufacturing_canonical) for contour geometry points
* run_manufacturing_contours.entry_point_jsonb for entry markers
* run_manufacturing_contours.lead_in_jsonb / lead_out_jsonb for lead descriptors
* run_manufacturing_contours.cut_order_index for cut-order labelling

**Non-negotiable scope boundaries**
* Reads ONLY persisted manufacturing plan truth + manufacturing_canonical
  derivative contour geometry + sheet dimensions.
* Never reads raw solver output, live project_manufacturing_selection,
  postprocessor config, or H1 sheet_svg artifacts as source.
* Writes ONLY to run_artifacts (manufacturing_preview_svg kind).
* Never writes to run_manufacturing_plans, run_manufacturing_contours,
  run_manufacturing_metrics, geometry_contour_classes, or any earlier
  truth table.
* No postprocessor adapter, machine-neutral export, worker auto-hook,
  or frontend redesign.
* Idempotent: delete-then-insert per run (no duplicate preview artifacts).
"""

from __future__ import annotations

import hashlib
import logging
import math
from dataclasses import dataclass
from typing import Any, Callable
from xml.sax.saxutils import escape

from api.supabase_client import SupabaseClient

UploadFn = Callable[..., None]
RegisterFn = Callable[..., None]

logger = logging.getLogger("vrs_api.manufacturing_preview_generator")


@dataclass
class ManufacturingPreviewGeneratorError(Exception):
    status_code: int
    detail: str


# ---------------------------------------------------------------------------
# SVG style constants
# ---------------------------------------------------------------------------

_SHEET_BG_FILL = "#f8fafc"
_SHEET_BORDER_STROKE = "#0f172a"
_OUTER_STROKE = "#1d4ed8"  # blue-700
_INNER_STROKE = "#dc2626"  # red-600
_OUTER_FILL = "rgba(59,130,246,0.12)"   # blue-500 @ 12%
_INNER_FILL = "rgba(239,68,68,0.08)"    # red-500 @ 8%
_ENTRY_MARKER_FILL = "#16a34a"  # green-600
_ENTRY_MARKER_RADIUS = 2.0
_LEAD_IN_STROKE = "#f59e0b"   # amber-500
_LEAD_OUT_STROKE = "#8b5cf6"  # violet-500
_LEAD_STROKE_WIDTH = 0.8
_CUT_ORDER_FONT_SIZE = 3.5
_CUT_ORDER_FILL = "#475569"   # slate-600

_STORAGE_BUCKET = "run-artifacts"
_ARTIFACT_KIND = "manufacturing_preview_svg"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def generate_manufacturing_preview(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    run_id: str,
    upload_object: UploadFn,
    register_artifact: RegisterFn,
) -> dict[str, Any]:
    """Generate per-sheet manufacturing preview SVG artifacts for a run.

    Returns a summary dict with created artifact count and details.
    """
    run_id = _require(run_id, "run_id")
    owner_user_id = _require(owner_user_id, "owner_user_id")

    # 1) Verify run ownership
    run = _load_run_for_owner(
        supabase=supabase,
        access_token=access_token,
        run_id=run_id,
        owner_user_id=owner_user_id,
    )
    project_id = str(run.get("project_id") or "").strip()
    if not project_id:
        raise ManufacturingPreviewGeneratorError(
            status_code=400, detail="run missing project_id",
        )

    # 2) Load persisted manufacturing plans
    plans = _load_manufacturing_plans(
        supabase=supabase,
        access_token=access_token,
        run_id=run_id,
    )
    if not plans:
        raise ManufacturingPreviewGeneratorError(
            status_code=400,
            detail="run has no persisted manufacturing plans",
        )

    # 3) Load manufacturing contours for all plans
    plan_ids = [str(p.get("id") or "").strip() for p in plans if p.get("id")]
    contours = _load_manufacturing_contours(
        supabase=supabase,
        access_token=access_token,
        plan_ids=plan_ids,
    )

    # 4) Load sheet dimensions
    sheets = _load_sheets(
        supabase=supabase,
        access_token=access_token,
        run_id=run_id,
    )
    if not sheets:
        raise ManufacturingPreviewGeneratorError(
            status_code=400,
            detail="run has no projection sheets",
        )

    # 5) Resolve manufacturing_canonical derivative geometry per contour
    derivative_cache: dict[str, dict[str, Any]] = {}

    # 6) Build per-sheet render data
    plan_by_sheet: dict[str, dict[str, Any]] = {}
    for plan in plans:
        sheet_id = str(plan.get("sheet_id") or "").strip()
        if sheet_id:
            plan_by_sheet[sheet_id] = plan

    contours_by_plan: dict[str, list[dict[str, Any]]] = {}
    for c in contours:
        plan_id = str(c.get("manufacturing_plan_id") or "").strip()
        contours_by_plan.setdefault(plan_id, []).append(c)

    # 7) Idempotent: delete existing manufacturing_preview_svg artifacts for this run
    _delete_existing_preview_artifacts(
        supabase=supabase,
        access_token=access_token,
        run_id=run_id,
    )

    # 8) Generate and persist per-sheet SVG
    artifacts_created: list[dict[str, Any]] = []

    for sheet in sheets:
        sheet_id = str(sheet.get("id") or "").strip()
        sheet_index = int(sheet.get("sheet_index") or 0)
        width_mm = _safe_float(sheet.get("width_mm"), 1000.0)
        height_mm = _safe_float(sheet.get("height_mm"), 1000.0)

        plan = plan_by_sheet.get(sheet_id)
        if not plan:
            logger.info("skip_sheet_no_plan sheet_id=%s sheet_index=%d", sheet_id, sheet_index)
            continue

        plan_id = str(plan.get("id") or "").strip()
        sheet_contours = contours_by_plan.get(plan_id, [])

        # Resolve geometry for each contour
        render_contours = _resolve_render_contours(
            supabase=supabase,
            access_token=access_token,
            contours=sheet_contours,
            derivative_cache=derivative_cache,
        )

        # Render SVG
        svg_content = _render_manufacturing_preview_svg(
            width_mm=width_mm,
            height_mm=height_mm,
            sheet_index=sheet_index,
            render_contours=render_contours,
        )

        svg_bytes = svg_content.encode("utf-8")
        content_sha256 = hashlib.sha256(svg_bytes).hexdigest()
        size_bytes = len(svg_bytes)

        filename = f"out/manufacturing_preview_sheet_{sheet_index + 1:03d}.svg"
        storage_hash = hashlib.sha256(
            f"{filename}\n{content_sha256}".encode("utf-8"),
        ).hexdigest()
        storage_path = (
            f"projects/{project_id}/runs/{run_id}/"
            f"manufacturing_preview_svg/{storage_hash}.svg"
        )

        metadata = {
            "legacy_artifact_type": _ARTIFACT_KIND,
            "filename": filename,
            "sheet_index": sheet_index,
            "size_bytes": size_bytes,
            "content_sha256": content_sha256,
            "preview_scope": "h2_e5_t1",
        }

        # Upload to storage
        upload_object(
            bucket=_STORAGE_BUCKET,
            object_key=storage_path,
            payload=svg_bytes,
        )

        # Register artifact
        register_artifact(
            run_id=run_id,
            artifact_kind=_ARTIFACT_KIND,
            storage_bucket=_STORAGE_BUCKET,
            storage_path=storage_path,
            metadata_json=metadata,
        )

        artifacts_created.append({
            "sheet_index": sheet_index,
            "filename": filename,
            "storage_path": storage_path,
            "content_sha256": content_sha256,
            "size_bytes": size_bytes,
        })

    return {
        "run_id": run_id,
        "project_id": project_id,
        "artifacts_created": len(artifacts_created),
        "artifacts": artifacts_created,
    }


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------


def _require(value: str | None, field: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise ManufacturingPreviewGeneratorError(
            status_code=400, detail=f"missing {field}",
        )
    return cleaned


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        f = float(value)
        return f if math.isfinite(f) else default
    except (TypeError, ValueError):
        return default


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
        raise ManufacturingPreviewGeneratorError(
            status_code=404, detail="run not found or not owned by user",
        )
    return rows[0]


def _load_manufacturing_plans(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
) -> list[dict[str, Any]]:
    return supabase.select_rows(
        table="app.run_manufacturing_plans",
        access_token=access_token,
        params={
            "select": "id,run_id,sheet_id,status,summary_jsonb",
            "run_id": f"eq.{run_id}",
            "order": "sheet_id.asc",
        },
    )


def _load_manufacturing_contours(
    *,
    supabase: SupabaseClient,
    access_token: str,
    plan_ids: list[str],
) -> list[dict[str, Any]]:
    all_contours: list[dict[str, Any]] = []
    for plan_id in plan_ids:
        rows = supabase.select_rows(
            table="app.run_manufacturing_contours",
            access_token=access_token,
            params={
                "select": "id,manufacturing_plan_id,placement_id,"
                          "geometry_derivative_id,contour_index,contour_kind,"
                          "feature_class,entry_point_jsonb,lead_in_jsonb,"
                          "lead_out_jsonb,cut_order_index",
                "manufacturing_plan_id": f"eq.{plan_id}",
                "order": "cut_order_index.asc",
            },
        )
        all_contours.extend(rows)
    return all_contours


def _load_sheets(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
) -> list[dict[str, Any]]:
    return supabase.select_rows(
        table="app.run_layout_sheets",
        access_token=access_token,
        params={
            "select": "id,run_id,sheet_index,width_mm,height_mm",
            "run_id": f"eq.{run_id}",
            "order": "sheet_index.asc",
        },
    )


def _load_derivative(
    *,
    supabase: SupabaseClient,
    access_token: str,
    geometry_derivative_id: str,
) -> dict[str, Any]:
    rows = supabase.select_rows(
        table="app.geometry_derivatives",
        access_token=access_token,
        params={
            "select": "id,derivative_kind,derivative_jsonb",
            "id": f"eq.{geometry_derivative_id}",
            "limit": "1",
        },
    )
    if not rows:
        raise ManufacturingPreviewGeneratorError(
            status_code=400,
            detail=f"manufacturing_canonical derivative not found: {geometry_derivative_id}",
        )
    row = rows[0]
    kind = str(row.get("derivative_kind") or "").strip()
    if kind != "manufacturing_canonical":
        raise ManufacturingPreviewGeneratorError(
            status_code=400,
            detail=f"derivative {geometry_derivative_id} is {kind}, expected manufacturing_canonical",
        )
    return row


def _delete_existing_preview_artifacts(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
) -> None:
    """Idempotent: delete existing manufacturing_preview_svg artifacts."""
    supabase.delete_rows(
        table="app.run_artifacts",
        access_token=access_token,
        filters={
            "run_id": f"eq.{run_id}",
            "artifact_kind": f"eq.{_ARTIFACT_KIND}",
        },
    )


# ---------------------------------------------------------------------------
# Render data resolution
# ---------------------------------------------------------------------------


@dataclass
class _RenderContour:
    contour_index: int
    contour_kind: str
    feature_class: str
    cut_order_index: int
    points: list[list[float]]
    entry_x: float
    entry_y: float
    lead_in_type: str
    lead_out_type: str
    placement_tx: float = 0.0
    placement_ty: float = 0.0
    placement_rotation_deg: float = 0.0


def _resolve_render_contours(
    *,
    supabase: SupabaseClient,
    access_token: str,
    contours: list[dict[str, Any]],
    derivative_cache: dict[str, dict[str, Any]],
) -> list[_RenderContour]:
    """Resolve contour geometry from manufacturing_canonical derivatives."""
    render_contours: list[_RenderContour] = []

    for contour in contours:
        geometry_derivative_id = str(
            contour.get("geometry_derivative_id") or "",
        ).strip()
        if not geometry_derivative_id:
            logger.warning(
                "skip_contour_no_derivative contour_id=%s",
                contour.get("id"),
            )
            continue

        # Load and cache derivative
        if geometry_derivative_id not in derivative_cache:
            derivative_cache[geometry_derivative_id] = _load_derivative(
                supabase=supabase,
                access_token=access_token,
                geometry_derivative_id=geometry_derivative_id,
            )

        derivative_row = derivative_cache[geometry_derivative_id]
        derivative_jsonb = derivative_row.get("derivative_jsonb") or {}

        contour_index = int(contour.get("contour_index") or 0)

        # Find matching contour in derivative geometry
        deriv_contours = derivative_jsonb.get("contours") or []
        matched_geom = None
        for dc in deriv_contours:
            if isinstance(dc, dict) and int(dc.get("contour_index") if dc.get("contour_index") is not None else -1) == contour_index:
                matched_geom = dc
                break

        if matched_geom is None:
            raise ManufacturingPreviewGeneratorError(
                status_code=400,
                detail=(
                    f"contour_index {contour_index} not found in "
                    f"manufacturing_canonical derivative {geometry_derivative_id}"
                ),
            )

        points = matched_geom.get("points") or []

        # Entry point
        entry_point = contour.get("entry_point_jsonb") or {}
        entry_x = _safe_float(entry_point.get("x"), 0.0)
        entry_y = _safe_float(entry_point.get("y"), 0.0)

        # Lead descriptors
        lead_in = contour.get("lead_in_jsonb") or {}
        lead_out = contour.get("lead_out_jsonb") or {}

        contour_kind = str(contour.get("contour_kind") or "outer")
        feature_class = str(contour.get("feature_class") or "default")
        cut_order_index = int(contour.get("cut_order_index") or 0)

        render_contours.append(_RenderContour(
            contour_index=contour_index,
            contour_kind=contour_kind,
            feature_class=feature_class,
            cut_order_index=cut_order_index,
            points=points,
            entry_x=entry_x,
            entry_y=entry_y,
            lead_in_type=str(lead_in.get("type") or "none"),
            lead_out_type=str(lead_out.get("type") or "none"),
        ))

    render_contours.sort(key=lambda c: c.cut_order_index)
    return render_contours


# ---------------------------------------------------------------------------
# SVG rendering
# ---------------------------------------------------------------------------


def _fmt(value: float) -> str:
    return f"{float(value):.6f}"


def _escape_xml_attr(value: str) -> str:
    return escape(value, {'"': "&quot;", "'": "&apos;"})


def _path_d_from_points(points: list[list[float]]) -> str:
    """Build an SVG path d attribute from a list of [x,y] points (closed)."""
    if not points or len(points) < 2:
        return ""
    parts = [f"M {_fmt(points[0][0])} {_fmt(points[0][1])}"]
    for pt in points[1:]:
        parts.append(f"L {_fmt(pt[0])} {_fmt(pt[1])}")
    parts.append("Z")
    return " ".join(parts)


def _render_manufacturing_preview_svg(
    *,
    width_mm: float,
    height_mm: float,
    sheet_index: int,
    render_contours: list[_RenderContour],
) -> str:
    """Render a manufacturing preview SVG for a single sheet."""
    lines: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg"'
        f' width="{_fmt(width_mm)}mm" height="{_fmt(height_mm)}mm"'
        f' viewBox="0 0 {_fmt(width_mm)} {_fmt(height_mm)}"'
        f' data-preview-scope="h2_e5_t1"'
        f' data-sheet-index="{sheet_index}">',
        # Sheet background
        f'  <rect x="0" y="0" width="100%" height="100%"'
        f' fill="{_SHEET_BG_FILL}" />',
        # Sheet boundary
        f'  <rect x="0" y="0" width="{_fmt(width_mm)}"'
        f' height="{_fmt(height_mm)}" fill="none"'
        f' stroke="{_SHEET_BORDER_STROKE}" stroke-width="0.6" />',
    ]

    for rc in render_contours:
        is_outer = rc.contour_kind == "outer"
        stroke = _OUTER_STROKE if is_outer else _INNER_STROKE
        fill = _OUTER_FILL if is_outer else _INNER_FILL
        stroke_width = "0.5" if is_outer else "0.35"

        path_d = _path_d_from_points(rc.points)
        if path_d:
            contour_kind_attr = _escape_xml_attr(rc.contour_kind)
            lines.append(
                f'  <path d="{path_d}" fill="{fill}" stroke="{stroke}"'
                f' stroke-width="{stroke_width}" fill-rule="evenodd"'
                f' data-contour-kind="{contour_kind_attr}"'
                f' data-contour-index="{rc.contour_index}"'
                f' data-cut-order="{rc.cut_order_index}" />'
            )

        # Entry marker
        lines.append(
            f'  <circle cx="{_fmt(rc.entry_x)}" cy="{_fmt(rc.entry_y)}"'
            f' r="{_ENTRY_MARKER_RADIUS}" fill="{_ENTRY_MARKER_FILL}"'
            f' stroke="none" opacity="0.85"'
            f' data-role="entry-marker"'
            f' data-cut-order="{rc.cut_order_index}" />'
        )

        # Lead-in indicator (short line from entry point)
        if rc.lead_in_type != "none" and rc.points:
            first_pt = rc.points[0]
            lines.append(
                f'  <line x1="{_fmt(rc.entry_x)}" y1="{_fmt(rc.entry_y)}"'
                f' x2="{_fmt(first_pt[0])}" y2="{_fmt(first_pt[1])}"'
                f' stroke="{_LEAD_IN_STROKE}"'
                f' stroke-width="{_LEAD_STROKE_WIDTH}"'
                f' stroke-dasharray="1.5,0.8"'
                f' data-role="lead-in"'
                f' data-lead-type="{_escape_xml_attr(rc.lead_in_type)}" />'
            )

        # Lead-out indicator (short line from last contour point)
        if rc.lead_out_type != "none" and rc.points:
            last_pt = rc.points[-1]
            lines.append(
                f'  <line x1="{_fmt(last_pt[0])}" y1="{_fmt(last_pt[1])}"'
                f' x2="{_fmt(rc.entry_x)}" y2="{_fmt(rc.entry_y)}"'
                f' stroke="{_LEAD_OUT_STROKE}"'
                f' stroke-width="{_LEAD_STROKE_WIDTH}"'
                f' stroke-dasharray="1.5,0.8"'
                f' data-role="lead-out"'
                f' data-lead-type="{_escape_xml_attr(rc.lead_out_type)}" />'
            )

        # Cut-order label
        lines.append(
            f'  <text x="{_fmt(rc.entry_x + _ENTRY_MARKER_RADIUS + 1.0)}"'
            f' y="{_fmt(rc.entry_y + _CUT_ORDER_FONT_SIZE * 0.35)}"'
            f' font-size="{_CUT_ORDER_FONT_SIZE}" fill="{_CUT_ORDER_FILL}"'
            f' font-family="monospace"'
            f' data-role="cut-order-label">{rc.cut_order_index}</text>'
        )

    lines.append("</svg>")
    return "\n".join(lines) + "\n"
