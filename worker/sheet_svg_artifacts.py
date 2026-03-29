from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any, Callable
from xml.sax.saxutils import escape

from worker.result_normalizer import placement_transform_point


class SheetSvgArtifactsError(RuntimeError):
    pass


@dataclass(frozen=True)
class PersistedSheetSvgArtifact:
    sheet_index: int
    filename: str
    storage_path: str
    content_sha256: str
    size_bytes: int


UploadFn = Callable[..., None]
RegisterFn = Callable[..., None]
_POINT_CLOSE_EPS = 1e-9


def _require_dict(raw: Any, *, field: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise SheetSvgArtifactsError(f"invalid {field}")
    return raw


def _require_list(raw: Any, *, field: str) -> list[Any]:
    if not isinstance(raw, list):
        raise SheetSvgArtifactsError(f"invalid {field}")
    return raw


def _require_str(raw: Any, *, field: str) -> str:
    value = str(raw or "").strip()
    if not value:
        raise SheetSvgArtifactsError(f"invalid {field}")
    return value


def _parse_nonnegative_int(raw: Any, *, field: str) -> int:
    if isinstance(raw, bool):
        raise SheetSvgArtifactsError(f"invalid {field}")
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise SheetSvgArtifactsError(f"invalid {field}") from exc
    if value < 0:
        raise SheetSvgArtifactsError(f"invalid {field}")
    return value


def _parse_positive_float(raw: Any, *, field: str) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise SheetSvgArtifactsError(f"invalid {field}") from exc
    if not math.isfinite(value) or value <= 0.0:
        raise SheetSvgArtifactsError(f"invalid {field}")
    return value


def _parse_finite_float(raw: Any, *, field: str) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise SheetSvgArtifactsError(f"invalid {field}") from exc
    if not math.isfinite(value):
        raise SheetSvgArtifactsError(f"invalid {field}")
    return value


def _parse_point(raw: Any, *, field: str) -> tuple[float, float]:
    if not isinstance(raw, list) or len(raw) != 2:
        raise SheetSvgArtifactsError(f"invalid {field}")
    return (
        _parse_finite_float(raw[0], field=f"{field}[0]"),
        _parse_finite_float(raw[1], field=f"{field}[1]"),
    )


def _parse_ring(raw: Any, *, field: str) -> list[tuple[float, float]]:
    points = _require_list(raw, field=field)
    if len(points) < 3:
        raise SheetSvgArtifactsError(f"invalid {field}")
    ring = [_parse_point(point_raw, field=f"{field}[{idx}]") for idx, point_raw in enumerate(points)]
    if len(ring) > 3 and _points_close(ring[0], ring[-1]):
        ring = ring[:-1]
    if len(ring) < 3:
        raise SheetSvgArtifactsError(f"invalid {field}")
    return ring


def _parse_hole_rings(raw: Any, *, field: str) -> list[list[tuple[float, float]]]:
    rings = _require_list(raw, field=field)
    return [_parse_ring(ring_raw, field=f"{field}[{idx}]") for idx, ring_raw in enumerate(rings)]


def _format_num(value: float) -> str:
    return f"{float(value):.6f}"


def _points_close(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return abs(a[0] - b[0]) <= _POINT_CLOSE_EPS and abs(a[1] - b[1]) <= _POINT_CLOSE_EPS


def _escape_xml_attr(value: str) -> str:
    return escape(value, {'"': "&quot;", "'": "&apos;"})


def _path_d_from_rings(outer_ring: list[tuple[float, float]], hole_rings: list[list[tuple[float, float]]]) -> str:
    segments: list[str] = []
    all_rings = [outer_ring, *hole_rings]
    for ring in all_rings:
        if not ring:
            continue
        head_x, head_y = ring[0]
        parts = [f"M {_format_num(head_x)} {_format_num(head_y)}"]
        for x, y in ring[1:]:
            parts.append(f"L {_format_num(x)} {_format_num(y)}")
        parts.append("Z")
        segments.append(" ".join(parts))
    return " ".join(segments)


def _transform_point(x: float, y: float, *, tx: float, ty: float, rotation_deg: float) -> tuple[float, float]:
    return placement_transform_point(
        local_x=x,
        local_y=y,
        tx=tx,
        ty=ty,
        rotation_deg=rotation_deg,
    )


def _transform_ring(
    ring: list[tuple[float, float]],
    *,
    tx: float,
    ty: float,
    rotation_deg: float,
    base_x: float,
    base_y: float,
) -> list[tuple[float, float]]:
    return [
        placement_transform_point(
            local_x=x,
            local_y=y,
            tx=tx,
            ty=ty,
            rotation_deg=rotation_deg,
            base_x=base_x,
            base_y=base_y,
        )
        for x, y in ring
    ]


def _bbox_min_from_rings(
    outer_ring: list[tuple[float, float]],
    hole_rings: list[list[tuple[float, float]]],
) -> tuple[float, float]:
    points = [*outer_ring]
    for ring in hole_rings:
        points.extend(ring)
    if not points:
        raise SheetSvgArtifactsError("invalid geometry rings")
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return (min(xs), min(ys))


def _color_for_part(part_revision_id: str) -> str:
    digest = hashlib.sha256(part_revision_id.encode("utf-8")).hexdigest()
    r = 90 + (int(digest[0:2], 16) % 120)
    g = 90 + (int(digest[2:4], 16) % 120)
    b = 90 + (int(digest[4:6], 16) % 120)
    return f"#{r:02x}{g:02x}{b:02x}"


def _sheet_filename(sheet_index: int) -> str:
    return f"out/sheet_{sheet_index + 1:03d}.svg"


def _canonical_storage_path(*, project_id: str, run_id: str, content_hash: str) -> str:
    project = _require_str(project_id, field="project_id")
    run = _require_str(run_id, field="run_id")
    digest = _require_str(content_hash, field="content_hash")
    return f"projects/{project}/runs/{run}/sheet_svg/{digest}.svg"


def _part_source_geometry_index(snapshot_row: dict[str, Any]) -> dict[str, str]:
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

    out: dict[str, str] = {}
    for idx, item in enumerate(parts_manifest):
        part_revision_id = _require_str(item.get("part_revision_id"), field=f"parts_manifest_jsonb[{idx}].part_revision_id")
        source_geometry_revision_id = _require_str(
            item.get("source_geometry_revision_id"),
            field=f"parts_manifest_jsonb[{idx}].source_geometry_revision_id",
        )
        if part_revision_id in out:
            raise SheetSvgArtifactsError(f"duplicate part_revision_id in snapshot: {part_revision_id}")
        out[part_revision_id] = source_geometry_revision_id
    return out


def _viewer_outline_by_part(
    *,
    snapshot_row: dict[str, Any],
    projection_placements: list[dict[str, Any]],
    viewer_outline_by_geometry_revision: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    part_source = _part_source_geometry_index(snapshot_row)

    part_ids_used = sorted(
        {
            _require_str(item.get("part_revision_id"), field="projection_placements[].part_revision_id")
            for item in projection_placements
            if isinstance(item, dict)
        }
    )

    out: dict[str, dict[str, Any]] = {}
    for part_revision_id in part_ids_used:
        source_geometry_revision_id = part_source.get(part_revision_id)
        if source_geometry_revision_id is None:
            raise SheetSvgArtifactsError(f"missing source geometry mapping for part_revision_id: {part_revision_id}")

        derivative_payload = viewer_outline_by_geometry_revision.get(source_geometry_revision_id)
        if derivative_payload is None:
            raise SheetSvgArtifactsError(
                f"missing viewer_outline derivative for geometry_revision_id: {source_geometry_revision_id}"
            )
        derivative = _require_dict(derivative_payload, field=f"viewer_outline[{source_geometry_revision_id}]")

        derivative_kind = str(derivative.get("derivative_kind") or "").strip().lower()
        if derivative_kind and derivative_kind != "viewer_outline":
            raise SheetSvgArtifactsError(f"invalid derivative kind for geometry_revision_id: {source_geometry_revision_id}")

        outline = _require_dict(derivative.get("outline"), field=f"viewer_outline[{source_geometry_revision_id}].outline")
        outer_ring = _parse_ring(
            outline.get("outer_polyline"),
            field=f"viewer_outline[{source_geometry_revision_id}].outline.outer_polyline",
        )
        hole_rings = _parse_hole_rings(
            outline.get("hole_outlines", []),
            field=f"viewer_outline[{source_geometry_revision_id}].outline.hole_outlines",
        )
        bbox_raw = derivative.get("bbox")
        if isinstance(bbox_raw, dict):
            base_x = _parse_finite_float(
                bbox_raw.get("min_x"),
                field=f"viewer_outline[{source_geometry_revision_id}].bbox.min_x",
            )
            base_y = _parse_finite_float(
                bbox_raw.get("min_y"),
                field=f"viewer_outline[{source_geometry_revision_id}].bbox.min_y",
            )
        else:
            base_x, base_y = _bbox_min_from_rings(outer_ring, hole_rings)
        out[part_revision_id] = {
            "outer_ring": outer_ring,
            "hole_rings": hole_rings,
            "base_x": base_x,
            "base_y": base_y,
        }
    return out


def _render_sheet_svg(
    *,
    sheet: dict[str, Any],
    placements: list[dict[str, Any]],
    outline_by_part: dict[str, dict[str, Any]],
) -> str:
    sheet_index = _parse_nonnegative_int(sheet.get("sheet_index"), field="projection_sheet.sheet_index")
    width_mm = _parse_positive_float(sheet.get("width_mm"), field=f"projection_sheet[{sheet_index}].width_mm")
    height_mm = _parse_positive_float(sheet.get("height_mm"), field=f"projection_sheet[{sheet_index}].height_mm")

    ordered = [item for item in placements if isinstance(item, dict)]
    ordered.sort(
        key=lambda item: (
            _parse_nonnegative_int(item.get("placement_index"), field="projection_placements[].placement_index"),
            _require_str(item.get("part_revision_id"), field="projection_placements[].part_revision_id"),
        )
    )

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_format_num(width_mm)}mm" height="{_format_num(height_mm)}mm" viewBox="0 0 {_format_num(width_mm)} {_format_num(height_mm)}">',
        '  <rect x="0" y="0" width="100%" height="100%" fill="#f8fafc" />',
        f'  <rect x="0" y="0" width="{_format_num(width_mm)}" height="{_format_num(height_mm)}" fill="none" stroke="#0f172a" stroke-width="0.6" />',
    ]

    for item in ordered:
        part_revision_id = _require_str(item.get("part_revision_id"), field="projection_placements[].part_revision_id")
        outline = outline_by_part.get(part_revision_id)
        if outline is None:
            raise SheetSvgArtifactsError(f"missing viewer outline mapping for part_revision_id: {part_revision_id}")

        transform = _require_dict(item.get("transform_jsonb"), field="projection_placements[].transform_jsonb")
        sheet_index_in_transform = _parse_nonnegative_int(
            transform.get("sheet_index"),
            field="projection_placements[].transform_jsonb.sheet_index",
        )
        if sheet_index_in_transform != sheet_index:
            raise SheetSvgArtifactsError(
                f"invalid placement sheet mapping: placement.sheet_index={sheet_index_in_transform}, sheet={sheet_index}"
            )
        tx = _parse_finite_float(transform.get("x"), field="projection_placements[].transform_jsonb.x")
        ty = _parse_finite_float(transform.get("y"), field="projection_placements[].transform_jsonb.y")
        rotation_deg = _parse_finite_float(
            transform.get("rotation_deg"),
            field="projection_placements[].transform_jsonb.rotation_deg",
        )
        instance_id = _require_str(transform.get("instance_id"), field="projection_placements[].transform_jsonb.instance_id")
        base_x = _parse_finite_float(outline.get("base_x"), field="outline_by_part[].base_x")
        base_y = _parse_finite_float(outline.get("base_y"), field="outline_by_part[].base_y")

        transformed_outer = _transform_ring(
            outline["outer_ring"],
            tx=tx,
            ty=ty,
            rotation_deg=rotation_deg,
            base_x=base_x,
            base_y=base_y,
        )
        transformed_holes = [
            _transform_ring(
                ring,
                tx=tx,
                ty=ty,
                rotation_deg=rotation_deg,
                base_x=base_x,
                base_y=base_y,
            )
            for ring in outline["hole_rings"]
        ]
        path_d = _path_d_from_rings(transformed_outer, transformed_holes)
        fill = _color_for_part(part_revision_id)
        part_revision_id_attr = _escape_xml_attr(part_revision_id)
        instance_id_attr = _escape_xml_attr(instance_id)
        lines.append(
            f'  <path d="{path_d}" fill="{fill}" fill-opacity="0.40" stroke="#0f172a" stroke-width="0.35" fill-rule="evenodd" data-part-revision-id="{part_revision_id_attr}" data-instance-id="{instance_id_attr}" data-placement-rotation-deg="{_format_num(rotation_deg)}" />'
        )

    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def persist_sheet_svg_artifacts(
    *,
    project_id: str,
    run_id: str,
    storage_bucket: str,
    snapshot_row: dict[str, Any],
    projection_sheets: list[dict[str, Any]],
    projection_placements: list[dict[str, Any]],
    viewer_outline_by_geometry_revision: dict[str, dict[str, Any]],
    upload_object: UploadFn,
    register_artifact: RegisterFn,
) -> list[PersistedSheetSvgArtifact]:
    _require_str(storage_bucket, field="storage_bucket")
    sheets = [item for item in projection_sheets if isinstance(item, dict)]
    sheets.sort(key=lambda item: _parse_nonnegative_int(item.get("sheet_index"), field="projection_sheets[].sheet_index"))

    valid_sheet_indexes = {
        _parse_nonnegative_int(item.get("sheet_index"), field="projection_sheets[].sheet_index") for item in sheets
    }
    grouped_placements: dict[int, list[dict[str, Any]]] = {}
    for item in projection_placements:
        if not isinstance(item, dict):
            continue
        sheet_index = _parse_nonnegative_int(item.get("sheet_index"), field="projection_placements[].sheet_index")
        if sheet_index not in valid_sheet_indexes:
            raise SheetSvgArtifactsError(f"invalid placement sheet relation: {sheet_index}")
        grouped_placements.setdefault(sheet_index, []).append(item)

    outline_by_part = _viewer_outline_by_part(
        snapshot_row=snapshot_row,
        projection_placements=[item for item in projection_placements if isinstance(item, dict)],
        viewer_outline_by_geometry_revision=viewer_outline_by_geometry_revision,
    )

    persisted: list[PersistedSheetSvgArtifact] = []
    for sheet in sheets:
        sheet_index = _parse_nonnegative_int(sheet.get("sheet_index"), field="projection_sheets[].sheet_index")
        filename = _sheet_filename(sheet_index)
        payload = _render_sheet_svg(
            sheet=sheet,
            placements=grouped_placements.get(sheet_index, []),
            outline_by_part=outline_by_part,
        ).encode("utf-8")
        content_sha256 = hashlib.sha256(payload).hexdigest()
        storage_hash = hashlib.sha256(f"{filename}\n{content_sha256}".encode("utf-8")).hexdigest()
        storage_path = _canonical_storage_path(project_id=project_id, run_id=run_id, content_hash=storage_hash)
        metadata = {
            "legacy_artifact_type": "sheet_svg",
            "filename": filename,
            "size_bytes": int(len(payload)),
            "sheet_index": int(sheet_index),
            "content_sha256": content_sha256,
            "generator_scope": "h1_e6_t2",
        }

        upload_object(bucket=storage_bucket, object_key=storage_path, payload=payload)
        register_artifact(
            run_id=run_id,
            artifact_kind="sheet_svg",
            storage_bucket=storage_bucket,
            storage_path=storage_path,
            metadata_json=metadata,
        )
        persisted.append(
            PersistedSheetSvgArtifact(
                sheet_index=sheet_index,
                filename=filename,
                storage_path=storage_path,
                content_sha256=content_sha256,
                size_bytes=len(payload),
            )
        )

    persisted.sort(key=lambda item: item.sheet_index)
    return persisted


def persisted_sheet_svg_artifacts_json(records: list[PersistedSheetSvgArtifact]) -> str:
    payload = [
        {
            "sheet_index": item.sheet_index,
            "filename": item.filename,
            "storage_path": item.storage_path,
            "content_sha256": item.content_sha256,
            "size_bytes": item.size_bytes,
        }
        for item in records
    ]
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
