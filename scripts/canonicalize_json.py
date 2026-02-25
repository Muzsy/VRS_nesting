#!/usr/bin/env python3
"""Canonicalize nesting_engine output into deterministic hash-view JSON.

Reads JSON from stdin and writes canonical JSON to stdout.
The output follows docs/nesting_engine/json_canonicalization.md:
  - schema_version = nesting_engine.hash_view.v1
  - placements sorted by (sheet_id, part_id, rotation_deg, x_scaled_i64, y_scaled_i64)
  - x/y scaled with round-half-away-from-zero at SCALE=1_000_000
"""

from __future__ import annotations

import json
import sys
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

SCALE = Decimal("1000000")
SCHEMA_VERSION = "nesting_engine.hash_view.v1"


def die(message: str) -> "NoReturn":
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(2)


def to_decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        die(f"{field} must not be boolean")
    if isinstance(value, (int, str)):
        try:
            return Decimal(str(value))
        except Exception as exc:  # pragma: no cover - defensive
            die(f"{field} is not numeric: {value!r} ({exc})")
    if isinstance(value, float):
        return Decimal(str(value))
    die(f"{field} is not numeric: {value!r}")


def round_half_away_from_zero(value: Decimal) -> int:
    scaled = value * SCALE
    if scaled >= 0:
        return int(scaled.to_integral_value(rounding=ROUND_HALF_UP))
    return -int((-scaled).to_integral_value(rounding=ROUND_HALF_UP))


def normalize_sheet_id(placement: dict[str, Any]) -> str:
    sheet_id = placement.get("sheet_id")
    if isinstance(sheet_id, str) and sheet_id:
        return sheet_id

    sheet = placement.get("sheet")
    if isinstance(sheet, bool):
        die("placements[].sheet must not be boolean")
    if isinstance(sheet, int):
        return f"S{sheet}"
    if isinstance(sheet, str) and sheet.strip():
        return sheet.strip()
    die("placements[] must include either sheet_id (string) or sheet (int/string)")


def normalize_placement(raw: Any, idx: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        die(f"placements[{idx}] is not an object")

    part_id = raw.get("part_id")
    if not isinstance(part_id, str) or not part_id:
        die(f"placements[{idx}].part_id must be a non-empty string")

    rotation_deg = raw.get("rotation_deg")
    if isinstance(rotation_deg, bool) or not isinstance(rotation_deg, int):
        die(f"placements[{idx}].rotation_deg must be an integer")

    x_scaled = raw.get("x_scaled_i64")
    y_scaled = raw.get("y_scaled_i64")
    if isinstance(x_scaled, int) and isinstance(y_scaled, int):
        x_scaled_i64 = int(x_scaled)
        y_scaled_i64 = int(y_scaled)
    else:
        x_mm = to_decimal(raw.get("x_mm"), f"placements[{idx}].x_mm")
        y_mm = to_decimal(raw.get("y_mm"), f"placements[{idx}].y_mm")
        x_scaled_i64 = round_half_away_from_zero(x_mm)
        y_scaled_i64 = round_half_away_from_zero(y_mm)

    return {
        "sheet_id": normalize_sheet_id(raw),
        "part_id": part_id,
        "rotation_deg": int(rotation_deg),
        "x_scaled_i64": x_scaled_i64,
        "y_scaled_i64": y_scaled_i64,
    }


def canonicalize(payload: Any) -> str:
    if not isinstance(payload, dict):
        die("top-level JSON value must be an object")

    placements = payload.get("placements")
    if not isinstance(placements, list):
        die("top-level placements must be an array")

    normalized = [normalize_placement(item, idx) for idx, item in enumerate(placements)]
    normalized.sort(
        key=lambda p: (
            p["sheet_id"],
            p["part_id"],
            p["rotation_deg"],
            p["x_scaled_i64"],
            p["y_scaled_i64"],
        )
    )

    hash_view = {
        "schema_version": SCHEMA_VERSION,
        "placements": normalized,
    }
    return json.dumps(hash_view, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def main() -> int:
    try:
        payload = json.load(sys.stdin, parse_float=Decimal)
    except json.JSONDecodeError as exc:
        die(f"invalid JSON on stdin: {exc}")

    print(canonicalize(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
