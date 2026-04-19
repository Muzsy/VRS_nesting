#!/usr/bin/env python3
"""DXF Prefilter E2-T1 -- Preflight inspect engine (V1).

This module is the inspect-only backend layer in front of the DXF prefilter
lane. It produces a deterministic, raw observation of what is inside a DXF /
JSON-fixture source:

* layer / color / linetype / entity inventories (raw, not canonicalised),
* contour / open-path / duplicate-contour / outer-like / inner-like
  candidates based on the existing importer truth,
* a separate ``diagnostics`` layer for inspect-level messages.

The service intentionally:

* does NOT perform role assignment (``CUT_OUTER`` / ``CUT_INNER`` /
  ``MARKING``) -- that is reserved for E2-T2;
* does NOT perform gap repair or deduplication -- that is E2-T3 / E2-T4;
* does NOT emit an acceptance outcome, write DB rows or mutate API routes --
  that is E2-T6 / E3 scope;
* does NOT invent RGB / BYLAYER color policy when the source backend omits
  explicit signals -- raw absence is reported as ``None``.

The service is built on top of the minimal, public importer inspect surface
(``vrs_nesting.dxf.importer.normalize_source_entities`` +
``probe_layer_rings``) so that there is still exactly one DXF parser truth
in the repo.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from vrs_nesting.dxf.importer import (
    DxfImportError,
    normalize_source_entities,
    probe_layer_rings,
)

__all__ = [
    "DxfPreflightInspectError",
    "inspect_dxf_source",
]


class DxfPreflightInspectError(RuntimeError):
    """Hard-fail for preflight inspect (e.g. unreadable source).

    Raised only when the underlying importer itself cannot open the source
    file. Soft (recoverable) problems land in ``result["diagnostics"]``
    instead of raising so that the caller can still read the partial
    inventory.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


_FINGERPRINT_HEX_LEN = 16
_COORD_ROUND_DECIMALS = 6
_RAW_HARD_ERRORS_PROPAGATE: frozenset[str] = frozenset(
    {
        "DXF_PATH_NOT_FOUND",
        "DXF_UNSUPPORTED_INPUT",
        "DXF_READ_FAILED",
        "DXF_BACKEND_MISSING",
        "DXF_JSON_PARSE",
        "DXF_JSON_SCHEMA",
        "DXF_UNSUPPORTED_UNITS",
    }
)


def inspect_dxf_source(source_path: str | Path) -> dict[str, Any]:
    """Run the DXF Preflight inspect engine on a source file.

    Returns a deterministic, JSON-serialisable inspect result with separate
    inventory / candidate / diagnostics layers. See module docstring for
    scope and non-scope details.
    """

    path = Path(source_path)
    try:
        entities = normalize_source_entities(path)
    except DxfImportError as exc:
        if exc.code in _RAW_HARD_ERRORS_PROPAGATE:
            raise DxfPreflightInspectError(exc.code, exc.message) from exc
        # Non-hard source read errors are reported as diagnostics but do not
        # raise. This keeps the inspect lane observable even when individual
        # entities have malformed data.
        return _build_soft_failure_result(path=path, hard_error=exc)

    backend = _resolve_backend(path)
    source_size_bytes = _safe_source_size_bytes(path)

    entity_inventory = _build_entity_inventory(entities)
    layer_inventory = _build_layer_inventory(entities)
    color_inventory = _build_color_inventory(entities)
    linetype_inventory = _build_linetype_inventory(entities)

    unique_layers = [item["layer"] for item in layer_inventory]
    layer_probes = {layer: probe_layer_rings(entities, layer=layer) for layer in unique_layers}

    contour_candidates = _build_contour_candidates(layer_probes)
    open_path_candidates = _build_open_path_candidates(layer_probes)
    duplicate_contour_candidates = _build_duplicate_contour_candidates(contour_candidates)
    outer_like_candidates, inner_like_candidates = _build_topology_candidates(contour_candidates)

    diagnostics = _build_diagnostics(layer_probes=layer_probes)

    return {
        "source_path": str(path.resolve()),
        "backend": backend,
        "source_size_bytes": source_size_bytes,
        "entity_inventory": entity_inventory,
        "layer_inventory": layer_inventory,
        "color_inventory": color_inventory,
        "linetype_inventory": linetype_inventory,
        "contour_candidates": contour_candidates,
        "open_path_candidates": open_path_candidates,
        "duplicate_contour_candidates": duplicate_contour_candidates,
        "outer_like_candidates": outer_like_candidates,
        "inner_like_candidates": inner_like_candidates,
        "diagnostics": diagnostics,
    }


# ---------------------------------------------------------------------------
# Inventory builders
# ---------------------------------------------------------------------------


