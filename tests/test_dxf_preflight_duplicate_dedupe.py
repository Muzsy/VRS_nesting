#!/usr/bin/env python3
"""DXF Prefilter E2-T4 -- duplicate contour dedupe unit tests.

Deterministic tests for the T4 duplicate-dedupe backend layer.

Coverage:
- exact duplicate (same role, closed ring) -> successful dedupe;
- tolerance-noise duplicate -> successful dedupe within threshold;
- over-threshold similar contour -> no auto-dedupe;
- original importer ring vs T3 repaired duplicate -> original kept;
- cross-role duplicate -> review/blocking conflict, no silent merge;
- marking/unassigned duplicate world -> no silent auto-dedupe;
- service emits no acceptance outcome and no DXF writer artifact.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from api.services.dxf_preflight_duplicate_dedupe import (
    DxfPreflightDuplicateDedupeError,
    dedupe_dxf_duplicate_contours,
)
from api.services.dxf_preflight_inspect import inspect_dxf_source
from api.services.dxf_preflight_role_resolver import resolve_dxf_roles


EXPECTED_TOP_LEVEL_KEYS = {
    "rules_profile_echo",
    "closed_contour_inventory",
    "duplicate_candidate_inventory",
    "applied_duplicate_dedupes",
    "deduped_contour_working_set",
    "remaining_duplicate_candidates",
    "review_required_candidates",
    "blocking_conflicts",
    "diagnostics",
}

FORBIDDEN_TOP_LEVEL_KEYS = {
    "accepted_for_import",
    "preflight_rejected",
    "acceptance",
    "acceptance_outcome",
    "normalized_dxf",
    "dxf_artifact",
}


def _write_fixture(path: Path, entities: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps({"entities": entities}), encoding="utf-8")


def _base_square(*, size: float = 10.0, x: float = 0.0, y: float = 0.0) -> list[list[float]]:
    return [
        [x, y],
        [x + size, y],
        [x + size, y + size],
        [x, y + size],
    ]


def _noisy_square(*, epsilon: float) -> list[list[float]]:
    return [
        [0.0 + epsilon, 0.0],
        [10.0, 0.0 + epsilon],
        [10.0 - epsilon, 10.0],
        [0.0, 10.0 - epsilon],
    ]


def _polyline_entity(*, layer: str, points: list[list[float]]) -> dict[str, Any]:
    return {
        "layer": layer,
        "type": "LWPOLYLINE",
        "closed": True,
        "points": points,
    }


def _gap_result_with_repaired_paths(
    repaired_paths: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "rules_profile_echo": {},
        "repair_candidate_inventory": [],
        "applied_gap_repairs": [],
        "repaired_path_working_set": repaired_paths or [],
        "remaining_open_path_candidates": [],
        "review_required_candidates": [],
        "blocking_conflicts": [],
        "diagnostics": {},
    }


def _run_chain(
    *,
    tmp_path: Path,
    entities: list[dict[str, Any]],
    t4_rules_profile: dict[str, Any] | None = None,
    role_rules_profile: dict[str, Any] | None = None,
    repaired_paths: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    fixture_path = tmp_path / "fixture.json"
    _write_fixture(fixture_path, entities)

    inspect_result = inspect_dxf_source(fixture_path)
    role_resolution = resolve_dxf_roles(
        inspect_result,
        rules_profile=role_rules_profile,
    )
    gap_repair_result = _gap_result_with_repaired_paths(repaired_paths)

    result = dedupe_dxf_duplicate_contours(
        inspect_result,
        role_resolution,
        gap_repair_result,
        rules_profile=t4_rules_profile,
    )
    return result, inspect_result, role_resolution


# ---------------------------------------------------------------------------
# Output shape + scope guards
# ---------------------------------------------------------------------------


def test_duplicate_dedupe_output_shape_has_documented_layers_only(tmp_path: Path) -> None:
    entities = [_polyline_entity(layer="CUT_OUTER", points=_base_square())]
    result, _inspect_result, _role_resolution = _run_chain(tmp_path=tmp_path, entities=entities)

    assert set(result.keys()) == EXPECTED_TOP_LEVEL_KEYS


def test_duplicate_dedupe_must_not_emit_acceptance_or_dxf_writer_world(tmp_path: Path) -> None:
    entities = [_polyline_entity(layer="CUT_OUTER", points=_base_square())]
    result, _inspect_result, _role_resolution = _run_chain(
        tmp_path=tmp_path,
        entities=entities,
        t4_rules_profile={
            "auto_repair_enabled": True,
            "duplicate_contour_merge_tolerance_mm": 0.05,
        },
    )

    assert not FORBIDDEN_TOP_LEVEL_KEYS & set(result.keys())


def test_rules_profile_echo_contains_only_t4_minimum_fields(tmp_path: Path) -> None:
    entities = [_polyline_entity(layer="CUT_OUTER", points=_base_square())]
    result, _inspect_result, _role_resolution = _run_chain(
        tmp_path=tmp_path,
        entities=entities,
        t4_rules_profile={
            "auto_repair_enabled": True,
            "duplicate_contour_merge_tolerance_mm": 0.04,
            "strict_mode": False,
            "interactive_review_on_ambiguity": True,
            # Out-of-scope fields
            "max_gap_close_mm": 1.0,
            "cut_color_map": [3],
            "marking_color_map": [2],
        },
    )

    assert set(result["rules_profile_echo"].keys()) == {
        "auto_repair_enabled",
        "duplicate_contour_merge_tolerance_mm",
        "strict_mode",
        "interactive_review_on_ambiguity",
    }
    ignored = set(result["diagnostics"]["rules_profile_source_fields_ignored"])
    assert {"max_gap_close_mm", "cut_color_map", "marking_color_map"} <= ignored


# ---------------------------------------------------------------------------
# Duplicate coverage
# ---------------------------------------------------------------------------


def test_exact_duplicate_same_role_closed_ring_is_deduped(tmp_path: Path) -> None:
    entities = [
        _polyline_entity(layer="CUT_OUTER", points=_base_square()),
        _polyline_entity(layer="CUT_OUTER", points=_base_square()),
    ]

    result, inspect_result, _role_resolution = _run_chain(
        tmp_path=tmp_path,
        entities=entities,
        t4_rules_profile={
            "auto_repair_enabled": True,
            "duplicate_contour_merge_tolerance_mm": 0.05,
        },
    )

    assert len(inspect_result["duplicate_contour_candidates"]) == 1
    assert result["diagnostics"]["inspect_exact_duplicate_signal_count"] == 1
    assert len(result["applied_duplicate_dedupes"]) == 1
    assert len(result["deduped_contour_working_set"]) == 1

    applied = result["applied_duplicate_dedupes"][0]
    assert applied["keeper"]["source"] == "importer_probe"
    assert len(applied["dropped"]) == 1


def test_tolerance_noise_duplicate_is_deduped_within_threshold(tmp_path: Path) -> None:
    entities = [
        _polyline_entity(layer="CUT_OUTER", points=_base_square()),
        _polyline_entity(layer="CUT_OUTER", points=_noisy_square(epsilon=0.01)),
    ]

    result, _inspect_result, _role_resolution = _run_chain(
        tmp_path=tmp_path,
        entities=entities,
        t4_rules_profile={
            "auto_repair_enabled": True,
            "duplicate_contour_merge_tolerance_mm": 0.02,
        },
    )

    assert len(result["applied_duplicate_dedupes"]) == 1
    assert len(result["deduped_contour_working_set"]) == 1
    statuses = [item["status"] for item in result["duplicate_candidate_inventory"]]
    assert "within_tolerance_same_role" in statuses


def test_over_tolerance_similar_contour_is_not_auto_deduped(tmp_path: Path) -> None:
    entities = [
        _polyline_entity(layer="CUT_OUTER", points=_base_square()),
        _polyline_entity(layer="CUT_OUTER", points=_noisy_square(epsilon=0.015)),
    ]

    result, _inspect_result, _role_resolution = _run_chain(
        tmp_path=tmp_path,
        entities=entities,
        t4_rules_profile={
            "auto_repair_enabled": True,
            "duplicate_contour_merge_tolerance_mm": 0.01,
        },
    )

    assert result["applied_duplicate_dedupes"] == []
    assert len(result["deduped_contour_working_set"]) == 2
    review_families = [item["family"] for item in result["review_required_candidates"]]
    assert "duplicate_candidate_over_tolerance" in review_families


def test_original_importer_ring_wins_against_t3_repaired_duplicate(tmp_path: Path) -> None:
    base = _base_square()
    entities = [_polyline_entity(layer="CUT_OUTER", points=base)]

    repaired_paths = [
        {
            "layer": "CUT_OUTER",
            "canonical_role": "CUT_OUTER",
            "source": "T3_gap_repair",
            "point_count": 5,
            "points": base + [base[0]],
        }
    ]

    result, _inspect_result, _role_resolution = _run_chain(
        tmp_path=tmp_path,
        entities=entities,
        repaired_paths=repaired_paths,
        t4_rules_profile={
            "auto_repair_enabled": True,
            "duplicate_contour_merge_tolerance_mm": 0.05,
        },
    )

    assert len(result["applied_duplicate_dedupes"]) == 1
    applied = result["applied_duplicate_dedupes"][0]
    assert applied["keeper"]["source"] == "importer_probe"
    dropped_sources = [item["contour"]["source"] for item in applied["dropped"]]
    assert dropped_sources == ["T3_gap_repair"]


def test_cross_role_duplicate_routes_to_blocking_in_strict_mode(tmp_path: Path) -> None:
    base = _base_square()
    entities = [
        _polyline_entity(layer="CUT_OUTER", points=base),
        _polyline_entity(layer="CUT_INNER", points=base),
    ]

    result, _inspect_result, _role_resolution = _run_chain(
        tmp_path=tmp_path,
        entities=entities,
        t4_rules_profile={
            "auto_repair_enabled": True,
            "duplicate_contour_merge_tolerance_mm": 0.05,
            "strict_mode": True,
            "interactive_review_on_ambiguity": True,
        },
    )

    assert result["applied_duplicate_dedupes"] == []
    blocking_families = [item["family"] for item in result["blocking_conflicts"]]
    assert "duplicate_cross_role_conflict" in blocking_families


def test_marking_repaired_duplicates_are_not_silently_auto_deduped(tmp_path: Path) -> None:
    entities = [_polyline_entity(layer="CUT_OUTER", points=_base_square())]

    marking = _base_square(size=5.0, x=20.0, y=20.0)
    repaired_paths = [
        {
            "layer": "MARKING",
            "canonical_role": "MARKING",
            "source": "T3_gap_repair",
            "point_count": 5,
            "points": marking + [marking[0]],
        },
        {
            "layer": "MARKING",
            "canonical_role": "MARKING",
            "source": "T3_gap_repair",
            "point_count": 5,
            "points": marking + [marking[0]],
        },
    ]

    result, _inspect_result, _role_resolution = _run_chain(
        tmp_path=tmp_path,
        entities=entities,
        repaired_paths=repaired_paths,
        t4_rules_profile={
            "auto_repair_enabled": True,
            "duplicate_contour_merge_tolerance_mm": 0.05,
        },
    )

    assert result["applied_duplicate_dedupes"] == []
    # Only CUT-like contour remains in deduped working set.
    assert len(result["deduped_contour_working_set"]) == 1
    assert all(item["canonical_role"] in {"CUT_OUTER", "CUT_INNER"} for item in result["deduped_contour_working_set"])


def test_auto_repair_disabled_keeps_duplicate_group_unresolved(tmp_path: Path) -> None:
    entities = [
        _polyline_entity(layer="CUT_OUTER", points=_base_square()),
        _polyline_entity(layer="CUT_OUTER", points=_base_square()),
    ]

    result, _inspect_result, _role_resolution = _run_chain(
        tmp_path=tmp_path,
        entities=entities,
        t4_rules_profile={
            "auto_repair_enabled": False,
            "duplicate_contour_merge_tolerance_mm": 0.05,
        },
    )

    assert result["applied_duplicate_dedupes"] == []
    families = [item["family"] for item in result["review_required_candidates"]]
    assert "duplicate_dedupe_disabled_by_profile" in families
    assert "cut_like_duplicate_remaining_after_dedupe" in families


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def test_duplicate_dedupe_rejects_non_mapping_inputs() -> None:
    with pytest.raises(DxfPreflightDuplicateDedupeError):
        dedupe_dxf_duplicate_contours(
            inspect_result={},
            role_resolution={},
            gap_repair_result={},
            rules_profile={"auto_repair_enabled": "yes"},  # type: ignore[arg-type]
        )
