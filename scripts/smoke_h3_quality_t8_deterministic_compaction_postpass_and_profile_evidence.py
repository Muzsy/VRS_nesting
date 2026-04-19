#!/usr/bin/env python3
"""Smoke for T8 deterministic compaction post-pass evidence."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "poc" / "nesting_engine" / "f3_4_compaction_slide_fixture_v2.json"
DEFAULT_BIN = ROOT / "rust" / "nesting_engine" / "target" / "release" / "nesting_engine"
MANIFEST_PATH = ROOT / "rust" / "nesting_engine" / "Cargo.toml"
EXPECTED_VERSION = "nesting_engine_v2"


def _ensure_bin(bin_path: Path) -> Path:
    cmd = [
        "cargo",
        "build",
        "--release",
        "--manifest-path",
        str(MANIFEST_PATH),
    ]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise AssertionError(
            "failed to build nesting_engine release binary for T8 smoke\n"
            f"cmd={' '.join(cmd)}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )

    if not (bin_path.is_file() and os.access(bin_path, os.X_OK)):
        raise AssertionError(f"nesting_engine binary missing after build: {bin_path}")

    return bin_path


def _load_output(bin_path: Path, fixture_payload: bytes, mode: str, run_index: int) -> dict[str, Any]:
    cmd = [str(bin_path), "nest", "--compaction", mode]
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        input=fixture_payload,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(
            "compaction smoke run failed "
            f"(mode={mode}, run={run_index}, rc={proc.returncode})\n"
            f"cmd={' '.join(cmd)}\n"
            f"stderr:\n{proc.stderr.decode('utf-8', errors='replace')}"
        )

    try:
        payload = json.loads(proc.stdout.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"compaction smoke output is not valid JSON (mode={mode}, run={run_index})"
        ) from exc

    if not isinstance(payload, dict):
        raise AssertionError(f"unexpected non-object output (mode={mode}, run={run_index})")

    version = str(payload.get("version", "")).strip()
    if version != EXPECTED_VERSION:
        raise AssertionError(
            f"unexpected version for mode={mode}, run={run_index}: {version!r}"
        )

    meta = payload.get("meta")
    if not isinstance(meta, dict):
        raise AssertionError(f"missing meta object for mode={mode}, run={run_index}")

    determinism_hash = str(meta.get("determinism_hash", "")).strip()
    if not determinism_hash:
        raise AssertionError(f"missing determinism_hash for mode={mode}, run={run_index}")

    compaction = meta.get("compaction")
    if not isinstance(compaction, dict):
        raise AssertionError(f"missing meta.compaction object for mode={mode}, run={run_index}")

    reported_mode = str(compaction.get("mode", "")).strip()
    if reported_mode != mode:
        raise AssertionError(
            f"meta.compaction.mode mismatch for mode={mode}, run={run_index}: {reported_mode!r}"
        )

    placements = payload.get("placements")
    if not isinstance(placements, list):
        raise AssertionError(f"missing placements array for mode={mode}, run={run_index}")

    unplaced = payload.get("unplaced")
    if not isinstance(unplaced, list):
        raise AssertionError(f"missing unplaced array for mode={mode}, run={run_index}")

    sheets_used = payload.get("sheets_used")
    if isinstance(sheets_used, bool) or not isinstance(sheets_used, int):
        raise AssertionError(f"invalid sheets_used for mode={mode}, run={run_index}: {sheets_used!r}")

    objective = payload.get("objective")
    objective_obj = objective if isinstance(objective, dict) else {}
    remnant_value_ppm = objective_obj.get("remnant_value_ppm")
    if isinstance(remnant_value_ppm, bool) or not isinstance(remnant_value_ppm, int):
        raise AssertionError(
            f"missing objective.remnant_value_ppm for mode={mode}, run={run_index}"
        )

    moved_items_count = compaction.get("moved_items_count")
    if isinstance(moved_items_count, bool) or not isinstance(moved_items_count, int):
        raise AssertionError(
            f"missing meta.compaction.moved_items_count for mode={mode}, run={run_index}"
        )

    extent_after = compaction.get("occupied_extent_after")
    if not isinstance(extent_after, dict):
        raise AssertionError(
            f"missing meta.compaction.occupied_extent_after for mode={mode}, run={run_index}"
        )

    width_after = extent_after.get("width_mm")
    height_after = extent_after.get("height_mm")
    if isinstance(width_after, bool) or not isinstance(width_after, (int, float)):
        raise AssertionError(
            f"missing occupied_extent_after.width_mm for mode={mode}, run={run_index}"
        )
    if isinstance(height_after, bool) or not isinstance(height_after, (int, float)):
        raise AssertionError(
            f"missing occupied_extent_after.height_mm for mode={mode}, run={run_index}"
        )

    return {
        "determinism_hash": determinism_hash,
        "sheets_used": int(sheets_used),
        "unplaced_count": len(unplaced),
        "remnant_value_ppm": int(remnant_value_ppm),
        "compaction_applied": bool(compaction.get("applied") is True),
        "compaction_moved_items_count": int(moved_items_count),
        "occupied_extent_after_width_mm": float(width_after),
        "occupied_extent_after_height_mm": float(height_after),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bin", default=str(DEFAULT_BIN), help="Path to nesting_engine binary")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Path to T8 fixture JSON")
    parser.add_argument(
        "--slide-runs",
        type=int,
        default=3,
        help="Repeated run count for --compaction slide determinism check (>=2)",
    )
    args = parser.parse_args(argv)

    if args.slide_runs < 2:
        raise AssertionError("--slide-runs must be >= 2")

    bin_path = _ensure_bin(Path(args.bin).resolve())
    input_path = Path(args.input).resolve()
    if not input_path.is_file():
        raise AssertionError(f"fixture JSON not found: {input_path}")

    fixture_payload = input_path.read_bytes()

    off = _load_output(bin_path, fixture_payload, "off", 1)
    slide_runs: list[dict[str, Any]] = []
    for idx in range(1, args.slide_runs + 1):
        slide_runs.append(_load_output(bin_path, fixture_payload, "slide", idx))

    slide_hashes = [str(item["determinism_hash"]) for item in slide_runs]
    if len(set(slide_hashes)) != 1:
        raise AssertionError(f"slide determinism hash mismatch across runs: {slide_hashes}")

    slide = slide_runs[0]

    # Primary objective guard: compaction post-pass cannot worsen placement completeness.
    if slide["unplaced_count"] != off["unplaced_count"]:
        raise AssertionError(
            f"primary objective regression: unplaced changed {off['unplaced_count']} -> {slide['unplaced_count']}"
        )
    if slide["sheets_used"] != off["sheets_used"]:
        raise AssertionError(
            f"primary objective regression: sheets_used changed {off['sheets_used']} -> {slide['sheets_used']}"
        )

    if not slide["compaction_applied"]:
        raise AssertionError("expected slide mode to apply compaction on the T8 fixture")
    if slide["compaction_moved_items_count"] <= 0:
        raise AssertionError("expected moved_items_count > 0 on the T8 fixture")

    width_delta = (
        slide["occupied_extent_after_width_mm"] - off["occupied_extent_after_width_mm"]
    )
    height_delta = (
        slide["occupied_extent_after_height_mm"] - off["occupied_extent_after_height_mm"]
    )

    if width_delta > 0.0 or height_delta > 0.0:
        raise AssertionError(
            "compaction extent regression: "
            f"width_delta={width_delta:.6f}, height_delta={height_delta:.6f}"
        )
    if width_delta >= 0.0 and height_delta >= 0.0:
        raise AssertionError(
            "expected measurable compaction uplift on fixture "
            "(width or height must strictly decrease)"
        )

    print(
        "[OK] T8 compaction smoke passed: "
        f"slide_hash={slide_hashes[0]}, "
        f"moved={slide['compaction_moved_items_count']}, "
        f"extent_delta_mm=(w={width_delta:.6f}, h={height_delta:.6f}), "
        f"remnant_delta_ppm={slide['remnant_value_ppm'] - off['remnant_value_ppm']}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
