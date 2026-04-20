#!/usr/bin/env python3
"""DXF Prefilter E2-T7 -- diagnostics renderer smoke."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.dxf_preflight_acceptance_gate import evaluate_dxf_prefilter_acceptance_gate
from api.services.dxf_preflight_diagnostics_renderer import (
    render_dxf_preflight_diagnostics_summary,
)
from api.services.dxf_preflight_duplicate_dedupe import dedupe_dxf_duplicate_contours
from api.services.dxf_preflight_gap_repair import repair_dxf_gaps
from api.services.dxf_preflight_inspect import inspect_dxf_source
from api.services.dxf_preflight_normalized_dxf_writer import write_normalized_dxf
from api.services.dxf_preflight_role_resolver import resolve_dxf_roles

EXPECTED_TOP_LEVEL_KEYS: tuple[str, ...] = (
    "source_inventory_summary",
    "role_mapping_summary",
    "issue_summary",
    "repair_summary",
    "acceptance_summary",
    "artifact_references",
)

FORBIDDEN_TOP_LEVEL_KEYS: tuple[str, ...] = (
    "db_insert",
    "route",
    "upload_trigger",
    "api_response",
    "frontend_component",
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


def _run_t1_to_t7(
    *,
    tmpdir: Path,
    fixture_name: str,
    entities: list[dict[str, Any]],
    role_rules_profile: dict[str, Any] | None = None,
    gap_rules_profile: dict[str, Any] | None = None,
    dedupe_rules_profile: dict[str, Any] | None = None,
    writer_rules_profile: dict[str, Any] | None = None,
    mutate_output_artifact: bool = False,
) -> dict[str, Any]:
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

    if mutate_output_artifact:
        output_path.write_text("CORRUPTED_DXF_PAYLOAD", encoding="utf-8")

    acceptance_result = evaluate_dxf_prefilter_acceptance_gate(
        inspect_result,
        role_resolution,
        gap_result,
        dedupe_result,
        normalized_result,
    )

    return render_dxf_preflight_diagnostics_summary(
        inspect_result,
        role_resolution,
        gap_result,
        dedupe_result,
        normalized_result,
        acceptance_result,
    )


def _check_shape(result: dict[str, Any]) -> None:
    for key in EXPECTED_TOP_LEVEL_KEYS:
        _assert(key in result, f"missing top-level key: {key}")
    for key in FORBIDDEN_TOP_LEVEL_KEYS:
        _assert(key not in result, f"T7 renderer must not expose {key}")


def _families(records: list[dict[str, Any]]) -> list[str]:
    return [str(item.get("family", "")) for item in records]


def _scenario_accepted(tmpdir: Path) -> None:
    result = _run_t1_to_t7(
        tmpdir=tmpdir,
        fixture_name="accepted.json",
        entities=[_polyline_entity(layer="CUT_OUTER", points=_square())],
    )
    _check_shape(result)

    _assert(
        result["acceptance_summary"]["acceptance_outcome"] == "accepted_for_import",
        "expected accepted_for_import outcome",
    )
    _assert(
        result["issue_summary"]["blocking_issues"] == [],
        "accepted path must have empty blocking issue list",
    )
    refs = result["artifact_references"]
    normalized_ref = next((item for item in refs if item.get("artifact_kind") == "normalized_dxf"), None)
    _assert(normalized_ref is not None, "normalized_dxf artifact reference missing")
    _assert(bool(normalized_ref["exists"]) is True, "normalized_dxf artifact must exist")


def _scenario_review_required(tmpdir: Path) -> None:
    result = _run_t1_to_t7(
        tmpdir=tmpdir,
        fixture_name="review.json",
        entities=[
            _polyline_entity(layer="CUT_OUTER", points=_square()),
            {"layer": "SCRIBE_LAYER", "type": "TEXT", "closed": False, "color_index": 2},
        ],
        role_rules_profile={"marking_color_map": [2]},
    )
    _check_shape(result)

    _assert(
        result["acceptance_summary"]["acceptance_outcome"] == "preflight_review_required",
        "expected preflight_review_required outcome",
    )
    review_families = _families(result["issue_summary"]["review_required_issues"])
    _assert(
        "writer_skipped_source_entity" in review_families,
        "writer skipped entity should surface in review_required issues",
    )
    _assert(
        result["repair_summary"]["counts"]["remaining_review_required_signal_count"] >= 1,
        "review scenario should have at least one unresolved review signal",
    )


def _scenario_rejected(tmpdir: Path) -> None:
    result = _run_t1_to_t7(
        tmpdir=tmpdir,
        fixture_name="rejected.json",
        entities=[_polyline_entity(layer="CUT_OUTER", points=_square())],
        mutate_output_artifact=True,
    )
    _check_shape(result)

    _assert(
        result["acceptance_summary"]["acceptance_outcome"] == "preflight_rejected",
        "expected preflight_rejected outcome",
    )
    _assert(
        result["issue_summary"]["importer_highlight"]["is_pass"] is False,
        "rejected scenario should include importer failure highlight",
    )
    blocking_families = _families(result["issue_summary"]["blocking_issues"])
    _assert(
        "importer_probe_failed" in blocking_families,
        "importer probe failure must surface in blocking issues",
    )


def main() -> int:
    with tempfile.TemporaryDirectory(
        prefix="vrs_t7_diagnostics_renderer_smoke_"
    ) as tmp_dir_str:
        tmpdir = Path(tmp_dir_str)
        _scenario_accepted(tmpdir)
        _scenario_review_required(tmpdir)
        _scenario_rejected(tmpdir)

    print("[OK] DXF Prefilter E2-T7 diagnostics renderer smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
