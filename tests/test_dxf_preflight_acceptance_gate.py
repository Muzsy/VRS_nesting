#!/usr/bin/env python3
"""DXF Prefilter E2-T6 -- acceptance gate unit tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from api.services.dxf_preflight_acceptance_gate import (
    DxfPreflightAcceptanceGateError,
    evaluate_dxf_prefilter_acceptance_gate,
)
from api.services.dxf_preflight_duplicate_dedupe import dedupe_dxf_duplicate_contours
from api.services.dxf_preflight_gap_repair import repair_dxf_gaps
from api.services.dxf_preflight_inspect import inspect_dxf_source
from api.services.dxf_preflight_normalized_dxf_writer import write_normalized_dxf
from api.services.dxf_preflight_role_resolver import resolve_dxf_roles
from vrs_nesting.dxf.importer import DxfImportError

pytest.importorskip("ezdxf")

EXPECTED_TOP_LEVEL_KEYS = {
    "acceptance_outcome",
    "normalized_dxf_echo",
    "importer_probe",
    "validator_probe",
    "blocking_reasons",
    "review_required_reasons",
    "diagnostics",
}

FORBIDDEN_TOP_LEVEL_KEYS = {
    "db_insert",
    "route",
    "upload_trigger",
    "feature_flag",
}


def _write_fixture(path: Path, entities: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps({"entities": entities}), encoding="utf-8")


def _square(*, size: float = 10.0, x: float = 0.0, y: float = 0.0) -> list[list[float]]:
    return [
        [x, y],
        [x + size, y],
        [x + size, y + size],
        [x, y + size],
    ]


def _polyline_entity(*, layer: str, points: list[list[float]]) -> dict[str, Any]:
    return {
        "layer": layer,
        "type": "LWPOLYLINE",
        "closed": True,
        "points": points,
    }


def _run_t1_to_t5(
    *,
    tmp_path: Path,
    entities: list[dict[str, Any]],
    role_rules_profile: dict[str, Any] | None = None,
    gap_rules_profile: dict[str, Any] | None = None,
    dedupe_rules_profile: dict[str, Any] | None = None,
    writer_rules_profile: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    fixture_path = tmp_path / "fixture.json"
    _write_fixture(fixture_path, entities)

    inspect_result = inspect_dxf_source(fixture_path)
    role_resolution = resolve_dxf_roles(inspect_result, rules_profile=role_rules_profile)
    gap_result = repair_dxf_gaps(
        inspect_result,
        role_resolution,
        rules_profile=gap_rules_profile,
    )
    dedupe_result = dedupe_dxf_duplicate_contours(
        inspect_result,
        role_resolution,
        gap_result,
        rules_profile=dedupe_rules_profile,
    )
    normalized_result = write_normalized_dxf(
        inspect_result,
        role_resolution,
        gap_result,
        dedupe_result,
        output_path=tmp_path / "normalized" / "artifact.dxf",
        rules_profile=writer_rules_profile,
    )
    return inspect_result, role_resolution, gap_result, dedupe_result, normalized_result


def _run_t1_to_t6(
    *,
    tmp_path: Path,
    entities: list[dict[str, Any]],
    role_rules_profile: dict[str, Any] | None = None,
    gap_rules_profile: dict[str, Any] | None = None,
    dedupe_rules_profile: dict[str, Any] | None = None,
    writer_rules_profile: dict[str, Any] | None = None,
    role_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    inspect_result, role_resolution, gap_result, dedupe_result, normalized_result = _run_t1_to_t5(
        tmp_path=tmp_path,
        entities=entities,
        role_rules_profile=role_rules_profile,
        gap_rules_profile=gap_rules_profile,
        dedupe_rules_profile=dedupe_rules_profile,
        writer_rules_profile=writer_rules_profile,
    )
    role_used = role_override if role_override is not None else role_resolution
    return evaluate_dxf_prefilter_acceptance_gate(
        inspect_result,
        role_used,
        gap_result,
        dedupe_result,
        normalized_result,
    )


def _families(records: list[dict[str, Any]]) -> list[str]:
    return [str(item.get("family", "")) for item in records]


def test_t6_output_shape_and_scope_guard(tmp_path: Path) -> None:
    result = _run_t1_to_t6(
        tmp_path=tmp_path,
        entities=[_polyline_entity(layer="CUT_OUTER", points=_square())],
    )

    assert set(result.keys()) == EXPECTED_TOP_LEVEL_KEYS
    assert not (FORBIDDEN_TOP_LEVEL_KEYS & set(result.keys()))


def test_t6_accepted_for_import_clean_path(tmp_path: Path) -> None:
    result = _run_t1_to_t6(
        tmp_path=tmp_path,
        entities=[_polyline_entity(layer="CUT_OUTER", points=_square())],
    )

    assert result["acceptance_outcome"] == "accepted_for_import"
    assert result["importer_probe"]["is_pass"] is True
    assert result["validator_probe"]["status"] == "validated"
    assert result["blocking_reasons"] == []
    assert result["review_required_reasons"] == []


def test_t6_review_required_when_writer_skips_marking_entity(tmp_path: Path) -> None:
    result = _run_t1_to_t6(
        tmp_path=tmp_path,
        entities=[
            _polyline_entity(layer="CUT_OUTER", points=_square()),
            {
                "layer": "SCRIBE_LAYER",
                "type": "TEXT",
                "closed": False,
                "color_index": 2,
            },
        ],
        role_rules_profile={"marking_color_map": [2]},
    )

    assert result["importer_probe"]["is_pass"] is True
    assert result["validator_probe"]["status"] == "validated"
    assert result["acceptance_outcome"] == "preflight_review_required"
    assert "writer_skipped_source_entity" in _families(result["review_required_reasons"])


def test_t6_rejected_when_importer_probe_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def _raise_import_error(_path: str) -> Any:
        raise DxfImportError("DXF_READ_FAILED", "forced importer failure for precedence test")

    monkeypatch.setattr(
        "api.services.dxf_preflight_acceptance_gate.import_part_raw",
        _raise_import_error,
    )

    result = _run_t1_to_t6(
        tmp_path=tmp_path,
        entities=[_polyline_entity(layer="CUT_OUTER", points=_square())],
    )

    assert result["acceptance_outcome"] == "preflight_rejected"
    assert result["importer_probe"]["is_pass"] is False
    assert result["validator_probe"]["status"] == "skipped_due_to_importer_failure"
    assert "importer_probe_failed" in _families(result["blocking_reasons"])


def test_t6_rejected_when_blocking_conflict_present_even_with_review_signal(tmp_path: Path) -> None:
    inspect_result, role_resolution, gap_result, dedupe_result, normalized_result = _run_t1_to_t5(
        tmp_path=tmp_path,
        entities=[
            _polyline_entity(layer="CUT_OUTER", points=_square()),
            {
                "layer": "SCRIBE_LAYER",
                "type": "TEXT",
                "closed": False,
                "color_index": 2,
            },
        ],
        role_rules_profile={"marking_color_map": [2]},
    )

    role_override = copy.deepcopy(role_resolution)
    role_override.setdefault("blocking_conflicts", []).append(
        {
            "family": "synthetic_blocking_for_precedence_test",
            "layer": "CUT_OUTER",
        }
    )

    result = evaluate_dxf_prefilter_acceptance_gate(
        inspect_result,
        role_override,
        gap_result,
        dedupe_result,
        normalized_result,
    )

    assert result["importer_probe"]["is_pass"] is True
    assert result["validator_probe"]["status"] == "validated"
    assert result["acceptance_outcome"] == "preflight_rejected"
    assert "role_resolution_blocking_conflict" in _families(result["blocking_reasons"])
    assert "writer_skipped_source_entity" in _families(result["review_required_reasons"])


def test_t6_rejected_when_validator_probe_rejects(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def _broken_canonical_probe(*, part_raw: Any, storage_bucket: str, storage_path: str) -> dict[str, Any]:
        _ = part_raw
        _ = storage_bucket
        _ = storage_path
        return {
            "canonical_format_version": "normalized_geometry.v1",
            "canonical_geometry_jsonb": {
                "format_version": "normalized_geometry.v1",
                "units": "mm",
                "outer_ring": [[0.0, 0.0], [10.0, 0.0]],  # invalid ring (<3 points)
                "hole_rings": [],
                "bbox": {"min_x": 0.0, "min_y": 0.0, "max_x": 10.0, "max_y": 0.0, "width": 10.0, "height": 0.0},
                "normalizer_meta": {},
                "source_lineage": {},
            },
            "bbox_jsonb": {"min_x": 0.0, "min_y": 0.0, "max_x": 10.0, "max_y": 0.0, "width": 10.0, "height": 0.0},
            "canonical_hash_sha256": "deadbeef",
        }

    monkeypatch.setattr(
        "api.services.dxf_preflight_acceptance_gate.build_canonical_geometry_probe_from_part_raw",
        _broken_canonical_probe,
    )

    result = _run_t1_to_t6(
        tmp_path=tmp_path,
        entities=[_polyline_entity(layer="CUT_OUTER", points=_square())],
    )

    assert result["importer_probe"]["is_pass"] is True
    assert result["validator_probe"]["status"] == "rejected"
    assert result["acceptance_outcome"] == "preflight_rejected"
    assert "validator_probe_rejected" in _families(result["blocking_reasons"])


def test_t6_raises_on_missing_normalized_artifact_path() -> None:
    with pytest.raises(DxfPreflightAcceptanceGateError) as exc:
        evaluate_dxf_prefilter_acceptance_gate(
            {},
            {},
            {},
            {},
            {"normalized_dxf": {"output_path": ""}},
        )

    assert exc.value.code == "DXF_ACCEPTANCE_GATE_OUTPUT_PATH_MISSING"
