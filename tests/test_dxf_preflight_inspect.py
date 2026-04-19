#!/usr/bin/env python3
"""DXF Prefilter E2-T1 -- preflight inspect engine unit tests.

These tests are intentionally backend-independent: they exercise the JSON
fixture path of ``vrs_nesting.dxf.importer`` so they reproduce on any dev /
CI environment without depending on ezdxf. The real DXF backend is covered
by existing importer tests and smoke suites; the preflight inspect engine
just needs deterministic proof that the inventory / candidate / diagnostics
layers behave correctly and that a hard-fail path still raises a stable
importer error as required by the canvas.
"""

from __future__ import annotations

import json

import pytest

from api.services.dxf_preflight_inspect import (
    DxfPreflightInspectError,
    inspect_dxf_source,
)
from vrs_nesting.dxf.importer import (
    DxfImportError,
    import_part_raw,
    normalize_source_entities,
    probe_layer_rings,
)


def _write_fixture(path, entities):
    path.write_text(json.dumps({"entities": entities}), encoding="utf-8")


def test_preflight_inspect_builds_layer_color_linetype_inventory(tmp_path):
    fixture_path = tmp_path / "inventory.json"
    _write_fixture(
        fixture_path,
        [
            {
                "layer": "CUT_OUTER",
                "type": "LWPOLYLINE",
                "closed": True,
                "points": [[0, 0], [100, 0], [100, 60], [0, 60]],
                "color_index": 7,
                "linetype_name": "CONTINUOUS",
            },
            {
                "layer": "CUT_INNER",
                "type": "LWPOLYLINE",
                "closed": True,
                "points": [[20, 20], [40, 20], [40, 30], [20, 30]],
                "color_index": 1,
                "linetype_name": "CONTINUOUS",
            },
            {
                "layer": "MARKING",
                "type": "LINE",
                "points": [[5, 5], [95, 5]],
                # No color / linetype -> raw None expected.
            },
        ],
    )

    result = inspect_dxf_source(fixture_path)

    assert result["backend"] == "json"
    layer_names = [item["layer"] for item in result["layer_inventory"]]
    assert layer_names == ["CUT_INNER", "CUT_OUTER", "MARKING"]

    cut_outer = next(item for item in result["layer_inventory"] if item["layer"] == "CUT_OUTER")
    assert cut_outer["entity_count"] == 1
    assert cut_outer["supported_count"] == 1
    assert cut_outer["unsupported_count"] == 0
    assert cut_outer["types"] == ["LWPOLYLINE"]

    color_counts = {item["color_index"]: item["count"] for item in result["color_inventory"]}
    assert color_counts == {1: 1, 7: 1, None: 1}

    linetype_counts = {item["linetype_name"]: item["count"] for item in result["linetype_inventory"]}
    assert linetype_counts == {"CONTINUOUS": 2, None: 1}

    marking_entity = next(
        item for item in result["entity_inventory"] if item["layer"] == "MARKING"
    )
    assert marking_entity["color_index"] is None
    assert marking_entity["linetype_name"] is None
    assert marking_entity["type"] == "LINE"
    assert marking_entity["point_count"] == 2


def test_preflight_inspect_detects_contour_and_open_path_candidates(tmp_path):
    fixture_path = tmp_path / "candidates.json"
    _write_fixture(
        fixture_path,
        [
            {
                "layer": "CUT_OUTER",
                "type": "LWPOLYLINE",
                "closed": True,
                "points": [[0, 0], [100, 0], [100, 60], [0, 60]],
            },
            {
                "layer": "CUT_INNER",
                "type": "LWPOLYLINE",
                "closed": True,
                "points": [[20, 20], [40, 20], [40, 30], [20, 30]],
            },
            {
                "layer": "CUT_INNER",
                "type": "LINE",
                "points": [[60, 20], [70, 20]],
            },
        ],
    )

    result = inspect_dxf_source(fixture_path)

    contour_layers = sorted(
        (item["layer"], item["ring_index"]) for item in result["contour_candidates"]
    )
    assert contour_layers == [("CUT_INNER", 0), ("CUT_OUTER", 0)]

    open_by_layer = {item["layer"]: item["open_path_count"] for item in result["open_path_candidates"]}
    assert open_by_layer == {"CUT_INNER": 1}


def test_preflight_inspect_flags_duplicate_contour_candidates(tmp_path):
    fixture_path = tmp_path / "duplicates.json"
    _write_fixture(
        fixture_path,
        [
            {
                "layer": "CUT_OUTER",
                "type": "LWPOLYLINE",
                "closed": True,
                "points": [[0, 0], [10, 0], [10, 10], [0, 10]],
            },
            {
                "layer": "DUPLICATE_OUTER",
                "type": "LWPOLYLINE",
                "closed": True,
                "points": [[0, 0], [10, 0], [10, 10], [0, 10]],
            },
        ],
    )

    result = inspect_dxf_source(fixture_path)

    duplicates = result["duplicate_contour_candidates"]
    assert len(duplicates) == 1
    ref_layers = sorted(ref["layer"] for ref in duplicates[0]["ring_references"])
    assert ref_layers == ["CUT_OUTER", "DUPLICATE_OUTER"]
    assert duplicates[0]["count"] == 2


