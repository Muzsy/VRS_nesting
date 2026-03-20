#!/usr/bin/env python3
"""H1-E6-T1 smoke: result normalizer projection truth."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any
import json
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from worker.result_normalizer import (  # noqa: E402
    NormalizedProjection,
    ResultNormalizerError,
    normalize_solver_output_projection,
    normalized_projection_json,
)


class FakeProjectionGateway:
    def __init__(self) -> None:
        self.state: dict[str, dict[str, Any]] = {}

    def replace_run_projection(self, *, run_id: str, projection: NormalizedProjection) -> None:
        self.state[run_id] = json.loads(normalized_projection_json(projection))


def _write_solver_output(run_dir: Path, payload: dict[str, Any]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "solver_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_solver_output_raw(run_dir: Path, content: str) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "solver_output.json").write_text(content, encoding="utf-8")


def _base_snapshot() -> dict[str, Any]:
    return {
        "project_manifest_jsonb": {"project_id": "project-1", "project_name": "Smoke Project"},
        "parts_manifest_jsonb": [
            {
                "project_part_requirement_id": "req-a",
                "part_revision_id": "part-rev-a",
                "part_definition_id": "part-def-a",
                "part_code": "PART-A",
                "required_qty": 3,
                "placement_priority": 10,
                "selected_nesting_derivative_id": "deriv-a",
                "source_geometry_revision_id": "geo-rev-a",
            },
            {
                "project_part_requirement_id": "req-b",
                "part_revision_id": "part-rev-b",
                "part_definition_id": "part-def-b",
                "part_code": "PART-B",
                "required_qty": 3,
                "placement_priority": 20,
                "selected_nesting_derivative_id": "deriv-b",
                "source_geometry_revision_id": "geo-rev-b",
            },
        ],
        "sheets_manifest_jsonb": [
            {
                "project_sheet_input_id": "sheet-in-1",
                "sheet_revision_id": "sheet-rev-1",
                "sheet_code": "SHEET-1",
                "required_qty": 2,
                "is_default": True,
                "placement_priority": 0,
                "width_mm": 100.0,
                "height_mm": 50.0,
            }
        ],
        "geometry_manifest_jsonb": [
            {
                "selected_nesting_derivative_id": "deriv-a",
                "polygon": {
                    "outer_ring": [[0.0, 0.0], [20.0, 0.0], [20.0, 10.0], [0.0, 10.0]],
                    "hole_rings": [],
                },
                "bbox": {
                    "min_x": 0.0,
                    "min_y": 0.0,
                    "max_x": 20.0,
                    "max_y": 10.0,
                    "width": 20.0,
                    "height": 10.0,
                },
            },
            {
                "selected_nesting_derivative_id": "deriv-b",
                "polygon": {
                    "outer_ring": [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]],
                    "hole_rings": [],
                },
                "bbox": {
                    "min_x": 0.0,
                    "min_y": 0.0,
                    "max_x": 10.0,
                    "max_y": 10.0,
                    "width": 10.0,
                    "height": 10.0,
                },
            },
        ],
    }


def _snapshot_with_holes_and_multi_sheet() -> dict[str, Any]:
    return {
        "project_manifest_jsonb": {"project_id": "project-2", "project_name": "Holes+Sheets"},
        "parts_manifest_jsonb": [
            {
                "project_part_requirement_id": "req-hole",
                "part_revision_id": "part-rev-hole",
                "part_definition_id": "part-def-hole",
                "part_code": "PART-HOLE",
                "required_qty": 1,
                "placement_priority": 0,
                "selected_nesting_derivative_id": "deriv-hole",
                "source_geometry_revision_id": "geo-hole",
            }
        ],
        "sheets_manifest_jsonb": [
            {
                "project_sheet_input_id": "sheet-in-small",
                "sheet_revision_id": "sheet-rev-small",
                "sheet_code": "SHEET-S",
                "required_qty": 1,
                "is_default": True,
                "placement_priority": 0,
                "width_mm": 100.0,
                "height_mm": 50.0,
            },
            {
                "project_sheet_input_id": "sheet-in-large",
                "sheet_revision_id": "sheet-rev-large",
                "sheet_code": "SHEET-L",
                "required_qty": 1,
                "is_default": False,
                "placement_priority": 10,
                "width_mm": 200.0,
                "height_mm": 100.0,
            },
        ],
        "geometry_manifest_jsonb": [
            {
                "selected_nesting_derivative_id": "deriv-hole",
                "polygon": {
                    "outer_ring": [[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0]],
                    "hole_rings": [
                        [[5.0, 5.0], [15.0, 5.0], [15.0, 15.0], [5.0, 15.0]],
                    ],
                },
                "bbox": {
                    "min_x": 0.0,
                    "min_y": 0.0,
                    "max_x": 20.0,
                    "max_y": 20.0,
                    "width": 20.0,
                    "height": 20.0,
                },
            }
        ],
    }


def _base_solver_output() -> dict[str, Any]:
    return {
        "contract_version": "v1",
        "status": "partial",
        "placements": [
            {
                "instance_id": "inst-a1",
                "part_id": "part-rev-a",
                "sheet_index": 0,
                "x": 10.0,
                "y": 5.0,
                "rotation_deg": 0.0,
            },
            {
                "instance_id": "inst-a2",
                "part_id": "part-rev-a",
                "sheet_index": 1,
                "x": 3.0,
                "y": 4.0,
                "rotation_deg": 90.0,
            },
            {
                "instance_id": "inst-b1",
                "part_id": "part-rev-b",
                "sheet_index": 1,
                "x": 50.0,
                "y": 7.0,
                "rotation_deg": 0.0,
            },
        ],
        "unplaced": [
            {"instance_id": "inst-b2", "part_id": "part-rev-b", "reason": "PART_NEVER_FITS_STOCK"},
            {"instance_id": "inst-b3", "part_id": "part-rev-b", "reason": "PART_NEVER_FITS_STOCK"},
            {"instance_id": "inst-a3", "part_id": "part-rev-a", "reason": "TIME_LIMIT"},
        ],
        "metrics": {"runtime_s": 1.23},
    }


def _assert_close(label: str, value: float, expected: float, tol: float = 1e-6) -> None:
    if abs(value - expected) > tol:
        raise RuntimeError(f"{label}: expected {expected}, got {value}")


def _assert_success_projection(tmp: Path) -> None:
    run_id = "run-ok"
    run_dir = tmp / run_id
    snapshot = _base_snapshot()
    solver_output = _base_solver_output()
    _write_solver_output(run_dir, solver_output)

    first = normalize_solver_output_projection(run_id=run_id, snapshot_row=snapshot, run_dir=run_dir)
    second = normalize_solver_output_projection(run_id=run_id, snapshot_row=snapshot, run_dir=run_dir)
    if normalized_projection_json(first) != normalized_projection_json(second):
        raise RuntimeError("normalizer output is not deterministic on repeated run")

    if first.summary.placed_count != 3:
        raise RuntimeError(f"placed_count mismatch: {first.summary.placed_count}")
    if first.summary.unplaced_count != 3:
        raise RuntimeError(f"unplaced_count mismatch: {first.summary.unplaced_count}")
    if first.summary.used_sheet_count != 2:
        raise RuntimeError(f"used_sheet_count mismatch: {first.summary.used_sheet_count}")

    if len(first.sheets) != 2:
        raise RuntimeError(f"sheet projection row count mismatch: {len(first.sheets)}")
    if len(first.placements) != 3:
        raise RuntimeError(f"placement projection row count mismatch: {len(first.placements)}")
    if len(first.unplaced) != 2:
        raise RuntimeError(f"unplaced aggregation row count mismatch: {len(first.unplaced)}")

    run_utilization = first.metrics.get("utilization_ratio")
    _assert_close("run utilization", float(run_utilization), 0.05)

    sheet0 = next((row for row in first.sheets if int(row["sheet_index"]) == 0), None)
    sheet1 = next((row for row in first.sheets if int(row["sheet_index"]) == 1), None)
    if sheet0 is None or sheet1 is None:
        raise RuntimeError("missing sheet_index 0/1 rows")
    _assert_close("sheet0 utilization", float(sheet0["utilization_ratio"]), 0.04)
    _assert_close("sheet1 utilization", float(sheet1["utilization_ratio"]), 0.06)

    rotated = next(
        (
            row
            for row in first.placements
            if str(row.get("transform_jsonb", {}).get("instance_id") or "") == "inst-a2"
        ),
        None,
    )
    if rotated is None:
        raise RuntimeError("missing rotated placement row")
    rotated_bbox = rotated.get("bbox_jsonb", {})
    _assert_close("rotated bbox width", float(rotated_bbox.get("width") or 0.0), 10.0)
    _assert_close("rotated bbox height", float(rotated_bbox.get("height") or 0.0), 20.0)

    bucket = {(str(row["part_revision_id"]), str(row.get("reason") or "")): int(row["remaining_qty"]) for row in first.unplaced}
    if bucket.get(("part-rev-b", "PART_NEVER_FITS_STOCK")) != 2:
        raise RuntimeError("remaining_qty aggregation mismatch for part-rev-b")
    if bucket.get(("part-rev-a", "TIME_LIMIT")) != 1:
        raise RuntimeError("remaining_qty aggregation mismatch for part-rev-a")

    gateway = FakeProjectionGateway()
    gateway.replace_run_projection(run_id=run_id, projection=first)
    first_state = json.dumps(gateway.state.get(run_id), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    gateway.replace_run_projection(run_id=run_id, projection=second)
    second_state = json.dumps(gateway.state.get(run_id), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if first_state != second_state:
        raise RuntimeError("fake gateway replace is not idempotent for the same normalized payload")


def _assert_all_placed_case(tmp: Path) -> None:
    run_dir = tmp / "run-all-placed"
    payload = _base_solver_output()
    payload["unplaced"] = []
    _write_solver_output(run_dir, payload)

    projection = normalize_solver_output_projection(run_id="run-all-placed", snapshot_row=_base_snapshot(), run_dir=run_dir)
    if projection.summary.unplaced_count != 0:
        raise RuntimeError(f"all-placed should have zero unplaced_count, got {projection.summary.unplaced_count}")
    if projection.unplaced:
        raise RuntimeError("all-placed should produce empty unplaced projection rows")


def _assert_all_unplaced_case(tmp: Path) -> None:
    run_dir = tmp / "run-all-unplaced"
    payload = _base_solver_output()
    payload["placements"] = []
    _write_solver_output(run_dir, payload)

    projection = normalize_solver_output_projection(run_id="run-all-unplaced", snapshot_row=_base_snapshot(), run_dir=run_dir)
    if projection.summary.placed_count != 0:
        raise RuntimeError(f"all-unplaced should have zero placed_count, got {projection.summary.placed_count}")
    if projection.summary.used_sheet_count != 0:
        raise RuntimeError(f"all-unplaced should have zero used_sheet_count, got {projection.summary.used_sheet_count}")
    if projection.sheets:
        raise RuntimeError("all-unplaced should produce no run_layout_sheets rows")
    if projection.metrics.get("utilization_ratio") is not None:
        raise RuntimeError("all-unplaced run utilization should be null/None")


def _assert_holes_and_multi_sheet_case(tmp: Path) -> None:
    run_dir = tmp / "run-holes-multi-sheet"
    payload = {
        "contract_version": "v1",
        "status": "ok",
        "placements": [
            {
                "instance_id": "inst-hole-1",
                "part_id": "part-rev-hole",
                "sheet_index": 1,
                "x": 10.0,
                "y": 20.0,
                "rotation_deg": 0.0,
            }
        ],
        "unplaced": [],
    }
    _write_solver_output(run_dir, payload)

    projection = normalize_solver_output_projection(
        run_id="run-holes-multi-sheet",
        snapshot_row=_snapshot_with_holes_and_multi_sheet(),
        run_dir=run_dir,
    )
    if projection.summary.used_sheet_count != 1:
        raise RuntimeError(f"holes/multi-sheet case should use exactly one sheet, got {projection.summary.used_sheet_count}")
    sheet_row = projection.sheets[0]
    if str(sheet_row.get("sheet_revision_id")) != "sheet-rev-large":
        raise RuntimeError(f"sheet_index expansion mismatch, expected sheet-rev-large, got {sheet_row.get('sheet_revision_id')}")
    _assert_close("holes/multi-sheet utilization", float(sheet_row.get("utilization_ratio") or 0.0), 0.015)


def _assert_error_cases(tmp: Path) -> None:
    base_snapshot = _base_snapshot()

    invalid_part = _base_solver_output()
    invalid_part["placements"][0]["part_id"] = "missing-part"
    invalid_part_dir = tmp / "run-invalid-part"
    _write_solver_output(invalid_part_dir, invalid_part)
    try:
        normalize_solver_output_projection(run_id="run-invalid-part", snapshot_row=base_snapshot, run_dir=invalid_part_dir)
    except ResultNormalizerError as exc:
        if "unknown part_id" not in str(exc):
            raise RuntimeError(f"unexpected unknown part_id error text: {exc}") from exc
    else:
        raise RuntimeError("expected ResultNormalizerError for unknown part_id")

    invalid_sheet = _base_solver_output()
    invalid_sheet["placements"][0]["sheet_index"] = 99
    invalid_sheet_dir = tmp / "run-invalid-sheet"
    _write_solver_output(invalid_sheet_dir, invalid_sheet)
    try:
        normalize_solver_output_projection(run_id="run-invalid-sheet", snapshot_row=deepcopy(base_snapshot), run_dir=invalid_sheet_dir)
    except ResultNormalizerError as exc:
        if "invalid sheet_index" not in str(exc):
            raise RuntimeError(f"unexpected invalid sheet_index error text: {exc}") from exc
    else:
        raise RuntimeError("expected ResultNormalizerError for invalid sheet_index")

    invalid_contract = _base_solver_output()
    invalid_contract["contract_version"] = "v2"
    invalid_contract_dir = tmp / "run-invalid-contract"
    _write_solver_output(invalid_contract_dir, invalid_contract)
    try:
        normalize_solver_output_projection(run_id="run-invalid-contract", snapshot_row=base_snapshot, run_dir=invalid_contract_dir)
    except ResultNormalizerError as exc:
        if "contract_version" not in str(exc):
            raise RuntimeError(f"unexpected invalid contract error text: {exc}") from exc
    else:
        raise RuntimeError("expected ResultNormalizerError for invalid contract_version")

    malformed_dir = tmp / "run-malformed-json"
    _write_solver_output_raw(malformed_dir, "{not-json")
    try:
        normalize_solver_output_projection(run_id="run-malformed-json", snapshot_row=base_snapshot, run_dir=malformed_dir)
    except ResultNormalizerError as exc:
        if "invalid solver output json" not in str(exc):
            raise RuntimeError(f"unexpected malformed json error text: {exc}") from exc
    else:
        raise RuntimeError("expected ResultNormalizerError for malformed solver_output.json")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="smoke_h1_e6_t1_"))
    try:
        _assert_success_projection(tmp)
        _assert_all_placed_case(tmp)
        _assert_all_unplaced_case(tmp)
        _assert_holes_and_multi_sheet_case(tmp)
        _assert_error_cases(tmp)
        print("PASS: H1-E6-T1 result normalizer projection smoke")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
