#!/usr/bin/env python3
"""Real-world DXF preflight regression tests for the four LV8 parts.

These files previously failed because all cutting geometry is on layer "0"
(not CUT_OUTER / CUT_INNER), which the old layer-level role resolver could
not classify.  After the contour-level resolver fix they must be accepted.

Fixtures (copies of samples/real_work_dxf/0014-01H/lv8jav/):
  LV8_02049_50db_REV7.dxf   → expected: 1 outer + 1 inner
  LV8_02048_20db_L_REV5.dxf → expected: 1 outer + 1 inner
  LV8_01170_10db_REV5.dxf   → expected: 1 outer + 0 inner
  LV8_00057_2_20db_REV8.dxf → expected: 1 outer + 1 inner  (ARC wrap-around)
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest

from api.services.dxf_preflight_acceptance_gate import evaluate_dxf_prefilter_acceptance_gate
from api.services.dxf_preflight_duplicate_dedupe import dedupe_dxf_duplicate_contours
from api.services.dxf_preflight_gap_repair import repair_dxf_gaps
from api.services.dxf_preflight_inspect import inspect_dxf_source
from api.services.dxf_preflight_normalized_dxf_writer import write_normalized_dxf
from api.services.dxf_preflight_role_resolver import resolve_dxf_roles

_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "dxf_preflight" / "real_world"

_PROFILE = {
    "strict_mode": False,
    "auto_repair_enabled": True,
    "interactive_review_on_ambiguity": True,
    "max_gap_close_mm": 2.0,
    "duplicate_contour_merge_tolerance_mm": 0.1,
}


def _run_full_preflight(dxf_path: Path) -> dict[str, Any]:
    """Run the complete T1→T6 preflight chain and return all stage results."""
    inspect_result = inspect_dxf_source(dxf_path)
    role_resolution = resolve_dxf_roles(inspect_result, rules_profile=_PROFILE)
    gap_repair_result = repair_dxf_gaps(inspect_result, role_resolution, rules_profile=_PROFILE)
    dedupe_result = dedupe_dxf_duplicate_contours(
        inspect_result, role_resolution, gap_repair_result, rules_profile=_PROFILE
    )
    with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as tmp:
        out_path = tmp.name
    writer_result = write_normalized_dxf(
        inspect_result,
        role_resolution,
        gap_repair_result,
        dedupe_result,
        output_path=out_path,
        rules_profile=_PROFILE,
    )
    gate_result = evaluate_dxf_prefilter_acceptance_gate(
        inspect_result,
        role_resolution,
        gap_repair_result,
        dedupe_result,
        writer_result,
    )
    return {
        "inspect": inspect_result,
        "roles": role_resolution,
        "repair": gap_repair_result,
        "dedupe": dedupe_result,
        "writer": writer_result,
        "gate": gate_result,
    }


@pytest.mark.parametrize(
    "fixture_name, expected_outer_count, expected_inner_count",
    [
        ("LV8_02049_50db_REV7.dxf", 1, 1),
        ("LV8_02048_20db_L_REV5.dxf", 1, 1),
        ("LV8_01170_10db_REV5.dxf", 1, 0),
        ("LV8_00057_2_20db_REV8.dxf", 1, 1),
    ],
)
def test_real_world_dxf_preflight_accepts_messy_layer_contours(
    fixture_name: str,
    expected_outer_count: int,
    expected_inner_count: int,
) -> None:
    fixture = _FIXTURES_DIR / fixture_name
    if not fixture.is_file():
        pytest.skip(f"fixture not found: {fixture}")

    result = _run_full_preflight(fixture)
    gate = result["gate"]
    roles = result["roles"]
    dedupe = result["dedupe"]
    importer_probe = gate["importer_probe"]

    # Must be fully accepted — the runtime only forwards to geometry import on accepted_for_import.
    assert gate["acceptance_outcome"] == "accepted_for_import", (
        f"{fixture_name}: expected 'accepted_for_import', got {gate['acceptance_outcome']!r}. "
        f"Blocking: {gate['blocking_reasons']}  Review: {gate['review_required_reasons']}"
    )

    # Importer must succeed (normalized DXF is structurally valid).
    assert importer_probe["is_pass"], (
        f"{fixture_name}: importer probe failed: "
        f"{importer_probe.get('error_code')} — {importer_probe.get('error_message')}"
    )

    # Contour count as seen by the acceptance gate importer.
    assert importer_probe["hole_count"] == expected_inner_count, (
        f"{fixture_name}: expected {expected_inner_count} holes, "
        f"got {importer_probe['hole_count']}"
    )

    # The contour-level resolver must have produced CUT_OUTER assignments.
    contour_assignments = roles.get("contour_role_assignments", [])
    outer_assigned = [a for a in contour_assignments if a["canonical_role"] == "CUT_OUTER"]
    inner_assigned = [a for a in contour_assignments if a["canonical_role"] == "CUT_INNER"]
    assert len(outer_assigned) >= expected_outer_count, (
        f"{fixture_name}: expected ≥{expected_outer_count} CUT_OUTER contour assignments, "
        f"got {len(outer_assigned)}"
    )
    assert len(inner_assigned) >= expected_inner_count, (
        f"{fixture_name}: expected ≥{expected_inner_count} CUT_INNER contour assignments, "
        f"got {len(inner_assigned)}"
    )

    # Dedupe working set must have the expected roles.
    working_set = dedupe.get("deduped_contour_working_set", [])
    ws_outer = [w for w in working_set if w["canonical_role"] == "CUT_OUTER"]
    ws_inner = [w for w in working_set if w["canonical_role"] == "CUT_INNER"]
    assert len(ws_outer) == expected_outer_count, (
        f"{fixture_name}: deduped working set has {len(ws_outer)} CUT_OUTER, expected {expected_outer_count}"
    )
    assert len(ws_inner) == expected_inner_count, (
        f"{fixture_name}: deduped working set has {len(ws_inner)} CUT_INNER, expected {expected_inner_count}"
    )


def test_real_world_no_cut_outer_layer_error_no_longer_raised() -> None:
    """None of the four fixtures should hit DXF_NO_OUTER_LAYER anymore."""
    for fixture_name in [
        "LV8_02049_50db_REV7.dxf",
        "LV8_02048_20db_L_REV5.dxf",
        "LV8_01170_10db_REV5.dxf",
        "LV8_00057_2_20db_REV8.dxf",
    ]:
        fixture = _FIXTURES_DIR / fixture_name
        if not fixture.is_file():
            pytest.skip(f"fixture not found: {fixture}")
        result = _run_full_preflight(fixture)
        importer_probe = result["gate"]["importer_probe"]
        assert importer_probe.get("error_code") != "DXF_NO_OUTER_LAYER", (
            f"{fixture_name} still produces DXF_NO_OUTER_LAYER"
        )


def test_real_world_gravir_text_does_not_block_cut_acceptance() -> None:
    """The TEXT entities on the 'Gravír' layer must not block cut geometry acceptance."""
    for fixture_name in [
        "LV8_02049_50db_REV7.dxf",
        "LV8_02048_20db_L_REV5.dxf",
    ]:
        fixture = _FIXTURES_DIR / fixture_name
        if not fixture.is_file():
            pytest.skip(f"fixture not found: {fixture}")
        result = _run_full_preflight(fixture)
        gate = result["gate"]
        # TEXT on Gravír layer may produce skipped_source_entities warnings,
        # but must NOT produce a blocking reason.
        blocking = gate["blocking_reasons"]
        importer_errors = [
            r for r in blocking if r.get("family") == "importer_probe_failed"
        ]
        assert not importer_errors, (
            f"{fixture_name}: importer failed — Gravír TEXT may be blocking: "
            f"{importer_errors}"
        )


def test_real_world_lv8_nested_hole_demoted_to_review_required() -> None:
    """T05j: Lv8_11612_6db has nested hole topology (hole-within-hole).

    The shapely validator emits GEO_TOPOLOGY_INVALID "Holes are nested" but this is
    a shapely limitation (hole-within-hole is valid GIS geometry but shapely marks it
    invalid). Policy A: demote to review_required with explicit reason
    DXF_PREFLIGHT_NESTED_ISLAND_REQUIRES_MANUAL_REVIEW instead of preflight_rejected.

    Expected outcome: preflight_review_required (NOT preflight_rejected).
    The file must NOT become accepted_for_import because the geometry meaning is ambiguous.
    """
    fixture = _FIXTURES_DIR / "Lv8_11612_6db REV3.dxf"
    if not fixture.is_file():
        pytest.skip(f"fixture not found: {fixture}")

    result = _run_full_preflight(fixture)
    gate = result["gate"]
    roles = result["roles"]

    # T05j: must be review_required, NOT rejected
    assert gate["acceptance_outcome"] == "preflight_review_required", (
        f"expected 'preflight_review_required', got {gate['acceptance_outcome']!r}. "
        f"Blocking: {gate['blocking_reasons']}  Review: {gate['review_required_reasons']}"
    )

    # Must have explicit nested island review reason
    review_reasons = gate["review_required_reasons"]
    nested_island_reasons = [
        r for r in review_reasons
        if r.get("family") == "DXF_PREFLIGHT_NESTED_ISLAND_REQUIRES_MANUAL_REVIEW"
    ]
    assert len(nested_island_reasons) == 1, (
        f"expected DXF_PREFLIGHT_NESTED_ISLAND_REQUIRES_MANUAL_REVIEW in review reasons, "
        f"got: {review_reasons}"
    )

    # Importer must still pass (normalized DXF is structurally valid)
    importer_probe = gate["importer_probe"]
    assert importer_probe["is_pass"], (
        f"importer probe failed: {importer_probe.get('error_code')} — "
        f"{importer_probe.get('error_message')}"
    )

    # Role resolver: no blocking conflicts
    blocking = roles.get("blocking_conflicts", [])
    assert len(blocking) == 0, f"role resolver should have no blocking conflicts: {blocking}"

    # Hole count: should be 11 (9 depth-1 + 2 depth-2)
    assert importer_probe["hole_count"] == 11, (
        f"expected 11 holes, got {importer_probe['hole_count']}"
    )