def test_preflight_inspect_detects_outer_and_inner_like_topology(tmp_path):
    fixture_path = tmp_path / "topology.json"
    _write_fixture(
        fixture_path,
        [
            {
                "layer": "CUT_OUTER",
                "type": "LWPOLYLINE",
                "closed": True,
                "points": [[0, 0], [100, 0], [100, 80], [0, 80]],
            },
            {
                "layer": "CUT_INNER",
                "type": "LWPOLYLINE",
                "closed": True,
                "points": [[10, 10], [30, 10], [30, 30], [10, 30]],
            },
        ],
    )

    result = inspect_dxf_source(fixture_path)

    outer_like = result["outer_like_candidates"]
    inner_like = result["inner_like_candidates"]

    assert len(outer_like) == 1
    assert outer_like[0]["layer"] == "CUT_OUTER"
    assert outer_like[0]["contains_ring_references"][0]["layer"] == "CUT_INNER"

    assert len(inner_like) == 1
    assert inner_like[0]["layer"] == "CUT_INNER"
    assert inner_like[0]["contained_by_ring_references"][0]["layer"] == "CUT_OUTER"


def test_preflight_inspect_soft_failure_preserves_inventory(tmp_path):
    """A per-layer hard error must surface as diagnostics, not raise.

    This reproduces the canvas requirement that the service reports raw
    observations even when part of the source is unclean (here: a self-
    intersecting closed LWPOLYLINE on ``CUT_OUTER``). The inspect service
    must still populate the entity / layer / color / linetype inventories
    for the caller.
    """

    fixture_path = tmp_path / "soft_failure.json"
    _write_fixture(
        fixture_path,
        [
            {
                "layer": "CUT_OUTER",
                "type": "LWPOLYLINE",
                "closed": True,
                "points": [[0, 0], [2, 2], [0, 2], [2, 0]],
                "color_index": 7,
            },
        ],
    )

    result = inspect_dxf_source(fixture_path)

    # Inventory must still reflect what we observed.
    assert len(result["entity_inventory"]) == 1
    assert result["entity_inventory"][0]["layer"] == "CUT_OUTER"

    probe_errors = result["diagnostics"]["probe_errors"]
    assert len(probe_errors) == 1
    assert probe_errors[0]["layer"] == "CUT_OUTER"
    assert probe_errors[0]["code"] == "DXF_INVALID_RING"

    # No contour candidate was produced; no acceptance outcome at all.
    assert result["contour_candidates"] == []
    assert "acceptance" not in result


def test_preflight_inspect_hard_fail_on_missing_source(tmp_path):
    missing_path = tmp_path / "does_not_exist.json"

    with pytest.raises(DxfPreflightInspectError) as exc:
        inspect_dxf_source(missing_path)

    assert exc.value.code == "DXF_PATH_NOT_FOUND"


def test_preflight_inspect_hard_fail_on_unsupported_input(tmp_path):
    unsupported_path = tmp_path / "input.txt"
    unsupported_path.write_text("no dxf here", encoding="utf-8")

    with pytest.raises(DxfPreflightInspectError) as exc:
        inspect_dxf_source(unsupported_path)

    assert exc.value.code == "DXF_UNSUPPORTED_INPUT"


def test_normalize_source_entities_public_surface_preserves_raw_signals(tmp_path):
    fixture_path = tmp_path / "raw_signals.json"
    _write_fixture(
        fixture_path,
        [
            {
                "layer": "CUT_OUTER",
                "type": "LWPOLYLINE",
                "closed": True,
                "points": [[0, 0], [1, 0], [1, 1], [0, 1]],
                "color": 3,
                "linetype": "DASHED",
            },
        ],
    )

    entities = normalize_source_entities(fixture_path)
    assert len(entities) == 1
    entity = entities[0]
    assert entity["layer"] == "CUT_OUTER"
    assert entity["color_index"] == 3
    assert entity["linetype_name"] == "DASHED"


def test_probe_layer_rings_returns_soft_error_shape(tmp_path):
    fixture_path = tmp_path / "probe_hard.json"
    _write_fixture(
        fixture_path,
        [
            {
                "layer": "CUT_OUTER",
                "type": "LWPOLYLINE",
                "closed": True,
                "points": [[0, 0], [2, 2], [0, 2], [2, 0]],
            },
        ],
    )

    entities = normalize_source_entities(fixture_path)
    probe = probe_layer_rings(entities, layer="CUT_OUTER")

    assert probe["layer"] == "CUT_OUTER"
    assert probe["entity_count"] == 1
    assert probe["rings"] == []
    assert probe["open_path_count"] == 0
    assert probe["hard_error"] is not None
    assert probe["hard_error"]["code"] == "DXF_INVALID_RING"


def test_import_part_raw_still_rejects_open_outer_after_preflight_helper_extraction(tmp_path):
    """Regression guard -- importer acceptance world must stay stable.

    E2-T1 only opens a minimal public helper and extends the normalized
    entity shape with optional raw signals. The existing `import_part_raw()`
    acceptance semantics (as tested by the repo smoke / E1 tests) must
    remain unchanged. This test re-verifies the most critical rejection so
    that future prefilter tasks cannot silently regress it.
    """

    fixture_path = tmp_path / "open_outer_guard.json"
    _write_fixture(
        fixture_path,
        [
            {
                "layer": "CUT_OUTER",
                "type": "LINE",
                "points": [[0, 0], [10, 0]],
            },
            {
                "layer": "CUT_OUTER",
                "type": "LINE",
                "points": [[10, 0], [10, 8]],
            },
        ],
    )

    with pytest.raises(DxfImportError) as exc:
        import_part_raw(fixture_path)

    assert exc.value.code == "DXF_OPEN_OUTER_PATH"
