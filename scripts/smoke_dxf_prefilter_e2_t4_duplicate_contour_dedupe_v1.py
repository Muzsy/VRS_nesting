#!/usr/bin/env python3
"""DXF Prefilter E2-T4 -- duplicate contour dedupe smoke.

Deterministic smoke for the duplicate-dedupe backend layer.
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

from api.services.dxf_preflight_duplicate_dedupe import dedupe_dxf_duplicate_contours
from api.services.dxf_preflight_inspect import inspect_dxf_source
from api.services.dxf_preflight_role_resolver import resolve_dxf_roles

EXPECTED_TOP_LEVEL_KEYS: tuple[str, ...] = (
    "rules_profile_echo",
    "closed_contour_inventory",
    "duplicate_candidate_inventory",
    "applied_duplicate_dedupes",
    "deduped_contour_working_set",
    "remaining_duplicate_candidates",
    "review_required_candidates",
    "blocking_conflicts",
    "diagnostics",
)

FORBIDDEN_TOP_LEVEL_KEYS: tuple[str, ...] = (
    "accepted_for_import",
    "acceptance",
    "acceptance_outcome",
    "preflight_rejected",
    "normalized_dxf",
    "dxf_artifact",
)


def _assert(cond: bool, message: str) -> None:
    if not cond:
        raise AssertionError(message)


def _write_fixture(path: Path, entities: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps({"entities": entities}), encoding="utf-8")


def _base_square(*, size: float = 10.0, x: float = 0.0, y: float = 0.0) -> list[list[float]]:
    return [[x, y], [x + size, y], [x + size, y + size], [x, y + size]]


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


def _gap_result(repaired_paths: list[dict[str, Any]] | None = None) -> dict[str, Any]:
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
    tmpdir: Path,
    fixture_name: str,
    entities: list[dict[str, Any]],
    rules_profile: dict[str, Any] | None = None,
    repaired_paths: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    fixture_path = tmpdir / fixture_name
    _write_fixture(fixture_path, entities)

    inspect_result = inspect_dxf_source(fixture_path)
    role_resolution = resolve_dxf_roles(inspect_result)
    result = dedupe_dxf_duplicate_contours(
        inspect_result,
        role_resolution,
        _gap_result(repaired_paths),
        rules_profile=rules_profile,
    )
    return result, inspect_result


def _check_shape(result: dict[str, Any]) -> None:
    for key in EXPECTED_TOP_LEVEL_KEYS:
        _assert(key in result, f"missing top-level key: {key}")
    for key in FORBIDDEN_TOP_LEVEL_KEYS:
        _assert(key not in result, f"T4 must not expose {key}")


def _families(records: list[dict[str, Any]]) -> list[str]:
    return [str(item.get("family", "")) for item in records]


def _scenario_exact_signal_vs_t4_keeper_drop(tmpdir: Path) -> None:
    entities = [
        _polyline_entity(layer="CUT_OUTER", points=_base_square()),
        _polyline_entity(layer="CUT_OUTER", points=_base_square()),
    ]
    result, inspect_result = _run_chain(
        tmpdir=tmpdir,
        fixture_name="exact.json",
        entities=entities,
        rules_profile={
            "auto_repair_enabled": True,
            "duplicate_contour_merge_tolerance_mm": 0.05,
        },
    )
    _check_shape(result)

    _assert(len(inspect_result["duplicate_contour_candidates"]) == 1, "inspect exact duplicate signal missing")
    _assert(result["diagnostics"]["inspect_exact_duplicate_signal_count"] == 1, "diagnostics must carry inspect exact duplicate count")
    _assert(len(result["applied_duplicate_dedupes"]) == 1, "T4 must apply one dedupe group")
    _assert(len(result["deduped_contour_working_set"]) == 1, "one keeper expected after dedupe")


def _scenario_tolerance_noise_dedupe(tmpdir: Path) -> None:
    entities = [
        _polyline_entity(layer="CUT_OUTER", points=_base_square()),
        _polyline_entity(layer="CUT_OUTER", points=_noisy_square(epsilon=0.01)),
    ]
    result, _inspect_result = _run_chain(
        tmpdir=tmpdir,
        fixture_name="noise.json",
        entities=entities,
        rules_profile={
            "auto_repair_enabled": True,
            "duplicate_contour_merge_tolerance_mm": 0.02,
        },
    )
    _check_shape(result)

    _assert(len(result["applied_duplicate_dedupes"]) == 1, "noise duplicate should dedupe within tolerance")


def _scenario_over_tolerance_review(tmpdir: Path) -> None:
    entities = [
        _polyline_entity(layer="CUT_OUTER", points=_base_square()),
        _polyline_entity(layer="CUT_OUTER", points=_noisy_square(epsilon=0.015)),
    ]
    result, _inspect_result = _run_chain(
        tmpdir=tmpdir,
        fixture_name="over_tol.json",
        entities=entities,
        rules_profile={
            "auto_repair_enabled": True,
            "duplicate_contour_merge_tolerance_mm": 0.01,
        },
    )
    _check_shape(result)

    _assert(len(result["applied_duplicate_dedupes"]) == 0, "over-threshold pair must not auto-dedupe")
    _assert(
        "duplicate_candidate_over_tolerance" in _families(result["review_required_candidates"]),
        "over-threshold duplicate must be surfaced as review_required",
    )


def _scenario_original_vs_t3_repaired_keeper_policy(tmpdir: Path) -> None:
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
    result, _inspect_result = _run_chain(
        tmpdir=tmpdir,
        fixture_name="orig_vs_t3.json",
        entities=entities,
        repaired_paths=repaired_paths,
        rules_profile={
            "auto_repair_enabled": True,
            "duplicate_contour_merge_tolerance_mm": 0.05,
        },
    )
    _check_shape(result)

    _assert(len(result["applied_duplicate_dedupes"]) == 1, "original-vs-T3 pair must be deduped")
    keeper = result["applied_duplicate_dedupes"][0]["keeper"]
    _assert(keeper["source"] == "importer_probe", "keeper policy must prefer importer-probe over T3_gap_repair")


def _scenario_cross_role_blocking(tmpdir: Path) -> None:
    base = _base_square()
    entities = [
        _polyline_entity(layer="CUT_OUTER", points=base),
        _polyline_entity(layer="CUT_INNER", points=base),
    ]
    result, _inspect_result = _run_chain(
        tmpdir=tmpdir,
        fixture_name="cross_role.json",
        entities=entities,
        rules_profile={
            "auto_repair_enabled": True,
            "duplicate_contour_merge_tolerance_mm": 0.05,
            "strict_mode": True,
            "interactive_review_on_ambiguity": True,
        },
    )
    _check_shape(result)

    _assert(len(result["applied_duplicate_dedupes"]) == 0, "cross-role duplicate must not be silently merged")
    _assert(
        "duplicate_cross_role_conflict" in _families(result["blocking_conflicts"]),
        "strict mode must route cross-role duplicate to blocking",
    )


def _scenario_auto_repair_disabled(tmpdir: Path) -> None:
    entities = [
        _polyline_entity(layer="CUT_OUTER", points=_base_square()),
        _polyline_entity(layer="CUT_OUTER", points=_base_square()),
    ]
    result, _inspect_result = _run_chain(
        tmpdir=tmpdir,
        fixture_name="disabled.json",
        entities=entities,
        rules_profile={
            "auto_repair_enabled": False,
            "duplicate_contour_merge_tolerance_mm": 0.05,
        },
    )
    _check_shape(result)

    families = _families(result["review_required_candidates"])
    _assert("duplicate_dedupe_disabled_by_profile" in families, "disabled profile family missing")
    _assert("cut_like_duplicate_remaining_after_dedupe" in families, "remaining duplicate family missing")


def _scenario_marking_not_silent_dedupe(tmpdir: Path) -> None:
    entities = [_polyline_entity(layer="CUT_OUTER", points=_base_square())]
    mark = _base_square(size=5.0, x=20.0, y=20.0)
    repaired_paths = [
        {
            "layer": "MARKING",
            "canonical_role": "MARKING",
            "source": "T3_gap_repair",
            "point_count": 5,
            "points": mark + [mark[0]],
        },
        {
            "layer": "MARKING",
            "canonical_role": "MARKING",
            "source": "T3_gap_repair",
            "point_count": 5,
            "points": mark + [mark[0]],
        },
    ]
    result, _inspect_result = _run_chain(
        tmpdir=tmpdir,
        fixture_name="marking.json",
        entities=entities,
        repaired_paths=repaired_paths,
        rules_profile={
            "auto_repair_enabled": True,
            "duplicate_contour_merge_tolerance_mm": 0.05,
        },
    )
    _check_shape(result)

    _assert(len(result["applied_duplicate_dedupes"]) == 0, "marking world must not be auto-deduped in cut-like T4 scope")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="vrs_t4_duplicate_dedupe_smoke_") as tmp_dir_str:
        tmpdir = Path(tmp_dir_str)
        _scenario_exact_signal_vs_t4_keeper_drop(tmpdir)
        _scenario_tolerance_noise_dedupe(tmpdir)
        _scenario_over_tolerance_review(tmpdir)
        _scenario_original_vs_t3_repaired_keeper_policy(tmpdir)
        _scenario_cross_role_blocking(tmpdir)
        _scenario_auto_repair_disabled(tmpdir)
        _scenario_marking_not_silent_dedupe(tmpdir)

    print("[OK] DXF Prefilter E2-T4 duplicate contour dedupe smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
