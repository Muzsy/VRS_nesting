#!/usr/bin/env python3
"""DXF Prefilter E5-T1 -- cross-module core unit test pack.

Fixture-driven regression matrix for the T1->T6 core pipeline.
Each scenario runs the full inspect -> role -> gap -> dedupe -> writer -> gate
chain on the same helper and asserts cross-step invariants, not just the
final acceptance outcome.

ezdxf dependency note (current-code truth):
  T5 (normalized DXF writer) and T6 (acceptance gate importer probe) require
  a real DXF artifact written and read via ezdxf.  This is not a shortcut --
  it is the actual production path.  pytest.importorskip("ezdxf") at module
  level skips the entire pack on environments where ezdxf is absent, making
  the dependency explicit rather than hiding it.

strict vs lenient truth:
  Several scenarios run in both lenient (strict_mode=False, default) and
  strict (strict_mode=True) modes.  In lenient mode upstream conflicts become
  review_required signals -> T6 returns preflight_review_required.  In strict
  mode the same conflicts become blocking -> T6 returns preflight_rejected.
  Each relevant test pair is named _lenient / _strict and asserts the exact
  outcome for each mode.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("ezdxf")  # T5/T6 require real DXF write/read via ezdxf

from api.services.dxf_preflight_acceptance_gate import (
    evaluate_dxf_prefilter_acceptance_gate,
)
from api.services.dxf_preflight_duplicate_dedupe import dedupe_dxf_duplicate_contours
from api.services.dxf_preflight_gap_repair import repair_dxf_gaps
from api.services.dxf_preflight_inspect import inspect_dxf_source
from api.services.dxf_preflight_normalized_dxf_writer import write_normalized_dxf
from api.services.dxf_preflight_role_resolver import resolve_dxf_roles


# ---------------------------------------------------------------------------
# Core pipeline helper (T1->T6)
# ---------------------------------------------------------------------------


def _write_json_fixture(path: Path, entities: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps({"entities": entities}), encoding="utf-8")


def _run_pipeline(
    tmp_path: Path,
    *,
    name: str,
    entities: list[dict[str, Any]],
    role_profile: dict[str, Any] | None = None,
    gap_profile: dict[str, Any] | None = None,
    dedupe_profile: dict[str, Any] | None = None,
    writer_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run T1->T6 and return all intermediate results keyed by stage name."""
    fx = tmp_path / f"{name}.json"
    _write_json_fixture(fx, entities)

    inspect = inspect_dxf_source(fx)
    role = resolve_dxf_roles(inspect, rules_profile=role_profile)
    gap = repair_dxf_gaps(inspect, role, rules_profile=gap_profile)
    dedupe = dedupe_dxf_duplicate_contours(inspect, role, gap, rules_profile=dedupe_profile)
    out_path = tmp_path / f"{name}.normalized.dxf"
    writer = write_normalized_dxf(
        inspect,
        role,
        gap,
        dedupe,
        output_path=out_path,
        rules_profile=writer_profile,
    )
    gate = evaluate_dxf_prefilter_acceptance_gate(inspect, role, gap, dedupe, writer)

    return {
        "inspect": inspect,
        "role": role,
        "gap": gap,
        "dedupe": dedupe,
        "writer": writer,
        "gate": gate,
        "output_path": out_path,
    }


# Common profile: enable auto-repair for T3 and T4 (lenient defaults otherwise).
_REPAIR_ENABLED: dict[str, Any] = {"auto_repair_enabled": True, "max_gap_close_mm": 1.0}


def _families(records: list[dict[str, Any]]) -> list[str]:
    return [str(item.get("family", "")) for item in records]


# ---------------------------------------------------------------------------
# a) Simple closed outer -> accepted_for_import
# ---------------------------------------------------------------------------


