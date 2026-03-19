from __future__ import annotations

import hashlib
import json
import math
from typing import Any


class EngineAdapterInputError(RuntimeError):
    pass


def _require_dict(raw: Any, *, field: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise EngineAdapterInputError(f"invalid {field}")
    return raw


def _require_list(raw: Any, *, field: str) -> list[Any]:
    if not isinstance(raw, list):
        raise EngineAdapterInputError(f"invalid {field}")
    return raw


def _require_non_empty_string(raw: Any, *, field: str) -> str:
    value = str(raw or "").strip()
    if not value:
        raise EngineAdapterInputError(f"invalid {field}")
    return value


def _parse_nonnegative_int(raw: Any, *, field: str) -> int:
    if isinstance(raw, bool):
        raise EngineAdapterInputError(f"invalid {field}")
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise EngineAdapterInputError(f"invalid {field}") from exc
    if value < 0:
        raise EngineAdapterInputError(f"invalid {field}")
    return value


def _parse_positive_int(raw: Any, *, field: str) -> int:
    value = _parse_nonnegative_int(raw, field=field)
    if value <= 0:
        raise EngineAdapterInputError(f"invalid {field}")
    return value


def _parse_positive_float(raw: Any, *, field: str) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise EngineAdapterInputError(f"invalid {field}") from exc
    if not math.isfinite(value) or value <= 0.0:
        raise EngineAdapterInputError(f"invalid {field}")
    return value


def _parse_point(raw: Any, *, field: str) -> list[float]:
    if isinstance(raw, list) and len(raw) == 2:
        x_raw, y_raw = raw
    elif isinstance(raw, dict):
        x_raw = raw.get("x")
        y_raw = raw.get("y")
    else:
        raise EngineAdapterInputError(f"invalid {field}")
    try:
        x = float(x_raw)
        y = float(y_raw)
    except (TypeError, ValueError) as exc:
        raise EngineAdapterInputError(f"invalid {field}") from exc
    if not math.isfinite(x) or not math.isfinite(y):
        raise EngineAdapterInputError(f"invalid {field}")
    return [x, y]


def _parse_ring(raw: Any, *, field: str) -> list[list[float]]:
    ring_raw = _require_list(raw, field=field)
    if len(ring_raw) < 3:
        raise EngineAdapterInputError(f"invalid {field}")
    return [_parse_point(point_raw, field=f"{field}[{idx}]") for idx, point_raw in enumerate(ring_raw)]


def _parse_hole_rings(raw: Any, *, field: str) -> list[list[list[float]]]:
    hole_rings_raw = _require_list(raw, field=field)
    return [_parse_ring(ring_raw, field=f"{field}[{idx}]") for idx, ring_raw in enumerate(hole_rings_raw)]


def _rotation_policy_to_allowed_degrees(solver_config: dict[str, Any]) -> list[int]:
    allow_free = bool(solver_config.get("allow_free_rotation"))
    if allow_free:
        raise EngineAdapterInputError("unsupported rotation policy: allow_free_rotation=true is not mappable to solver v1")

    step = _parse_positive_int(solver_config.get("rotation_step_deg"), field="solver_config_jsonb.rotation_step_deg")
    seen: set[int] = set()
    ordered: list[int] = []
    angle = 0
    for _ in range(360):
        if angle in seen:
            break
        seen.add(angle)
        ordered.append(angle)
        angle = (angle + step) % 360

    if not ordered:
        raise EngineAdapterInputError("unsupported rotation policy: empty rotation set")

    allowed = {0, 90, 180, 270}
    unsupported = sorted({value for value in ordered if value not in allowed})
    if unsupported:
        raise EngineAdapterInputError(
            f"unsupported rotation policy: rotation_step_deg={step} yields {unsupported}, solver v1 allows 0/90/180/270"
        )
    return sorted(set(ordered))


def _build_geometry_index(geometry_manifest: list[Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for idx, raw_item in enumerate(geometry_manifest):
        item = _require_dict(raw_item, field=f"geometry_manifest_jsonb[{idx}]")
        derivative_id = _require_non_empty_string(
            item.get("selected_nesting_derivative_id"),
            field=f"geometry_manifest_jsonb[{idx}].selected_nesting_derivative_id",
        )
        polygon = _require_dict(item.get("polygon"), field=f"geometry_manifest_jsonb[{idx}].polygon")
        bbox = _require_dict(item.get("bbox"), field=f"geometry_manifest_jsonb[{idx}].bbox")

        outer_points = _parse_ring(polygon.get("outer_ring"), field=f"geometry_manifest_jsonb[{idx}].polygon.outer_ring")
        holes_points = _parse_hole_rings(
            polygon.get("hole_rings", []),
            field=f"geometry_manifest_jsonb[{idx}].polygon.hole_rings",
        )
        width = _parse_positive_float(bbox.get("width"), field=f"geometry_manifest_jsonb[{idx}].bbox.width")
        height = _parse_positive_float(bbox.get("height"), field=f"geometry_manifest_jsonb[{idx}].bbox.height")
        out[derivative_id] = {
            "outer_points": outer_points,
            "holes_points": holes_points,
            "width": width,
            "height": height,
        }
    return out


def build_solver_input_from_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    project_manifest = _require_dict(snapshot.get("project_manifest_jsonb"), field="project_manifest_jsonb")
    parts_manifest_raw = _require_list(snapshot.get("parts_manifest_jsonb"), field="parts_manifest_jsonb")
    sheets_manifest_raw = _require_list(snapshot.get("sheets_manifest_jsonb"), field="sheets_manifest_jsonb")
    geometry_manifest_raw = _require_list(snapshot.get("geometry_manifest_jsonb"), field="geometry_manifest_jsonb")
    solver_config = _require_dict(snapshot.get("solver_config_jsonb"), field="solver_config_jsonb")

    project_name = _require_non_empty_string(project_manifest.get("project_name"), field="project_manifest_jsonb.project_name")
    seed = _parse_nonnegative_int(solver_config.get("seed", 0), field="solver_config_jsonb.seed")
    time_limit_s = _parse_positive_int(solver_config.get("time_limit_s", 60), field="solver_config_jsonb.time_limit_s")

    allowed_rotations_deg = _rotation_policy_to_allowed_degrees(solver_config)
    geometry_index = _build_geometry_index(geometry_manifest_raw)

    parts_manifest = [item for item in parts_manifest_raw if isinstance(item, dict)]
    parts_manifest.sort(
        key=lambda item: (
            int(item.get("placement_priority") or 0),
            str(item.get("part_code") or ""),
            str(item.get("part_revision_id") or ""),
            str(item.get("project_part_requirement_id") or ""),
        )
    )
    parts: list[dict[str, Any]] = []
    for idx, part in enumerate(parts_manifest):
        part_revision_id = _require_non_empty_string(part.get("part_revision_id"), field=f"parts_manifest_jsonb[{idx}].part_revision_id")
        derivative_id = _require_non_empty_string(
            part.get("selected_nesting_derivative_id"),
            field=f"parts_manifest_jsonb[{idx}].selected_nesting_derivative_id",
        )
        quantity = _parse_positive_int(part.get("required_qty"), field=f"parts_manifest_jsonb[{idx}].required_qty")
        geometry = geometry_index.get(derivative_id)
        if geometry is None:
            raise EngineAdapterInputError(f"missing geometry manifest for derivative {derivative_id}")

        parts.append(
            {
                "id": part_revision_id,
                "width": geometry["width"],
                "height": geometry["height"],
                "quantity": quantity,
                "allowed_rotations_deg": allowed_rotations_deg,
                "outer_points": geometry["outer_points"],
                "holes_points": geometry["holes_points"],
            }
        )

    if not parts:
        raise EngineAdapterInputError("parts_manifest_jsonb is empty")

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
    stocks: list[dict[str, Any]] = []
    for idx, sheet in enumerate(sheets_manifest):
        stock_id = _require_non_empty_string(
            sheet.get("sheet_revision_id") or sheet.get("project_sheet_input_id"),
            field=f"sheets_manifest_jsonb[{idx}].sheet_revision_id",
        )
        quantity = _parse_positive_int(sheet.get("required_qty"), field=f"sheets_manifest_jsonb[{idx}].required_qty")
        width = _parse_positive_float(sheet.get("width_mm"), field=f"sheets_manifest_jsonb[{idx}].width_mm")
        height = _parse_positive_float(sheet.get("height_mm"), field=f"sheets_manifest_jsonb[{idx}].height_mm")
        stocks.append(
            {
                "id": stock_id,
                "quantity": quantity,
                "width": width,
                "height": height,
                "outer_points": [[0.0, 0.0], [width, 0.0], [width, height], [0.0, height]],
                "holes_points": [],
            }
        )

    if not stocks:
        raise EngineAdapterInputError("sheets_manifest_jsonb is empty")

    return {
        "contract_version": "v1",
        "project_name": project_name,
        "seed": seed,
        "time_limit_s": time_limit_s,
        "stocks": stocks,
        "parts": parts,
    }


def solver_input_sha256(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def solver_runtime_params(payload: dict[str, Any]) -> tuple[int, int]:
    seed = _parse_nonnegative_int(payload.get("seed"), field="solver_input.seed")
    time_limit_s = _parse_positive_int(payload.get("time_limit_s"), field="solver_input.time_limit_s")
    return seed, time_limit_s
