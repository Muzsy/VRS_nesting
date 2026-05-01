#!/usr/bin/env python3
"""DXF Prefilter E2-T4 -- duplicate contour dedupe service (V1).

This module is the duplicate-contour dedupe backend layer in the DXF prefilter
lane. It sits on top of:

* the E2-T1 inspect result (``inspect_dxf_source`` output),
* the E2-T2 role resolution (``resolve_dxf_roles`` output),
* the E2-T3 gap repair result (``repair_dxf_gaps`` output),
* a minimal rules profile slice.

It produces a deterministic dedupe-aware closed-contour working truth:

* ``closed_contour_inventory`` -- original importer-probe rings plus T3 repaired
  rings in one role-aware inventory,
* ``duplicate_candidate_inventory`` -- evaluated pair candidates and their
  tolerance/topology status,
* ``applied_duplicate_dedupes`` -- keeper/drop decisions for unambiguous groups,
* ``deduped_contour_working_set`` -- cut-like closed contours after dedupe,
* ``remaining_duplicate_candidates`` -- unresolved duplicate situations,
* ``review_required_candidates`` / ``blocking_conflicts`` -- policy-routed
  conflict families,
* ``diagnostics`` -- explicit separation of inspect exact-duplicate signal
  versus T4 tolerance-based keeper/drop decisions.

Scope boundary (intentional):

* uses the existing importer public probe surface
  (``normalize_source_entities`` + ``probe_layer_rings``) and does not implement
  a new DXF parser,
* does not reopen role assignment policy (reads ``role_resolution`` only),
* does not perform gap repair (reads ``gap_repair_result`` only),
* does not write normalized DXF artifacts (T5 scope),
* does not emit acceptance outcomes (T6 scope),
* does not touch DB persistence, API routes, or frontend UI.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from vrs_nesting.dxf.importer import DxfImportError, normalize_source_entities, probe_layer_rings

__all__ = [
    "DxfPreflightDuplicateDedupeError",
    "dedupe_dxf_duplicate_contours",
]


_CUT_LIKE_ROLES: frozenset[str] = frozenset({"CUT_OUTER", "CUT_INNER"})
_ALLOWED_RULES_PROFILE_FIELDS: frozenset[str] = frozenset(
    {
        "auto_repair_enabled",
        "duplicate_contour_merge_tolerance_mm",
        "strict_mode",
        "interactive_review_on_ambiguity",
    }
)
_DEFAULT_DUPLICATE_MERGE_TOLERANCE_MM: float = 0.05
_POINT_CLOSE_EPSILON_MM: float = 1e-9


class DxfPreflightDuplicateDedupeError(RuntimeError):
    """Raised for structural misuse of the T4 boundary."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def dedupe_dxf_duplicate_contours(
    inspect_result: Mapping[str, Any],
    role_resolution: Mapping[str, Any],
    gap_repair_result: Mapping[str, Any],
    rules_profile: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run deterministic duplicate-contour dedupe on cut-like closed contours."""
    if not isinstance(inspect_result, Mapping):
        raise DxfPreflightDuplicateDedupeError(
            "DXF_DUPLICATE_DEDUPE_INVALID_INSPECT_RESULT",
            "inspect_result must be a mapping as produced by inspect_dxf_source().",
        )
    if not isinstance(role_resolution, Mapping):
        raise DxfPreflightDuplicateDedupeError(
            "DXF_DUPLICATE_DEDUPE_INVALID_ROLE_RESOLUTION",
            "role_resolution must be a mapping as produced by resolve_dxf_roles().",
        )
    if not isinstance(gap_repair_result, Mapping):
        raise DxfPreflightDuplicateDedupeError(
            "DXF_DUPLICATE_DEDUPE_INVALID_GAP_REPAIR_RESULT",
            "gap_repair_result must be a mapping as produced by repair_dxf_gaps().",
        )

    profile = _normalize_rules_profile(rules_profile if rules_profile is not None else {})

    layer_roles = _extract_layer_roles(role_resolution)
    cut_like_layers = {layer: role for layer, role in layer_roles.items() if role in _CUT_LIKE_ROLES}
    contour_roles = _extract_contour_roles(role_resolution)

    review_required_candidates: list[dict[str, Any]] = []
    blocking_conflicts: list[dict[str, Any]] = []

    # Build original closed contour inventory from importer probe truth.
    source_path_raw = str(inspect_result.get("source_path", ""))
    source_load_error: dict[str, Any] | None = None
    original_contours: list[dict[str, Any]] = []

    entities: list[dict[str, Any]] = []
    if source_path_raw:
        source_path = Path(source_path_raw)
        if source_path.is_file():
            try:
                entities = normalize_source_entities(source_path)
            except DxfImportError as exc:
                source_load_error = {"code": exc.code, "message": exc.message}
        else:
            source_load_error = {
                "code": "DXF_DUPLICATE_DEDUPE_SOURCE_NOT_FOUND",
                "message": f"source_path not accessible: {source_path_raw}",
            }

    if contour_roles:
        # Contour-level role truth is available: use it instead of layer-level roles.
        # Probe each layer that appears in contour_roles.
        layers_to_probe = sorted({layer for layer, _ in contour_roles})
        for layer in layers_to_probe:
            if not entities:
                break
            probe = probe_layer_rings(entities, layer=layer)
            hard_error = probe.get("hard_error")
            if isinstance(hard_error, Mapping):
                _emit_conflict(
                    review_required_candidates,
                    blocking_conflicts,
                    family="duplicate_topology_not_safe",
                    strict_mode=profile["strict_mode"],
                    interactive_review=profile["interactive_review_on_ambiguity"],
                    payload={
                        "layer": layer,
                        "canonical_role": "contour_level",
                        "source": "importer_probe",
                        "error_code": str(hard_error.get("code", "UNKNOWN")),
                        "error_message": str(hard_error.get("message", "")),
                    },
                )
                continue

            rings = probe.get("rings")
            if not isinstance(rings, list):
                continue

            for ring_index, ring in enumerate(rings):
                canonical_role = contour_roles.get((layer, ring_index))
                if canonical_role not in _CUT_LIKE_ROLES:
                    continue
                normalized = _normalize_ring_points(ring)
                if normalized is None:
                    continue
                contour_id = f"orig:{layer}:{ring_index}"
                original_contours.append(
                    {
                        "contour_id": contour_id,
                        "layer": layer,
                        "canonical_role": canonical_role,
                        "source": "importer_probe",
                        "source_detail": "T1_importer_probe",
                        "origin_index": ring_index,
                        "source_priority": 0,
                        "canonical_layer_priority": 0 if layer == canonical_role else 1,
                        "point_count": len(normalized),
                        "points": normalized,
                        "bbox": _bbox_of_points(normalized),
                        "dedupe_eligible": True,
                    }
                )
    else:
        # Fallback: use layer-level cut roles (original behaviour).
        for layer, canonical_role in sorted(cut_like_layers.items()):
            if not entities:
                break
            probe = probe_layer_rings(entities, layer=layer)
            hard_error = probe.get("hard_error")
            if isinstance(hard_error, Mapping):
                _emit_conflict(
                    review_required_candidates,
                    blocking_conflicts,
                    family="duplicate_topology_not_safe",
                    strict_mode=profile["strict_mode"],
                    interactive_review=profile["interactive_review_on_ambiguity"],
                    payload={
                        "layer": layer,
                        "canonical_role": canonical_role,
                        "source": "importer_probe",
                        "error_code": str(hard_error.get("code", "UNKNOWN")),
                        "error_message": str(hard_error.get("message", "")),
                    },
                )
                continue

            rings = probe.get("rings")
            if not isinstance(rings, list):
                continue

            for ring_index, ring in enumerate(rings):
                normalized = _normalize_ring_points(ring)
                if normalized is None:
                    continue
                contour_id = f"orig:{layer}:{ring_index}"
                original_contours.append(
                    {
                        "contour_id": contour_id,
                        "layer": layer,
                        "canonical_role": canonical_role,
                        "source": "importer_probe",
                        "source_detail": "T1_importer_probe",
                        "origin_index": ring_index,
                        "source_priority": 0,
                        "canonical_layer_priority": 0 if layer == canonical_role else 1,
                        "point_count": len(normalized),
                        "points": normalized,
                        "bbox": _bbox_of_points(normalized),
                        "dedupe_eligible": True,
                    }
                )

    # Add T3 repaired closed contours to the same inventory.
    repaired_contours: list[dict[str, Any]] = []
    repaired_paths = gap_repair_result.get("repaired_path_working_set")
    if isinstance(repaired_paths, list):
        for repaired_index, repaired in enumerate(repaired_paths):
            if not isinstance(repaired, Mapping):
                continue
            layer = str(repaired.get("layer", ""))
            canonical_role = str(repaired.get("canonical_role", ""))
            points = repaired.get("points")
            normalized = _normalize_ring_points(points)
            if normalized is None:
                continue
            source_label = str(repaired.get("source", "T3_gap_repair"))
            contour_id = f"t3:{layer}:{repaired_index}"
            repaired_contours.append(
                {
                    "contour_id": contour_id,
                    "layer": layer,
                    "canonical_role": canonical_role,
                    "source": source_label,
                    "source_detail": "T3_gap_repair",
                    "origin_index": repaired_index,
                    "source_priority": 1,
                    "canonical_layer_priority": 0 if layer == canonical_role else 1,
                    "point_count": len(normalized),
                    "points": normalized,
                    "bbox": _bbox_of_points(normalized),
                    "dedupe_eligible": canonical_role in _CUT_LIKE_ROLES,
                }
            )

    closed_contour_inventory_raw = original_contours + repaired_contours

    # Track inspect exact-duplicate signal for diagnostics/evidence separation.
    inspect_exact_refs = _extract_inspect_exact_duplicate_refs(inspect_result)
    inspect_exact_groups = _extract_inspect_exact_duplicate_groups(inspect_result)

    # Candidate evaluation.
    duplicate_candidate_inventory: list[dict[str, Any]] = []
    remaining_duplicate_candidates: list[dict[str, Any]] = []
    duplicate_edges: list[tuple[str, str, float]] = []

    by_id: dict[str, dict[str, Any]] = {
        str(item["contour_id"]): item for item in closed_contour_inventory_raw
    }

    eligible = [item for item in closed_contour_inventory_raw if bool(item.get("dedupe_eligible"))]
    eligible_sorted = sorted(eligible, key=lambda item: str(item["contour_id"]))

    tol = float(profile["duplicate_contour_merge_tolerance_mm"])

    for i, left in enumerate(eligible_sorted):
        for right in eligible_sorted[i + 1 :]:
            pair_key = _pair_key(str(left["contour_id"]), str(right["contour_id"]))
            if pair_key not in inspect_exact_refs and not _bbox_close(
                left["bbox"],
                right["bbox"],
                margin=max(tol * 2.0, 1e-6),
            ):
                continue

            role_left = str(left["canonical_role"])
            role_right = str(right["canonical_role"])

            # Topology-safe duplicate check requires same point count and role-safe rings.
            distance = _ring_alignment_distance(
                left["points"],
                right["points"],
            )

            if distance is None:
                duplicate_candidate_inventory.append(
                    {
                        "candidate_pair": [
                            _contour_ref(left),
                            _contour_ref(right),
                        ],
                        "status": "topology_not_safe",
                        "reason": "point_count_mismatch_or_invalid_ring",
                    }
                )
                _emit_conflict(
                    review_required_candidates,
                    blocking_conflicts,
                    family="duplicate_topology_not_safe",
                    strict_mode=profile["strict_mode"],
                    interactive_review=profile["interactive_review_on_ambiguity"],
                    payload={
                        "canonical_role_left": role_left,
                        "canonical_role_right": role_right,
                        "pair": [_contour_ref(left), _contour_ref(right)],
                    },
                )
                remaining_duplicate_candidates.append(
                    {
                        "family": "duplicate_topology_not_safe",
                        "pair": [_contour_ref(left), _contour_ref(right)],
                        "reason": "point_count_mismatch_or_invalid_ring",
                    }
                )
                continue

            if distance <= tol:
                if role_left == role_right:
                    duplicate_edges.append((str(left["contour_id"]), str(right["contour_id"]), distance))
                    duplicate_candidate_inventory.append(
                        {
                            "candidate_pair": [
                                _contour_ref(left),
                                _contour_ref(right),
                            ],
                            "status": "within_tolerance_same_role",
                            "canonical_role": role_left,
                            "alignment_distance_mm": round(distance, 6),
                            "duplicate_contour_merge_tolerance_mm": tol,
                            "inspect_exact_signal": pair_key in inspect_exact_refs,
                        }
                    )
                else:
                    duplicate_candidate_inventory.append(
                        {
                            "candidate_pair": [
                                _contour_ref(left),
                                _contour_ref(right),
                            ],
                            "status": "within_tolerance_cross_role",
                            "alignment_distance_mm": round(distance, 6),
                            "duplicate_contour_merge_tolerance_mm": tol,
                        }
                    )
                    _emit_conflict(
                        review_required_candidates,
                        blocking_conflicts,
                        family="duplicate_cross_role_conflict",
                        strict_mode=profile["strict_mode"],
                        interactive_review=profile["interactive_review_on_ambiguity"],
                        payload={
                            "canonical_role_left": role_left,
                            "canonical_role_right": role_right,
                            "pair": [_contour_ref(left), _contour_ref(right)],
                            "alignment_distance_mm": round(distance, 6),
                        },
                    )
                    remaining_duplicate_candidates.append(
                        {
                            "family": "duplicate_cross_role_conflict",
                            "pair": [_contour_ref(left), _contour_ref(right)],
                            "alignment_distance_mm": round(distance, 6),
                        }
                    )
            else:
                duplicate_candidate_inventory.append(
                    {
                        "candidate_pair": [
                            _contour_ref(left),
                            _contour_ref(right),
                        ],
                        "status": "over_tolerance",
                        "canonical_role_left": role_left,
                        "canonical_role_right": role_right,
                        "alignment_distance_mm": round(distance, 6),
                        "duplicate_contour_merge_tolerance_mm": tol,
                    }
                )
                if role_left == role_right:
                    _emit_conflict(
                        review_required_candidates,
                        blocking_conflicts,
                        family="duplicate_candidate_over_tolerance",
                        strict_mode=profile["strict_mode"],
                        interactive_review=profile["interactive_review_on_ambiguity"],
                        payload={
                            "canonical_role": role_left,
                            "pair": [_contour_ref(left), _contour_ref(right)],
                            "alignment_distance_mm": round(distance, 6),
                            "duplicate_contour_merge_tolerance_mm": tol,
                        },
                    )
                    remaining_duplicate_candidates.append(
                        {
                            "family": "duplicate_candidate_over_tolerance",
                            "pair": [_contour_ref(left), _contour_ref(right)],
                            "alignment_distance_mm": round(distance, 6),
                            "duplicate_contour_merge_tolerance_mm": tol,
                        }
                    )

    # Build duplicate groups from same-role within-threshold edges.
    groups = _build_duplicate_groups(duplicate_edges)

    applied_duplicate_dedupes: list[dict[str, Any]] = []
    dropped_contour_ids: set[str] = set()

    for group_index, group in enumerate(groups):
        records = [by_id[contour_id] for contour_id in sorted(group)]
        if len(records) < 2:
            continue

        canonical_roles = {str(record["canonical_role"]) for record in records}
        canonical_role = sorted(canonical_roles)[0]

        if not profile["auto_repair_enabled"]:
            _emit_conflict(
                review_required_candidates,
                blocking_conflicts,
                family="duplicate_dedupe_disabled_by_profile",
                strict_mode=profile["strict_mode"],
                interactive_review=profile["interactive_review_on_ambiguity"],
                payload={
                    "canonical_role": canonical_role,
                    "group": [_contour_ref(record) for record in records],
                },
            )
            remaining_duplicate_candidates.append(
                {
                    "family": "duplicate_dedupe_disabled_by_profile",
                    "canonical_role": canonical_role,
                    "group": [_contour_ref(record) for record in records],
                }
            )
            _emit_conflict(
                review_required_candidates,
                blocking_conflicts,
                family="cut_like_duplicate_remaining_after_dedupe",
                strict_mode=profile["strict_mode"],
                interactive_review=profile["interactive_review_on_ambiguity"],
                payload={
                    "canonical_role": canonical_role,
                    "group": [_contour_ref(record) for record in records],
                    "reason": "duplicate_dedupe_disabled_by_profile",
                },
            )
            continue

        ordered = sorted(records, key=_keeper_rank_key)
        best = ordered[0]
        best_bucket = (int(best["source_priority"]), int(best["canonical_layer_priority"]))
        top_bucket = [
            record
            for record in ordered
            if (
                int(record["source_priority"]),
                int(record["canonical_layer_priority"]),
            )
            == best_bucket
        ]

        # Ambiguous if only T3-repaired records are present at strongest precedence.
        if len(top_bucket) > 1 and best_bucket[0] > 0:
            _emit_conflict(
                review_required_candidates,
                blocking_conflicts,
                family="ambiguous_duplicate_group",
                strict_mode=profile["strict_mode"],
                interactive_review=profile["interactive_review_on_ambiguity"],
                payload={
                    "canonical_role": canonical_role,
                    "group": [_contour_ref(record) for record in records],
                    "ambiguity_reason": "multiple_t3_repaired_candidates_same_precedence",
                },
            )
            remaining_duplicate_candidates.append(
                {
                    "family": "ambiguous_duplicate_group",
                    "canonical_role": canonical_role,
                    "group": [_contour_ref(record) for record in records],
                }
            )
            _emit_conflict(
                review_required_candidates,
                blocking_conflicts,
                family="cut_like_duplicate_remaining_after_dedupe",
                strict_mode=profile["strict_mode"],
                interactive_review=profile["interactive_review_on_ambiguity"],
                payload={
                    "canonical_role": canonical_role,
                    "group": [_contour_ref(record) for record in records],
                    "reason": "ambiguous_duplicate_group",
                },
            )
            continue

        dropped = [record for record in ordered[1:]]
        for record in dropped:
            dropped_contour_ids.add(str(record["contour_id"]))

        applied_duplicate_dedupes.append(
            {
                "group_id": f"duplicate_group_{group_index}",
                "canonical_role": canonical_role,
                "keeper": _contour_ref(best),
                "keeper_evidence": {
                    "source_priority": int(best["source_priority"]),
                    "canonical_layer_priority": int(best["canonical_layer_priority"]),
                    "selection_policy": (
                        "original importer-probe contour preferred over T3_gap_repair; "
                        "then canonical source layer preferred; then stable tie-break "
                        "(layer, source, origin_index, contour_id)."
                    ),
                    "tie_break_key": list(_keeper_rank_key(best)),
                },
                "dropped": [
                    {
                        "contour": _contour_ref(record),
                        "drop_reason": "duplicate_within_tolerance",
                    }
                    for record in dropped
                ],
            }
        )

    # Deduped working set is cut-like closed world after keeper/drop decisions.
    deduped_contour_working_set = [
        _working_set_item(record)
        for record in sorted(eligible_sorted, key=_keeper_rank_key)
        if str(record["contour_id"]) not in dropped_contour_ids
    ]

    closed_contour_inventory = [
        _inventory_item(record)
        for record in sorted(closed_contour_inventory_raw, key=_keeper_rank_key)
    ]

    diagnostics = _build_diagnostics(
        profile=profile,
        source_load_error=source_load_error,
        inspect_exact_groups=inspect_exact_groups,
        duplicate_candidate_inventory=duplicate_candidate_inventory,
        applied_duplicate_dedupes=applied_duplicate_dedupes,
        remaining_duplicate_candidates=remaining_duplicate_candidates,
    )

    return {
        "rules_profile_echo": profile["echo"],
        "closed_contour_inventory": closed_contour_inventory,
        "duplicate_candidate_inventory": duplicate_candidate_inventory,
        "applied_duplicate_dedupes": applied_duplicate_dedupes,
        "deduped_contour_working_set": deduped_contour_working_set,
        "remaining_duplicate_candidates": remaining_duplicate_candidates,
        "review_required_candidates": review_required_candidates,
        "blocking_conflicts": blocking_conflicts,
        "diagnostics": diagnostics,
    }


# ---------------------------------------------------------------------------
# Rules profile
# ---------------------------------------------------------------------------


def _normalize_rules_profile(rules_profile: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(rules_profile, Mapping):
        raise DxfPreflightDuplicateDedupeError(
            "DXF_DUPLICATE_DEDUPE_INVALID_RULES_PROFILE",
            "rules_profile must be a mapping.",
        )

    accepted: dict[str, Any] = {}
    ignored: set[str] = set()
    for key, value in rules_profile.items():
        key_str = str(key)
        if key_str in _ALLOWED_RULES_PROFILE_FIELDS:
            accepted[key_str] = value
        else:
            ignored.add(key_str)

    auto_repair_enabled = _coerce_bool(accepted.get("auto_repair_enabled"), default=False)
    tolerance_mm = _coerce_positive_float(
        accepted.get("duplicate_contour_merge_tolerance_mm"),
        default=_DEFAULT_DUPLICATE_MERGE_TOLERANCE_MM,
    )
    strict_mode = _coerce_bool(accepted.get("strict_mode"), default=False)
    interactive_review = _coerce_bool(
        accepted.get("interactive_review_on_ambiguity"),
        default=True,
    )

    echo = {
        "auto_repair_enabled": auto_repair_enabled,
        "duplicate_contour_merge_tolerance_mm": tolerance_mm,
        "strict_mode": strict_mode,
        "interactive_review_on_ambiguity": interactive_review,
    }

    return {
        "echo": echo,
        "auto_repair_enabled": auto_repair_enabled,
        "duplicate_contour_merge_tolerance_mm": tolerance_mm,
        "strict_mode": strict_mode,
        "interactive_review_on_ambiguity": interactive_review,
        "accepted_fields": set(accepted.keys()),
        "ignored_fields": ignored,
    }


# ---------------------------------------------------------------------------
# Role + inspect extraction
# ---------------------------------------------------------------------------


def _extract_layer_roles(role_resolution: Mapping[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    assignments = role_resolution.get("layer_role_assignments")
    if not isinstance(assignments, list):
        return out
    for record in assignments:
        if not isinstance(record, Mapping):
            continue
        layer = str(record.get("layer", ""))
        canonical_role = str(record.get("canonical_role", ""))
        if layer:
            out[layer] = canonical_role
    return out


def _extract_contour_roles(
    role_resolution: Mapping[str, Any],
) -> dict[tuple[str, int], str]:
    """Extract contour-level role assignments as {(layer, ring_index): canonical_role}."""
    out: dict[tuple[str, int], str] = {}
    assignments = role_resolution.get("contour_role_assignments")
    if not isinstance(assignments, list):
        return out
    for record in assignments:
        if not isinstance(record, Mapping):
            continue
        layer = str(record.get("layer", ""))
        ring_index = _as_int(record.get("ring_index"), default=-1)
        canonical_role = str(record.get("canonical_role", ""))
        if layer and ring_index >= 0 and canonical_role in _CUT_LIKE_ROLES:
            out[(layer, ring_index)] = canonical_role
    return out


def _extract_inspect_exact_duplicate_groups(
    inspect_result: Mapping[str, Any],
) -> list[dict[str, Any]]:
    raw = inspect_result.get("duplicate_contour_candidates")
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        refs_raw = item.get("ring_references")
        refs: list[dict[str, Any]] = []
        if isinstance(refs_raw, list):
            for ref in refs_raw:
                if not isinstance(ref, Mapping):
                    continue
                layer = str(ref.get("layer", ""))
                ring_index = _as_int(ref.get("ring_index"), default=-1)
                if layer and ring_index >= 0:
                    refs.append({"layer": layer, "ring_index": ring_index})
        if not refs:
            continue
        out.append(
            {
                "fingerprint": str(item.get("fingerprint", "")),
                "count": len(refs),
                "ring_references": sorted(refs, key=lambda r: (r["layer"], r["ring_index"])),
            }
        )
    return out


def _extract_inspect_exact_duplicate_refs(
    inspect_result: Mapping[str, Any],
) -> set[tuple[str, str]]:
    groups = _extract_inspect_exact_duplicate_groups(inspect_result)
    out: set[tuple[str, str]] = set()
    for group in groups:
        refs = group["ring_references"]
        contour_ids = [f"orig:{ref['layer']}:{int(ref['ring_index'])}" for ref in refs]
        for i, left in enumerate(contour_ids):
            for right in contour_ids[i + 1 :]:
                out.add(_pair_key(left, right))
    return out


# ---------------------------------------------------------------------------
# Duplicate grouping + ranking
# ---------------------------------------------------------------------------


def _build_duplicate_groups(edges: list[tuple[str, str, float]]) -> list[set[str]]:
    if not edges:
        return []

    parent: dict[str, str] = {}

    def find(x: str) -> str:
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != x:
            nxt = parent[x]
            parent[x] = root
            x = nxt
        return root

    def union(a: str, b: str) -> None:
        ra = find(a)
        rb = find(b)
        if ra != rb:
            if ra < rb:
                parent[rb] = ra
            else:
                parent[ra] = rb

    for a, b, _distance in edges:
        if a not in parent:
            parent[a] = a
        if b not in parent:
            parent[b] = b
        union(a, b)

    groups: dict[str, set[str]] = {}
    for node in sorted(parent):
        root = find(node)
        groups.setdefault(root, set()).add(node)

    out = [members for members in groups.values() if len(members) > 1]
    out.sort(key=lambda members: sorted(members))
    return out


def _keeper_rank_key(record: dict[str, Any]) -> tuple[int, int, str, str, int, str]:
    return (
        int(record["source_priority"]),
        int(record["canonical_layer_priority"]),
        str(record["layer"]),
        str(record["source"]),
        int(record["origin_index"]),
        str(record["contour_id"]),
    )


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------


def _normalize_ring_points(raw_points: Any) -> list[list[float]] | None:
    if not isinstance(raw_points, list):
        return None
    parsed: list[list[float]] = []
    for point in raw_points:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            return None
        x = _as_float(point[0], default=math.nan)
        y = _as_float(point[1], default=math.nan)
        if not math.isfinite(x) or not math.isfinite(y):
            return None
        parsed.append([x, y])

    if len(parsed) < 3:
        return None

    if _distance(parsed[0], parsed[-1]) <= _POINT_CLOSE_EPSILON_MM:
        parsed = parsed[:-1]

    if len(parsed) < 3:
        return None

    return parsed


def _bbox_of_points(points: list[list[float]]) -> dict[str, float]:
    xs = [float(p[0]) for p in points]
    ys = [float(p[1]) for p in points]
    return {
        "min_x": min(xs),
        "min_y": min(ys),
        "max_x": max(xs),
        "max_y": max(ys),
    }


def _bbox_close(left: dict[str, float], right: dict[str, float], *, margin: float) -> bool:
    return (
        abs(float(left["min_x"]) - float(right["min_x"])) <= margin
        and abs(float(left["min_y"]) - float(right["min_y"])) <= margin
        and abs(float(left["max_x"]) - float(right["max_x"])) <= margin
        and abs(float(left["max_y"]) - float(right["max_y"])) <= margin
    )


def _ring_alignment_distance(
    ring_a: list[list[float]],
    ring_b: list[list[float]],
) -> float | None:
    """Return min max-point distance across cyclic shifts and both orientations.

    Returns ``None`` for topology-unsafe comparisons (different vertex count or
    too-short rings).
    """
    n = len(ring_a)
    if n != len(ring_b) or n < 3:
        return None

    best = math.inf
    for orientation in (ring_b, list(reversed(ring_b))):
        for shift in range(n):
            max_dist = 0.0
            for idx in range(n):
                a = ring_a[idx]
                b = orientation[(idx + shift) % n]
                dist = _distance(a, b)
                if dist > max_dist:
                    max_dist = dist
                if max_dist >= best:
                    break
            if max_dist < best:
                best = max_dist
    return best


# ---------------------------------------------------------------------------
# Record builders
# ---------------------------------------------------------------------------


def _contour_ref(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "contour_id": str(record["contour_id"]),
        "layer": str(record["layer"]),
        "canonical_role": str(record["canonical_role"]),
        "source": str(record["source"]),
        "origin_index": int(record["origin_index"]),
    }


def _inventory_item(record: dict[str, Any]) -> dict[str, Any]:
    return {
        **_contour_ref(record),
        "point_count": int(record["point_count"]),
        "bbox": dict(record["bbox"]),
        "dedupe_eligible": bool(record["dedupe_eligible"]),
    }


def _working_set_item(record: dict[str, Any]) -> dict[str, Any]:
    return {
        **_contour_ref(record),
        "point_count": int(record["point_count"]),
        "points": [[float(p[0]), float(p[1])] for p in record["points"]],
    }


# ---------------------------------------------------------------------------
# Conflict + diagnostics
# ---------------------------------------------------------------------------


def _emit_conflict(
    review_required: list[dict[str, Any]],
    blocking: list[dict[str, Any]],
    *,
    family: str,
    strict_mode: bool,
    interactive_review: bool,
    payload: dict[str, Any],
) -> None:
    severity = "blocking" if (strict_mode or not interactive_review) else "review_required"
    record: dict[str, Any] = {"family": family, "severity": severity}
    record.update(payload)
    if severity == "blocking":
        blocking.append(record)
    else:
        review_required.append(record)


def _build_diagnostics(
    *,
    profile: dict[str, Any],
    source_load_error: dict[str, Any] | None,
    inspect_exact_groups: list[dict[str, Any]],
    duplicate_candidate_inventory: list[dict[str, Any]],
    applied_duplicate_dedupes: list[dict[str, Any]],
    remaining_duplicate_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    notes = [
        (
            "inspect_exact_signal_layer: inspect_result['duplicate_contour_candidates'] "
            "is an exact fingerprint-level signal only; it does not perform "
            "tolerance-based keeper/drop decisions."
        ),
        (
            "t4_tolerance_decision_layer: T4 evaluates duplicate equivalence with "
            "duplicate_contour_merge_tolerance_mm and applies deterministic "
            "keeper/drop policy only within cut-like closed contour world."
        ),
        (
            "keeper_policy: original importer-probe contour preferred over "
            "T3_gap_repair contour; then canonical source-layer preference; "
            "then stable tie-break (layer, source, origin_index, contour_id)."
        ),
        (
            "t5_t6_scope_boundary: normalized DXF writer remains T5 scope; "
            "acceptance gate remains T6 scope."
        ),
    ]

    return {
        "rules_profile_source_fields_accepted": sorted(profile["accepted_fields"]),
        "rules_profile_source_fields_ignored": sorted(profile["ignored_fields"]),
        "source_load_error": source_load_error,
        "inspect_exact_duplicate_signal_count": len(inspect_exact_groups),
        "inspect_exact_duplicate_signals": inspect_exact_groups,
        "t4_duplicate_candidate_count": len(duplicate_candidate_inventory),
        "t4_applied_dedupe_count": len(applied_duplicate_dedupes),
        "t4_remaining_duplicate_count": len(remaining_duplicate_candidates),
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# Primitive helpers
# ---------------------------------------------------------------------------


def _pair_key(left_id: str, right_id: str) -> tuple[str, str]:
    return (left_id, right_id) if left_id < right_id else (right_id, left_id)


def _distance(a: list[float], b: list[float]) -> float:
    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))


def _as_int(value: Any, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    return default


def _as_float(value: Any, *, default: float) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _coerce_bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise DxfPreflightDuplicateDedupeError(
        "DXF_DUPLICATE_DEDUPE_INVALID_RULES_PROFILE",
        f"expected bool for rules-profile field, got {type(value).__name__}",
    )


def _coerce_positive_float(value: Any, *, default: float) -> float:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DxfPreflightDuplicateDedupeError(
            "DXF_DUPLICATE_DEDUPE_INVALID_RULES_PROFILE",
            f"expected positive numeric rules-profile field, got {type(value).__name__}",
        )
    value_f = float(value)
    if not math.isfinite(value_f) or value_f <= 0:
        raise DxfPreflightDuplicateDedupeError(
            "DXF_DUPLICATE_DEDUPE_INVALID_RULES_PROFILE",
            "duplicate_contour_merge_tolerance_mm must be positive finite number",
        )
    return value_f