def test_simple_closed_outer_accepted(tmp_path: Path) -> None:
    """Single closed CUT_OUTER ring: full chain clean, accepted_for_import."""
    r = _run_pipeline(
        tmp_path,
        name="simple_outer",
        entities=[
            {
                "layer": "CUT_OUTER",
                "type": "LWPOLYLINE",
                "closed": True,
                "points": [[0, 0], [100, 0], [100, 60], [0, 60]],
            }
        ],
        gap_profile=_REPAIR_ENABLED,
        dedupe_profile=_REPAIR_ENABLED,
    )

    # T1 inspect: 1 contour, no open paths, no duplicates
    assert len(r["inspect"]["contour_candidates"]) == 1
    assert r["inspect"]["open_path_candidates"] == []
    assert r["inspect"]["duplicate_contour_candidates"] == []

    # T2 role: CUT_OUTER assigned via explicit_canonical_layer, no conflicts
    co_role = next(
        a for a in r["role"]["layer_role_assignments"] if a["layer"] == "CUT_OUTER"
    )
    assert co_role["canonical_role"] == "CUT_OUTER"
    assert co_role["decision_source"] == "explicit_canonical_layer"
    assert r["role"]["blocking_conflicts"] == []
    assert r["role"]["review_required_candidates"] == []

    # T3 gap: nothing to repair
    assert r["gap"]["applied_gap_repairs"] == []
    assert r["gap"]["remaining_open_path_candidates"] == []

    # T4 dedupe: 1 contour in working set, no dedupes needed
    assert len(r["dedupe"]["deduped_contour_working_set"]) == 1
    assert r["dedupe"]["applied_duplicate_dedupes"] == []

    # T5 writer: output path exists, 1 cut contour written
    assert r["output_path"].is_file()
    assert r["writer"]["normalized_dxf"]["cut_contour_count"] == 1
    assert r["writer"]["normalized_dxf"]["output_path"] != ""

    # T6 gate: clean pass
    assert r["gate"]["acceptance_outcome"] == "accepted_for_import"
    assert r["gate"]["blocking_reasons"] == []
    assert r["gate"]["review_required_reasons"] == []
    assert r["gate"]["importer_probe"]["is_pass"] is True


# ---------------------------------------------------------------------------
# b) Outer + inner -> accepted_for_import
# ---------------------------------------------------------------------------


def test_outer_plus_inner_accepted(tmp_path: Path) -> None:
    """CUT_OUTER + CUT_INNER: both survive writer/gate, accepted_for_import."""
    r = _run_pipeline(
        tmp_path,
        name="outer_inner",
        entities=[
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
        ],
        gap_profile=_REPAIR_ENABLED,
        dedupe_profile=_REPAIR_ENABLED,
    )

    # T1 inspect: 2 contours, no open paths
    contour_layers = {c["layer"] for c in r["inspect"]["contour_candidates"]}
    assert "CUT_OUTER" in contour_layers
    assert "CUT_INNER" in contour_layers
    assert r["inspect"]["open_path_candidates"] == []

    # T2 role: both layers canonical, no conflicts
    role_map = {
        a["layer"]: a["canonical_role"] for a in r["role"]["layer_role_assignments"]
    }
    assert role_map["CUT_OUTER"] == "CUT_OUTER"
    assert role_map["CUT_INNER"] == "CUT_INNER"
    assert r["role"]["blocking_conflicts"] == []
    assert r["role"]["review_required_candidates"] == []

    # T4 dedupe: 2 contours survive, no dedupes
    assert len(r["dedupe"]["deduped_contour_working_set"]) == 2
    assert r["dedupe"]["applied_duplicate_dedupes"] == []

    # T5 writer: both cut layers written
    written_layers = set(r["writer"]["normalized_dxf"]["written_layers"])
    assert "CUT_OUTER" in written_layers
    assert "CUT_INNER" in written_layers
    assert r["writer"]["normalized_dxf"]["cut_contour_count"] == 2

    # T6 gate: inner ring does not break gate
    assert r["gate"]["acceptance_outcome"] == "accepted_for_import"
    assert r["gate"]["blocking_reasons"] == []
    assert r["gate"]["review_required_reasons"] == []
    assert r["gate"]["importer_probe"]["hole_count"] >= 1


