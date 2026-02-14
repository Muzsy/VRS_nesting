#!/usr/bin/env python3
"""Smoke checks for real DXF fixtures covering ARC/SPLINE/chaining paths."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vrs_nesting.dxf.importer import DxfImportError, import_part_raw


FIX_DIR = ROOT / "samples" / "dxf_demo"


def _require_ezdxf() -> None:
    if importlib.util.find_spec("ezdxf") is None:
        raise AssertionError(
            "ezdxf dependency missing for real DXF smoke. "
            "Install with: python3 -m pip install --break-system-packages ezdxf"
        )


def _expect_positive() -> None:
    part = import_part_raw(FIX_DIR / "part_arc_spline_chaining_ok.dxf")
    if len(part.outer_points_mm) < 3:
        raise AssertionError("outer ring too short")
    if len(part.holes_points_mm) < 1:
        raise AssertionError("expected at least one hole")

    types = {str(entity.get("type", "")).upper() for entity in part.source_entities}
    if "ARC" not in types:
        raise AssertionError(f"ARC not found in source_entities: {sorted(types)}")
    if "SPLINE" not in types:
        raise AssertionError(f"SPLINE not found in source_entities: {sorted(types)}")


def _expect_negative() -> None:
    try:
        import_part_raw(FIX_DIR / "part_chain_open_fail.dxf")
    except DxfImportError as exc:
        if exc.code != "DXF_OPEN_OUTER_PATH":
            raise AssertionError(f"expected DXF_OPEN_OUTER_PATH, got {exc.code}") from exc
        return
    raise AssertionError("expected DxfImportError for open chaining fixture")


def main() -> int:
    _require_ezdxf()

    required = [
        FIX_DIR / "stock_rect_1000x2000.dxf",
        FIX_DIR / "part_arc_spline_chaining_ok.dxf",
        FIX_DIR / "part_chain_open_fail.dxf",
    ]
    for path in required:
        if not path.is_file():
            raise AssertionError(f"missing fixture: {path}")

    _expect_positive()
    _expect_negative()

    print("[OK] real DXF fixture smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
