#!/usr/bin/env python3
"""DXF Prefilter E2-T5 -- normalized DXF writer smoke."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.dxf_preflight_duplicate_dedupe import dedupe_dxf_duplicate_contours
from api.services.dxf_preflight_gap_repair import repair_dxf_gaps
from api.services.dxf_preflight_inspect import inspect_dxf_source
from api.services.dxf_preflight_normalized_dxf_writer import write_normalized_dxf
from api.services.dxf_preflight_role_resolver import resolve_dxf_roles

EXPECTED_TOP_LEVEL_KEYS: tuple[str, ...] = (
    "rules_profile_echo",
    "normalized_dxf",
    "writer_layer_inventory",
    "skipped_source_entities",
    "diagnostics",
)

FORBIDDEN_TOP_LEVEL_KEYS: tuple[str, ...] = (
    "accepted_for_import",
    "preflight_rejected",
    "acceptance",
    "acceptance_outcome",
    "db_insert",
    "route",
)


def _assert(cond: bool, message: str) -> None:
    if not cond:
        raise AssertionError(message)


def _write_fixture(path: Path, entities: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps({"entities": entities}), encoding="utf-8")


def _square(*, size: float = 10.0, x: float = 0.0, y: float = 0.0) -> list[list[float]]:
    return [[x, y], [x + size, y], [x + size, y + size], [x, y + size]]


def _polyline_entity(*, layer: str, points: list[list[float]]) -> dict[str, Any]:
    return {"layer": layer, "type": "LWPOLYLINE", "closed": True, "points": points}


def _run_chain(
    *,
    tmpdir: Path,
    fixture_name: str,
    entities: list[dict[str, Any]],
    role_rules_profile: dict[str, Any] | None = None,
    gap_rules_profile: dict[str, Any] | None = None,
    dedupe_rules_profile: dict[str, Any] | None = None,
    writer_rules_profile: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], Path]:
    fixture_path = tmpdir / fixture_name
    _write_fixture(fixture_path, entities)

    inspect_result = inspect_dxf_source(fixture_path)
    role_resolution = resolve_dxf_roles(
        inspect_result,
        rules_profile=role_rules_profile,
    )
    gap_result = repair_dxf_gaps(
        inspect_result,
        role_resolution,
        rules_profile=gap_rules_profile,
    )
    dedupe_result = dedupe_dxf_duplicate_contours(
        inspect_result,
        role_resolution,
        gap_result,
        rules_profile=dedupe_rules_profile,
    )

    output_path = tmpdir / f"{fixture_path.stem}.normalized.dxf"
    result = write_normalized_dxf(
        inspect_result,
        role_resolution,
        gap_result,
        dedupe_result,
        output_path=output_path,
        rules_profile=writer_rules_profile,
    )
    return result, output_path


def _check_shape(result: dict[str, Any]) -> None:
    for key in EXPECTED_TOP_LEVEL_KEYS:
        _assert(key in result, f"missing top-level key: {key}")
    for key in FORBIDDEN_TOP_LEVEL_KEYS:
        _assert(key not in result, f"T5 writer must not expose {key}")


def _read_doc(path: Path) -> Any:
    try:
        import ezdxf
    except ImportError as exc:
        raise AssertionError("smoke requires ezdxf dependency") from exc
    return ezdxf.readfile(path)


def _scenario_full_chain_writer_boundary(tmpdir: Path) -> None:
    entities = [
        _polyline_entity(layer="CUT_OUTER", points=_square()),
        _polyline_entity(layer="CUT_OUTER", points=_square()),  # duplicate source contour
        {"layer": "CUT_OUTER", "type": "LINE", "points": [[0.0, 0.0], [20.0, 0.0]]},  # open cut source
        {"layer": "SCRIBE_LAYER", "type": "LINE", "points": [[2.0, 2.0], [8.0, 2.0]], "color_index": 2},
        {"layer": "SCRIBE_LAYER", "type": "TEXT", "closed": False, "color_index": 2},
    ]

    result, output_path = _run_chain(
        tmpdir=tmpdir,
        fixture_name="t5_full_chain.json",
        entities=entities,
        role_rules_profile={"marking_color_map": [2]},
        dedupe_rules_profile={
            "auto_repair_enabled": True,
            "duplicate_contour_merge_tolerance_mm": 0.05,
        },
    )

    _check_shape(result)
    _assert(output_path.is_file(), "normalized artifact file missing")
    _assert(result["normalized_dxf"]["cut_contour_count"] == 1, "cut world must come from T4 deduped set")
    _assert(result["normalized_dxf"]["marking_entity_count"] == 1, "one replayable marking entity expected")
    _assert(len(result["skipped_source_entities"]) == 1, "unsupported marking entity must be skipped")
    _assert(result["skipped_source_entities"][0]["source_type"] == "TEXT", "expected TEXT skip record")
    _assert(
        result["diagnostics"]["source_cut_entities_not_replayed_count"] >= 2,
        "source cut entities should be suppressed in T5 writer boundary",
    )

    doc = _read_doc(output_path)
    cut_outer = [entity for entity in doc.modelspace() if str(entity.dxf.layer) == "CUT_OUTER"]
    cut_outer_types = [str(entity.dxftype()).upper() for entity in cut_outer]
    _assert(cut_outer_types.count("LWPOLYLINE") == 1, "exactly one deduped cut contour should be written")
    _assert("LINE" not in cut_outer_types, "open source cut LINE must not leak into output")

    marking = [entity for entity in doc.modelspace() if str(entity.dxf.layer) == "MARKING"]
    _assert(len(marking) == 1, "expected one MARKING replay entity")
    _assert(str(marking[0].dxftype()).upper() == "LINE", "marking replay entity should be LINE")


def _scenario_canonical_layer_colors(tmpdir: Path) -> None:
    entities = [
        _polyline_entity(layer="CUT_OUTER", points=_square()),
        {"layer": "ETCH", "type": "LINE", "points": [[0.0, 1.0], [5.0, 1.0]], "color_index": 2},
    ]

    result, output_path = _run_chain(
        tmpdir=tmpdir,
        fixture_name="t5_colors.json",
        entities=entities,
        role_rules_profile={"marking_color_map": [2]},
        writer_rules_profile={"canonical_layer_colors": {"CUT_OUTER": 4, "CUT_INNER": 5, "MARKING": 6}},
    )
    _check_shape(result)

    echo = result["rules_profile_echo"]["canonical_layer_colors"]
    _assert(echo == {"CUT_OUTER": 4, "CUT_INNER": 5, "MARKING": 6}, "rules profile echo mismatch")

    doc = _read_doc(output_path)
    _assert(int(doc.layers.get("CUT_OUTER").dxf.color) == 4, "CUT_OUTER color mismatch")
    _assert(int(doc.layers.get("CUT_INNER").dxf.color) == 5, "CUT_INNER color mismatch")
    _assert(int(doc.layers.get("MARKING").dxf.color) == 6, "MARKING color mismatch")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="vrs_t5_normalized_writer_smoke_") as tmp_dir_str:
        tmpdir = Path(tmp_dir_str)
        _scenario_full_chain_writer_boundary(tmpdir)
        _scenario_canonical_layer_colors(tmpdir)

    print("[OK] DXF Prefilter E2-T5 normalized DXF writer smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
