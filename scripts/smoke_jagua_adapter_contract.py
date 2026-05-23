#!/usr/bin/env python3
"""JG-04 jagua adapter contract smoke: builds + runs jagua_adapter_smoke binary and checks output."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
MANIFEST = ROOT / "rust" / "vrs_solver" / "Cargo.toml"
SMOKE_BIN = ROOT / "rust" / "vrs_solver" / "target" / "release" / "jagua_adapter_smoke"


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def _ok(msg: str) -> None:
    print(f"OK: {msg}")


def build_smoke() -> None:
    print("[Building jagua_adapter_smoke binary]")
    result = subprocess.run(
        [
            "cargo",
            "build",
            "--release",
            "--manifest-path",
            str(MANIFEST),
            "--bin",
            "jagua_adapter_smoke",
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    if result.returncode != 0:
        _fail(f"cargo build --bin jagua_adapter_smoke failed:\n{result.stderr}")
    _ok("cargo build --bin jagua_adapter_smoke PASS")


def run_smoke() -> dict:
    if not SMOKE_BIN.is_file():
        _fail(f"Smoke binary not found: {SMOKE_BIN}")
    result = subprocess.run(
        [str(SMOKE_BIN)],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    if result.returncode != 0:
        _fail(
            f"jagua_adapter_smoke exited {result.returncode}:\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    try:
        return json.loads(result.stdout)
    except Exception as exc:
        _fail(f"Smoke binary output is not valid JSON: {exc}\noutput: {result.stdout!r}")


def check_output(data: dict) -> None:
    # Top-level status
    if data.get("status") != "ok":
        _fail(f"Expected status=ok, got: {data.get('status')!r}")
    _ok("status=ok")

    cases = data.get("cases", {})

    # Case 1: item-item non-overlap
    if cases.get("item_item_non_overlap") is not True:
        _fail(
            f"item_item_non_overlap expected true (disjoint rects → no collision), "
            f"got: {cases.get('item_item_non_overlap')!r}"
        )
    _ok("item_item_non_overlap=true (disjoint rects correctly detected as non-colliding)")

    # Case 2: item-item overlap
    if cases.get("item_item_overlap") is not True:
        _fail(
            f"item_item_overlap expected true (overlapping rects → collision), "
            f"got: {cases.get('item_item_overlap')!r}"
        )
    _ok("item_item_overlap=true (overlapping rects correctly detected as colliding)")

    # Case 3: item-sheet boundary
    if cases.get("item_sheet_boundary") is not True:
        _fail(
            f"item_sheet_boundary expected true (inside accepted + outside rejected), "
            f"got: {cases.get('item_sheet_boundary')!r}"
        )
    _ok("item_sheet_boundary=true (inside item accepted, outside item rejected)")

    # Conversion note must be present
    notes = data.get("notes", [])
    if "f64_to_f32_conversion_used" not in notes:
        _fail(
            f"Expected 'f64_to_f32_conversion_used' in notes (precision risk documented), "
            f"got: {notes!r}"
        )
    _ok("f64_to_f32_conversion_used note present (precision risk documented)")


def main() -> None:
    print("=== JG-04 jagua adapter contract smoke ===")
    build_smoke()
    print("\n[Running jagua_adapter_smoke binary]")
    data = run_smoke()
    print(f"Binary output:\n{json.dumps(data, indent=2)}")
    print("\n[Checking assertions]")
    check_output(data)
    print("\nALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    main()
