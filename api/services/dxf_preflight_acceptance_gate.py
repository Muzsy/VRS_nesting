#!/usr/bin/env python3
"""DXF Prefilter E2-T6 -- acceptance gate backend service (V1)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from api.services.dxf_geometry_import import (
    build_canonical_geometry_probe_from_part_raw,
)
from api.services.geometry_validation_report import build_geometry_validation_probe
from vrs_nesting.dxf.importer import DxfImportError, PartRaw, import_part_raw

__all__ = [
    "DxfPreflightAcceptanceGateError",
    "evaluate_dxf_prefilter_acceptance_gate",
]

_ACCEPTED = "accepted_for_import"
_REJECTED = "preflight_rejected"
_REVIEW_REQUIRED = "preflight_review_required"
_LOCAL_BUCKET = "prefilter_local_artifact"


class DxfPreflightAcceptanceGateError(RuntimeError):
    """Raised for structural misuse of the T6 acceptance-gate boundary."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def evaluate_dxf_prefilter_acceptance_gate(
    inspect_result: Mapping[str, Any],
    role_resolution: Mapping[str, Any],
    gap_repair_result: Mapping[str, Any],
    duplicate_dedupe_result: Mapping[str, Any],
    normalized_dxf_writer_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate normalized artifact acceptance on importer + validator truth."""
    _require_mapping(
        inspect_result,
        code="DXF_ACCEPTANCE_GATE_INVALID_INSPECT_RESULT",
        message="inspect_result must be a mapping as produced by inspect_dxf_source().",
    )
    _require_mapping(
        role_resolution,
        code="DXF_ACCEPTANCE_GATE_INVALID_ROLE_RESOLUTION",
        message="role_resolution must be a mapping as produced by resolve_dxf_roles().",
    )
    _require_mapping(
        gap_repair_result,
        code="DXF_ACCEPTANCE_GATE_INVALID_GAP_REPAIR_RESULT",
        message="gap_repair_result must be a mapping as produced by repair_dxf_gaps().",
    )
    _require_mapping(
        duplicate_dedupe_result,
        code="DXF_ACCEPTANCE_GATE_INVALID_DUPLICATE_DEDUPE_RESULT",
        message=(
            "duplicate_dedupe_result must be a mapping as produced by "
            "dedupe_dxf_duplicate_contours()."
        ),
    )
    _require_mapping(
        normalized_dxf_writer_result,
        code="DXF_ACCEPTANCE_GATE_INVALID_NORMALIZED_WRITER_RESULT",
        message="normalized_dxf_writer_result must be a mapping as produced by write_normalized_dxf().",
    )

    normalized_dxf = normalized_dxf_writer_result.get("normalized_dxf")
    if not isinstance(normalized_dxf, Mapping):
        raise DxfPreflightAcceptanceGateError(
            "DXF_ACCEPTANCE_GATE_NORMALIZED_DXF_MISSING",
            "normalized_dxf_writer_result.normalized_dxf must be a mapping.",
        )

    output_path_raw = str(normalized_dxf.get("output_path", "")).strip()
    if not output_path_raw:
        raise DxfPreflightAcceptanceGateError(
            "DXF_ACCEPTANCE_GATE_OUTPUT_PATH_MISSING",
            "normalized_dxf.output_path is required.",
        )
    artifact_path = Path(output_path_raw).resolve()
    if not artifact_path.is_file():
        raise DxfPreflightAcceptanceGateError(
            "DXF_ACCEPTANCE_GATE_OUTPUT_PATH_NOT_FOUND",
            f"normalized artifact path not accessible: {artifact_path}",
        )

    importer_probe, part_raw = _run_importer_probe(artifact_path)
    validator_probe = _build_default_validator_probe()

    if part_raw is not None:
        validator_probe = _run_validator_probe(
            part_raw=part_raw,
            artifact_path=artifact_path,
        )

    blocking_reasons = _collect_blocking_reasons(
        role_resolution=role_resolution,
        gap_repair_result=gap_repair_result,
        duplicate_dedupe_result=duplicate_dedupe_result,
        importer_probe=importer_probe,
        validator_probe=validator_probe,
    )
    review_required_reasons = _collect_review_required_reasons(
        role_resolution=role_resolution,
        gap_repair_result=gap_repair_result,
        duplicate_dedupe_result=duplicate_dedupe_result,
        normalized_dxf_writer_result=normalized_dxf_writer_result,
    )

    outcome, precedence = _resolve_outcome(
        importer_probe=importer_probe,
        validator_probe=validator_probe,
        blocking_reasons=blocking_reasons,
        review_required_reasons=review_required_reasons,
    )

    normalized_dxf_echo = {
        "output_path": str(artifact_path),
        "writer_backend": str(normalized_dxf.get("writer_backend", "")),
        "written_layers": _as_str_list(normalized_dxf.get("written_layers")),
        "written_entity_count": _as_int(normalized_dxf.get("written_entity_count"), default=0),
        "cut_contour_count": _as_int(normalized_dxf.get("cut_contour_count"), default=0),
        "marking_entity_count": _as_int(normalized_dxf.get("marking_entity_count"), default=0),
    }

    diagnostics = {
        "precedence_rule_applied": precedence,
        "upstream_signal_counts": {
            "role_resolution_blocking_conflicts": len(
                _as_dict_list(role_resolution.get("blocking_conflicts"))
            ),
            "gap_repair_blocking_conflicts": len(
                _as_dict_list(gap_repair_result.get("blocking_conflicts"))
            ),
            "duplicate_dedupe_blocking_conflicts": len(
                _as_dict_list(duplicate_dedupe_result.get("blocking_conflicts"))
            ),
            "role_resolution_review_required": len(
                _as_dict_list(role_resolution.get("review_required_candidates"))
            ),
            "gap_repair_review_required": len(
                _as_dict_list(gap_repair_result.get("review_required_candidates"))
            ),
            "gap_repair_remaining_open_paths": len(
                _as_dict_list(gap_repair_result.get("remaining_open_path_candidates"))
            ),
            "duplicate_dedupe_review_required": len(
                _as_dict_list(duplicate_dedupe_result.get("review_required_candidates"))
            ),
            "duplicate_dedupe_remaining_duplicates": len(
                _as_dict_list(duplicate_dedupe_result.get("remaining_duplicate_candidates"))
            ),
            "writer_skipped_source_entities": len(
                _as_dict_list(normalized_dxf_writer_result.get("skipped_source_entities"))
            ),
        },
        "reason_counts": {
            "blocking_count": len(blocking_reasons),
            "review_required_count": len(review_required_reasons),
        },
        "notes": [
            "t6_scope_boundary: local gate verdict only; no DB persistence, API route, upload trigger, or UI.",
            "importer_probe_boundary: normalized artifact is validated via import_part_raw() on the writer output path.",
            "validator_probe_boundary: validator logic is reused through a public pure helper without DB insert.",
        ],
    }

    return {
        "acceptance_outcome": outcome,
        "normalized_dxf_echo": normalized_dxf_echo,
        "importer_probe": importer_probe,
        "validator_probe": validator_probe,
        "blocking_reasons": blocking_reasons,
        "review_required_reasons": review_required_reasons,
        "diagnostics": diagnostics,
    }


def _run_importer_probe(artifact_path: Path) -> tuple[dict[str, Any], PartRaw | None]:
    try:
        part_raw = import_part_raw(str(artifact_path))
    except DxfImportError as exc:
        return (
            {
                "is_pass": False,
                "error_code": exc.code,
                "error_message": exc.message,
                "outer_point_count": 0,
                "hole_count": 0,
                "source_entity_count": 0,
            },
            None,
        )

    return (
        {
            "is_pass": True,
            "error_code": None,
            "error_message": None,
            "outer_point_count": len(part_raw.outer_points_mm),
            "hole_count": len(part_raw.holes_points_mm),
            "source_entity_count": len(part_raw.source_entities),
        },
        part_raw,
    )


def _run_validator_probe(
    *,
    part_raw: PartRaw,
    artifact_path: Path,
) -> dict[str, Any]:
    canonical_probe = build_canonical_geometry_probe_from_part_raw(
        part_raw=part_raw,
        storage_bucket=_LOCAL_BUCKET,
        storage_path=str(artifact_path),
    )
    canonical_geometry = canonical_probe["canonical_geometry_jsonb"]
    bbox_jsonb = canonical_probe["bbox_jsonb"]
    canonical_hash = str(canonical_probe["canonical_hash_sha256"])
    canonical_format_version = str(canonical_probe["canonical_format_version"])

    geometry_revision = {
        "id": f"prefilter_local::{canonical_hash[:16]}",
        "canonical_format_version": canonical_format_version,
        "canonical_geometry_jsonb": canonical_geometry,
        "bbox_jsonb": bbox_jsonb,
        "canonical_hash_sha256": canonical_hash,
        "source_hash_sha256": canonical_hash,
    }

    probe = build_geometry_validation_probe(geometry_revision=geometry_revision)
    status = str(probe.get("status", "")).strip()
    summary_jsonb = _as_dict(probe.get("summary_jsonb"))
    report_jsonb = _as_dict(probe.get("report_jsonb"))

    return {
        "is_pass": status == "validated",
        "status": status or "unknown",
        "issue_count": _as_int(summary_jsonb.get("issue_count"), default=0),
        "warning_count": _as_int(summary_jsonb.get("warning_count"), default=0),
        "error_count": _as_int(summary_jsonb.get("error_count"), default=0),
        "validator_version": str(summary_jsonb.get("validator_version", "")),
        "canonical_format_version": str(summary_jsonb.get("canonical_format_version", "")),
        "summary_jsonb": summary_jsonb,
        "report_jsonb": report_jsonb,
    }


def _build_default_validator_probe() -> dict[str, Any]:
    return {
        "is_pass": False,
        "status": "skipped_due_to_importer_failure",
        "issue_count": 0,
        "warning_count": 0,
        "error_count": 0,
        "validator_version": "",
        "canonical_format_version": "",
        "summary_jsonb": {},
        "report_jsonb": {},
    }


def _collect_blocking_reasons(
    *,
    role_resolution: Mapping[str, Any],
    gap_repair_result: Mapping[str, Any],
    duplicate_dedupe_result: Mapping[str, Any],
    importer_probe: Mapping[str, Any],
    validator_probe: Mapping[str, Any],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    _extend_reason_group(
        out,
        source="role_resolution.blocking_conflicts",
        family="role_resolution_blocking_conflict",
        items=_as_dict_list(role_resolution.get("blocking_conflicts")),
    )
    _extend_reason_group(
        out,
        source="gap_repair_result.blocking_conflicts",
        family="gap_repair_blocking_conflict",
        items=_as_dict_list(gap_repair_result.get("blocking_conflicts")),
    )
    _extend_reason_group(
        out,
        source="duplicate_dedupe_result.blocking_conflicts",
        family="duplicate_dedupe_blocking_conflict",
        items=_as_dict_list(duplicate_dedupe_result.get("blocking_conflicts")),
    )

    if not bool(importer_probe.get("is_pass")):
        out.append(
            {
                "source": "importer_probe",
                "family": "importer_probe_failed",
                "details": {
                    "error_code": str(importer_probe.get("error_code") or ""),
                    "error_message": str(importer_probe.get("error_message") or ""),
                },
            }
        )

    if str(validator_probe.get("status", "")).strip() == "rejected":
        out.append(
            {
                "source": "validator_probe",
                "family": "validator_probe_rejected",
                "details": {
                    "issue_count": _as_int(validator_probe.get("issue_count"), default=0),
                    "error_count": _as_int(validator_probe.get("error_count"), default=0),
                },
            }
        )

    return out


def _collect_review_required_reasons(
    *,
    role_resolution: Mapping[str, Any],
    gap_repair_result: Mapping[str, Any],
    duplicate_dedupe_result: Mapping[str, Any],
    normalized_dxf_writer_result: Mapping[str, Any],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    _extend_reason_group(
        out,
        source="role_resolution.review_required_candidates",
        family="role_resolution_review_required",
        items=_as_dict_list(role_resolution.get("review_required_candidates")),
    )
    _extend_reason_group(
        out,
        source="gap_repair_result.review_required_candidates",
        family="gap_repair_review_required",
        items=_as_dict_list(gap_repair_result.get("review_required_candidates")),
    )
    _extend_reason_group(
        out,
        source="gap_repair_result.remaining_open_path_candidates",
        family="gap_repair_remaining_open_path",
        items=_as_dict_list(gap_repair_result.get("remaining_open_path_candidates")),
    )
    _extend_reason_group(
        out,
        source="duplicate_dedupe_result.review_required_candidates",
        family="duplicate_dedupe_review_required",
        items=_as_dict_list(duplicate_dedupe_result.get("review_required_candidates")),
    )
    _extend_reason_group(
        out,
        source="duplicate_dedupe_result.remaining_duplicate_candidates",
        family="duplicate_dedupe_remaining_duplicate",
        items=_as_dict_list(duplicate_dedupe_result.get("remaining_duplicate_candidates")),
    )
    _extend_reason_group(
        out,
        source="normalized_dxf_writer_result.skipped_source_entities",
        family="writer_skipped_source_entity",
        items=_as_dict_list(normalized_dxf_writer_result.get("skipped_source_entities")),
    )
    return out


def _resolve_outcome(
    *,
    importer_probe: Mapping[str, Any],
    validator_probe: Mapping[str, Any],
    blocking_reasons: list[dict[str, Any]],
    review_required_reasons: list[dict[str, Any]],
) -> tuple[str, str]:
    if not bool(importer_probe.get("is_pass")):
        return _REJECTED, "importer_failed"

    if str(validator_probe.get("status", "")).strip() == "rejected":
        return _REJECTED, "validator_rejected"

    if blocking_reasons:
        return _REJECTED, "blocking_conflict_present"

    if review_required_reasons:
        return _REVIEW_REQUIRED, "review_required_signal_present"

    return _ACCEPTED, "clean_pass"


def _extend_reason_group(
    out: list[dict[str, Any]],
    *,
    source: str,
    family: str,
    items: list[dict[str, Any]],
) -> None:
    sorted_items = sorted(items, key=_reason_item_sort_key)
    for item in sorted_items:
        out.append(
            {
                "source": source,
                "family": family,
                "details": item,
            }
        )


def _reason_item_sort_key(item: dict[str, Any]) -> tuple[str, str]:
    family = str(item.get("family", ""))
    payload = json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return family, payload


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _as_dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    out: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, Mapping):
            out.append(dict(item))
    return out


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        out.append(str(item))
    return out


def _as_int(raw: Any, *, default: int) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int):
        return default
    return int(raw)


def _require_mapping(value: Any, *, code: str, message: str) -> None:
    if not isinstance(value, Mapping):
        raise DxfPreflightAcceptanceGateError(code, message)
