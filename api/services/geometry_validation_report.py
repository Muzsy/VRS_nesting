from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from api.supabase_client import SupabaseClient

logger = logging.getLogger("vrs_api.geometry_validation_report")

_VALIDATOR_VERSION = "geometry_validator.v1"
_EXPECTED_CANONICAL_FORMAT_VERSION = "normalized_geometry.v1"
_BBOX_EPSILON_MM = 1e-6

_SEVERITY_ORDER = {
    "error": 0,
    "warning": 1,
    "info": 2,
}


def _add_issue(
    issues: list[dict[str, Any]],
    *,
    code: str,
    severity: str,
    path: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> None:
    issue = {
        "code": code,
        "severity": severity,
        "path": path,
        "message": message,
    }
    if details is not None:
        issue["details"] = details
    issues.append(issue)


def _issue_sort_key(issue: dict[str, Any]) -> tuple[Any, ...]:
    details_raw = issue.get("details")
    details_json = ""
    if isinstance(details_raw, dict):
        details_json = json.dumps(details_raw, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (
        _SEVERITY_ORDER.get(str(issue.get("severity")), 99),
        str(issue.get("code", "")),
        str(issue.get("path", "")),
        str(issue.get("message", "")),
        details_json,
    )


def _parse_ring(
    *,
    raw: Any,
    path: str,
    issues: list[dict[str, Any]],
) -> list[list[float]] | None:
    if not isinstance(raw, list):
        _add_issue(
            issues,
            code="GEO_RING_TYPE",
            severity="error",
            path=path,
            message="ring must be an array of points",
        )
        return None
    if len(raw) < 3:
        _add_issue(
            issues,
            code="GEO_RING_TOO_SHORT",
            severity="error",
            path=path,
            message="ring must contain at least 3 points",
        )
        return None

    ring: list[list[float]] = []
    for idx, point in enumerate(raw):
        if not isinstance(point, list) or len(point) != 2:
            _add_issue(
                issues,
                code="GEO_POINT_TYPE",
                severity="error",
                path=f"{path}[{idx}]",
                message="point must be [x, y]",
            )
            return None
        x, y = point
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            _add_issue(
                issues,
                code="GEO_POINT_TYPE",
                severity="error",
                path=f"{path}[{idx}]",
                message="point coordinates must be numeric",
            )
            return None
        ring.append([float(x), float(y)])
    return ring


def _compute_bbox_from_rings(
    *,
    outer_ring: list[list[float]],
    hole_rings: list[list[list[float]]],
) -> dict[str, float]:
    points: list[list[float]] = list(outer_ring)
    for ring in hole_rings:
        points.extend(ring)

    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    min_x = min(xs)
    min_y = min(ys)
    max_x = max(xs)
    max_y = max(ys)
    return {
        "min_x": min_x,
        "min_y": min_y,
        "max_x": max_x,
        "max_y": max_y,
        "width": max_x - min_x,
        "height": max_y - min_y,
    }


def _bbox_matches(
    *,
    expected: dict[str, Any],
    computed: dict[str, float],
) -> bool:
    for key, comp in computed.items():
        value = expected.get(key)
        if not isinstance(value, (int, float)):
            return False
        if abs(float(value) - float(comp)) > _BBOX_EPSILON_MM:
            return False
    return True


def _canonical_hash(payload: dict[str, Any]) -> str:
    canonical_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def _run_topology_checks(
    *,
    outer_ring: list[list[float]] | None,
    hole_rings: list[list[list[float]]],
    issues: list[dict[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "engine": "shapely",
        "checked": False,
    }
    if outer_ring is None:
        return result

    try:
        from shapely.geometry import Polygon
        from shapely.validation import explain_validity
    except Exception:  # noqa: BLE001
        _add_issue(
            issues,
            code="GEO_TOPOLOGY_ENGINE_UNAVAILABLE",
            severity="warning",
            path="report_jsonb.topology_checks",
            message="topology checks skipped because shapely is unavailable",
        )
        result["engine"] = "none"
        return result

    try:
        polygon = Polygon(outer_ring, holes=hole_rings)
        outer_polygon = Polygon(outer_ring)
    except Exception as exc:  # noqa: BLE001
        _add_issue(
            issues,
            code="GEO_TOPOLOGY_BUILD_FAILED",
            severity="error",
            path="canonical_geometry_jsonb",
            message=f"failed to build polygon from rings: {exc}",
        )
        result["build_error"] = str(exc)
        return result

    result["checked"] = True
    result["is_valid"] = bool(polygon.is_valid)
    result["area"] = float(polygon.area)
    result["hole_count"] = len(hole_rings)

    if not outer_polygon.is_valid:
        _add_issue(
            issues,
            code="GEO_OUTER_INVALID",
            severity="error",
            path="canonical_geometry_jsonb.outer_ring",
            message=str(explain_validity(outer_polygon)),
        )

    if not polygon.is_valid:
        _add_issue(
            issues,
            code="GEO_TOPOLOGY_INVALID",
            severity="error",
            path="canonical_geometry_jsonb",
            message=str(explain_validity(polygon)),
        )

    for idx, ring in enumerate(hole_rings):
        hole_poly = Polygon(ring)
        if not hole_poly.is_valid:
            _add_issue(
                issues,
                code="GEO_HOLE_INVALID",
                severity="error",
                path=f"canonical_geometry_jsonb.hole_rings[{idx}]",
                message=str(explain_validity(hole_poly)),
            )
            continue

        representative = hole_poly.representative_point()
        if not outer_polygon.contains(representative):
            _add_issue(
                issues,
                code="GEO_HOLE_OUTSIDE_OUTER",
                severity="error",
                path=f"canonical_geometry_jsonb.hole_rings[{idx}]",
                message="hole is not strictly inside outer ring",
            )

    return result


def _build_validation_payload(
    *,
    geometry_revision: dict[str, Any],
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    revision_id = str(geometry_revision.get("id") or "").strip()
    canonical_format_version = str(geometry_revision.get("canonical_format_version") or "").strip()
    canonical_geometry = geometry_revision.get("canonical_geometry_jsonb")

    outer_ring: list[list[float]] | None = None
    hole_rings: list[list[list[float]]] = []

    if not isinstance(canonical_geometry, dict):
        _add_issue(
            issues,
            code="GEO_CANONICAL_MISSING",
            severity="error",
            path="canonical_geometry_jsonb",
            message="canonical geometry payload is missing or invalid",
        )
        canonical_geometry_dict: dict[str, Any] = {}
    else:
        canonical_geometry_dict = canonical_geometry

    payload_format_version = str(canonical_geometry_dict.get("format_version") or "").strip()
    if payload_format_version != canonical_format_version:
        _add_issue(
            issues,
            code="GEO_FORMAT_VERSION_MISMATCH",
            severity="error",
            path="canonical_geometry_jsonb.format_version",
            message="canonical payload format_version does not match geometry revision",
            details={
                "payload": payload_format_version,
                "revision": canonical_format_version,
            },
        )

    if payload_format_version != _EXPECTED_CANONICAL_FORMAT_VERSION:
        _add_issue(
            issues,
            code="GEO_FORMAT_VERSION_UNSUPPORTED",
            severity="error",
            path="canonical_geometry_jsonb.format_version",
            message="unsupported canonical format version for validator",
            details={"expected": _EXPECTED_CANONICAL_FORMAT_VERSION, "got": payload_format_version},
        )

    outer_ring = _parse_ring(raw=canonical_geometry_dict.get("outer_ring"), path="canonical_geometry_jsonb.outer_ring", issues=issues)

    hole_rings_raw = canonical_geometry_dict.get("hole_rings")
    if not isinstance(hole_rings_raw, list):
        _add_issue(
            issues,
            code="GEO_HOLE_RINGS_TYPE",
            severity="error",
            path="canonical_geometry_jsonb.hole_rings",
            message="hole_rings must be an array",
        )
    else:
        for idx, raw_ring in enumerate(hole_rings_raw):
            parsed = _parse_ring(raw=raw_ring, path=f"canonical_geometry_jsonb.hole_rings[{idx}]", issues=issues)
            if parsed is not None:
                hole_rings.append(parsed)

    if outer_ring is not None:
        computed_bbox = _compute_bbox_from_rings(outer_ring=outer_ring, hole_rings=hole_rings)

        payload_bbox = canonical_geometry_dict.get("bbox")
        if not isinstance(payload_bbox, dict) or not _bbox_matches(expected=payload_bbox, computed=computed_bbox):
            _add_issue(
                issues,
                code="GEO_BBOX_PAYLOAD_MISMATCH",
                severity="error",
                path="canonical_geometry_jsonb.bbox",
                message="payload bbox is missing or inconsistent with canonical rings",
                details={"computed": computed_bbox},
            )

        row_bbox = geometry_revision.get("bbox_jsonb")
        if not isinstance(row_bbox, dict) or not _bbox_matches(expected=row_bbox, computed=computed_bbox):
            _add_issue(
                issues,
                code="GEO_BBOX_ROW_MISMATCH",
                severity="error",
                path="geometry_revisions.bbox_jsonb",
                message="geometry_revisions.bbox_jsonb is missing or inconsistent with canonical rings",
                details={"computed": computed_bbox},
            )

    if not isinstance(canonical_geometry_dict.get("normalizer_meta"), dict):
        _add_issue(
            issues,
            code="GEO_NORMALIZER_META_MISSING",
            severity="warning",
            path="canonical_geometry_jsonb.normalizer_meta",
            message="normalizer_meta is missing",
        )

    if not isinstance(canonical_geometry_dict.get("source_lineage"), dict):
        _add_issue(
            issues,
            code="GEO_SOURCE_LINEAGE_MISSING",
            severity="warning",
            path="canonical_geometry_jsonb.source_lineage",
            message="source_lineage is missing",
        )

    canonical_hash = str(geometry_revision.get("canonical_hash_sha256") or "").strip()
    if not canonical_hash:
        _add_issue(
            issues,
            code="GEO_CANONICAL_HASH_MISSING",
            severity="error",
            path="geometry_revisions.canonical_hash_sha256",
            message="canonical hash is missing",
        )
    elif canonical_geometry_dict:
        computed_hash = _canonical_hash(canonical_geometry_dict)
        if canonical_hash != computed_hash:
            _add_issue(
                issues,
                code="GEO_CANONICAL_HASH_MISMATCH",
                severity="error",
                path="geometry_revisions.canonical_hash_sha256",
                message="canonical hash does not match canonical geometry payload",
                details={"expected": computed_hash, "actual": canonical_hash},
            )

    source_hash = str(geometry_revision.get("source_hash_sha256") or "").strip()
    if not source_hash:
        _add_issue(
            issues,
            code="GEO_SOURCE_HASH_MISSING",
            severity="warning",
            path="geometry_revisions.source_hash_sha256",
            message="source hash is missing",
        )

    topology_checks = _run_topology_checks(outer_ring=outer_ring, hole_rings=hole_rings, issues=issues)

    sorted_issues = sorted(issues, key=_issue_sort_key)
    error_count = sum(1 for issue in sorted_issues if issue.get("severity") == "error")
    warning_count = sum(1 for issue in sorted_issues if issue.get("severity") == "warning")
    status = "validated" if error_count == 0 else "rejected"

    summary_jsonb = {
        "is_pass": error_count == 0,
        "issue_count": len(sorted_issues),
        "warning_count": warning_count,
        "error_count": error_count,
        "validator_version": _VALIDATOR_VERSION,
        "canonical_format_version": canonical_format_version,
    }

    report_jsonb = {
        "issues": sorted_issues,
        "severity_summary": {
            "error_count": error_count,
            "warning_count": warning_count,
            "info_count": sum(1 for issue in sorted_issues if issue.get("severity") == "info"),
        },
        "topology_checks": topology_checks,
        "normalizer_meta": canonical_geometry_dict.get("normalizer_meta") if isinstance(canonical_geometry_dict.get("normalizer_meta"), dict) else {},
        "source_lineage": canonical_geometry_dict.get("source_lineage") if isinstance(canonical_geometry_dict.get("source_lineage"), dict) else {},
        "validated_geometry_ref": {
            "geometry_revision_id": revision_id,
            "canonical_hash_sha256": canonical_hash,
            "canonical_format_version": canonical_format_version,
            "source_hash_sha256": source_hash,
        },
    }

    return status, summary_jsonb, report_jsonb


def _next_validation_seq(
    *,
    supabase: SupabaseClient,
    access_token: str,
    geometry_revision_id: str,
) -> int:
    params = {
        "select": "validation_seq",
        "geometry_revision_id": f"eq.{geometry_revision_id}",
        "order": "validation_seq.desc",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.geometry_validation_reports", access_token=access_token, params=params)
    if not rows:
        return 1

    latest = rows[0].get("validation_seq")
    try:
        latest_seq = int(latest)
    except (TypeError, ValueError):
        latest_seq = 0
    if latest_seq < 0:
        latest_seq = 0
    return latest_seq + 1


def create_geometry_validation_report(
    *,
    supabase: SupabaseClient,
    access_token: str,
    geometry_revision: dict[str, Any],
) -> dict[str, Any]:
    geometry_revision_id = str(geometry_revision.get("id") or "").strip()
    if not geometry_revision_id:
        raise ValueError("missing geometry revision id")

    status, summary_jsonb, report_jsonb = _build_validation_payload(geometry_revision=geometry_revision)
    validation_seq = _next_validation_seq(
        supabase=supabase,
        access_token=access_token,
        geometry_revision_id=geometry_revision_id,
    )

    source_hash = str(geometry_revision.get("source_hash_sha256") or "").strip() or None

    validation_report = supabase.insert_row(
        table="app.geometry_validation_reports",
        access_token=access_token,
        payload={
            "geometry_revision_id": geometry_revision_id,
            "validation_seq": validation_seq,
            "status": status,
            "validator_version": _VALIDATOR_VERSION,
            "summary_jsonb": summary_jsonb,
            "report_jsonb": report_jsonb,
            "source_hash_sha256": source_hash,
        },
    )

    updated_rows = supabase.update_rows(
        table="app.geometry_revisions",
        access_token=access_token,
        payload={"status": status},
        filters={"id": f"eq.{geometry_revision_id}"},
    )
    if updated_rows:
        updated_geometry_revision = updated_rows[0]
    else:
        updated_geometry_revision = dict(geometry_revision)
        updated_geometry_revision["status"] = status

    return {
        "geometry_revision": updated_geometry_revision,
        "validation_report": validation_report,
    }
