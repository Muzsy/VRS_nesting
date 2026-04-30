from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any


class ResultNormalizerError(RuntimeError):
    pass


_OUT_OF_SHEET_EPS_MM = 1e-6


@dataclass(frozen=True)
class ProjectionSummary:
    placed_count: int
    unplaced_count: int
    used_sheet_count: int


@dataclass(frozen=True)
class NormalizedProjection:
    sheets: list[dict[str, Any]]
    placements: list[dict[str, Any]]
    unplaced: list[dict[str, Any]]
    metrics: dict[str, Any]
    summary: ProjectionSummary


def _require_dict(raw: Any, *, field: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ResultNormalizerError(f"invalid {field}")
    return raw


def _require_list(raw: Any, *, field: str) -> list[Any]:
    if not isinstance(raw, list):
        raise ResultNormalizerError(f"invalid {field}")
    return raw


def _require_str(raw: Any, *, field: str) -> str:
    value = str(raw or "").strip()
    if not value:
        raise ResultNormalizerError(f"invalid {field}")
    return value


def _parse_nonnegative_int(raw: Any, *, field: str) -> int:
    if isinstance(raw, bool):
        raise ResultNormalizerError(f"invalid {field}")
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ResultNormalizerError(f"invalid {field}") from exc
    if value < 0:
        raise ResultNormalizerError(f"invalid {field}")
    return value


def _parse_positive_int(raw: Any, *, field: str) -> int:
    value = _parse_nonnegative_int(raw, field=field)
    if value <= 0:
        raise ResultNormalizerError(f"invalid {field}")
    return value


def _parse_finite_float(raw: Any, *, field: str) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ResultNormalizerError(f"invalid {field}") from exc
    if not math.isfinite(value):
        raise ResultNormalizerError(f"invalid {field}")
    return value


def _parse_positive_float(raw: Any, *, field: str) -> float:
    value = _parse_finite_float(raw, field=field)
    if value <= 0.0:
        raise ResultNormalizerError(f"invalid {field}")
    return value


def _parse_point(raw: Any, *, field: str) -> tuple[float, float]:
    if isinstance(raw, list) and len(raw) == 2:
        x_raw, y_raw = raw
    elif isinstance(raw, dict):
        x_raw = raw.get("x")
        y_raw = raw.get("y")
    else:
        raise ResultNormalizerError(f"invalid {field}")
    return (_parse_finite_float(x_raw, field=f"{field}.x"), _parse_finite_float(y_raw, field=f"{field}.y"))


def _parse_ring(raw: Any, *, field: str) -> list[tuple[float, float]]:
    points = _require_list(raw, field=field)
    if len(points) < 3:
        raise ResultNormalizerError(f"invalid {field}")
    return [_parse_point(point_raw, field=f"{field}[{idx}]") for idx, point_raw in enumerate(points)]


def _parse_hole_rings(raw: Any, *, field: str) -> list[list[tuple[float, float]]]:
    rings = _require_list(raw, field=field)
    return [_parse_ring(ring_raw, field=f"{field}[{idx}]") for idx, ring_raw in enumerate(rings)]


def _round6(value: float) -> float:
    return round(float(value), 6)


def _round5(value: float) -> float:
    return round(float(value), 5)


def _ring_signed_area(ring: list[tuple[float, float]]) -> float:
    area2 = 0.0
    for idx in range(len(ring)):
        x1, y1 = ring[idx]
        x2, y2 = ring[(idx + 1) % len(ring)]
        area2 += x1 * y2 - x2 * y1
    return area2 / 2.0


def _polygon_area_mm2(outer_ring: list[tuple[float, float]], hole_rings: list[list[tuple[float, float]]]) -> float:
    outer = abs(_ring_signed_area(outer_ring))
    holes = sum(abs(_ring_signed_area(ring)) for ring in hole_rings)
    area = outer - holes
    if area <= 0.0:
        raise ResultNormalizerError("invalid geometry polygon area")
    return area


def placement_transform_point(
    *,
    local_x: float,
    local_y: float,
    tx: float,
    ty: float,
    rotation_deg: float,
    base_x: float = 0.0,
    base_y: float = 0.0,
) -> tuple[float, float]:
    theta = math.radians(rotation_deg)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    norm_x = local_x - base_x
    norm_y = local_y - base_y
    return (norm_x * cos_t - norm_y * sin_t + tx, norm_x * sin_t + norm_y * cos_t + ty)


def _bbox_origin_and_size(*, bbox: dict[str, float]) -> tuple[float, float, float, float]:
    min_x = _parse_finite_float(bbox.get("min_x"), field="bbox.min_x")
    min_y = _parse_finite_float(bbox.get("min_y"), field="bbox.min_y")
    max_x = _parse_finite_float(bbox.get("max_x"), field="bbox.max_x")
    max_y = _parse_finite_float(bbox.get("max_y"), field="bbox.max_y")
    if max_x <= min_x or max_y <= min_y:
        raise ResultNormalizerError("invalid geometry bbox")
    width = _parse_positive_float(bbox.get("width"), field="bbox.width")
    height = _parse_positive_float(bbox.get("height"), field="bbox.height")
    return (min_x, min_y, width, height)


def _transform_bbox(*, bbox: dict[str, float], x: float, y: float, rotation_deg: float) -> dict[str, float]:
    _, _, width, height = _bbox_origin_and_size(bbox=bbox)
    # Projection truth uses bbox-min origin reference: R(local - bbox_min) + translation.
    corners = ((0.0, 0.0), (width, 0.0), (width, height), (0.0, height))
    transformed: list[tuple[float, float]] = []
    for local_x, local_y in corners:
        transformed.append(
            placement_transform_point(
                local_x=local_x,
                local_y=local_y,
                tx=x,
                ty=y,
                rotation_deg=rotation_deg,
                base_x=0.0,
                base_y=0.0,
            )
        )

    xs = [point[0] for point in transformed]
    ys = [point[1] for point in transformed]
    out_min_x = min(xs)
    out_max_x = max(xs)
    out_min_y = min(ys)
    out_max_y = max(ys)

    return {
        "min_x": _round6(out_min_x),
        "min_y": _round6(out_min_y),
        "max_x": _round6(out_max_x),
        "max_y": _round6(out_max_y),
        "width": _round6(out_max_x - out_min_x),
        "height": _round6(out_max_y - out_min_y),
    }


def _assert_bbox_within_sheet(
    *,
    bbox: dict[str, float],
    sheet_width_mm: float,
    sheet_height_mm: float,
    sheet_index: int,
    instance_id: str,
) -> None:
    min_x = _parse_finite_float(bbox.get("min_x"), field="bbox_jsonb.min_x")
    min_y = _parse_finite_float(bbox.get("min_y"), field="bbox_jsonb.min_y")
    max_x = _parse_finite_float(bbox.get("max_x"), field="bbox_jsonb.max_x")
    max_y = _parse_finite_float(bbox.get("max_y"), field="bbox_jsonb.max_y")
    if (
        min_x < -_OUT_OF_SHEET_EPS_MM
        or min_y < -_OUT_OF_SHEET_EPS_MM
        or max_x > sheet_width_mm + _OUT_OF_SHEET_EPS_MM
        or max_y > sheet_height_mm + _OUT_OF_SHEET_EPS_MM
    ):
        raise ResultNormalizerError(
            "projected bbox out of sheet bounds: "
            f"sheet_index={sheet_index} instance_id={instance_id} "
            f"bbox=({min_x:.6f},{min_y:.6f},{max_x:.6f},{max_y:.6f}) "
            f"sheet=({sheet_width_mm:.6f},{sheet_height_mm:.6f}) "
            f"epsilon_mm={_OUT_OF_SHEET_EPS_MM:.6f}"
        )


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _load_enabled_cavity_plan(run_dir: Path) -> dict[str, Any] | None:
    cavity_plan_path = run_dir / "cavity_plan.json"
    if not cavity_plan_path.is_file():
        return None
    try:
        payload = json.loads(cavity_plan_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ResultNormalizerError(f"invalid cavity_plan json: {cavity_plan_path}") from exc
    plan = _require_dict(payload, field="cavity_plan")
    enabled = bool(plan.get("enabled"))
    if not enabled:
        return None
    version = str(plan.get("version") or "").strip()
    if version != "cavity_plan_v1":
        raise ResultNormalizerError(f"invalid cavity_plan version: {version or '<empty>'}")
    return plan


def _normalize_rotation_deg(value: float) -> float:
    normalized = float(value) % 360.0
    if normalized < 0.0:
        normalized += 360.0
    return normalized


def _build_part_index(snapshot_row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    geometry_manifest = _require_list(snapshot_row.get("geometry_manifest_jsonb"), field="geometry_manifest_jsonb")
    geometry_by_derivative: dict[str, dict[str, Any]] = {}
    for idx, geometry_raw in enumerate(geometry_manifest):
        geometry = _require_dict(geometry_raw, field=f"geometry_manifest_jsonb[{idx}]")
        derivative_id = _require_str(
            geometry.get("selected_nesting_derivative_id"),
            field=f"geometry_manifest_jsonb[{idx}].selected_nesting_derivative_id",
        )
        polygon = _require_dict(geometry.get("polygon"), field=f"geometry_manifest_jsonb[{idx}].polygon")
        bbox = _require_dict(geometry.get("bbox"), field=f"geometry_manifest_jsonb[{idx}].bbox")

        outer_ring = _parse_ring(polygon.get("outer_ring"), field=f"geometry_manifest_jsonb[{idx}].polygon.outer_ring")
        hole_rings = _parse_hole_rings(
            polygon.get("hole_rings", []),
            field=f"geometry_manifest_jsonb[{idx}].polygon.hole_rings",
        )
        area_mm2 = _polygon_area_mm2(outer_ring, hole_rings)
        geometry_by_derivative[derivative_id] = {
            "bbox": {
                "min_x": _parse_finite_float(bbox.get("min_x"), field=f"geometry_manifest_jsonb[{idx}].bbox.min_x"),
                "min_y": _parse_finite_float(bbox.get("min_y"), field=f"geometry_manifest_jsonb[{idx}].bbox.min_y"),
                "max_x": _parse_finite_float(bbox.get("max_x"), field=f"geometry_manifest_jsonb[{idx}].bbox.max_x"),
                "max_y": _parse_finite_float(bbox.get("max_y"), field=f"geometry_manifest_jsonb[{idx}].bbox.max_y"),
                "width": _parse_positive_float(bbox.get("width"), field=f"geometry_manifest_jsonb[{idx}].bbox.width"),
                "height": _parse_positive_float(bbox.get("height"), field=f"geometry_manifest_jsonb[{idx}].bbox.height"),
            },
            "area_mm2": area_mm2,
        }

    parts_manifest_raw = _require_list(snapshot_row.get("parts_manifest_jsonb"), field="parts_manifest_jsonb")
    parts_manifest = [item for item in parts_manifest_raw if isinstance(item, dict)]
    parts_manifest.sort(
        key=lambda item: (
            int(item.get("placement_priority") or 0),
            str(item.get("part_code") or ""),
            str(item.get("part_revision_id") or ""),
            str(item.get("project_part_requirement_id") or ""),
        )
    )

    part_index: dict[str, dict[str, Any]] = {}
    for idx, part in enumerate(parts_manifest):
        part_revision_id = _require_str(part.get("part_revision_id"), field=f"parts_manifest_jsonb[{idx}].part_revision_id")
        derivative_id = _require_str(
            part.get("selected_nesting_derivative_id"),
            field=f"parts_manifest_jsonb[{idx}].selected_nesting_derivative_id",
        )
        if part_revision_id in part_index:
            raise ResultNormalizerError(f"duplicate part_revision_id in snapshot: {part_revision_id}")
        geometry = geometry_by_derivative.get(derivative_id)
        if geometry is None:
            raise ResultNormalizerError(f"missing geometry for derivative: {derivative_id}")
        part_index[part_revision_id] = {
            "part_revision_id": part_revision_id,
            "part_definition_id": _require_str(part.get("part_definition_id"), field=f"parts_manifest_jsonb[{idx}].part_definition_id"),
            "part_code": _require_str(part.get("part_code"), field=f"parts_manifest_jsonb[{idx}].part_code"),
            "source_geometry_revision_id": _require_str(
                part.get("source_geometry_revision_id"),
                field=f"parts_manifest_jsonb[{idx}].source_geometry_revision_id",
            ),
            "selected_nesting_derivative_id": derivative_id,
            "bbox": geometry["bbox"],
            "area_mm2": geometry["area_mm2"],
        }

    return part_index


def _build_sheet_instances(snapshot_row: dict[str, Any]) -> list[dict[str, Any]]:
    sheets_manifest_raw = _require_list(snapshot_row.get("sheets_manifest_jsonb"), field="sheets_manifest_jsonb")
    sheets_manifest = [item for item in sheets_manifest_raw if isinstance(item, dict)]
    sheets_manifest.sort(
        key=lambda item: (
            0 if bool(item.get("is_default")) else 1,
            int(item.get("placement_priority") or 0),
            str(item.get("sheet_code") or ""),
            str(item.get("sheet_revision_id") or ""),
            str(item.get("project_sheet_input_id") or ""),
        )
    )

    expanded: list[dict[str, Any]] = []
    for idx, sheet in enumerate(sheets_manifest):
        required_qty = _parse_positive_int(sheet.get("required_qty"), field=f"sheets_manifest_jsonb[{idx}].required_qty")
        sheet_revision_id = _require_str(sheet.get("sheet_revision_id"), field=f"sheets_manifest_jsonb[{idx}].sheet_revision_id")
        width_mm = _parse_positive_float(sheet.get("width_mm"), field=f"sheets_manifest_jsonb[{idx}].width_mm")
        height_mm = _parse_positive_float(sheet.get("height_mm"), field=f"sheets_manifest_jsonb[{idx}].height_mm")
        for copy_index in range(required_qty):
            expanded.append(
                {
                    "sheet_index": len(expanded),
                    "sheet_revision_id": sheet_revision_id,
                    "width_mm": width_mm,
                    "height_mm": height_mm,
                    "sheet_code": str(sheet.get("sheet_code") or ""),
                    "project_sheet_input_id": str(sheet.get("project_sheet_input_id") or ""),
                    "copy_index": copy_index,
                }
            )
    if not expanded:
        raise ResultNormalizerError("empty sheets manifest")
    return expanded


def _normalize_solver_output_projection_v1(*, run_id: str, snapshot_row: dict[str, Any], run_dir: Path) -> NormalizedProjection:
    run_id_clean = _require_str(run_id, field="run_id")
    output_path = run_dir / "solver_output.json"
    try:
        output_payload = json.loads(output_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ResultNormalizerError(f"invalid solver output json: {output_path}") from exc
    output = _require_dict(output_payload, field="solver_output")
    if output.get("contract_version") != "v1":
        raise ResultNormalizerError("invalid solver output contract_version")

    placements_raw = _require_list(output.get("placements"), field="solver_output.placements")
    unplaced_raw = _require_list(output.get("unplaced"), field="solver_output.unplaced")

    part_index = _build_part_index(snapshot_row)
    sheet_instances = _build_sheet_instances(snapshot_row)

    placement_rows: list[dict[str, Any]] = []
    sheet_used: set[int] = set()
    per_sheet_counter: dict[int, int] = {}
    per_sheet_placed_area: dict[int, float] = {}

    for idx, placement_raw in enumerate(placements_raw):
        placement = _require_dict(placement_raw, field=f"solver_output.placements[{idx}]")
        part_id = _require_str(placement.get("part_id"), field=f"solver_output.placements[{idx}].part_id")
        part = part_index.get(part_id)
        if part is None:
            raise ResultNormalizerError(f"unknown part_id in solver output: {part_id}")

        sheet_index = _parse_nonnegative_int(placement.get("sheet_index"), field=f"solver_output.placements[{idx}].sheet_index")
        if sheet_index >= len(sheet_instances):
            raise ResultNormalizerError(f"invalid sheet_index in solver output: {sheet_index}")
        sheet_used.add(sheet_index)

        instance_id = _require_str(placement.get("instance_id"), field=f"solver_output.placements[{idx}].instance_id")
        x = _parse_finite_float(placement.get("x"), field=f"solver_output.placements[{idx}].x")
        y = _parse_finite_float(placement.get("y"), field=f"solver_output.placements[{idx}].y")
        rotation_deg = _parse_finite_float(placement.get("rotation_deg"), field=f"solver_output.placements[{idx}].rotation_deg")

        placement_index = per_sheet_counter.get(sheet_index, 0)
        per_sheet_counter[sheet_index] = placement_index + 1
        per_sheet_placed_area[sheet_index] = per_sheet_placed_area.get(sheet_index, 0.0) + float(part["area_mm2"])

        transform_jsonb = {
            "x": _round6(x),
            "y": _round6(y),
            "rotation_deg": _round6(rotation_deg),
            "sheet_index": int(sheet_index),
            "instance_id": instance_id,
        }
        bbox_jsonb = _transform_bbox(bbox=part["bbox"], x=x, y=y, rotation_deg=rotation_deg)
        metadata_jsonb = {
            "normalizer_scope": "h1_e6_t1",
            "part_code": part["part_code"],
            "part_definition_id": part["part_definition_id"],
            "source_geometry_revision_id": part["source_geometry_revision_id"],
            "selected_nesting_derivative_id": part["selected_nesting_derivative_id"],
        }

        placement_rows.append(
            {
                "sheet_index": int(sheet_index),
                "placement_index": int(placement_index),
                "part_revision_id": part_id,
                "quantity": 1,
                "transform_jsonb": transform_jsonb,
                "bbox_jsonb": bbox_jsonb,
                "metadata_jsonb": metadata_jsonb,
            }
        )

    placement_rows.sort(key=lambda item: (int(item["sheet_index"]), int(item["placement_index"])))

    sheet_rows: list[dict[str, Any]] = []
    total_sheet_area = 0.0
    total_placed_area = 0.0
    per_sheet_metrics: list[dict[str, Any]] = []
    for sheet_index in sorted(sheet_used):
        sheet = sheet_instances[sheet_index]
        width_mm = float(sheet["width_mm"])
        height_mm = float(sheet["height_mm"])
        sheet_area = width_mm * height_mm
        placed_area = float(per_sheet_placed_area.get(sheet_index, 0.0))
        sheet_utilization = (placed_area / sheet_area) if sheet_area > 0.0 else None

        total_sheet_area += sheet_area
        total_placed_area += placed_area

        sheet_row = {
            "sheet_index": int(sheet_index),
            "sheet_revision_id": str(sheet["sheet_revision_id"]),
            "width_mm": _round6(width_mm),
            "height_mm": _round6(height_mm),
            "utilization_ratio": _round5(sheet_utilization) if sheet_utilization is not None else None,
            "metadata_jsonb": {
                "normalizer_scope": "h1_e6_t1",
                "sheet_code": str(sheet["sheet_code"]),
                "project_sheet_input_id": str(sheet["project_sheet_input_id"]),
                "copy_index": int(sheet["copy_index"]),
                "placements_count": int(per_sheet_counter.get(sheet_index, 0)),
                "placed_area_mm2": _round6(placed_area),
                "sheet_area_mm2": _round6(sheet_area),
            },
        }
        sheet_rows.append(sheet_row)

        per_sheet_metrics.append(
            {
                "sheet_index": int(sheet_index),
                "placements_count": int(per_sheet_counter.get(sheet_index, 0)),
                "placed_area_mm2": _round6(placed_area),
                "sheet_area_mm2": _round6(sheet_area),
                "utilization_ratio": _round5(sheet_utilization) if sheet_utilization is not None else None,
            }
        )

    unplaced_bucket: dict[tuple[str, str], dict[str, Any]] = {}
    for idx, unplaced_item_raw in enumerate(unplaced_raw):
        unplaced_item = _require_dict(unplaced_item_raw, field=f"solver_output.unplaced[{idx}]")
        part_id = _require_str(unplaced_item.get("part_id"), field=f"solver_output.unplaced[{idx}].part_id")
        part = part_index.get(part_id)
        if part is None:
            raise ResultNormalizerError(f"unknown part_id in solver output unplaced: {part_id}")
        instance_id = _require_str(unplaced_item.get("instance_id"), field=f"solver_output.unplaced[{idx}].instance_id")
        reason_raw = str(unplaced_item.get("reason") or "").strip()
        reason_key = reason_raw or ""

        key = (part_id, reason_key)
        if key not in unplaced_bucket:
            unplaced_bucket[key] = {
                "part_revision_id": part_id,
                "reason": reason_raw or None,
                "remaining_qty": 0,
                "instance_ids": [],
                "part_code": part["part_code"],
            }
        unplaced_bucket[key]["remaining_qty"] = int(unplaced_bucket[key]["remaining_qty"]) + 1
        unplaced_bucket[key]["instance_ids"].append(instance_id)

    unplaced_rows: list[dict[str, Any]] = []
    for key in sorted(unplaced_bucket.keys(), key=lambda item: (item[0], item[1])):
        bucket = unplaced_bucket[key]
        unplaced_rows.append(
            {
                "part_revision_id": str(bucket["part_revision_id"]),
                "remaining_qty": int(bucket["remaining_qty"]),
                "reason": bucket["reason"],
                "metadata_jsonb": {
                    "normalizer_scope": "h1_e6_t1",
                    "part_code": str(bucket["part_code"]),
                    "instance_ids": sorted(str(value) for value in bucket["instance_ids"]),
                },
            }
        )

    placed_count = len(placement_rows)
    unplaced_count = sum(int(row["remaining_qty"]) for row in unplaced_rows)
    used_sheet_count = len(sheet_rows)
    run_utilization = (total_placed_area / total_sheet_area) if total_sheet_area > 0.0 else None

    raw_metrics = output.get("metrics")
    metrics_jsonb: dict[str, Any] = {
        "normalizer_scope": "h1_e6_t1",
        "run_id": run_id_clean,
        "placement_origin_ref": "bbox_min_corner",
        "sheet_bounds_epsilon_mm": _OUT_OF_SHEET_EPS_MM,
        "solver_status": str(output.get("status") or "").strip() or None,
        "per_sheet": per_sheet_metrics,
        "totals": {
            "placed_area_mm2": _round6(total_placed_area),
            "sheet_area_mm2": _round6(total_sheet_area),
        },
    }
    if isinstance(raw_metrics, dict):
        metrics_jsonb["raw_solver_metrics"] = raw_metrics

    metrics_row = {
        "placed_count": int(placed_count),
        "unplaced_count": int(unplaced_count),
        "used_sheet_count": int(used_sheet_count),
        "utilization_ratio": _round5(run_utilization) if run_utilization is not None else None,
        "remnant_value": None,
        "metrics_jsonb": metrics_jsonb,
    }

    return NormalizedProjection(
        sheets=sheet_rows,
        placements=placement_rows,
        unplaced=unplaced_rows,
        metrics=metrics_row,
        summary=ProjectionSummary(
            placed_count=int(placed_count),
            unplaced_count=int(unplaced_count),
            used_sheet_count=int(used_sheet_count),
        ),
    )


def _normalize_solver_output_projection_v2(*, run_id: str, snapshot_row: dict[str, Any], run_dir: Path) -> NormalizedProjection:
    run_id_clean = _require_str(run_id, field="run_id")
    output_path = run_dir / "nesting_output.json"
    try:
        output_payload = json.loads(output_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ResultNormalizerError(f"invalid nesting_engine output json: {output_path}") from exc
    output = _require_dict(output_payload, field="nesting_output")
    if output.get("version") != "nesting_engine_v2":
        raise ResultNormalizerError("invalid nesting_engine output version")

    placements_raw = _require_list(output.get("placements"), field="nesting_output.placements")
    unplaced_raw = _require_list(output.get("unplaced"), field="nesting_output.unplaced")

    part_index = _build_part_index(snapshot_row)
    sheet_instances = _build_sheet_instances(snapshot_row)
    cavity_plan = _load_enabled_cavity_plan(run_dir)
    cavity_enabled = cavity_plan is not None
    cavity_plan_version = str(cavity_plan.get("version")) if cavity_enabled else None

    virtual_parts: dict[str, dict[str, Any]] = {}
    top_level_instance_bases: dict[str, int] = {}
    if cavity_enabled:
        virtual_raw = _require_dict(cavity_plan.get("virtual_parts"), field="cavity_plan.virtual_parts")
        for virtual_id_raw, virtual_item_raw in virtual_raw.items():
            virtual_id = _require_str(virtual_id_raw, field="cavity_plan.virtual_parts.<key>")
            virtual_item = _require_dict(virtual_item_raw, field=f"cavity_plan.virtual_parts.{virtual_id}")
            parent_part_revision_id = _require_str(
                virtual_item.get("parent_part_revision_id"),
                field=f"cavity_plan.virtual_parts.{virtual_id}.parent_part_revision_id",
            )
            parent_instance = _parse_nonnegative_int(
                virtual_item.get("parent_instance"),
                field=f"cavity_plan.virtual_parts.{virtual_id}.parent_instance",
            )
            internal_raw = _require_list(
                virtual_item.get("internal_placements", []),
                field=f"cavity_plan.virtual_parts.{virtual_id}.internal_placements",
            )
            internal_placements: list[dict[str, Any]] = []
            for internal_idx, internal_raw_item in enumerate(internal_raw):
                internal_item = _require_dict(
                    internal_raw_item,
                    field=f"cavity_plan.virtual_parts.{virtual_id}.internal_placements[{internal_idx}]",
                )
                internal_placements.append(
                    {
                        "child_part_revision_id": _require_str(
                            internal_item.get("child_part_revision_id"),
                            field=(
                                "cavity_plan.virtual_parts."
                                f"{virtual_id}.internal_placements[{internal_idx}].child_part_revision_id"
                            ),
                        ),
                        "child_instance": _parse_nonnegative_int(
                            internal_item.get("child_instance"),
                            field=(
                                "cavity_plan.virtual_parts."
                                f"{virtual_id}.internal_placements[{internal_idx}].child_instance"
                            ),
                        ),
                        "cavity_index": _parse_nonnegative_int(
                            internal_item.get("cavity_index"),
                            field=(
                                "cavity_plan.virtual_parts."
                                f"{virtual_id}.internal_placements[{internal_idx}].cavity_index"
                            ),
                        ),
                        "x_local_mm": _parse_finite_float(
                            internal_item.get("x_local_mm"),
                            field=(
                                "cavity_plan.virtual_parts."
                                f"{virtual_id}.internal_placements[{internal_idx}].x_local_mm"
                            ),
                        ),
                        "y_local_mm": _parse_finite_float(
                            internal_item.get("y_local_mm"),
                            field=(
                                "cavity_plan.virtual_parts."
                                f"{virtual_id}.internal_placements[{internal_idx}].y_local_mm"
                            ),
                        ),
                        "rotation_deg": _parse_finite_float(
                            internal_item.get("rotation_deg"),
                            field=(
                                "cavity_plan.virtual_parts."
                                f"{virtual_id}.internal_placements[{internal_idx}].rotation_deg"
                            ),
                        ),
                        "placement_origin_ref": str(internal_item.get("placement_origin_ref") or "").strip() or None,
                    }
                )
            virtual_parts[virtual_id] = {
                "parent_part_revision_id": parent_part_revision_id,
                "parent_instance": parent_instance,
                "internal_placements": internal_placements,
            }

        instance_bases_raw = _require_dict(cavity_plan.get("instance_bases"), field="cavity_plan.instance_bases")
        for child_part_id_raw, base_item_raw in instance_bases_raw.items():
            child_part_id = _require_str(child_part_id_raw, field="cavity_plan.instance_bases.<key>")
            base_item = _require_dict(base_item_raw, field=f"cavity_plan.instance_bases.{child_part_id}")
            top_level_instance_bases[child_part_id] = _parse_nonnegative_int(
                base_item.get("top_level_instance_base", 0),
                field=f"cavity_plan.instance_bases.{child_part_id}.top_level_instance_base",
            )

    placement_rows: list[dict[str, Any]] = []
    sheet_used: set[int] = set()
    per_sheet_counter: dict[int, int] = {}
    per_sheet_placed_area: dict[int, float] = {}

    def _append_placement_row(
        *,
        sheet_index: int,
        part_revision_id: str,
        instance_id: str,
        x: float,
        y: float,
        rotation_deg: float,
        part: dict[str, Any],
        metadata_jsonb: dict[str, Any],
    ) -> None:
        placement_index = per_sheet_counter.get(sheet_index, 0)
        per_sheet_counter[sheet_index] = placement_index + 1
        per_sheet_placed_area[sheet_index] = per_sheet_placed_area.get(sheet_index, 0.0) + float(part["area_mm2"])
        transform_jsonb = {
            "x": _round6(x),
            "y": _round6(y),
            "rotation_deg": _round6(rotation_deg),
            "sheet_index": int(sheet_index),
            "instance_id": instance_id,
        }
        placement_rows.append(
            {
                "sheet_index": int(sheet_index),
                "placement_index": int(placement_index),
                "part_revision_id": part_revision_id,
                "quantity": 1,
                "transform_jsonb": transform_jsonb,
                "bbox_jsonb": _transform_bbox(bbox=part["bbox"], x=x, y=y, rotation_deg=rotation_deg),
                "metadata_jsonb": metadata_jsonb,
            }
        )

    for idx, placement_raw in enumerate(placements_raw):
        placement = _require_dict(placement_raw, field=f"nesting_output.placements[{idx}]")
        part_id = _require_str(placement.get("part_id"), field=f"nesting_output.placements[{idx}].part_id")
        instance = _parse_nonnegative_int(placement.get("instance"), field=f"nesting_output.placements[{idx}].instance")
        sheet_index = _parse_nonnegative_int(placement.get("sheet"), field=f"nesting_output.placements[{idx}].sheet")
        if sheet_index >= len(sheet_instances):
            raise ResultNormalizerError(f"invalid sheet in nesting_output: {sheet_index}")
        sheet_used.add(sheet_index)

        x = _parse_finite_float(placement.get("x_mm"), field=f"nesting_output.placements[{idx}].x_mm")
        y = _parse_finite_float(placement.get("y_mm"), field=f"nesting_output.placements[{idx}].y_mm")
        rotation_deg = _parse_finite_float(
            placement.get("rotation_deg"),
            field=f"nesting_output.placements[{idx}].rotation_deg",
        )

        virtual = virtual_parts.get(part_id) if cavity_enabled else None
        if virtual is not None:
            parent_part_id = str(virtual["parent_part_revision_id"])
            parent_part = part_index.get(parent_part_id)
            if parent_part is None:
                raise ResultNormalizerError(f"missing parent part in cavity plan: {parent_part_id}")
            parent_instance = int(virtual["parent_instance"])
            parent_instance_id = f"{parent_part_id}:{parent_instance}"
            parent_metadata: dict[str, Any] = {
                "normalizer_scope": "h3_quality_t4_v2_bridge",
                "engine_backend": "nesting_engine_v2",
                "part_code": parent_part["part_code"],
                "part_definition_id": parent_part["part_definition_id"],
                "source_geometry_revision_id": parent_part["source_geometry_revision_id"],
                "selected_nesting_derivative_id": parent_part["selected_nesting_derivative_id"],
                "instance": int(parent_instance),
            }
            if cavity_enabled:
                parent_metadata.update(
                    {
                        "placement_scope": "top_level_parent",
                        "cavity_plan_version": cavity_plan_version,
                        "solver_instance": int(instance),
                    }
                )
            _append_placement_row(
                sheet_index=sheet_index,
                part_revision_id=parent_part_id,
                instance_id=parent_instance_id,
                x=x,
                y=y,
                rotation_deg=rotation_deg,
                part=parent_part,
                metadata_jsonb=parent_metadata,
            )

            for internal_idx, internal in enumerate(virtual["internal_placements"]):
                child_part_id = str(internal["child_part_revision_id"])
                child_part = part_index.get(child_part_id)
                if child_part is None:
                    raise ResultNormalizerError(f"unknown child part in cavity plan: {child_part_id}")
                child_instance = int(internal["child_instance"])
                local_x = float(internal["x_local_mm"])
                local_y = float(internal["y_local_mm"])
                local_rotation = float(internal["rotation_deg"])
                abs_x, abs_y = placement_transform_point(
                    local_x=local_x,
                    local_y=local_y,
                    tx=x,
                    ty=y,
                    rotation_deg=rotation_deg,
                )
                abs_rotation = _normalize_rotation_deg(rotation_deg + local_rotation)
                child_instance_id = f"{child_part_id}:{child_instance}"
                child_metadata: dict[str, Any] = {
                    "normalizer_scope": "h3_quality_t4_v2_bridge",
                    "engine_backend": "nesting_engine_v2",
                    "part_code": child_part["part_code"],
                    "part_definition_id": child_part["part_definition_id"],
                    "source_geometry_revision_id": child_part["source_geometry_revision_id"],
                    "selected_nesting_derivative_id": child_part["selected_nesting_derivative_id"],
                    "instance": int(child_instance),
                    "placement_scope": "internal_cavity",
                    "cavity_plan_version": cavity_plan_version,
                    "parent_part_revision_id": parent_part_id,
                    "parent_instance": int(parent_instance),
                    "internal_placement_index": int(internal_idx),
                    "cavity_index": int(internal["cavity_index"]),
                    "local_transform": {
                        "x_local_mm": _round6(local_x),
                        "y_local_mm": _round6(local_y),
                        "rotation_deg": _round6(local_rotation),
                        "placement_origin_ref": internal["placement_origin_ref"],
                    },
                }
                _append_placement_row(
                    sheet_index=sheet_index,
                    part_revision_id=child_part_id,
                    instance_id=child_instance_id,
                    x=abs_x,
                    y=abs_y,
                    rotation_deg=abs_rotation,
                    part=child_part,
                    metadata_jsonb=child_metadata,
                )
            continue

        part = part_index.get(part_id)
        if part is None:
            raise ResultNormalizerError(f"unknown part_id in nesting_output: {part_id}")
        top_level_instance_base = int(top_level_instance_bases.get(part_id, 0)) if cavity_enabled else 0
        mapped_instance = instance + top_level_instance_base
        metadata_jsonb: dict[str, Any] = {
            "normalizer_scope": "h3_quality_t4_v2_bridge",
            "engine_backend": "nesting_engine_v2",
            "part_code": part["part_code"],
            "part_definition_id": part["part_definition_id"],
            "source_geometry_revision_id": part["source_geometry_revision_id"],
            "selected_nesting_derivative_id": part["selected_nesting_derivative_id"],
            "instance": int(mapped_instance),
        }
        if cavity_enabled:
            metadata_jsonb.update(
                {
                    "placement_scope": "top_level",
                    "cavity_plan_version": cavity_plan_version,
                    "solver_instance": int(instance),
                    "top_level_instance_base": int(top_level_instance_base),
                }
            )
        _append_placement_row(
            sheet_index=sheet_index,
            part_revision_id=part_id,
            instance_id=f"{part_id}:{mapped_instance}",
            x=x,
            y=y,
            rotation_deg=rotation_deg,
            part=part,
            metadata_jsonb=metadata_jsonb,
        )

    placement_rows.sort(key=lambda item: (int(item["sheet_index"]), int(item["placement_index"])))

    sheet_rows: list[dict[str, Any]] = []
    total_sheet_area = 0.0
    total_placed_area = 0.0
    per_sheet_metrics: list[dict[str, Any]] = []
    for sheet_index in sorted(sheet_used):
        sheet = sheet_instances[sheet_index]
        width_mm = float(sheet["width_mm"])
        height_mm = float(sheet["height_mm"])
        sheet_area = width_mm * height_mm
        placed_area = float(per_sheet_placed_area.get(sheet_index, 0.0))
        sheet_utilization = (placed_area / sheet_area) if sheet_area > 0.0 else None

        total_sheet_area += sheet_area
        total_placed_area += placed_area

        sheet_row = {
            "sheet_index": int(sheet_index),
            "sheet_revision_id": str(sheet["sheet_revision_id"]),
            "width_mm": _round6(width_mm),
            "height_mm": _round6(height_mm),
            "utilization_ratio": _round5(sheet_utilization) if sheet_utilization is not None else None,
            "metadata_jsonb": {
                "normalizer_scope": "h3_quality_t4_v2_bridge",
                "engine_backend": "nesting_engine_v2",
                "sheet_code": str(sheet["sheet_code"]),
                "project_sheet_input_id": str(sheet["project_sheet_input_id"]),
                "copy_index": int(sheet["copy_index"]),
                "placements_count": int(per_sheet_counter.get(sheet_index, 0)),
                "placed_area_mm2": _round6(placed_area),
                "sheet_area_mm2": _round6(sheet_area),
            },
        }
        sheet_rows.append(sheet_row)

        per_sheet_metrics.append(
            {
                "sheet_index": int(sheet_index),
                "placements_count": int(per_sheet_counter.get(sheet_index, 0)),
                "placed_area_mm2": _round6(placed_area),
                "sheet_area_mm2": _round6(sheet_area),
                "utilization_ratio": _round5(sheet_utilization) if sheet_utilization is not None else None,
            }
        )

    unplaced_bucket: dict[tuple[str, str], dict[str, Any]] = {}
    for idx, unplaced_item_raw in enumerate(unplaced_raw):
        unplaced_item = _require_dict(unplaced_item_raw, field=f"nesting_output.unplaced[{idx}]")
        part_id = _require_str(unplaced_item.get("part_id"), field=f"nesting_output.unplaced[{idx}].part_id")
        instance = _parse_nonnegative_int(unplaced_item.get("instance"), field=f"nesting_output.unplaced[{idx}].instance")
        reason_raw = str(unplaced_item.get("reason") or "").strip()
        reason_key = reason_raw or ""
        mapped_part_id = part_id
        mapped_instance = instance
        if cavity_enabled:
            virtual = virtual_parts.get(part_id)
            if virtual is not None:
                mapped_part_id = str(virtual["parent_part_revision_id"])
                mapped_instance = int(virtual["parent_instance"])
            else:
                mapped_instance = instance + int(top_level_instance_bases.get(part_id, 0))
        part = part_index.get(mapped_part_id)
        if part is None:
            raise ResultNormalizerError(f"unknown part_id in nesting_output unplaced: {mapped_part_id}")
        key = (mapped_part_id, reason_key)
        if key not in unplaced_bucket:
            unplaced_bucket[key] = {
                "part_revision_id": mapped_part_id,
                "reason": reason_raw or None,
                "remaining_qty": 0,
                "instance_ids": [],
                "part_code": part["part_code"],
            }
        unplaced_bucket[key]["remaining_qty"] = int(unplaced_bucket[key]["remaining_qty"]) + 1
        unplaced_bucket[key]["instance_ids"].append(f"{mapped_part_id}:{mapped_instance}")

    unplaced_rows: list[dict[str, Any]] = []
    for key in sorted(unplaced_bucket.keys(), key=lambda item: (item[0], item[1])):
        bucket = unplaced_bucket[key]
        unplaced_rows.append(
            {
                "part_revision_id": str(bucket["part_revision_id"]),
                "remaining_qty": int(bucket["remaining_qty"]),
                "reason": bucket["reason"],
                "metadata_jsonb": {
                    "normalizer_scope": "h3_quality_t4_v2_bridge",
                    "engine_backend": "nesting_engine_v2",
                    "part_code": str(bucket["part_code"]),
                    "instance_ids": sorted(str(value) for value in bucket["instance_ids"]),
                    **(
                        {
                            "placement_scope": "unplaced",
                            "cavity_plan_version": cavity_plan_version,
                        }
                        if cavity_enabled
                        else {}
                    ),
                },
            }
        )

    placed_count = len(placement_rows)
    unplaced_count = sum(int(row["remaining_qty"]) for row in unplaced_rows)
    used_sheet_count = len(sheet_rows)
    computed_run_utilization = (total_placed_area / total_sheet_area) if total_sheet_area > 0.0 else None

    objective = output.get("objective")
    objective_dict = objective if isinstance(objective, dict) else {}
    objective_util_pct = objective_dict.get("utilization_pct")
    objective_util_ratio: float | None = None
    if isinstance(objective_util_pct, (int, float)):
        objective_util_ratio = _round5(float(objective_util_pct) / 100.0)

    remnant_value = objective_dict.get("remnant_value_ppm")
    remnant_value_float: float | None = None
    if isinstance(remnant_value, (int, float)):
        remnant_value_float = float(remnant_value)

    metrics_jsonb: dict[str, Any] = {
        "normalizer_scope": "h3_quality_t4_v2_bridge",
        "engine_backend": "nesting_engine_v2",
        "run_id": run_id_clean,
        "placement_origin_ref": "bbox_min_corner",
        "sheet_bounds_epsilon_mm": _OUT_OF_SHEET_EPS_MM,
        "solver_status": str(output.get("status") or "").strip() or None,
        "per_sheet": per_sheet_metrics,
        "totals": {
            "placed_area_mm2": _round6(total_placed_area),
            "sheet_area_mm2": _round6(total_sheet_area),
        },
        "objective": objective_dict,
        "meta": output.get("meta") if isinstance(output.get("meta"), dict) else {},
        "sheets_used_reported": _parse_nonnegative_int(output.get("sheets_used", 0), field="nesting_output.sheets_used"),
    }
    if cavity_enabled:
        metrics_jsonb["cavity_plan"] = {
            "enabled": True,
            "version": cavity_plan_version,
            "virtual_parent_count": len(virtual_parts),
        }

    metrics_row = {
        "placed_count": int(placed_count),
        "unplaced_count": int(unplaced_count),
        "used_sheet_count": int(used_sheet_count),
        "utilization_ratio": objective_util_ratio if objective_util_ratio is not None else (_round5(computed_run_utilization) if computed_run_utilization is not None else None),
        "remnant_value": remnant_value_float,
        "metrics_jsonb": metrics_jsonb,
    }

    return NormalizedProjection(
        sheets=sheet_rows,
        placements=placement_rows,
        unplaced=unplaced_rows,
        metrics=metrics_row,
        summary=ProjectionSummary(
            placed_count=int(placed_count),
            unplaced_count=int(unplaced_count),
            used_sheet_count=int(used_sheet_count),
        ),
    )


def normalize_solver_output_projection(*, run_id: str, snapshot_row: dict[str, Any], run_dir: Path) -> NormalizedProjection:
    if (run_dir / "solver_output.json").is_file():
        return _normalize_solver_output_projection_v1(run_id=run_id, snapshot_row=snapshot_row, run_dir=run_dir)
    if (run_dir / "nesting_output.json").is_file():
        return _normalize_solver_output_projection_v2(run_id=run_id, snapshot_row=snapshot_row, run_dir=run_dir)
    raise ResultNormalizerError("missing solver output json: expected solver_output.json or nesting_output.json")


def normalized_projection_json(payload: NormalizedProjection) -> str:
    return _canonical_json(
        {
            "sheets": payload.sheets,
            "placements": payload.placements,
            "unplaced": payload.unplaced,
            "metrics": payload.metrics,
            "summary": {
                "placed_count": payload.summary.placed_count,
                "unplaced_count": payload.summary.unplaced_count,
                "used_sheet_count": payload.summary.used_sheet_count,
            },
        }
    )


def assert_projection_within_sheet_bounds(
    *,
    sheets: list[dict[str, Any]],
    placements: list[dict[str, Any]],
) -> None:
    sheet_bounds: dict[int, tuple[float, float]] = {}
    for idx, sheet in enumerate(sheets):
        if not isinstance(sheet, dict):
            raise ResultNormalizerError(f"invalid sheets[{idx}]")
        sheet_index = _parse_nonnegative_int(sheet.get("sheet_index"), field=f"sheets[{idx}].sheet_index")
        width_mm = _parse_positive_float(sheet.get("width_mm"), field=f"sheets[{idx}].width_mm")
        height_mm = _parse_positive_float(sheet.get("height_mm"), field=f"sheets[{idx}].height_mm")
        sheet_bounds[sheet_index] = (width_mm, height_mm)

    for idx, placement in enumerate(placements):
        if not isinstance(placement, dict):
            raise ResultNormalizerError(f"invalid placements[{idx}]")
        sheet_index = _parse_nonnegative_int(placement.get("sheet_index"), field=f"placements[{idx}].sheet_index")
        bounds = sheet_bounds.get(sheet_index)
        if bounds is None:
            raise ResultNormalizerError(f"invalid placement sheet relation: {sheet_index}")
        transform = _require_dict(placement.get("transform_jsonb"), field=f"placements[{idx}].transform_jsonb")
        instance_id = _require_str(transform.get("instance_id"), field=f"placements[{idx}].transform_jsonb.instance_id")
        bbox = _require_dict(placement.get("bbox_jsonb"), field=f"placements[{idx}].bbox_jsonb")
        _assert_bbox_within_sheet(
            bbox=bbox,
            sheet_width_mm=bounds[0],
            sheet_height_mm=bounds[1],
            sheet_index=sheet_index,
            instance_id=instance_id,
        )
