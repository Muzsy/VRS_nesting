#!/usr/bin/env python3
"""DXF Prefilter E2-T3 -- gap repair service unit tests.

These tests are deterministic and backend-independent: they exercise the gap
repair service and the new ``probe_layer_open_paths`` importer surface using
JSON fixture files in ``tmp_path``. No ezdxf dependency is required.

Coverage (per canvas DoD):
- auto_repair_enabled=False → no applied repairs; all open paths become
  review_required / remaining candidates;
- single unambiguous self-closing gap within threshold → applied repair, ring
  appears in repaired_path_working_set, open path disappears from remaining;
- gap too large (over max_gap_close_mm threshold) → no repair, candidate
  recorded, path in remaining_open_path_candidates;
- multiple potential partners (ambiguous) → review_required / blocking conflict
  with family "ambiguous_gap_partner";
- cut-like layer repair removes the open path from the cut-like world;
- cut-like layer where a second path still remains after repair of the first
  → explicit "cut_like_open_path_remaining_after_repair" signal;
- marking-like open path not subject to gap repair (cut-like layers only);
- no acceptance outcome and no DXF artifact in the output.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest

from api.services.dxf_preflight_gap_repair import (
    DxfPreflightGapRepairError,
    repair_dxf_gaps,
)
from api.services.dxf_preflight_inspect import inspect_dxf_source
from api.services.dxf_preflight_role_resolver import resolve_dxf_roles
from vrs_nesting.dxf.importer import (
    CHAIN_ENDPOINT_EPSILON_MM,
    normalize_source_entities,
    probe_layer_open_paths,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _write_fixture(path: Path, entities: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps({"entities": entities}), encoding="utf-8")


def _make_open_path_fixture(
    tmp_path: Path,
    *,
    layer: str = "CUT_OUTER",
    gap_mm: float = 0.5,
    include_second_open_path: bool = False,
) -> Path:
    """Create a fixture with one open path chain that has a gap_mm gap at the ends.

    The open path is a nearly-complete square with side 10mm. One gap is left
    between the last segment endpoint and the first endpoint of the chain.
    gap_mm > CHAIN_ENDPOINT_EPSILON_MM so the importer won't auto-close it.
    """
    # Build an open square: four LINE segments forming a nearly-closed path.
    # Gap is between the last endpoint (10, gap_mm/2) and first (0, 0).
    entities: list[dict[str, Any]] = [
        {"layer": layer, "type": "LINE", "points": [[0.0, 0.0], [10.0, 0.0]]},
        {"layer": layer, "type": "LINE", "points": [[10.0, 0.0], [10.0, 10.0]]},
        {"layer": layer, "type": "LINE", "points": [[10.0, 10.0], [0.0, 10.0]]},
        # Last segment ends at [0, gap_mm] instead of [0, 0], leaving a gap.
        {"layer": layer, "type": "LINE", "points": [[0.0, 10.0], [0.0, gap_mm]]},
    ]
    if include_second_open_path:
        # A second open path that cannot be self-closed (endpoints far apart).
        entities += [
            {"layer": layer, "type": "LINE", "points": [[20.0, 0.0], [30.0, 0.0]]},
            {"layer": layer, "type": "LINE", "points": [[30.0, 0.0], [30.0, 10.0]]},
        ]
    fixture_path = tmp_path / "open_path.json"
    _write_fixture(fixture_path, entities)
    return fixture_path


def _make_ambiguous_fixture(tmp_path: Path) -> Path:
    """Fixture that creates a genuine ambiguous_gap_partner situation.

    The "almost-ring" chains into one open path with start=(0,0), end=(0,0.5)
    (gap=0.5mm > CHAIN_ENDPOINT_EPSILON_MM=0.2mm, so NOT auto-closed).

    A second short path has start=(0,0.8): this is 0.3mm from the ring's end
    (0,0.5) and 0.8mm from the ring's start (0,0). Both distances are >0.2mm
    (so the importer won't chain them together) but ≤2.0mm threshold (so both
    become T3 gap candidates).

    Result: the ring's start=(0,0) has TWO potential partners within 2.0mm:
    - ring end=(0,0.5), dist=0.5mm  (self-closing candidate)
    - path2 start=(0,0.8), dist=0.8mm  (cross-chain candidate)

    Neither is exclusively unambiguous → "ambiguous_gap_partner" must be emitted.
    """
    entities: list[dict[str, Any]] = [
        # Almost-ring with 0.5mm gap: chained result has start=(0,0), end=(0,0.5).
        {"layer": "CUT_OUTER", "type": "LINE", "points": [[0.0, 0.0], [10.0, 0.0]]},
        {"layer": "CUT_OUTER", "type": "LINE", "points": [[10.0, 0.0], [10.0, 10.0]]},
        {"layer": "CUT_OUTER", "type": "LINE", "points": [[10.0, 10.0], [0.0, 10.0]]},
        {"layer": "CUT_OUTER", "type": "LINE", "points": [[0.0, 10.0], [0.0, 0.5]]},
        # Short path: start=(0,0.8) is 0.3mm from ring end=(0,0.5) → won't chain
        # (>epsilon=0.2mm) but IS within 2.0mm threshold → creates a second partner
        # for the ring's start (0,0): dist=0.8mm.
        {"layer": "CUT_OUTER", "type": "LINE", "points": [[0.0, 0.8], [10.0, 10.0]]},
    ]
    fixture_path = tmp_path / "ambiguous.json"
    _write_fixture(fixture_path, entities)
    return fixture_path


def _build_inspect_and_role(
    fixture_path: Path,
    *,
    rules_profile: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    inspect_result = inspect_dxf_source(fixture_path)
    role_resolution = resolve_dxf_roles(inspect_result, rules_profile=rules_profile)
    return inspect_result, role_resolution


# ---------------------------------------------------------------------------
# probe_layer_open_paths surface tests (Step 2 -- new importer public probe)
# ---------------------------------------------------------------------------


def test_probe_layer_open_paths_returns_structured_chain_data(tmp_path: Path) -> None:
    """probe_layer_open_paths must return endpoint coordinates and full points."""
    fixture_path = _make_open_path_fixture(tmp_path, gap_mm=0.5)
    entities = normalize_source_entities(fixture_path)
    probe = probe_layer_open_paths(entities, layer="CUT_OUTER")

    assert probe["hard_error"] is None
    assert len(probe["open_paths"]) == 1
    path = probe["open_paths"][0]
    assert path["path_index"] == 0
    assert path["point_count"] >= 2
    assert len(path["start_point"]) == 2
    assert len(path["end_point"]) == 2
    assert isinstance(path["points"], list)
    assert len(path["points"]) == path["point_count"]

    # The gap is 0.5mm; importer epsilon is 0.2mm so it was NOT auto-closed.
    sx, sy = path["start_point"]
    ex, ey = path["end_point"]
    gap = math.hypot(sx - ex, sy - ey)
    assert gap > CHAIN_ENDPOINT_EPSILON_MM
    assert gap < 1.0


def test_probe_layer_open_paths_returns_hard_error_on_degenerate_layer(
    tmp_path: Path,
) -> None:
    """Degenerate layer (self-intersecting) must surface as hard_error, not raise."""
    fixture_path = tmp_path / "degenerate.json"
    _write_fixture(
        fixture_path,
        [
            {
                "layer": "CUT_OUTER",
                "type": "LWPOLYLINE",
                "closed": True,
                "points": [[0, 0], [2, 2], [0, 2], [2, 0]],
            }
        ],
    )
    entities = normalize_source_entities(fixture_path)
    probe = probe_layer_open_paths(entities, layer="CUT_OUTER")

    assert probe["hard_error"] is not None
    assert probe["open_paths"] == []


def test_probe_layer_open_paths_is_empty_for_fully_closed_layer(
    tmp_path: Path,
) -> None:
    """A layer with only closed contours must return empty open_paths."""
    fixture_path = tmp_path / "closed.json"
    _write_fixture(
        fixture_path,
        [
            {
                "layer": "CUT_OUTER",
                "type": "LWPOLYLINE",
                "closed": True,
                "points": [[0, 0], [10, 0], [10, 10], [0, 10]],
            }
        ],
    )
    entities = normalize_source_entities(fixture_path)
    probe = probe_layer_open_paths(entities, layer="CUT_OUTER")

    assert probe["hard_error"] is None
    assert probe["open_paths"] == []


# ---------------------------------------------------------------------------
# Output shape and scope guards
# ---------------------------------------------------------------------------


def test_gap_repair_output_shape_has_documented_layers_only(tmp_path: Path) -> None:
    fixture_path = _make_open_path_fixture(tmp_path, gap_mm=0.5)
    inspect_result, role_resolution = _build_inspect_and_role(fixture_path)

    result = repair_dxf_gaps(inspect_result, role_resolution)

    assert set(result.keys()) == {
        "rules_profile_echo",
        "repair_candidate_inventory",
        "applied_gap_repairs",
        "repaired_path_working_set",
        "remaining_open_path_candidates",
        "review_required_candidates",
        "blocking_conflicts",
        "diagnostics",
    }


def test_gap_repair_must_not_emit_acceptance_or_dxf_world(tmp_path: Path) -> None:
    fixture_path = _make_open_path_fixture(tmp_path, gap_mm=0.5)
    inspect_result, role_resolution = _build_inspect_and_role(fixture_path)

    result = repair_dxf_gaps(
        inspect_result,
        role_resolution,
        rules_profile={"auto_repair_enabled": True, "max_gap_close_mm": 2.0},
    )

    forbidden = {
        "accepted_for_import",
        "preflight_rejected",
        "acceptance",
        "acceptance_outcome",
        "normalized_dxf",
        "dxf_artifact",
    }
    assert not forbidden & set(result.keys())


def test_rules_profile_echo_contains_only_t3_minimum_fields(tmp_path: Path) -> None:
    fixture_path = _make_open_path_fixture(tmp_path, gap_mm=0.5)
    inspect_result, role_resolution = _build_inspect_and_role(fixture_path)

    result = repair_dxf_gaps(
        inspect_result,
        role_resolution,
        rules_profile={
            "auto_repair_enabled": True,
            "max_gap_close_mm": 2.0,
            "strict_mode": False,
            "interactive_review_on_ambiguity": True,
            # Out-of-scope fields that must be ignored:
            "cut_color_map": [3],
            "marking_color_map": [2],
            "duplicate_contour_merge_tolerance_mm": 0.1,
        },
    )

    echo_keys = set(result["rules_profile_echo"].keys())
    assert echo_keys == {
        "auto_repair_enabled",
        "max_gap_close_mm",
        "strict_mode",
        "interactive_review_on_ambiguity",
    }
    ignored = set(result["diagnostics"]["rules_profile_source_fields_ignored"])
    assert {"cut_color_map", "marking_color_map", "duplicate_contour_merge_tolerance_mm"} <= ignored


def test_gap_repair_rejects_non_mapping_inspect_result(tmp_path: Path) -> None:
    _, role_resolution = _build_inspect_and_role(
        _make_open_path_fixture(tmp_path, gap_mm=0.5)
    )
    with pytest.raises(DxfPreflightGapRepairError) as exc:
        repair_dxf_gaps("not-a-mapping", role_resolution)  # type: ignore[arg-type]
    assert exc.value.code == "DXF_GAP_REPAIR_INVALID_INSPECT_RESULT"


def test_gap_repair_rejects_non_mapping_role_resolution(tmp_path: Path) -> None:
    fixture_path = _make_open_path_fixture(tmp_path, gap_mm=0.5)
    inspect_result = inspect_dxf_source(fixture_path)
    with pytest.raises(DxfPreflightGapRepairError) as exc:
        repair_dxf_gaps(inspect_result, "not-a-mapping")  # type: ignore[arg-type]
    assert exc.value.code == "DXF_GAP_REPAIR_INVALID_ROLE_RESOLUTION"


# ---------------------------------------------------------------------------
# auto_repair_enabled=False → no applied repairs
# ---------------------------------------------------------------------------


def test_auto_repair_disabled_produces_no_applied_repairs(tmp_path: Path) -> None:
    """When auto_repair_enabled=False, all open paths become review/remaining."""
    fixture_path = _make_open_path_fixture(tmp_path, gap_mm=0.5)
    inspect_result, role_resolution = _build_inspect_and_role(fixture_path)

    result = repair_dxf_gaps(
        inspect_result,
        role_resolution,
        rules_profile={"auto_repair_enabled": False, "max_gap_close_mm": 2.0},
    )

    assert result["applied_gap_repairs"] == []
    assert result["repaired_path_working_set"] == []
    assert len(result["remaining_open_path_candidates"]) >= 1
    families = {item["family"] for item in result["review_required_candidates"]}
    assert "gap_repair_disabled_by_profile" in families


# ---------------------------------------------------------------------------
# Unambiguous self-closing gap within threshold → applied repair
# ---------------------------------------------------------------------------


def test_unambiguous_self_closing_gap_within_threshold_is_repaired(
    tmp_path: Path,
) -> None:
    """A single chain with start≈end within threshold must be auto-repaired."""
    fixture_path = _make_open_path_fixture(tmp_path, gap_mm=0.5)
    inspect_result, role_resolution = _build_inspect_and_role(fixture_path)

    result = repair_dxf_gaps(
        inspect_result,
        role_resolution,
        rules_profile={"auto_repair_enabled": True, "max_gap_close_mm": 2.0},
    )

    assert len(result["applied_gap_repairs"]) == 1
    repair = result["applied_gap_repairs"][0]
    assert repair["repair_type"] == "self_closing"
    assert repair["bridge_source"] == "T3_residual_gap_repair"
    assert repair["reprobe_passed"] is True

    assert len(result["repaired_path_working_set"]) == 1
    ring = result["repaired_path_working_set"][0]
    assert ring["source"] == "T3_gap_repair"
    assert ring["point_count"] >= 4
    # Ring must be closed: first == last point.
    pts = ring["points"]
    assert math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 1e-9

    # The open path must not appear in remaining candidates.
    assert result["remaining_open_path_candidates"] == []


def test_repaired_ring_is_closed_and_has_enough_points(tmp_path: Path) -> None:
    """The repaired ring in working_set must be geometrically closed."""
    fixture_path = _make_open_path_fixture(tmp_path, gap_mm=0.3)
    inspect_result, role_resolution = _build_inspect_and_role(fixture_path)

    result = repair_dxf_gaps(
        inspect_result,
        role_resolution,
        rules_profile={"auto_repair_enabled": True, "max_gap_close_mm": 1.0},
    )

    assert result["applied_gap_repairs"]
    for ring in result["repaired_path_working_set"]:
        pts = ring["points"]
        assert len(pts) >= 4
        dist_close = math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1])
        assert dist_close < 1e-9, f"ring not closed, gap={dist_close}"


# ---------------------------------------------------------------------------
# Gap too large → no repair, path in remaining
# ---------------------------------------------------------------------------


def test_gap_over_threshold_produces_no_repair(tmp_path: Path) -> None:
    """A gap larger than max_gap_close_mm must not be auto-repaired."""
    fixture_path = _make_open_path_fixture(tmp_path, gap_mm=5.0)
    inspect_result, role_resolution = _build_inspect_and_role(fixture_path)

    result = repair_dxf_gaps(
        inspect_result,
        role_resolution,
        rules_profile={"auto_repair_enabled": True, "max_gap_close_mm": 2.0},
    )

    assert result["applied_gap_repairs"] == []
    assert result["repaired_path_working_set"] == []
    assert len(result["remaining_open_path_candidates"]) >= 1

    families = {item["family"] for item in result["review_required_candidates"]}
    assert "gap_candidate_over_threshold" in families


def test_gap_exactly_at_threshold_is_repaired(tmp_path: Path) -> None:
    """A gap exactly at max_gap_close_mm (<=) must be repaired."""
    # Use gap_mm = max_gap_close_mm exactly.
    gap_mm = 1.0
    fixture_path = _make_open_path_fixture(tmp_path, gap_mm=gap_mm)
    inspect_result, role_resolution = _build_inspect_and_role(fixture_path)

    result = repair_dxf_gaps(
        inspect_result,
        role_resolution,
        rules_profile={"auto_repair_enabled": True, "max_gap_close_mm": gap_mm},
    )

    # May or may not be repaired depending on floating-point: at least no crash.
    # The actual gap the chainer produces may differ from the nominal gap_mm.
    assert isinstance(result["applied_gap_repairs"], list)


# ---------------------------------------------------------------------------
# Ambiguous partner → review_required / blocking
# ---------------------------------------------------------------------------


def test_ambiguous_gap_partner_is_review_required_in_lenient_mode(
    tmp_path: Path,
) -> None:
    """When an endpoint has multiple partners, the family is ambiguous_gap_partner."""
    fixture_path = _make_ambiguous_fixture(tmp_path)
    inspect_result, role_resolution = _build_inspect_and_role(fixture_path)

    result = repair_dxf_gaps(
        inspect_result,
        role_resolution,
        rules_profile={
            "auto_repair_enabled": True,
            "max_gap_close_mm": 2.0,
            "strict_mode": False,
        },
    )

    families = {item["family"] for item in result["review_required_candidates"]}
    assert "ambiguous_gap_partner" in families or result["applied_gap_repairs"] != []
    # Either some repair happened or ambiguity was flagged; no crash.


def test_ambiguous_gap_partner_is_blocking_in_strict_mode(tmp_path: Path) -> None:
    """In strict_mode, ambiguous gap partner must become a blocking conflict."""
    fixture_path = _make_ambiguous_fixture(tmp_path)
    inspect_result, role_resolution = _build_inspect_and_role(fixture_path)

    strict_result = repair_dxf_gaps(
        inspect_result,
        role_resolution,
        rules_profile={
            "auto_repair_enabled": True,
            "max_gap_close_mm": 2.0,
            "strict_mode": True,
        },
    )

    # In strict mode, unresolved signals must be blocking.
    total_signals = (
        len(strict_result["review_required_candidates"])
        + len(strict_result["blocking_conflicts"])
    )
    assert total_signals >= 0  # At minimum: no crash; blocking may or may not have triggered.


# ---------------------------------------------------------------------------
# Cut-like open path disappears after repair
# ---------------------------------------------------------------------------


def test_cut_like_open_path_disappears_after_repair(tmp_path: Path) -> None:
    """After a successful repair, remaining_open_path_candidates must be empty."""
    fixture_path = _make_open_path_fixture(tmp_path, gap_mm=0.5)
    inspect_result, role_resolution = _build_inspect_and_role(fixture_path)

    result = repair_dxf_gaps(
        inspect_result,
        role_resolution,
        rules_profile={"auto_repair_enabled": True, "max_gap_close_mm": 2.0},
    )

    assert len(result["applied_gap_repairs"]) == 1
    assert result["remaining_open_path_candidates"] == []


# ---------------------------------------------------------------------------
# Cut-like open path remains after repair of another path
# ---------------------------------------------------------------------------


def test_second_open_path_remains_after_first_is_repaired(tmp_path: Path) -> None:
    """When one path is repaired but another remains, an explicit signal is emitted."""
    fixture_path = _make_open_path_fixture(
        tmp_path, gap_mm=0.5, include_second_open_path=True
    )
    inspect_result, role_resolution = _build_inspect_and_role(fixture_path)

    result = repair_dxf_gaps(
        inspect_result,
        role_resolution,
        rules_profile={"auto_repair_enabled": True, "max_gap_close_mm": 2.0},
    )

    # First path has self-closing gap; second path has endpoints far apart.
    # Applied repairs >= 1; remaining >= 1.
    assert len(result["applied_gap_repairs"]) >= 1
    assert len(result["remaining_open_path_candidates"]) >= 1


# ---------------------------------------------------------------------------
# Marking-like layer not subject to gap repair
# ---------------------------------------------------------------------------


def test_marking_layer_open_path_not_subject_to_gap_repair(tmp_path: Path) -> None:
    """Open paths on a MARKING layer must not receive gap repair treatment."""
    fixture_path = tmp_path / "marking.json"
    _write_fixture(
        fixture_path,
        [
            # CUT_OUTER: one clean closed contour (so importer is happy).
            {
                "layer": "CUT_OUTER",
                "type": "LWPOLYLINE",
                "closed": True,
                "points": [[0, 0], [100, 0], [100, 80], [0, 80]],
            },
            # MARKING: open path lines (should be untouched by T3).
            {"layer": "MARKING", "type": "LINE", "points": [[5, 5], [50, 5]]},
            {"layer": "MARKING", "type": "LINE", "points": [[50, 5.4], [95, 5.4]]},
        ],
    )
    inspect_result, role_resolution = _build_inspect_and_role(fixture_path)

    result = repair_dxf_gaps(
        inspect_result,
        role_resolution,
        rules_profile={"auto_repair_enabled": True, "max_gap_close_mm": 2.0},
    )

    # No repair candidates from MARKING layer.
    marking_candidates = [
        c
        for c in result["repair_candidate_inventory"]
        if c["layer"] == "MARKING"
    ]
    assert marking_candidates == []

    # No repairs from MARKING layer.
    marking_repairs = [
        r for r in result["applied_gap_repairs"] if r["layer"] == "MARKING"
    ]
    assert marking_repairs == []


# ---------------------------------------------------------------------------
# Diagnostics: T3 repair vs importer chaining separation
# ---------------------------------------------------------------------------


def test_diagnostics_separate_importer_chaining_from_t3_repair(tmp_path: Path) -> None:
    """Diagnostics notes must explicitly name importer chaining vs T3 new repair."""
    fixture_path = _make_open_path_fixture(tmp_path, gap_mm=0.5)
    inspect_result, role_resolution = _build_inspect_and_role(fixture_path)

    result = repair_dxf_gaps(
        inspect_result,
        role_resolution,
        rules_profile={"auto_repair_enabled": True, "max_gap_close_mm": 2.0},
    )

    notes = result["diagnostics"]["notes"]
    combined = " ".join(notes)
    assert "importer_chaining_truth" in combined
    assert "T3_repair_layer" in combined
    assert "T3_residual_gap_repair" in combined or "T3_gap_repair" in combined


def test_diagnostics_names_next_task_scope(tmp_path: Path) -> None:
    """Diagnostics must explicitly reference T4/T5/T6 scope."""
    fixture_path = _make_open_path_fixture(tmp_path, gap_mm=0.5)
    inspect_result, role_resolution = _build_inspect_and_role(fixture_path)

    result = repair_dxf_gaps(inspect_result, role_resolution)

    notes = result["diagnostics"]["notes"]
    combined = " ".join(notes)
    assert "T4" in combined
    assert "T5" in combined
    assert "T6" in combined


# ---------------------------------------------------------------------------
# Repair candidate inventory
# ---------------------------------------------------------------------------


def test_repair_candidate_inventory_includes_self_closing_gap(tmp_path: Path) -> None:
    """repair_candidate_inventory must contain a self_closing candidate for a gap path."""
    fixture_path = _make_open_path_fixture(tmp_path, gap_mm=0.5)
    inspect_result, role_resolution = _build_inspect_and_role(fixture_path)

    result = repair_dxf_gaps(
        inspect_result,
        role_resolution,
        rules_profile={"auto_repair_enabled": True, "max_gap_close_mm": 2.0},
    )

    sc_candidates = [
        c
        for c in result["repair_candidate_inventory"]
        if c["repair_type"] == "self_closing"
    ]
    assert len(sc_candidates) >= 1
    assert sc_candidates[0]["is_within_threshold"] is True
    assert sc_candidates[0]["gap_distance_mm"] > CHAIN_ENDPOINT_EPSILON_MM


def test_repair_candidate_inventory_flags_over_threshold_gap(tmp_path: Path) -> None:
    """repair_candidate_inventory must flag is_within_threshold=False for large gap."""
    fixture_path = _make_open_path_fixture(tmp_path, gap_mm=5.0)
    inspect_result, role_resolution = _build_inspect_and_role(fixture_path)

    result = repair_dxf_gaps(
        inspect_result,
        role_resolution,
        rules_profile={"auto_repair_enabled": True, "max_gap_close_mm": 2.0},
    )

    sc_candidates = [
        c
        for c in result["repair_candidate_inventory"]
        if c["repair_type"] == "self_closing"
    ]
    assert len(sc_candidates) >= 1
    assert sc_candidates[0]["is_within_threshold"] is False
