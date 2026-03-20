from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any, Callable


class SheetDxfArtifactsError(RuntimeError):
    pass


@dataclass(frozen=True)
class PersistedSheetDxfArtifact:
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
        raise SheetDxfArtifactsError(f"invalid {field}")
    return raw


def _require_list(raw: Any, *, field: str) -> list[Any]:
    if not isinstance(raw, list):
        raise SheetDxfArtifactsError(f"invalid {field}")
    return raw


def _require_str(raw: Any, *, field: str) -> str:
    value = str(raw or "").strip()
    if not value:
        raise SheetDxfArtifactsError(f"invalid {field}")
    return value


def _parse_nonnegative_int(raw: Any, *, field: str) -> int:
    if isinstance(raw, bool):
        raise SheetDxfArtifactsError(f"invalid {field}")
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise SheetDxfArtifactsError(f"invalid {field}") from exc
    if value < 0:
        raise SheetDxfArtifactsError(f"invalid {field}")
    return value


def _parse_positive_float(raw: Any, *, field: str) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise SheetDxfArtifactsError(f"invalid {field}") from exc
    if not math.isfinite(value) or value <= 0.0:
        raise SheetDxfArtifactsError(f"invalid {field}")
    return value


def _parse_finite_float(raw: Any, *, field: str) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise SheetDxfArtifactsError(f"invalid {field}") from exc
    if not math.isfinite(value):
        raise SheetDxfArtifactsError(f"invalid {field}")
    return value


def _parse_point(raw: Any, *, field: str) -> tuple[float, float]:
    if not isinstance(raw, list) or len(raw) != 2:
        raise SheetDxfArtifactsError(f"invalid {field}")
    return (
        _parse_finite_float(raw[0], field=f"{field}[0]"),
        _parse_finite_float(raw[1], field=f"{field}[1]"),
    )


