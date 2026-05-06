#!/usr/bin/env python3
"""DXF Prefilter E2-T7 -- diagnostics and repair summary renderer (V1)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

__all__ = [
    "DxfPreflightDiagnosticsRendererError",
    "render_dxf_preflight_diagnostics_summary",
]


_SEVERITY_ORDER: dict[str, int] = {
    "blocking": 0,
    "review_required": 1,
    "warning": 2,
    "info": 3,
}


class DxfPreflightDiagnosticsRendererError(RuntimeError):
    """Raised for structural misuse of the T7 diagnostics renderer boundary."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def render_dxf_preflight_diagnostics_summary(
    inspect_result: Mapping[str, Any],
    role_resolution: Mapping[str, Any],
    gap_repair_result: Mapping[str, Any],
    duplicate_dedupe_result: Mapping[str, Any],
    normalized_dxf_writer_result: Mapping[str, Any],
    acceptance_gate_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Render a single deterministic diagnostics/repair summary object from T1..T6 truth."""
    _require_mapping(
        inspect_result,
        code="DXF_DIAGNOSTICS_RENDERER_INVALID_INSPECT_RESULT",
        message="inspect_result must be a mapping as produced by inspect_dxf_source().",
    )
    _require_mapping(
        role_resolution,
        code="DXF_DIAGNOSTICS_RENDERER_INVALID_ROLE_RESOLUTION",
        message="role_resolution must be a mapping as produced by resolve_dxf_roles().",
    )
    _require_mapping(
        gap_repair_result,
        code="DXF_DIAGNOSTICS_RENDERER_INVALID_GAP_REPAIR_RESULT",
        message="gap_repair_result must be a mapping as produced by repair_dxf_gaps().",
    )
    _require_mapping(
        duplicate_dedupe_result,
        code="DXF_DIAGNOSTICS_RENDERER_INVALID_DUPLICATE_DEDUPE_RESULT",
        message=(
            "duplicate_dedupe_result must be a mapping as produced by "
            "dedupe_dxf_duplicate_contours()."
        ),
    )
    _require_mapping(
        normalized_dxf_writer_result,
        code="DXF_DIAGNOSTICS_RENDERER_INVALID_NORMALIZED_WRITER_RESULT",
        message="normalized_dxf_writer_result must be a mapping as produced by write_normalized_dxf().",
    )
    _require_mapping(
        acceptance_gate_result,
        code="DXF_DIAGNOSTICS_RENDERER_INVALID_ACCEPTANCE_GATE_RESULT",
        message=(
            "acceptance_gate_result must be a mapping as produced by "
            "evaluate_dxf_prefilter_acceptance_gate()."
        ),
    )

    source_inventory_summary = _build_source_inventory_summary(inspect_result)
    role_mapping_summary = _build_role_mapping_summary(role_resolution)
    repair_summary = _build_repair_summary(
        role_resolution=role_resolution,
        gap_repair_result=gap_repair_result,
        duplicate_dedupe_result=duplicate_dedupe_result,
        normalized_dxf_writer_result=normalized_dxf_writer_result,
    )
    acceptance_summary = _build_acceptance_summary(acceptance_gate_result)
    artifact_references = _build_artifact_references(
        inspect_result=inspect_result,
        normalized_dxf_writer_result=normalized_dxf_writer_result,
    )
    issue_summary = _build_issue_summary(
        inspect_result=inspect_result,
        role_resolution=role_resolution,
        gap_repair_result=gap_repair_result,
        duplicate_dedupe_result=duplicate_dedupe_result,
        normalized_dxf_writer_result=normalized_dxf_writer_result,
        acceptance_gate_result=acceptance_gate_result,
    )

    return {
        "source_inventory_summary": source_inventory_summary,
        "role_mapping_summary": role_mapping_summary,
        "issue_summary": issue_summary,
        "repair_summary": repair_summary,
        "acceptance_summary": acceptance_summary,
        "artifact_references": artifact_references,
    }


def _build_source_inventory_summary(inspect_result: Mapping[str, Any]) -> dict[str, Any]:
    layer_inventory = _stable_sorted_dict_list(inspect_result.get("layer_inventory"))
    color_inventory = _stable_sorted_dict_list(inspect_result.get("color_inventory"))
    linetype_inventory = _stable_sorted_dict_list(inspect_result.get("linetype_inventory"))
    entity_inventory = _as_dict_list(inspect_result.get("entity_inventory"))
    contour_candidates = _as_dict_list(inspect_result.get("contour_candidates"))
    open_path_candidates = _as_dict_list(inspect_result.get("open_path_candidates"))
    duplicate_groups = _as_dict_list(inspect_result.get("duplicate_contour_candidates"))

    duplicate_members = 0
    for group in duplicate_groups:
        count = _as_int(group.get("count"), default=-1)
        if count >= 0:
            duplicate_members += count
            continue
        refs = _as_dict_list(group.get("ring_references"))
        duplicate_members += len(refs)

    return {
        "source_path": str(inspect_result.get("source_path", "")),
        "backend": str(inspect_result.get("backend", "")),
        "source_size_bytes": _as_optional_int(inspect_result.get("source_size_bytes")),
        "found_layers": [str(item.get("layer", "")) for item in layer_inventory],
        "layer_inventory": layer_inventory,
        "found_colors": [item.get("color_index") for item in color_inventory],
        "color_inventory": color_inventory,
        "found_linetypes": [item.get("linetype_name") for item in linetype_inventory],
        "linetype_inventory": linetype_inventory,
        "entity_count": len(entity_inventory),
        "contour_count": len(contour_candidates),
        "open_path_layer_count": len(open_path_candidates),
        "open_path_total_count": sum(
            _as_int(item.get("open_path_count"), default=0) for item in open_path_candidates
        ),
        "duplicate_candidate_group_count": len(duplicate_groups),
        "duplicate_candidate_member_count": duplicate_members,
    }


def _build_role_mapping_summary(role_resolution: Mapping[str, Any]) -> dict[str, Any]:
    layer_role_assignments = _stable_sorted_dict_list(role_resolution.get("layer_role_assignments"))
    resolved_inventory = _as_dict(role_resolution.get("resolved_role_inventory"))
    resolved_inventory_sorted = {
        key: _as_int(resolved_inventory[key], default=0) for key in sorted(resolved_inventory)
    }
    return {
        "rules_profile_echo": _as_jsonable(role_resolution.get("rules_profile_echo")),
        "layer_role_assignments": layer_role_assignments,
        "resolved_role_inventory": resolved_inventory_sorted,
        "layer_assignment_count": len(layer_role_assignments),
        "review_required_count": len(_as_dict_list(role_resolution.get("review_required_candidates"))),
        "blocking_conflict_count": len(_as_dict_list(role_resolution.get("blocking_conflicts"))),
    }


def _build_repair_summary(
    *,
    role_resolution: Mapping[str, Any],
    gap_repair_result: Mapping[str, Any],
    duplicate_dedupe_result: Mapping[str, Any],
    normalized_dxf_writer_result: Mapping[str, Any],
) -> dict[str, Any]:
    applied_gap_repairs = _stable_sorted_dict_list(gap_repair_result.get("applied_gap_repairs"))
    applied_duplicate_dedupes = _stable_sorted_dict_list(
        duplicate_dedupe_result.get("applied_duplicate_dedupes")
    )
    skipped_source_entities = _stable_sorted_dict_list(
        normalized_dxf_writer_result.get("skipped_source_entities")
    )
    remaining_open_paths = _stable_sorted_dict_list(
        gap_repair_result.get("remaining_open_path_candidates")
    )
    remaining_duplicates = _stable_sorted_dict_list(
        duplicate_dedupe_result.get("remaining_duplicate_candidates")
    )

    remaining_review_signals: list[dict[str, Any]] = []
    for item in _as_dict_list(role_resolution.get("review_required_candidates")):
        remaining_review_signals.append(
            {
                "source": "role_resolver.review_required_candidates",
                "family": str(item.get("family", "")),
                "details": item,
            }
        )
    for item in _as_dict_list(gap_repair_result.get("review_required_candidates")):
        remaining_review_signals.append(
            {
                "source": "gap_repair.review_required_candidates",
                "family": str(item.get("family", "")),
                "details": item,
            }
        )
    for item in _as_dict_list(duplicate_dedupe_result.get("review_required_candidates")):
        remaining_review_signals.append(
            {
                "source": "duplicate_dedupe.review_required_candidates",
                "family": str(item.get("family", "")),
                "details": item,
            }
        )
    for item in skipped_source_entities:
        remaining_review_signals.append(
            {
                "source": "normalized_writer.skipped_source_entities",
                "family": "writer_skipped_source_entity",
                "details": item,
            }
        )
    remaining_review_signals = _stable_sorted_dict_list(remaining_review_signals)

    return {
        "applied_gap_repairs": applied_gap_repairs,
        "applied_duplicate_dedupes": applied_duplicate_dedupes,
        "skipped_source_entities": skipped_source_entities,
        "remaining_open_path_candidates": remaining_open_paths,
        "remaining_duplicate_candidates": remaining_duplicates,
        "remaining_review_required_signals": remaining_review_signals,
        "counts": {
            "applied_gap_repair_count": len(applied_gap_repairs),
            "applied_duplicate_dedupe_count": len(applied_duplicate_dedupes),
            "skipped_source_entity_count": len(skipped_source_entities),
            "remaining_open_path_count": len(remaining_open_paths),
            "remaining_duplicate_count": len(remaining_duplicates),
            "remaining_review_required_signal_count": len(remaining_review_signals),
        },
    }


def _build_acceptance_summary(acceptance_gate_result: Mapping[str, Any]) -> dict[str, Any]:
    diagnostics = _as_dict(acceptance_gate_result.get("diagnostics"))
    importer_probe = _as_dict(acceptance_gate_result.get("importer_probe"))
    validator_probe = _as_dict(acceptance_gate_result.get("validator_probe"))
    blocking_reasons = _as_dict_list(acceptance_gate_result.get("blocking_reasons"))
    review_required_reasons = _as_dict_list(acceptance_gate_result.get("review_required_reasons"))

    return {
        "acceptance_outcome": str(acceptance_gate_result.get("acceptance_outcome", "")),
        "precedence_rule_applied": str(diagnostics.get("precedence_rule_applied", "")),
        "importer_probe": {
            "is_pass": bool(importer_probe.get("is_pass")),
            "error_code": importer_probe.get("error_code"),
            "error_message": importer_probe.get("error_message"),
            "outer_point_count": _as_int(importer_probe.get("outer_point_count"), default=0),
            "hole_count": _as_int(importer_probe.get("hole_count"), default=0),
            "source_entity_count": _as_int(importer_probe.get("source_entity_count"), default=0),
        },
        "validator_probe": {
            "is_pass": bool(validator_probe.get("is_pass")),
            "status": str(validator_probe.get("status", "")),
            "issue_count": _as_int(validator_probe.get("issue_count"), default=0),
            "warning_count": _as_int(validator_probe.get("warning_count"), default=0),
            "error_count": _as_int(validator_probe.get("error_count"), default=0),
            "validator_version": str(validator_probe.get("validator_version", "")),
            "canonical_format_version": str(validator_probe.get("canonical_format_version", "")),
        },
        "blocking_reason_count": len(blocking_reasons),
        "review_required_reason_count": len(review_required_reasons),
    }


def _build_artifact_references(
    *,
    inspect_result: Mapping[str, Any],
    normalized_dxf_writer_result: Mapping[str, Any],
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []

    normalized_dxf = normalized_dxf_writer_result.get("normalized_dxf")
    if isinstance(normalized_dxf, Mapping):
        output_path = str(normalized_dxf.get("output_path", "")).strip()
        if output_path:
            path = Path(output_path).resolve()
            refs.append(
                {
                    "artifact_kind": "normalized_dxf",
                    "path": str(path),
                    "exists": path.is_file(),
                    "download_label": "Download normalized DXF",
                    "writer_backend": str(normalized_dxf.get("writer_backend", "")),
                }
            )

    source_path_raw = str(inspect_result.get("source_path", "")).strip()
    if source_path_raw:
        source_path = Path(source_path_raw).resolve()
        refs.append(
            {
                "artifact_kind": "source_input",
                "path": str(source_path),
                "exists": source_path.is_file(),
                "download_label": "Open source input",
            }
        )

    return _stable_sorted_dict_list(refs)


def _build_issue_summary(
    *,
    inspect_result: Mapping[str, Any],
    role_resolution: Mapping[str, Any],
    gap_repair_result: Mapping[str, Any],
    duplicate_dedupe_result: Mapping[str, Any],
    normalized_dxf_writer_result: Mapping[str, Any],
    acceptance_gate_result: Mapping[str, Any],
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []

    _append_issues_from_records(
        issues,
        records=_as_dict_list(role_resolution.get("blocking_conflicts")),
        severity_hint="blocking",
        source="role_resolver",
    )
    _append_issues_from_records(
        issues,
        records=_as_dict_list(role_resolution.get("review_required_candidates")),
        severity_hint="review_required",
        source="role_resolver",
    )

    _append_issues_from_records(
        issues,
        records=_as_dict_list(gap_repair_result.get("blocking_conflicts")),
        severity_hint="blocking",
        source="gap_repair",
    )
    _append_issues_from_records(
        issues,
        records=_as_dict_list(gap_repair_result.get("review_required_candidates")),
        severity_hint="review_required",
        source="gap_repair",
    )
    _append_issues_from_records(
        issues,
        records=_as_dict_list(gap_repair_result.get("remaining_open_path_candidates")),
        severity_hint="review_required",
        source="gap_repair",
        fallback_family="gap_repair_remaining_open_path",
    )

    _append_issues_from_records(
        issues,
        records=_as_dict_list(duplicate_dedupe_result.get("blocking_conflicts")),
        severity_hint="blocking",
        source="duplicate_dedupe",
    )
    _append_issues_from_records(
        issues,
        records=_as_dict_list(duplicate_dedupe_result.get("review_required_candidates")),
        severity_hint="review_required",
        source="duplicate_dedupe",
    )
    _append_issues_from_records(
        issues,
        records=_as_dict_list(duplicate_dedupe_result.get("remaining_duplicate_candidates")),
        severity_hint="review_required",
        source="duplicate_dedupe",
        fallback_family="duplicate_dedupe_remaining_duplicate",
    )

    for item in _as_dict_list(normalized_dxf_writer_result.get("skipped_source_entities")):
        _append_issue(
            issues,
            severity="review_required",
            source="normalized_writer",
            family="writer_skipped_source_entity",
            details=item,
            code=str(item.get("reason", "WRITER_SKIPPED_SOURCE_ENTITY")).upper(),
            message=(
                "Source entity was skipped by normalized DXF writer; review may be required "
                "before import."
            ),
        )

    # Importer/validator highlights from acceptance gate are acceptance-specific and
    # should be preserved in the unified issue list without duplicating upstream
    # role/gap/dedupe families.
    for reason in _as_dict_list(acceptance_gate_result.get("blocking_reasons")):
        source_raw = str(reason.get("source", ""))
        if source_raw not in {"importer_probe", "validator_probe"}:
            continue
        _append_issue(
            issues,
            severity="blocking",
            source=_map_acceptance_source(source_raw),
            family=str(reason.get("family", "acceptance_gate_blocking_reason")),
            details=_as_dict(reason.get("details")),
            code=str(reason.get("family", "ACCEPTANCE_GATE_BLOCKING_REASON")).upper(),
            message=_default_acceptance_reason_message(reason),
        )

    # Propagate review_required_reasons from the acceptance gate (e.g. nested island
    # demotion: validator errors that were demoted to review_required rather than blocking).
    for reason in _as_dict_list(acceptance_gate_result.get("review_required_reasons")):
        source_raw = str(reason.get("source", ""))
        if source_raw not in {"importer_probe", "validator_probe"}:
            continue
        _append_issue(
            issues,
            severity="review_required",
            source=_map_acceptance_source(source_raw),
            family=str(reason.get("family", "acceptance_gate_review_required_reason")),
            details=_as_dict(reason.get("details")),
            code=str(reason.get("family", "ACCEPTANCE_GATE_REVIEW_REQUIRED_REASON")).upper(),
            message=_default_acceptance_reason_message(reason),
        )

    inspect_diagnostics = _as_dict(inspect_result.get("diagnostics"))
    for error in _as_dict_list(inspect_diagnostics.get("probe_errors")):
        _append_issue(
            issues,
            severity="warning",
            source="inspect",
            family=str(error.get("family", "inspect_probe_error")),
            details=error,
            code=str(error.get("code", "INSPECT_PROBE_ERROR")).upper(),
            message=str(error.get("message", "Inspect probe reported a recoverable issue.")),
        )
    _append_note_issues(
        issues,
        source="inspect",
        notes=inspect_diagnostics.get("notes"),
        family="inspect_note",
    )

    gap_diagnostics = _as_dict(gap_repair_result.get("diagnostics"))
    _append_optional_source_load_issue(
        issues,
        source="gap_repair",
        source_load_error=gap_diagnostics.get("source_load_error"),
    )
    _append_note_issues(
        issues,
        source="gap_repair",
        notes=gap_diagnostics.get("notes"),
        family="gap_repair_note",
    )

    dedupe_diagnostics = _as_dict(duplicate_dedupe_result.get("diagnostics"))
    _append_optional_source_load_issue(
        issues,
        source="duplicate_dedupe",
        source_load_error=dedupe_diagnostics.get("source_load_error"),
    )
    _append_note_issues(
        issues,
        source="duplicate_dedupe",
        notes=dedupe_diagnostics.get("notes"),
        family="duplicate_dedupe_note",
    )

    writer_diagnostics = _as_dict(normalized_dxf_writer_result.get("diagnostics"))
    _append_note_issues(
        issues,
        source="normalized_writer",
        notes=writer_diagnostics.get("notes"),
        family="normalized_writer_note",
    )

    acceptance_diagnostics = _as_dict(acceptance_gate_result.get("diagnostics"))
    _append_note_issues(
        issues,
        source="acceptance_gate",
        notes=acceptance_diagnostics.get("notes"),
        family="acceptance_gate_note",
    )

    issues_sorted = sorted(issues, key=_issue_sort_key)

    def by_severity(level: str) -> list[dict[str, Any]]:
        return [issue for issue in issues_sorted if issue["severity"] == level]

    importer_probe = _as_dict(acceptance_gate_result.get("importer_probe"))
    validator_probe = _as_dict(acceptance_gate_result.get("validator_probe"))

    return {
        "normalized_issues": issues_sorted,
        "blocking_issues": by_severity("blocking"),
        "review_required_issues": by_severity("review_required"),
        "warning_issues": by_severity("warning"),
        "info_issues": by_severity("info"),
        "counts_by_severity": {
            "blocking": len(by_severity("blocking")),
            "review_required": len(by_severity("review_required")),
            "warning": len(by_severity("warning")),
            "info": len(by_severity("info")),
        },
        "importer_highlight": {
            "is_pass": bool(importer_probe.get("is_pass")),
            "error_code": importer_probe.get("error_code"),
            "error_message": importer_probe.get("error_message"),
            "outer_point_count": _as_int(importer_probe.get("outer_point_count"), default=0),
            "hole_count": _as_int(importer_probe.get("hole_count"), default=0),
            "source_entity_count": _as_int(importer_probe.get("source_entity_count"), default=0),
        },
        "validator_highlight": {
            "is_pass": bool(validator_probe.get("is_pass")),
            "status": str(validator_probe.get("status", "")),
            "issue_count": _as_int(validator_probe.get("issue_count"), default=0),
            "warning_count": _as_int(validator_probe.get("warning_count"), default=0),
            "error_count": _as_int(validator_probe.get("error_count"), default=0),
            "validator_version": str(validator_probe.get("validator_version", "")),
            "canonical_format_version": str(validator_probe.get("canonical_format_version", "")),
        },
    }


def _append_issues_from_records(
    out: list[dict[str, Any]],
    *,
    records: list[dict[str, Any]],
    severity_hint: str,
    source: str,
    fallback_family: str | None = None,
) -> None:
    for record in records:
        severity_raw = str(record.get("severity", "")).strip()
        severity = severity_hint
        if severity_raw in _SEVERITY_ORDER:
            severity = severity_raw
        family = str(record.get("family", "")).strip()
        if not family:
            family = fallback_family or "unspecified"
        code = str(record.get("code", "")).strip()
        if not code:
            code = str(record.get("display_code", "")).strip()
        if not code:
            code = _derive_code(source=source, family=family)
        message = str(record.get("message", "")).strip()
        if not message:
            message = f"{severity} signal from {source}: {family}"
        _append_issue(
            out,
            severity=severity,
            source=source,
            family=family,
            details=record,
            code=code,
            message=message,
        )


def _append_optional_source_load_issue(
    out: list[dict[str, Any]],
    *,
    source: str,
    source_load_error: Any,
) -> None:
    err = _as_dict(source_load_error)
    if not err:
        return
    code = str(err.get("code", "SOURCE_LOAD_ERROR")).strip() or "SOURCE_LOAD_ERROR"
    message = str(err.get("message", "Source load error reported.")).strip()
    _append_issue(
        out,
        severity="warning",
        source=source,
        family="source_load_error",
        details=err,
        code=code.upper(),
        message=message,
    )


def _append_note_issues(
    out: list[dict[str, Any]],
    *,
    source: str,
    notes: Any,
    family: str,
) -> None:
    if not isinstance(notes, list):
        return
    for index, note in enumerate(notes):
        if not isinstance(note, str):
            continue
        message = note.strip()
        if not message:
            continue
        _append_issue(
            out,
            severity="info",
            source=source,
            family=family,
            details={"note_index": index, "note": message},
            code=_derive_code(source=source, family=family),
            message=message,
        )


def _append_issue(
    out: list[dict[str, Any]],
    *,
    severity: str,
    source: str,
    family: str,
    details: Any,
    code: str,
    message: str,
) -> None:
    severity_value = severity if severity in _SEVERITY_ORDER else "info"
    source_value = source.strip() if source.strip() else "unknown"
    family_value = family.strip() if family.strip() else "unspecified"
    code_value = code.strip() if code.strip() else _derive_code(source_value, family_value)
    message_value = message.strip() if message.strip() else f"{severity_value} signal"
    out.append(
        {
            "severity": severity_value,
            "source": source_value,
            "family": family_value,
            "code": code_value,
            "display_code": code_value,
            "message": message_value,
            "details": _as_jsonable(details),
        }
    )


def _default_acceptance_reason_message(reason: Mapping[str, Any]) -> str:
    family = str(reason.get("family", ""))
    if family == "importer_probe_failed":
        return "Acceptance gate importer probe failed on normalized artifact."
    if family == "validator_probe_rejected":
        return "Acceptance gate validator probe rejected normalized artifact."
    return f"Acceptance gate blocking reason: {family or 'unknown'}"


def _map_acceptance_source(source_raw: str) -> str:
    if source_raw == "importer_probe":
        return "acceptance_gate.importer"
    if source_raw == "validator_probe":
        return "acceptance_gate.validator"
    return "acceptance_gate"


def _issue_sort_key(issue: dict[str, Any]) -> tuple[int, str, str, str, str]:
    severity = str(issue.get("severity", "info"))
    severity_rank = _SEVERITY_ORDER.get(severity, 999)
    source = str(issue.get("source", ""))
    family = str(issue.get("family", ""))
    code = str(issue.get("code", ""))
    payload = json.dumps(issue.get("details", {}), ensure_ascii=False, sort_keys=True)
    return severity_rank, source, family, code, payload


def _derive_code(source: str, family: str) -> str:
    raw = f"{source}_{family}".upper()
    out = []
    for char in raw:
        if char.isalnum():
            out.append(char)
        else:
            out.append("_")
    code = "".join(out)
    while "__" in code:
        code = code.replace("__", "_")
    return code.strip("_") or "UNSPECIFIED"


def _stable_sorted_dict_list(value: Any) -> list[dict[str, Any]]:
    records = _as_dict_list(value)
    return sorted(records, key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True))


def _as_jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _as_jsonable(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, list):
        return [_as_jsonable(item) for item in value]
    return value


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return {str(k): v for k, v in value.items()}
    return {}


def _as_dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    out: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, Mapping):
            out.append({str(k): v for k, v in item.items()})
    return out


def _as_int(value: Any, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return default


def _as_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def _require_mapping(value: Any, *, code: str, message: str) -> None:
    if not isinstance(value, Mapping):
        raise DxfPreflightDiagnosticsRendererError(code, message)
