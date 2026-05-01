#!/usr/bin/env python3
"""DXF Prefilter E2-T5 -- normalized DXF writer backend (V1).

This module builds a local normalized DXF artifact from the existing prefilter
truth layers:

* E2-T1 inspect result,
* E2-T2 role resolution,
* E2-T3 gap repair result,
* E2-T4 duplicate dedupe result.

Scope boundary (intentional):
* cut-like world is written only from
  ``duplicate_dedupe_result["deduped_contour_working_set"]``,
* marking-like world is written from source entity replay based on T2 role
  truth,
* rules-profile surface is minimal (``canonical_layer_colors`` only),
* output is a local normalized DXF artifact on an explicit ``output_path``,
* no acceptance outcome, DB persistence, API route, upload trigger, or UI.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from vrs_nesting.dxf.importer import DxfImportError, normalize_source_entities

__all__ = [
    "DxfPreflightNormalizedDxfWriterError",
    "write_normalized_dxf",
]

_CANONICAL_CUT_ROLES: frozenset[str] = frozenset({"CUT_OUTER", "CUT_INNER"})
_CANONICAL_MARKING_ROLE = "MARKING"
_CANONICAL_LAYERS: tuple[str, str, str] = ("CUT_OUTER", "CUT_INNER", "MARKING")

_ALLOWED_RULES_PROFILE_FIELDS: frozenset[str] = frozenset({"canonical_layer_colors"})
_DEFAULT_CANONICAL_LAYER_COLORS: dict[str, int] = {
    "CUT_OUTER": 1,
    "CUT_INNER": 3,
    "MARKING": 2,
}


class DxfPreflightNormalizedDxfWriterError(RuntimeError):
    """Raised for structural misuse or unrecoverable writer-side failures."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def write_normalized_dxf(
    inspect_result: Mapping[str, Any],
    role_resolution: Mapping[str, Any],
    gap_repair_result: Mapping[str, Any],
    duplicate_dedupe_result: Mapping[str, Any],
    *,
    output_path: str | Path,
    rules_profile: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Write a local normalized DXF artifact from E2-T1..T4 truth layers."""
    _require_mapping(
        inspect_result,
        code="DXF_NORMALIZED_WRITER_INVALID_INSPECT_RESULT",
        message="inspect_result must be a mapping as produced by inspect_dxf_source().",
    )
    _require_mapping(
        role_resolution,
        code="DXF_NORMALIZED_WRITER_INVALID_ROLE_RESOLUTION",
        message="role_resolution must be a mapping as produced by resolve_dxf_roles().",
    )
    _require_mapping(
        gap_repair_result,
        code="DXF_NORMALIZED_WRITER_INVALID_GAP_REPAIR_RESULT",
        message="gap_repair_result must be a mapping as produced by repair_dxf_gaps().",
    )
    _require_mapping(
        duplicate_dedupe_result,
        code="DXF_NORMALIZED_WRITER_INVALID_DUPLICATE_DEDUPE_RESULT",
        message=(
            "duplicate_dedupe_result must be a mapping as produced by "
            "dedupe_dxf_duplicate_contours()."
        ),
    )
    if not isinstance(output_path, (str, Path)):
        raise DxfPreflightNormalizedDxfWriterError(
            "DXF_NORMALIZED_WRITER_INVALID_OUTPUT_PATH",
            "output_path must be str or Path.",
        )

    profile = _normalize_rules_profile(rules_profile if rules_profile is not None else {})
    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    source_path_str = str(inspect_result.get("source_path", "")).strip()
    if not source_path_str:
        raise DxfPreflightNormalizedDxfWriterError(
            "DXF_NORMALIZED_WRITER_SOURCE_PATH_MISSING",
            "inspect_result.source_path is required for source replay boundary.",
        )
    source_path = Path(source_path_str)
    if not source_path.is_file():
        raise DxfPreflightNormalizedDxfWriterError(
            "DXF_NORMALIZED_WRITER_SOURCE_NOT_FOUND",
            f"source_path not accessible: {source_path}",
        )

    try:
        source_entities = normalize_source_entities(source_path)
    except DxfImportError as exc:
        raise DxfPreflightNormalizedDxfWriterError(
            "DXF_NORMALIZED_WRITER_SOURCE_LOAD_FAILED",
            f"{exc.code}: {exc.message}",
        ) from exc

    ezdxf = _require_ezdxf()
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 4  # millimeters — ezdxf defaults to 6 (meters)
    msp = doc.modelspace()

    _ensure_canonical_layers(doc, profile["canonical_layer_colors"])

    cut_write = _write_cut_world(
        msp=msp,
        duplicate_dedupe_result=duplicate_dedupe_result,
        role_resolution=role_resolution,
    )
    marking_indices = _extract_marking_indices(role_resolution, source_entities)
    source_cut_entity_count = _count_source_cut_entities(role_resolution)
    marking_write = _write_marking_world(
        msp=msp,
        source_entities=source_entities,
        marking_indices=marking_indices,
    )

    doc.saveas(output)

    layer_counts = {
        "CUT_OUTER": cut_write["layer_counts"]["CUT_OUTER"],
        "CUT_INNER": cut_write["layer_counts"]["CUT_INNER"],
        "MARKING": marking_write["written_count"],
    }
    writer_layer_inventory = [
        {
            "layer": layer,
            "canonical_role": layer,
            "color_index": int(profile["canonical_layer_colors"][layer]),
            "entity_count": int(layer_counts[layer]),
            "writer_source": (
                "deduped_contour_working_set"
                if layer in _CANONICAL_CUT_ROLES
                else "source_entity_replay"
            ),
        }
        for layer in _CANONICAL_LAYERS
    ]

    written_layers = [layer for layer in _CANONICAL_LAYERS if layer_counts[layer] > 0]
    written_entity_count = sum(layer_counts.values())

    diagnostics = _build_diagnostics(
        profile=profile,
        role_resolution=role_resolution,
        gap_repair_result=gap_repair_result,
        duplicate_dedupe_result=duplicate_dedupe_result,
        cut_write=cut_write,
        marking_write=marking_write,
        source_cut_entity_count=source_cut_entity_count,
    )

    return {
        "rules_profile_echo": profile["echo"],
        "normalized_dxf": {
            "output_path": str(output),
            "writer_backend": "ezdxf",
            "written_layers": written_layers,
            "written_entity_count": int(written_entity_count),
            "cut_contour_count": int(cut_write["contour_count"]),
            "marking_entity_count": int(marking_write["written_count"]),
        },
        "writer_layer_inventory": writer_layer_inventory,
        "skipped_source_entities": marking_write["skipped_source_entities"],
        "diagnostics": diagnostics,
    }


def _require_mapping(value: Any, *, code: str, message: str) -> None:
    if not isinstance(value, Mapping):
        raise DxfPreflightNormalizedDxfWriterError(code, message)


def _normalize_rules_profile(rules_profile: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(rules_profile, Mapping):
        raise DxfPreflightNormalizedDxfWriterError(
            "DXF_NORMALIZED_WRITER_INVALID_RULES_PROFILE",
            "rules_profile must be a mapping.",
        )

    accepted: dict[str, Any] = {}
    ignored: set[str] = set()
    for key, value in rules_profile.items():
        key_str = str(key)
        if key_str in _ALLOWED_RULES_PROFILE_FIELDS:
            accepted[key_str] = value
        else:
            ignored.add(key_str)

    colors = _coerce_canonical_layer_colors(accepted.get("canonical_layer_colors"))
    echo = {
        "canonical_layer_colors": {
            "CUT_OUTER": int(colors["CUT_OUTER"]),
            "CUT_INNER": int(colors["CUT_INNER"]),
            "MARKING": int(colors["MARKING"]),
        }
    }

    return {
        "echo": echo,
        "canonical_layer_colors": colors,
        "accepted_fields": set(accepted.keys()),
        "ignored_fields": ignored,
    }


def _coerce_canonical_layer_colors(raw: Any) -> dict[str, int]:
    out: dict[str, int] = dict(_DEFAULT_CANONICAL_LAYER_COLORS)
    if raw is None:
        return out
    if not isinstance(raw, Mapping):
        raise DxfPreflightNormalizedDxfWriterError(
            "DXF_NORMALIZED_WRITER_INVALID_RULES_PROFILE",
            "canonical_layer_colors must be a mapping when provided.",
        )

    for raw_key, raw_value in raw.items():
        key = str(raw_key).strip().upper()
        if key not in _CANONICAL_LAYERS:
            continue
        if not isinstance(raw_value, int) or isinstance(raw_value, bool):
            raise DxfPreflightNormalizedDxfWriterError(
                "DXF_NORMALIZED_WRITER_INVALID_RULES_PROFILE",
                f"canonical_layer_colors[{key!r}] must be integer ACI index.",
            )
        color_index = int(raw_value)
        if color_index < 0 or color_index > 256:
            raise DxfPreflightNormalizedDxfWriterError(
                "DXF_NORMALIZED_WRITER_INVALID_RULES_PROFILE",
                f"canonical_layer_colors[{key!r}] must be in range [0, 256].",
            )
        out[key] = color_index
    return out


def _require_ezdxf() -> Any:
    try:
        import ezdxf
    except ImportError as exc:
        raise DxfPreflightNormalizedDxfWriterError(
            "DXF_NORMALIZED_WRITER_BACKEND_MISSING",
            "normalized DXF writer requires 'ezdxf' dependency.",
        ) from exc
    return ezdxf


def _ensure_canonical_layers(doc: Any, canonical_layer_colors: dict[str, int]) -> None:
    for layer in _CANONICAL_LAYERS:
        if layer in doc.layers:
            layer_record = doc.layers.get(layer)
        else:
            layer_record = doc.layers.new(name=layer)
        layer_record.dxf.color = int(canonical_layer_colors[layer])


def _write_cut_world(
    *,
    msp: Any,
    duplicate_dedupe_result: Mapping[str, Any],
    role_resolution: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    deduped_raw = duplicate_dedupe_result.get("deduped_contour_working_set")
    deduped = deduped_raw if isinstance(deduped_raw, list) else []

    layer_counts = {"CUT_OUTER": 0, "CUT_INNER": 0}
    contour_count = 0
    invalid_entries = 0

    for item in deduped:
        if not isinstance(item, Mapping):
            invalid_entries += 1
            continue
        role = str(item.get("canonical_role", "")).upper()
        if role not in _CANONICAL_CUT_ROLES:
            continue
        points = _coerce_point_tuples(item.get("points"))
        if points is None or len(points) < 3:
            invalid_entries += 1
            continue
        msp.add_lwpolyline(points, close=True, dxfattribs={"layer": role})
        layer_counts[role] += 1
        contour_count += 1

    writer_diagnostics: list[str] = []
    if layer_counts["CUT_OUTER"] == 0:
        writer_diagnostics.append("DXF_NORMALIZED_WRITER_NO_CUT_OUTER_WRITTEN")
    if layer_counts["CUT_OUTER"] > 1:
        writer_diagnostics.append("DXF_NORMALIZED_WRITER_MULTIPLE_CUT_OUTERS_WRITTEN")

    return {
        "layer_counts": layer_counts,
        "contour_count": contour_count,
        "invalid_entries": invalid_entries,
        "writer_diagnostics": writer_diagnostics,
    }


def _extract_marking_indices(
    role_resolution: Mapping[str, Any],
    source_entities: list[dict[str, Any]],
) -> list[int]:
    out: set[int] = set()
    assignments = role_resolution.get("entity_role_assignments")
    if isinstance(assignments, list):
        for item in assignments:
            if not isinstance(item, Mapping):
                continue
            role = str(item.get("canonical_role", "")).upper()
            idx = _as_int(item.get("entity_index"), default=-1)
            if role == _CANONICAL_MARKING_ROLE and 0 <= idx < len(source_entities):
                out.add(idx)

    if out:
        return sorted(out)

    # Fallback if caller omitted entity-level assignments: use layer-level role.
    layer_roles: dict[str, str] = {}
    layer_assignments = role_resolution.get("layer_role_assignments")
    if isinstance(layer_assignments, list):
        for item in layer_assignments:
            if not isinstance(item, Mapping):
                continue
            layer = str(item.get("layer", ""))
            role = str(item.get("canonical_role", "")).upper()
            if layer:
                layer_roles[layer] = role
    for idx, entity in enumerate(source_entities):
        layer = str(entity.get("layer", ""))
        if layer_roles.get(layer) == _CANONICAL_MARKING_ROLE:
            out.add(idx)
    return sorted(out)


def _count_source_cut_entities(role_resolution: Mapping[str, Any]) -> int:
    count = 0
    assignments = role_resolution.get("entity_role_assignments")
    if not isinstance(assignments, list):
        return 0
    for item in assignments:
        if not isinstance(item, Mapping):
            continue
        role = str(item.get("canonical_role", "")).upper()
        if role in _CANONICAL_CUT_ROLES:
            count += 1
    return count


def _write_marking_world(
    *,
    msp: Any,
    source_entities: list[dict[str, Any]],
    marking_indices: list[int],
) -> dict[str, Any]:
    written_count = 0
    skipped_source_entities: list[dict[str, Any]] = []

    for idx in marking_indices:
        if idx < 0 or idx >= len(source_entities):
            continue
        entity = source_entities[idx]
        write_result = _replay_marking_entity(msp, entity)
        written_count += write_result["written_count"]
        if write_result["skip_reason"] is not None:
            skipped_source_entities.append(
                {
                    "entity_index": idx,
                    "source_layer": str(entity.get("layer", "")),
                    "source_type": str(entity.get("type", "")).upper(),
                    "canonical_role": "MARKING",
                    "reason": str(write_result["skip_reason"]),
                }
            )

    return {
        "written_count": written_count,
        "skipped_source_entities": sorted(
            skipped_source_entities,
            key=lambda item: (
                int(item["entity_index"]),
                str(item["source_layer"]),
                str(item["source_type"]),
                str(item["reason"]),
            ),
        ),
    }


def _replay_marking_entity(msp: Any, entity: Mapping[str, Any]) -> dict[str, Any]:
    if bool(entity.get("_unsupported", False)):
        return {"written_count": 0, "skip_reason": "unsupported_entity_type"}

    etype = str(entity.get("type", "")).upper().strip()
    if not etype:
        return {"written_count": 0, "skip_reason": "missing_entity_type"}

    if etype == "LINE":
        points = _coerce_point_tuples(entity.get("points"))
        if points is None or len(points) < 2:
            return {"written_count": 0, "skip_reason": "line_points_invalid"}
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            msp.add_line((x1, y1, 0.0), (x2, y2, 0.0), dxfattribs={"layer": "MARKING"})
        return {"written_count": len(points) - 1, "skip_reason": None}

    if etype in {"LWPOLYLINE", "POLYLINE"}:
        points = _coerce_point_tuples(entity.get("points"))
        if points is None or len(points) < 2:
            return {"written_count": 0, "skip_reason": "polyline_points_invalid"}
        msp.add_lwpolyline(
            points,
            close=bool(entity.get("closed", False)),
            dxfattribs={"layer": "MARKING"},
        )
        return {"written_count": 1, "skip_reason": None}

    if etype == "ARC":
        center = _coerce_point(entity.get("center"))
        radius = _coerce_float(entity.get("radius"))
        start = _coerce_float(entity.get("start_angle"))
        end = _coerce_float(entity.get("end_angle"))
        if center is None or radius is None or radius <= 0.0 or start is None or end is None:
            return {"written_count": 0, "skip_reason": "arc_geometry_invalid"}
        msp.add_arc(
            (center[0], center[1], 0.0),
            radius,
            start,
            end,
            dxfattribs={"layer": "MARKING"},
        )
        return {"written_count": 1, "skip_reason": None}

    if etype == "CIRCLE":
        center = _coerce_point(entity.get("center"))
        radius = _coerce_float(entity.get("radius"))
        if center is None or radius is None or radius <= 0.0:
            return {"written_count": 0, "skip_reason": "circle_geometry_invalid"}
        msp.add_circle((center[0], center[1], 0.0), radius, dxfattribs={"layer": "MARKING"})
        return {"written_count": 1, "skip_reason": None}

    if etype == "SPLINE":
        points = _coerce_point_tuples(entity.get("points"))
        if points is None or len(points) < 2:
            return {"written_count": 0, "skip_reason": "spline_points_invalid"}
        spline = msp.add_spline(
            fit_points=[(x, y, 0.0) for x, y in points],
            dxfattribs={"layer": "MARKING"},
        )
        if bool(entity.get("closed", False)):
            spline.dxf.flags = int(getattr(spline.dxf, "flags", 0)) | 1
        return {"written_count": 1, "skip_reason": None}

    if etype == "ELLIPSE":
        center = _coerce_point(entity.get("center"))
        major_axis = _coerce_point(entity.get("major_axis"))
        ratio = _coerce_float(entity.get("ratio"))
        start_param = _coerce_float(entity.get("start_param"), default=0.0)
        end_param = _coerce_float(entity.get("end_param"), default=math.tau)
        if (
            center is not None
            and major_axis is not None
            and ratio is not None
            and ratio > 0.0
            and start_param is not None
            and end_param is not None
        ):
            msp.add_ellipse(
                center=(center[0], center[1], 0.0),
                major_axis=(major_axis[0], major_axis[1], 0.0),
                ratio=ratio,
                start_param=start_param,
                end_param=end_param,
                dxfattribs={"layer": "MARKING"},
            )
            return {"written_count": 1, "skip_reason": None}

        points = _coerce_point_tuples(entity.get("points"))
        if points is None or len(points) < 2:
            return {"written_count": 0, "skip_reason": "ellipse_geometry_invalid"}
        msp.add_lwpolyline(
            points,
            close=bool(entity.get("closed", True)),
            dxfattribs={"layer": "MARKING"},
        )
        return {"written_count": 1, "skip_reason": None}

    return {"written_count": 0, "skip_reason": "unsupported_entity_type"}


def _build_diagnostics(
    *,
    profile: dict[str, Any],
    role_resolution: Mapping[str, Any],
    gap_repair_result: Mapping[str, Any],
    duplicate_dedupe_result: Mapping[str, Any],
    cut_write: dict[str, Any],
    marking_write: dict[str, Any],
    source_cut_entity_count: int,
) -> dict[str, Any]:
    unresolved_truth = {
        "role_resolution_review_required_count": len(
            _as_dict_list(role_resolution.get("review_required_candidates"))
        ),
        "role_resolution_blocking_conflict_count": len(
            _as_dict_list(role_resolution.get("blocking_conflicts"))
        ),
        "gap_repair_remaining_open_path_count": len(
            _as_dict_list(gap_repair_result.get("remaining_open_path_candidates"))
        ),
        "gap_repair_review_required_count": len(
            _as_dict_list(gap_repair_result.get("review_required_candidates"))
        ),
        "gap_repair_blocking_conflict_count": len(
            _as_dict_list(gap_repair_result.get("blocking_conflicts"))
        ),
        "duplicate_dedupe_remaining_candidate_count": len(
            _as_dict_list(duplicate_dedupe_result.get("remaining_duplicate_candidates"))
        ),
        "duplicate_dedupe_review_required_count": len(
            _as_dict_list(duplicate_dedupe_result.get("review_required_candidates"))
        ),
        "duplicate_dedupe_blocking_conflict_count": len(
            _as_dict_list(duplicate_dedupe_result.get("blocking_conflicts"))
        ),
    }

    notes = [
        (
            "cut_writer_boundary: CUT_OUTER/CUT_INNER geometry is written only from "
            "T4 deduped_contour_working_set; source cut entities are not replayed."
        ),
        (
            "marking_writer_boundary: MARKING geometry is replayed from source "
            "entities selected by T2 role truth."
        ),
        (
            "canonical_layer_colors: deterministic defaults apply when profile "
            "does not override layer colors."
        ),
        (
            "t6_scope_boundary: unresolved review/blocking signals are surfaced as "
            "diagnostics only; this writer emits no acceptance verdict."
        ),
    ]

    return {
        "rules_profile_source_fields_accepted": sorted(profile["accepted_fields"]),
        "rules_profile_source_fields_ignored": sorted(profile["ignored_fields"]),
        "unresolved_truth": unresolved_truth,
        "source_cut_entities_not_replayed_count": int(source_cut_entity_count),
        "cut_working_set_invalid_entry_count": int(cut_write["invalid_entries"]),
        "marking_skipped_count": len(_as_dict_list(marking_write.get("skipped_source_entities"))),
        "writer_diagnostics": list(cut_write.get("writer_diagnostics", [])),
        "notes": notes,
    }


def _as_dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    out: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, Mapping):
            out.append(dict(item))
    return out


def _coerce_point(raw: Any) -> tuple[float, float] | None:
    if not isinstance(raw, (list, tuple)) or len(raw) != 2:
        return None
    x = _coerce_float(raw[0])
    y = _coerce_float(raw[1])
    if x is None or y is None:
        return None
    return (x, y)


def _coerce_point_tuples(raw: Any) -> list[tuple[float, float]] | None:
    if not isinstance(raw, list):
        return None
    out: list[tuple[float, float]] = []
    for item in raw:
        point = _coerce_point(item)
        if point is None:
            return None
        out.append(point)
    return out


def _coerce_float(raw: Any, *, default: float | None = None) -> float | None:
    if raw is None:
        return default
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    value = float(raw)
    if not math.isfinite(value):
        return None
    return value


def _as_int(raw: Any, *, default: int) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int):
        return default
    return int(raw)