def _points_close(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return abs(a[0] - b[0]) <= _POINT_CLOSE_EPS and abs(a[1] - b[1]) <= _POINT_CLOSE_EPS


def _parse_ring(raw: Any, *, field: str) -> list[tuple[float, float]]:
    points = _require_list(raw, field=field)
    if len(points) < 3:
        raise SheetDxfArtifactsError(f"invalid {field}")
    ring = [_parse_point(point_raw, field=f"{field}[{idx}]") for idx, point_raw in enumerate(points)]
    if len(ring) > 3 and _points_close(ring[0], ring[-1]):
        ring = ring[:-1]
    if len(ring) < 3:
        raise SheetDxfArtifactsError(f"invalid {field}")
    return ring


def _parse_hole_rings(raw: Any, *, field: str) -> list[list[tuple[float, float]]]:
    rings = _require_list(raw, field=field)
    return [_parse_ring(ring_raw, field=f"{field}[{idx}]") for idx, ring_raw in enumerate(rings)]


def _format_num(value: float) -> str:
    rounded = round(float(value), 6)
    if abs(rounded) < 1e-9:
        rounded = 0.0
    text = f"{rounded:.6f}".rstrip("0").rstrip(".")
    return text or "0"


def _transform_point(x: float, y: float, *, tx: float, ty: float, rotation_deg: float) -> tuple[float, float]:
    theta = math.radians(rotation_deg)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    return (x * cos_t - y * sin_t + tx, x * sin_t + y * cos_t + ty)


def _transform_ring(ring: list[tuple[float, float]], *, tx: float, ty: float, rotation_deg: float) -> list[tuple[float, float]]:
    return [_transform_point(x, y, tx=tx, ty=ty, rotation_deg=rotation_deg) for x, y in ring]


def _sheet_filename(sheet_index: int) -> str:
    return f"out/sheet_{sheet_index + 1:03d}.dxf"


def _canonical_storage_path(*, project_id: str, run_id: str, content_hash: str) -> str:
    project = _require_str(project_id, field="project_id")
    run = _require_str(run_id, field="run_id")
    digest = _require_str(content_hash, field="content_hash")
    return f"projects/{project}/runs/{run}/sheet_dxf/{digest}.dxf"


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
            raise SheetDxfArtifactsError(f"duplicate part_revision_id in snapshot: {part_revision_id}")
        out[part_revision_id] = source_geometry_revision_id
    return out


def _nesting_canonical_by_part(
    *,
    snapshot_row: dict[str, Any],
    projection_placements: list[dict[str, Any]],
    nesting_canonical_by_geometry_revision: dict[str, dict[str, Any]],
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
            raise SheetDxfArtifactsError(f"missing source geometry mapping for part_revision_id: {part_revision_id}")

        derivative_payload = nesting_canonical_by_geometry_revision.get(source_geometry_revision_id)
        if derivative_payload is None:
            raise SheetDxfArtifactsError(
                f"missing nesting_canonical derivative for geometry_revision_id: {source_geometry_revision_id}"
            )
        derivative = _require_dict(derivative_payload, field=f"nesting_canonical[{source_geometry_revision_id}]")

        derivative_kind = str(derivative.get("derivative_kind") or "").strip().lower()
        if derivative_kind and derivative_kind != "nesting_canonical":
            raise SheetDxfArtifactsError(f"invalid derivative kind for geometry_revision_id: {source_geometry_revision_id}")

        polygon = _require_dict(
            derivative.get("polygon"),
            field=f"nesting_canonical[{source_geometry_revision_id}].polygon",
        )
        outer_ring = _parse_ring(
            polygon.get("outer_ring"),
            field=f"nesting_canonical[{source_geometry_revision_id}].polygon.outer_ring",
        )
        hole_rings = _parse_hole_rings(
            polygon.get("hole_rings", []),
            field=f"nesting_canonical[{source_geometry_revision_id}].polygon.hole_rings",
        )
        out[part_revision_id] = {
            "outer_ring": outer_ring,
            "hole_rings": hole_rings,
        }
    return out


def _append_pair(pairs: list[tuple[str, str]], code: int | str, value: int | float | str) -> None:
    pairs.append((str(code), str(value)))


def _append_lwpolyline(
    pairs: list[tuple[str, str]],
    *,
    handle: str,
    owner_handle: str,
    layer: str,
    ring: list[tuple[float, float]],
) -> None:
    if len(ring) < 3:
        raise SheetDxfArtifactsError("invalid lwpolyline ring")
    _append_pair(pairs, 0, "LWPOLYLINE")
    _append_pair(pairs, 5, handle)
    _append_pair(pairs, 330, owner_handle)
    _append_pair(pairs, 100, "AcDbEntity")
    _append_pair(pairs, 8, layer)
    _append_pair(pairs, 100, "AcDbPolyline")
    _append_pair(pairs, 90, len(ring))
    _append_pair(pairs, 70, 1)
    for x, y in ring:
        _append_pair(pairs, 10, _format_num(x))
        _append_pair(pairs, 20, _format_num(y))


def _next_handle(counter: list[int]) -> str:
    value = counter[0]
    counter[0] += 1
    return format(value, "X")


def _pairs_to_dxf_text(pairs: list[tuple[str, str]]) -> str:
    lines: list[str] = []
    for code, value in pairs:
        lines.append(code)
        lines.append(value)
    return "\n".join(lines) + "\n"


def _render_sheet_dxf(
    *,
    sheet: dict[str, Any],
    placements: list[dict[str, Any]],
    geometry_by_part: dict[str, dict[str, Any]],
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

    pairs: list[tuple[str, str]] = []
    handle_counter = [0x10]
    root_owner_handle = "0"

    _append_pair(pairs, 0, "SECTION")
    _append_pair(pairs, 2, "HEADER")
    _append_pair(pairs, 9, "$ACADVER")
    _append_pair(pairs, 1, "AC1015")
    _append_pair(pairs, 9, "$INSUNITS")
    _append_pair(pairs, 70, 4)
    _append_pair(pairs, 9, "$MEASUREMENT")
    _append_pair(pairs, 70, 1)
    _append_pair(pairs, 9, "$EXTMIN")
    _append_pair(pairs, 10, _format_num(0.0))
    _append_pair(pairs, 20, _format_num(0.0))
    _append_pair(pairs, 9, "$EXTMAX")
    _append_pair(pairs, 10, _format_num(width_mm))
    _append_pair(pairs, 20, _format_num(height_mm))
    _append_pair(pairs, 9, "$LIMMIN")
    _append_pair(pairs, 10, _format_num(0.0))
    _append_pair(pairs, 20, _format_num(0.0))
    _append_pair(pairs, 9, "$LIMMAX")
    _append_pair(pairs, 10, _format_num(width_mm))
    _append_pair(pairs, 20, _format_num(height_mm))
    _append_pair(pairs, 0, "ENDSEC")

    _append_pair(pairs, 0, "SECTION")
    _append_pair(pairs, 2, "TABLES")
    layer_table_handle = _next_handle(handle_counter)
    _append_pair(pairs, 0, "TABLE")
    _append_pair(pairs, 5, layer_table_handle)
    _append_pair(pairs, 330, root_owner_handle)
    _append_pair(pairs, 100, "AcDbSymbolTable")
    _append_pair(pairs, 2, "LAYER")
    _append_pair(pairs, 70, 3)
    for layer_name, color in (("SHEET_FRAME", 7), ("PART_OUTER", 3), ("PART_HOLE", 1)):
        layer_handle = _next_handle(handle_counter)
        _append_pair(pairs, 0, "LAYER")
        _append_pair(pairs, 5, layer_handle)
        _append_pair(pairs, 330, layer_table_handle)
        _append_pair(pairs, 100, "AcDbSymbolTableRecord")
        _append_pair(pairs, 100, "AcDbLayerTableRecord")
        _append_pair(pairs, 2, layer_name)
        _append_pair(pairs, 70, 0)
        _append_pair(pairs, 62, color)
        _append_pair(pairs, 6, "CONTINUOUS")
    _append_pair(pairs, 0, "ENDTAB")
    _append_pair(pairs, 0, "ENDSEC")

    _append_pair(pairs, 0, "SECTION")
    _append_pair(pairs, 2, "ENTITIES")

    frame_ring = [(0.0, 0.0), (width_mm, 0.0), (width_mm, height_mm), (0.0, height_mm)]
    _append_lwpolyline(
        pairs,
        handle=_next_handle(handle_counter),
        owner_handle=root_owner_handle,
        layer="SHEET_FRAME",
        ring=frame_ring,
    )

    for item in ordered:
        part_revision_id = _require_str(item.get("part_revision_id"), field="projection_placements[].part_revision_id")
        geometry = geometry_by_part.get(part_revision_id)
        if geometry is None:
            raise SheetDxfArtifactsError(f"missing geometry mapping for part_revision_id: {part_revision_id}")

        transform = _require_dict(item.get("transform_jsonb"), field="projection_placements[].transform_jsonb")
        sheet_index_in_transform = _parse_nonnegative_int(
            transform.get("sheet_index"),
            field="projection_placements[].transform_jsonb.sheet_index",
        )
        if sheet_index_in_transform != sheet_index:
            raise SheetDxfArtifactsError(
                f"invalid placement sheet mapping: placement.sheet_index={sheet_index_in_transform}, sheet={sheet_index}"
            )
        tx = _parse_finite_float(transform.get("x"), field="projection_placements[].transform_jsonb.x")
        ty = _parse_finite_float(transform.get("y"), field="projection_placements[].transform_jsonb.y")
        rotation_deg = _parse_finite_float(
            transform.get("rotation_deg"),
            field="projection_placements[].transform_jsonb.rotation_deg",
        )

        transformed_outer = _transform_ring(geometry["outer_ring"], tx=tx, ty=ty, rotation_deg=rotation_deg)
        _append_lwpolyline(
            pairs,
            handle=_next_handle(handle_counter),
            owner_handle=root_owner_handle,
            layer="PART_OUTER",
            ring=transformed_outer,
        )
        for hole_ring in geometry["hole_rings"]:
            transformed_hole = _transform_ring(hole_ring, tx=tx, ty=ty, rotation_deg=rotation_deg)
            _append_lwpolyline(
                pairs,
                handle=_next_handle(handle_counter),
                owner_handle=root_owner_handle,
                layer="PART_HOLE",
                ring=transformed_hole,
            )

    _append_pair(pairs, 0, "ENDSEC")
    _append_pair(pairs, 0, "EOF")

    return _pairs_to_dxf_text(pairs)


def persist_sheet_dxf_artifacts(
    *,
    project_id: str,
    run_id: str,
    storage_bucket: str,
    snapshot_row: dict[str, Any],
    projection_sheets: list[dict[str, Any]],
    projection_placements: list[dict[str, Any]],
    nesting_canonical_by_geometry_revision: dict[str, dict[str, Any]],
    upload_object: UploadFn,
    register_artifact: RegisterFn,
) -> list[PersistedSheetDxfArtifact]:
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
            raise SheetDxfArtifactsError(f"invalid placement sheet relation: {sheet_index}")
        grouped_placements.setdefault(sheet_index, []).append(item)

    geometry_by_part = _nesting_canonical_by_part(
        snapshot_row=snapshot_row,
        projection_placements=[item for item in projection_placements if isinstance(item, dict)],
        nesting_canonical_by_geometry_revision=nesting_canonical_by_geometry_revision,
    )

    persisted: list[PersistedSheetDxfArtifact] = []
    for sheet in sheets:
        sheet_index = _parse_nonnegative_int(sheet.get("sheet_index"), field="projection_sheets[].sheet_index")
        filename = _sheet_filename(sheet_index)
        payload = _render_sheet_dxf(
            sheet=sheet,
            placements=grouped_placements.get(sheet_index, []),
            geometry_by_part=geometry_by_part,
        ).encode("utf-8")
        content_sha256 = hashlib.sha256(payload).hexdigest()
        storage_hash_input = "\n".join([project_id, run_id, filename, content_sha256])
        storage_hash = hashlib.sha256(storage_hash_input.encode("utf-8")).hexdigest()
        storage_path = _canonical_storage_path(project_id=project_id, run_id=run_id, content_hash=storage_hash)
        metadata = {
            "legacy_artifact_type": "sheet_dxf",
            "filename": filename,
            "size_bytes": int(len(payload)),
            "sheet_index": int(sheet_index),
            "content_sha256": content_sha256,
            "generator_scope": "h1_e6_t3",
        }

        upload_object(bucket=storage_bucket, object_key=storage_path, payload=payload)
        register_artifact(
            run_id=run_id,
            artifact_kind="sheet_dxf",
            storage_bucket=storage_bucket,
            storage_path=storage_path,
            metadata_json=metadata,
        )
        persisted.append(
            PersistedSheetDxfArtifact(
                sheet_index=sheet_index,
                filename=filename,
                storage_path=storage_path,
                content_sha256=content_sha256,
                size_bytes=len(payload),
            )
        )

    persisted.sort(key=lambda item: item.sheet_index)
    return persisted


def persisted_sheet_dxf_artifacts_json(records: list[PersistedSheetDxfArtifact]) -> str:
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
