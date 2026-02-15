#!/usr/bin/env python3

import pytest

from vrs_nesting.project.model import ProjectValidationError, parse_project


def _minimal_project_with_rotations(rotations):
    return {
        "version": "v1",
        "name": "unit_test",
        "seed": 0,
        "time_limit_s": 60,
        "stocks": [{"id": "S1", "width": 100, "height": 100, "quantity": 1}],
        "parts": [
            {
                "id": "P1",
                "width": 10,
                "height": 5,
                "quantity": 1,
                "allowed_rotations_deg": rotations,
            }
        ],
    }


def test_parse_project_normalizes_allowed_rotations_deg():
    model = parse_project(_minimal_project_with_rotations([360, 90, 450, 0, 90]))

    assert model.parts[0].allowed_rotations_deg == [0, 90]


def test_parse_project_invalid_rotation_raises_schema_range():
    with pytest.raises(ProjectValidationError) as exc:
        parse_project(_minimal_project_with_rotations([45]))

    assert exc.value.code == "E_SCHEMA_RANGE"
