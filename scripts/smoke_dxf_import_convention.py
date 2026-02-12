#!/usr/bin/env python3
"""Smoke checks for DXF layer-convention importer."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vrs_nesting.dxf.importer import DxfImportError, import_part_raw
FIX_DIR = ROOT / "samples" / "dxf_import"


def _expect_success(path: Path) -> None:
    part = import_part_raw(path)
    if len(part.outer_points_mm) < 3:
        raise AssertionError("outer polygon too short")
    if len(part.holes_points_mm) != 1:
        raise AssertionError(f"expected 1 hole, got {len(part.holes_points_mm)}")


def _expect_error(path: Path, code: str) -> None:
    try:
        import_part_raw(path)
    except DxfImportError as exc:
        if exc.code != code:
            raise AssertionError(f"expected error code {code}, got {exc.code}") from exc
        return
    raise AssertionError(f"expected importer error {code} for {path}")


def main() -> int:
    _expect_success(FIX_DIR / "part_contract_ok.json")
    _expect_error(FIX_DIR / "part_missing_outer.json", "DXF_NO_OUTER_LAYER")
    _expect_error(FIX_DIR / "part_open_outer.json", "DXF_OPEN_OUTER_PATH")
    print("[OK] DXF import convention smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
