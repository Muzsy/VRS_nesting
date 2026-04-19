#!/usr/bin/env python3
"""DXF Prefilter E2-T2 -- color/layer role resolver smoke.

Deterministic, backend-independent smoke for the role-resolver stage. It
feeds in-memory inspect-result fixtures (no DXF / JSON file I/O) into the
resolver and checks that:

* the output carries only the documented top-level layers (no acceptance,
  repair or normalized-DXF world leaks in);
* the explicit canonical layer precedence (``CUT_OUTER`` / ``CUT_INNER`` /
  ``MARKING``) wins over color hint and topology proxy;
* a non-canonical layer with a color hint and a topology proxy resolves to
  the expected cut-like role (outer vs inner);
* a ``MARKING`` layer with an open path is silent success, but a
  cut-like layer with an open path lands in review_required (lenient) or
  blocking (strict_mode);
* ``interactive_review_on_ambiguity=False`` promotes ambiguity to
  blocking_conflicts even in lenient strict_mode;
* the resolver reflects only the minimal T2 rules-profile slice in
  ``rules_profile_echo`` and records ignored fields under diagnostics.

The smoke intentionally does NOT import the DXF parser or the inspect
engine. T1 coverage is handled by its own smoke and tests. This file
exists solely to prove the T2 role-resolver contract deterministically.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.dxf_preflight_role_resolver import resolve_dxf_roles


EXPECTED_TOP_LEVEL_KEYS: tuple[str, ...] = (
    "rules_profile_echo",
    "layer_role_assignments",
    "entity_role_assignments",
    "resolved_role_inventory",
    "review_required_candidates",
    "blocking_conflicts",
    "diagnostics",
)

FORBIDDEN_TOP_LEVEL_KEYS: tuple[str, ...] = (
    # Acceptance world (E2-T6) must not leak into T2.
    "accepted_for_import",
    "acceptance",
    "acceptance_outcome",
    "preflight_rejected",
    # Repair / writer world (E2-T3 / T4 / T5) must not leak into T2.
    "repair",
    "repairs",
    "gap_fixes",
    "normalized_dxf",
    "normalized_source",
)


def _assert(cond: bool, message: str) -> None:
    if not cond:
        raise AssertionError(message)


def _layer_record(result: dict, layer: str) -> dict:
    for record in result["layer_role_assignments"]:
        if record["layer"] == layer:
            return record
    raise AssertionError(f"layer '{layer}' missing from layer_role_assignments")


def _entity(
    *,
    entity_index: int,
    layer: str,
    color_index: int | None = None,
    closed: bool = True,
    type_: str = "LWPOLYLINE",
    point_count: int = 4,
) -> dict[str, Any]:
    return {
        "entity_index": entity_index,
        "layer": layer,
        "type": type_,
        "closed": closed,
        "color_index": color_index,
        "linetype_name": "CONTINUOUS",
        "point_count": point_count,
        "unsupported": False,
    }


def _layer_inv(layer: str, count: int = 1) -> dict[str, Any]:
    return {
        "layer": layer,
        "entity_count": count,
        "supported_count": count,
        "unsupported_count": 0,
        "types": ["LWPOLYLINE"],
    }


def _build_inspect_result(
    *,
    entities: list[dict[str, Any]],
    contour_layers: list[str] | None = None,
    open_path_layers: dict[str, int] | None = None,
    outer_like_layers: list[str] | None = None,
    inner_like_layers: list[str] | None = None,
) -> dict[str, Any]:
    layer_set = sorted({entity["layer"] for entity in entities})
    contour_layers = contour_layers if contour_layers is not None else layer_set
    open_path_layers = open_path_layers or {}
    outer_like_layers = outer_like_layers or []
    inner_like_layers = inner_like_layers or []

    return {
        "source_path": "in-memory-fixture",
        "backend": "in-memory",
        "source_size_bytes": None,
        "entity_inventory": entities,
        "layer_inventory": [_layer_inv(layer) for layer in layer_set],
        "color_inventory": [],
        "linetype_inventory": [],
        "contour_candidates": [
            {"layer": layer, "ring_index": 0, "point_count": 4, "bbox": {}, "fingerprint": f"fp-{layer}"}
            for layer in contour_layers
        ],
        "open_path_candidates": [
            {"layer": layer, "open_path_count": int(count)}
            for layer, count in sorted(open_path_layers.items())
        ],
        "duplicate_contour_candidates": [],
        "outer_like_candidates": [
            {"layer": layer, "ring_index": 0, "contains_ring_references": []}
            for layer in outer_like_layers
        ],
        "inner_like_candidates": [
            {"layer": layer, "ring_index": 0, "contained_by_ring_references": []}
            for layer in inner_like_layers
        ],
        "diagnostics": {"probe_errors": [], "notes": []},
    }


def _check_shape(result: dict) -> None:
    for key in EXPECTED_TOP_LEVEL_KEYS:
        _assert(key in result, f"missing top-level key: {key}")
    for forbidden in FORBIDDEN_TOP_LEVEL_KEYS:
        _assert(
            forbidden not in result,
            f"role-resolver T2 must not expose '{forbidden}'",
        )
    inventory = result["resolved_role_inventory"]
    _assert(
        set(inventory.keys()) >= {"CUT_OUTER", "CUT_INNER", "MARKING", "UNASSIGNED"},
        f"resolved_role_inventory missing canonical bucket: {sorted(inventory.keys())}",
    )


def _scenario_canonical_green_path() -> None:
    inspect_result = _build_inspect_result(
        entities=[
            _entity(entity_index=0, layer="CUT_OUTER", color_index=7),
            _entity(entity_index=1, layer="CUT_INNER", color_index=1),
            _entity(entity_index=2, layer="MARKING", color_index=2, closed=False, type_="LINE", point_count=2),
        ],
        open_path_layers={"MARKING": 1},
        outer_like_layers=["CUT_OUTER"],
        inner_like_layers=["CUT_INNER"],
    )

    result = resolve_dxf_roles(inspect_result)
    _check_shape(result)

    _assert(
        _layer_record(result, "CUT_OUTER")["canonical_role"] == "CUT_OUTER",
        "CUT_OUTER explicit canonical layer must win",
    )
    _assert(
        _layer_record(result, "CUT_INNER")["canonical_role"] == "CUT_INNER",
        "CUT_INNER explicit canonical layer must win",
    )
    _assert(
        _layer_record(result, "MARKING")["canonical_role"] == "MARKING",
        "MARKING explicit canonical layer must win",
    )
    _assert(
        all(
            record["decision_source"] == "explicit_canonical_layer"
            for record in result["layer_role_assignments"]
        ),
        "all canonical-layer decisions must cite explicit_canonical_layer",
    )
    _assert(result["review_required_candidates"] == [], "green path must have no review-required")
    _assert(result["blocking_conflicts"] == [], "green path must have no blocking conflicts")


def _scenario_color_hint_plus_topology_outer() -> None:
    inspect_result = _build_inspect_result(
        entities=[
            _entity(entity_index=0, layer="LASER_OUTER_4", color_index=4),
            _entity(entity_index=1, layer="LASER_INNER_5", color_index=5),
        ],
        outer_like_layers=["LASER_OUTER_4"],
        inner_like_layers=["LASER_INNER_5"],
    )

    result = resolve_dxf_roles(
        inspect_result,
        rules_profile={"cut_color_map": [4, 5], "marking_color_map": []},
    )

    _assert(
        _layer_record(result, "LASER_OUTER_4")["canonical_role"] == "CUT_OUTER",
        "cut-like layer with outer topology must resolve to CUT_OUTER",
    )
    _assert(
        _layer_record(result, "LASER_INNER_5")["canonical_role"] == "CUT_INNER",
        "cut-like layer with inner topology must resolve to CUT_INNER",
    )
    _assert(
        _layer_record(result, "LASER_OUTER_4")["decision_source"]
        == "color_hint_plus_topology_proxy",
        "decision_source must be color_hint_plus_topology_proxy for color+topology path",
    )
    _assert(result["blocking_conflicts"] == [], "unambiguous color+topology path must not block")


def _scenario_cut_like_open_path_review_vs_blocking() -> None:
    inspect_result = _build_inspect_result(
        entities=[_entity(entity_index=0, layer="CUT_OUTER", color_index=7, closed=False)],
        contour_layers=[],
        open_path_layers={"CUT_OUTER": 1},
        outer_like_layers=["CUT_OUTER"],
    )

    lenient = resolve_dxf_roles(inspect_result)
    strict = resolve_dxf_roles(inspect_result, rules_profile={"strict_mode": True})

    lenient_families = [item["family"] for item in lenient["review_required_candidates"]]
    _assert(
        "cut_like_open_path_on_canonical_layer" in lenient_families,
        "cut-like open path must be review-required in lenient mode",
    )
    _assert(lenient["blocking_conflicts"] == [], "cut-like open path must not block in lenient mode")

    strict_families = [item["family"] for item in strict["blocking_conflicts"]]
    _assert(
        "cut_like_open_path_on_canonical_layer" in strict_families,
        "cut-like open path must block in strict_mode",
    )


def _scenario_marking_open_path_is_silent_success() -> None:
    inspect_result = _build_inspect_result(
        entities=[_entity(entity_index=0, layer="MARKING", color_index=2, closed=False, type_="LINE", point_count=2)],
        contour_layers=[],
        open_path_layers={"MARKING": 1},
    )

    result = resolve_dxf_roles(inspect_result)

    _assert(
        _layer_record(result, "MARKING")["canonical_role"] == "MARKING",
        "marking layer with open path must still resolve to MARKING",
    )
    _assert(result["review_required_candidates"] == [], "marking open path must be silent success")
    _assert(result["blocking_conflicts"] == [], "marking open path must be silent success")


def _scenario_interactive_review_off_promotes_ambiguity_to_blocking() -> None:
    inspect_result = _build_inspect_result(
        entities=[_entity(entity_index=0, layer="LASER_GENERIC", color_index=3)],
    )

    result = resolve_dxf_roles(
        inspect_result,
        rules_profile={"cut_color_map": [3], "interactive_review_on_ambiguity": False},
    )

    blocking_families = [item["family"] for item in result["blocking_conflicts"]]
    _assert(
        "cut_like_topology_ambiguous" in blocking_families,
        "interactive_review_on_ambiguity=False must promote ambiguity to blocking",
    )


def _scenario_color_hint_cannot_override_canonical_layer() -> None:
    inspect_result = _build_inspect_result(
        entities=[_entity(entity_index=0, layer="MARKING", color_index=4, closed=False, type_="LINE", point_count=2)],
        contour_layers=[],
        open_path_layers={"MARKING": 1},
    )

    result = resolve_dxf_roles(
        inspect_result,
        rules_profile={"cut_color_map": [4], "marking_color_map": []},
    )

    record = _layer_record(result, "MARKING")
    _assert(record["canonical_role"] == "MARKING", "color hint must not override canonical MARKING layer")
    _assert(
        record["decision_source"] == "explicit_canonical_layer",
        "decision_source must stay explicit_canonical_layer even when color hint disagrees",
    )
    families = [item["family"] for item in result["review_required_candidates"]]
    _assert(
        "explicit_layer_vs_color_hint_conflict" in families,
        "color-hint conflict must surface as review_required",
    )


def _scenario_rules_profile_echo_only_t2_minimum() -> None:
    inspect_result = _build_inspect_result(entities=[])

    result = resolve_dxf_roles(
        inspect_result,
        rules_profile={
            "strict_mode": True,
            "interactive_review_on_ambiguity": False,
            "cut_color_map": [3],
            "marking_color_map": [2],
            "max_gap_close_mm": 0.5,
            "auto_repair_enabled": True,
            "metadata_jsonb": {"unrelated": "field"},
        },
    )

    echo_keys = set(result["rules_profile_echo"].keys())
    _assert(
        echo_keys == {"strict_mode", "interactive_review_on_ambiguity", "cut_color_map", "marking_color_map"},
        f"rules_profile_echo must contain only the minimal T2 slice, got: {sorted(echo_keys)}",
    )
    ignored = set(result["diagnostics"]["rules_profile_source_fields_ignored"])
    _assert(
        {"max_gap_close_mm", "auto_repair_enabled", "metadata_jsonb"} <= ignored,
        f"out-of-scope profile fields must be reflected as ignored, got: {sorted(ignored)}",
    )


def main() -> int:
    _scenario_canonical_green_path()
    _scenario_color_hint_plus_topology_outer()
    _scenario_cut_like_open_path_review_vs_blocking()
    _scenario_marking_open_path_is_silent_success()
    _scenario_interactive_review_off_promotes_ambiguity_to_blocking()
    _scenario_color_hint_cannot_override_canonical_layer()
    _scenario_rules_profile_echo_only_t2_minimum()
    print("[OK] DXF Prefilter E2-T2 color/layer role resolver smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
