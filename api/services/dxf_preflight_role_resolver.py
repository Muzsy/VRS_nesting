#!/usr/bin/env python3
"""DXF Prefilter E2-T2 -- Color/layer role resolver (V1).

This module is the role-resolver layer of the DXF prefilter lane. It sits on
top of the E2-T1 inspect result object (``inspect_dxf_source``) plus a
minimal, in-memory rules profile and produces a deterministic canonical role
world:

* ``layer_role_assignments`` -- per-layer canonical role assignment with the
  decision source that produced it,
* ``entity_role_assignments`` -- per-entity projection of the layer role
  plus the raw color hint direction observed on that entity,
* ``resolved_role_inventory`` -- counts grouped by canonical role,
* ``review_required_candidates`` / ``blocking_conflicts`` -- conflict
  signals with named conflict families,
* ``rules_profile_echo`` -- the minimal profile slice actually consumed,
* ``diagnostics`` -- which rules-profile fields were accepted / ignored and
  free-form notes.

Precedence rules (enforced in this order, and tested in
``tests/test_dxf_preflight_role_resolver.py``):

1. explicit canonical source layer (``CUT_OUTER`` / ``CUT_INNER`` /
   ``MARKING``) wins;
2. color hint via ``cut_color_map`` / ``marking_color_map`` can provide a
   ``cut-like`` or ``marking-like`` direction when the layer is non-canonical;
3. the E2-T1 topology proxy (``outer_like_candidates`` /
   ``inner_like_candidates``) disambiguates outer vs inner when and only
   when the color hint already chose cut-like.

Conflicts that cannot be resolved deterministically are reported as named
families, not silenced. Cut-like open paths never count as silent success.

Scope boundary (intentional):

* does NOT re-open the DXF importer or read source files -- it operates on
  the E2-T1 inspect result object exclusively,
* does NOT mutate geometry, repair gaps, dedupe duplicate contours or write
  a normalised DXF (E2-T3 / T4 / T5),
* does NOT produce an acceptance outcome (``accepted_for_import`` /
  ``preflight_rejected``) -- that is E2-T6 scope,
* does NOT touch DB persistence, API routes or frontend UI,
* does NOT treat ``linetype_name`` as a first-class role decision signal --
  it stays in the raw evidence layer only.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

__all__ = [
    "CANONICAL_LAYER_ROLES",
    "DxfPreflightRoleResolverError",
    "resolve_dxf_roles",
]


CANONICAL_LAYER_ROLES: frozenset[str] = frozenset({"CUT_OUTER", "CUT_INNER", "MARKING"})
_CUT_LIKE_ROLES: frozenset[str] = frozenset({"CUT_OUTER", "CUT_INNER"})
_UNASSIGNED_ROLE: str = "UNASSIGNED"

_ALLOWED_RULES_PROFILE_FIELDS: frozenset[str] = frozenset(
    {
        "strict_mode",
        "interactive_review_on_ambiguity",
        "cut_color_map",
        "marking_color_map",
    }
)

# Conflict families where the explicit canonical source layer wins and the
# report is informational only (never blocks on its own, even in strict_mode).
_DIAGNOSTIC_ONLY_FAMILIES: frozenset[str] = frozenset(
    {
        "explicit_layer_vs_color_hint_conflict",
        "mixed_cut_and_marking_on_canonical_layer",
        "topology_proxy_not_compatible_with_explicit_layer",
    }
)


class DxfPreflightRoleResolverError(RuntimeError):
    """Raised for structural misuse of the resolver boundary.

    The resolver itself never signals DXF-level problems this way -- DXF
    observations land in the ``review_required_candidates`` /
    ``blocking_conflicts`` layers so the caller can still read the full
    resolution. This exception is reserved for "caller handed us nonsense"
    situations (e.g. ``inspect_result`` missing or not a mapping).
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def resolve_dxf_roles(
    inspect_result: Mapping[str, Any],
    rules_profile: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve canonical DXF prefilter roles from an inspect result.

    Parameters
    ----------
    inspect_result:
        The shape returned by
        ``api.services.dxf_preflight_inspect.inspect_dxf_source``.
    rules_profile:
        Optional mapping. Only the minimal T2 slice (``strict_mode``,
        ``interactive_review_on_ambiguity``, ``cut_color_map``,
        ``marking_color_map``) is consumed; other keys are ignored but
        reported in ``diagnostics.rules_profile_source_fields_ignored``.

    Returns
    -------
    dict[str, Any]
        Deterministic, JSON-serialisable resolution with the shape described
        at the top of the module.
    """

    if not isinstance(inspect_result, Mapping):
        raise DxfPreflightRoleResolverError(
            "DXF_ROLE_RESOLVER_INVALID_INSPECT_RESULT",
            "inspect_result must be a mapping as produced by inspect_dxf_source().",
        )

    profile = _normalize_rules_profile(rules_profile if rules_profile is not None else {})

    entity_inventory = _as_dict_list(inspect_result.get("entity_inventory"))
    layer_inventory = _as_dict_list(inspect_result.get("layer_inventory"))
    open_path_candidates = _as_dict_list(inspect_result.get("open_path_candidates"))
    outer_like = _as_dict_list(inspect_result.get("outer_like_candidates"))
    inner_like = _as_dict_list(inspect_result.get("inner_like_candidates"))
    contour_candidates = _as_dict_list(inspect_result.get("contour_candidates"))

    open_path_counts: dict[str, int] = {
        str(item.get("layer", "")): _as_int(item.get("open_path_count"), default=0)
        for item in open_path_candidates
    }
    outer_like_layers: set[str] = {str(item.get("layer", "")) for item in outer_like}
    inner_like_layers: set[str] = {str(item.get("layer", "")) for item in inner_like}
    contour_layers: set[str] = {str(item.get("layer", "")) for item in contour_candidates}

    entities_by_layer: dict[str, list[dict[str, Any]]] = {}
    for entity in entity_inventory:
        layer = str(entity.get("layer", ""))
        entities_by_layer.setdefault(layer, []).append(dict(entity))
    for layer_record in layer_inventory:
        entities_by_layer.setdefault(str(layer_record.get("layer", "")), [])

    layer_role_assignments: list[dict[str, Any]] = []
    entity_role_assignments: list[dict[str, Any]] = []
    review_required_candidates: list[dict[str, Any]] = []
    blocking_conflicts: list[dict[str, Any]] = []

    for layer in sorted(entities_by_layer):
        entities = entities_by_layer[layer]
        signals = _collect_layer_signals(
            layer=layer,
            entities=entities,
            cut_colors=profile["cut_color_map"],
            marking_colors=profile["marking_color_map"],
            outer_like_layers=outer_like_layers,
            inner_like_layers=inner_like_layers,
            open_path_counts=open_path_counts,
            contour_layers=contour_layers,
        )
        resolution = _resolve_layer(
            signals=signals,
            strict_mode=profile["strict_mode"],
            interactive_review=profile["interactive_review_on_ambiguity"],
        )
        layer_role_assignments.append(resolution["layer_record"])
        entity_role_assignments.extend(
            _project_entity_assignments(
                entities=entities,
                layer_record=resolution["layer_record"],
                entity_color_direction=signals["entity_color_direction"],
            )
        )
        review_required_candidates.extend(resolution["review_required"])
        blocking_conflicts.extend(resolution["blocking"])

    contour_role_assignments, contour_resolved_layers = _resolve_contour_roles(
        contour_candidates=contour_candidates,
        outer_like=outer_like,
        inner_like=inner_like,
        layer_role_assignments=layer_role_assignments,
        profile=profile,
        review_required_candidates=review_required_candidates,
        blocking_conflicts=blocking_conflicts,
    )

    # Suppress no_signal_layer_with_contour conflicts for layers fully resolved
    # at contour level; update those layer records' decision_source.
    _apply_contour_resolution_to_layer_records(
        layer_role_assignments=layer_role_assignments,
        review_required_candidates=review_required_candidates,
        blocking_conflicts=blocking_conflicts,
        contour_resolved_layers=contour_resolved_layers,
    )

    resolved_role_inventory = _build_resolved_role_inventory(
        layer_role_assignments=layer_role_assignments,
        entity_role_assignments=entity_role_assignments,
    )

    diagnostics: dict[str, Any] = {
        "rules_profile_source_fields_accepted": sorted(profile["accepted_fields"]),
        "rules_profile_source_fields_ignored": sorted(profile["ignored_fields"]),
        "rules_profile_color_map_overlap": sorted(profile["color_map_overlap"]),
        "notes": [],
    }

    return {
        "rules_profile_echo": profile["echo"],
        "layer_role_assignments": layer_role_assignments,
        "entity_role_assignments": entity_role_assignments,
        "contour_role_assignments": contour_role_assignments,
        "resolved_role_inventory": resolved_role_inventory,
        "review_required_candidates": review_required_candidates,
        "blocking_conflicts": blocking_conflicts,
        "diagnostics": diagnostics,
    }


# ---------------------------------------------------------------------------
# Rules profile normalisation
# ---------------------------------------------------------------------------


def _normalize_rules_profile(rules_profile: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(rules_profile, Mapping):
        raise DxfPreflightRoleResolverError(
            "DXF_ROLE_RESOLVER_INVALID_RULES_PROFILE",
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

    strict_mode = _coerce_bool(accepted.get("strict_mode"), default=False)
    interactive_review = _coerce_bool(
        accepted.get("interactive_review_on_ambiguity"), default=True
    )
    cut_colors = _coerce_color_set(accepted.get("cut_color_map"))
    marking_colors = _coerce_color_set(accepted.get("marking_color_map"))

    overlap = frozenset(cut_colors & marking_colors)

    echo: dict[str, Any] = {
        "strict_mode": strict_mode,
        "interactive_review_on_ambiguity": interactive_review,
        "cut_color_map": sorted(cut_colors),
        "marking_color_map": sorted(marking_colors),
    }

    return {
        "echo": echo,
        "strict_mode": strict_mode,
        "interactive_review_on_ambiguity": interactive_review,
        "cut_color_map": frozenset(cut_colors),
        "marking_color_map": frozenset(marking_colors),
        "color_map_overlap": overlap,
        "accepted_fields": set(accepted.keys()),
        "ignored_fields": ignored,
    }


# ---------------------------------------------------------------------------
# Layer-level signal collection and resolution
# ---------------------------------------------------------------------------


def _collect_layer_signals(
    *,
    layer: str,
    entities: list[dict[str, Any]],
    cut_colors: frozenset[int],
    marking_colors: frozenset[int],
    outer_like_layers: set[str],
    inner_like_layers: set[str],
    open_path_counts: dict[str, int],
    contour_layers: set[str],
) -> dict[str, Any]:
    canonical_layer_role = layer if layer in CANONICAL_LAYER_ROLES else None

    entity_color_direction: dict[int, str] = {}
    has_cut_hint = False
    has_marking_hint = False
    for entity in entities:
        color = entity.get("color_index")
        if not isinstance(color, int) or isinstance(color, bool):
            continue
        hits_cut = color in cut_colors
        hits_marking = color in marking_colors
        entity_index = _as_int(entity.get("entity_index"), default=-1)
        if entity_index < 0:
            continue
        if hits_cut and hits_marking:
            entity_color_direction[entity_index] = "both"
            has_cut_hint = True
            has_marking_hint = True
        elif hits_cut:
            entity_color_direction[entity_index] = "cut"
            has_cut_hint = True
        elif hits_marking:
            entity_color_direction[entity_index] = "marking"
            has_marking_hint = True

    return {
        "layer": layer,
        "canonical_layer_role": canonical_layer_role,
        "has_cut_hint": has_cut_hint,
        "has_marking_hint": has_marking_hint,
        "entity_color_direction": entity_color_direction,
        "is_outer_like": layer in outer_like_layers,
        "is_inner_like": layer in inner_like_layers,
        "open_path_count": int(open_path_counts.get(layer, 0)),
        "has_contour": layer in contour_layers,
    }


def _resolve_layer(
    *,
    signals: dict[str, Any],
    strict_mode: bool,
    interactive_review: bool,
) -> dict[str, Any]:
    review_required: list[dict[str, Any]] = []
    blocking: list[dict[str, Any]] = []

    layer = str(signals["layer"])
    canonical_layer_role = signals["canonical_layer_role"]
    has_cut_hint = bool(signals["has_cut_hint"])
    has_marking_hint = bool(signals["has_marking_hint"])
    is_outer_like = bool(signals["is_outer_like"])
    is_inner_like = bool(signals["is_inner_like"])
    open_path_count = int(signals["open_path_count"])
    has_contour = bool(signals["has_contour"])

    canonical_role: str
    decision_source: str

    if canonical_layer_role is not None:
        canonical_role = str(canonical_layer_role)
        decision_source = "explicit_canonical_layer"

        if canonical_role in _CUT_LIKE_ROLES and has_marking_hint and not has_cut_hint:
            _emit_conflict(
                review_required,
                blocking,
                family="explicit_layer_vs_color_hint_conflict",
                strict_mode=strict_mode,
                interactive_review=interactive_review,
                payload={
                    "layer": layer,
                    "canonical_layer_role": canonical_role,
                    "observed_color_direction": "marking",
                    "resolution": "canonical_layer_wins",
                },
            )
        if canonical_role == "MARKING" and has_cut_hint and not has_marking_hint:
            _emit_conflict(
                review_required,
                blocking,
                family="explicit_layer_vs_color_hint_conflict",
                strict_mode=strict_mode,
                interactive_review=interactive_review,
                payload={
                    "layer": layer,
                    "canonical_layer_role": canonical_role,
                    "observed_color_direction": "cut",
                    "resolution": "canonical_layer_wins",
                },
            )
        if has_cut_hint and has_marking_hint:
            _emit_conflict(
                review_required,
                blocking,
                family="mixed_cut_and_marking_on_canonical_layer",
                strict_mode=strict_mode,
                interactive_review=interactive_review,
                payload={
                    "layer": layer,
                    "canonical_layer_role": canonical_role,
                    "resolution": "canonical_layer_wins",
                },
            )
        if canonical_role == "CUT_OUTER" and is_inner_like and not is_outer_like:
            _emit_conflict(
                review_required,
                blocking,
                family="topology_proxy_not_compatible_with_explicit_layer",
                strict_mode=strict_mode,
                interactive_review=interactive_review,
                payload={
                    "layer": layer,
                    "canonical_layer_role": canonical_role,
                    "topology_observation": "inner_like_only",
                    "resolution": "canonical_layer_wins",
                },
            )
        if canonical_role == "CUT_INNER" and is_outer_like and not is_inner_like:
            _emit_conflict(
                review_required,
                blocking,
                family="topology_proxy_not_compatible_with_explicit_layer",
                strict_mode=strict_mode,
                interactive_review=interactive_review,
                payload={
                    "layer": layer,
                    "canonical_layer_role": canonical_role,
                    "topology_observation": "outer_like_only",
                    "resolution": "canonical_layer_wins",
                },
            )
        if canonical_role in _CUT_LIKE_ROLES and open_path_count > 0:
            _emit_conflict(
                review_required,
                blocking,
                family="cut_like_open_path_on_canonical_layer",
                strict_mode=strict_mode,
                interactive_review=interactive_review,
                payload={
                    "layer": layer,
                    "canonical_layer_role": canonical_role,
                    "open_path_count": open_path_count,
                },
            )
    elif has_cut_hint and has_marking_hint:
        canonical_role = _UNASSIGNED_ROLE
        decision_source = "unresolved_mixed_color_hints"
        _emit_conflict(
            review_required,
            blocking,
            family="mixed_cut_and_marking_on_non_canonical_layer",
            strict_mode=strict_mode,
            interactive_review=interactive_review,
            payload={"layer": layer},
        )
    elif has_marking_hint and not has_cut_hint:
        canonical_role = "MARKING"
        decision_source = "color_hint"
    elif has_cut_hint and not has_marking_hint:
        if is_outer_like and not is_inner_like:
            canonical_role = "CUT_OUTER"
            decision_source = "color_hint_plus_topology_proxy"
        elif is_inner_like and not is_outer_like:
            canonical_role = "CUT_INNER"
            decision_source = "color_hint_plus_topology_proxy"
        else:
            canonical_role = _UNASSIGNED_ROLE
            decision_source = "unresolved_cut_like_topology_ambiguous"
            _emit_conflict(
                review_required,
                blocking,
                family="cut_like_topology_ambiguous",
                strict_mode=strict_mode,
                interactive_review=interactive_review,
                payload={
                    "layer": layer,
                    "is_outer_like": is_outer_like,
                    "is_inner_like": is_inner_like,
                },
            )
        if canonical_role in _CUT_LIKE_ROLES and open_path_count > 0:
            _emit_conflict(
                review_required,
                blocking,
                family="cut_like_open_path_on_color_hint_layer",
                strict_mode=strict_mode,
                interactive_review=interactive_review,
                payload={
                    "layer": layer,
                    "canonical_layer_role": canonical_role,
                    "open_path_count": open_path_count,
                },
            )
    else:
        canonical_role = _UNASSIGNED_ROLE
        decision_source = "unresolved_no_signal"
        if has_contour:
            _emit_conflict(
                review_required,
                blocking,
                family="no_signal_layer_with_contour",
                strict_mode=strict_mode,
                interactive_review=interactive_review,
                payload={"layer": layer},
            )

    layer_record: dict[str, Any] = {
        "layer": layer,
        "canonical_role": canonical_role,
        "decision_source": decision_source,
        "signals": {
            "canonical_layer_role": canonical_layer_role,
            "has_cut_hint": has_cut_hint,
            "has_marking_hint": has_marking_hint,
            "is_outer_like": is_outer_like,
            "is_inner_like": is_inner_like,
            "open_path_count": open_path_count,
            "has_contour": has_contour,
        },
    }

    return {
        "layer_record": layer_record,
        "review_required": review_required,
        "blocking": blocking,
    }


def _emit_conflict(
    review_required: list[dict[str, Any]],
    blocking: list[dict[str, Any]],
    *,
    family: str,
    strict_mode: bool,
    interactive_review: bool,
    payload: dict[str, Any],
) -> None:
    severity = _classify_conflict(
        family=family,
        strict_mode=strict_mode,
        interactive_review=interactive_review,
    )
    record: dict[str, Any] = {"family": family, "severity": severity}
    record.update(payload)
    if severity == "blocking":
        blocking.append(record)
    else:
        review_required.append(record)


def _classify_conflict(
    *, family: str, strict_mode: bool, interactive_review: bool
) -> str:
    if family in _DIAGNOSTIC_ONLY_FAMILIES:
        return "review_required"
    if strict_mode:
        return "blocking"
    if not interactive_review:
        return "blocking"
    return "review_required"


def _project_entity_assignments(
    *,
    entities: list[dict[str, Any]],
    layer_record: dict[str, Any],
    entity_color_direction: dict[int, str],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for entity in entities:
        entity_index = _as_int(entity.get("entity_index"), default=-1)
        if entity_index < 0:
            continue
        out.append(
            {
                "entity_index": entity_index,
                "layer": str(entity.get("layer", "")),
                "canonical_role": layer_record["canonical_role"],
                "decision_source": layer_record["decision_source"],
                "color_direction": entity_color_direction.get(entity_index),
            }
        )
    out.sort(key=lambda item: int(item["entity_index"]))
    return out


def _resolve_contour_roles(
    *,
    contour_candidates: list[dict[str, Any]],
    outer_like: list[dict[str, Any]],
    inner_like: list[dict[str, Any]],
    layer_role_assignments: list[dict[str, Any]],
    profile: dict[str, Any],
    review_required_candidates: list[dict[str, Any]],
    blocking_conflicts: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], set[str]]:
    """Classify each closed contour as CUT_OUTER, CUT_INNER, or skip.

    Returns (contour_role_assignments, contour_resolved_layers) where
    contour_resolved_layers is the set of layers where ALL contours got a
    contour-level cut role (so the layer-level no_signal conflict can be suppressed).
    """
    layer_canonical: dict[str, str] = {
        str(rec["layer"]): str(rec["canonical_role"])
        for rec in layer_role_assignments
    }

    # Build containment index from outer_like/inner_like candidates.
    # Key: (layer, ring_index) → list of rings it contains
    contains_map: dict[tuple[str, int], list[tuple[str, int]]] = {}
    for item in outer_like:
        key = (str(item["layer"]), int(item["ring_index"]))
        refs = [
            (str(r["layer"]), int(r["ring_index"]))
            for r in _as_dict_list(item.get("contains_ring_references"))
        ]
        contains_map[key] = refs

    contained_by_map: dict[tuple[str, int], list[tuple[str, int]]] = {}
    for item in inner_like:
        key = (str(item["layer"]), int(item["ring_index"]))
        refs = [
            (str(r["layer"]), int(r["ring_index"]))
            for r in _as_dict_list(item.get("contained_by_ring_references"))
        ]
        contained_by_map[key] = refs

    # Separate contour candidates into canonical and non-canonical groups.
    canonical_contours: list[dict[str, Any]] = []
    candidate_contours: list[dict[str, Any]] = []  # non-canonical, potential cut

    layer_decision_source: dict[str, str] = {
        str(rec["layer"]): str(rec.get("decision_source", ""))
        for rec in layer_role_assignments
    }

    for c in contour_candidates:
        layer = str(c.get("layer", ""))
        role = layer_canonical.get(layer, _UNASSIGNED_ROLE)
        if role in CANONICAL_LAYER_ROLES:
            # Explicit canonical layer OR layer already resolved by color/topology signals.
            canonical_contours.append(c)
        elif layer_decision_source.get(layer) == "unresolved_no_signal":
            # No color hint, no explicit layer name → contour-level topology can decide.
            candidate_contours.append(c)
        # All other unresolved cases (mixed hints, cut-like but ambiguous topology, etc.)
        # are left to the layer-level resolver; do not auto-classify at contour level.

    assignments: list[dict[str, Any]] = []

    # 1. Canonical layer contours keep their explicit role.
    for c in canonical_contours:
        layer = str(c.get("layer", ""))
        role = layer_canonical[layer]
        if role in _CUT_LIKE_ROLES:
            assignments.append({
                "contour_id": str(c.get("contour_id", f"orig:{layer}:{c.get('ring_index', 0)}")),
                "layer": layer,
                "ring_index": int(c.get("ring_index", 0)),
                "canonical_role": role,
                "decision_source": "explicit_canonical_layer",
                "bbox": c.get("bbox"),
                "area_abs_mm2": float(c.get("area_abs_mm2", 0.0)),
            })

    # 2. Non-canonical cut candidates: classify by topology.
    contour_resolved_layers: set[str] = set()
    if candidate_contours:
        # Group all candidate contours together (cross-layer topology is possible)
        _classify_cut_candidates(
            candidates=candidate_contours,
            contains_map=contains_map,
            contained_by_map=contained_by_map,
            profile=profile,
            assignments=assignments,
            review_required_candidates=review_required_candidates,
            blocking_conflicts=blocking_conflicts,
        )

        # Determine which non-canonical layers had ALL contours successfully resolved.
        candidate_layers: set[str] = {str(c["layer"]) for c in candidate_contours}
        assigned_ids: set[str] = {
            str(a["contour_id"]) for a in assignments
            if str(a.get("decision_source", "")) != "explicit_canonical_layer"
        }
        for layer in candidate_layers:
            layer_candidate_ids = {
                str(c.get("contour_id", "")) for c in candidate_contours
                if str(c["layer"]) == layer
            }
            if layer_candidate_ids and layer_candidate_ids.issubset(assigned_ids):
                contour_resolved_layers.add(layer)

    return assignments, contour_resolved_layers


def _classify_cut_candidates(
    *,
    candidates: list[dict[str, Any]],
    contains_map: dict[tuple[str, int], list[tuple[str, int]]],
    contained_by_map: dict[tuple[str, int], list[tuple[str, int]]],
    profile: dict[str, Any],
    assignments: list[dict[str, Any]],
    review_required_candidates: list[dict[str, Any]],
    blocking_conflicts: list[dict[str, Any]],
) -> None:
    """Classify candidate contours as CUT_OUTER or CUT_INNER using bbox containment."""
    candidate_keys: set[tuple[str, int]] = {
        (str(c["layer"]), int(c["ring_index"])) for c in candidates
    }
    by_key: dict[tuple[str, int], dict[str, Any]] = {
        (str(c["layer"]), int(c["ring_index"])): c for c in candidates
    }

    if len(candidates) == 1:
        c = candidates[0]
        layer = str(c["layer"])
        ring_index = int(c["ring_index"])
        assignments.append({
            "contour_id": str(c.get("contour_id", f"orig:{layer}:{ring_index}")),
            "layer": layer,
            "ring_index": ring_index,
            "canonical_role": "CUT_OUTER",
            "decision_source": "single_closed_contour_auto_outer",
            "bbox": c.get("bbox"),
            "area_abs_mm2": float(c.get("area_abs_mm2", 0.0)),
        })
        return

    # Multiple candidates: find top-level (not contained by any other candidate).
    top_level: list[dict[str, Any]] = []
    contained: list[dict[str, Any]] = []
    for c in candidates:
        key = (str(c["layer"]), int(c["ring_index"]))
        # Check if this contour is contained by any other candidate contour
        outer_refs = contained_by_map.get(key, [])
        contained_by_candidate = any(ref in candidate_keys for ref in outer_refs)
        if contained_by_candidate:
            contained.append(c)
        else:
            top_level.append(c)

    if len(top_level) > 1:
        # Multiple separate outer contours — cannot auto-classify as one part.
        _emit_conflict(
            review_required_candidates,
            blocking_conflicts,
            family="no_signal_multiple_outer_candidates",
            strict_mode=profile["strict_mode"],
            interactive_review=profile["interactive_review_on_ambiguity"],
            payload={
                "candidate_count": len(top_level),
                "layers": sorted({str(c["layer"]) for c in top_level}),
            },
        )
        return

    if len(top_level) == 1:
        outer_c = top_level[0]
        outer_key = (str(outer_c["layer"]), int(outer_c["ring_index"]))
        assignments.append({
            "contour_id": str(outer_c.get("contour_id", f"orig:{outer_c['layer']}:{outer_c['ring_index']}")),
            "layer": str(outer_c["layer"]),
            "ring_index": int(outer_c["ring_index"]),
            "canonical_role": "CUT_OUTER",
            "decision_source": "contour_topology_auto",
            "bbox": outer_c.get("bbox"),
            "area_abs_mm2": float(outer_c.get("area_abs_mm2", 0.0)),
        })

    for c in contained:
        key = (str(c["layer"]), int(c["ring_index"]))
        # Check for deeply nested (island) contours: contained by a contour that is itself contained
        outer_refs = contained_by_map.get(key, [])
        direct_outer_in_candidates = [ref for ref in outer_refs if ref in candidate_keys]
        # If any of the direct outers is itself in `contained`, this is an island — not supported.
        is_nested = any(
            any(ref2 in candidate_keys for ref2 in contained_by_map.get(ref, []))
            for ref in direct_outer_in_candidates
        )
        if is_nested:
            _emit_conflict(
                review_required_candidates,
                blocking_conflicts,
                family="contour_nested_island_unsupported",
                strict_mode=profile["strict_mode"],
                interactive_review=profile["interactive_review_on_ambiguity"],
                payload={
                    "layer": str(c["layer"]),
                    "ring_index": int(c["ring_index"]),
                    "contour_id": str(c.get("contour_id", "")),
                },
            )
            continue
        assignments.append({
            "contour_id": str(c.get("contour_id", f"orig:{c['layer']}:{c['ring_index']}")),
            "layer": str(c["layer"]),
            "ring_index": int(c["ring_index"]),
            "canonical_role": "CUT_INNER",
            "decision_source": "contour_topology_auto",
            "bbox": c.get("bbox"),
            "area_abs_mm2": float(c.get("area_abs_mm2", 0.0)),
        })


def _apply_contour_resolution_to_layer_records(
    *,
    layer_role_assignments: list[dict[str, Any]],
    review_required_candidates: list[dict[str, Any]],
    blocking_conflicts: list[dict[str, Any]],
    contour_resolved_layers: set[str],
) -> None:
    """Update layer records and remove no_signal conflicts for fully resolved layers."""
    if not contour_resolved_layers:
        return

    for rec in layer_role_assignments:
        if str(rec.get("layer", "")) in contour_resolved_layers:
            rec["decision_source"] = "resolved_by_contour_roles"

    # Remove no_signal_layer_with_contour conflicts for fully resolved layers.
    def keep(item: dict[str, Any], resolved: set[str]) -> bool:
        if str(item.get("family", "")) != "no_signal_layer_with_contour":
            return True
        return str(item.get("layer", "")) not in resolved

    review_required_candidates[:] = [
        item for item in review_required_candidates if keep(item, contour_resolved_layers)
    ]
    blocking_conflicts[:] = [
        item for item in blocking_conflicts if keep(item, contour_resolved_layers)
    ]


def _build_resolved_role_inventory(
    *,
    layer_role_assignments: list[dict[str, Any]],
    entity_role_assignments: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {
        role: {"layer_count": 0, "entity_count": 0, "layers": []}
        for role in ("CUT_OUTER", "CUT_INNER", "MARKING", _UNASSIGNED_ROLE)
    }
    for record in layer_role_assignments:
        role = str(record["canonical_role"])
        bucket = buckets.setdefault(
            role, {"layer_count": 0, "entity_count": 0, "layers": []}
        )
        bucket["layer_count"] = int(bucket["layer_count"]) + 1
        bucket["layers"].append(str(record["layer"]))
    for entry in entity_role_assignments:
        role = str(entry["canonical_role"])
        bucket = buckets.setdefault(
            role, {"layer_count": 0, "entity_count": 0, "layers": []}
        )
        bucket["entity_count"] = int(bucket["entity_count"]) + 1
    for role in buckets:
        buckets[role]["layers"] = sorted(buckets[role]["layers"])
    return buckets


# ---------------------------------------------------------------------------
# Coercion helpers
# ---------------------------------------------------------------------------


def _coerce_bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise DxfPreflightRoleResolverError(
        "DXF_ROLE_RESOLVER_INVALID_RULES_PROFILE",
        f"expected bool for rules-profile field, got {type(value).__name__}",
    )


def _coerce_color_set(value: Any) -> set[int]:
    if value is None:
        return set()
    candidates: Iterable[Any]
    if isinstance(value, Mapping):
        candidates = value.keys()
    elif isinstance(value, (list, tuple, set, frozenset)):
        candidates = value
    else:
        raise DxfPreflightRoleResolverError(
            "DXF_ROLE_RESOLVER_INVALID_RULES_PROFILE",
            f"expected iterable of ACI color indices, got {type(value).__name__}",
        )
    out: set[int] = set()
    for item in candidates:
        if isinstance(item, bool) or not isinstance(item, int):
            raise DxfPreflightRoleResolverError(
                "DXF_ROLE_RESOLVER_INVALID_RULES_PROFILE",
                f"color index must be int, got {type(item).__name__}",
            )
        out.add(int(item))
    return out


def _as_dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    out: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, Mapping):
            out.append(dict(item))
    return out


def _as_int(value: Any, *, default: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return int(value)
