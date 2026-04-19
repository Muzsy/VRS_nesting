#!/usr/bin/env python3
"""DXF Prefilter E2-T2 -- color/layer role resolver unit tests.

These tests are intentionally backend-independent: they exercise the
resolver against deterministic in-memory inspect-result fixtures so they do
not require ``ezdxf`` or any DXF / JSON file I/O. The E2-T1 inspect engine
is covered by its own tests; this suite proves that, given a stable
inspect-result shape and a minimal rules profile, the resolver:

* respects the precedence: explicit canonical layer > color hint >
  topology proxy;
* lets the color hint provide a cut-like / marking-like direction only
  when the layer is non-canonical;
* uses the topology proxy only to disambiguate outer vs inner for cut-like
  signals;
* names conflict families instead of silencing them;
* never produces an acceptance outcome / repair / DXF write;
* keeps the existing ``CUT_OUTER`` / ``CUT_INNER`` importer truth on the
  easiest green path.
"""

from __future__ import annotations

from typing import Any

import pytest

from api.services.dxf_preflight_role_resolver import (
    CANONICAL_LAYER_ROLES,
    DxfPreflightRoleResolverError,
    resolve_dxf_roles,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


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


def _layer_record(result: dict[str, Any], layer: str) -> dict[str, Any]:
    for record in result["layer_role_assignments"]:
        if record["layer"] == layer:
            return record
    raise KeyError(layer)


# ---------------------------------------------------------------------------
# Output shape + scope guards
# ---------------------------------------------------------------------------


def test_resolver_output_shape_has_documented_layers_only():
    inspect_result = _build_inspect_result(
        entities=[_entity(entity_index=0, layer="CUT_OUTER", color_index=7)],
        outer_like_layers=["CUT_OUTER"],
    )

    result = resolve_dxf_roles(inspect_result)

    assert set(result.keys()) == {
        "rules_profile_echo",
        "layer_role_assignments",
        "entity_role_assignments",
        "resolved_role_inventory",
        "review_required_candidates",
        "blocking_conflicts",
        "diagnostics",
    }


def test_resolver_must_not_emit_acceptance_or_repair_world():
    inspect_result = _build_inspect_result(
        entities=[_entity(entity_index=0, layer="CUT_OUTER")],
        outer_like_layers=["CUT_OUTER"],
    )

    result = resolve_dxf_roles(inspect_result)

    forbidden = {
        "accepted_for_import",
        "preflight_rejected",
        "acceptance_outcome",
        "acceptance_status",
        "repair",
        "repairs",
        "gap_fixes",
        "normalized_dxf",
    }
    assert not forbidden & set(result.keys())
    for layer_record in result["layer_role_assignments"]:
        assert "accepted_for_import" not in layer_record
        assert "rejected" not in layer_record


def test_canonical_layer_roles_constant_matches_documented_truth():
    assert CANONICAL_LAYER_ROLES == frozenset({"CUT_OUTER", "CUT_INNER", "MARKING"})


# ---------------------------------------------------------------------------
# Precedence: explicit canonical layer > color hint > topology proxy
# ---------------------------------------------------------------------------


def test_explicit_canonical_layer_precedence_keeps_importer_truth_green():
    inspect_result = _build_inspect_result(
        entities=[
            _entity(entity_index=0, layer="CUT_OUTER", color_index=7),
            _entity(entity_index=1, layer="CUT_INNER", color_index=1),
            _entity(entity_index=2, layer="MARKING", color_index=2, closed=False, type_="LINE", point_count=2),
        ],
        outer_like_layers=["CUT_OUTER"],
        inner_like_layers=["CUT_INNER"],
    )

    result = resolve_dxf_roles(inspect_result)

    assert _layer_record(result, "CUT_OUTER")["canonical_role"] == "CUT_OUTER"
    assert _layer_record(result, "CUT_OUTER")["decision_source"] == "explicit_canonical_layer"
    assert _layer_record(result, "CUT_INNER")["canonical_role"] == "CUT_INNER"
    assert _layer_record(result, "MARKING")["canonical_role"] == "MARKING"
    assert result["blocking_conflicts"] == []
    assert result["review_required_candidates"] == []


def test_color_hint_falls_back_to_marking_on_non_canonical_layer():
    inspect_result = _build_inspect_result(
        entities=[
            _entity(entity_index=0, layer="ETCH_GUIDE", color_index=2, closed=False, type_="LINE", point_count=2),
        ],
        contour_layers=[],
        open_path_layers={"ETCH_GUIDE": 1},
    )

    result = resolve_dxf_roles(
        inspect_result,
        rules_profile={"marking_color_map": [2], "cut_color_map": []},
    )

    record = _layer_record(result, "ETCH_GUIDE")
    assert record["canonical_role"] == "MARKING"
    assert record["decision_source"] == "color_hint"
    assert result["blocking_conflicts"] == []
    assert result["review_required_candidates"] == []


def test_color_hint_plus_topology_proxy_resolves_outer_for_cut_like_layer():
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

    outer_record = _layer_record(result, "LASER_OUTER_4")
    inner_record = _layer_record(result, "LASER_INNER_5")
    assert outer_record["canonical_role"] == "CUT_OUTER"
    assert outer_record["decision_source"] == "color_hint_plus_topology_proxy"
    assert inner_record["canonical_role"] == "CUT_INNER"
    assert inner_record["decision_source"] == "color_hint_plus_topology_proxy"
    assert result["blocking_conflicts"] == []
    assert result["review_required_candidates"] == []


def test_color_hint_does_not_override_canonical_layer():
    """Explicit `MARKING` layer must keep its role even if a 'cut' color hint hits."""

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
    assert record["canonical_role"] == "MARKING"
    assert record["decision_source"] == "explicit_canonical_layer"
    families = sorted(item["family"] for item in result["review_required_candidates"])
    assert "explicit_layer_vs_color_hint_conflict" in families


# ---------------------------------------------------------------------------
# Conflict family coverage
# ---------------------------------------------------------------------------


def test_explicit_layer_vs_color_hint_conflict_is_review_required_only():
    inspect_result = _build_inspect_result(
        entities=[_entity(entity_index=0, layer="CUT_OUTER", color_index=2)],
        outer_like_layers=["CUT_OUTER"],
    )

    lenient = resolve_dxf_roles(
        inspect_result,
        rules_profile={"marking_color_map": [2], "cut_color_map": []},
    )
    strict = resolve_dxf_roles(
        inspect_result,
        rules_profile={"strict_mode": True, "marking_color_map": [2], "cut_color_map": []},
    )

    assert lenient["blocking_conflicts"] == []
    review_families = [item["family"] for item in lenient["review_required_candidates"]]
    assert review_families == ["explicit_layer_vs_color_hint_conflict"]
    # Diagnostic-only family stays review_required even in strict_mode.
    assert strict["blocking_conflicts"] == []
    strict_families = [item["family"] for item in strict["review_required_candidates"]]
    assert strict_families == ["explicit_layer_vs_color_hint_conflict"]


def test_cut_like_open_path_is_review_required_lenient_blocking_strict():
    inspect_result = _build_inspect_result(
        entities=[_entity(entity_index=0, layer="CUT_OUTER", color_index=7, closed=False)],
        contour_layers=[],
        open_path_layers={"CUT_OUTER": 1},
        outer_like_layers=["CUT_OUTER"],
    )

    lenient = resolve_dxf_roles(inspect_result)
    strict = resolve_dxf_roles(inspect_result, rules_profile={"strict_mode": True})

    lenient_families = [item["family"] for item in lenient["review_required_candidates"]]
    assert "cut_like_open_path_on_canonical_layer" in lenient_families
    assert lenient["blocking_conflicts"] == []

    strict_families = [item["family"] for item in strict["blocking_conflicts"]]
    assert "cut_like_open_path_on_canonical_layer" in strict_families
    assert strict["review_required_candidates"] == []


def test_marking_layer_open_path_is_silent_success():
    """Marking-jellegu layeren a nyitott path nem konfliktus."""

    inspect_result = _build_inspect_result(
        entities=[_entity(entity_index=0, layer="MARKING", color_index=2, closed=False, type_="LINE", point_count=2)],
        contour_layers=[],
        open_path_layers={"MARKING": 1},
    )

    result = resolve_dxf_roles(inspect_result)

    record = _layer_record(result, "MARKING")
    assert record["canonical_role"] == "MARKING"
    assert result["blocking_conflicts"] == []
    assert result["review_required_candidates"] == []


def test_cut_like_topology_ambiguous_is_unassigned_with_review_or_blocking():
    inspect_result = _build_inspect_result(
        entities=[_entity(entity_index=0, layer="LASER_GENERIC", color_index=3)],
        # Color says cut-like, but topology proxy is silent (no outer/inner-like).
    )

    lenient = resolve_dxf_roles(
        inspect_result,
        rules_profile={"cut_color_map": [3]},
    )
    strict = resolve_dxf_roles(
        inspect_result,
        rules_profile={"cut_color_map": [3], "strict_mode": True},
    )

    lenient_record = _layer_record(lenient, "LASER_GENERIC")
    assert lenient_record["canonical_role"] == "UNASSIGNED"
    assert lenient_record["decision_source"] == "unresolved_cut_like_topology_ambiguous"
    review_families = [item["family"] for item in lenient["review_required_candidates"]]
    assert "cut_like_topology_ambiguous" in review_families
    assert lenient["blocking_conflicts"] == []

    blocking_families = [item["family"] for item in strict["blocking_conflicts"]]
    assert "cut_like_topology_ambiguous" in blocking_families


def test_interactive_review_flag_promotes_ambiguity_to_blocking():
    """`interactive_review_on_ambiguity=False` blocks even in lenient strict_mode."""

    inspect_result = _build_inspect_result(
        entities=[_entity(entity_index=0, layer="LASER_GENERIC", color_index=3)],
    )

    no_review = resolve_dxf_roles(
        inspect_result,
        rules_profile={"cut_color_map": [3], "interactive_review_on_ambiguity": False},
    )

    blocking_families = [item["family"] for item in no_review["blocking_conflicts"]]
    assert "cut_like_topology_ambiguous" in blocking_families
    assert no_review["review_required_candidates"] == []


def test_mixed_cut_and_marking_on_non_canonical_layer_is_unassigned_with_conflict():
    inspect_result = _build_inspect_result(
        entities=[
            _entity(entity_index=0, layer="MIXED_LAYER", color_index=3),
            _entity(entity_index=1, layer="MIXED_LAYER", color_index=2),
        ],
    )

    result = resolve_dxf_roles(
        inspect_result,
        rules_profile={"cut_color_map": [3], "marking_color_map": [2]},
    )

    record = _layer_record(result, "MIXED_LAYER")
    assert record["canonical_role"] == "UNASSIGNED"
    assert record["decision_source"] == "unresolved_mixed_color_hints"
    families = [item["family"] for item in result["review_required_candidates"]]
    assert "mixed_cut_and_marking_on_non_canonical_layer" in families


def test_topology_proxy_not_compatible_is_diagnostic_only():
    """Bbox topology that disagrees with explicit CUT_OUTER must NOT block."""

    inspect_result = _build_inspect_result(
        entities=[_entity(entity_index=0, layer="CUT_OUTER", color_index=7)],
        outer_like_layers=[],
        inner_like_layers=["CUT_OUTER"],  # bbox-contained -> topology disagrees
    )

    strict = resolve_dxf_roles(inspect_result, rules_profile={"strict_mode": True})

    assert _layer_record(strict, "CUT_OUTER")["canonical_role"] == "CUT_OUTER"
    assert strict["blocking_conflicts"] == []
    families = [item["family"] for item in strict["review_required_candidates"]]
    assert "topology_proxy_not_compatible_with_explicit_layer" in families


# ---------------------------------------------------------------------------
# Outputs / inventory layers
# ---------------------------------------------------------------------------


def test_resolved_role_inventory_aggregates_layer_and_entity_counts():
    inspect_result = _build_inspect_result(
        entities=[
            _entity(entity_index=0, layer="CUT_OUTER", color_index=7),
            _entity(entity_index=1, layer="CUT_INNER", color_index=1),
            _entity(entity_index=2, layer="CUT_INNER", color_index=1),
            _entity(entity_index=3, layer="MARKING", color_index=2, closed=False, type_="LINE", point_count=2),
        ],
        outer_like_layers=["CUT_OUTER"],
        inner_like_layers=["CUT_INNER"],
    )

    result = resolve_dxf_roles(inspect_result)
    inventory = result["resolved_role_inventory"]

    assert inventory["CUT_OUTER"] == {"layer_count": 1, "entity_count": 1, "layers": ["CUT_OUTER"]}
    assert inventory["CUT_INNER"] == {"layer_count": 1, "entity_count": 2, "layers": ["CUT_INNER"]}
    assert inventory["MARKING"] == {"layer_count": 1, "entity_count": 1, "layers": ["MARKING"]}
    assert inventory["UNASSIGNED"] == {"layer_count": 0, "entity_count": 0, "layers": []}


def test_entity_role_assignments_record_color_direction_per_entity():
    inspect_result = _build_inspect_result(
        entities=[
            _entity(entity_index=0, layer="MIXED_LAYER", color_index=3),
            _entity(entity_index=1, layer="MIXED_LAYER", color_index=2),
            _entity(entity_index=2, layer="MIXED_LAYER", color_index=99),  # unmapped
        ],
    )

    result = resolve_dxf_roles(
        inspect_result,
        rules_profile={"cut_color_map": [3], "marking_color_map": [2]},
    )

    by_index = {item["entity_index"]: item for item in result["entity_role_assignments"]}
    assert by_index[0]["color_direction"] == "cut"
    assert by_index[1]["color_direction"] == "marking"
    assert by_index[2]["color_direction"] is None


def test_rules_profile_echo_only_contains_t2_minimum_fields():
    inspect_result = _build_inspect_result(entities=[])

    result = resolve_dxf_roles(
        inspect_result,
        rules_profile={
            "strict_mode": True,
            "interactive_review_on_ambiguity": False,
            "cut_color_map": [3],
            "marking_color_map": [2],
            # Out-of-T2-scope keys must be ignored.
            "max_gap_close_mm": 0.5,
            "auto_repair_enabled": True,
            "metadata_jsonb": {"unrelated": "field"},
        },
    )

    echo = result["rules_profile_echo"]
    assert set(echo.keys()) == {
        "strict_mode",
        "interactive_review_on_ambiguity",
        "cut_color_map",
        "marking_color_map",
    }
    assert echo["strict_mode"] is True
    assert echo["interactive_review_on_ambiguity"] is False
    assert echo["cut_color_map"] == [3]
    assert echo["marking_color_map"] == [2]

    diagnostics = result["diagnostics"]
    assert "max_gap_close_mm" in diagnostics["rules_profile_source_fields_ignored"]
    assert "auto_repair_enabled" in diagnostics["rules_profile_source_fields_ignored"]
    assert "metadata_jsonb" in diagnostics["rules_profile_source_fields_ignored"]


def test_rules_profile_invalid_field_type_raises():
    inspect_result = _build_inspect_result(entities=[])

    with pytest.raises(DxfPreflightRoleResolverError) as exc:
        resolve_dxf_roles(inspect_result, rules_profile={"strict_mode": "yes"})

    assert exc.value.code == "DXF_ROLE_RESOLVER_INVALID_RULES_PROFILE"


def test_resolver_does_not_invent_signals_when_inspect_result_is_silent():
    """No layers, no entities -> empty role world, no review/blocking."""

    inspect_result = _build_inspect_result(entities=[])

    result = resolve_dxf_roles(inspect_result, rules_profile={"cut_color_map": [3]})

    assert result["layer_role_assignments"] == []
    assert result["entity_role_assignments"] == []
    assert result["review_required_candidates"] == []
    assert result["blocking_conflicts"] == []
    assert all(
        bucket["layer_count"] == 0 and bucket["entity_count"] == 0
        for bucket in result["resolved_role_inventory"].values()
    )


def test_resolver_rejects_non_mapping_inspect_result():
    with pytest.raises(DxfPreflightRoleResolverError) as exc:
        resolve_dxf_roles("not-a-mapping")  # type: ignore[arg-type]

    assert exc.value.code == "DXF_ROLE_RESOLVER_INVALID_INSPECT_RESULT"
