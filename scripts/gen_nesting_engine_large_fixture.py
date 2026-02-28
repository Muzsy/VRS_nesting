#!/usr/bin/env python3
"""Generate deterministic large noholes fixtures for nesting_engine F2-3 benchmarks."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = ROOT / "poc/nesting_engine/f2_3_f4_cfr_order_hardening_noholes_v2.json"
DEFAULT_OUT_500 = ROOT / "poc/nesting_engine/f2_3_large_500_noholes_v2.json"
DEFAULT_OUT_1000 = ROOT / "poc/nesting_engine/f2_3_large_1000_noholes_v2.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _make_large_fixture(base_payload: dict[str, Any], total_parts: int) -> dict[str, Any]:
    if total_parts <= 0:
        raise ValueError("total_parts must be > 0")

    base_parts = base_payload.get("parts")
    if not isinstance(base_parts, list) or not base_parts:
        raise ValueError("base payload must contain a non-empty parts list")

    out = copy.deepcopy(base_payload)
    generated_parts: list[dict[str, Any]] = []

    for idx in range(total_parts):
        src = base_parts[idx % len(base_parts)]
        if not isinstance(src, dict):
            raise ValueError(f"base part is not an object: index={idx % len(base_parts)}")
        base_id = str(src.get("id", "")).strip()
        if not base_id:
            raise ValueError(f"base part id is missing at index={idx % len(base_parts)}")

        part = {
            "id": f"{base_id}__i{idx + 1:06d}",
            "quantity": 1,
            "allowed_rotations_deg": copy.deepcopy(src.get("allowed_rotations_deg", [])),
            "outer_points_mm": copy.deepcopy(src.get("outer_points_mm", [])),
            "holes_points_mm": copy.deepcopy(src.get("holes_points_mm", [])),
        }
        generated_parts.append(part)

    out["parts"] = generated_parts
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=str(DEFAULT_BASE), help="Base noholes fixture JSON path")
    parser.add_argument("--out-500", default=str(DEFAULT_OUT_500), help="Output path for 500 fixture")
    parser.add_argument("--out-1000", default=str(DEFAULT_OUT_1000), help="Output path for 1000 fixture")
    args = parser.parse_args(argv)

    base = Path(args.base)
    if not base.is_absolute():
        base = (ROOT / base).resolve()
    if not base.is_file():
        raise FileNotFoundError(f"base fixture not found: {base}")

    out_500 = Path(args.out_500)
    if not out_500.is_absolute():
        out_500 = ROOT / out_500
    out_1000 = Path(args.out_1000)
    if not out_1000.is_absolute():
        out_1000 = ROOT / out_1000

    payload = _read_json(base)
    fixture_500 = _make_large_fixture(payload, 500)
    fixture_1000 = _make_large_fixture(payload, 1000)

    _write_json(out_500, fixture_500)
    _write_json(out_1000, fixture_1000)

    print(f"[OK] wrote 500 fixture: {out_500}")
    print(f"[OK] wrote 1000 fixture: {out_1000}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
