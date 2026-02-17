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