# ---------------------------------------------------------------------------
# c) Unambiguous small gap -> T3 repairs it
#
# Current-code truth: T2 flags the open path as cut_like_open_path_on_canonical_layer
# (review_required in lenient mode) BEFORE T3 repairs it.  That T2 signal persists
# in role_resolution and causes T6 to return preflight_review_required even after
# the repair.  The key invariants are T3.applied_gap_repairs >= 1 and
# T3.remaining_open_path_candidates == [].
# ---------------------------------------------------------------------------


def test_small_gap_repaired(tmp_path: Path) -> None:
    """Open path with 0.4 mm gap: T3 repairs it; T2 open-path flag causes review_required."""
    r = _run_pipeline(
        tmp_path,
        name="small_gap",
        entities=[
            {
                "layer": "CUT_OUTER",
                "type": "LWPOLYLINE",
                "closed": False,
                # start=(0,0), end=(0,0.4): gap=0.4mm > CHAIN_EPSILON(0.2), < threshold(1.0)
                "points": [[0, 0], [100, 0], [100, 60], [0, 60], [0, 0.4]],
            }
        ],
        gap_profile=_REPAIR_ENABLED,
        dedupe_profile=_REPAIR_ENABLED,
    )

    # T1 inspect: open path detected, no closed contour yet
    assert len(r["inspect"]["open_path_candidates"]) >= 1
    assert r["inspect"]["open_path_candidates"][0]["layer"] == "CUT_OUTER"
    assert len(r["inspect"]["contour_candidates"]) == 0

    # T2 role: CUT_OUTER assigned, but open path emits cut_like_open_path_on_canonical_layer
    co_role = next(
        a for a in r["role"]["layer_role_assignments"] if a["layer"] == "CUT_OUTER"
    )
    assert co_role["canonical_role"] == "CUT_OUTER"
    rr_fams = _families(r["role"]["review_required_candidates"])
    assert "cut_like_open_path_on_canonical_layer" in rr_fams
    # No blocking in lenient mode
    assert r["role"]["blocking_conflicts"] == []

    # T3 gap: repair applied, nothing remaining
    assert len(r["gap"]["applied_gap_repairs"]) >= 1
    repair = r["gap"]["applied_gap_repairs"][0]
    assert repair["repair_type"] == "self_closing"
    assert repair["bridge_source"] == "T3_residual_gap_repair"
    assert r["gap"]["remaining_open_path_candidates"] == []
    assert r["gap"]["blocking_conflicts"] == []

    # T4 dedupe: repaired ring present in working set
    assert len(r["dedupe"]["deduped_contour_working_set"]) >= 1
    assert r["dedupe"]["deduped_contour_working_set"][0]["source"] == "T3_gap_repair"

    # T5 writer: repaired ring was written
    assert r["output_path"].is_file()
    assert r["writer"]["normalized_dxf"]["cut_contour_count"] >= 1

    # T6 gate: T2 open-path review signal persists -> preflight_review_required
    assert r["gate"]["acceptance_outcome"] == "preflight_review_required"
    gate_fams = _families(r["gate"]["review_required_reasons"])
    assert "role_resolution_review_required" in gate_fams
    assert r["gate"]["blocking_reasons"] == []


# ---------------------------------------------------------------------------
# d) Gap over threshold -> unresolved; lenient=review_required, strict=rejected
# ---------------------------------------------------------------------------