def _build_entity_inventory(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, entity in enumerate(entities):
        points = entity.get("points")
        point_count = len(points) if isinstance(points, list) else None
        closed_value = entity.get("closed")
        closed = closed_value if isinstance(closed_value, bool) else None
        out.append(
            {
                "entity_index": idx,
                "layer": str(entity.get("layer", "")),
                "type": str(entity.get("type", "")).upper(),
                "closed": closed,
                "color_index": _as_optional_int(entity.get("color_index")),
                "linetype_name": _as_optional_str(entity.get("linetype_name")),
                "point_count": point_count,
                "unsupported": bool(entity.get("_unsupported", False)),
            }
        )
    return out


def _build_layer_inventory(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_layer: dict[str, dict[str, Any]] = {}
    for entity in entities:
        layer = str(entity.get("layer", ""))
        etype = str(entity.get("type", "")).upper()
        unsupported = bool(entity.get("_unsupported", False))
        bucket = by_layer.setdefault(
            layer,
            {
                "layer": layer,
                "entity_count": 0,
                "supported_count": 0,
                "unsupported_count": 0,
                "types": set(),
            },
        )
        bucket["entity_count"] += 1
        if unsupported:
            bucket["unsupported_count"] += 1
        else:
            bucket["supported_count"] += 1
        bucket["types"].add(etype)

    ordered: list[dict[str, Any]] = []
    for layer in sorted(by_layer):
        info = by_layer[layer]
        ordered.append(
            {
                "layer": info["layer"],
                "entity_count": info["entity_count"],
                "supported_count": info["supported_count"],
                "unsupported_count": info["unsupported_count"],
                "types": sorted(info["types"]),
            }
        )
    return ordered


def _build_color_inventory(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[int | None, int] = {}
    for entity in entities:
        key = _as_optional_int(entity.get("color_index"))
        counts[key] = counts.get(key, 0) + 1
    return _inventory_sorted(counts, key_name="color_index")


def _build_linetype_inventory(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str | None, int] = {}
    for entity in entities:
        key = _as_optional_str(entity.get("linetype_name"))
        counts[key] = counts.get(key, 0) + 1
    return _inventory_sorted(counts, key_name="linetype_name")


# ---------------------------------------------------------------------------
# Candidate builders
# ---------------------------------------------------------------------------


def _build_contour_candidates(
    layer_probes: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for layer in sorted(layer_probes):
        probe = layer_probes[layer]
        rings = probe.get("rings") or []
        for ring_index, ring in enumerate(rings):
            out.append(
                {
                    "layer": layer,
                    "ring_index": ring_index,
                    "point_count": len(ring),
                    "bbox": _bbox_of_ring(ring),
                    "fingerprint": _ring_fingerprint(ring),
                }
            )
    return out


def _build_open_path_candidates(
    layer_probes: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for layer in sorted(layer_probes):
        probe = layer_probes[layer]
        open_count = int(probe.get("open_path_count") or 0)
        if open_count > 0:
            out.append({"layer": layer, "open_path_count": open_count})
    return out


def _build_duplicate_contour_candidates(
    contour_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for candidate in contour_candidates:
        fingerprint = str(candidate["fingerprint"])
        groups.setdefault(fingerprint, []).append(candidate)

    out: list[dict[str, Any]] = []
    for fingerprint in sorted(groups):
        members = groups[fingerprint]
        if len(members) < 2:
            continue
        refs = [
            {"layer": m["layer"], "ring_index": int(m["ring_index"])} for m in members
        ]
        refs.sort(key=lambda item: (item["layer"], item["ring_index"]))
        out.append(
            {
                "fingerprint": fingerprint,
                "count": len(members),
                "ring_references": refs,
            }
        )
    return out


def _build_topology_candidates(
    contour_candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return ``(outer_like, inner_like)`` candidates based on bbox containment.

    This is explicitly a *topology proxy*, not a role decision. The canonical
    role assignment (``CUT_OUTER`` vs ``CUT_INNER`` vs ``MARKING``) happens
    in E2-T2. T1 only exposes whether one ring's bbox strictly contains
    another ring's bbox so that the later lane has a ready-made signal.
    """

    outer_like: list[dict[str, Any]] = []
    inner_like: list[dict[str, Any]] = []

    contains_map: dict[tuple[str, int], list[dict[str, Any]]] = {}
    contained_by_map: dict[tuple[str, int], list[dict[str, Any]]] = {}

    for i, candidate_a in enumerate(contour_candidates):
        for j, candidate_b in enumerate(contour_candidates):
            if i == j:
                continue
            if _bbox_strictly_contains(candidate_a["bbox"], candidate_b["bbox"]):
                a_key = (candidate_a["layer"], int(candidate_a["ring_index"]))
                b_key = (candidate_b["layer"], int(candidate_b["ring_index"]))
                contains_map.setdefault(a_key, []).append(
                    {"layer": candidate_b["layer"], "ring_index": int(candidate_b["ring_index"])}
                )
                contained_by_map.setdefault(b_key, []).append(
                    {"layer": candidate_a["layer"], "ring_index": int(candidate_a["ring_index"])}
                )

    for candidate in contour_candidates:
        key = (candidate["layer"], int(candidate["ring_index"]))
        contained_refs = contains_map.get(key)
        if contained_refs:
            refs = sorted(contained_refs, key=lambda item: (item["layer"], item["ring_index"]))
            outer_like.append(
                {
                    "layer": candidate["layer"],
                    "ring_index": int(candidate["ring_index"]),
                    "contains_ring_references": refs,
                }
            )
        outer_refs = contained_by_map.get(key)
        if outer_refs:
            refs = sorted(outer_refs, key=lambda item: (item["layer"], item["ring_index"]))
            inner_like.append(
                {
                    "layer": candidate["layer"],
                    "ring_index": int(candidate["ring_index"]),
                    "contained_by_ring_references": refs,
                }
            )

    outer_like.sort(key=lambda item: (item["layer"], item["ring_index"]))
    inner_like.sort(key=lambda item: (item["layer"], item["ring_index"]))
    return outer_like, inner_like


# ---------------------------------------------------------------------------
# Diagnostics + misc helpers
# ---------------------------------------------------------------------------


def _build_diagnostics(*, layer_probes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    probe_errors: list[dict[str, Any]] = []
    for layer in sorted(layer_probes):
        probe = layer_probes[layer]
        hard_error = probe.get("hard_error")
        if isinstance(hard_error, dict):
            probe_errors.append(
                {
                    "layer": layer,
                    "code": str(hard_error.get("code", "")),
                    "message": str(hard_error.get("message", "")),
                }
            )
    return {
        "probe_errors": probe_errors,
        "notes": [],
    }


def _build_soft_failure_result(
    *, path: Path, hard_error: DxfImportError
) -> dict[str, Any]:
    return {
        "source_path": str(path.resolve()),
        "backend": _resolve_backend(path),
        "source_size_bytes": _safe_source_size_bytes(path),
        "entity_inventory": [],
        "layer_inventory": [],
        "color_inventory": [],
        "linetype_inventory": [],
        "contour_candidates": [],
        "open_path_candidates": [],
        "duplicate_contour_candidates": [],
        "outer_like_candidates": [],
        "inner_like_candidates": [],
        "diagnostics": {
            "probe_errors": [
                {
                    "layer": "*",
                    "code": hard_error.code,
                    "message": hard_error.message,
                }
            ],
            "notes": ["source_read_soft_failure"],
        },
    }


def _inventory_sorted(
    counts: dict[Any, int], *, key_name: str
) -> list[dict[str, Any]]:
    def sort_key(item: tuple[Any, int]) -> tuple[int, Any]:
        value, _count = item
        # Push None to the end deterministically.
        return (1 if value is None else 0, value if value is not None else "")

    ordered = sorted(counts.items(), key=sort_key)
    return [{key_name: value, "count": count} for value, count in ordered]


def _as_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return int(value)


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _resolve_backend(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix == ".dxf":
        return "dxf"
    return "unknown"


def _safe_source_size_bytes(path: Path) -> int | None:
    try:
        return int(path.stat().st_size)
    except OSError:
        return None


def _bbox_of_ring(ring: list[list[float]]) -> dict[str, float]:
    xs = [float(point[0]) for point in ring]
    ys = [float(point[1]) for point in ring]
    return {
        "min_x": min(xs),
        "min_y": min(ys),
        "max_x": max(xs),
        "max_y": max(ys),
    }


def _bbox_strictly_contains(outer: dict[str, float], inner: dict[str, float]) -> bool:
    return (
        float(outer["min_x"]) < float(inner["min_x"])
        and float(outer["min_y"]) < float(inner["min_y"])
        and float(outer["max_x"]) > float(inner["max_x"])
        and float(outer["max_y"]) > float(inner["max_y"])
    )


def _ring_fingerprint(ring: list[list[float]]) -> str:
    if not ring:
        return "0" * _FINGERPRINT_HEX_LEN

    rounded: list[tuple[float, float]] = [
        (round(float(p[0]), _COORD_ROUND_DECIMALS), round(float(p[1]), _COORD_ROUND_DECIMALS))
        for p in ring
    ]
    min_idx = min(range(len(rounded)), key=lambda i: rounded[i])
    rotated = rounded[min_idx:] + rounded[:min_idx]
    reversed_rotated = list(reversed(rotated))
    canonical = rotated if rotated <= reversed_rotated else reversed_rotated
    canonical_payload = json.dumps(canonical, separators=(",", ":"))
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()[:_FINGERPRINT_HEX_LEN]
