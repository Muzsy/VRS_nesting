#!/usr/bin/env python3

import pytest

from vrs_nesting.nesting.instances import validate_multi_sheet_output


def _base_input_payload() -> dict:
    return {
        "contract_version": "v1",
        "project_name": "status_validation",
        "seed": 0,
        "time_limit_s": 60,
        "stocks": [{"id": "SHEET_A", "width": 100, "height": 100, "quantity": 1}],
        "parts": [{"id": "PART_A", "width": 10, "height": 10, "quantity": 1, "allowed_rotations_deg": [0]}],
    }


def test_validate_multi_sheet_output_accepts_ok_and_partial_status():
    input_payload = _base_input_payload()

    ok_output = {
        "contract_version": "v1",
        "status": "ok",
        "placements": [{"instance_id": "PART_A__0001", "part_id": "PART_A", "sheet_index": 0, "x": 0, "y": 0, "rotation_deg": 0}],
        "unplaced": [],
    }
    validate_multi_sheet_output(input_payload, ok_output)

    partial_output = {
        "contract_version": "v1",
        "status": "partial",
        "placements": [],
        "unplaced": [{"instance_id": "PART_A__0001", "part_id": "PART_A", "reason": "NO_CAPACITY"}],
    }
    validate_multi_sheet_output(input_payload, partial_output)


def test_validate_multi_sheet_output_rejects_invalid_status():
    input_payload = _base_input_payload()
    invalid_output = {
        "contract_version": "v1",
        "status": "done",
        "placements": [],
        "unplaced": [{"instance_id": "PART_A__0001", "part_id": "PART_A", "reason": "NO_CAPACITY"}],
    }

    with pytest.raises(ValueError, match="output.status must be ok or partial"):
        validate_multi_sheet_output(input_payload, invalid_output)


def test_validate_multi_sheet_output_uses_polygon_overlap_not_bbox_only():
    input_payload = {
        "contract_version": "v1",
        "project_name": "poly_overlap_precision",
        "seed": 0,
        "time_limit_s": 60,
        "stocks": [{"id": "SHEET_A", "width": 10, "height": 10, "quantity": 1}],
        "parts": [
            {
                "id": "TRI_A",
                "width": 2,
                "height": 2,
                "quantity": 1,
                "allowed_rotations_deg": [0],
                "outer_points": [[0, 0], [2, 0], [0, 2]],
            },
            {
                "id": "TRI_B",
                "width": 2,
                "height": 2,
                "quantity": 1,
                "allowed_rotations_deg": [0],
                "outer_points": [[2, 2], [0, 2], [2, 0]],
            },
        ],
    }
    output_payload = {
        "contract_version": "v1",
        "status": "ok",
        "placements": [
            {"instance_id": "TRI_A__0001", "part_id": "TRI_A", "sheet_index": 0, "x": 1, "y": 1, "rotation_deg": 0},
            {"instance_id": "TRI_B__0001", "part_id": "TRI_B", "sheet_index": 0, "x": 1, "y": 1, "rotation_deg": 0},
        ],
        "unplaced": [],
    }

    # Triangles share only a border line, area overlap is zero.
    validate_multi_sheet_output(input_payload, output_payload)


def test_validate_multi_sheet_output_rejects_spacing_violation():
    input_payload = {
        "contract_version": "v1",
        "project_name": "spacing_violation",
        "seed": 0,
        "time_limit_s": 60,
        "spacing_mm": 1.0,
        "stocks": [{"id": "SHEET_A", "width": 20, "height": 20, "quantity": 1}],
        "parts": [
            {"id": "PART_A", "width": 4, "height": 4, "quantity": 1, "allowed_rotations_deg": [0]},
            {"id": "PART_B", "width": 4, "height": 4, "quantity": 1, "allowed_rotations_deg": [0]},
        ],
    }
    output_payload = {
        "contract_version": "v1",
        "status": "ok",
        "placements": [
            {"instance_id": "PART_A__0001", "part_id": "PART_A", "sheet_index": 0, "x": 0, "y": 0, "rotation_deg": 0},
            {"instance_id": "PART_B__0001", "part_id": "PART_B", "sheet_index": 0, "x": 4.5, "y": 0, "rotation_deg": 0},
        ],
        "unplaced": [],
    }

    with pytest.raises(ValueError, match="spacing violation"):
        validate_multi_sheet_output(input_payload, output_payload)


def test_validate_multi_sheet_output_rejects_margin_violation():
    input_payload = {
        "contract_version": "v1",
        "project_name": "margin_violation",
        "seed": 0,
        "time_limit_s": 60,
        "margin_mm": 1.0,
        "stocks": [{"id": "SHEET_A", "width": 20, "height": 20, "quantity": 1}],
        "parts": [{"id": "PART_A", "width": 4, "height": 4, "quantity": 1, "allowed_rotations_deg": [0]}],
    }
    output_payload = {
        "contract_version": "v1",
        "status": "ok",
        "placements": [{"instance_id": "PART_A__0001", "part_id": "PART_A", "sheet_index": 0, "x": 0, "y": 0, "rotation_deg": 0}],
        "unplaced": [],
    }

    with pytest.raises(ValueError, match="margin violation"):
        validate_multi_sheet_output(input_payload, output_payload)