def test_gap_over_threshold_lenient(tmp_path: Path) -> None:
    """Open path with 50 mm gap (> 1.0 mm threshold): lenient -> preflight_review_required."""
    r = _run_pipeline(
        tmp_path,
        name="gap_over_thresh_lenient",
        entities=[
            # Valid outer so T5/T6 importer can pass
            {
                "layer": "CUT_OUTER",
                "type": "LWPOLYLINE",
                "closed": True,
                "points": [[0, 0], [100, 0], [100, 60], [0, 60]],
            },
            # CUT_INNER with a gap far over threshold (50 mm)
            {
                "layer": "CUT_INNER",
                "type": "LWPOLYLINE",
                "closed": False,
                "points": [[20, 20], [40, 20], [40, 30], [20, 30], [20, 70]],
            },
        ],
        gap_profile={"auto_repair_enabled": True, "max_gap_close_mm": 1.0},
        dedupe_profile=_REPAIR_ENABLED,
        # lenient defaults: strict_mode=False, interactive_review_on_ambiguity=True
    )

    # T3: gap over threshold -> remaining, review_required (not blocking in lenient)
    over_thresh = [
        c
        for c in r["gap"]["remaining_open_path_candidates"]
        if c.get("reason") == "gap_candidate_over_threshold"
    ]
    assert len(over_thresh) >= 1
    assert "gap_candidate_over_threshold" in _families(r["gap"]["review_required_candidates"])
    assert r["gap"]["blocking_conflicts"] == []

    # T6: review_required outcome
    assert r["gate"]["acceptance_outcome"] == "preflight_review_required"
    assert r["gate"]["blocking_reasons"] == []
    assert r["gate"]["importer_probe"]["is_pass"] is True


def test_gap_over_threshold_strict(tmp_path: Path) -> None:
    """Open path with 50 mm gap (> 1.0 mm threshold): strict -> preflight_rejected."""
    strict = {"strict_mode": True}
    r = _run_pipeline(
        tmp_path,
        name="gap_over_thresh_strict",
        entities=[
            {
                "layer": "CUT_OUTER",
                "type": "LWPOLYLINE",
                "closed": True,
                "points": [[0, 0], [100, 0], [100, 60], [0, 60]],
            },
            {
                "layer": "CUT_INNER",
                "type": "LWPOLYLINE",
                "closed": False,
                "points": [[20, 20], [40, 20], [40, 30], [20, 30], [20, 70]],
            },
        ],
        role_profile=strict,
        gap_profile={"auto_repair_enabled": True, "max_gap_close_mm": 1.0, "strict_mode": True},
        dedupe_profile={**_REPAIR_ENABLED, "strict_mode": True},
    )

    # T3: gap over threshold -> blocking in strict mode
    assert len(r["gap"]["blocking_conflicts"]) >= 1
    assert "gap_candidate_over_threshold" in _families(r["gap"]["blocking_conflicts"])

    # T6: rejected due to blocking conflict
    assert r["gate"]["acceptance_outcome"] == "preflight_rejected"
    gate_block_fams = _families(r["gate"]["blocking_reasons"])
    assert "gap_repair_blocking_conflict" in gate_block_fams


# ---------------------------------------------------------------------------
# e) Duplicate contour -> deduped then accepted
# ---------------------------------------------------------------------------


def test_duplicate_contour_deduped_accepted(tmp_path: Path) -> None:
    """Two identical CUT_OUTER rings: T4 dedupes to 1, accepted_for_import."""
    square = [[0, 0], [100, 0], [100, 60], [0, 60]]
    r = _run_pipeline(
        tmp_path,
        name="duplicate_contour",
        entities=[
            {"layer": "CUT_OUTER", "type": "LWPOLYLINE", "closed": True, "points": square},
            {"layer": "CUT_OUTER", "type": "LWPOLYLINE", "closed": True, "points": square},
        ],
        gap_profile=_REPAIR_ENABLED,
        dedupe_profile=_REPAIR_ENABLED,
    )

    # T1 inspect: exact duplicate fingerprint detected
    assert len(r["inspect"]["duplicate_contour_candidates"]) >= 1
    assert r["inspect"]["duplicate_contour_candidates"][0]["count"] == 2

    # T2 role: no conflicts (both closed, canonical layer)
    assert r["role"]["blocking_conflicts"] == []
    assert r["role"]["review_required_candidates"] == []

    # T4 dedupe: 1 keeper/drop group applied, 1 contour in working set
    assert len(r["dedupe"]["applied_duplicate_dedupes"]) >= 1
    assert len(r["dedupe"]["deduped_contour_working_set"]) == 1

    # T5 writer: exactly 1 CUT_OUTER contour (duplicates collapsed)
    assert r["writer"]["normalized_dxf"]["cut_contour_count"] == 1

    # T6 gate: clean pass - dedupe resolved the duplicate
    assert r["gate"]["acceptance_outcome"] == "accepted_for_import"
    assert r["gate"]["blocking_reasons"] == []
    assert r["gate"]["review_required_reasons"] == []


