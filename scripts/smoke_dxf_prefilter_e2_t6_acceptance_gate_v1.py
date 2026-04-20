#!/usr/bin/env python3
"""DXF Prefilter E2-T6 -- acceptance gate smoke."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.dxf_preflight_acceptance_gate import (
    evaluate_dxf_prefilter_acceptance_gate,
)
from api.services.dxf_preflight_duplicate_dedupe import dedupe_dxf_duplicate_contours
from api.services.dxf_preflight_gap_repair import repair_dxf_gaps
from api.services.dxf_preflight_inspect import inspect_dxf_source
from api.services.dxf_preflight_normalized_dxf_writer import write_normalized_dxf
from api.services.dxf_preflight_role_resolver import resolve_dxf_roles

EXPECTED_TOP_LEVEL_KEYS: tuple[str, ...] = (
    "acceptance_outcome",
    "normalized_dxf_echo",
    "importer_probe",
    "validator_probe",
    "blocking_reasons",
    "review_required_reasons",
    "diagnostics",
)

FORBIDDEN_TOP_LEVEL_KEYS: tuple[str, ...] = (
    "db_insert",
    "route",
    "upload_trigger",
    "feature_flag",
)


def _assert(cond: bool, message: str) -> None:
    if not cond:
        raise AssertionError(message)


def _write_fixture(path: Path, entities: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps({"entities": entities}), encoding="utf-8")


def _square(*, size: float = 10.0, x: float = 0.0, y: float = 0.0) -> list[list[float]]:
    return [[x, y], [x + size, y], [x + size, y + size], [x, y + size]]


def _polyline_entity(*, layer: str, points: list[list[float]]) -> dict[str, Any]:
    return {"layer": layer, "type": "LWPOLYLINE", "closed": True, "points": points}


def _run_t1_to_t5(
    *,
    tmpdir: Path,
    fixture_name: str,
    entities: list[dict[str, Any]],
    role_rules_profile: dict[str, Any] | None = None,
    gap_rules_profile: dict[str, Any] | None = None,
    dedupe_rules_profile: dict[str, Any] | None = None,
    writer_rules_profile: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], Path]:
    fixture_path = tmpdir / fixture_name
    _write_fixture(fixture_path, entities)

    inspect_result = inspect_dxf_source(fixture_path)
    role_resolution = resolve_dxf_roles(inspect_result, rules_profile=role_rules_profile)
    gap_result = repair_dxf_gaps(inspect_result, role_resolution, rules_profile=gap_rules_profile)
    dedupe_result = dedupe_dxf_duplicate_contours(
        inspect_result,
        role_resolution,
        gap_result,
        rules_profile=dedupe_rules_profile,
    )
    output_path = tmpdir / f"{fixture_path.stem}.normalized.dxf"
    normalized_result = write_normalized_dxf(
        inspect_result,
        role_resolution,
        gap_result,
        dedupe_result,
        output_path=output_path,
        rules_profile=writer_rules_profile,
    )
    return inspect_result, role_resolution, gap_result, dedupe_result, normalized_result, output_path


def _run_t6(
    *,
    inspect_result: dict[str, Any],
    role_resolution: dict[str, Any],
    gap_result: dict[str, Any],
    dedupe_result: dict[str, Any],
    normalized_result: dict[str, Any],
) -> dict[str, Any]:
    return evaluate_dxf_prefilter_acceptance_gate(
        inspect_result,
        role_resolution,
        gap_result,
        dedupe_result,
        normalized_result,
    )


def _check_shape(result: dict[str, Any]) -> None:
    for key in EXPECTED_TOP_LEVEL_KEYS:
        _assert(key in result, f"missing top-level key: {key}")
    for forbidden in FORBIDDEN_TOP_LEVEL_KEYS:
        _assert(forbidden not in result, f"T6 gate must not expose {forbidden}")


def _families(records: list[dict[str, Any]]) -> list[str]:
    return [str(item.get("family", "")) for item in records]


def _scenario_accepted_for_import(tmpdir: Path) -> None:
    inspect_result, role_resolution, gap_result, dedupe_result, normalized_result, output_path = _run_t1_to_t5(
        tmpdir=tmpdir,
        fixture_name="accepted.json",
        entities=[_polyline_entity(layer="CUT_OUTER", points=_square())],
    )

    _assert(output_path.is_file(), "normalized artifact must exist before T6")
    result = _run_t6(
        inspect_result=inspect_result,
        role_resolution=role_resolution,
        gap_result=gap_result,
        dedupe_result=dedupe_result,
        normalized_result=normalized_result,
    )
    _check_shape(result)

    _assert(result["acceptance_outcome"] == "accepted_for_import", "expected accepted_for_import outcome")
    _assert(result["importer_probe"]["is_pass"] is True, "importer probe must pass")
    _assert(result["validator_probe"]["status"] == "validated", "validator probe must be validated")
    _assert(result["blocking_reasons"] == [], "accepted path must have no blocking reasons")
    _assert(result["review_required_reasons"] == [], "accepted path must have no review-required reasons")


def _scenario_review_required(tmpdir: Path) -> None:
    inspect_result, role_resolution, gap_result, dedupe_result, normalized_result, _output_path = _run_t1_to_t5(
        tmpdir=tmpdir,
        fixture_name="review.json",
        entities=[
            _polyline_entity(layer="CUT_OUTER", points=_square()),
            {"layer": "SCRIBE_LAYER", "type": "TEXT", "closed": False, "color_index": 2},
        ],
        role_rules_profile={"marking_color_map": [2]},
    )

    result = _run_t6(
        inspect_result=inspect_result,
        role_resolution=role_resolution,
        gap_result=gap_result,
        dedupe_result=dedupe_result,
        normalized_result=normalized_result,
    )
    _check_shape(result)

    _assert(result["acceptance_outcome"] == "preflight_review_required", "expected review-required outcome")
    _assert(result["importer_probe"]["is_pass"] is True, "review path importer should still pass")
    _assert(result["validator_probe"]["status"] == "validated", "review path validator should still pass")
    _assert(
        "writer_skipped_source_entity" in _families(result["review_required_reasons"]),
        "writer skipped entity must surface as review-required reason",
    )


def _scenario_rejected_importer_fail(tmpdir: Path) -> None:
    inspect_result, role_resolution, gap_result, dedupe_result, normalized_result, output_path = _run_t1_to_t5(
        tmpdir=tmpdir,
        fixture_name="rejected.json",
        entities=[_polyline_entity(layer="CUT_OUTER", points=_square())],
    )

    # Simulate post-writer artifact corruption; T6 must reject on importer probe.
    output_path.write_text("CORRUPTED_DXF_PAYLOAD", encoding="utf-8")

    result = _run_t6(
        inspect_result=inspect_result,
        role_resolution=role_resolution,
        gap_result=gap_result,
        dedupe_result=dedupe_result,
        normalized_result=normalized_result,
    )
    _check_shape(result)

    _assert(result["acceptance_outcome"] == "preflight_rejected", "expected rejected outcome")
    _assert(result["importer_probe"]["is_pass"] is False, "importer probe must fail on corrupted artifact")
    _assert(
        "importer_probe_failed" in _families(result["blocking_reasons"]),
        "importer failure must be reflected in blocking reasons",
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="vrs_t6_acceptance_gate_smoke_") as tmp_dir_str:
        tmpdir = Path(tmp_dir_str)
        _scenario_accepted_for_import(tmpdir)
        _scenario_review_required(tmpdir)
        _scenario_rejected_importer_fail(tmpdir)

    print("[OK] DXF Prefilter E2-T6 acceptance gate smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
