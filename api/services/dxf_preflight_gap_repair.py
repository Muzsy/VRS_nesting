#!/usr/bin/env python3
"""DXF Prefilter E2-T3 -- Gap repair service (V1).

This module is the residual gap repair backend layer of the DXF prefilter lane.
It sits on top of:

* the E2-T1 inspect result (``inspect_dxf_source`` output),
* the E2-T2 role resolution (``resolve_dxf_roles`` output),
* a minimal, in-memory rules profile slice.

It produces a deterministic, repair-aware working truth:

* ``repair_candidate_inventory`` -- all residual gap candidates found,
* ``applied_gap_repairs`` -- repairs that were actually applied,
* ``repaired_path_working_set`` -- closed rings produced by applied repairs,
* ``remaining_open_path_candidates`` -- cut-like open paths that could not
  be repaired (too large, ambiguous, or cross-chain without sealing),
* ``review_required_candidates`` -- ambiguous / disabled / over-threshold
  gap signals requiring human or later-lane attention,
* ``blocking_conflicts`` -- hard-fail gap signals (e.g. strict_mode +
  unresolved cut-like open path, or failed reprobe),
* ``diagnostics`` -- T3-specific notes separating the pre-existing importer
  chaining truth from the new T3 residual gap repair layer.

V1 auto-repair scope (per canvas):
  Only self-closing gaps are auto-repaired: a single open path chain whose
  start and end are within ``max_gap_close_mm`` and where the pairing is
  unambiguous (no competing partner endpoint within that threshold). This
  covers the most common practical case -- a ring with exactly one small gap
  that the importer's chaining could not close within
  ``CHAIN_ENDPOINT_EPSILON_MM`` (0.2 mm).

  Cross-chain endpoint pairs within threshold are detected as candidates but
  V1 does not auto-repair them (joining two chains rarely seals into a ring
  after the importer has already run its greedy chaining). They surface as
  ``review_required_candidates`` with family ``gap_candidate_cross_chain``.

Scope boundary (intentional):

* does NOT re-implement DXF parsing -- uses the public importer probe surface
  (``normalize_source_entities`` + ``probe_layer_open_paths``),
* does NOT reopen the role resolver -- reads ``role_resolution`` exclusively,
* does NOT deduplicate contours (E2-T4 scope),
* does NOT write a normalised DXF file (E2-T5 scope),
* does NOT produce an acceptance outcome (E2-T6 scope),
* does NOT touch DB persistence, API routes or frontend UI.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from vrs_nesting.dxf.importer import (
    CHAIN_ENDPOINT_EPSILON_MM,
    DxfImportError,
    normalize_source_entities,
    probe_layer_open_paths,
)

__all__ = [
    "DxfPreflightGapRepairError",
    "repair_dxf_gaps",
]

_CUT_LIKE_ROLES: frozenset[str] = frozenset({"CUT_OUTER", "CUT_INNER"})

_ALLOWED_RULES_PROFILE_FIELDS: frozenset[str] = frozenset(
    {
        "auto_repair_enabled",
        "max_gap_close_mm",
        "strict_mode",
        "interactive_review_on_ambiguity",
    }
)

_DEFAULT_MAX_GAP_CLOSE_MM: float = 1.0


class DxfPreflightGapRepairError(RuntimeError):
    """Raised for structural misuse of the gap repair boundary.

    DXF-level problems land in ``review_required_candidates`` /
    ``blocking_conflicts`` instead of raising. This exception is reserved
    for caller-error situations (e.g. ``inspect_result`` not a mapping).
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def repair_dxf_gaps(
    inspect_result: Mapping[str, Any],
    role_resolution: Mapping[str, Any],
    rules_profile: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply deterministic residual gap repairs on cut-like open paths (E2-T3).

    Parameters
    ----------
    inspect_result:
        The shape returned by
        ``api.services.dxf_preflight_inspect.inspect_dxf_source``.
        Must contain ``source_path`` for the importer probe to load entities.
    role_resolution:
        The shape returned by
        ``api.services.dxf_preflight_role_resolver.resolve_dxf_roles``.
        Used to identify which layers are cut-like and therefore subject to
        gap repair.
    rules_profile:
        Optional mapping. Only the minimal T3 slice is consumed:
        ``auto_repair_enabled``, ``max_gap_close_mm``, ``strict_mode``,
        ``interactive_review_on_ambiguity``. Other keys are ignored and
        reported in ``diagnostics.rules_profile_source_fields_ignored``.

    Returns
    -------
    dict[str, Any]
        Deterministic, JSON-serialisable result with the shape described in
        the module docstring. Never contains an acceptance outcome, DXF
        artifact, or persistence side-effect.
    """
    if not isinstance(inspect_result, Mapping):
        raise DxfPreflightGapRepairError(
            "DXF_GAP_REPAIR_INVALID_INSPECT_RESULT",
            "inspect_result must be a mapping as produced by inspect_dxf_source().",
        )
    if not isinstance(role_resolution, Mapping):
        raise DxfPreflightGapRepairError(
            "DXF_GAP_REPAIR_INVALID_ROLE_RESOLUTION",
            "role_resolution must be a mapping as produced by resolve_dxf_roles().",
        )

    profile = _normalize_rules_profile(rules_profile if rules_profile is not None else {})

    # Collect cut-like layer → canonical_role mapping from role resolution.
    cut_like_layers = _extract_cut_like_layers(role_resolution)

    # Load source entities via the public importer surface.
    source_path_str = str(inspect_result.get("source_path", ""))
    entities_by_layer: dict[str, list[dict[str, Any]]] = {}
    source_load_error: dict[str, Any] | None = None

    if source_path_str:
        source_path = Path(source_path_str)
        if source_path.is_file():
            try:
                all_entities = normalize_source_entities(source_path)
                for layer in cut_like_layers:
                    probe = probe_layer_open_paths(all_entities, layer=layer)
                    if probe["hard_error"] is None:
                        entities_by_layer[layer] = probe["open_paths"]
            except DxfImportError as exc:
                source_load_error = {"code": exc.code, "message": exc.message}
        else:
            source_load_error = {
                "code": "DXF_GAP_REPAIR_SOURCE_NOT_FOUND",
                "message": f"source_path not accessible: {source_path_str}",
            }

    repair_candidate_inventory: list[dict[str, Any]] = []
    applied_gap_repairs: list[dict[str, Any]] = []
    repaired_path_working_set: list[dict[str, Any]] = []
    remaining_open_path_candidates: list[dict[str, Any]] = []
    review_required_candidates: list[dict[str, Any]] = []
    blocking_conflicts: list[dict[str, Any]] = []

    for layer, canonical_role in sorted(cut_like_layers.items()):
        open_paths = entities_by_layer.get(layer, [])

        if not open_paths:
            continue

        # Build all endpoint pairs with distances.
        candidates = _build_gap_candidates(
            open_paths,
            layer=layer,
            canonical_role=canonical_role,
            max_gap_close_mm=profile["max_gap_close_mm"],
        )
        repair_candidate_inventory.extend(candidates)

        # When auto-repair is disabled, all open paths become review candidates.
        if not profile["auto_repair_enabled"]:
            for path in open_paths:
                _emit_conflict(
                    review_required_candidates,
                    blocking_conflicts,
                    family="gap_repair_disabled_by_profile",
                    strict_mode=profile["strict_mode"],
                    interactive_review=profile["interactive_review_on_ambiguity"],
                    payload={
                        "layer": layer,
                        "canonical_role": canonical_role,
                        "path_index": int(path["path_index"]),
                        "open_path_count": len(open_paths),
                    },
                )
            for path in open_paths:
                remaining_open_path_candidates.append(
                    {
                        "layer": layer,
                        "canonical_role": canonical_role,
                        "path_index": int(path["path_index"]),
                        "reason": "gap_repair_disabled_by_profile",
                    }
                )
            continue

        # Compute endpoint partners within threshold for ambiguity detection.
        partners = _compute_endpoint_partners(
            open_paths, max_gap_close_mm=profile["max_gap_close_mm"]
        )

        repaired_indices: set[int] = set()

        for path in open_paths:
            pi = int(path["path_index"])
            if pi in repaired_indices:
                continue

            sc_candidate = _find_self_closing_candidate(candidates, path_index=pi)
            if sc_candidate is None:
                # No self-closing gap candidate for this path; check cross-chain.
                cross = _find_cross_chain_candidates(candidates, path_index=pi)
                if cross:
                    for c in cross:
                        _emit_conflict(
                            review_required_candidates,
                            blocking_conflicts,
                            family="gap_candidate_cross_chain",
                            strict_mode=profile["strict_mode"],
                            interactive_review=profile["interactive_review_on_ambiguity"],
                            payload={
                                "layer": layer,
                                "canonical_role": canonical_role,
                                "path_a_index": c["path_a_index"],
                                "path_b_index": c["path_b_index"],
                                "gap_distance_mm": c["gap_distance_mm"],
                                "note": "cross_chain_join_not_auto_repaired_in_v1",
                            },
                        )
                remaining_open_path_candidates.append(
                    {
                        "layer": layer,
                        "canonical_role": canonical_role,
                        "path_index": pi,
                        "reason": "no_self_closing_candidate",
                    }
                )
                continue

            gap_dist = float(sc_candidate["gap_distance_mm"])

            # Check threshold.
            if gap_dist > profile["max_gap_close_mm"]:
                _emit_conflict(
                    review_required_candidates,
                    blocking_conflicts,
                    family="gap_candidate_over_threshold",
                    strict_mode=profile["strict_mode"],
                    interactive_review=profile["interactive_review_on_ambiguity"],
                    payload={
                        "layer": layer,
                        "canonical_role": canonical_role,
                        "path_index": pi,
                        "gap_distance_mm": gap_dist,
                        "max_gap_close_mm": profile["max_gap_close_mm"],
                    },
                )
                remaining_open_path_candidates.append(
                    {
                        "layer": layer,
                        "canonical_role": canonical_role,
                        "path_index": pi,
                        "reason": "gap_candidate_over_threshold",
                        "gap_distance_mm": gap_dist,
                    }
                )
                continue

            # Check ambiguity.
            ep_start = (pi, "start")
            ep_end = (pi, "end")
            start_partners = partners.get(ep_start, [])
            end_partners = partners.get(ep_end, [])

            # For self-closing: start's partner should be exclusively (pi, "end")
            # and end's partner should be exclusively (pi, "start").
            start_is_exclusive = len(start_partners) == 1 and start_partners[0][:2] == (pi, "end")
            end_is_exclusive = len(end_partners) == 1 and end_partners[0][:2] == (pi, "start")

            if not start_is_exclusive or not end_is_exclusive:
                _emit_conflict(
                    review_required_candidates,
                    blocking_conflicts,
                    family="ambiguous_gap_partner",
                    strict_mode=profile["strict_mode"],
                    interactive_review=profile["interactive_review_on_ambiguity"],
                    payload={
                        "layer": layer,
                        "canonical_role": canonical_role,
                        "path_index": pi,
                        "gap_distance_mm": gap_dist,
                        "start_partner_count": len(start_partners),
                        "end_partner_count": len(end_partners),
                    },
                )
                remaining_open_path_candidates.append(
                    {
                        "layer": layer,
                        "canonical_role": canonical_role,
                        "path_index": pi,
                        "reason": "ambiguous_gap_partner",
                        "gap_distance_mm": gap_dist,
                    }
                )
                continue

            # Attempt repair.
            repair = _apply_self_closing_repair(
                path,
                layer=layer,
                canonical_role=canonical_role,
                gap_distance_mm=gap_dist,
            )

            if repair is None or not repair["reprobe_passed"]:
                _emit_conflict(
                    review_required_candidates,
                    blocking_conflicts,
                    family="gap_repair_failed_reprobe",
                    strict_mode=profile["strict_mode"],
                    interactive_review=profile["interactive_review_on_ambiguity"],
                    payload={
                        "layer": layer,
                        "canonical_role": canonical_role,
                        "path_index": pi,
                        "gap_distance_mm": gap_dist,
                    },
                )
                remaining_open_path_candidates.append(
                    {
                        "layer": layer,
                        "canonical_role": canonical_role,
                        "path_index": pi,
                        "reason": "gap_repair_failed_reprobe",
                    }
                )
                continue

            repaired_indices.add(pi)
            applied_gap_repairs.append(repair)
            repaired_path_working_set.append(repair["repaired_path"])

        # Paths that remain open after all repairs.
        for path in open_paths:
            pi = int(path["path_index"])
            if pi in repaired_indices:
                continue
            # Check if already recorded as remaining.
            already_remaining = any(
                r["layer"] == layer and r.get("path_index") == pi
                for r in remaining_open_path_candidates
            )
            if not already_remaining:
                _emit_conflict(
                    review_required_candidates,
                    blocking_conflicts,
                    family="cut_like_open_path_remaining_after_repair",
                    strict_mode=profile["strict_mode"],
                    interactive_review=profile["interactive_review_on_ambiguity"],
                    payload={
                        "layer": layer,
                        "canonical_role": canonical_role,
                        "path_index": pi,
                    },
                )
                remaining_open_path_candidates.append(
                    {
                        "layer": layer,
                        "canonical_role": canonical_role,
                        "path_index": pi,
                        "reason": "cut_like_open_path_remaining_after_repair",
                    }
                )

    diagnostics = _build_diagnostics(
        profile=profile,
        applied_gap_repairs=applied_gap_repairs,
        remaining_open_path_candidates=remaining_open_path_candidates,
        source_load_error=source_load_error,
    )

    return {
        "rules_profile_echo": profile["echo"],
        "repair_candidate_inventory": repair_candidate_inventory,
        "applied_gap_repairs": applied_gap_repairs,
        "repaired_path_working_set": repaired_path_working_set,
        "remaining_open_path_candidates": remaining_open_path_candidates,
        "review_required_candidates": review_required_candidates,
        "blocking_conflicts": blocking_conflicts,
        "diagnostics": diagnostics,
    }


# ---------------------------------------------------------------------------
# Rules profile normalisation
# ---------------------------------------------------------------------------


def _normalize_rules_profile(rules_profile: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(rules_profile, Mapping):
        raise DxfPreflightGapRepairError(
            "DXF_GAP_REPAIR_INVALID_RULES_PROFILE",
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
    strict_mode = _coerce_bool(accepted.get("strict_mode"), default=False)
    interactive_review = _coerce_bool(
        accepted.get("interactive_review_on_ambiguity"), default=True
    )
    max_gap_close_mm = _coerce_positive_float(
        accepted.get("max_gap_close_mm"), default=_DEFAULT_MAX_GAP_CLOSE_MM
    )

    echo: dict[str, Any] = {
        "auto_repair_enabled": auto_repair_enabled,
        "max_gap_close_mm": max_gap_close_mm,
        "strict_mode": strict_mode,
        "interactive_review_on_ambiguity": interactive_review,
    }

    return {
        "echo": echo,
        "auto_repair_enabled": auto_repair_enabled,
        "max_gap_close_mm": max_gap_close_mm,
        "strict_mode": strict_mode,
        "interactive_review_on_ambiguity": interactive_review,
        "accepted_fields": set(accepted.keys()),
        "ignored_fields": ignored,
    }


# ---------------------------------------------------------------------------
# Role extraction
# ---------------------------------------------------------------------------


def _extract_cut_like_layers(role_resolution: Mapping[str, Any]) -> dict[str, str]:
    """Return ``{layer: canonical_role}`` for all cut-like layers."""
    result: dict[str, str] = {}
    layer_role_assignments = role_resolution.get("layer_role_assignments")
    if not isinstance(layer_role_assignments, list):
        return result
    for record in layer_role_assignments:
        if not isinstance(record, Mapping):
            continue
        role = str(record.get("canonical_role", ""))
        if role in _CUT_LIKE_ROLES:
            layer = str(record.get("layer", ""))
            if layer:
                result[layer] = role
    return result


# ---------------------------------------------------------------------------
# Gap candidate building
# ---------------------------------------------------------------------------


def _build_gap_candidates(
    open_paths: list[dict[str, Any]],
    *,
    layer: str,
    canonical_role: str,
    max_gap_close_mm: float,
) -> list[dict[str, Any]]:
    """Build all endpoint-pair gap candidates for this layer's open paths."""

    # Each open path has two endpoints: "start" (index 0) and "end" (index -1).
    # We enumerate all pairs (including self-closing: same path, start vs end).
    endpoints: list[tuple[int, str, float, float]] = []
    for path in open_paths:
        pi = int(path["path_index"])
        sx, sy = float(path["start_point"][0]), float(path["start_point"][1])
        ex, ey = float(path["end_point"][0]), float(path["end_point"][1])
        endpoints.append((pi, "start", sx, sy))
        endpoints.append((pi, "end", ex, ey))

    candidates: list[dict[str, Any]] = []
    n = len(endpoints)
    seen: set[frozenset[tuple[int, str]]] = set()

    for a in range(n):
        for b in range(n):
            if a == b:
                continue
            pi_a, pk_a, xa, ya = endpoints[a]
            pi_b, pk_b, xb, yb = endpoints[b]
            # Skip same endpoint of same path.
            if pi_a == pi_b and pk_a == pk_b:
                continue
            pair_key: frozenset[tuple[int, str]] = frozenset(
                {(pi_a, pk_a), (pi_b, pk_b)}
            )
            if pair_key in seen:
                continue
            seen.add(pair_key)

            dist = math.hypot(xa - xb, ya - yb)
            repair_type = "self_closing" if pi_a == pi_b else "cross_chain"
            candidates.append(
                {
                    "layer": layer,
                    "canonical_role": canonical_role,
                    "path_a_index": pi_a,
                    "endpoint_a": pk_a,
                    "path_b_index": pi_b,
                    "endpoint_b": pk_b,
                    "gap_distance_mm": round(dist, 6),
                    "repair_type": repair_type,
                    "is_within_threshold": dist <= max_gap_close_mm,
                }
            )

    return candidates


def _compute_endpoint_partners(
    open_paths: list[dict[str, Any]],
    *,
    max_gap_close_mm: float,
) -> dict[tuple[int, str], list[tuple[int, str, float]]]:
    """For each endpoint, list all other endpoints within the gap threshold.

    Returns ``{(path_index, endpoint_key): [(path_index, endpoint_key, dist), ...]}``.
    Used for ambiguity detection: if an endpoint has more than one partner
    within threshold, the repair is ambiguous.
    """
    endpoints: list[tuple[int, str, float, float]] = []
    for path in open_paths:
        pi = int(path["path_index"])
        sx, sy = float(path["start_point"][0]), float(path["start_point"][1])
        ex, ey = float(path["end_point"][0]), float(path["end_point"][1])
        endpoints.append((pi, "start", sx, sy))
        endpoints.append((pi, "end", ex, ey))

    partners: dict[tuple[int, str], list[tuple[int, str, float]]] = {}
    n = len(endpoints)
    for a in range(n):
        pi_a, pk_a, xa, ya = endpoints[a]
        for b in range(n):
            if a == b:
                continue
            pi_b, pk_b, xb, yb = endpoints[b]
            if pi_a == pi_b and pk_a == pk_b:
                continue
            dist = math.hypot(xa - xb, ya - yb)
            if dist <= max_gap_close_mm:
                ep_a = (pi_a, pk_a)
                partners.setdefault(ep_a, []).append((pi_b, pk_b, dist))
    return partners


def _find_self_closing_candidate(
    candidates: list[dict[str, Any]], *, path_index: int
) -> dict[str, Any] | None:
    """Return the self-closing candidate for the given path, or None."""
    for c in candidates:
        if (
            c["repair_type"] == "self_closing"
            and c["path_a_index"] == path_index
        ):
            return c
    return None


def _find_cross_chain_candidates(
    candidates: list[dict[str, Any]], *, path_index: int
) -> list[dict[str, Any]]:
    """Return all cross-chain candidates that involve the given path index."""
    return [
        c
        for c in candidates
        if c["repair_type"] == "cross_chain"
        and c["is_within_threshold"]
        and (c["path_a_index"] == path_index or c["path_b_index"] == path_index)
    ]


# ---------------------------------------------------------------------------
# Repair application
# ---------------------------------------------------------------------------


def _apply_self_closing_repair(
    path: dict[str, Any],
    *,
    layer: str,
    canonical_role: str,
    gap_distance_mm: float,
) -> dict[str, Any] | None:
    """Bridge the gap between start and end of a single open path.

    The gap bridge adds a direct line segment connecting the chain's last point
    back to its first point, sealing it into a closed ring. This is a
    ``T3_residual_gap_repair`` operation -- distinct from the importer's own
    ``CHAIN_ENDPOINT_EPSILON_MM`` chaining which ran before T3.

    Returns a repair record including the closed ring in ``repaired_path``,
    or ``None`` when the resulting ring would be degenerate (fewer than 3
    distinct points).
    """
    points = path.get("points")
    if not isinstance(points, list) or len(points) < 3:
        return None

    # Construct the closed ring: bridge last → first point.
    ring_points = [[float(p[0]), float(p[1])] for p in points]
    ring_points.append([float(points[0][0]), float(points[0][1])])

    # Reprobe: verify the constructed ring is closed (start == end, >= 4 points).
    reprobe_passed = (
        len(ring_points) >= 4
        and math.hypot(
            ring_points[0][0] - ring_points[-1][0],
            ring_points[0][1] - ring_points[-1][1],
        )
        <= CHAIN_ENDPOINT_EPSILON_MM
    )

    repaired_path: dict[str, Any] = {
        "layer": layer,
        "canonical_role": canonical_role,
        "source": "T3_gap_repair",
        "point_count": len(ring_points),
        "points": ring_points,
    }

    return {
        "layer": layer,
        "canonical_role": canonical_role,
        "path_a_index": int(path["path_index"]),
        "endpoint_a": "end",
        "path_b_index": int(path["path_index"]),
        "endpoint_b": "start",
        "gap_distance_mm": gap_distance_mm,
        "repair_type": "self_closing",
        "bridge_source": "T3_residual_gap_repair",
        "reprobe_passed": reprobe_passed,
        "repaired_path": repaired_path,
    }


# ---------------------------------------------------------------------------
# Conflict routing
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


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


def _build_diagnostics(
    *,
    profile: dict[str, Any],
    applied_gap_repairs: list[dict[str, Any]],
    remaining_open_path_candidates: list[dict[str, Any]],
    source_load_error: dict[str, Any] | None,
) -> dict[str, Any]:
    notes: list[str] = []

    # Distinguish importer chaining truth from T3 new repair layer.
    notes.append(
        f"importer_chaining_truth: the existing importer already chained open path "
        f"segments within CHAIN_ENDPOINT_EPSILON_MM={CHAIN_ENDPOINT_EPSILON_MM}mm "
        f"before T3 ran; T3 operates only on residual gaps larger than that epsilon."
    )
    notes.append(
        f"T3_repair_layer: {len(applied_gap_repairs)} self-closing gap(s) bridged "
        f"by T3 in this run; bridge_source='T3_residual_gap_repair' marks each applied repair."
    )
    notes.append(
        f"remaining_after_T3: {len(remaining_open_path_candidates)} cut-like open path(s) "
        f"remain after T3; these require T4 (duplicate dedupe), T5 (normalized DXF writer), "
        f"or T6 (acceptance gate) attention."
    )
    notes.append(
        "T4_scope: duplicate contour dedupe. "
        "T5_scope: normalized DXF writer. "
        "T6_scope: acceptance gate (accepted_for_import / preflight_rejected)."
    )

    return {
        "rules_profile_source_fields_accepted": sorted(profile["accepted_fields"]),
        "rules_profile_source_fields_ignored": sorted(profile["ignored_fields"]),
        "source_load_error": source_load_error,
        "applied_gap_repair_count": len(applied_gap_repairs),
        "remaining_open_path_count": len(remaining_open_path_candidates),
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# Coercion helpers
# ---------------------------------------------------------------------------


def _coerce_bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise DxfPreflightGapRepairError(
        "DXF_GAP_REPAIR_INVALID_RULES_PROFILE",
        f"expected bool for rules-profile field, got {type(value).__name__}",
    )


def _coerce_positive_float(value: Any, *, default: float) -> float:
    if value is None:
        return default
    if isinstance(value, bool):
        raise DxfPreflightGapRepairError(
            "DXF_GAP_REPAIR_INVALID_RULES_PROFILE",
            "expected positive numeric for rules-profile field, got bool",
        )
    if not isinstance(value, (int, float)):
        raise DxfPreflightGapRepairError(
            "DXF_GAP_REPAIR_INVALID_RULES_PROFILE",
            f"expected positive numeric for rules-profile field, got {type(value).__name__}",
        )
    fval = float(value)
    if not math.isfinite(fval) or fval <= 0:
        raise DxfPreflightGapRepairError(
            "DXF_GAP_REPAIR_INVALID_RULES_PROFILE",
            f"max_gap_close_mm must be a positive finite number, got {fval}",
        )
    return fval