# ---------------------------------------------------------------------------
# f) Ambiguous gap partner -> lenient=review_required, strict=rejected
#
# Path A has a self-closing candidate (gap 0.4 mm) but path B's start endpoint
# is also within threshold, making path A's start endpoint non-exclusively
# paired -> ambiguous_gap_partner conflict.
# A valid closed outer is included so T5/T6 can produce a working artifact.
# ---------------------------------------------------------------------------


def test_ambiguous_gap_partner_lenient(tmp_path: Path) -> None:
    """Ambiguous gap partner: lenient -> preflight_review_required (not accepted)."""
    r = _run_pipeline(
        tmp_path,
        name="ambiguous_gap_lenient",
        entities=[
            # Valid closed outer so T5/T6 importer can pass
            {
                "layer": "CUT_OUTER",
                "type": "LWPOLYLINE",
                "closed": True,
                "points": [[-50, -50], [200, -50], [200, 150], [-50, 150]],
            },
            # Path A: self-closing gap 0.5 mm (within threshold 1.0 mm); B.start is
            # also within 1.0 mm of A's endpoints -> both partners exist -> ambiguous.
            # A.end=(0,0.5); B.start=(0,0.8): dist=0.3 mm > CHAIN_EPSILON(0.2) so the
            # importer does NOT chain A and B automatically.
            {
                "layer": "CUT_OUTER",
                "type": "LWPOLYLINE",
                "closed": False,
                "points": [[0, 0], [100, 0], [100, 60], [0, 60], [0, 0.5]],
            },
            # Path B: start=(0,0.8) is 0.8 mm from A.start and 0.3 mm from A.end;
            # both within 1.0 mm threshold -> creates ambiguity for path A's repair.
            {
                "layer": "CUT_OUTER",
                "type": "LWPOLYLINE",
                "closed": False,
                "points": [[0, 0.8], [50, 0], [50, 30], [0, 30]],
            },
        ],
        gap_profile={"auto_repair_enabled": True, "max_gap_close_mm": 1.0},
        dedupe_profile=_REPAIR_ENABLED,
    )

    # T3: ambiguous_gap_partner emitted (lenient -> review_required, not blocking)
    t3_rr_fams = _families(r["gap"]["review_required_candidates"])
    assert "ambiguous_gap_partner" in t3_rr_fams
    assert r["gap"]["blocking_conflicts"] == []

    # T6: not silently accepted
    assert r["gate"]["acceptance_outcome"] != "accepted_for_import"
    # Specifically review_required in lenient mode
    assert r["gate"]["acceptance_outcome"] == "preflight_review_required"


def test_ambiguous_gap_partner_strict(tmp_path: Path) -> None:
    """Ambiguous gap partner: strict -> preflight_rejected."""
    strict = {"strict_mode": True}
    r = _run_pipeline(
        tmp_path,
        name="ambiguous_gap_strict",
        entities=[
            {
                "layer": "CUT_OUTER",
                "type": "LWPOLYLINE",
                "closed": True,
                "points": [[-50, -50], [200, -50], [200, 150], [-50, 150]],
            },
            {
                "layer": "CUT_OUTER",
                "type": "LWPOLYLINE",
                "closed": False,
                "points": [[0, 0], [100, 0], [100, 60], [0, 60], [0, 0.5]],
            },
            {
                "layer": "CUT_OUTER",
                "type": "LWPOLYLINE",
                "closed": False,
                "points": [[0, 0.8], [50, 0], [50, 30], [0, 30]],
            },
        ],
        role_profile=strict,
        gap_profile={"auto_repair_enabled": True, "max_gap_close_mm": 1.0, "strict_mode": True},
        dedupe_profile={**_REPAIR_ENABLED, "strict_mode": True},
    )

    # T3: ambiguous_gap_partner -> blocking in strict mode
    assert "ambiguous_gap_partner" in _families(r["gap"]["blocking_conflicts"])

    # T6: rejected
    assert r["gate"]["acceptance_outcome"] == "preflight_rejected"
    assert "gap_repair_blocking_conflict" in _families(r["gate"]["blocking_reasons"])


