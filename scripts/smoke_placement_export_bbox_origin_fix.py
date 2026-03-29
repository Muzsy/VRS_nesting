#!/usr/bin/env python3
"""Smoke for placement_export_bbox_origin_fix."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import math
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from worker.result_normalizer import (  # noqa: E402
    ResultNormalizerError,
    assert_projection_within_sheet_bounds,
    normalize_solver_output_projection,
)
from worker.sheet_dxf_artifacts import persist_sheet_dxf_artifacts  # noqa: E402
from worker.sheet_svg_artifacts import persist_sheet_svg_artifacts  # noqa: E402


class FakeArtifactGateway:
    def __init__(self) -> None:
        self.uploaded: dict[str, bytes] = {}
        self.registered: list[dict[str, Any]] = []

    def upload_object(self, *, bucket: str, object_key: str, payload: bytes) -> None:
        self.uploaded[f"{bucket}:{object_key}"] = payload

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


def _assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _assert_close(label: str, actual: float, expected: float, tol: float = 1e-6) -> None:
    if not math.isclose(actual, expected, abs_tol=tol):
        raise RuntimeError(f"{label}: expected {expected}, got {actual}")


def _write_solver_output(run_dir: Path, payload: dict[str, Any]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "solver_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _snapshot() -> dict[str, Any]:
    return {
        "project_manifest_jsonb": {"project_id": "project-origin-fix"},
        "parts_manifest_jsonb": [
            {
                "project_part_requirement_id": "req-neg",
                "part_revision_id": "part-rev-neg",
                "part_definition_id": "part-def-neg",
                "part_code": "PART-NEG",
                "required_qty": 1,
                "placement_priority": 0,
                "selected_nesting_derivative_id": "deriv-neg",
                "source_geometry_revision_id": "geo-rev-neg",
            }
        ],
        "sheets_manifest_jsonb": [
            {
                "project_sheet_input_id": "sheet-in-1",
                "sheet_revision_id": "sheet-rev-1",
                "sheet_code": "SHEET-1",
                "required_qty": 1,
                "is_default": True,
                "placement_priority": 0,
                "width_mm": 100.0,
                "height_mm": 80.0,
            }
        ],
        "geometry_manifest_jsonb": [
            {
                "selected_nesting_derivative_id": "deriv-neg",
                "polygon": {
                    "outer_ring": [[-5.0, -3.0], [15.0, -3.0], [15.0, 7.0], [-5.0, 7.0]],
                    "hole_rings": [],
                },
                "bbox": {
                    "min_x": -5.0,
                    "min_y": -3.0,
                    "max_x": 15.0,
                    "max_y": 7.0,
                    "width": 20.0,
                    "height": 10.0,
                },
            }
        ],
    }


def _solver_output(*, x: float, y: float, rotation_deg: float) -> dict[str, Any]:
    return {
        "contract_version": "v1",
        "status": "ok",
        "placements": [
            {
                "instance_id": "inst-neg-1",
                "part_id": "part-rev-neg",
                "sheet_index": 0,
                "x": x,
                "y": y,
                "rotation_deg": rotation_deg,
            }
        ],
        "unplaced": [],
        "metrics": {"runtime_s": 0.1},
    }


def _viewer_outline_derivatives() -> dict[str, dict[str, Any]]:
    return {
        "geo-rev-neg": {
            "derivative_kind": "viewer_outline",
            "format_version": "viewer_outline.v1",
            "units": "mm",
            "bbox": {"min_x": -5.0, "min_y": -3.0, "max_x": 15.0, "max_y": 7.0, "width": 20.0, "height": 10.0},
            "outline": {
                "outer_polyline": [[-5.0, -3.0], [15.0, -3.0], [15.0, 7.0], [-5.0, 7.0], [-5.0, -3.0]],
                "hole_outlines": [],
            },
        }
    }


def _nesting_canonical_derivatives() -> dict[str, dict[str, Any]]:
    return {
        "geo-rev-neg": {
            "derivative_kind": "nesting_canonical",
            "format_version": "nesting_canonical.v1",
            "units": "mm",
            "bbox": {"min_x": -5.0, "min_y": -3.0, "max_x": 15.0, "max_y": 7.0, "width": 20.0, "height": 10.0},
            "placement_hints": {"origin_ref": "bbox_min_corner", "rotation_unit": "deg"},
            "polygon": {
                "outer_ring": [[-5.0, -3.0], [15.0, -3.0], [15.0, 7.0], [-5.0, 7.0], [-5.0, -3.0]],
                "hole_rings": [],
            },
        }
    }


def _extract_outer_points_from_dxf(dxf_text: str) -> list[tuple[float, float]]:
    lines = dxf_text.splitlines()
    if len(lines) % 2 != 0:
        raise RuntimeError("invalid DXF line count")

    pairs: list[tuple[str, str]] = []
    for idx in range(0, len(lines), 2):
        pairs.append((lines[idx], lines[idx + 1]))

    i = 0
    while i < len(pairs):
        code, value = pairs[i]
        if code == "0" and value == "LWPOLYLINE":
            layer = ""
            points: list[tuple[float, float]] = []
            j = i + 1
            while j < len(pairs) and pairs[j][0] != "0":
                c, v = pairs[j]
                if c == "8":
                    layer = v
                    j += 1
                    continue
                if c == "10":
                    if j + 1 >= len(pairs) or pairs[j + 1][0] != "20":
                        raise RuntimeError("invalid LWPOLYLINE vertex encoding")
                    x = float(v)
                    y = float(pairs[j + 1][1])
                    points.append((x, y))
                    j += 2
                    continue
                j += 1
            if layer == "PART_OUTER":
                return points
            i = j
            continue
        i += 1
    raise RuntimeError("PART_OUTER polyline missing in DXF")


def _normalize_points(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    normalized = {(round(x, 6), round(y, 6)) for x, y in points}
    return sorted(normalized)


def _assert_projection_and_exports(tmp: Path) -> None:
    run_id = "run-origin-fix"
    run_dir = tmp / run_id
    snapshot = _snapshot()
    _write_solver_output(run_dir, _solver_output(x=30.0, y=20.0, rotation_deg=180.0))

    projection = normalize_solver_output_projection(run_id=run_id, snapshot_row=snapshot, run_dir=run_dir)
    assert_projection_within_sheet_bounds(
        sheets=projection.sheets,
        placements=projection.placements,
    )
    _assert_true(len(projection.placements) == 1, "expected exactly one placement row")
    placement_row = projection.placements[0]
    bbox = placement_row.get("bbox_jsonb", {})
    _assert_close("bbox.min_x", float(bbox.get("min_x")), 10.0)
    _assert_close("bbox.min_y", float(bbox.get("min_y")), 10.0)
    _assert_close("bbox.max_x", float(bbox.get("max_x")), 30.0)
    _assert_close("bbox.max_y", float(bbox.get("max_y")), 20.0)
    _assert_close("bbox.width", float(bbox.get("width")), 20.0)
    _assert_close("bbox.height", float(bbox.get("height")), 10.0)

    transform = placement_row.get("transform_jsonb", {})
    _assert_close("rotation_deg passthrough", float(transform.get("rotation_deg")), 180.0)

    svg_gateway = FakeArtifactGateway()
    persist_sheet_svg_artifacts(
        project_id="project-origin-fix",
        run_id=run_id,
        storage_bucket="run-artifacts",
        snapshot_row=snapshot,
        projection_sheets=projection.sheets,
        projection_placements=projection.placements,
        viewer_outline_by_geometry_revision=_viewer_outline_derivatives(),
        upload_object=svg_gateway.upload_object,
        register_artifact=svg_gateway.register_artifact,
    )
    _assert_true(len(svg_gateway.uploaded) == 1, "expected one uploaded SVG artifact")
    svg_text = next(iter(svg_gateway.uploaded.values())).decode("utf-8")
    _assert_true('data-placement-rotation-deg="180.000000"' in svg_text, "SVG rotation metadata mismatch")
    _assert_true("M 30.000000 20.000000" in svg_text, "SVG transformed start point mismatch")
    _assert_true("L 10.000000 10.000000" in svg_text, "SVG transformed corner mismatch")

    dxf_gateway = FakeArtifactGateway()
    persist_sheet_dxf_artifacts(
        project_id="project-origin-fix",
        run_id=run_id,
        storage_bucket="run-artifacts",
        snapshot_row=snapshot,
        projection_sheets=projection.sheets,
        projection_placements=projection.placements,
        nesting_canonical_by_geometry_revision=_nesting_canonical_derivatives(),
        upload_object=dxf_gateway.upload_object,
        register_artifact=dxf_gateway.register_artifact,
    )
    _assert_true(len(dxf_gateway.uploaded) == 1, "expected one uploaded DXF artifact")
    dxf_text = next(iter(dxf_gateway.uploaded.values())).decode("utf-8")
    dxf_outer = _normalize_points(_extract_outer_points_from_dxf(dxf_text))

    expected_outer = _normalize_points([(30.0, 20.0), (10.0, 20.0), (10.0, 10.0), (30.0, 10.0)])
    _assert_true(dxf_outer == expected_outer, f"DXF transformed outer ring mismatch: {dxf_outer} != {expected_outer}")

    # SVG and DXF must describe the same sheet-space placement.
    _assert_true("30.000000 20.000000" in svg_text, "SVG reference point missing")
    _assert_true((30.0, 20.0) in _extract_outer_points_from_dxf(dxf_text), "DXF reference point missing")


def _assert_out_of_sheet_guard(tmp: Path) -> None:
    run_dir = tmp / "run-out-of-sheet"
    _write_solver_output(run_dir, _solver_output(x=90.0, y=75.0, rotation_deg=0.0))
    projection = normalize_solver_output_projection(
        run_id="run-out-of-sheet",
        snapshot_row=_snapshot(),
        run_dir=run_dir,
    )
    try:
        assert_projection_within_sheet_bounds(
            sheets=projection.sheets,
            placements=projection.placements,
        )
    except ResultNormalizerError as exc:
        _assert_true("out of sheet bounds" in str(exc), f"unexpected guard error message: {exc}")
        return
    raise RuntimeError("expected ResultNormalizerError for out-of-sheet projection")


def main() -> int:
    tmp_root = Path(tempfile.mkdtemp(prefix="smoke_placement_export_bbox_origin_fix_"))
    try:
        _assert_projection_and_exports(tmp_root)
        _assert_out_of_sheet_guard(tmp_root)
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)

    print("smoke_placement_export_bbox_origin_fix: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
