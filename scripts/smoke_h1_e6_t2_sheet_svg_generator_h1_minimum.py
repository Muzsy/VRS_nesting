#!/usr/bin/env python3
"""H1-E6-T2 smoke: sheet SVG artifact generator boundary."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from worker.sheet_svg_artifacts import (  # noqa: E402
    SheetSvgArtifactsError,
    persist_sheet_svg_artifacts,
    persisted_sheet_svg_artifacts_json,
)


class FakeArtifactGateway:
    def __init__(self) -> None:
        self.uploaded: dict[str, bytes] = {}
        self.registered: list[dict[str, Any]] = []

    def upload_object(self, *, bucket: str, object_key: str, payload: bytes) -> None:
        key = f"{bucket}:{object_key}"
        self.uploaded[key] = payload

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
        "project_manifest_jsonb": {"project_id": "project-1"},
        "parts_manifest_jsonb": [
            {
                "project_part_requirement_id": "req-a",
                "part_revision_id": "part-rev-a",
                "part_definition_id": "part-def-a",
                "part_code": "PART-A",
                "required_qty": 2,
                "placement_priority": 0,
                "source_geometry_revision_id": "geo-rev-a",
                "selected_nesting_derivative_id": "deriv-a",
            },
            {
                "project_part_requirement_id": "req-b",
                "part_revision_id": "part-rev-b",
                "part_definition_id": "part-def-b",
                "part_code": "PART-B",
                "required_qty": 1,
                "placement_priority": 10,
                "source_geometry_revision_id": "geo-rev-b",
                "selected_nesting_derivative_id": "deriv-b",
            },
        ],
    }


def _projection_sheets() -> list[dict[str, Any]]:
    return [
        {
            "sheet_index": 0,
            "sheet_revision_id": "sheet-rev-1",
            "width_mm": 100.0,
            "height_mm": 50.0,
            "utilization_ratio": 0.18,
            "metadata_jsonb": {},
        },
        {
            "sheet_index": 1,
            "sheet_revision_id": "sheet-rev-1",
            "width_mm": 100.0,
            "height_mm": 50.0,
            "utilization_ratio": 0.24,
            "metadata_jsonb": {},
        },
    ]


def _projection_placements() -> list[dict[str, Any]]:
    return [
        {
            "sheet_index": 0,
            "placement_index": 0,
            "part_revision_id": "part-rev-a",
            "quantity": 1,
            "transform_jsonb": {
                "instance_id": "inst-a1",
                "part_id": "part-rev-a",
                "sheet_index": 0,
                "x": 10.0,
                "y": 10.0,
                "rotation_deg": 0.0,
            },
            "bbox_jsonb": {},
            "metadata_jsonb": {},
        },
        {
            "sheet_index": 1,
            "placement_index": 0,
            "part_revision_id": "part-rev-a",
            "quantity": 1,
            "transform_jsonb": {
                "instance_id": "inst-a2",
                "part_id": "part-rev-a",
                "sheet_index": 1,
                "x": 20.0,
                "y": 8.0,
                "rotation_deg": 90.0,
            },
            "bbox_jsonb": {},
            "metadata_jsonb": {},
        },
        {
            "sheet_index": 1,
            "placement_index": 1,
            "part_revision_id": "part-rev-b",
            "quantity": 1,
            "transform_jsonb": {
                "instance_id": "inst-b1",
                "part_id": "part-rev-b",
                "sheet_index": 1,
                "x": 55.0,
                "y": 12.0,
                "rotation_deg": 0.0,
            },
            "bbox_jsonb": {},
            "metadata_jsonb": {},
        },
    ]


def _viewer_outline_by_geometry() -> dict[str, dict[str, Any]]:
    return {
        "geo-rev-a": {
            "derivative_kind": "viewer_outline",
            "format_version": "viewer_outline.v1",
            "outline": {
                "outer_polyline": [[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0], [0.0, 0.0]],
                "hole_outlines": [
                    [[5.0, 5.0], [15.0, 5.0], [15.0, 15.0], [5.0, 15.0], [5.0, 5.0]],
                ],
            },
        },
        "geo-rev-b": {
            "derivative_kind": "viewer_outline",
            "format_version": "viewer_outline.v1",
            "outline": {
                "outer_polyline": [[0.0, 0.0], [15.0, 0.0], [15.0, 10.0], [0.0, 10.0], [0.0, 0.0]],
                "hole_outlines": [],
            },
        },
    }


def _assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _assert_success_and_deterministic_rerun() -> None:
    snapshot = _snapshot()
    projection_sheets = _projection_sheets()
    projection_placements = _projection_placements()
    viewer_outline = _viewer_outline_by_geometry()

    first_gateway = FakeArtifactGateway()
    first = persist_sheet_svg_artifacts(
        project_id="project-1",
        run_id="run-1",
        storage_bucket="run-artifacts",
        snapshot_row=snapshot,
        projection_sheets=projection_sheets,
        projection_placements=projection_placements,
        viewer_outline_by_geometry_revision=viewer_outline,
        upload_object=first_gateway.upload_object,
        register_artifact=first_gateway.register_artifact,
    )

    _assert_true(len(first) == 2, f"expected 2 sheet SVG artifacts, got {len(first)}")

    first_json = persisted_sheet_svg_artifacts_json(first)
    second_gateway = FakeArtifactGateway()
    second = persist_sheet_svg_artifacts(
        project_id="project-1",
        run_id="run-1",
        storage_bucket="run-artifacts",
        snapshot_row=deepcopy(snapshot),
        projection_sheets=deepcopy(projection_sheets),
        projection_placements=deepcopy(projection_placements),
        viewer_outline_by_geometry_revision=deepcopy(viewer_outline),
        upload_object=second_gateway.upload_object,
        register_artifact=second_gateway.register_artifact,
    )
    second_json = persisted_sheet_svg_artifacts_json(second)
    _assert_true(first_json == second_json, "sheet SVG persisted payload is not deterministic")

    first_keys = sorted(first_gateway.uploaded.keys())
    second_keys = sorted(second_gateway.uploaded.keys())
    _assert_true(first_keys == second_keys, "uploaded storage keys differ across identical rerun")

    for key in first_keys:
        _assert_true(first_gateway.uploaded[key] == second_gateway.uploaded[key], f"uploaded payload differs for {key}")

    registered = sorted(first_gateway.registered, key=lambda item: int(item["metadata_json"]["sheet_index"]))
    _assert_true(len(registered) == 2, f"expected 2 registered records, got {len(registered)}")

    for idx, row in enumerate(registered):
        metadata = row["metadata_json"]
        expected_filename = f"out/sheet_{idx + 1:03d}.svg"
        _assert_true(row["artifact_kind"] == "sheet_svg", "artifact_kind must be sheet_svg")
        _assert_true(row["storage_bucket"] == "run-artifacts", "storage_bucket must be run-artifacts")
        _assert_true(str(metadata.get("legacy_artifact_type")) == "sheet_svg", "legacy_artifact_type mismatch")
        _assert_true(str(metadata.get("filename")) == expected_filename, "route-compatible filename mismatch")
        _assert_true(int(metadata.get("sheet_index")) == idx, "sheet_index metadata mismatch")
        _assert_true(int(metadata.get("size_bytes")) > 0, "size_bytes must be positive")
        _assert_true(len(str(metadata.get("content_sha256") or "")) == 64, "content_sha256 must be hex digest")

    sample_svg = next(iter(first_gateway.uploaded.values())).decode("utf-8")
    _assert_true('fill-rule="evenodd"' in sample_svg, "hole-compatible fill-rule is missing")
    _assert_true('viewBox="0 0 100.000000 50.000000"' in sample_svg, "sheet viewBox mismatch")
    _assert_true('data-instance-id="inst-a2"' in sample_svg or 'data-instance-id="inst-a1"' in sample_svg, "placement marker missing")


def _assert_missing_viewer_outline_error() -> None:
    viewer_outline = _viewer_outline_by_geometry()
    del viewer_outline["geo-rev-a"]

    try:
        persist_sheet_svg_artifacts(
            project_id="project-1",
            run_id="run-1",
            storage_bucket="run-artifacts",
            snapshot_row=_snapshot(),
            projection_sheets=_projection_sheets(),
            projection_placements=_projection_placements(),
            viewer_outline_by_geometry_revision=viewer_outline,
            upload_object=FakeArtifactGateway().upload_object,
            register_artifact=FakeArtifactGateway().register_artifact,
        )
    except SheetSvgArtifactsError as exc:
        _assert_true("missing viewer_outline derivative" in str(exc), "expected missing viewer_outline error")
        return
    raise RuntimeError("missing viewer_outline case did not raise SheetSvgArtifactsError")


def _assert_invalid_sheet_relation_error() -> None:
    placements = _projection_placements()
    placements[0]["sheet_index"] = 99

    try:
        persist_sheet_svg_artifacts(
            project_id="project-1",
            run_id="run-1",
            storage_bucket="run-artifacts",
            snapshot_row=_snapshot(),
            projection_sheets=_projection_sheets(),
            projection_placements=placements,
            viewer_outline_by_geometry_revision=_viewer_outline_by_geometry(),
            upload_object=FakeArtifactGateway().upload_object,
            register_artifact=FakeArtifactGateway().register_artifact,
        )
    except SheetSvgArtifactsError as exc:
        _assert_true("invalid placement sheet relation" in str(exc), "expected invalid sheet relation error")
        return
    raise RuntimeError("invalid sheet relation case did not raise SheetSvgArtifactsError")


def _assert_invalid_placement_mapping_error() -> None:
    placements = _projection_placements()
    placements[0]["transform_jsonb"]["sheet_index"] = 1

    try:
        persist_sheet_svg_artifacts(
            project_id="project-1",
            run_id="run-1",
            storage_bucket="run-artifacts",
            snapshot_row=_snapshot(),
            projection_sheets=_projection_sheets(),
            projection_placements=placements,
            viewer_outline_by_geometry_revision=_viewer_outline_by_geometry(),
            upload_object=FakeArtifactGateway().upload_object,
            register_artifact=FakeArtifactGateway().register_artifact,
        )
    except SheetSvgArtifactsError as exc:
        _assert_true("invalid placement sheet mapping" in str(exc), "expected invalid placement mapping error")
        return
    raise RuntimeError("invalid placement mapping case did not raise SheetSvgArtifactsError")


def main() -> int:
    _assert_success_and_deterministic_rerun()
    _assert_missing_viewer_outline_error()
    _assert_invalid_sheet_relation_error()
    _assert_invalid_placement_mapping_error()
    print("PASS: H1-E6-T2 sheet SVG generator smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