# ---------------------------------------------------------------------------
# g) Conflicting layer-color role -> not silently accepted
#
# A non-canonical layer (CUSTOM_CUT) has entities with both a cut-color (1)
# and a marking-color (2) -> mixed_cut_and_marking_on_non_canonical_layer.
# In lenient mode: review_required.  In strict mode: blocking -> rejected.
# A valid CUT_OUTER entity is included to keep T5/T6 functional.
# ---------------------------------------------------------------------------


_CONFLICT_ENTITIES: list[dict[str, Any]] = [
    # Valid canonical outer so T5/T6 can produce a working artifact
    {
        "layer": "CUT_OUTER",
        "type": "LWPOLYLINE",
        "closed": True,
        "points": [[0, 0], [100, 0], [100, 60], [0, 60]],
    },
    # Non-canonical layer: entity with cut-color
    {
        "layer": "CUSTOM_CUT",
        "type": "LWPOLYLINE",
        "closed": True,
        "color_index": 1,
        "points": [[10, 10], [30, 10], [30, 20], [10, 20]],
    },
    # Non-canonical layer: entity with marking-color (same layer -> mixed conflict)
    {
        "layer": "CUSTOM_CUT",
        "type": "LINE",
        "closed": False,
        "color_index": 2,
        "points": [[5, 5], [50, 5]],
    },
]


def test_conflicting_layer_color_lenient_not_accepted(tmp_path: Path) -> None:
    """Non-canonical layer with cut+marking color: lenient -> review_required, not accepted."""
    r = _run_pipeline(
        tmp_path,
        name="color_conflict_lenient",
        entities=_CONFLICT_ENTITIES,
        role_profile={"cut_color_map": [1], "marking_color_map": [2]},
        gap_profile=_REPAIR_ENABLED,
        dedupe_profile=_REPAIR_ENABLED,
    )

    # T2: mixed_cut_and_marking_on_non_canonical_layer -> review_required (lenient)
    rr_fams = _families(r["role"]["review_required_candidates"])
    assert "mixed_cut_and_marking_on_non_canonical_layer" in rr_fams
    assert r["role"]["blocking_conflicts"] == []

    # T6: not silently accepted
    assert r["gate"]["acceptance_outcome"] != "accepted_for_import"
    assert r["gate"]["acceptance_outcome"] == "preflight_review_required"


def test_conflicting_layer_color_strict_rejected(tmp_path: Path) -> None:
    """Non-canonical layer with cut+marking color: strict -> preflight_rejected."""
    strict = {"strict_mode": True}
    r = _run_pipeline(
        tmp_path,
        name="color_conflict_strict",
        entities=_CONFLICT_ENTITIES,
        role_profile={"cut_color_map": [1], "marking_color_map": [2], "strict_mode": True},
        gap_profile={**_REPAIR_ENABLED, "strict_mode": True},
        dedupe_profile={**_REPAIR_ENABLED, "strict_mode": True},
    )

    # T2: mixed conflict -> blocking in strict mode
    block_fams = _families(r["role"]["blocking_conflicts"])
    assert "mixed_cut_and_marking_on_non_canonical_layer" in block_fams

    # T6: rejected
    assert r["gate"]["acceptance_outcome"] == "preflight_rejected"
    gate_block_fams = _families(r["gate"]["blocking_reasons"])
    assert "role_resolution_blocking_conflict" in gate_block_fams
