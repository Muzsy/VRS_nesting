#!/usr/bin/env python3
"""DXF Prefilter E2-T5 -- normalized DXF writer unit tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from api.services.dxf_preflight_duplicate_dedupe import dedupe_dxf_duplicate_contours
from api.services.dxf_preflight_gap_repair import repair_dxf_gaps
from api.services.dxf_preflight_inspect import inspect_dxf_source
from api.services.dxf_preflight_normalized_dxf_writer import write_normalized_dxf
from api.services.dxf_preflight_role_resolver import resolve_dxf_roles

pytest.importorskip("ezdxf")

EXPECTED_TOP_LEVEL_KEYS = {
    "rules_profile_echo",
    "normalized_dxf",
    "writer_layer_inventory",
    "skipped_source_entities",
    "diagnostics",
}

FORBIDDEN_TOP_LEVEL_KEYS = {
    "accepted_for_import",
    "preflight_rejected",
    "acceptance",
    "acceptance_outcome",
    "db_insert",
    "route",
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


def _run_chain(
    *,
    tmp_path: Path,
    entities: list[dict[str, Any]],
    role_rules_profile: dict[str, Any] | None = None,
    gap_rules_profile: dict[str, Any] | None = None,
    dedupe_rules_profile: dict[str, Any] | None = None,
    writer_rules_profile: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], Path]:
    fixture_path = tmp_path / "fixture.json"
    _write_fixture(fixture_path, entities)

    inspect_result = inspect_dxf_source(fixture_path)
    role_resolution = resolve_dxf_roles(
        inspect_result,
        rules_profile=role_rules_profile,
    )
    gap_repair_result = repair_dxf_gaps(
        inspect_result,
        role_resolution,
        rules_profile=gap_rules_profile,
    )
    dedupe_result = dedupe_dxf_duplicate_contours(
        inspect_result,
        role_resolution,
        gap_repair_result,
        rules_profile=dedupe_rules_profile,
    )

    output_path = tmp_path / "normalized" / "normalized.dxf"
    result = write_normalized_dxf(
        inspect_result,
        role_resolution,
        gap_repair_result,
        dedupe_result,
        output_path=output_path,
        rules_profile=writer_rules_profile,
    )
    return result, role_resolution, gap_repair_result, dedupe_result, output_path


def _read_doc(path: Path) -> Any:
    import ezdxf

    return ezdxf.readfile(path)


def _modelspace_by_layer(doc: Any, layer: str) -> list[Any]:
    return [entity for entity in doc.modelspace() if str(entity.dxf.layer) == layer]


def test_t5_output_shape_and_scope_guard(tmp_path: Path) -> None:
    entities = [_polyline_entity(layer="CUT_OUTER", points=_square())]
    result, _role, _gap, _dedupe, _output_path = _run_chain(
        tmp_path=tmp_path,
        entities=entities,
    )

    assert set(result.keys()) == EXPECTED_TOP_LEVEL_KEYS
    assert not FORBIDDEN_TOP_LEVEL_KEYS & set(result.keys())


def test_t5_rules_profile_echo_uses_only_canonical_layer_colors(tmp_path: Path) -> None:
    entities = [
        _polyline_entity(layer="CUT_OUTER", points=_square()),
        {
            "layer": "ETCH_A",
            "type": "LINE",
            "points": [[0.0, 0.0], [5.0, 5.0]],
            "color_index": 2,
        },
    ]

    result, _role, _gap, _dedupe, output_path = _run_chain(
        tmp_path=tmp_path,
        entities=entities,
        role_rules_profile={"marking_color_map": [2]},
        writer_rules_profile={
            "canonical_layer_colors": {"CUT_OUTER": 11, "CUT_INNER": 5, "MARKING": 6},
            "strict_mode": True,
        },
    )

    assert set(result["rules_profile_echo"].keys()) == {"canonical_layer_colors"}
    assert result["rules_profile_echo"]["canonical_layer_colors"] == {
        "CUT_OUTER": 11,
        "CUT_INNER": 5,
        "MARKING": 6,
    }
    ignored = set(result["diagnostics"]["rules_profile_source_fields_ignored"])
    assert "strict_mode" in ignored

    doc = _read_doc(output_path)
    assert int(doc.layers.get("CUT_OUTER").dxf.color) == 11
    assert int(doc.layers.get("CUT_INNER").dxf.color) == 5
    assert int(doc.layers.get("MARKING").dxf.color) == 6


def test_t5_cut_world_comes_from_t4_deduped_working_set(tmp_path: Path) -> None:
    entities = [
        _polyline_entity(layer="CUT_OUTER", points=_square()),
        _polyline_entity(layer="CUT_OUTER", points=_square()),  # duplicate
        {"layer": "CUT_OUTER", "type": "LINE", "points": [[0.0, 0.0], [50.0, 0.0]]},  # open cut
        {
            "layer": "ETCH_B",
            "type": "LINE",
            "points": [[2.0, 2.0], [8.0, 2.0]],
            "color_index": 2,
        },
    ]

    result, _role, _gap, dedupe, output_path = _run_chain(
        tmp_path=tmp_path,
        entities=entities,
        role_rules_profile={"marking_color_map": [2]},
        dedupe_rules_profile={
            "auto_repair_enabled": True,
            "duplicate_contour_merge_tolerance_mm": 0.05,
        },
    )

    assert len(dedupe["deduped_contour_working_set"]) == 1
    assert result["normalized_dxf"]["cut_contour_count"] == 1

    doc = _read_doc(output_path)
    cut_outer_entities = _modelspace_by_layer(doc, "CUT_OUTER")
    cut_outer_types = [str(entity.dxftype()).upper() for entity in cut_outer_entities]
    assert cut_outer_types.count("LWPOLYLINE") == 1
    assert "LINE" not in cut_outer_types

    assert result["diagnostics"]["source_cut_entities_not_replayed_count"] >= 2


def test_t5_marking_replay_and_structured_skip(tmp_path: Path) -> None:
    entities = [
        _polyline_entity(layer="CUT_OUTER", points=_square()),
        {
            "layer": "SCRIBE_LAYER",
            "type": "LINE",
            "points": [[1.0, 1.0], [9.0, 1.0]],
            "color_index": 2,
        },
        {
            "layer": "SCRIBE_LAYER",
            "type": "TEXT",
            "closed": False,
            "color_index": 2,
        },
    ]

    result, _role, _gap, _dedupe, output_path = _run_chain(
        tmp_path=tmp_path,
        entities=entities,
        role_rules_profile={"marking_color_map": [2]},
    )

    assert result["normalized_dxf"]["marking_entity_count"] == 1
    skipped = result["skipped_source_entities"]
    assert len(skipped) == 1
    assert skipped[0]["source_type"] == "TEXT"
    assert skipped[0]["reason"] == "unsupported_entity_type"

    doc = _read_doc(output_path)
    marking_entities = _modelspace_by_layer(doc, "MARKING")
    assert len(marking_entities) == 1
    assert str(marking_entities[0].dxftype()).upper() == "LINE"


def test_t5_normalized_metadata_fields_are_present(tmp_path: Path) -> None:
    entities = [_polyline_entity(layer="CUT_OUTER", points=_square())]
    result, _role, _gap, _dedupe, output_path = _run_chain(
        tmp_path=tmp_path,
        entities=entities,
    )

    metadata = result["normalized_dxf"]
    assert metadata["output_path"] == str(output_path.resolve())
    assert metadata["writer_backend"] == "ezdxf"
    assert isinstance(metadata["written_layers"], list)
    assert isinstance(metadata["written_entity_count"], int)
    assert isinstance(metadata["cut_contour_count"], int)
    assert isinstance(metadata["marking_entity_count"], int)
