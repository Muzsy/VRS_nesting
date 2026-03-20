#!/usr/bin/env python3
"""H1-E6-T3 smoke: sheet DXF artifact generator boundary."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any
import json
import math
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from worker.sheet_dxf_artifacts import (  # noqa: E402
    SheetDxfArtifactsError,
    persist_sheet_dxf_artifacts,
    persisted_sheet_dxf_artifacts_json,
)


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
                "rotation_deg": 30.0,
            },
            "bbox_jsonb": {},
            "metadata_jsonb": {},
        },
    ]


def _nesting_canonical_by_geometry() -> dict[str, dict[str, Any]]:
    return {
        "geo-rev-a": {
            "derivative_kind": "nesting_canonical",
            "format_version": "nesting_canonical.v1",
            "polygon": {
                "outer_ring": [[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0], [0.0, 0.0]],
                "hole_rings": [
                    [[5.0, 5.0], [15.0, 5.0], [15.0, 15.0], [5.0, 15.0], [5.0, 5.0]],
                ],
            },
        },
        "geo-rev-b": {
            "derivative_kind": "nesting_canonical",
            "format_version": "nesting_canonical.v1",
            "polygon": {
                "outer_ring": [[0.0, 0.0], [15.0, 0.0], [15.0, 10.0], [0.0, 10.0], [0.0, 0.0]],
                "hole_rings": [],
            },
        },
    }


def _parse_dxf_pairs(dxf_text: str) -> list[tuple[str, str]]:
    lines = dxf_text.splitlines()
    if len(lines) % 2 != 0:
        raise RuntimeError("invalid DXF line count")
    out: list[tuple[str, str]] = []
    for idx in range(0, len(lines), 2):
        out.append((lines[idx], lines[idx + 1]))
    return out


def _extract_lwpolylines(pairs: list[tuple[str, str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
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
                        raise RuntimeError("invalid DXF LWPOLYLINE vertex encoding")
                    x = float(v)
                    y = float(pairs[j + 1][1])
                    points.append((x, y))
                    j += 2
                    continue
                j += 1
            out.append({"layer": layer, "points": points})
            i = j
            continue
        i += 1
    return out


def _contains_point(polylines: list[dict[str, Any]], *, layer: str, x: float, y: float, tol: float = 1e-6) -> bool:
    for polyline in polylines:
        if str(polyline.get("layer") or "") != layer:
            continue
        for px, py in polyline.get("points", []):
            if math.isclose(px, x, abs_tol=tol) and math.isclose(py, y, abs_tol=tol):
                return True
    return False


def _assert_success_and_deterministic_rerun() -> None:
    snapshot = _snapshot()
    projection_sheets = _projection_sheets()
    projection_placements = _projection_placements()
    nesting = _nesting_canonical_by_geometry()

    first_gateway = FakeArtifactGateway()
    first = persist_sheet_dxf_artifacts(
        project_id="project-1",
        run_id="run-1",
        storage_bucket="run-artifacts",
        snapshot_row=snapshot,
        projection_sheets=projection_sheets,
        projection_placements=projection_placements,
        nesting_canonical_by_geometry_revision=nesting,
        upload_object=first_gateway.upload_object,
        register_artifact=first_gateway.register_artifact,
    )

    _assert_true(len(first) == 2, f"expected 2 sheet DXF artifacts, got {len(first)}")

    first_json = persisted_sheet_dxf_artifacts_json(first)
    second_gateway = FakeArtifactGateway()
    second = persist_sheet_dxf_artifacts(
        project_id="project-1",
        run_id="run-1",
        storage_bucket="run-artifacts",
        snapshot_row=deepcopy(snapshot),
        projection_sheets=deepcopy(projection_sheets),
        projection_placements=deepcopy(projection_placements),
        nesting_canonical_by_geometry_revision=deepcopy(nesting),
        upload_object=second_gateway.upload_object,
        register_artifact=second_gateway.register_artifact,
    )
    second_json = persisted_sheet_dxf_artifacts_json(second)
    _assert_true(first_json == second_json, "sheet DXF persisted payload is not deterministic")

    first_keys = sorted(first_gateway.uploaded.keys())
    second_keys = sorted(second_gateway.uploaded.keys())
    _assert_true(first_keys == second_keys, "uploaded storage keys differ across identical rerun")
    for key in first_keys:
        _assert_true(first_gateway.uploaded[key] == second_gateway.uploaded[key], f"uploaded payload differs for {key}")

    registered = sorted(first_gateway.registered, key=lambda item: int(item["metadata_json"]["sheet_index"]))
    _assert_true(len(registered) == 2, f"expected 2 registered rows, got {len(registered)}")

    for idx, row in enumerate(registered):
        metadata = row["metadata_json"]
        expected_filename = f"out/sheet_{idx + 1:03d}.dxf"
        _assert_true(row["artifact_kind"] == "sheet_dxf", "artifact_kind must be sheet_dxf")
        _assert_true(row["storage_bucket"] == "run-artifacts", "storage_bucket must be run-artifacts")
        _assert_true(str(metadata.get("legacy_artifact_type")) == "sheet_dxf", "legacy_artifact_type mismatch")
        _assert_true(str(metadata.get("filename")) == expected_filename, "route-compatible filename mismatch")
        _assert_true(int(metadata.get("sheet_index")) == idx, "sheet_index metadata mismatch")
        _assert_true(int(metadata.get("size_bytes")) > 0, "size_bytes must be positive")
        _assert_true(len(str(metadata.get("content_sha256") or "")) == 64, "content_sha256 must be sha256")

        storage_key = f"{row['storage_bucket']}:{row['storage_path']}"
        payload = first_gateway.uploaded[storage_key].decode("utf-8")
        _assert_true("0\nSECTION\n2\nHEADER\n" in payload, "DXF HEADER section is missing")
        _assert_true("0\nSECTION\n2\nENTITIES\n" in payload, "DXF ENTITIES section is missing")
        _assert_true("0\nLWPOLYLINE\n" in payload, "DXF polyline entity is missing")

        polylines = _extract_lwpolylines(_parse_dxf_pairs(payload))
        if idx == 0:
            _assert_true(len(polylines) == 3, f"sheet 0 should have 3 polylines, got {len(polylines)}")
            _assert_true(_contains_point(polylines, layer="PART_OUTER", x=10.0, y=10.0), "sheet 0 transform point missing")
        if idx == 1:
            _assert_true(len(polylines) == 4, f"sheet 1 should have 4 polylines, got {len(polylines)}")
            _assert_true(_contains_point(polylines, layer="PART_OUTER", x=20.0, y=28.0), "sheet 1 rotated point missing")
            _assert_true(
                _contains_point(polylines, layer="PART_OUTER", x=67.990381, y=19.5),
                "sheet 1 non-orthogonal rotated point missing",
            )


def _assert_empty_sheet_case() -> None:
    placements = [item for item in _projection_placements() if int(item.get("sheet_index") or 0) == 0]

    gateway = FakeArtifactGateway()
    records = persist_sheet_dxf_artifacts(
        project_id="project-1",
        run_id="run-empty-sheet",
        storage_bucket="run-artifacts",
        snapshot_row=_snapshot(),
        projection_sheets=_projection_sheets(),
        projection_placements=placements,
        nesting_canonical_by_geometry_revision=_nesting_canonical_by_geometry(),
        upload_object=gateway.upload_object,
        register_artifact=gateway.register_artifact,
    )
    _assert_true(len(records) == 2, "all projection sheets must produce a DXF artifact")

    second = sorted(gateway.registered, key=lambda item: int(item["metadata_json"]["sheet_index"]))[1]
    payload = gateway.uploaded[f"{second['storage_bucket']}:{second['storage_path']}"]
    polylines = _extract_lwpolylines(_parse_dxf_pairs(payload.decode("utf-8")))
    _assert_true(len(polylines) == 1, "empty sheet should contain frame-only polyline")
    _assert_true(str(polylines[0].get("layer") or "") == "SHEET_FRAME", "empty sheet frame layer mismatch")


def _assert_missing_nesting_canonical_error() -> None:
    nesting = _nesting_canonical_by_geometry()
    del nesting["geo-rev-a"]

    try:
        persist_sheet_dxf_artifacts(
            project_id="project-1",
            run_id="run-1",
            storage_bucket="run-artifacts",
            snapshot_row=_snapshot(),
            projection_sheets=_projection_sheets(),
            projection_placements=_projection_placements(),
            nesting_canonical_by_geometry_revision=nesting,
            upload_object=FakeArtifactGateway().upload_object,
            register_artifact=FakeArtifactGateway().register_artifact,
        )
    except SheetDxfArtifactsError as exc:
        _assert_true("missing nesting_canonical derivative" in str(exc), "expected missing nesting_canonical error")
        return
    raise RuntimeError("missing nesting_canonical case did not raise SheetDxfArtifactsError")


def _assert_invalid_sheet_relation_error() -> None:
    placements = _projection_placements()
    placements[0]["sheet_index"] = 99

    try:
        persist_sheet_dxf_artifacts(
            project_id="project-1",
            run_id="run-1",
            storage_bucket="run-artifacts",
            snapshot_row=_snapshot(),
            projection_sheets=_projection_sheets(),
            projection_placements=placements,
            nesting_canonical_by_geometry_revision=_nesting_canonical_by_geometry(),
            upload_object=FakeArtifactGateway().upload_object,
            register_artifact=FakeArtifactGateway().register_artifact,
        )
    except SheetDxfArtifactsError as exc:
        _assert_true("invalid placement sheet relation" in str(exc), "expected invalid sheet relation error")
        return
    raise RuntimeError("invalid sheet relation case did not raise SheetDxfArtifactsError")


def _assert_invalid_placement_mapping_error() -> None:
    placements = _projection_placements()
    placements[0]["transform_jsonb"]["sheet_index"] = 1

    try:
        persist_sheet_dxf_artifacts(
            project_id="project-1",
            run_id="run-1",
            storage_bucket="run-artifacts",
            snapshot_row=_snapshot(),
            projection_sheets=_projection_sheets(),
            projection_placements=placements,
            nesting_canonical_by_geometry_revision=_nesting_canonical_by_geometry(),
            upload_object=FakeArtifactGateway().upload_object,
            register_artifact=FakeArtifactGateway().register_artifact,
        )
    except SheetDxfArtifactsError as exc:
        _assert_true("invalid placement sheet mapping" in str(exc), "expected invalid placement mapping error")
        return
    raise RuntimeError("invalid placement mapping case did not raise SheetDxfArtifactsError")


def _assert_duplicate_part_revision_error() -> None:
    snapshot = _snapshot()
    snapshot["parts_manifest_jsonb"].append(
        {
            "project_part_requirement_id": "req-dup",
            "part_revision_id": "part-rev-a",
            "part_definition_id": "part-def-a",
            "part_code": "PART-A-DUP",
            "required_qty": 1,
            "placement_priority": 99,
            "source_geometry_revision_id": "geo-rev-b",
            "selected_nesting_derivative_id": "deriv-b",
        }
    )

    try:
        persist_sheet_dxf_artifacts(
            project_id="project-1",
            run_id="run-dup",
            storage_bucket="run-artifacts",
            snapshot_row=snapshot,
            projection_sheets=_projection_sheets(),
            projection_placements=_projection_placements(),
            nesting_canonical_by_geometry_revision=_nesting_canonical_by_geometry(),
            upload_object=FakeArtifactGateway().upload_object,
            register_artifact=FakeArtifactGateway().register_artifact,
        )
    except SheetDxfArtifactsError as exc:
        _assert_true("duplicate part_revision_id in snapshot" in str(exc), "expected duplicate part_revision_id error")
        return
    raise RuntimeError("duplicate part_revision_id case did not raise SheetDxfArtifactsError")


def main() -> int:
    _assert_success_and_deterministic_rerun()
    _assert_empty_sheet_case()
    _assert_missing_nesting_canonical_error()
    _assert_invalid_sheet_relation_error()
    _assert_invalid_placement_mapping_error()
    _assert_duplicate_part_revision_error()
    print("PASS: H1-E6-T3 sheet DXF artifact generator smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
