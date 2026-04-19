#!/usr/bin/env python3
"""DXF Prefilter E2-T1 -- preflight inspect engine smoke.

Deterministic, backend-independent smoke for the inspect-only DXF preflight
engine. It runs the public importer inspect helper + the preflight inspect
service against a fixed in-memory JSON fixture and checks:

* the inspect result has the expected inventory / candidate / diagnostics
  layers,
* raw `layer / type / closed / color_index / linetype_name` signals survive
  normalisation,
* contour, open-path, duplicate, outer-like and inner-like candidates are
  listed without any role assignment / repair / acceptance outcome,
* a hard-fail input (missing file) still produces a stable importer-level
  error (``DxfPreflightInspectError``) as required by the canvas.

The smoke intentionally does NOT depend on the real ``ezdxf`` backend so
that it stays green in minimal CI environments; the real DXF backend is
covered by the existing repo smoke suite.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.dxf_preflight_inspect import (
    DxfPreflightInspectError,
    inspect_dxf_source,
)


EXPECTED_KEYS: tuple[str, ...] = (
    "source_path",
    "backend",
    "source_size_bytes",
    "entity_inventory",
    "layer_inventory",
    "color_inventory",
    "linetype_inventory",
    "contour_candidates",
    "open_path_candidates",
    "duplicate_contour_candidates",
    "outer_like_candidates",
    "inner_like_candidates",
    "diagnostics",
)

FORBIDDEN_KEYS: tuple[str, ...] = (
    # Acceptance world (E2-T6) must not leak into T1.
    "acceptance",
    "acceptance_outcome",
    "acceptance_status",
    # Role assignment world (E2-T2) must not leak into T1.
    "roles",
    "role_assignments",
    "canonical_roles",
    # Repair world (E2-T3 / E2-T4) must not leak into T1.
    "repair",
    "repairs",
    "gap_fixes",
)


def _write_fixture_file(tmp_dir: Path) -> Path:
    payload = {
        "entities": [
            {
                "layer": "CUT_OUTER",
                "type": "LWPOLYLINE",
                "closed": True,
                "points": [[0, 0], [100, 0], [100, 80], [0, 80]],
                "color_index": 7,
                "linetype_name": "CONTINUOUS",
            },
            {
                "layer": "CUT_INNER",
                "type": "LWPOLYLINE",
                "closed": True,
                "points": [[10, 10], [30, 10], [30, 30], [10, 30]],
                "color_index": 1,
                "linetype_name": "CONTINUOUS",
            },
            {
                "layer": "CUT_INNER",
                "type": "LWPOLYLINE",
                "closed": True,
                "points": [[10, 10], [30, 10], [30, 30], [10, 30]],
                "color_index": 1,
                "linetype_name": "CONTINUOUS",
            },
            {
                "layer": "CUT_INNER",
                "type": "LINE",
                "points": [[50, 50], [60, 50]],
            },
            {
                "layer": "MARKING",
                "type": "LINE",
                "points": [[5, 5], [95, 5]],
            },
        ]
    }
    fixture_path = tmp_dir / "preflight_inspect_smoke.json"
    fixture_path.write_text(json.dumps(payload), encoding="utf-8")
    return fixture_path


def _assert(cond: bool, message: str) -> None:
    if not cond:
        raise AssertionError(message)


def _check_inspect_result(result: dict) -> None:
    # Shape check.
    for key in EXPECTED_KEYS:
        _assert(key in result, f"missing top-level key: {key}")
    for forbidden in FORBIDDEN_KEYS:
        _assert(forbidden not in result, f"preflight T1 must not expose '{forbidden}'")

    _assert(result["backend"] == "json", f"backend expected 'json', got {result['backend']!r}")

    # Inventories.
    layer_names = [item["layer"] for item in result["layer_inventory"]]
    _assert(
        layer_names == sorted(layer_names),
        "layer_inventory must be deterministically sorted by layer name",
    )
    _assert(
        set(layer_names) == {"CUT_INNER", "CUT_OUTER", "MARKING"},
        f"unexpected layer set: {layer_names}",
    )

    color_counts = {item["color_index"]: item["count"] for item in result["color_inventory"]}
    _assert(color_counts.get(7) == 1, "expected raw ACI color_index=7 present once")
    _assert(color_counts.get(1) == 2, "expected raw ACI color_index=1 present twice")
    _assert(color_counts.get(None) == 2, "expected 2 entities without explicit color (raw None)")

    linetype_counts = {item["linetype_name"]: item["count"] for item in result["linetype_inventory"]}
    _assert(
        linetype_counts.get("CONTINUOUS") == 3,
        "expected CONTINUOUS linetype count == 3",
    )
    _assert(linetype_counts.get(None) == 2, "expected 2 entities without explicit linetype (raw None)")

    # Candidates.
    contour_refs = sorted((c["layer"], c["ring_index"]) for c in result["contour_candidates"])
    _assert(
        contour_refs == [("CUT_INNER", 0), ("CUT_INNER", 1), ("CUT_OUTER", 0)],
        f"unexpected contour candidates: {contour_refs}",
    )

    open_by_layer = {c["layer"]: c["open_path_count"] for c in result["open_path_candidates"]}
    _assert(
        open_by_layer == {"CUT_INNER": 1, "MARKING": 1},
        f"unexpected open-path candidates: {open_by_layer}",
    )

    duplicates = result["duplicate_contour_candidates"]
    _assert(len(duplicates) == 1, f"expected exactly one duplicate contour group, got {len(duplicates)}")
    dup_refs = sorted((r["layer"], r["ring_index"]) for r in duplicates[0]["ring_references"])
    _assert(
        dup_refs == [("CUT_INNER", 0), ("CUT_INNER", 1)],
        f"unexpected duplicate contour members: {dup_refs}",
    )

    outer_like_layers = sorted(c["layer"] for c in result["outer_like_candidates"])
    inner_like_layers = sorted(c["layer"] for c in result["inner_like_candidates"])
    _assert("CUT_OUTER" in outer_like_layers, "CUT_OUTER must appear as outer-like (bbox contains inner)")
    _assert("CUT_INNER" in inner_like_layers, "CUT_INNER must appear as inner-like (bbox contained by outer)")

    # Diagnostics shape.
    diagnostics = result["diagnostics"]
    _assert(isinstance(diagnostics, dict), "diagnostics must be a dict")
    _assert(isinstance(diagnostics.get("probe_errors"), list), "diagnostics.probe_errors must be a list")
    _assert(isinstance(diagnostics.get("notes"), list), "diagnostics.notes must be a list")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="vrs_preflight_inspect_smoke_") as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        fixture_path = _write_fixture_file(tmp_dir)

        result = inspect_dxf_source(fixture_path)
        _check_inspect_result(result)

        # Hard-fail leg: missing source must raise DxfPreflightInspectError
        # with a stable code -- this is the run.md-required hard-fail scenario.
        missing_path = tmp_dir / "does_not_exist.json"
        try:
            inspect_dxf_source(missing_path)
        except DxfPreflightInspectError as exc:
            _assert(
                exc.code == "DXF_PATH_NOT_FOUND",
                f"expected DXF_PATH_NOT_FOUND on missing source, got {exc.code}",
            )
        else:
            raise AssertionError("expected DxfPreflightInspectError for missing source")

    print("[OK] DXF Prefilter E2-T1 preflight inspect engine smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
