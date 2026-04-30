#!/usr/bin/env python3
"""Smoke for cavity T6 SVG/DXF export validation."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from worker.result_normalizer import normalize_solver_output_projection  # noqa: E402
from worker.sheet_dxf_artifacts import persist_sheet_dxf_artifacts  # noqa: E402
from worker.sheet_svg_artifacts import persist_sheet_svg_artifacts  # noqa: E402


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _rect(x0: float, y0: float, x1: float, y1: float) -> list[list[float]]:
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


class FakeArtifactGateway:
    def __init__(self) -> None:
        self.uploaded: dict[str, bytes] = {}
        self.registered: list[dict[str, Any]] = []

    def upload_object(self, *, bucket: str, object_key: str, payload: bytes) -> None:
        self.uploaded[f"{bucket}:{object_key}"] = bytes(payload)

    def register_artifact(
        self,
        *,
        run_id: str,
        artifact_kind: str,
        storage_bucket: str,
        storage_path: str,
        metadata_json: dict[str, Any],
    ) -> None:
        self.registered.append(
            {
                "run_id": run_id,
                "artifact_kind": artifact_kind,
                "storage_bucket": storage_bucket,
                "storage_path": storage_path,
                "metadata_json": json.loads(json.dumps(metadata_json, ensure_ascii=False, sort_keys=True)),
            }
        )


def _snapshot() -> dict[str, Any]:
    return {
        "project_manifest_jsonb": {"project_id": "project-cavity-t6", "project_name": "Cavity T6"},
        "parts_manifest_jsonb": [
            {
                "project_part_requirement_id": "req-parent",
                "part_revision_id": "parent-a",
                "part_definition_id": "part-def-parent",
                "part_code": "PARENT_A",
                "required_qty": 1,
                "placement_priority": 1,
                "selected_nesting_derivative_id": "drv-parent-a",
                "source_geometry_revision_id": "geo-parent-a",
            },
            {
                "project_part_requirement_id": "req-child",
                "part_revision_id": "child-a",
                "part_definition_id": "part-def-child",
                "part_code": "CHILD_A",
                "required_qty": 3,
                "placement_priority": 2,
                "selected_nesting_derivative_id": "drv-child-a",
                "source_geometry_revision_id": "geo-child-a",
            },
        ],
        "sheets_manifest_jsonb": [
            {
                "project_sheet_input_id": "sheet-input-1",
                "sheet_revision_id": "sheet-rev-1",
                "sheet_code": "SHEET-001",
                "required_qty": 1,
                "is_default": True,
                "placement_priority": 0,
                "width_mm": 200.0,
                "height_mm": 200.0,
            }
        ],
        "geometry_manifest_jsonb": [
            {
                "selected_nesting_derivative_id": "drv-parent-a",
                "polygon": {
                    "outer_ring": _rect(0.0, 0.0, 30.0, 20.0),
                    "hole_rings": [_rect(8.0, 4.0, 22.0, 16.0)],
                },
                "bbox": {
                    "min_x": 0.0,
                    "min_y": 0.0,
                    "max_x": 30.0,
                    "max_y": 20.0,
                    "width": 30.0,
                    "height": 20.0,
                },
            },
            {
                "selected_nesting_derivative_id": "drv-child-a",
                "polygon": {
                    "outer_ring": _rect(0.0, 0.0, 4.0, 3.0),
                    "hole_rings": [],
                },
                "bbox": {
                    "min_x": 0.0,
                    "min_y": 0.0,
                    "max_x": 4.0,
                    "max_y": 3.0,
                    "width": 4.0,
                    "height": 3.0,
                },
            },
        ],
    }


def _viewer_outline_by_geometry_revision() -> dict[str, dict[str, Any]]:
    return {
        "geo-parent-a": {
            "derivative_kind": "viewer_outline",
            "format_version": "viewer_outline.v1",
            "bbox": {"min_x": 0.0, "min_y": 0.0, "max_x": 30.0, "max_y": 20.0, "width": 30.0, "height": 20.0},
            "outline": {
                "outer_polyline": [[0.0, 0.0], [30.0, 0.0], [30.0, 20.0], [0.0, 20.0], [0.0, 0.0]],
                "hole_outlines": [
                    [[8.0, 4.0], [22.0, 4.0], [22.0, 16.0], [8.0, 16.0], [8.0, 4.0]],
                ],
            },
        },
        "geo-child-a": {
            "derivative_kind": "viewer_outline",
            "format_version": "viewer_outline.v1",
            "bbox": {"min_x": 0.0, "min_y": 0.0, "max_x": 4.0, "max_y": 3.0, "width": 4.0, "height": 3.0},
            "outline": {
                "outer_polyline": [[0.0, 0.0], [4.0, 0.0], [4.0, 3.0], [0.0, 3.0], [0.0, 0.0]],
                "hole_outlines": [],
            },
        },
    }


def _nesting_canonical_by_geometry_revision() -> dict[str, dict[str, Any]]:
    return {
        "geo-parent-a": {
            "derivative_kind": "nesting_canonical",
            "format_version": "nesting_canonical.v1",
            "bbox": {"min_x": 0.0, "min_y": 0.0, "max_x": 30.0, "max_y": 20.0, "width": 30.0, "height": 20.0},
            "placement_hints": {"origin_ref": "bbox_min_corner", "rotation_unit": "deg"},
            "polygon": {
                "outer_ring": [[0.0, 0.0], [30.0, 0.0], [30.0, 20.0], [0.0, 20.0], [0.0, 0.0]],
                "hole_rings": [
                    [[8.0, 4.0], [22.0, 4.0], [22.0, 16.0], [8.0, 16.0], [8.0, 4.0]],
                ],
            },
        },
        "geo-child-a": {
            "derivative_kind": "nesting_canonical",
            "format_version": "nesting_canonical.v1",
            "bbox": {"min_x": 0.0, "min_y": 0.0, "max_x": 4.0, "max_y": 3.0, "width": 4.0, "height": 3.0},
            "placement_hints": {"origin_ref": "bbox_min_corner", "rotation_unit": "deg"},
            "polygon": {
                "outer_ring": [[0.0, 0.0], [4.0, 0.0], [4.0, 3.0], [0.0, 3.0], [0.0, 0.0]],
                "hole_rings": [],
            },
        },
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _parse_dxf_pairs(dxf_text: str) -> list[tuple[str, str]]:
    lines = dxf_text.splitlines()
    if len(lines) % 2 != 0:
        raise RuntimeError("invalid DXF line count")
    out: list[tuple[str, str]] = []
    for idx in range(0, len(lines), 2):
        out.append((lines[idx], lines[idx + 1]))
    return out


def _count_lwpolyline_layer(pairs: list[tuple[str, str]], *, layer: str) -> int:
    count = 0
    i = 0
    while i < len(pairs):
        code, value = pairs[i]
        if code == "0" and value == "LWPOLYLINE":
            found_layer = ""
            j = i + 1
            while j < len(pairs) and pairs[j][0] != "0":
                if pairs[j][0] == "8":
                    found_layer = pairs[j][1]
                    break
                j += 1
            if found_layer == layer:
                count += 1
            i = j
            continue
        i += 1
    return count


def _run_case(tmp_root: Path) -> None:
    snapshot = _snapshot()
    run_dir = tmp_root / "run-1"
    _write_json(
        run_dir / "nesting_output.json",
        {
            "version": "nesting_engine_v2",
            "status": "partial",
            "sheets_used": 1,
            "placements": [
                {
                    "part_id": "__cavity_composite__parent-a__000000",
                    "instance": 0,
                    "sheet": 0,
                    "x_mm": 70.0,
                    "y_mm": 80.0,
                    "rotation_deg": 90.0,
                },
                {
                    "part_id": "child-a",
                    "instance": 0,
                    "sheet": 0,
                    "x_mm": 20.0,
                    "y_mm": 25.0,
                    "rotation_deg": 0.0,
                },
            ],
            "unplaced": [{"part_id": "child-a", "instance": 1, "reason": "TIME_LIMIT"}],
            "objective": {"utilization_pct": 33.0},
            "meta": {},
        },
    )
    _write_json(
        run_dir / "cavity_plan.json",
        {
            "version": "cavity_plan_v1",
            "enabled": True,
            "policy": {},
            "virtual_parts": {
                "__cavity_composite__parent-a__000000": {
                    "kind": "parent_composite",
                    "parent_part_revision_id": "parent-a",
                    "parent_instance": 0,
                    "source_geometry_revision_id": "geo-parent-a",
                    "selected_nesting_derivative_id": "drv-parent-a",
                    "internal_placements": [
                        {
                            "child_part_revision_id": "child-a",
                            "child_instance": 0,
                            "cavity_index": 0,
                            "x_local_mm": 2.0,
                            "y_local_mm": 3.0,
                            "rotation_deg": 180,
                            "placement_origin_ref": "bbox_min_corner",
                        }
                    ],
                    "cavity_diagnostics": [],
                }
            },
            "instance_bases": {"child-a": {"internal_reserved_count": 1, "top_level_instance_base": 1}},
            "quantity_delta": {"child-a": {"original_required_qty": 3, "internal_qty": 1, "top_level_qty": 2}},
            "diagnostics": [],
        },
    )

    projection = normalize_solver_output_projection(run_id="run-1", snapshot_row=snapshot, run_dir=run_dir)
    _assert(len(projection.sheets) == 1, "expected exactly one projected sheet")
    _assert(len(projection.placements) == 3, f"expected 3 placement rows, got {len(projection.placements)}")

    projection_payload = json.dumps(
        {"placements": projection.placements, "unplaced": projection.unplaced},
        ensure_ascii=False,
        sort_keys=True,
    )
    _assert("__cavity_composite__" not in projection_payload, "virtual id leaked to normalized projection")

    svg_gateway = FakeArtifactGateway()
    svg_records = persist_sheet_svg_artifacts(
        project_id="project-cavity-t6",
        run_id="run-1",
        storage_bucket="run-artifacts",
        snapshot_row=snapshot,
        projection_sheets=projection.sheets,
        projection_placements=projection.placements,
        viewer_outline_by_geometry_revision=_viewer_outline_by_geometry_revision(),
        upload_object=svg_gateway.upload_object,
        register_artifact=svg_gateway.register_artifact,
    )
    _assert(len(svg_records) == 1, "expected one SVG artifact")
    _assert(len(svg_gateway.uploaded) == 1, "expected one uploaded SVG payload")
    svg_text = next(iter(svg_gateway.uploaded.values())).decode("utf-8")
    _assert("__cavity_composite__" not in svg_text, "virtual id leaked to SVG artifact")
    _assert('data-part-revision-id="parent-a"' in svg_text, "parent path missing from SVG")
    _assert(svg_text.count('data-part-revision-id="child-a"') == 2, "child rows missing from SVG")
    parent_line = next(
        (line for line in svg_text.splitlines() if 'data-part-revision-id="parent-a"' in line),
        "",
    )
    _assert("Z M " in parent_line, "parent hole path missing from SVG parent geometry")

    dxf_gateway = FakeArtifactGateway()
    dxf_records = persist_sheet_dxf_artifacts(
        project_id="project-cavity-t6",
        run_id="run-1",
        storage_bucket="run-artifacts",
        snapshot_row=snapshot,
        projection_sheets=projection.sheets,
        projection_placements=projection.placements,
        nesting_canonical_by_geometry_revision=_nesting_canonical_by_geometry_revision(),
        upload_object=dxf_gateway.upload_object,
        register_artifact=dxf_gateway.register_artifact,
    )
    _assert(len(dxf_records) == 1, "expected one DXF artifact")
    _assert(len(dxf_gateway.uploaded) == 1, "expected one uploaded DXF payload")
    dxf_text = next(iter(dxf_gateway.uploaded.values())).decode("utf-8")
    _assert("__cavity_composite__" not in dxf_text, "virtual id leaked to DXF artifact")
    pairs = _parse_dxf_pairs(dxf_text)
    _assert(_count_lwpolyline_layer(pairs, layer="PART_HOLE") >= 1, "parent hole polyline missing in DXF")
    _assert(_count_lwpolyline_layer(pairs, layer="PART_OUTER") >= 3, "parent/child outer polylines missing in DXF")


def main() -> int:
    tmp_root = Path(tempfile.mkdtemp(prefix="smoke_cavity_t6_svg_dxf_export_validation_"))
    try:
        _run_case(tmp_root)
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
    print("[smoke_cavity_t6_svg_dxf_export_validation] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
