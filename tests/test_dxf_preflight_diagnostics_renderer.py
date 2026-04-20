#!/usr/bin/env python3
"""DXF Prefilter E2-T7 -- diagnostics renderer unit tests."""

from __future__ import annotations

import builtins
from pathlib import Path
from typing import Any

import pytest

from api.services.dxf_preflight_diagnostics_renderer import (
    DxfPreflightDiagnosticsRendererError,
    render_dxf_preflight_diagnostics_summary,
)

EXPECTED_TOP_LEVEL_KEYS = {
    "source_inventory_summary",
    "role_mapping_summary",
    "issue_summary",
    "repair_summary",
    "acceptance_summary",
    "artifact_references",
}

FORBIDDEN_TOP_LEVEL_KEYS = {
    "db_insert",
    "route",
    "upload_trigger",
    "api_response",
    "frontend_component",
}


def _write_json_fixture(path: Path) -> None:
    path.write_text('{"entities":[]}', encoding="utf-8")


def _base_inputs(tmp_path: Path) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    source_path = tmp_path / "source_fixture.json"
    normalized_path = tmp_path / "normalized_output.dxf"
    _write_json_fixture(source_path)
    normalized_path.write_text("normalized-placeholder", encoding="utf-8")

    inspect_result = {
        "source_path": str(source_path.resolve()),
        "backend": "json",
        "source_size_bytes": source_path.stat().st_size,
        "entity_inventory": [
            {"entity_index": 0, "layer": "CUT_OUTER", "type": "LWPOLYLINE"},
            {"entity_index": 1, "layer": "SCRIBE", "type": "TEXT"},
        ],
        "layer_inventory": [
            {"layer": "CUT_OUTER", "entity_count": 1},
            {"layer": "SCRIBE", "entity_count": 1},
        ],
        "color_inventory": [
            {"color_index": 1, "count": 1},
            {"color_index": 2, "count": 1},
        ],
        "linetype_inventory": [{"linetype_name": "CONTINUOUS", "count": 2}],
        "contour_candidates": [{"layer": "CUT_OUTER", "ring_index": 0}],
        "open_path_candidates": [{"layer": "CUT_OUTER", "open_path_count": 1}],
        "duplicate_contour_candidates": [],
        "outer_like_candidates": [{"layer": "CUT_OUTER"}],
        "inner_like_candidates": [],
        "diagnostics": {
            "probe_errors": [
                {
                    "family": "inspect_probe_warning",
                    "code": "INSPECT_PROBE_WARNING",
                    "message": "recoverable inspect warning",
                }
            ],
            "notes": ["inspect-note"],
        },
    }

    role_resolution = {
        "rules_profile_echo": {"strict_mode": False},
        "layer_role_assignments": [
            {"layer": "CUT_OUTER", "canonical_role": "CUT_OUTER"},
            {"layer": "SCRIBE", "canonical_role": "MARKING"},
        ],
        "entity_role_assignments": [],
        "resolved_role_inventory": {
            "CUT_OUTER": 1,
            "CUT_INNER": 0,
            "MARKING": 1,
            "UNASSIGNED": 0,
        },
        "review_required_candidates": [],
        "blocking_conflicts": [],
        "diagnostics": {"notes": []},
    }

    gap_repair_result = {
        "rules_profile_echo": {"auto_repair_enabled": True},
        "repair_candidate_inventory": [],
        "applied_gap_repairs": [
            {
                "family": "gap_candidate_self_closing",
                "layer": "CUT_OUTER",
                "path_a_index": 0,
                "path_b_index": 0,
            }
        ],
        "repaired_path_working_set": [],
        "remaining_open_path_candidates": [],
        "review_required_candidates": [],
        "blocking_conflicts": [],
        "diagnostics": {"notes": ["gap-note"], "source_load_error": None},
    }

    duplicate_dedupe_result = {
        "rules_profile_echo": {"auto_repair_enabled": True},
        "closed_contour_inventory": [],
        "duplicate_candidate_inventory": [],
        "applied_duplicate_dedupes": [
            {
                "group_id": "duplicate_group_0",
                "keeper": {"contour_id": "orig:CUT_OUTER:0"},
                "dropped": [{"contour": {"contour_id": "orig:CUT_OUTER:1"}}],
            }
        ],
        "deduped_contour_working_set": [],
        "remaining_duplicate_candidates": [],
        "review_required_candidates": [],
        "blocking_conflicts": [],
        "diagnostics": {"notes": ["dedupe-note"], "source_load_error": None},
    }

    normalized_dxf_writer_result = {
        "rules_profile_echo": {},
        "normalized_dxf": {
            "output_path": str(normalized_path.resolve()),
            "writer_backend": "ezdxf",
            "written_layers": ["CUT_OUTER", "MARKING"],
            "written_entity_count": 2,
            "cut_contour_count": 1,
            "marking_entity_count": 1,
        },
        "writer_layer_inventory": [],
        "skipped_source_entities": [],
        "diagnostics": {"notes": ["writer-note"]},
    }

    acceptance_gate_result = {
        "acceptance_outcome": "accepted_for_import",
        "normalized_dxf_echo": {},
        "importer_probe": {
            "is_pass": True,
            "error_code": None,
            "error_message": None,
            "outer_point_count": 4,
            "hole_count": 0,
            "source_entity_count": 2,
        },
        "validator_probe": {
            "is_pass": True,
            "status": "validated",
            "issue_count": 0,
            "warning_count": 0,
            "error_count": 0,
            "validator_version": "v1",
            "canonical_format_version": "normalized_geometry.v1",
        },
        "blocking_reasons": [],
        "review_required_reasons": [],
        "diagnostics": {
            "precedence_rule_applied": "clean_pass",
            "notes": ["acceptance-note"],
        },
    }

    return (
        inspect_result,
        role_resolution,
        gap_repair_result,
        duplicate_dedupe_result,
        normalized_dxf_writer_result,
        acceptance_gate_result,
    )


