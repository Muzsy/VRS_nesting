#!/usr/bin/env python3
"""DXF Prefilter E2-T3 -- gap repair smoke.

Deterministic smoke for the residual gap repair backend layer. It writes
minimal JSON fixture files to a temporary directory, runs the full
inspect → role-resolve → gap-repair chain, and verifies the contract for
each scenario.

Scenarios covered:

* GREEN PATH -- self-closing gap below threshold, unambiguous:
  auto-repair is applied, repaired_path_working_set grows, remaining empty.
* AUTO-REPAIR DISABLED -- all cut-like open paths become review candidates;
  no repair is applied.
* OVER-THRESHOLD GAP -- gap > max_gap_close_mm surfaces as review candidate
  with family ``gap_candidate_over_threshold``.
* MARKING-LIKE OPEN PATH -- marking-layer paths never enter the gap repair
  world; they produce no candidates and no conflicts.
* RULES PROFILE ECHO -- only the T3 minimum slice is reflected in
  ``rules_profile_echo``; out-of-scope keys land in
  ``diagnostics.rules_profile_source_fields_ignored``.
* OUTPUT SHAPE -- no acceptance, dedupe, writer or route world leaks in the
  T3 output.
* BRIDGE SOURCE MARKER -- applied repairs carry
  ``bridge_source='T3_residual_gap_repair'`` and ``reprobe_passed=True``.
* AMBIGUOUS PARTNER -- when an endpoint has more than one partner within
  threshold, the repair is review-required with family
  ``ambiguous_gap_partner``.

This smoke intentionally does NOT cover duplicate-dedupe (T4), normalized DXF
writer (T5), or acceptance gate (T6) -- those are out of T3 scope.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.dxf_preflight_gap_repair import repair_dxf_gaps
from api.services.dxf_preflight_inspect import inspect_dxf_source
from api.services.dxf_preflight_role_resolver import resolve_dxf_roles


# ---------------------------------------------------------------------------
# Expected output shape
# ---------------------------------------------------------------------------

EXPECTED_TOP_LEVEL_KEYS: tuple[str, ...] = (
    "rules_profile_echo",
    "repair_candidate_inventory",
    "applied_gap_repairs",
    "repaired_path_working_set",
    "remaining_open_path_candidates",
    "review_required_candidates",
    "blocking_conflicts",
    "diagnostics",
)

FORBIDDEN_TOP_LEVEL_KEYS: tuple[str, ...] = (
    # Acceptance world (T6)
    "accepted_for_import",
    "acceptance",
    "acceptance_outcome",
    "preflight_rejected",
    # Dedupe world (T4)
    "deduplicated",
    "duplicate_report",
    # Writer world (T5)
    "normalized_dxf",
    "normalized_source",
    # Persistence / route world
    "db_insert",
    "route",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assert(cond: bool, message: str) -> None:
    if not cond:
        raise AssertionError(message)


def _write_fixture(path: Path, entities: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps({"entities": entities}), encoding="utf-8")


def _run_chain(
    entities: list[dict[str, Any]],
    tmpdir: Path,
    fixture_name: str,
    *,
    rules_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fixture_path = tmpdir / fixture_name
    _write_fixture(fixture_path, entities)
    inspect_result = inspect_dxf_source(fixture_path)
    role_resolution = resolve_dxf_roles(inspect_result, rules_profile=rules_profile)
    return repair_dxf_gaps(inspect_result, role_resolution, rules_profile=rules_profile)


def _check_shape(result: dict[str, Any]) -> None:
    for key in EXPECTED_TOP_LEVEL_KEYS:
        _assert(key in result, f"missing top-level key: {key}")
    for forbidden in FORBIDDEN_TOP_LEVEL_KEYS:
        _assert(
            forbidden not in result,
            f"T3 gap repair must not expose '{forbidden}'",
        )


def _make_almost_ring(*, gap_mm: float) -> list[dict[str, Any]]:
    """4 LINE segments forming almost-closed 10×10 square with ``gap_mm`` gap."""
    return [
        {"layer": "CUT_OUTER", "type": "LINE", "points": [[0.0, 0.0], [10.0, 0.0]]},
        {"layer": "CUT_OUTER", "type": "LINE", "points": [[10.0, 0.0], [10.0, 10.0]]},
        {"layer": "CUT_OUTER", "type": "LINE", "points": [[10.0, 10.0], [0.0, 10.0]]},
        {"layer": "CUT_OUTER", "type": "LINE", "points": [[0.0, 10.0], [0.0, gap_mm]]},
    ]


def _families(records: list[dict[str, Any]]) -> list[str]:
    return [r["family"] for r in records]


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


def _scenario_output_shape(tmpdir: Path) -> None:
    """Basic output shape check -- all expected keys present, forbidden absent."""
    entities = _make_almost_ring(gap_mm=0.5)
    result = _run_chain(
        entities, tmpdir, "shape.json",
        rules_profile={"auto_repair_enabled": True, "max_gap_close_mm": 2.0},
    )
    _check_shape(result)


def _scenario_green_path_auto_repair(tmpdir: Path) -> None:
    """Self-closing gap < threshold, unambiguous → repair applied."""
    entities = _make_almost_ring(gap_mm=0.5)
    result = _run_chain(
        entities, tmpdir, "green.json",
        rules_profile={"auto_repair_enabled": True, "max_gap_close_mm": 2.0},
    )
    _check_shape(result)

    _assert(
        len(result["applied_gap_repairs"]) == 1,
        f"expected 1 applied repair, got {len(result['applied_gap_repairs'])}",
    )
    repair = result["applied_gap_repairs"][0]
    _assert(repair["bridge_source"] == "T3_residual_gap_repair", "bridge_source must be T3_residual_gap_repair")
    _assert(repair["reprobe_passed"] is True, "reprobe must pass for unambiguous self-closing gap")
    _assert(repair["repair_type"] == "self_closing", "repair_type must be self_closing")

    _assert(
        len(result["repaired_path_working_set"]) == 1,
        f"expected 1 repaired path, got {len(result['repaired_path_working_set'])}",
    )
    repaired = result["repaired_path_working_set"][0]
    _assert(repaired["canonical_role"] == "CUT_OUTER", "repaired path must carry canonical_role")
    _assert(repaired["source"] == "T3_gap_repair", "repaired path source must be T3_gap_repair")

    _assert(
        len(result["remaining_open_path_candidates"]) == 0,
        f"no remaining open paths expected after successful repair, got {result['remaining_open_path_candidates']}",
    )


def _scenario_auto_repair_disabled(tmpdir: Path) -> None:
    """auto_repair_enabled=False → all open paths become review candidates, no repairs."""
    entities = _make_almost_ring(gap_mm=0.5)
    result = _run_chain(
        entities, tmpdir, "disabled.json",
        rules_profile={"auto_repair_enabled": False, "max_gap_close_mm": 2.0},
    )
    _check_shape(result)

    _assert(
        len(result["applied_gap_repairs"]) == 0,
        "auto_repair_enabled=False must produce no applied repairs",
    )
    _assert(
        len(result["repaired_path_working_set"]) == 0,
        "auto_repair_enabled=False must produce no repaired_path_working_set entries",
    )
    families = _families(result["review_required_candidates"])
    _assert(
        "gap_repair_disabled_by_profile" in families,
        f"expected gap_repair_disabled_by_profile in review_required_candidates, got {families}",
    )
    _assert(
        len(result["remaining_open_path_candidates"]) >= 1,
        "auto_repair_enabled=False must leave open paths as remaining",
    )


def _scenario_over_threshold(tmpdir: Path) -> None:
    """Gap > max_gap_close_mm → gap_candidate_over_threshold, no repair applied."""
    entities = _make_almost_ring(gap_mm=3.0)
    result = _run_chain(
        entities, tmpdir, "overthreshold.json",
        rules_profile={"auto_repair_enabled": True, "max_gap_close_mm": 2.0},
    )
    _check_shape(result)

    _assert(
        len(result["applied_gap_repairs"]) == 0,
        "over-threshold gap must not be repaired",
    )
    families = _families(result["review_required_candidates"])
    _assert(
        "gap_candidate_over_threshold" in families,
        f"expected gap_candidate_over_threshold, got {families}",
    )
    _assert(
        len(result["remaining_open_path_candidates"]) >= 1,
        "over-threshold open path must remain as candidate",
    )


def _scenario_marking_like_no_repair(tmpdir: Path) -> None:
    """MARKING-layer open path → T3 produces no gap candidates, no conflicts."""
    entities = [
        {"layer": "MARKING", "type": "LINE", "points": [[0.0, 0.0], [5.0, 5.0]]},
    ]
    result = _run_chain(
        entities, tmpdir, "marking.json",
        rules_profile={"auto_repair_enabled": True, "max_gap_close_mm": 2.0},
    )
    _check_shape(result)

    _assert(
        result["applied_gap_repairs"] == [],
        "marking-layer open path must not receive any gap repair",
    )
    _assert(
        result["repair_candidate_inventory"] == [],
        "marking-layer open path must not appear in repair_candidate_inventory",
    )
    _assert(
        result["review_required_candidates"] == [],
        "marking-layer open path must not produce review_required_candidates in T3",
    )
    _assert(
        result["blocking_conflicts"] == [],
        "marking-layer open path must not produce blocking_conflicts in T3",
    )
    _assert(
        result["remaining_open_path_candidates"] == [],
        "marking-layer open path must not appear in remaining_open_path_candidates",
    )


def _scenario_rules_profile_echo_only_t3_minimum(tmpdir: Path) -> None:
    """rules_profile_echo must contain only the T3 minimum slice."""
    entities = _make_almost_ring(gap_mm=0.5)
    result = _run_chain(
        entities, tmpdir, "profileecho.json",
        rules_profile={
            "auto_repair_enabled": True,
            "max_gap_close_mm": 1.0,
            "strict_mode": False,
            "interactive_review_on_ambiguity": True,
            # Out-of-scope T2/other fields
            "cut_color_map": [4],
            "marking_color_map": [],
            "metadata_jsonb": {"unrelated": True},
        },
    )
    _check_shape(result)

    echo_keys = set(result["rules_profile_echo"].keys())
    _assert(
        echo_keys == {"auto_repair_enabled", "max_gap_close_mm", "strict_mode", "interactive_review_on_ambiguity"},
        f"rules_profile_echo must contain only T3 minimum slice, got {sorted(echo_keys)}",
    )

    ignored = set(result["diagnostics"]["rules_profile_source_fields_ignored"])
    _assert(
        {"cut_color_map", "marking_color_map", "metadata_jsonb"} <= ignored,
        f"out-of-scope fields must appear in rules_profile_source_fields_ignored, got {sorted(ignored)}",
    )


def _scenario_ambiguous_partner(tmpdir: Path) -> None:
    """Endpoint with >1 partner within threshold → ambiguous_gap_partner, no auto-repair."""
    # Almost-ring: start=(0,0), end=(0,0.5) — 0.5mm self-closing gap.
    # Extra path: start=(0,0.8) — 0.8mm from ring start, 0.3mm from ring end (>epsilon, won't chain).
    # Ring start now has 2 partners within 2.0mm threshold: ring end AND extra path start → ambiguous.
    entities: list[dict[str, Any]] = [
        {"layer": "CUT_OUTER", "type": "LINE", "points": [[0.0, 0.0], [10.0, 0.0]]},
        {"layer": "CUT_OUTER", "type": "LINE", "points": [[10.0, 0.0], [10.0, 10.0]]},
        {"layer": "CUT_OUTER", "type": "LINE", "points": [[10.0, 10.0], [0.0, 10.0]]},
        {"layer": "CUT_OUTER", "type": "LINE", "points": [[0.0, 10.0], [0.0, 0.5]]},
        # start=(0,0.8) is 0.3mm from ring end=(0,0.5) → won't chain (>0.2mm)
        # but 0.8mm from ring start=(0,0) → within 2.0mm → creates ambiguity
        {"layer": "CUT_OUTER", "type": "LINE", "points": [[0.0, 0.8], [10.0, 10.0]]},
    ]
    result = _run_chain(
        entities, tmpdir, "ambiguous.json",
        rules_profile={"auto_repair_enabled": True, "max_gap_close_mm": 2.0},
    )
    _check_shape(result)

    _assert(
        len(result["applied_gap_repairs"]) == 0,
        "ambiguous endpoint must not trigger auto-repair",
    )

    all_review_families = _families(result["review_required_candidates"])
    all_blocking_families = _families(result["blocking_conflicts"])
    _assert(
        "ambiguous_gap_partner" in all_review_families or "ambiguous_gap_partner" in all_blocking_families,
        f"expected ambiguous_gap_partner, got review={all_review_families} blocking={all_blocking_families}",
    )


def _scenario_no_acceptance_outcome_no_dxf_artifact(tmpdir: Path) -> None:
    """T3 must not emit acceptance outcome or DXF artifact fields."""
    entities = _make_almost_ring(gap_mm=0.5)
    result = _run_chain(
        entities, tmpdir, "noleak.json",
        rules_profile={"auto_repair_enabled": True, "max_gap_close_mm": 2.0},
    )
    for forbidden in FORBIDDEN_TOP_LEVEL_KEYS:
        _assert(forbidden not in result, f"T3 must not expose '{forbidden}'")


def _scenario_importer_vs_t3_separation_in_diagnostics(tmpdir: Path) -> None:
    """diagnostics notes must explicitly separate importer chaining from T3 repair."""
    entities = _make_almost_ring(gap_mm=0.5)
    result = _run_chain(
        entities, tmpdir, "diag.json",
        rules_profile={"auto_repair_enabled": True, "max_gap_close_mm": 2.0},
    )
    notes = " ".join(result["diagnostics"]["notes"])
    _assert(
        "importer_chaining_truth" in notes,
        "diagnostics must name the importer chaining truth separation",
    )
    _assert(
        "T3_repair_layer" in notes,
        "diagnostics must name the T3 repair layer separation",
    )
    _assert(
        "T4_scope" in notes or "T5_scope" in notes or "T6_scope" in notes,
        "diagnostics must name what remains for downstream lanes",
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def main() -> int:
    with tempfile.TemporaryDirectory() as _tmp:
        tmpdir = Path(_tmp)

        _scenario_output_shape(tmpdir)
        _scenario_green_path_auto_repair(tmpdir)
        _scenario_auto_repair_disabled(tmpdir)
        _scenario_over_threshold(tmpdir)
        _scenario_marking_like_no_repair(tmpdir)
        _scenario_rules_profile_echo_only_t3_minimum(tmpdir)
        _scenario_ambiguous_partner(tmpdir)
        _scenario_no_acceptance_outcome_no_dxf_artifact(tmpdir)
        _scenario_importer_vs_t3_separation_in_diagnostics(tmpdir)

    print("[OK] DXF Prefilter E2-T3 gap repair smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