def _render(
    tmp_path: Path,
    *,
    role_override: dict[str, Any] | None = None,
    gap_override: dict[str, Any] | None = None,
    dedupe_override: dict[str, Any] | None = None,
    writer_override: dict[str, Any] | None = None,
    acceptance_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    (
        inspect_result,
        role_resolution,
        gap_repair_result,
        duplicate_dedupe_result,
        normalized_dxf_writer_result,
        acceptance_gate_result,
    ) = _base_inputs(tmp_path)

    return render_dxf_preflight_diagnostics_summary(
        inspect_result,
        role_override if role_override is not None else role_resolution,
        gap_override if gap_override is not None else gap_repair_result,
        dedupe_override if dedupe_override is not None else duplicate_dedupe_result,
        writer_override if writer_override is not None else normalized_dxf_writer_result,
        acceptance_override if acceptance_override is not None else acceptance_gate_result,
    )


def _families(records: list[dict[str, Any]]) -> list[str]:
    return [str(item.get("family", "")) for item in records]


def test_t7_output_shape_and_scope_guard(tmp_path: Path) -> None:
    result = _render(tmp_path)
    assert set(result.keys()) == EXPECTED_TOP_LEVEL_KEYS
    assert not (FORBIDDEN_TOP_LEVEL_KEYS & set(result.keys()))


def test_t7_accepted_flow_has_clean_acceptance_and_local_artifact_reference(tmp_path: Path) -> None:
    result = _render(tmp_path)

    assert result["acceptance_summary"]["acceptance_outcome"] == "accepted_for_import"
    assert result["acceptance_summary"]["precedence_rule_applied"] == "clean_pass"
    assert result["issue_summary"]["blocking_issues"] == []

    artifact_kinds = [item["artifact_kind"] for item in result["artifact_references"]]
    assert "normalized_dxf" in artifact_kinds
    normalized_ref = next(item for item in result["artifact_references"] if item["artifact_kind"] == "normalized_dxf")
    assert normalized_ref["exists"] is True
    assert normalized_ref["download_label"] == "Download normalized DXF"


def test_t7_review_required_flow_separates_review_issues_and_unresolved_repairs(tmp_path: Path) -> None:
    (
        _inspect,
        role_resolution,
        gap_repair_result,
        duplicate_dedupe_result,
        normalized_dxf_writer_result,
        acceptance_gate_result,
    ) = _base_inputs(tmp_path)

    gap_repair_result["remaining_open_path_candidates"] = [
        {"family": "cut_like_open_path_remaining_after_repair", "layer": "CUT_OUTER", "path_index": 3}
    ]
    gap_repair_result["review_required_candidates"] = [
        {"family": "ambiguous_gap_partner", "layer": "CUT_OUTER", "severity": "review_required"}
    ]
    duplicate_dedupe_result["remaining_duplicate_candidates"] = [
        {"family": "duplicate_candidate_over_tolerance", "pair": [{"contour_id": "a"}, {"contour_id": "b"}]}
    ]
    normalized_dxf_writer_result["skipped_source_entities"] = [
        {"source_entity_index": 1, "source_type": "TEXT", "reason": "unsupported_entity_type"}
    ]
    acceptance_gate_result["acceptance_outcome"] = "preflight_review_required"
    acceptance_gate_result["diagnostics"]["precedence_rule_applied"] = "review_required_signal_present"
    acceptance_gate_result["review_required_reasons"] = [
        {"source": "normalized_dxf_writer_result.skipped_source_entities", "family": "writer_skipped_source_entity"}
    ]

    result = _render(
        tmp_path,
        role_override=role_resolution,
        gap_override=gap_repair_result,
        dedupe_override=duplicate_dedupe_result,
        writer_override=normalized_dxf_writer_result,
        acceptance_override=acceptance_gate_result,
    )

    assert result["acceptance_summary"]["acceptance_outcome"] == "preflight_review_required"
    review_families = _families(result["issue_summary"]["review_required_issues"])
    assert "cut_like_open_path_remaining_after_repair" in review_families
    assert "writer_skipped_source_entity" in review_families

    repair_counts = result["repair_summary"]["counts"]
    assert repair_counts["remaining_open_path_count"] == 1
    assert repair_counts["remaining_duplicate_count"] == 1
    assert repair_counts["skipped_source_entity_count"] == 1


def test_t7_rejected_flow_surfaces_importer_highlight_and_blocking_issue(tmp_path: Path) -> None:
    (
        _inspect,
        role_resolution,
        gap_repair_result,
        duplicate_dedupe_result,
        normalized_dxf_writer_result,
        acceptance_gate_result,
    ) = _base_inputs(tmp_path)

    acceptance_gate_result["acceptance_outcome"] = "preflight_rejected"
    acceptance_gate_result["diagnostics"]["precedence_rule_applied"] = "importer_failed"
    acceptance_gate_result["importer_probe"] = {
        "is_pass": False,
        "error_code": "DXF_READ_FAILED",
        "error_message": "forced importer fail",
        "outer_point_count": 0,
        "hole_count": 0,
        "source_entity_count": 0,
    }
    acceptance_gate_result["validator_probe"]["status"] = "skipped_due_to_importer_failure"
    acceptance_gate_result["blocking_reasons"] = [
        {
            "source": "importer_probe",
            "family": "importer_probe_failed",
            "details": {"error_code": "DXF_READ_FAILED", "error_message": "forced importer fail"},
        }
    ]

    result = _render(
        tmp_path,
        role_override=role_resolution,
        gap_override=gap_repair_result,
        dedupe_override=duplicate_dedupe_result,
        writer_override=normalized_dxf_writer_result,
        acceptance_override=acceptance_gate_result,
    )

    assert result["acceptance_summary"]["acceptance_outcome"] == "preflight_rejected"
    assert result["issue_summary"]["importer_highlight"]["is_pass"] is False

    blocking = result["issue_summary"]["blocking_issues"]
    assert any(item["source"] == "acceptance_gate.importer" for item in blocking)
    assert any(item["family"] == "importer_probe_failed" for item in blocking)


def test_t7_source_inventory_and_repair_summary_counts_are_deterministic(tmp_path: Path) -> None:
    result = _render(tmp_path)

    source = result["source_inventory_summary"]
    assert source["entity_count"] == 2
    assert source["contour_count"] == 1
    assert source["open_path_layer_count"] == 1
    assert source["open_path_total_count"] == 1
    assert source["found_layers"] == ["CUT_OUTER", "SCRIBE"]
    assert source["found_colors"] == [1, 2]

    repair = result["repair_summary"]
    assert repair["counts"]["applied_gap_repair_count"] == 1
    assert repair["counts"]["applied_duplicate_dedupe_count"] == 1
    assert repair["counts"]["remaining_open_path_count"] == 0
    assert repair["counts"]["remaining_duplicate_count"] == 0


def test_t7_renderer_does_not_require_ezdxf_when_inputs_are_precomputed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import = builtins.__import__

    def _guarded_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "ezdxf":
            raise AssertionError("renderer must not import ezdxf")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _guarded_import)

    result = _render(tmp_path)
    assert result["acceptance_summary"]["acceptance_outcome"] == "accepted_for_import"


def test_t7_raises_on_invalid_structural_inputs() -> None:
    with pytest.raises(DxfPreflightDiagnosticsRendererError) as exc:
        render_dxf_preflight_diagnostics_summary(
            inspect_result={},
            role_resolution={},
            gap_repair_result={},
            duplicate_dedupe_result={},
            normalized_dxf_writer_result={},
            acceptance_gate_result=None,  # type: ignore[arg-type]
        )

    assert exc.value.code == "DXF_DIAGNOSTICS_RENDERER_INVALID_ACCEPTANCE_GATE_RESULT"
